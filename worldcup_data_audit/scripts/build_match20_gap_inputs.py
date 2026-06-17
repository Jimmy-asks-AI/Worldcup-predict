from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
RAW = WORKSPACE_ROOT / "worldcup_data_audit" / "data" / "raw"
PROCESSED = WORKSPACE_ROOT / "worldcup_data_audit" / "data" / "processed"
INPUTS = WORKSPACE_ROOT / "inputs"
REPORTS = WORKSPACE_ROOT / "outputs" / "reports"

FIFA_API = "https://api.fifa.com/api/v3"
OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "codex-worldcup-gap-fill/1.0"

MATCH = {
    "local_match_id": "20",
    "home_team": "Austria",
    "away_team": "Jordan",
    "id_competition": "17",
    "id_season": "285023",
    "id_stage": "289273",
    "id_match": "400021498",
    "match_centre_url": "https://www.fifa.com/en/match-centre/match/17/285023/289273/400021498",
}

LINEUP_FIELDS = [
    "match_id",
    "team",
    "player",
    "role",
    "position",
    "rating",
    "rating_basis",
    "status",
    "expected_minutes",
    "sub_minute",
    "official",
    "source",
    "notes",
    "nationality",
    "club",
]

SQUAD_FIELDS = [
    "match_id",
    "source",
    "source_timestamp",
    "team",
    "fifa_team_id",
    "country_code",
    "player_id",
    "player",
    "short_name",
    "shirt_number",
    "role",
    "position",
    "status_code",
    "captain",
    "birth_date",
    "height_cm",
    "weight_kg",
    "international_caps",
    "international_goals",
    "fifa_statistics_matches",
    "fifa_statistics_goals",
    "fifa_statistics_wins",
    "fifa_statistics_draws",
    "fifa_statistics_losses",
    "player_detail_available",
    "statistics_available",
    "notes",
]

PROFILE_FIELDS = [
    "match_id",
    "team",
    "player_id",
    "player",
    "role",
    "position",
    "shirt_number",
    "captain",
    "birth_date",
    "height_cm",
    "weight_kg",
    "international_caps",
    "international_goals",
    "statistics_matches",
    "statistics_goals",
    "source",
    "source_timestamp",
    "notes",
]

IDENTITY_FIELDS = [
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

JOIN_FIELDS = [
    "match_id",
    "team",
    "player",
    "role",
    "position",
    "matched_rows",
    "total_minutes",
    "goals",
    "assists",
    "xg",
    "shots",
    "shots_on_target",
    "key_passes",
    "tackles",
    "interceptions",
    "blocks",
    "clearances",
    "yellow_cards",
    "red_cards",
    "source_note",
]

WEATHER_FIELDS = [
    "match_id",
    "stadium",
    "time_utc",
    "source",
    "source_timestamp",
    "temperature_c",
    "humidity_pct",
    "precipitation_mm",
    "wind_kph",
    "weather_basis",
    "notes",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def fetch_json(url: str, cache_path: Path, sleep_seconds: float = 0.0) -> Any:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read().decode("utf-8")
    cache_path.write_text(payload, encoding="utf-8")
    if sleep_seconds:
        time.sleep(sleep_seconds)
    return json.loads(payload)


def desc(value: Any) -> str:
    if isinstance(value, list) and value:
        for item in value:
            if item.get("Locale") == "en-GB" and item.get("Description"):
                return str(item["Description"])
        return str(value[0].get("Description", ""))
    if value is None:
        return ""
    return str(value)


def key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def pos(value: Any) -> str:
    return {0: "GK", 1: "DF", 2: "MF", 3: "FW"}.get(value, "MF")


def role(status: Any) -> str:
    if status == 1:
        return "starter"
    if status == 2:
        return "substitute"
    return "reserve"


def expected_minutes(player_role: str) -> str:
    if player_role == "starter":
        return "90"
    if player_role == "substitute":
        return "25"
    return "0"


def aggregate_statsbomb_rows(performance_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, float]]:
    metrics = [
        "minutes",
        "goals",
        "assists",
        "xg",
        "shots",
        "shots_on_target",
        "key_passes",
        "tackles",
        "interceptions",
        "blocks",
        "clearances",
        "yellow_cards",
        "red_cards",
    ]
    out: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in performance_rows:
        team = row.get("national_team") or row.get("team") or ""
        player = row.get("player_name", "")
        if not team or not player:
            continue
        bucket = out[(team, key(player))]
        bucket["matched_rows"] += 1
        for metric in metrics:
            try:
                bucket[metric] += float(row.get(metric, "") or 0.0)
            except ValueError:
                pass
    return out


def build_fifa_inputs() -> dict[str, Any]:
    raw_dir = RAW / "fifa_api"
    player_dir = raw_dir / "match20_players"
    match_id = MATCH["id_match"]
    id_comp = MATCH["id_competition"]
    id_season = MATCH["id_season"]
    id_stage = MATCH["id_stage"]
    source_timestamp = now_utc()

    urls = {
        "calendar": f"{FIFA_API}/calendar/id/{match_id}?language=en",
        "live": f"{FIFA_API}/live/football/{id_comp}/{id_season}/{id_stage}/{match_id}?language=en",
        "timeline": f"{FIFA_API}/timelines/{id_comp}/{id_season}/{id_stage}/{match_id}?language=en",
        "season_squads": f"{FIFA_API}/teams/squads/all/{id_comp}/{id_season}?language=en",
    }
    calendar = fetch_json(urls["calendar"], raw_dir / "match20_calendar.json")
    live = fetch_json(urls["live"], raw_dir / "match20_live.json")
    timeline = fetch_json(urls["timeline"], raw_dir / "match20_timeline.json")
    season_squads = fetch_json(urls["season_squads"], raw_dir / "season_teams_squads.json")

    lineups: list[dict[str, Any]] = []
    squad_rows: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    identities: list[dict[str, Any]] = []
    player_fetches = {"detail_ok": 0, "detail_null": 0, "statistics_ok": 0, "statistics_null": 0}

    for side in ("HomeTeam", "AwayTeam"):
        team_obj = live.get(side) or {}
        team = desc(team_obj.get("TeamName"))
        country_code = team_obj.get("IdCountry", "")
        fifa_team_id = team_obj.get("IdTeam", "")
        for player in team_obj.get("Players") or []:
            player_id = str(player.get("IdPlayer", ""))
            player_name = desc(player.get("PlayerName"))
            short_name = desc(player.get("ShortName"))
            player_role = role(player.get("Status"))
            position = pos(player.get("Position"))
            detail = fetch_json(f"{FIFA_API}/players/{player_id}?language=en", player_dir / f"player_{player_id}.json", 0.05)
            stats = fetch_json(
                f"{FIFA_API}/individualstatistics/player/{player_id}?language=en",
                player_dir / f"individualstatistics_{player_id}.json",
                0.05,
            )
            if detail:
                player_fetches["detail_ok"] += 1
            else:
                player_fetches["detail_null"] += 1
                detail = {}
            if stats:
                player_fetches["statistics_ok"] += 1
            else:
                player_fetches["statistics_null"] += 1
                stats = {}

            common_note = f"FIFA live player Status={player.get('Status')}; source={MATCH['match_centre_url']}"
            lineups.append(
                {
                    "match_id": MATCH["local_match_id"],
                    "team": team,
                    "player": player_name,
                    "role": player_role,
                    "position": position,
                    "rating": "",
                    "rating_basis": "pre_kickoff",
                    "status": "available",
                    "expected_minutes": expected_minutes(player_role),
                    "sub_minute": "",
                    "official": "true",
                    "source": "fifa_api_live_match",
                    "notes": common_note,
                    "nationality": team,
                    "club": "",
                }
            )
            squad_rows.append(
                {
                    "match_id": MATCH["local_match_id"],
                    "source": "fifa_api_live_match",
                    "source_timestamp": source_timestamp,
                    "team": team,
                    "fifa_team_id": fifa_team_id,
                    "country_code": country_code,
                    "player_id": player_id,
                    "player": player_name,
                    "short_name": short_name,
                    "shirt_number": player.get("ShirtNumber", ""),
                    "role": player_role,
                    "position": position,
                    "status_code": player.get("Status", ""),
                    "captain": str(bool(player.get("Captain"))).upper(),
                    "birth_date": detail.get("BirthDate", ""),
                    "height_cm": detail.get("Height", ""),
                    "weight_kg": detail.get("Weight", ""),
                    "international_caps": detail.get("InternationalCaps", ""),
                    "international_goals": detail.get("Goals", ""),
                    "fifa_statistics_matches": stats.get("MatchesPlayed", ""),
                    "fifa_statistics_goals": stats.get("GoalsScored", ""),
                    "fifa_statistics_wins": stats.get("WinMatches", ""),
                    "fifa_statistics_draws": stats.get("DrawMatches", ""),
                    "fifa_statistics_losses": stats.get("LostMatches", ""),
                    "player_detail_available": "TRUE" if detail else "FALSE",
                    "statistics_available": "TRUE" if stats else "FALSE",
                    "notes": common_note,
                }
            )
            profiles.append(
                {
                    "match_id": MATCH["local_match_id"],
                    "team": team,
                    "player_id": player_id,
                    "player": player_name,
                    "role": player_role,
                    "position": position,
                    "shirt_number": player.get("ShirtNumber", ""),
                    "captain": str(bool(player.get("Captain"))).upper(),
                    "birth_date": detail.get("BirthDate", ""),
                    "height_cm": detail.get("Height", ""),
                    "weight_kg": detail.get("Weight", ""),
                    "international_caps": detail.get("InternationalCaps", ""),
                    "international_goals": detail.get("Goals", ""),
                    "statistics_matches": stats.get("MatchesPlayed", ""),
                    "statistics_goals": stats.get("GoalsScored", ""),
                    "source": "fifa_api_player_profile_and_individualstatistics",
                    "source_timestamp": source_timestamp,
                    "notes": "FIFA profile statistics are national/FIFA competition profile fields, not full club form.",
                }
            )
            identities.append(
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "birth_date": detail.get("BirthDate", ""),
                    "national_team": team,
                    "club_team": "",
                    "provider_player_id": player_id,
                    "provider": "fifa_api",
                    "valid_from": "",
                    "valid_to": "",
                }
            )

    lineups.sort(key=lambda row: (row["team"], 0 if row["role"] == "starter" else 1, int(row.get("shirt_number") or 999)))
    squad_rows.sort(key=lambda row: (row["team"], 0 if row["role"] == "starter" else 1, int(row.get("shirt_number") or 999)))
    profiles.sort(key=lambda row: (row["team"], 0 if row["role"] == "starter" else 1, int(row.get("shirt_number") or 999)))

    lineup_path = INPUTS / "lineups" / "match20_austria_jordan_fifa_official.csv"
    squad_path = PROCESSED / "fifa_match20_squad.csv"
    profile_path = INPUTS / "player_performance" / "fifa_match20_player_profiles.csv"
    identity_path = INPUTS / "player_performance" / "fifa_match20_player_identity_map.csv"
    write_csv(lineup_path, lineups, LINEUP_FIELDS)
    write_csv(squad_path, squad_rows, SQUAD_FIELDS)
    write_csv(profile_path, profiles, PROFILE_FIELDS)
    write_csv(identity_path, identities, IDENTITY_FIELDS)

    performance_rows = read_csv(INPUTS / "player_performance" / "player_match_performance.csv")
    aggregated = aggregate_statsbomb_rows(performance_rows)
    joined: list[dict[str, Any]] = []
    for row in lineups:
        bucket = aggregated.get((row["team"], key(row["player"])), {})
        joined.append(
            {
                "match_id": row["match_id"],
                "team": row["team"],
                "player": row["player"],
                "role": row["role"],
                "position": row["position"],
                "matched_rows": int(bucket.get("matched_rows", 0)),
                "total_minutes": round(bucket.get("minutes", 0.0), 1),
                "goals": round(bucket.get("goals", 0.0), 3),
                "assists": round(bucket.get("assists", 0.0), 3),
                "xg": round(bucket.get("xg", 0.0), 4),
                "shots": round(bucket.get("shots", 0.0), 3),
                "shots_on_target": round(bucket.get("shots_on_target", 0.0), 3),
                "key_passes": round(bucket.get("key_passes", 0.0), 3),
                "tackles": round(bucket.get("tackles", 0.0), 3),
                "interceptions": round(bucket.get("interceptions", 0.0), 3),
                "blocks": round(bucket.get("blocks", 0.0), 3),
                "clearances": round(bucket.get("clearances", 0.0), 3),
                "yellow_cards": round(bucket.get("yellow_cards", 0.0), 3),
                "red_cards": round(bucket.get("red_cards", 0.0), 3),
                "source_note": "matched StatsBomb open-data rows" if bucket else "no local StatsBomb player rows",
            }
        )
    join_path = PROCESSED / "fifa_match20_lineup_player_performance_join.csv"
    write_csv(join_path, joined, JOIN_FIELDS)

    return {
        "calendar_path": str(raw_dir / "match20_calendar.json"),
        "live_path": str(raw_dir / "match20_live.json"),
        "timeline_path": str(raw_dir / "match20_timeline.json"),
        "season_squads_path": str(raw_dir / "season_teams_squads.json"),
        "match_status": calendar.get("MatchStatus", ""),
        "officiality_status": calendar.get("OfficialityStatus", ""),
        "home_tactics": (live.get("HomeTeam") or {}).get("Tactics", ""),
        "away_tactics": (live.get("AwayTeam") or {}).get("Tactics", ""),
        "officials": [desc(item.get("Name")) for item in (calendar.get("Officials") or [])],
        "timeline_events": len(timeline.get("Event") or []) if isinstance(timeline, dict) else 0,
        "season_squads_teams": len(season_squads.get("Results") or []) if isinstance(season_squads, dict) else 0,
        "lineup_path": str(lineup_path),
        "squad_path": str(squad_path),
        "profile_path": str(profile_path),
        "identity_path": str(identity_path),
        "join_path": str(join_path),
        "lineup_rows": len(lineups),
        "starter_rows": len([row for row in lineups if row["role"] == "starter"]),
        "substitute_rows": len([row for row in lineups if row["role"] == "substitute"]),
        "profile_rows": len(profiles),
        "player_fetches": player_fetches,
        "statsbomb_join_rows_with_match": len([row for row in joined if int(row["matched_rows"]) > 0]),
        "statsbomb_join_rows_by_team": {
            team: len([row for row in joined if row["team"] == team and int(row["matched_rows"]) > 0])
            for team in (MATCH["home_team"], MATCH["away_team"])
        },
        "urls": urls,
    }


def exact_weather_row() -> dict[str, Any] | None:
    fixtures = {row.get("match_id"): row for row in read_csv(PROCESSED / "fixtures_2026.csv")}
    stadiums = read_csv(PROCESSED / "stadiums_2026.csv")
    fixture = fixtures.get(MATCH["local_match_id"])
    if not fixture:
        return None
    stadium = next((row for row in stadiums if row.get("stadium_name") == fixture.get("stadium") or row.get("fifa_name") == fixture.get("stadium")), None)
    if not stadium:
        return None
    kickoff = (fixture.get("kickoff_utc") or "").replace(":00Z", "")
    if not kickoff:
        return None
    date = kickoff.split("T")[0]
    params = urllib.parse.urlencode(
        {
            "latitude": stadium.get("latitude"),
            "longitude": stadium.get("longitude"),
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "start_date": date,
            "end_date": date,
            "timezone": "UTC",
        }
    )
    url = f"{OPEN_METEO_API}?{params}"
    weather = fetch_json(url, RAW / "open_meteo" / "match20_weather.json")
    hourly = weather.get("hourly") or {}
    times = hourly.get("time") or []
    if kickoff not in times:
        return None
    idx = times.index(kickoff)
    return {
        "match_id": MATCH["local_match_id"],
        "stadium": fixture.get("stadium", ""),
        "time_utc": fixture.get("kickoff_utc", ""),
        "source": "open_meteo_hourly_forecast",
        "source_timestamp": now_utc(),
        "temperature_c": hourly.get("temperature_2m", [""])[idx],
        "humidity_pct": hourly.get("relative_humidity_2m", [""])[idx],
        "precipitation_mm": hourly.get("precipitation", [""])[idx],
        "wind_kph": hourly.get("wind_speed_10m", [""])[idx],
        "weather_basis": "exact_kickoff_hour_forecast",
        "notes": url,
    }


def upsert_weather(row: dict[str, Any] | None) -> dict[str, Any]:
    path = INPUTS / "match_context" / "weather_forecast.csv"
    rows = read_csv(path)
    before = len(rows)
    if row:
        rows = [item for item in rows if item.get("match_id") != MATCH["local_match_id"]]
        rows.append(row)
        rows.sort(key=lambda item: int(item.get("match_id") or 9999))
        write_csv(path, rows, WEATHER_FIELDS)
    return {"path": str(path), "before_rows": before, "after_rows": len(rows), "updated": bool(row), "row": row or {}}


def event_coverage() -> dict[str, Any]:
    rows = read_csv(PROCESSED / "statsbomb_event_half_team_summary.csv")
    by_team = {
        team: len([row for row in rows if row.get("team") == team])
        for team in (MATCH["home_team"], MATCH["away_team"])
    }
    return {"path": str(PROCESSED / "statsbomb_event_half_team_summary.csv"), "rows": len(rows), "by_team": by_team}


def write_report(summary: dict[str, Any]) -> Path:
    report_path = REPORTS / "match20_gap_fill_report.md"
    REPORTS.mkdir(parents=True, exist_ok=True)
    fifa = summary["fifa"]
    weather = summary["weather"]
    events = summary["event_coverage"]
    lines = [
        "# Austria vs Jordan Gap Fill Report",
        "",
        f"Generated: {now_utc()}",
        "",
        "## What Was Filled",
        "",
        f"- Official FIFA live lineup CSV: `{fifa['lineup_path']}`",
        f"- FIFA 26-player squad extract: `{fifa['squad_path']}`",
        f"- FIFA player profile/stat extract: `{fifa['profile_path']}`",
        f"- FIFA player identity map: `{fifa['identity_path']}`",
        f"- Official lineup to local player-performance join: `{fifa['join_path']}`",
        f"- Exact kickoff-hour weather row updated: `{weather['path']}`",
        "",
        "## Coverage",
        "",
        f"- FIFA lineup rows: {fifa['lineup_rows']} ({fifa['starter_rows']} starters, {fifa['substitute_rows']} substitutes).",
        f"- FIFA player profile rows: {fifa['profile_rows']}.",
        f"- FIFA player detail fetches: {fifa['player_fetches']}.",
        f"- FIFA timeline events currently available: {fifa['timeline_events']}.",
        f"- Local StatsBomb lineup-player matches: {fifa['statsbomb_join_rows_with_match']} of {fifa['lineup_rows']}.",
        f"- Local StatsBomb player matches by team: {fifa['statsbomb_join_rows_by_team']}.",
        f"- Team-half event sample rows: {events['rows']}; target-team rows: {events['by_team']}.",
        f"- Exact weather updated: {weather['updated']}; row: `{weather['row']}`",
        "",
        "## Remaining Gaps",
        "",
        "- Injury/suspension rows are not separately exposed by this FIFA live endpoint. They should be added only from a trusted pre-kickoff injury or squad-availability source.",
        "- Substitution strategy is not official before kickoff. The CSV marks official bench players and default expected minutes, but it does not know the coach's planned substitutions.",
        "- FIFA player profiles provide national/FIFA profile statistics, not full club plus national player-match performance.",
        "- StatsBomb open data now covers Austria event samples from public Euro matches, but Jordan still has no local team-event sample.",
        "- `playerstatistics/match/...` is null before the match has live stats; it must not be used for a pre-match prediction.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    summary = {
        "fifa": build_fifa_inputs(),
        "weather": upsert_weather(exact_weather_row()),
        "event_coverage": event_coverage(),
    }
    report_path = write_report(summary)
    summary["report"] = str(report_path)
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
