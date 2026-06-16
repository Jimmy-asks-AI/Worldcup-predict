from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from .aliases import normalize_team
from .models import ActualResult, Fixture


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "worldcup_data_audit" / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"


def normalize_fixture_side(value: str) -> str:
    text = value or ""
    if text.startswith(("Group ", "Winner Match ", "Loser Match ")):
        return text
    return normalize_team(text)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


class DataAgent:
    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self._fixtures: list[Fixture] | None = None
        self._teams: dict[str, str] | None = None
        self._actual_results: dict[str, ActualResult] | None = None

    def require_files(self) -> None:
        required = [
            "fixtures_2026.csv",
            "teams_2026.csv",
            "worldcup26_games.csv",
            "derived_elo_snapshot.csv",
            "derived_recent_form.csv",
            "international_results_worldcup_only.csv",
        ]
        missing = [name for name in required if not (self.data_dir / name).exists()]
        if missing:
            raise FileNotFoundError(f"Missing processed data files: {', '.join(missing)}")

    def fixtures(self) -> list[Fixture]:
        if self._fixtures is None:
            self.require_files()
            rows = read_csv(self.data_dir / "fixtures_2026.csv")
            fixtures = [
                Fixture(
                    match_id=row["match_id"],
                    stage=row["stage"],
                    group=row.get("group", ""),
                    home_team=normalize_fixture_side(row.get("home_team", "")),
                    away_team=normalize_fixture_side(row.get("away_team", "")),
                    kickoff_utc=row.get("kickoff_utc", ""),
                    stadium=row.get("stadium", ""),
                )
                for row in rows
            ]
            if len(fixtures) != 104:
                raise ValueError(f"Expected 104 fixtures, found {len(fixtures)}")
            self._fixtures = fixtures
        return self._fixtures

    def group_fixtures(self) -> list[Fixture]:
        return [f for f in self.fixtures() if f.stage == "group-stage"]

    def knockout_fixtures(self) -> list[Fixture]:
        return [f for f in self.fixtures() if f.stage != "group-stage"]

    def teams_by_group(self) -> dict[str, list[str]]:
        groups: dict[str, set[str]] = {}
        for fixture in self.group_fixtures():
            groups.setdefault(fixture.group, set()).update([fixture.home_team, fixture.away_team])
        out = {group: sorted(teams) for group, teams in groups.items()}
        if len(out) != 12 or any(len(teams) != 4 for teams in out.values()):
            raise ValueError("Expected 12 groups of 4 teams from fixtures_2026.csv")
        return dict(sorted(out.items()))

    def teams(self) -> dict[str, str]:
        if self._teams is None:
            rows = read_csv(self.data_dir / "teams_2026.csv")
            teams = {normalize_team(row["team_name"]): row.get("fifa_code", "") for row in rows}
            if len(teams) != 48:
                raise ValueError(f"Expected 48 teams, found {len(teams)}")
            self._teams = teams
        return self._teams

    def actual_results(self) -> dict[str, ActualResult]:
        if self._actual_results is None:
            rows = read_csv(self.data_dir / "worldcup26_games.csv")
            actuals: dict[str, ActualResult] = {}
            for row in rows:
                if row.get("finished") != "TRUE":
                    continue
                home_score = row.get("actual_home_score", "")
                away_score = row.get("actual_away_score", "")
                if home_score == "" or away_score == "":
                    continue
                actuals[row["match_id"]] = ActualResult(
                    match_id=row["match_id"],
                    home_team=normalize_team(row.get("home_team", "")),
                    away_team=normalize_team(row.get("away_team", "")),
                    home_score=int(home_score),
                    away_score=int(away_score),
                )
            self._actual_results = actuals
        return self._actual_results


def refresh_data() -> int:
    script = ROOT / "worldcup_data_audit" / "scripts" / "pull_and_audit_worldcup_data.py"
    if not script.exists():
        raise FileNotFoundError(f"Data audit script not found: {script}")
    return subprocess.call([sys.executable, str(script)], cwd=str(ROOT))
