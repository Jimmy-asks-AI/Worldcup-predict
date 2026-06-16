from __future__ import annotations

import math
from dataclasses import asdict
from typing import TYPE_CHECKING

from .aliases import normalize_team
from .events import EventAgent
from .models import MatchPrediction
from .strength import StrengthAgent

if TYPE_CHECKING:
    from .context import MatchContextAgent
    from .lineups import LineupAgent


class ScorelineAgent:
    def __init__(
        self,
        strength: StrengthAgent,
        max_goals: int = 7,
        lineup: "LineupAgent | None" = None,
        context: "MatchContextAgent | None" = None,
        events: EventAgent | None = None,
    ):
        self.strength = strength
        self.max_goals = max_goals
        self.lineup = lineup
        self.context = context
        self.events = events

    @staticmethod
    def poisson_pmf(k: int, lam: float) -> float:
        return math.exp(-lam) * (lam**k) / math.factorial(k)

    def predict(self, home: str, away: str, match_id: str = "") -> MatchPrediction:
        home = normalize_team(home)
        away = normalize_team(away)
        lam_h, lam_a, warnings = self.strength.expected_lambdas(home, away)
        lineup_payload = {}
        context_payload = {}
        if self.lineup:
            adjustment = self.lineup.match_adjustment(home, away, match_id)
            lam_h = round(max(0.15, min(4.5, lam_h * adjustment.lambda_home_multiplier)), 4)
            lam_a = round(max(0.15, min(4.5, lam_a * adjustment.lambda_away_multiplier)), 4)
            warnings.extend(adjustment.warnings)
            lineup_payload = asdict(adjustment)
        if self.context:
            adjustment = self.context.match_adjustment(home, away, match_id)
            lam_h = round(max(0.15, min(4.5, lam_h * adjustment.lambda_home_multiplier)), 4)
            lam_a = round(max(0.15, min(4.5, lam_a * adjustment.lambda_away_multiplier)), 4)
            warnings.extend(adjustment.warnings)
            context_payload = adjustment.as_payload()
        matrix = []
        total = 0.0
        for h_goals in range(self.max_goals + 1):
            row = []
            for a_goals in range(self.max_goals + 1):
                p = self.poisson_pmf(h_goals, lam_h) * self.poisson_pmf(a_goals, lam_a)
                row.append(p)
                total += p
            matrix.append(row)
        matrix = [[p / total for p in row] for row in matrix]

        p_home = p_draw = p_away = 0.0
        scorelines = []
        for h_goals, row in enumerate(matrix):
            for a_goals, p in enumerate(row):
                if h_goals > a_goals:
                    p_home += p
                elif h_goals == a_goals:
                    p_draw += p
                else:
                    p_away += p
                scorelines.append(
                    {
                        "scoreline": f"{h_goals}-{a_goals}",
                        "home_goals": h_goals,
                        "away_goals": a_goals,
                        "probability": round(p, 6),
                    }
                )
        scorelines.sort(key=lambda item: item["probability"], reverse=True)
        event_payload = (
            self.events.predict(home, away, lam_h, lam_a, context_payload) if self.events else {}
        )
        return MatchPrediction(
            home_team=home,
            away_team=away,
            lambda_home=lam_h,
            lambda_away=lam_a,
            p_home_win=round(p_home, 6),
            p_draw=round(p_draw, 6),
            p_away_win=round(p_away, 6),
            top_scorelines=scorelines[:10],
            expected_goals=round(lam_h + lam_a, 4),
            warnings=warnings,
            match_id=match_id,
            lineup_adjustment=lineup_payload,
            context_adjustment=context_payload,
            event_prediction=event_payload,
        )

    def sample_score(self, rng, home: str, away: str, match_id: str = "") -> tuple[int, int]:
        pred = self.predict(home, away, match_id=match_id)
        return self._poisson_sample(rng, pred.lambda_home), self._poisson_sample(rng, pred.lambda_away)

    @staticmethod
    def _poisson_sample(rng, lam: float) -> int:
        limit = math.exp(-lam)
        k = 0
        p = 1.0
        while p > limit:
            k += 1
            p *= rng.random()
        return k - 1
