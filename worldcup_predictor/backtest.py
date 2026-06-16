from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .aliases import normalize_team
from .data import DEFAULT_DATA_DIR, OUTPUT_DIR, read_csv
from .scoreline import ScorelineAgent
from .strength import elo_goal_multipliers, elo_win_probability


@dataclass
class TeamBacktestState:
    elo: float = 1500.0
    matches: int = 0
    goals_for: int = 0
    goals_against: int = 0
    recent_for: list[int] = field(default_factory=list)
    recent_against: list[int] = field(default_factory=list)

    def attack_average(self, fallback: float) -> float:
        if not self.matches:
            return fallback
        all_avg = self.goals_for / self.matches
        recent_avg = sum(self.recent_for) / len(self.recent_for) if self.recent_for else all_avg
        return 0.65 * recent_avg + 0.35 * all_avg

    def defense_average(self, fallback: float) -> float:
        if not self.matches:
            return fallback
        all_avg = self.goals_against / self.matches
        recent_avg = sum(self.recent_against) / len(self.recent_against) if self.recent_against else all_avg
        return 0.65 * recent_avg + 0.35 * all_avg

    def update_goals(self, goals_for: int, goals_against: int, window: int) -> None:
        self.matches += 1
        self.goals_for += goals_for
        self.goals_against += goals_against
        self.recent_for.append(goals_for)
        self.recent_against.append(goals_against)
        if len(self.recent_for) > window:
            self.recent_for.pop(0)
            self.recent_against.pop(0)


class BacktestAgent:
    def __init__(
        self,
        data_dir: Path | str = DEFAULT_DATA_DIR,
        max_goals: int = 7,
        min_prior_matches: int = 3,
        recent_window: int = 10,
        elo_k: float = 30.0,
    ):
        self.data_dir = Path(data_dir)
        self.max_goals = max_goals
        self.min_prior_matches = min_prior_matches
        self.recent_window = recent_window
        self.elo_k = elo_k
        self.states: defaultdict[str, TeamBacktestState] = defaultdict(TeamBacktestState)
        self.total_goals = 0
        self.team_games = 0

    def run(self, start_year: int | None = 1954, end_year: int | None = None) -> dict:
        rows = self._historical_rows()
        evaluated = 0
        skipped = 0
        brier_sum = 0.0
        log_loss_sum = 0.0
        rps_sum = 0.0
        calibration = defaultdict(lambda: {"count": 0, "confidence_sum": 0.0, "correct": 0})

        for row in rows:
            year = int(row["date"][:4])
            home = normalize_team(row["home_team"])
            away = normalize_team(row["away_team"])
            hg = int(row["home_score"])
            ag = int(row["away_score"])
            if start_year is not None and year < start_year:
                self._update_after_match(home, away, hg, ag)
                continue
            if end_year is not None and year > end_year:
                self._update_after_match(home, away, hg, ag)
                continue
            if self.states[home].matches < self.min_prior_matches or self.states[away].matches < self.min_prior_matches:
                skipped += 1
                self._update_after_match(home, away, hg, ag)
                continue

            probs = self._predict_wdl(home, away)
            actual = self._actual_vector(hg, ag)
            brier_sum += sum((p - y) ** 2 for p, y in zip(probs, actual))
            actual_prob = sum(p * y for p, y in zip(probs, actual))
            log_loss_sum += -math.log(max(actual_prob, 1e-12))
            rps_sum += self._rps(probs, actual)
            self._add_calibration(calibration, probs, actual)
            evaluated += 1
            self._update_after_match(home, away, hg, ag)

        if evaluated == 0:
            raise ValueError("No historical matches were eligible for backtest")
        return {
            "config": {
                "data": str(self.data_dir / "international_results_worldcup_only.csv"),
                "start_year": start_year,
                "end_year": end_year,
                "min_prior_matches": self.min_prior_matches,
                "recent_window": self.recent_window,
                "elo_k": self.elo_k,
                "max_goals": self.max_goals,
                "time_safe": True,
            },
            "matches_evaluated": evaluated,
            "matches_skipped_insufficient_history": skipped,
            "brier_score": round(brier_sum / evaluated, 6),
            "log_loss": round(log_loss_sum / evaluated, 6),
            "ranked_probability_score": round(rps_sum / evaluated, 6),
            "calibration": self._format_calibration(calibration),
            "warnings": [
                "This backtest uses rolling World Cup-only Elo and scoring history; it does not validate lineup features unless historical pre-kickoff lineup files are supplied in a future extension.",
                "Use log_loss, Brier score, RPS, and calibration buckets to decide whether a lineup multiplier improves out-of-sample predictions.",
            ],
        }

    def _historical_rows(self) -> list[dict[str, str]]:
        rows = read_csv(self.data_dir / "international_results_worldcup_only.csv")
        clean_rows = []
        for row in rows:
            if not row.get("date") or row.get("home_score") == "" or row.get("away_score") == "":
                continue
            try:
                int(row["home_score"])
                int(row["away_score"])
            except ValueError:
                continue
            clean_rows.append(row)
        return sorted(clean_rows, key=lambda item: (item["date"], item["home_team"], item["away_team"]))

    def _global_goal_average(self) -> float:
        return self.total_goals / self.team_games if self.team_games else 1.35

    def _predict_wdl(self, home: str, away: str) -> tuple[float, float, float]:
        base = self._global_goal_average()
        h = self.states[home]
        a = self.states[away]

        def capped(value: float, low: float = 0.45, high: float = 1.9) -> float:
            return max(low, min(high, value))

        h_attack = capped(h.attack_average(base) / base)
        a_attack = capped(a.attack_average(base) / base)
        h_def_vuln = capped(h.defense_average(base) / base)
        a_def_vuln = capped(a.defense_average(base) / base)
        h_elo, a_elo = elo_goal_multipliers(h.elo - a.elo)
        lam_h = max(0.2, min(3.8, base * h_attack * a_def_vuln * h_elo))
        lam_a = max(0.2, min(3.8, base * a_attack * h_def_vuln * a_elo))
        return self._poisson_wdl(lam_h, lam_a)

    def _poisson_wdl(self, lam_h: float, lam_a: float) -> tuple[float, float, float]:
        matrix = []
        total = 0.0
        for h_goals in range(self.max_goals + 1):
            row = []
            for a_goals in range(self.max_goals + 1):
                p = ScorelineAgent.poisson_pmf(h_goals, lam_h) * ScorelineAgent.poisson_pmf(a_goals, lam_a)
                row.append(p)
                total += p
            matrix.append(row)
        p_home = p_draw = p_away = 0.0
        for h_goals, row in enumerate(matrix):
            for a_goals, p in enumerate(row):
                p /= total
                if h_goals > a_goals:
                    p_home += p
                elif h_goals == a_goals:
                    p_draw += p
                else:
                    p_away += p
        return p_home, p_draw, p_away

    @staticmethod
    def _actual_vector(hg: int, ag: int) -> tuple[int, int, int]:
        if hg > ag:
            return 1, 0, 0
        if hg == ag:
            return 0, 1, 0
        return 0, 0, 1

    @staticmethod
    def _rps(probs: tuple[float, float, float], actual: tuple[int, int, int]) -> float:
        pred_cum = 0.0
        actual_cum = 0.0
        total = 0.0
        for p, y in zip(probs[:-1], actual[:-1]):
            pred_cum += p
            actual_cum += y
            total += (pred_cum - actual_cum) ** 2
        return total / 2.0

    @staticmethod
    def _add_calibration(calibration, probs: tuple[float, float, float], actual: tuple[int, int, int]) -> None:
        confidence = max(probs)
        predicted_idx = probs.index(confidence)
        actual_idx = actual.index(1)
        bucket = min(9, int(confidence * 10))
        label = f"{bucket / 10:.1f}-{(bucket + 1) / 10:.1f}"
        calibration[label]["count"] += 1
        calibration[label]["confidence_sum"] += confidence
        calibration[label]["correct"] += int(predicted_idx == actual_idx)

    @staticmethod
    def _format_calibration(calibration) -> list[dict]:
        rows = []
        for bucket in sorted(calibration):
            item = calibration[bucket]
            count = item["count"]
            rows.append(
                {
                    "bucket": bucket,
                    "count": count,
                    "avg_confidence": round(item["confidence_sum"] / count, 6),
                    "accuracy": round(item["correct"] / count, 6),
                }
            )
        return rows

    def _update_after_match(self, home: str, away: str, hg: int, ag: int) -> None:
        h = self.states[home]
        a = self.states[away]
        expected_h = elo_win_probability(h.elo - a.elo)
        actual_h = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
        h.elo += self.elo_k * (actual_h - expected_h)
        a.elo += self.elo_k * ((1.0 - actual_h) - (1.0 - expected_h))
        h.update_goals(hg, ag, self.recent_window)
        a.update_goals(ag, hg, self.recent_window)
        self.total_goals += hg + ag
        self.team_games += 2


def run_backtest(
    data_dir: Path | str = DEFAULT_DATA_DIR,
    start_year: int | None = 1954,
    end_year: int | None = None,
    min_prior_matches: int = 3,
) -> dict:
    return BacktestAgent(data_dir=data_dir, min_prior_matches=min_prior_matches).run(
        start_year=start_year,
        end_year=end_year,
    )


def write_backtest_report(result: dict, output_path: Path | str | None = None) -> Path:
    path = Path(output_path) if output_path else OUTPUT_DIR / "reports" / "backtest_metrics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
