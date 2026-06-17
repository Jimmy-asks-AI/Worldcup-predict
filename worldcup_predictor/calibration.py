from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable

from .aliases import normalize_team
from .backtest import BacktestAgent
from .data import DEFAULT_DATA_DIR, OUTPUT_DIR


ProbabilityTransform = Callable[[tuple[float, float, float]], tuple[float, float, float]]


def temperature_draw_calibrate(
    probs: tuple[float, float, float],
    temperature: float,
    draw_multiplier: float,
) -> tuple[float, float, float]:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    exponent = 1.0 / temperature
    weights = [math.pow(max(prob, 1e-12), exponent) for prob in probs]
    weights[1] *= draw_multiplier
    total = sum(weights)
    return tuple(weight / total for weight in weights)  # type: ignore[return-value]


class CalibrationAgent:
    """Evaluate an optional W/D/L calibration layer without changing the score model."""

    def __init__(
        self,
        data_dir: Path | str = DEFAULT_DATA_DIR,
        min_prior_matches: int = 3,
        score_model: str = "independent_poisson",
        dixon_coles_rho: float = -0.08,
    ):
        self.data_dir = Path(data_dir)
        self.min_prior_matches = min_prior_matches
        self.score_model = score_model
        self.dixon_coles_rho = dixon_coles_rho

    def run(
        self,
        start_year: int = 2018,
        end_year: int | None = None,
        min_training_matches: int = 50,
    ) -> dict:
        records = self._prediction_records(end_year=end_year)
        train = [row for row in records if row["year"] < start_year]
        evaluation = [row for row in records if row["year"] >= start_year]
        if len(train) < min_training_matches:
            raise ValueError(
                f"Only {len(train)} training matches before {start_year}; "
                f"need at least {min_training_matches}"
            )
        if not evaluation:
            raise ValueError(f"No evaluation matches at or after {start_year}")

        best = self._fit_temperature_draw(train)
        transform = lambda probs: temperature_draw_calibrate(
            probs,
            temperature=best["temperature"],
            draw_multiplier=best["draw_multiplier"],
        )
        train_base = self._metrics(train)
        train_calibrated = self._metrics(train, transform)
        eval_base = self._metrics(evaluation)
        eval_calibrated = self._metrics(evaluation, transform)
        deltas = {
            "log_loss_calibrated_minus_uncalibrated": round(
                eval_calibrated["log_loss"] - eval_base["log_loss"], 6
            ),
            "brier_calibrated_minus_uncalibrated": round(
                eval_calibrated["brier_score"] - eval_base["brier_score"], 6
            ),
            "rps_calibrated_minus_uncalibrated": round(
                eval_calibrated["ranked_probability_score"] - eval_base["ranked_probability_score"], 6
            ),
            "ece_calibrated_minus_uncalibrated": round(
                eval_calibrated["expected_calibration_error"] - eval_base["expected_calibration_error"], 6
            ),
        }
        improved_count = sum(
            1
            for key in [
                "log_loss_calibrated_minus_uncalibrated",
                "brier_calibrated_minus_uncalibrated",
                "rps_calibrated_minus_uncalibrated",
            ]
            if deltas[key] < -0.0001
        )
        calibration_not_worse = deltas["ece_calibrated_minus_uncalibrated"] <= 0.01
        recommended = improved_count >= 2 and calibration_not_worse
        reason = (
            "Calibration improved at least two probability-loss metrics without materially worsening ECE."
            if recommended
            else "Keep calibration disabled by default until it improves at least two probability-loss metrics without materially worsening ECE."
        )
        return {
            "purpose": "rivu_intel45_inspired_wdl_calibration_gate",
            "source_project": "https://github.com/rivu-intel45/FIFA-2026-Winner-Prediction",
            "config": {
                "data": str(self.data_dir / "international_results_worldcup_only.csv"),
                "start_year": start_year,
                "end_year": end_year,
                "min_prior_matches": self.min_prior_matches,
                "min_training_matches": min_training_matches,
                "score_model": self.score_model,
                "dixon_coles_rho": self.dixon_coles_rho if self.score_model == "dixon_coles" else None,
                "time_safe": True,
                "default_changes_prediction": False,
            },
            "training_matches": len(train),
            "evaluation_matches": len(evaluation),
            "calibration_model": {
                "type": "temperature_plus_draw_multiplier_grid_search",
                "temperature": best["temperature"],
                "draw_multiplier": best["draw_multiplier"],
                "selection_metric": "training_log_loss",
                "status": "optional_gate_only",
            },
            "training": {
                "uncalibrated": train_base,
                "temperature_calibrated": train_calibrated,
            },
            "evaluation": {
                "uncalibrated": eval_base,
                "temperature_calibrated": eval_calibrated,
            },
            "deltas": deltas,
            "gate": {
                "improved_probability_loss_metric_count": improved_count,
                "calibration_not_materially_worse": calibration_not_worse,
                "default_enable_recommended": recommended,
                "reason": reason,
            },
            "warnings": [
                "This is a lightweight probability calibration gate, not an XGBoost replacement for the scoreline model.",
                "It does not change exact score, total goals, event-count, lineup, or tournament sampling outputs.",
                "Promote a calibration layer only after time-safe validation improves probability quality and preserves calibration.",
            ],
        }

    def _prediction_records(self, end_year: int | None = None) -> list[dict]:
        agent = BacktestAgent(
            data_dir=self.data_dir,
            min_prior_matches=self.min_prior_matches,
            score_model=self.score_model,
            dixon_coles_rho=self.dixon_coles_rho,
        )
        records = []
        for row in agent._historical_rows():
            year = int(row["date"][:4])
            if end_year is not None and year > end_year:
                break
            home = normalize_team(row["home_team"])
            away = normalize_team(row["away_team"])
            hg = int(row["home_score"])
            ag = int(row["away_score"])
            if agent.states[home].matches < self.min_prior_matches or agent.states[away].matches < self.min_prior_matches:
                agent._update_after_match(home, away, hg, ag)
                continue
            prediction = agent._predict_distribution(home, away)
            actual = agent._actual_vector(hg, ag)
            records.append(
                {
                    "date": row["date"],
                    "year": year,
                    "home_team": home,
                    "away_team": away,
                    "home_score": hg,
                    "away_score": ag,
                    "probs": prediction["wdl"],
                    "actual": actual,
                }
            )
            agent._update_after_match(home, away, hg, ag)
        return records

    def _fit_temperature_draw(self, records: list[dict]) -> dict[str, float]:
        best = {"temperature": 1.0, "draw_multiplier": 1.0, "log_loss": self._metrics(records)["log_loss"]}
        temperatures = [round(0.70 + idx * 0.05, 2) for idx in range(23)]
        draw_multipliers = [round(0.80 + idx * 0.05, 2) for idx in range(9)]
        for temperature in temperatures:
            for draw_multiplier in draw_multipliers:
                transform = lambda probs, t=temperature, d=draw_multiplier: temperature_draw_calibrate(
                    probs,
                    temperature=t,
                    draw_multiplier=d,
                )
                metrics = self._metrics(records, transform)
                if metrics["log_loss"] < best["log_loss"]:
                    best = {
                        "temperature": temperature,
                        "draw_multiplier": draw_multiplier,
                        "log_loss": metrics["log_loss"],
                    }
        return best

    @staticmethod
    def _metrics(records: list[dict], transform: ProbabilityTransform | None = None) -> dict:
        brier_sum = 0.0
        log_loss_sum = 0.0
        rps_sum = 0.0
        correct = 0
        buckets: dict[str, dict[str, float]] = {}
        for row in records:
            probs = row["probs"]
            if transform:
                probs = transform(probs)
            actual = row["actual"]
            brier_sum += sum((p - y) ** 2 for p, y in zip(probs, actual))
            actual_prob = sum(p * y for p, y in zip(probs, actual))
            log_loss_sum += -math.log(max(actual_prob, 1e-12))
            rps_sum += CalibrationAgent._rps(probs, actual)
            confidence = max(probs)
            predicted_idx = probs.index(confidence)
            actual_idx = actual.index(1)
            correct += int(predicted_idx == actual_idx)
            bucket = min(9, int(confidence * 10))
            label = f"{bucket / 10:.1f}-{(bucket + 1) / 10:.1f}"
            item = buckets.setdefault(label, {"count": 0, "confidence_sum": 0.0, "correct": 0})
            item["count"] += 1
            item["confidence_sum"] += confidence
            item["correct"] += int(predicted_idx == actual_idx)
        count = len(records)
        calibration = []
        ece = 0.0
        for bucket in sorted(buckets):
            item = buckets[bucket]
            bucket_count = int(item["count"])
            avg_confidence = item["confidence_sum"] / bucket_count
            accuracy = item["correct"] / bucket_count
            ece += (bucket_count / count) * abs(accuracy - avg_confidence)
            calibration.append(
                {
                    "bucket": bucket,
                    "count": bucket_count,
                    "avg_confidence": round(avg_confidence, 6),
                    "accuracy": round(accuracy, 6),
                }
            )
        return {
            "log_loss": round(log_loss_sum / count, 6),
            "brier_score": round(brier_sum / count, 6),
            "ranked_probability_score": round(rps_sum / count, 6),
            "outcome_accuracy": round(correct / count, 6),
            "expected_calibration_error": round(ece, 6),
            "calibration": calibration,
        }

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


def run_calibration_backtest(
    data_dir: Path | str = DEFAULT_DATA_DIR,
    start_year: int = 2018,
    end_year: int | None = None,
    min_prior_matches: int = 3,
    min_training_matches: int = 50,
    score_model: str = "independent_poisson",
    dixon_coles_rho: float = -0.08,
) -> dict:
    return CalibrationAgent(
        data_dir=data_dir,
        min_prior_matches=min_prior_matches,
        score_model=score_model,
        dixon_coles_rho=dixon_coles_rho,
    ).run(
        start_year=start_year,
        end_year=end_year,
        min_training_matches=min_training_matches,
    )


def write_calibration_report(result: dict, output_path: Path | str | None = None) -> Path:
    path = Path(output_path) if output_path else OUTPUT_DIR / "reports" / "calibration_backtest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
