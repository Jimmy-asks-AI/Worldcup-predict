from __future__ import annotations

import csv
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
RAW = WORKSPACE_ROOT / "worldcup_data_audit" / "data" / "raw"
PROCESSED = WORKSPACE_ROOT / "worldcup_data_audit" / "data" / "processed"
INPUTS = WORKSPACE_ROOT / "inputs" / "match_context"
REPORTS = WORKSPACE_ROOT / "outputs" / "reports"
FIFA_RANKING_URL = "https://api.fifa.com/api/v3/rankings/?gender=1&count=300&language=en"

MANUAL_COORD_FALLBACKS = {
    "metlife stadium": ("40.8135", "-74.0745"),
    "new york/new jersey stadium": ("40.8135", "-74.0745"),
    "bc place": ("49.2768", "-123.1119"),
    "bc place vancouver": ("49.2768", "-123.1119"),
}


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


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def fetch_json(url: str, cache_path: Path) -> dict:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "worldcup-predictor/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
        cache_path.write_text(payload, encoding="utf-8")
        return json.loads(payload)
    except Exception:
        if cache_path.exists():
            return read_json(cache_path)
        raise


def parse_dt(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    return radius_km * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def timezone_guess(longitude: float) -> int:
    return int(round(longitude / 15.0))


def stadium_lookup() -> dict[str, dict[str, str]]:
    rows = read_csv(PROCESSED / "stadiums_2026.csv")
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        for key in (row.get("stadium_name", ""), row.get("fifa_name", "")):
            if key:
                fallback = MANUAL_COORD_FALLBACKS.get(key.strip().lower())
                if fallback and (not row.get("latitude") or not row.get("longitude")):
                    row = {**row, "latitude": fallback[0], "longitude": fallback[1]}
                out[key.strip().lower()] = row
                if "arrowhead" in key.strip().lower():
                    out["arrowhead stadium"] = row
    return out


def build_travel_rows() -> list[dict[str, str]]:
    fixtures = [row for row in read_csv(PROCESSED / "fixtures_2026.csv") if row.get("stage") == "group-stage"]
    stadiums = stadium_lookup()
    by_team: dict[str, list[dict[str, str]]] = {}
    for fixture in fixtures:
        kickoff = parse_dt(fixture.get("kickoff_utc", ""))
        if not kickoff:
            continue
        stadium = stadiums.get((fixture.get("stadium") or "").strip().lower())
        if not stadium:
            continue
        for side in ("home_team", "away_team"):
            row = dict(fixture)
            row["team"] = fixture[side]
            row["kickoff_dt"] = kickoff.isoformat()
            row["latitude"] = stadium.get("latitude", "")
            row["longitude"] = stadium.get("longitude", "")
            row["stadium_name"] = stadium.get("stadium_name", fixture.get("stadium", ""))
            by_team.setdefault(fixture[side], []).append(row)

    out = []
    for team, matches in by_team.items():
        matches.sort(key=lambda item: item["kickoff_dt"])
        previous = None
        for fixture in matches:
            kickoff = parse_dt(fixture["kickoff_dt"])
            lat = float(fixture["latitude"])
            lon = float(fixture["longitude"])
            if previous is None:
                travel_km = 0.0
                rest_days = 7.0
                timezone_shift = 0.0
                notes = "first group match; previous venue unknown, neutral travel baseline"
            else:
                prev_kickoff = parse_dt(previous["kickoff_dt"])
                prev_lat = float(previous["latitude"])
                prev_lon = float(previous["longitude"])
                travel_km = haversine_km(prev_lat, prev_lon, lat, lon)
                rest_days = (kickoff - prev_kickoff).total_seconds() / 86400.0 if kickoff and prev_kickoff else 5.0
                timezone_shift = abs(timezone_guess(lon) - timezone_guess(prev_lon))
                notes = f"derived from previous venue {previous['stadium_name']} to {fixture['stadium_name']}"
            disruption = min(1.0, max(0.0, travel_km / 5000.0 * 0.55 + max(0.0, 4.0 - rest_days) / 4.0 * 0.45))
            out.append(
                {
                    "match_id": fixture["match_id"],
                    "team": team,
                    "source": "derived_fixture_venue_sequence",
                    "source_timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "travel_km": f"{travel_km:.1f}",
                    "rest_days": f"{rest_days:.2f}",
                    "timezone_shift_hours": f"{timezone_shift:.1f}",
                    "training_disruption_score": f"{disruption:.3f}",
                    "fatigue_basis": "fixture_sequence_and_stadium_coordinates",
                    "notes": notes,
                }
            )
            previous = fixture
    out.sort(key=lambda row: (int(row["match_id"]), row["team"]))
    return out


def to_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except ValueError:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def localized_name(values: list[dict] | None) -> str:
    if not values:
        return ""
    for item in values:
        if item.get("Locale") == "en-GB" and item.get("Description"):
            return item["Description"]
    return values[0].get("Description", "")


def build_fifa_ranking_rows() -> list[dict[str, str]]:
    teams = {
        row["fifa_code"]: row["team_name"]
        for row in read_csv(PROCESSED / "teams_2026.csv")
        if row.get("fifa_code") and row.get("team_name")
    }
    raw = fetch_json(FIFA_RANKING_URL, RAW / "fifa_rankings_men_latest.json")
    rows = []
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for item in raw.get("Results", []):
        code = item.get("IdCountry", "")
        team_name = teams.get(code, localized_name(item.get("TeamName")))
        if not team_name:
            continue
        rows.append(
            {
                "team": team_name,
                "fifa_code": code,
                "fifa_rank": item.get("Rank", ""),
                "fifa_previous_rank": item.get("PrevRank", ""),
                "fifa_points": item.get("DecimalTotalPoints", item.get("TotalPoints", "")),
                "fifa_previous_points": item.get("DecimalPrevPoints", item.get("PrevPoints", "")),
                "confederation": item.get("ConfederationName", ""),
                "ranking_schedule_id": item.get("IdSchedule", ""),
                "published_at": item.get("PubDate", ""),
                "previous_published_at": item.get("PrePubDate", ""),
                "source": "fifa_official_rankings_api",
                "source_url": FIFA_RANKING_URL,
                "source_timestamp": timestamp,
                "is_2026_team": "TRUE" if code in teams else "FALSE",
            }
        )
    rows.sort(key=lambda row: int(row["fifa_rank"]) if str(row.get("fifa_rank", "")).isdigit() else 9999)
    return rows


def build_tactics_rows() -> list[dict[str, str]]:
    form_rows = {row["team"]: row for row in read_csv(PROCESSED / "derived_recent_form.csv") if row.get("team")}
    elo_rows = {row["team"]: row for row in read_csv(PROCESSED / "derived_elo_snapshot.csv") if row.get("team")}
    teams = [row["team_name"] for row in read_csv(PROCESSED / "teams_2026.csv") if row.get("team_name")]
    rows = []
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for team in sorted(teams):
        form = form_rows.get(team, {})
        elo = elo_rows.get(team, {})
        gf = to_float(form.get("recent_goals_for_per_match"), 1.25)
        ga = to_float(form.get("recent_goals_against_per_match"), 1.25)
        ppg = to_float(form.get("recent_points_per_match"), 1.35)
        rating = to_float(elo.get("elo"), 1500.0)
        strength = clamp((rating - 1500.0) / 350.0, -1.0, 1.0)
        attack = clamp((gf - 1.25) / 1.25, -1.0, 1.0)
        defense = clamp((1.25 - ga) / 1.25, -1.0, 1.0)
        pressing = clamp(50.0 + 13.0 * strength + 8.0 * (ppg - 1.35), 25.0, 82.0)
        width = clamp(50.0 + 15.0 * attack, 30.0, 75.0)
        set_piece = clamp(50.0 + 8.0 * strength + 6.0 * defense, 30.0, 75.0)
        counter = clamp(50.0 + 10.0 * attack - 4.0 * strength, 30.0, 78.0)
        line_height = clamp(50.0 + 10.0 * strength - 8.0 * defense, 28.0, 78.0)
        possession = clamp(50.0 + 16.0 * strength + 6.0 * attack, 25.0, 85.0)
        rows.append(
            {
                "match_id": "",
                "team": team,
                "source": "derived_recent_form_elo_style_prior",
                "source_timestamp": timestamp,
                "formation": "style-prior",
                "pressing_intensity": f"{pressing:.1f}",
                "attacking_width": f"{width:.1f}",
                "set_piece_strength": f"{set_piece:.1f}",
                "counter_attack_threat": f"{counter:.1f}",
                "defensive_line_height": f"{line_height:.1f}",
                "possession_bias": f"{possession:.1f}",
                "style_basis": "derived_from_recent_goals_recent_points_and_elo",
                "notes": "team style prior; replace with confirmed tactical scouting when available",
            }
        )
    return rows


def build_referee_prior_rows() -> list[dict[str, str]]:
    half_rows = read_csv(PROCESSED / "statsbomb_event_half_team_summary.csv")
    if not half_rows:
        return []
    match_ids = sorted({row.get("match_id", "") for row in half_rows if row.get("match_id")})
    match_count = max(1, len(match_ids))
    cards = sum(to_float(row.get("yellow_cards")) for row in half_rows)
    reds = sum(to_float(row.get("red_cards")) for row in half_rows)
    fouls = sum(to_float(row.get("fouls_committed")) for row in half_rows)
    penalties = sum(to_float(row.get("penalty_shots")) for row in half_rows)
    return [
        {
            "match_id": "",
            "referee": "global_worldcup_event_prior",
            "source": "statsbomb_open_data_event_sample",
            "source_timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "cards_per_match": f"{cards / match_count:.3f}",
            "red_cards_per_match": f"{reds / match_count:.3f}",
            "fouls_per_match": f"{fouls / match_count:.3f}",
            "penalties_per_match": f"{penalties / match_count:.3f}",
            "home_bias_index": "0",
            "strictness_basis": "global_prior_from_statsbomb_worldcup_event_sample",
            "notes": "global prior only; replace with assigned referee history once known",
        }
    ]


def build_player_performance_contract_rows() -> list[dict[str, str]]:
    source = PROCESSED / "statsbomb_player_match_performance_sample.csv"
    if not source.exists():
        return []
    source_rows = read_csv(source)
    teams = {row["team_name"] for row in read_csv(PROCESSED / "teams_2026.csv") if row.get("team_name")}
    rows = []
    for row in source_rows:
        team = row.get("team", "")
        if team not in teams:
            continue
        rows.append(
            {
                "snapshot_date": row.get("snapshot_date", ""),
                "match_id": "",
                "match_date": row.get("match_date", ""),
                "source": row.get("source", "statsbomb_open_data"),
                "source_timestamp": row.get("source_timestamp", ""),
                "player_id": row.get("player_id", ""),
                "player_name": row.get("player_name", ""),
                "national_team": team,
                "team": team,
                "club": "",
                "team_type": row.get("team_type", "national"),
                "competition": row.get("competition", ""),
                "opponent": row.get("opponent", ""),
                "home_away_neutral": row.get("home_away_neutral", ""),
                "position": row.get("position", ""),
                "minutes": row.get("minutes", ""),
                "started": row.get("started", ""),
                "goals": row.get("goals", ""),
                "assists": row.get("assists", ""),
                "xg": row.get("xg", ""),
                "xa": row.get("xa", ""),
                "shots": row.get("shots", ""),
                "shots_on_target": row.get("shots_on_target", ""),
                "key_passes": row.get("key_passes", ""),
                "progressive_passes": row.get("progressive_passes", ""),
                "progressive_carries": row.get("progressive_carries", ""),
                "touches_box": row.get("touches_box", ""),
                "pressures": row.get("pressures", ""),
                "tackles": row.get("tackles", ""),
                "interceptions": row.get("interceptions", ""),
                "blocks": row.get("blocks", ""),
                "clearances": row.get("clearances", ""),
                "aerial_duels_won": row.get("aerial_duels_won", ""),
                "duels_won": row.get("duels_won", ""),
                "yellow_cards": row.get("yellow_cards", ""),
                "red_cards": row.get("red_cards", ""),
                "keeper_saves": row.get("keeper_saves", ""),
                "keeper_goals_prevented": row.get("keeper_goals_prevented", ""),
                "match_rating": row.get("match_rating", ""),
                "rating_basis": row.get("rating_basis", "historical_event_counts_snapshot"),
            }
        )
    return rows


def build_weather_rows_from_sample() -> list[dict[str, str]]:
    sample_path = PROCESSED / "weather_hourly_sample.csv"
    if not sample_path.exists():
        return []
    sample_rows = read_csv(sample_path)
    if not sample_rows:
        return []
    stadium_samples: dict[str, list[dict[str, str]]] = {}
    for row in sample_rows:
        stadium_samples.setdefault((row.get("stadium") or "").strip().lower(), []).append(row)
    aliases = stadium_lookup()
    fields = []
    for fixture in read_csv(PROCESSED / "fixtures_2026.csv"):
        stadium = (fixture.get("stadium") or "").strip().lower()
        stadium_row = aliases.get(stadium)
        possible_names = [stadium]
        if stadium_row:
            possible_names.extend(
                [
                    (stadium_row.get("stadium_name") or "").strip().lower(),
                    (stadium_row.get("fifa_name") or "").strip().lower(),
                ]
            )
        candidates = []
        for name in possible_names:
            candidates.extend(stadium_samples.get(name, []))
        if not candidates:
            continue
        sample = candidates[0]
        fields.append(
            {
                "match_id": fixture.get("match_id", ""),
                "stadium": fixture.get("stadium", ""),
                "time_utc": fixture.get("kickoff_utc", ""),
                "source": "open_meteo_hourly_sample_reused_by_stadium",
                "source_timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "temperature_c": sample.get("temperature_2m", ""),
                "humidity_pct": sample.get("relative_humidity_2m", ""),
                "precipitation_mm": sample.get("precipitation", ""),
                "wind_kph": sample.get("wind_speed_10m", ""),
                "weather_basis": "stadium_sample_not_exact_kickoff_forecast",
                "notes": f"sample source time {sample.get('time_utc', '')}; refresh close to kickoff",
            }
        )
    fields.sort(key=lambda row: int(row["match_id"]))
    return fields


def main() -> int:
    fifa_ranking_fields = [
        "team",
        "fifa_code",
        "fifa_rank",
        "fifa_previous_rank",
        "fifa_points",
        "fifa_previous_points",
        "confederation",
        "ranking_schedule_id",
        "published_at",
        "previous_published_at",
        "source",
        "source_url",
        "source_timestamp",
        "is_2026_team",
    ]
    fifa_ranking_rows = build_fifa_ranking_rows()
    write_csv(PROCESSED / "fifa_ranking_snapshot.csv", fifa_ranking_rows, fifa_ranking_fields)
    travel_fields = [
        "match_id",
        "team",
        "source",
        "source_timestamp",
        "travel_km",
        "rest_days",
        "timezone_shift_hours",
        "training_disruption_score",
        "fatigue_basis",
        "notes",
    ]
    travel_rows = build_travel_rows()
    write_csv(INPUTS / "team_travel_fatigue.csv", travel_rows, travel_fields)
    tactic_fields = [
        "match_id",
        "team",
        "source",
        "source_timestamp",
        "formation",
        "pressing_intensity",
        "attacking_width",
        "set_piece_strength",
        "counter_attack_threat",
        "defensive_line_height",
        "possession_bias",
        "style_basis",
        "notes",
    ]
    tactic_rows = build_tactics_rows()
    write_csv(INPUTS / "tactics.csv", tactic_rows, tactic_fields)
    referee_fields = [
        "match_id",
        "referee",
        "source",
        "source_timestamp",
        "cards_per_match",
        "red_cards_per_match",
        "fouls_per_match",
        "penalties_per_match",
        "home_bias_index",
        "strictness_basis",
        "notes",
    ]
    referee_rows = build_referee_prior_rows()
    write_csv(INPUTS / "referees.csv", referee_rows, referee_fields)
    weather_fields = [
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
    weather_rows = build_weather_rows_from_sample()
    write_csv(INPUTS / "weather_forecast.csv", weather_rows, weather_fields)
    performance_fields = [
        "snapshot_date",
        "match_id",
        "match_date",
        "source",
        "source_timestamp",
        "player_id",
        "player_name",
        "national_team",
        "team",
        "club",
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
    player_rows = build_player_performance_contract_rows()
    performance_path = WORKSPACE_ROOT / "inputs" / "player_performance" / "player_match_performance.csv"
    write_csv(performance_path, player_rows, performance_fields)
    event_half_path = PROCESSED / "statsbomb_event_half_team_summary.csv"
    event_half_rows = read_csv(event_half_path) if event_half_path.exists() else []
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = {
        "team_travel_fatigue_rows": len(travel_rows),
        "tactics_rows": len(tactic_rows),
        "referee_prior_rows": len(referee_rows),
        "weather_rows": len(weather_rows),
        "player_performance_rows": len(player_rows),
        "fifa_ranking_rows": len(fifa_ranking_rows),
        "fifa_ranking_2026_team_rows": len([row for row in fifa_ranking_rows if row.get("is_2026_team") == "TRUE"]),
        "event_half_team_rows": len(event_half_rows),
        "outputs": {
            "fifa_ranking_snapshot": str(PROCESSED / "fifa_ranking_snapshot.csv"),
            "fifa_ranking_raw": str(RAW / "fifa_rankings_men_latest.json"),
            "event_half_team_summary": str(event_half_path),
            "team_travel_fatigue": str(INPUTS / "team_travel_fatigue.csv"),
            "tactics": str(INPUTS / "tactics.csv"),
            "referees": str(INPUTS / "referees.csv"),
            "weather": str(INPUTS / "weather_forecast.csv"),
            "player_performance": str(performance_path),
        },
        "method": "non-odds context from FIFA ranking API plus existing processed fixtures, stadiums, Elo/recent form, Open-Meteo sample, and StatsBomb open-data samples",
        "limitations": [
            "FIFA ranking is a national-team strength prior and can overlap with Elo; model weight is intentionally small.",
            "First match has neutral travel because team base camps are not available.",
            "Knockout travel cannot be known until simulated teams are resolved.",
            "Timezone shift is approximated from longitude.",
            "Tactics are heuristic priors from recent form and Elo, not confirmed coaching plans.",
            "Referee row is a global event-environment prior, not assigned referee history.",
            "Event-count predictions use partial StatsBomb half-team event samples and should be recalibrated with a larger feed.",
            "Weather rows reuse available stadium samples and must be refreshed close to kickoff for real forecasts.",
            "Player performance rows are partial StatsBomb open-data samples, not full club and national-team coverage.",
        ],
    }
    (REPORTS / "non_odds_context_build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
