from __future__ import annotations

import csv
import json
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


AUDIT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = AUDIT_ROOT.parent
RAW = AUDIT_ROOT / "data" / "raw"
PROCESSED = AUDIT_ROOT / "data" / "processed"
REPORTS = AUDIT_ROOT / "reports"
OUTPUT_REPORTS = WORKSPACE_ROOT / "outputs" / "reports"
PLAYER_INPUTS = WORKSPACE_ROOT / "inputs" / "player_performance"

USER_AGENT = "codex-worldcup-player-performance-audit/1.0"
STATSBOMB_RAW = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

PLAYER_MATCH_FIELDS = [
    "snapshot_date",
    "match_date",
    "source",
    "source_timestamp",
    "player_id",
    "player_name",
    "team",
    "team_type",
    "competition",
    "opponent",
    "home_away_neutral",
    "position",
    "minutes",
    "started",
    "goals",
    "assists",
    "xg",
    "xa",
    "shots",
    "shots_on_target",
    "key_passes",
    "progressive_passes",
    "progressive_carries",
    "touches_box",
    "pressures",
    "tackles",
    "interceptions",
    "blocks",
    "clearances",
    "aerial_duels_won",
    "duels_won",
    "yellow_cards",
    "red_cards",
    "keeper_saves",
    "keeper_goals_prevented",
    "match_rating",
    "rating_basis",
]

PLAYER_MAP_FIELDS = [
    "player_id",
    "player_name",
    "birth_date",
    "national_team",
    "club_team",
    "provider_player_id",
    "provider",
    "valid_from",
    "valid_to",
]

SOURCE_MANIFEST_FIELDS = [
    "source",
    "license",
    "coverage_start",
    "coverage_end",
    "competitions",
    "player_metrics_available",
    "pre_kickoff_safe",
    "notes",
]


@dataclass
class FetchResult:
    name: str
    url: str
    ok: bool
    path: str
    note: str


def ensure_dirs() -> None:
    for path in (RAW, PROCESSED, REPORTS, OUTPUT_REPORTS, PLAYER_INPUTS):
        path.mkdir(parents=True, exist_ok=True)


def request_json(url: str, timeout: int = 40) -> Any:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"})
            with urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - data audit records final failure
            last_exc = exc
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError("request failed without an exception")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def fetch_statsbomb_competitions(fetches: list[FetchResult]) -> list[dict[str, Any]]:
    path = RAW / "statsbomb_competitions.json"
    url = f"{STATSBOMB_RAW}/competitions.json"
    try:
        data = request_json(url)
        write_json(path, data)
        fetches.append(FetchResult("statsbomb_competitions", url, True, str(path), f"{len(data)} competition seasons"))
        return data
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        if path.exists():
            data = load_json(path)
            fetches.append(FetchResult("statsbomb_competitions", url, True, str(path), f"used cached file after {type(exc).__name__}"))
            return data
        fetches.append(FetchResult("statsbomb_competitions", url, False, "", f"{type(exc).__name__}: {exc}"))
        return []


def fetch_statsbomb_matches(competitions: list[dict[str, Any]], fetches: list[FetchResult]) -> dict[int, dict[str, Any]]:
    match_by_id: dict[int, dict[str, Any]] = {}
    for comp in competitions:
        comp_id = comp.get("competition_id")
        season_id = comp.get("season_id")
        if comp_id is None or season_id is None:
            continue
        path = RAW / "statsbomb_matches_all" / f"matches_{comp_id}_{season_id}.json"
        url = f"{STATSBOMB_RAW}/matches/{comp_id}/{season_id}.json"
        try:
            data = request_json(url)
            write_json(path, data)
            fetches.append(FetchResult(f"statsbomb_matches_{comp_id}_{season_id}", url, True, str(path), f"{len(data)} matches"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            if path.exists():
                data = load_json(path)
                fetches.append(FetchResult(f"statsbomb_matches_{comp_id}_{season_id}", url, True, str(path), f"used cached file after {type(exc).__name__}"))
            else:
                fetches.append(FetchResult(f"statsbomb_matches_{comp_id}_{season_id}", url, False, "", f"{type(exc).__name__}: {exc}"))
                continue
        for match in data:
            match_id = match.get("match_id")
            if match_id is not None:
                item = dict(match)
                item["_competition"] = comp
                match_by_id[int(match_id)] = item
    return match_by_id


def fetch_lineups_for_existing_events(fetches: list[FetchResult]) -> None:
    for event_path in sorted(RAW.glob("statsbomb_events_*.json")):
        match_id = event_path.stem.replace("statsbomb_events_", "")
        path = RAW / f"statsbomb_lineups_{match_id}.json"
        if path.exists():
            continue
        url = f"{STATSBOMB_RAW}/lineups/{match_id}.json"
        try:
            data = request_json(url)
            write_json(path, data)
            fetches.append(FetchResult(f"statsbomb_lineups_{match_id}", url, True, str(path), f"{len(data)} teams"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            fetches.append(FetchResult(f"statsbomb_lineups_{match_id}", url, False, "", f"{type(exc).__name__}: {exc}"))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_minute(text: Any, default: float = 0.0) -> float:
    if text in (None, ""):
        return default
    if isinstance(text, (int, float)):
        return float(text)
    pieces = str(text).split(":")
    try:
        minute = float(pieces[0])
        second = float(pieces[1]) if len(pieces) > 1 else 0.0
        return minute + second / 60.0
    except (TypeError, ValueError):
        return default


def build_lineup_context(match_id: str) -> dict[int, dict[str, Any]]:
    path = RAW / f"statsbomb_lineups_{match_id}.json"
    if not path.exists():
        return {}
    context: dict[int, dict[str, Any]] = {}
    lineups = load_json(path)
    for team in lineups:
        team_name = team.get("team_name", "")
        for player in team.get("lineup", []):
            player_id = player.get("player_id")
            if player_id is None:
                continue
            positions = player.get("positions") or []
            minutes = 0.0
            started = False
            position_name = ""
            for pos in positions:
                if not position_name:
                    position_name = pos.get("position", "")
                if pos.get("start_reason") == "Starting XI":
                    started = True
                start = parse_minute(pos.get("from"), 0.0)
                end = parse_minute(pos.get("to"), 90.0 if pos.get("to") is None else start)
                minutes += max(0.0, min(120.0, end) - max(0.0, start))
            context[int(player_id)] = {
                "team": team_name,
                "player_name": player.get("player_name", ""),
                "position": position_name,
                "minutes": round(minutes, 2),
                "started": started,
            }
    return context


def event_player(event: dict[str, Any]) -> tuple[int | None, str]:
    player = event.get("player") or {}
    player_id = player.get("id")
    return (int(player_id), player.get("name", "")) if player_id is not None else (None, "")


def is_touch_in_box(event: dict[str, Any]) -> bool:
    location = event.get("location") or []
    if len(location) < 2:
        return False
    x, y = safe_float(location[0]), safe_float(location[1])
    return x >= 102 and 18 <= y <= 62


def build_player_event_sample(match_by_id: dict[int, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    generated = datetime.now(timezone.utc).date().isoformat()
    performance: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    names: dict[tuple[str, int], str] = {}
    teams: dict[tuple[str, int], str] = {}
    lineups: dict[tuple[str, int], dict[str, Any]] = {}
    identities: dict[int, dict[str, Any]] = {}

    for path in sorted(RAW.glob("statsbomb_events_*.json")):
        match_id = path.stem.replace("statsbomb_events_", "")
        lineup_context = build_lineup_context(match_id)
        events = load_json(path)
        for event in events:
            player_id, player_name = event_player(event)
            if player_id is None:
                continue
            key = (match_id, player_id)
            event_type = (event.get("type") or {}).get("name", "")
            names[key] = player_name
            teams[key] = (event.get("team") or {}).get("name", "")
            if player_id in lineup_context:
                lineups[key] = lineup_context[player_id]
            identities[player_id] = {
                "player_id": player_id,
                "player_name": player_name,
                "birth_date": "",
                "national_team": teams[key],
                "club_team": "",
                "provider_player_id": player_id,
                "provider": "statsbomb_open_data",
                "valid_from": "",
                "valid_to": "",
            }

            if event_type == "Shot":
                performance[key]["shots"] += 1
                shot = event.get("shot") or {}
                outcome = (shot.get("outcome") or {}).get("name", "")
                performance[key]["xg"] += safe_float(shot.get("statsbomb_xg"))
                if outcome == "Goal":
                    performance[key]["goals"] += 1
                    performance[key]["shots_on_target"] += 1
                elif outcome in {"Saved", "Saved to Post"}:
                    performance[key]["shots_on_target"] += 1
            elif event_type == "Pass":
                pass_obj = event.get("pass") or {}
                if pass_obj.get("shot_assist") or pass_obj.get("goal_assist"):
                    performance[key]["key_passes"] += 1
                if pass_obj.get("goal_assist"):
                    performance[key]["assists"] += 1
                start = event.get("location") or []
                end = pass_obj.get("end_location") or []
                if len(start) >= 2 and len(end) >= 2 and safe_float(end[0]) - safe_float(start[0]) >= 20:
                    performance[key]["progressive_passes"] += 1
            elif event_type == "Carry":
                carry = event.get("carry") or {}
                start = event.get("location") or []
                end = carry.get("end_location") or []
                if len(start) >= 2 and len(end) >= 2 and safe_float(end[0]) - safe_float(start[0]) >= 15:
                    performance[key]["progressive_carries"] += 1
            elif event_type == "Pressure":
                performance[key]["pressures"] += 1
            elif event_type == "Interception":
                performance[key]["interceptions"] += 1
            elif event_type == "Block":
                performance[key]["blocks"] += 1
            elif event_type == "Clearance":
                performance[key]["clearances"] += 1
            elif event_type == "Duel":
                duel = event.get("duel") or {}
                duel_type = (duel.get("type") or {}).get("name", "")
                outcome = (duel.get("outcome") or {}).get("name", "")
                if "Tackle" in duel_type:
                    performance[key]["tackles"] += 1
                if "Won" in outcome or "Success" in outcome:
                    performance[key]["duels_won"] += 1
            elif event_type == "Goal Keeper":
                keeper = event.get("goalkeeper") or {}
                keeper_type = (keeper.get("type") or {}).get("name", "")
                if "Saved" in keeper_type:
                    performance[key]["keeper_saves"] += 1
            elif event_type in {"Foul Committed", "Bad Behaviour"}:
                card = ((event.get("foul_committed") or {}).get("card") or (event.get("bad_behaviour") or {}).get("card") or {}).get("name", "")
                if card == "Yellow Card":
                    performance[key]["yellow_cards"] += 1
                elif card in {"Red Card", "Second Yellow"}:
                    performance[key]["red_cards"] += 1

            if is_touch_in_box(event):
                performance[key]["touches_box"] += 1

    rows: list[dict[str, Any]] = []
    for key, counters in sorted(performance.items()):
        match_id, player_id = key
        match = match_by_id.get(int(match_id), {})
        comp = match.get("_competition") or {}
        home_team = (match.get("home_team") or {}).get("home_team_name", "")
        away_team = (match.get("away_team") or {}).get("away_team_name", "")
        team = teams.get(key) or (lineups.get(key) or {}).get("team", "")
        opponent = away_team if team == home_team else home_team if team == away_team else ""
        lineup = lineups.get(key, {})
        row = {
            "snapshot_date": generated,
            "match_date": match.get("match_date", ""),
            "source": "statsbomb_open_data",
            "source_timestamp": generated,
            "player_id": player_id,
            "player_name": names.get(key, ""),
            "team": team,
            "team_type": "national" if (comp.get("competition_international") is True or comp.get("competition_name") in {"FIFA World Cup", "UEFA Euro", "Copa America", "African Cup of Nations"}) else "club",
            "competition": comp.get("competition_name", ""),
            "opponent": opponent,
            "home_away_neutral": "home" if team == home_team else "away" if team == away_team else "neutral",
            "position": lineup.get("position", ""),
            "minutes": lineup.get("minutes", ""),
            "started": "TRUE" if lineup.get("started") else "FALSE",
            "goals": counters["goals"],
            "assists": counters["assists"],
            "xg": round(counters["xg"], 5),
            "xa": "",
            "shots": counters["shots"],
            "shots_on_target": counters["shots_on_target"],
            "key_passes": counters["key_passes"],
            "progressive_passes": counters["progressive_passes"],
            "progressive_carries": counters["progressive_carries"],
            "touches_box": counters["touches_box"],
            "pressures": counters["pressures"],
            "tackles": counters["tackles"],
            "interceptions": counters["interceptions"],
            "blocks": counters["blocks"],
            "clearances": counters["clearances"],
            "aerial_duels_won": "",
            "duels_won": counters["duels_won"],
            "yellow_cards": counters["yellow_cards"],
            "red_cards": counters["red_cards"],
            "keeper_saves": counters["keeper_saves"],
            "keeper_goals_prevented": "",
            "match_rating": "",
            "rating_basis": "historical_event_counts_snapshot",
        }
        rows.append(row)
    return rows, list(identities.values())


def competition_coverage(match_by_id: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    local_event_ids = {int(path.stem.replace("statsbomb_events_", "")) for path in RAW.glob("statsbomb_events_*.json")}
    for match in match_by_id.values():
        comp = match.get("_competition") or {}
        key = (str(comp.get("competition_name", "")), str(comp.get("season_name", "")))
        grouped[key].append(match)
    rows: list[dict[str, Any]] = []
    for (competition, season), matches in sorted(grouped.items()):
        dates = sorted([m.get("match_date", "") for m in matches if m.get("match_date")])
        teams = set()
        local_events = 0
        for match in matches:
            if int(match.get("match_id")) in local_event_ids:
                local_events += 1
            for side in ("home_team", "away_team"):
                team = (match.get(side) or {}).get(f"{side}_name", "")
                if team:
                    teams.add(team)
        comp = matches[0].get("_competition") or {}
        rows.append(
            {
                "source": "statsbomb_open_data",
                "competition": competition,
                "season": season,
                "gender": comp.get("competition_gender", ""),
                "international": comp.get("competition_international", ""),
                "youth": comp.get("competition_youth", ""),
                "matches": len(matches),
                "local_event_files": local_events,
                "teams": len(teams),
                "date_start": dates[0] if dates else "",
                "date_end": dates[-1] if dates else "",
            }
        )
    return rows


def build_source_manifest(coverage_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    statsbomb_dates = [date for row in coverage_rows for date in (row.get("date_start"), row.get("date_end")) if date]
    return [
        {
            "source": "statsbomb_open_data",
            "license": "Public research use with StatsBomb attribution required",
            "coverage_start": min(statsbomb_dates) if statsbomb_dates else "",
            "coverage_end": max(statsbomb_dates) if statsbomb_dates else "",
            "competitions": len(coverage_rows),
            "player_metrics_available": "events, lineups, xG on shots, substitutions, cards; partial club and international coverage",
            "pre_kickoff_safe": "future-only after local snapshot; not sufficient for historical backtest snapshots",
            "notes": "Legally usable for research, but open-data coverage is partial and does not cover all club/national-team matches for 2026 players.",
        },
        {
            "source": "martj42_international_goalscorers",
            "license": "not verified in this audit",
            "coverage_start": "",
            "coverage_end": "",
            "competitions": "international matches only",
            "player_metrics_available": "goal scorer, minute, own-goal flag, penalty flag",
            "pre_kickoff_safe": "future-only after local snapshot",
            "notes": "Useful for scorer history only; not broad player performance.",
        },
        {
            "source": "thestatsapi",
            "license": "commercial/API-key required",
            "coverage_start": "unknown without account",
            "coverage_end": "unknown without account",
            "competitions": "World Cup and football APIs advertised",
            "player_metrics_available": "confirmed lineups, live player stats, xG advertised",
            "pre_kickoff_safe": "potentially yes for live 2026; not locally available",
            "notes": "Requires API key; no historical player-performance pull was possible in this local audit.",
        },
    ]


def write_report(fetches: list[FetchResult], coverage_rows: list[dict[str, Any]], sample_rows: list[dict[str, Any]], identities: list[dict[str, Any]]) -> None:
    statsbomb_total_matches = sum(int(row.get("matches") or 0) for row in coverage_rows)
    statsbomb_local_events = sum(int(row.get("local_event_files") or 0) for row in coverage_rows)
    men_rows = [row for row in coverage_rows if row.get("gender") == "male" and str(row.get("youth")).lower() == "false"]
    local_teams = sorted({row["team"] for row in sample_rows if row.get("team")})
    verdict = "not_sufficient_for_model_gate"

    lines = [
        "# Player Performance Data Audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Verdict",
        "",
        f"`{verdict}`",
        "",
        "The next step was data acquisition and validation, not model integration. The audit found usable public event data, but not the complete, historical, pre-kickoff-safe club and national-team player-performance dataset needed to prove out-of-sample improvement.",
        "",
        "## Local Outputs",
        "",
        f"- Source manifest: `{PLAYER_INPUTS / 'source_manifest.csv'}`",
        f"- Empty contract file: `{PLAYER_INPUTS / 'player_match_performance.csv'}`",
        f"- Empty identity contract: `{PLAYER_INPUTS / 'player_identity_map.csv'}`",
        f"- StatsBomb sample performance rows: `{PROCESSED / 'statsbomb_player_match_performance_sample.csv'}`",
        f"- StatsBomb sample identities: `{PROCESSED / 'statsbomb_player_identity_sample.csv'}`",
        f"- StatsBomb coverage table: `{PROCESSED / 'player_performance_source_coverage.csv'}`",
        "",
        "## Coverage Summary",
        "",
        f"- StatsBomb open-data match metadata rows discovered: {statsbomb_total_matches}",
        f"- Male non-youth competition-season rows discovered: {len(men_rows)}",
        f"- Local StatsBomb event files currently available: {statsbomb_local_events}",
        f"- Player-match sample rows generated from local event files: {len(sample_rows)}",
        f"- Unique player identities in sample: {len(identities)}",
        f"- Teams represented in local sample: {len(local_teams)}",
        "",
        "## Source Findings",
        "",
        "- StatsBomb Open Data is legal for public research with attribution, and it provides JSON competitions, matches, events, and lineups. It is the only source that could be processed locally without credentials.",
        "- The local StatsBomb sample is useful for parser development, but it is not enough to validate a player-performance model across all 2026 World Cup players.",
        "- TheStatsAPI advertises confirmed lineups, substitutions, live player stats, and xG, but the JSON endpoint requires an API key, so it is not available as a local model input yet.",
        "- The international goalscorers file is player-level but only covers goals, minutes, own-goal flags, and penalties. It is not enough to represent full player form.",
        "",
        "## Gate Result",
        "",
        "Do not enable player-performance adjustments in live predictions yet.",
        "",
        "Required before implementation:",
        "",
        "- A legally usable player-performance feed with historical club and national-team coverage.",
        "- Pre-kickoff-safe source timestamps for each player-match row.",
        "- Stable player identity mapping across club and national-team data.",
        "- A time-safe backtest showing lower log loss and no Brier/calibration regression versus the current baseline.",
        "",
        "## Fetch Results",
        "",
        "| Source | Status | Note |",
        "|---|---:|---|",
    ]
    for item in fetches:
        status = "ok" if item.ok else "failed"
        lines.append(f"| {item.name} | {status} | {item.note} |")
    OUTPUT_REPORTS.mkdir(parents=True, exist_ok=True)
    (OUTPUT_REPORTS / "player_performance_data_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_contract_templates() -> None:
    write_csv(PLAYER_INPUTS / "player_match_performance.csv", [], PLAYER_MATCH_FIELDS)
    write_csv(PLAYER_INPUTS / "player_identity_map.csv", [], PLAYER_MAP_FIELDS)


def main() -> int:
    ensure_dirs()
    fetches: list[FetchResult] = []
    competitions = fetch_statsbomb_competitions(fetches)
    match_by_id = fetch_statsbomb_matches(competitions, fetches)
    fetch_lineups_for_existing_events(fetches)
    coverage_rows = competition_coverage(match_by_id)
    sample_rows, identities = build_player_event_sample(match_by_id)
    source_manifest = build_source_manifest(coverage_rows)

    write_contract_templates()
    write_csv(PLAYER_INPUTS / "source_manifest.csv", source_manifest, SOURCE_MANIFEST_FIELDS)
    write_csv(PROCESSED / "player_performance_source_coverage.csv", coverage_rows, list(coverage_rows[0].keys()) if coverage_rows else [])
    write_csv(PROCESSED / "statsbomb_player_match_performance_sample.csv", sample_rows, PLAYER_MATCH_FIELDS)
    write_csv(PROCESSED / "statsbomb_player_identity_sample.csv", identities, PLAYER_MAP_FIELDS)
    write_report(fetches, coverage_rows, sample_rows, identities)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": "not_sufficient_for_model_gate",
        "source_manifest": str(PLAYER_INPUTS / "source_manifest.csv"),
        "player_match_contract": str(PLAYER_INPUTS / "player_match_performance.csv"),
        "player_identity_contract": str(PLAYER_INPUTS / "player_identity_map.csv"),
        "coverage_table": str(PROCESSED / "player_performance_source_coverage.csv"),
        "statsbomb_sample": str(PROCESSED / "statsbomb_player_match_performance_sample.csv"),
        "identity_sample": str(PROCESSED / "statsbomb_player_identity_sample.csv"),
        "report": str(OUTPUT_REPORTS / "player_performance_data_audit.md"),
        "fetches": [item.__dict__ for item in fetches],
        "statsbomb_competition_seasons": len(coverage_rows),
        "statsbomb_match_metadata_rows": sum(int(row.get("matches") or 0) for row in coverage_rows),
        "statsbomb_sample_player_match_rows": len(sample_rows),
        "statsbomb_sample_player_identities": len(identities),
    }
    (REPORTS / "player_performance_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
