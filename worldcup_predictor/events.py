from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from .aliases import normalize_team
from .data import DEFAULT_DATA_DIR, read_csv


EVENT_METRICS = {
    "yellow_cards": {"label": "yellow_cards", "cap": 8, "context": "discipline"},
    "red_cards": {"label": "red_cards", "cap": 3, "context": "discipline"},
    "corners": {"label": "corners", "cap": 16, "context": "set_piece"},
    "free_kicks": {"label": "free_kick_passes", "cap": 24, "context": "set_piece"},
    "penalties": {"label": "penalty_shots", "cap": 4, "context": "penalty"},
}


def _num(row: dict[str, str], name: str, default: float = 0.0) -> float:
    try:
        return float(row.get(name, "") or default)
    except ValueError:
        return default


def _poisson_mode(lam: float) -> int:
    return max(0, int(math.floor(lam)))


class EventAgent:
    """Predicts match event counts by half from historical team-half event rates."""

    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.team_rates, self.global_rates, self.sample_rows = self._load_event_rates()

    def _load_event_rates(self) -> tuple[dict[str, dict[int, dict[str, float]]], dict[int, dict[str, float]], int]:
        path = self.data_dir / "statsbomb_event_half_team_summary.csv"
        if not path.exists():
            return {}, {}, 0
        rows = read_csv(path)
        team_totals: dict[str, dict[int, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        global_totals: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        team_counts: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        global_counts: dict[int, float] = defaultdict(float)
        for row in rows:
            team = normalize_team(row.get("team", ""))
            half = int(_num(row, "half", 0.0))
            if half not in {1, 2}:
                continue
            team_counts[team][half] += 1.0
            global_counts[half] += 1.0
            for metric, info in EVENT_METRICS.items():
                column = str(info["label"])
                value = _num(row, column)
                team_totals[team][half][metric] += value
                global_totals[half][metric] += value
        team_rates = {}
        for team, halves in team_totals.items():
            team_rates[team] = {}
            for half, totals in halves.items():
                denom = max(1.0, team_counts[team][half])
                team_rates[team][half] = {metric: totals[metric] / denom for metric in EVENT_METRICS}
        global_rates = {}
        for half, totals in global_totals.items():
            denom = max(1.0, global_counts[half])
            global_rates[half] = {metric: totals[metric] / denom for metric in EVENT_METRICS}
        return team_rates, global_rates, len(rows)

    def predict(
        self,
        home: str,
        away: str,
        lambda_home: float,
        lambda_away: float,
        context_adjustment: dict[str, object] | None = None,
    ) -> dict[str, object]:
        home = normalize_team(home)
        away = normalize_team(away)
        context_adjustment = context_adjustment or {}
        discipline_index = float(context_adjustment.get("discipline_index") or 1.0)
        set_piece_index = float(context_adjustment.get("set_piece_index") or 1.0)
        referee = context_adjustment.get("referee_context") or {}
        penalty_rate = float(referee.get("penalties_per_match") or 0.25) / 0.25
        total_lambda = max(0.2, lambda_home + lambda_away)
        tempo_index = max(0.85, min(1.18, total_lambda / 2.65))
        teams = {
            "home": self._team_event_prediction(home, tempo_index, discipline_index, set_piece_index, penalty_rate),
            "away": self._team_event_prediction(away, tempo_index, discipline_index, set_piece_index, penalty_rate),
        }
        totals = {}
        for metric in EVENT_METRICS:
            first_half = teams["home"][metric]["first_half_expected"] + teams["away"][metric]["first_half_expected"]
            second_half = teams["home"][metric]["second_half_expected"] + teams["away"][metric]["second_half_expected"]
            total = first_half + second_half
            totals[metric] = {
                "first_half_expected": round(first_half, 3),
                "second_half_expected": round(second_half, 3),
                "total_expected": round(total, 3),
                "most_likely_total": _poisson_mode(total),
            }
        warnings = []
        if self.sample_rows == 0:
            warnings.append("missing StatsBomb half-team event sample; event predictions are neutral")
        for team in (home, away):
            if team not in self.team_rates:
                warnings.append(f"{team} missing event sample, fallback global half rates")
        return {
            "source": "statsbomb_event_half_team_summary",
            "sample_rows": self.sample_rows,
            "context": {
                "tempo_index": round(tempo_index, 4),
                "discipline_index": round(discipline_index, 4),
                "set_piece_index": round(set_piece_index, 4),
                "penalty_rate_index": round(max(0.7, min(1.5, penalty_rate)), 4),
            },
            "teams": teams,
            "match_totals": totals,
            "warnings": warnings,
        }

    def _team_event_prediction(
        self,
        team: str,
        tempo_index: float,
        discipline_index: float,
        set_piece_index: float,
        penalty_rate: float,
    ) -> dict[str, dict[str, float | int]]:
        out = {}
        for metric, info in EVENT_METRICS.items():
            first = self._half_rate(team, 1, metric)
            second = self._half_rate(team, 2, metric)
            context = info["context"]
            if context == "discipline":
                multiplier = discipline_index
            elif context == "set_piece":
                multiplier = set_piece_index * tempo_index
            elif context == "penalty":
                multiplier = max(0.7, min(1.5, penalty_rate)) * discipline_index
            else:
                multiplier = 1.0
            first *= multiplier
            second *= multiplier
            total = first + second
            out[metric] = {
                "first_half_expected": round(first, 3),
                "second_half_expected": round(second, 3),
                "total_expected": round(total, 3),
                "most_likely_total": _poisson_mode(total),
            }
        return out

    def _half_rate(self, team: str, half: int, metric: str) -> float:
        team_half = self.team_rates.get(team, {}).get(half)
        if team_half and metric in team_half:
            return team_half[metric]
        return self.global_rates.get(half, {}).get(metric, 0.0)
