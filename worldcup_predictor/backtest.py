from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .aliases import normalize_team
from .data import DEFAULT_DATA_DIR, OUTPUT_DIR, read_csv
from .score_models import aggregate_wdl, scoreline_matrix, sorted_scorelines, validate_score_model
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
        score_model: str = "independent_poisson",
        dixon_coles_rho: float = -0.08,
    ):
        self.data_dir = Path(data_dir)
        self.max_goals = max_goals
        self.min_prior_matches = min_prior_matches
        self.recent_window = recent_window
        self.elo_k = elo_k
        self.score_model = validate_score_model(score_model)
        self.dixon_coles_rho = dixon_coles_rho
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
        outcome_correct = 0
        exact_score_correct = 0
        top3_scoreline_correct = 0
        home_goal_abs_error = 0.0
        away_goal_abs_error = 0.0
        total_goal_abs_error = 0.0
        home_goal_sq_error = 0.0
        away_goal_sq_error = 0.0
        total_goal_sq_error = 0.0
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

            prediction = self._predict_distribution(home, away)
            probs = prediction["wdl"]
            actual = self._actual_vector(hg, ag)
            brier_sum += sum((p - y) ** 2 for p, y in zip(probs, actual))
            actual_prob = sum(p * y for p, y in zip(probs, actual))
            log_loss_sum += -math.log(max(actual_prob, 1e-12))
            rps_sum += self._rps(probs, actual)
            predicted_idx = probs.index(max(probs))
            actual_idx = actual.index(1)
            outcome_correct += int(predicted_idx == actual_idx)
            top_scorelines = prediction["top_scorelines"]
            exact_score = f"{hg}-{ag}"
            exact_score_correct += int(top_scorelines[0]["scoreline"] == exact_score)
            top3_scoreline_correct += int(exact_score in {row["scoreline"] for row in top_scorelines[:3]})
            lam_h = prediction["lambda_home"]
            lam_a = prediction["lambda_away"]
            total_pred = lam_h + lam_a
            total_actual = hg + ag
            home_goal_abs_error += abs(lam_h - hg)
            away_goal_abs_error += abs(lam_a - ag)
            total_goal_abs_error += abs(total_pred - total_actual)
            home_goal_sq_error += (lam_h - hg) ** 2
            away_goal_sq_error += (lam_a - ag) ** 2
            total_goal_sq_error += (total_pred - total_actual) ** 2
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
                "score_model": self.score_model,
                "dixon_coles_rho": self.dixon_coles_rho if self.score_model == "dixon_coles" else None,
                "time_safe": True,
            },
            "matches_evaluated": evaluated,
            "matches_skipped_insufficient_history": skipped,
            "brier_score": round(brier_sum / evaluated, 6),
            "log_loss": round(log_loss_sum / evaluated, 6),
            "ranked_probability_score": round(rps_sum / evaluated, 6),
            "outcome_accuracy": round(outcome_correct / evaluated, 6),
            "exact_score_accuracy": round(exact_score_correct / evaluated, 6),
            "top3_scoreline_accuracy": round(top3_scoreline_correct / evaluated, 6),
            "home_goal_mae": round(home_goal_abs_error / evaluated, 6),
            "away_goal_mae": round(away_goal_abs_error / evaluated, 6),
            "total_goal_mae": round(total_goal_abs_error / evaluated, 6),
            "combined_goal_mae": round((home_goal_abs_error + away_goal_abs_error) / (evaluated * 2), 6),
            "home_goal_rmse": round(math.sqrt(home_goal_sq_error / evaluated), 6),
            "away_goal_rmse": round(math.sqrt(away_goal_sq_error / evaluated), 6),
            "total_goal_rmse": round(math.sqrt(total_goal_sq_error / evaluated), 6),
            "combined_goal_rmse": round(math.sqrt((home_goal_sq_error + away_goal_sq_error) / (evaluated * 2)), 6),
            "calibration": self._format_calibration(calibration),
            "warnings": [
                "This backtest uses rolling World Cup-only Elo and scoring history; it does not validate lineup features unless historical pre-kickoff lineup files are supplied in a future extension.",
                "Use log_loss, Brier score, RPS, calibration buckets, exact score accuracy, and goal MAE/RMSE to decide whether a model change improves out-of-sample predictions.",
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
        return self._predict_distribution(home, away)["wdl"]

    def _predict_distribution(self, home: str, away: str) -> dict:
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
        matrix = scoreline_matrix(
            lam_h,
            lam_a,
            max_goals=self.max_goals,
            score_model=self.score_model,
            dixon_coles_rho=self.dixon_coles_rho,
        )
        return {
            "lambda_home": lam_h,
            "lambda_away": lam_a,
            "wdl": aggregate_wdl(matrix),
            "top_scorelines": sorted_scorelines(matrix),
        }

    def _poisson_wdl(self, lam_h: float, lam_a: float) -> tuple[float, float, float]:
        matrix = scoreline_matrix(
            lam_h,
            lam_a,
            max_goals=self.max_goals,
            score_model=self.score_model,
            dixon_coles_rho=self.dixon_coles_rho,
        )
        return aggregate_wdl(matrix)

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
    score_model: str = "independent_poisson",
    dixon_coles_rho: float = -0.08,
) -> dict:
    return BacktestAgent(
        data_dir=data_dir,
        min_prior_matches=min_prior_matches,
        score_model=score_model,
        dixon_coles_rho=dixon_coles_rho,
    ).run(
        start_year=start_year,
        end_year=end_year,
    )


def tune_dixon_coles_rho(
    data_dir: Path | str = DEFAULT_DATA_DIR,
    start_year: int | None = 2018,
    end_year: int | None = None,
    min_prior_matches: int = 3,
    rho_values: list[float] | None = None,
) -> dict:
    candidates = rho_values or [-0.16, -0.12, -0.08, -0.04, 0.0, 0.04]
    baseline = run_backtest(
        data_dir=data_dir,
        start_year=start_year,
        end_year=end_year,
        min_prior_matches=min_prior_matches,
        score_model="independent_poisson",
    )
    rows = [_tuning_row("independent_poisson", None, baseline)]
    for rho in candidates:
        result = run_backtest(
            data_dir=data_dir,
            start_year=start_year,
            end_year=end_year,
            min_prior_matches=min_prior_matches,
            score_model="dixon_coles",
            dixon_coles_rho=rho,
        )
        rows.append(_tuning_row("dixon_coles", rho, result))
    best_by_log_loss = min(rows, key=lambda item: item["log_loss"])
    best_by_rps = min(rows, key=lambda item: item["ranked_probability_score"])
    best_dc = min((row for row in rows if row["score_model"] == "dixon_coles"), key=lambda item: item["log_loss"])
    deltas = {
        "best_dixon_coles_log_loss_minus_independent": round(best_dc["log_loss"] - rows[0]["log_loss"], 6),
        "best_dixon_coles_brier_minus_independent": round(best_dc["brier_score"] - rows[0]["brier_score"], 6),
        "best_dixon_coles_rps_minus_independent": round(
            best_dc["ranked_probability_score"] - rows[0]["ranked_probability_score"],
            6,
        ),
        "best_dixon_coles_top3_scoreline_accuracy_minus_independent": round(
            best_dc["top3_scoreline_accuracy"] - rows[0]["top3_scoreline_accuracy"],
            6,
        ),
    }
    material_thresholds = {
        "best_dixon_coles_log_loss_minus_independent": -0.005,
        "best_dixon_coles_brier_minus_independent": -0.002,
        "best_dixon_coles_rps_minus_independent": -0.001,
    }
    improved_count = sum(1 for key, threshold in material_thresholds.items() if deltas[key] <= threshold)
    recommended = best_by_log_loss["score_model"] == "dixon_coles" and improved_count >= 2
    return {
        "purpose": "alan_turing_institute_inspired_dixon_coles_rho_tuning",
        "source_project": "https://github.com/alan-turing-institute/WorldCupPrediction",
        "config": {
            "data": str(Path(data_dir) / "international_results_worldcup_only.csv"),
            "start_year": start_year,
            "end_year": end_year,
            "min_prior_matches": min_prior_matches,
            "rho_values": candidates,
            "time_safe": True,
            "default_changes_prediction": False,
        },
        "results": rows,
        "best_by_log_loss": best_by_log_loss,
        "best_by_ranked_probability_score": best_by_rps,
        "deltas_vs_independent": deltas,
        "gate": {
            "material_improvement_thresholds": material_thresholds,
            "improved_probability_loss_metric_count": improved_count,
            "default_enable_recommended": recommended,
            "reason": (
                "A Dixon-Coles rho candidate materially beat independent Poisson on log-loss and at least two probability-loss metrics."
                if recommended
                else "Keep independent Poisson as default unless a Dixon-Coles rho materially beats it on log-loss and at least two probability-loss metrics."
            ),
        },
        "warnings": [
            "This tunes only the low-score Dixon-Coles correlation parameter; it does not add team, lineup, or context data.",
            "Do not change the default score model from this report alone unless the gate recommends it and downstream reports remain coherent.",
        ],
    }


def _tuning_row(score_model: str, rho: float | None, result: dict) -> dict:
    return {
        "score_model": score_model,
        "dixon_coles_rho": rho,
        "matches_evaluated": result["matches_evaluated"],
        "log_loss": result["log_loss"],
        "brier_score": result["brier_score"],
        "ranked_probability_score": result["ranked_probability_score"],
        "outcome_accuracy": result["outcome_accuracy"],
        "exact_score_accuracy": result["exact_score_accuracy"],
        "top3_scoreline_accuracy": result["top3_scoreline_accuracy"],
        "combined_goal_mae": result["combined_goal_mae"],
        "combined_goal_rmse": result["combined_goal_rmse"],
    }


def write_dixon_coles_tuning_report(result: dict, output_path: Path | str | None = None) -> Path:
    path = Path(output_path) if output_path else OUTPUT_DIR / "reports" / "dixon_coles_rho_tuning.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_backtest_report(result: dict, output_path: Path | str | None = None) -> Path:
    path = Path(output_path) if output_path else OUTPUT_DIR / "reports" / "backtest_metrics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
