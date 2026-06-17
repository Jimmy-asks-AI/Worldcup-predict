from __future__ import annotations

import math
import random


SUPPORTED_SCORE_MODELS = ("independent_poisson", "dixon_coles")


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def validate_score_model(score_model: str) -> str:
    if score_model not in SUPPORTED_SCORE_MODELS:
        allowed = ", ".join(SUPPORTED_SCORE_MODELS)
        raise ValueError(f"Unsupported score_model {score_model!r}; expected one of: {allowed}")
    return score_model


def dixon_coles_tau(home_goals: int, away_goals: int, lambda_home: float, lambda_away: float, rho: float) -> float:
    if home_goals == 0 and away_goals == 0:
        value = 1.0 - lambda_home * lambda_away * rho
    elif home_goals == 0 and away_goals == 1:
        value = 1.0 + lambda_home * rho
    elif home_goals == 1 and away_goals == 0:
        value = 1.0 + lambda_away * rho
    elif home_goals == 1 and away_goals == 1:
        value = 1.0 - rho
    else:
        value = 1.0
    return max(0.001, value)


def scoreline_matrix(
    lambda_home: float,
    lambda_away: float,
    max_goals: int = 7,
    score_model: str = "independent_poisson",
    dixon_coles_rho: float = -0.08,
) -> list[list[float]]:
    validate_score_model(score_model)
    matrix = []
    total = 0.0
    for home_goals in range(max_goals + 1):
        row = []
        for away_goals in range(max_goals + 1):
            probability = poisson_pmf(home_goals, lambda_home) * poisson_pmf(away_goals, lambda_away)
            if score_model == "dixon_coles":
                probability *= dixon_coles_tau(home_goals, away_goals, lambda_home, lambda_away, dixon_coles_rho)
            row.append(probability)
            total += probability
        matrix.append(row)
    if total <= 0:
        raise ValueError("Scoreline matrix has no probability mass")
    return [[probability / total for probability in row] for row in matrix]


def aggregate_wdl(matrix: list[list[float]]) -> tuple[float, float, float]:
    p_home = p_draw = p_away = 0.0
    for home_goals, row in enumerate(matrix):
        for away_goals, probability in enumerate(row):
            if home_goals > away_goals:
                p_home += probability
            elif home_goals == away_goals:
                p_draw += probability
            else:
                p_away += probability
    return p_home, p_draw, p_away


def sorted_scorelines(matrix: list[list[float]]) -> list[dict[str, float | str]]:
    scorelines = []
    for home_goals, row in enumerate(matrix):
        for away_goals, probability in enumerate(row):
            scorelines.append(
                {
                    "scoreline": f"{home_goals}-{away_goals}",
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "probability": round(probability, 6),
                }
            )
    scorelines.sort(key=lambda item: item["probability"], reverse=True)
    return scorelines


def sample_scoreline(rng: random.Random, matrix: list[list[float]]) -> tuple[int, int]:
    threshold = rng.random()
    cumulative = 0.0
    last = (0, 0)
    for home_goals, row in enumerate(matrix):
        for away_goals, probability in enumerate(row):
            cumulative += probability
            last = (home_goals, away_goals)
            if threshold <= cumulative:
                return home_goals, away_goals
    return last
