from __future__ import annotations

import random
from dataclasses import dataclass

from .score_models import aggregate_wdl, scoreline_matrix, validate_score_model


def _quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("Cannot compute quantile for empty values")
    ordered = sorted(values)
    idx = (len(ordered) - 1) * q
    lower = int(idx)
    upper = min(lower + 1, len(ordered) - 1)
    weight = idx - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _interval(values: list[float]) -> dict[str, float]:
    return {
        "p05": round(_quantile(values, 0.05), 6),
        "p50": round(_quantile(values, 0.50), 6),
        "p95": round(_quantile(values, 0.95), 6),
    }


@dataclass(frozen=True)
class UncertaintyAgent:
    samples: int = 500
    lambda_sd: float = 0.12
    seed: int = 2026

    def __post_init__(self):
        if self.samples < 50:
            raise ValueError("Uncertainty samples must be at least 50")
        if self.lambda_sd <= 0:
            raise ValueError("lambda_sd must be positive")

    def estimate(
        self,
        lambda_home: float,
        lambda_away: float,
        max_goals: int,
        score_model: str,
        dixon_coles_rho: float = -0.08,
    ) -> dict[str, object]:
        validate_score_model(score_model)
        rng = random.Random(self.seed)
        p_home_values: list[float] = []
        p_draw_values: list[float] = []
        p_away_values: list[float] = []
        expected_goals_values: list[float] = []

        for _ in range(self.samples):
            home_lambda = self._perturbed_lambda(rng, lambda_home)
            away_lambda = self._perturbed_lambda(rng, lambda_away)
            matrix = scoreline_matrix(
                home_lambda,
                away_lambda,
                max_goals=max_goals,
                score_model=score_model,
                dixon_coles_rho=dixon_coles_rho,
            )
            p_home, p_draw, p_away = aggregate_wdl(matrix)
            p_home_values.append(p_home)
            p_draw_values.append(p_draw)
            p_away_values.append(p_away)
            expected_goals_values.append(home_lambda + away_lambda)

        return {
            "used": True,
            "method": "lambda_lognormal_perturbation",
            "bayesian_status": "proxy_not_full_bayesian",
            "source_inspiration": "lbenz730/world_cup_2026 Bayesian bivariate Poisson uncertainty framing",
            "samples": self.samples,
            "seed": self.seed,
            "lambda_sd": self.lambda_sd,
            "intervals": {
                "p_home_win": _interval(p_home_values),
                "p_draw": _interval(p_draw_values),
                "p_away_win": _interval(p_away_values),
                "expected_goals": _interval(expected_goals_values),
            },
            "warnings": [
                "This is a lightweight uncertainty proxy around fitted lambdas, not a full Bayesian bivariate Poisson posterior.",
            ],
        }

    def _perturbed_lambda(self, rng: random.Random, value: float) -> float:
        multiplier = rng.lognormvariate(-0.5 * self.lambda_sd * self.lambda_sd, self.lambda_sd)
        return round(max(0.15, min(4.5, value * multiplier)), 6)
