from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_FILES = {
    "package": [
        "worldcup_predictor/cli.py",
        "worldcup_predictor/data.py",
        "worldcup_predictor/strength.py",
        "worldcup_predictor/scoreline.py",
        "worldcup_predictor/tournament.py",
        "worldcup_predictor/report.py",
    ],
    "processed": [
        "worldcup_data_audit/data/processed/fixtures_2026.csv",
        "worldcup_data_audit/data/processed/teams_2026.csv",
        "worldcup_data_audit/data/processed/worldcup26_games.csv",
        "worldcup_data_audit/data/processed/derived_elo_snapshot.csv",
        "worldcup_data_audit/data/processed/derived_recent_form.csv",
        "worldcup_data_audit/data/processed/international_results_worldcup_only.csv",
        "worldcup_data_audit/data/processed/fifa_ranking_snapshot.csv",
        "worldcup_data_audit/data/processed/statsbomb_event_half_team_summary.csv",
    ],
    "optional_context": [
        "inputs/player_ratings/eafc26_player_ratings.csv",
        "inputs/player_performance/player_match_performance.csv",
        "inputs/match_context/weather_forecast.csv",
        "inputs/match_context/team_travel_fatigue.csv",
        "inputs/match_context/tactics.csv",
        "inputs/match_context/referees.csv",
        "inputs/lineups/template.csv",
    ],
}

COUNT_EXPECTATIONS = {
    "worldcup_data_audit/data/processed/fixtures_2026.csv": ("eq", 104),
    "worldcup_data_audit/data/processed/teams_2026.csv": ("eq", 48),
    "worldcup_data_audit/data/processed/international_results_worldcup_only.csv": ("min", 900),
    "worldcup_data_audit/data/processed/fifa_ranking_snapshot.csv": ("min", 48),
    "worldcup_data_audit/data/processed/statsbomb_event_half_team_summary.csv": ("min", 1),
    "inputs/player_ratings/eafc26_player_ratings.csv": ("min", 1000),
    "inputs/player_performance/player_match_performance.csv": ("min", 1),
    "inputs/match_context/weather_forecast.csv": ("min", 1),
    "inputs/match_context/team_travel_fatigue.csv": ("min", 1),
    "inputs/match_context/tactics.csv": ("min", 1),
    "inputs/match_context/referees.csv": ("min", 1),
}


def count_csv(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as fh:
        return sum(1 for _ in csv.DictReader(fh))


def check_count(count: int | None, rule: tuple[str, int]) -> bool:
    if count is None:
        return False
    op, expected = rule
    if op == "eq":
        return count == expected
    if op == "min":
        return count >= expected
    raise ValueError(f"Unknown rule: {op}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Health check for the local worldcup_predictor model")
    parser.add_argument("--root", default=".", help="Repository root containing worldcup_predictor/")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result: dict[str, object] = {
        "root": str(root),
        "status": "ok",
        "missing": {},
        "counts": {},
        "warnings": [],
    }

    missing_any = False
    for group, rel_paths in REQUIRED_FILES.items():
        missing = [rel for rel in rel_paths if not (root / rel).exists()]
        if missing:
            result["missing"][group] = missing
            missing_any = True

    counts = {}
    for rel, rule in COUNT_EXPECTATIONS.items():
        count = count_csv(root / rel)
        counts[rel] = {
            "rows": count,
            "expectation": f"{rule[0]} {rule[1]}",
            "ok": check_count(count, rule),
        }
    result["counts"] = counts

    failed_counts = [rel for rel, item in counts.items() if not item["ok"]]
    if failed_counts:
        result["warnings"].append({"count_check_failed": failed_counts})

    lineup_template = root / "inputs/lineups/template.csv"
    if lineup_template.exists() and count_csv(lineup_template) == 0:
        result["warnings"].append("lineup template exists but does not contain real official starters")

    if missing_any:
        result["status"] = "missing_files"
    elif failed_counts:
        result["status"] = "warning"

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"ok", "warning"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
