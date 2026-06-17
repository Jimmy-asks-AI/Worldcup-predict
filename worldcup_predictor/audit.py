from __future__ import annotations

import csv
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .data import OUTPUT_DIR, ROOT
from .models import MatchPrediction


DEFAULT_AUDIT_LOG = OUTPUT_DIR / "audit" / "prediction_runs.jsonl"


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _file_metadata(path_value: str | Path | None) -> dict[str, Any]:
    if not path_value:
        return {"path": None, "exists": False}
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    metadata: dict[str, Any] = {
        "path": _relative(path),
        "exists": path.exists(),
    }
    if not path.exists() or not path.is_file():
        return metadata
    payload = path.read_bytes()
    metadata.update(
        {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    )
    if path.suffix.lower() == ".csv":
        try:
            text = payload.decode("utf-8-sig")
            metadata["rows"] = sum(1 for _ in csv.DictReader(text.splitlines()))
        except UnicodeDecodeError:
            metadata["rows"] = None
    return metadata


class PredictionAuditAgent:
    def __init__(self, output_path: str | Path = DEFAULT_AUDIT_LOG):
        self.output_path = Path(output_path)

    def append_match_prediction(
        self,
        prediction: MatchPrediction,
        command: str,
        cli_args: Any,
        run_type: str = "predict_match",
    ) -> Path:
        entry = self._entry(prediction, command, cli_args, run_type)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        return self.output_path

    def _entry(self, prediction: MatchPrediction, command: str, cli_args: Any, run_type: str) -> dict[str, Any]:
        args = vars(cli_args) if hasattr(cli_args, "__dict__") else {}
        data_files = {
            "fixtures": _file_metadata("worldcup_data_audit/data/processed/fixtures_2026.csv"),
            "teams": _file_metadata("worldcup_data_audit/data/processed/teams_2026.csv"),
            "worldcup_games": _file_metadata("worldcup_data_audit/data/processed/worldcup26_games.csv"),
            "elo": _file_metadata("worldcup_data_audit/data/processed/derived_elo_snapshot.csv"),
            "recent_form": _file_metadata("worldcup_data_audit/data/processed/derived_recent_form.csv"),
            "worldcup_history": _file_metadata("worldcup_data_audit/data/processed/international_results_worldcup_only.csv"),
            "fifa_ranking": _file_metadata("worldcup_data_audit/data/processed/fifa_ranking_snapshot.csv"),
            "event_half_sample": _file_metadata("worldcup_data_audit/data/processed/statsbomb_event_half_team_summary.csv"),
            "lineup_file": _file_metadata(args.get("lineup_file")),
            "player_ratings_file": _file_metadata(args.get("player_ratings_file")),
            "player_performance_file": _file_metadata(args.get("player_performance_file")),
            "weather_file": _file_metadata(args.get("weather_file")),
            "travel_file": _file_metadata(args.get("travel_file")),
            "tactics_file": _file_metadata(args.get("tactics_file")),
            "referee_file": _file_metadata(args.get("referee_file")),
        }
        return {
            "audit_version": 1,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "source_inspiration": "pravindurgani/wc26-matchday-intelligence append-only audit log",
            "run_type": run_type,
            "command": command,
            "argv": sys.argv[1:],
            "pre_match_safe_boundary": {
                "uses_finished_scores_only_when_marked_finished": True,
                "uses_real_betting_odds": False,
                "lineup_requires_trusted_source": bool(args.get("lineup_file")),
                "live_or_post_match_data_allowed": False,
            },
            "cli_options": {
                "match_id": args.get("match_id", ""),
                "use_generated_context": bool(args.get("use_generated_context", False)),
                "lineup_allowed_source": args.get("lineup_allowed_source"),
                "allow_projected_lineups": bool(args.get("allow_projected_lineups", False)),
                "score_model": args.get("score_model", prediction.score_model),
                "dixon_coles_rho": args.get("dixon_coles_rho"),
                "include_uncertainty": bool(args.get("include_uncertainty", False)),
                "uncertainty_samples": args.get("uncertainty_samples"),
            },
            "data_files": data_files,
            "prediction": {
                "match_id": prediction.match_id,
                "home_team": prediction.home_team,
                "away_team": prediction.away_team,
                "lambda_home": prediction.lambda_home,
                "lambda_away": prediction.lambda_away,
                "p_home_win": prediction.p_home_win,
                "p_draw": prediction.p_draw,
                "p_away_win": prediction.p_away_win,
                "expected_goals": prediction.expected_goals,
                "top_scorelines": prediction.top_scorelines[:5],
                "score_model": prediction.score_model,
                "score_model_parameters": prediction.score_model_parameters,
                "uncertainty": prediction.uncertainty,
                "warnings": prediction.warnings,
            },
            "explanation_summary": {
                "headline": prediction.explanation.get("headline") if prediction.explanation else "",
                "data_quality": (
                    prediction.explanation.get("factors", {}).get("data_quality", {}).get("summary")
                    if prediction.explanation
                    else ""
                ),
            },
        }


def append_prediction_audit(
    prediction: MatchPrediction,
    command: str,
    cli_args: Any,
    run_type: str = "predict_match",
    output_path: str | Path = DEFAULT_AUDIT_LOG,
) -> Path:
    return PredictionAuditAgent(output_path).append_match_prediction(prediction, command, cli_args, run_type)
