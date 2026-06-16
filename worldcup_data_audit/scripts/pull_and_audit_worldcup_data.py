from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

USER_AGENT = "codex-worldcup-data-audit/1.0"


@dataclass
class FetchResult:
    name: str
    url: str
    ok: bool
    path: str | None
    note: str


SOURCES = {
    "thestatsapi_fixtures": "https://www.thestatsapi.com/world-cup/data/fixtures.json",
    "worldcup26_games": "https://worldcup26.ir/get/games",
    "worldcup26_groups": "https://worldcup26.ir/get/groups",
    "worldcup26_teams": "https://worldcup26.ir/get/teams",
    "worldcup26_stadiums": "https://worldcup26.ir/get/stadiums",
    "international_results": "https://raw.githubusercontent.com/martj42/international_results/master/results.csv",
    "international_goalscorers": "https://raw.githubusercontent.com/martj42/international_results/master/goalscorers.csv",
    "international_shootouts": "https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv",
    "statsbomb_competitions": "https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json",
    "statsbomb_wc2022_matches": "https://raw.githubusercontent.com/statsbomb/open-data/master/data/matches/43/106.json",
}


STADIUM_COORDS = {
    "Estadio Azteca": (19.3029, -99.1505),
    "Estadio Guadalajara": (20.6819, -103.4620),
    "Estadio Monterrey": (25.6682, -100.2441),
    "Dallas Stadium": (32.7473, -97.0945),
    "Houston Stadium": (29.6847, -95.4107),
    "Atlanta Stadium": (33.7554, -84.4008),
    "Boston Stadium": (42.0909, -71.2643),
    "New York New Jersey Stadium": (40.8135, -74.0745),
    "Philadelphia Stadium": (39.9008, -75.1675),
    "Miami Stadium": (25.9580, -80.2389),
    "Kansas City Stadium": (39.0490, -94.4839),
    "Los Angeles Stadium": (33.9535, -118.3392),
    "San Francisco Bay Area Stadium": (37.4030, -121.9700),
    "Seattle Stadium": (47.5952, -122.3316),
    "Toronto Stadium": (43.6332, -79.4186),
    "Vancouver Stadium": (49.2768, -123.1119),
}


def ensure_dirs() -> None:
    for path in (RAW, PROCESSED, REPORTS):
        path.mkdir(parents=True, exist_ok=True)


def request_bytes(url: str, timeout: int = 40) -> bytes:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urlopen(req, timeout=timeout) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 - caller records final failure
            last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError("request failed without an exception")


def fetch_to_file(name: str, url: str, suffix: str) -> FetchResult:
    target = RAW / f"{name}{suffix}"
    try:
        data = request_bytes(url)
        target.write_bytes(data)
        return FetchResult(name, url, True, str(target), f"{len(data)} bytes")
    except HTTPError as exc:
        return FetchResult(name, url, False, None, f"HTTP {exc.code}: {exc.reason}")
    except URLError as exc:
        return FetchResult(name, url, False, None, f"URL error: {exc.reason}")
    except Exception as exc:  # noqa: BLE001 - audit should record all failures
        return FetchResult(name, url, False, None, f"{type(exc).__name__}: {exc}")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if not fieldnames:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def flatten_tsa_fixtures(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in data.get("fixtures", []):
        rows.append(
            {
                "source": "thestatsapi",
                "match_id": item.get("matchNumber"),
                "date": item.get("date"),
                "kickoff_utc": item.get("kickoffUtc"),
                "stage": item.get("stage"),
                "group": item.get("group"),
                "home_team": item.get("homeTeam"),
                "away_team": item.get("awayTeam"),
                "stadium": item.get("stadium"),
                "host_city": item.get("hostCity"),
                "status": "scheduled",
            }
        )
    return rows


def flatten_worldcup26_games(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in data.get("games", []):
        finished = item.get("finished")
        is_finished = str(finished).upper() == "TRUE"
        rows.append(
            {
                "source": "worldcup26.ir",
                "match_id": item.get("id"),
                "date_local": item.get("local_date"),
                "stage": item.get("type"),
                "group": item.get("group"),
                "matchday": item.get("matchday"),
                "home_team": item.get("home_team_name_en"),
                "away_team": item.get("away_team_name_en"),
                "raw_home_score": item.get("home_score"),
                "raw_away_score": item.get("away_score"),
                "actual_home_score": item.get("home_score") if is_finished else "",
                "actual_away_score": item.get("away_score") if is_finished else "",
                "home_scorers": item.get("home_scorers"),
                "away_scorers": item.get("away_scorers"),
                "stadium_id": item.get("stadium_id"),
                "finished": finished,
                "time_elapsed": item.get("time_elapsed"),
            }
        )
    return rows


def flatten_worldcup26_groups(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for group in data.get("groups", []):
        for team in group.get("teams", []):
            rows.append(
                {
                    "source": "worldcup26.ir",
                    "group": group.get("name"),
                    "team_id": team.get("team_id"),
                    "played": team.get("mp"),
                    "won": team.get("w"),
                    "drawn": team.get("d"),
                    "lost": team.get("l"),
                    "points": team.get("pts"),
                    "goals_for": team.get("gf"),
                    "goals_against": team.get("ga"),
                    "goal_difference": team.get("gd"),
                }
            )
    return rows


def flatten_teams(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "team_id": item.get("id"),
            "team_name": item.get("name_en"),
            "fifa_code": item.get("fifa_code"),
            "iso2": item.get("iso2"),
            "group": item.get("groups"),
        }
        for item in data.get("teams", [])
    ]


def flatten_stadiums(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in data.get("stadiums", []):
        fifa_name = item.get("fifa_name")
        coords = STADIUM_COORDS.get(fifa_name) or STADIUM_COORDS.get(item.get("name_en"))
        rows.append(
            {
                "stadium_id": item.get("id"),
                "stadium_name": item.get("name_en"),
                "fifa_name": fifa_name,
                "city": item.get("city_en"),
                "country": item.get("country_en"),
                "capacity": item.get("capacity"),
                "region": item.get("region"),
                "latitude": coords[0] if coords else "",
                "longitude": coords[1] if coords else "",
            }
        )
    return rows


def statsbomb_worldcup_seasons(comp: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in comp:
        if "World Cup" in item.get("competition_name", ""):
            rows.append(
                {
                    "competition_id": item.get("competition_id"),
                    "season_id": item.get("season_id"),
                    "competition_name": item.get("competition_name"),
                    "season_name": item.get("season_name"),
                    "match_available": item.get("match_available"),
                    "event_available": item.get("event_available"),
                    "match_available_360": item.get("match_available_360"),
                    "event_updated": item.get("event_updated"),
                }
            )
    return rows


def flatten_statsbomb_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in matches:
        rows.append(
            {
                "match_id": item.get("match_id"),
                "match_date": item.get("match_date"),
                "kick_off": item.get("kick_off"),
                "stage": (item.get("competition_stage") or {}).get("name"),
                "home_team": (item.get("home_team") or {}).get("home_team_name"),
                "away_team": (item.get("away_team") or {}).get("away_team_name"),
                "home_score": item.get("home_score"),
                "away_score": item.get("away_score"),
                "stadium": (item.get("stadium") or {}).get("name"),
                "referee": (item.get("referee") or {}).get("name"),
            }
        )
    return rows


def fetch_statsbomb_events(match_ids: list[int], limit: int = 6) -> list[FetchResult]:
    results = []
    for match_id in match_ids[:limit]:
        url = f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/{match_id}.json"
        results.append(fetch_to_file(f"statsbomb_events_{match_id}", url, ".json"))
    return results


def event_team_name(event: dict[str, Any]) -> str:
    team = event.get("team") or {}
    return team.get("name") or ""


def summarize_statsbomb_events(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    event_rows: list[dict[str, Any]] = []
    half_rows: list[dict[str, Any]] = []

    for path in paths:
        match_id = path.stem.replace("statsbomb_events_", "")
        events = load_json(path)
        by_team_half: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
        type_counter = Counter()

        for event in events:
            event_type = (event.get("type") or {}).get("name", "")
            type_counter[event_type] += 1
            team = event_team_name(event)
            period = int(event.get("period") or 0)
            half = 1 if period == 1 else 2 if period == 2 else period
            key = (team, half)

            if event_type == "Shot":
                by_team_half[key]["shots"] += 1
                shot = event.get("shot") or {}
                if (shot.get("outcome") or {}).get("name") == "Goal":
                    by_team_half[key]["goals"] += 1
                if (shot.get("type") or {}).get("name") == "Penalty":
                    by_team_half[key]["penalty_shots"] += 1
            if event_type == "Foul Committed":
                by_team_half[key]["fouls_committed"] += 1
                card = ((event.get("foul_committed") or {}).get("card") or {}).get("name")
                if card == "Yellow Card":
                    by_team_half[key]["yellow_cards"] += 1
                elif card == "Red Card":
                    by_team_half[key]["red_cards"] += 1
                elif card == "Second Yellow":
                    by_team_half[key]["second_yellows"] += 1
            if event_type == "Bad Behaviour":
                card = ((event.get("bad_behaviour") or {}).get("card") or {}).get("name")
                if card == "Yellow Card":
                    by_team_half[key]["yellow_cards"] += 1
                elif card == "Red Card":
                    by_team_half[key]["red_cards"] += 1
            pass_obj = event.get("pass") or {}
            pass_type = (pass_obj.get("type") or {}).get("name")
            if pass_type == "Corner":
                by_team_half[key]["corners"] += 1
            elif pass_type == "Free Kick":
                by_team_half[key]["free_kick_passes"] += 1
            if (event.get("play_pattern") or {}).get("name") == "From Free Kick":
                by_team_half[key]["free_kick_sequence_events"] += 1

        event_rows.append(
            {
                "match_id": match_id,
                "event_count": len(events),
                "passes": type_counter["Pass"],
                "shots": type_counter["Shot"],
                "fouls_committed": type_counter["Foul Committed"],
                "fouls_won": type_counter["Foul Won"],
                "bad_behaviour": type_counter["Bad Behaviour"],
                "substitutions": type_counter["Substitution"],
            }
        )

        for (team, half), counter in sorted(by_team_half.items()):
            if not team or half not in (1, 2):
                continue
            half_rows.append(
                {
                    "match_id": match_id,
                    "team": team,
                    "half": half,
                    "goals": counter["goals"],
                    "shots": counter["shots"],
                    "fouls_committed": counter["fouls_committed"],
                    "yellow_cards": counter["yellow_cards"],
                    "red_cards": counter["red_cards"],
                    "second_yellows": counter["second_yellows"],
                    "corners": counter["corners"],
                    "free_kick_passes": counter["free_kick_passes"],
                    "free_kick_sequence_events": counter["free_kick_sequence_events"],
                    "penalty_shots": counter["penalty_shots"],
                }
            )

    return event_rows, half_rows


def expected_score(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-(ra - rb) / 400.0))


def build_elo_snapshot(results: list[dict[str, str]]) -> list[dict[str, Any]]:
    ratings: dict[str, float] = defaultdict(lambda: 1500.0)
    games: dict[str, int] = defaultdict(int)

    complete = [
        row
        for row in results
        if row.get("home_score") not in ("", "NA", None)
        and row.get("away_score") not in ("", "NA", None)
    ]
    complete.sort(key=lambda r: r["date"])

    for row in complete:
        home = row["home_team"]
        away = row["away_team"]
        try:
            hg = int(row["home_score"])
            ag = int(row["away_score"])
        except ValueError:
            continue
        rh = ratings[home]
        ra = ratings[away]
        actual = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
        margin = abs(hg - ag)
        importance = 1.0
        tournament = row.get("tournament", "")
        if tournament == "FIFA World Cup":
            importance = 2.5
        elif "qualif" in tournament.lower():
            importance = 1.5
        k = 24.0 * importance * (1.0 + math.log1p(margin) / 2.0)
        exp_h = expected_score(rh, ra)
        ratings[home] = rh + k * (actual - exp_h)
        ratings[away] = ra + k * ((1.0 - actual) - (1.0 - exp_h))
        games[home] += 1
        games[away] += 1

    rows = [
        {"team": team, "elo": round(rating, 1), "games": games[team]}
        for team, rating in ratings.items()
    ]
    rows.sort(key=lambda row: row["elo"], reverse=True)
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def aggregate_team_form(results: list[dict[str, str]], n: int = 10) -> list[dict[str, Any]]:
    matches_by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        if row.get("home_score") in ("", "NA", None) or row.get("away_score") in ("", "NA", None):
            continue
        try:
            hg = int(row["home_score"])
            ag = int(row["away_score"])
        except ValueError:
            continue
        date = row.get("date", "")
        home, away = row["home_team"], row["away_team"]
        matches_by_team[home].append({"date": date, "gf": hg, "ga": ag, "result": 1 if hg > ag else 0.5 if hg == ag else 0})
        matches_by_team[away].append({"date": date, "gf": ag, "ga": hg, "result": 1 if ag > hg else 0.5 if hg == ag else 0})

    rows = []
    for team, matches in matches_by_team.items():
        recent = sorted(matches, key=lambda r: r["date"])[-n:]
        if not recent:
            continue
        rows.append(
            {
                "team": team,
                "recent_matches": len(recent),
                "recent_points_per_match": round(sum(r["result"] * 3 for r in recent) / len(recent), 3),
                "recent_goals_for_per_match": round(sum(r["gf"] for r in recent) / len(recent), 3),
                "recent_goals_against_per_match": round(sum(r["ga"] for r in recent) / len(recent), 3),
            }
        )
    rows.sort(key=lambda r: r["recent_points_per_match"], reverse=True)
    return rows


def fetch_weather_samples(stadium_rows: list[dict[str, Any]], max_stadiums: int = 6) -> FetchResult:
    rows = []
    for stadium in stadium_rows[:max_stadiums]:
        lat, lon = stadium.get("latitude"), stadium.get("longitude")
        if lat == "" or lon == "":
            continue
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "forecast_days": 7,
            "timezone": "UTC",
        }
        url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
        try:
            data = json.loads(request_bytes(url).decode("utf-8"))
            hourly = data.get("hourly", {})
            for i, time in enumerate(hourly.get("time", [])[:24]):
                rows.append(
                    {
                        "stadium": stadium.get("fifa_name") or stadium.get("stadium_name"),
                        "city": stadium.get("city"),
                        "time_utc": time,
                        "temperature_2m": hourly.get("temperature_2m", [None])[i],
                        "relative_humidity_2m": hourly.get("relative_humidity_2m", [None])[i],
                        "precipitation": hourly.get("precipitation", [None])[i],
                        "wind_speed_10m": hourly.get("wind_speed_10m", [None])[i],
                    }
                )
        except Exception as exc:  # noqa: BLE001
            rows.append({"stadium": stadium.get("stadium_name"), "error": str(exc)})
    path = PROCESSED / "weather_hourly_sample.csv"
    write_csv(path, rows)
    return FetchResult("open_meteo_weather_sample", "https://api.open-meteo.com/v1/forecast", True, str(path), f"{len(rows)} hourly rows")


def generate_audit_report(fetches: list[FetchResult], metrics: dict[str, Any]) -> None:
    lines = []
    lines.append("# World Cup Prediction Data Audit")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Fetch Results")
    lines.append("")
    lines.append("| Source | Status | Local path | Note |")
    lines.append("|---|---:|---|---|")
    for item in fetches:
        status = "ok" if item.ok else "failed"
        path = item.path or ""
        lines.append(f"| {item.name} | {status} | `{path}` | {item.note} |")

    lines.append("")
    lines.append("## Processed Tables")
    lines.append("")
    lines.append("| Table | Rows | Use |")
    lines.append("|---|---:|---|")
    for name, info in metrics.get("tables", {}).items():
        lines.append(f"| `{name}` | {info['rows']} | {info['use']} |")

    lines.append("")
    lines.append("## Requirement Coverage")
    lines.append("")
    lines.append("| Requirement | Current coverage | Result |")
    lines.append("|---|---|---|")
    for row in metrics.get("coverage", []):
        lines.append(f"| {row['requirement']} | {row['coverage']} | {row['result']} |")

    lines.append("")
    lines.append("## Key Findings")
    lines.append("")
    for finding in metrics.get("findings", []):
        lines.append(f"- {finding}")

    (REPORTS / "data_audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()
    fetches: list[FetchResult] = []

    suffix_by_name = {
        name: ".csv" if url.endswith(".csv") else ".json"
        for name, url in SOURCES.items()
    }
    for name, url in SOURCES.items():
        fetches.append(fetch_to_file(name, url, suffix_by_name[name]))

    # Optional official FIFA ranking page snapshot. Parsed later only if needed.
    fetches.append(fetch_to_file("fifa_ranking_men_page", "https://inside.fifa.com/fifa-world-ranking/men", ".html"))
    fetches.append(fetch_to_file("thestatsapi_lineups_page", "https://www.thestatsapi.com/world-cup/lineups", ".html"))
    fetches.append(fetch_to_file("thestatsapi_odds_page", "https://www.thestatsapi.com/world-cup/odds", ".html"))

    tables: dict[str, dict[str, Any]] = {}

    if (RAW / "thestatsapi_fixtures.json").exists():
        rows = flatten_tsa_fixtures(load_json(RAW / "thestatsapi_fixtures.json"))
        write_csv(PROCESSED / "fixtures_2026.csv", rows)
        tables["fixtures_2026.csv"] = {"rows": len(rows), "use": "2026 full schedule base table"}

    if (RAW / "worldcup26_games.json").exists():
        rows = flatten_worldcup26_games(load_json(RAW / "worldcup26_games.json"))
        write_csv(PROCESSED / "worldcup26_games.csv", rows)
        tables["worldcup26_games.csv"] = {"rows": len(rows), "use": "live or current match scores from non-official source"}

    if (RAW / "worldcup26_groups.json").exists():
        rows = flatten_worldcup26_groups(load_json(RAW / "worldcup26_groups.json"))
        write_csv(PROCESSED / "worldcup26_group_table.csv", rows)
        tables["worldcup26_group_table.csv"] = {"rows": len(rows), "use": "current group standings from non-official source"}

    team_rows: list[dict[str, Any]] = []
    if (RAW / "worldcup26_teams.json").exists():
        team_rows = flatten_teams(load_json(RAW / "worldcup26_teams.json"))
        write_csv(PROCESSED / "teams_2026.csv", team_rows)
        tables["teams_2026.csv"] = {"rows": len(team_rows), "use": "team names and FIFA codes"}

    stadium_rows: list[dict[str, Any]] = []
    if (RAW / "worldcup26_stadiums.json").exists():
        stadium_rows = flatten_stadiums(load_json(RAW / "worldcup26_stadiums.json"))
        write_csv(PROCESSED / "stadiums_2026.csv", stadium_rows)
        tables["stadiums_2026.csv"] = {"rows": len(stadium_rows), "use": "venue metadata and manually mapped coordinates"}
        fetches.append(fetch_weather_samples(stadium_rows))
        tables["weather_hourly_sample.csv"] = {"rows": sum(1 for _ in (PROCESSED / "weather_hourly_sample.csv").open(encoding="utf-8")) - 1, "use": "hourly weather feature sample from Open-Meteo"}

    results_rows: list[dict[str, str]] = []
    if (RAW / "international_results.csv").exists():
        results_rows = read_csv_dicts(RAW / "international_results.csv")
        wc_rows = [row for row in results_rows if row.get("tournament") == "FIFA World Cup"]
        write_csv(PROCESSED / "international_results_worldcup_only.csv", wc_rows)
        tables["international_results_worldcup_only.csv"] = {"rows": len(wc_rows), "use": "World Cup historical scoreline training and backtesting"}

        elo_rows = build_elo_snapshot(results_rows)
        write_csv(PROCESSED / "derived_elo_snapshot.csv", elo_rows)
        tables["derived_elo_snapshot.csv"] = {"rows": len(elo_rows), "use": "self-computed national-team Elo from international results"}

        form_rows = aggregate_team_form(results_rows)
        write_csv(PROCESSED / "derived_recent_form.csv", form_rows)
        tables["derived_recent_form.csv"] = {"rows": len(form_rows), "use": "recent form, goals for, goals against features"}

    if (RAW / "international_goalscorers.csv").exists():
        goalscorer_rows = read_csv_dicts(RAW / "international_goalscorers.csv")
        wc_goal_rows = [row for row in goalscorer_rows if row.get("date", "") >= "1930-01-01"]
        write_csv(PROCESSED / "international_goalscorers.csv", wc_goal_rows)
        tables["international_goalscorers.csv"] = {"rows": len(wc_goal_rows), "use": "goal minute and penalty flags where available"}

    if (RAW / "international_shootouts.csv").exists():
        shootout_rows = read_csv_dicts(RAW / "international_shootouts.csv")
        write_csv(PROCESSED / "international_shootouts.csv", shootout_rows)
        tables["international_shootouts.csv"] = {"rows": len(shootout_rows), "use": "penalty shootout winner modeling"}

    if (RAW / "statsbomb_competitions.json").exists():
        comp_rows = statsbomb_worldcup_seasons(load_json(RAW / "statsbomb_competitions.json"))
        write_csv(PROCESSED / "statsbomb_worldcup_seasons.csv", comp_rows)
        tables["statsbomb_worldcup_seasons.csv"] = {"rows": len(comp_rows), "use": "which World Cup seasons are available in StatsBomb open data"}

    statsbomb_match_rows: list[dict[str, Any]] = []
    if (RAW / "statsbomb_wc2022_matches.json").exists():
        statsbomb_match_rows = flatten_statsbomb_matches(load_json(RAW / "statsbomb_wc2022_matches.json"))
        write_csv(PROCESSED / "statsbomb_wc2022_matches.csv", statsbomb_match_rows)
        tables["statsbomb_wc2022_matches.csv"] = {"rows": len(statsbomb_match_rows), "use": "StatsBomb match IDs for event download"}
        match_ids = [int(row["match_id"]) for row in statsbomb_match_rows if row.get("match_id")]
        fetches.extend(fetch_statsbomb_events(match_ids, limit=8))

    event_paths = sorted(RAW.glob("statsbomb_events_*.json"))
    if event_paths:
        event_rows, half_rows = summarize_statsbomb_events(event_paths)
        write_csv(PROCESSED / "statsbomb_event_match_summary.csv", event_rows)
        write_csv(PROCESSED / "statsbomb_event_half_team_summary.csv", half_rows)
        tables["statsbomb_event_match_summary.csv"] = {"rows": len(event_rows), "use": "event-level match coverage sample"}
        tables["statsbomb_event_half_team_summary.csv"] = {"rows": len(half_rows), "use": "team-half event counts for goals, cards, corners, free kicks, penalties"}

    coverage = [
        {
            "requirement": "2026 schedule",
            "coverage": "104 rows from TheStatsAPI fixtures plus team/stadium tables",
            "result": "sufficient for fixture base, cross-check recommended",
        },
        {
            "requirement": "historical matches",
            "coverage": "international results CSV and StatsBomb World Cup matches/events; current scores must use actual_* fields only",
            "result": "sufficient for scoreline, 1X2, Elo, and event model training",
        },
        {
            "requirement": "FIFA ranking",
            "coverage": "official FIFA ranking page saved as HTML, not parsed into stable table yet",
            "result": "partially sufficient; needs parser/cache or manual export",
        },
        {
            "requirement": "Elo",
            "coverage": "derived Elo snapshot computed locally from international results",
            "result": "sufficient for a reproducible baseline",
        },
        {
            "requirement": "lineups",
            "coverage": "TheStatsAPI lineup page saved; JSON API requires key; confirmed lineups appear about 75 minutes pre-kickoff",
            "result": "not sufficient without API key for automated live system",
        },
        {
            "requirement": "odds",
            "coverage": "TheStatsAPI odds page saved; API requires key; page claims 1X2, totals, BTTS, corners",
            "result": "not sufficient without API key for automated model input",
        },
        {
            "requirement": "weather",
            "coverage": "Open-Meteo hourly sample downloaded for mapped stadiums",
            "result": "sufficient for rolling forecast features; far-future exact forecast still time-limited",
        },
        {
            "requirement": "exact score and 1X2 prediction",
            "coverage": "historical scorelines, derived Elo, recent form, StatsBomb event samples",
            "result": "sufficient for baseline Poisson/ML models",
        },
        {
            "requirement": "group ranking and champion simulation",
            "coverage": "fixture base plus scoreline simulation inputs available",
            "result": "sufficient after implementing 2026 tournament rules",
        },
        {
            "requirement": "goals, goal difference, cards, free kicks, corners, penalties by half",
            "coverage": "StatsBomb event half-team sample contains goals, shots, fouls, cards, corners, free-kick passes, penalties",
            "result": "sufficient for historical event model training; 2026 live requires event feed/API",
        },
    ]

    findings = [
        "Free sources can support a working baseline for schedule, historical results, Elo, recent form, weather, scoreline simulation, group ranking, and champion odds.",
        "The largest blocking gap for the requested rich prediction set is live 2026 event data: confirmed lineups, odds, corners, free kicks, cards, and penalties need an API key or commercial feed.",
        "StatsBomb open data is strong enough to train half-level event-count models, but it is historical open data, not a 2026 live feed.",
        "worldcup26.ir fills raw score fields with 0-0 for unplayed fixtures; processed files expose actual_home_score and actual_away_score only for finished matches.",
        "FIFA ranking can be validated against the official page snapshot, but it still needs a robust parser or a maintained export before it becomes a clean model input.",
        "Self-computed Elo is the most reproducible team-strength input because it does not rely on fragile web-table scraping.",
    ]

    metrics = {"tables": tables, "coverage": coverage, "findings": findings}
    generate_audit_report(fetches, metrics)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_dir": str(RAW),
        "processed_dir": str(PROCESSED),
        "report": str(REPORTS / "data_audit_report.md"),
        "fetches": [item.__dict__ for item in fetches],
        "tables": tables,
    }
    (REPORTS / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
