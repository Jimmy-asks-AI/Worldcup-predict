from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .aliases import normalize_team
from .data import DEFAULT_DATA_DIR, read_csv


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAYER_PERFORMANCE_FILE = ROOT / "inputs" / "player_performance" / "player_match_performance.csv"
DEFAULT_MATCH_CONTEXT_DIR = ROOT / "inputs" / "match_context"
DEFAULT_WEATHER_FILE = DEFAULT_MATCH_CONTEXT_DIR / "weather_forecast.csv"
DEFAULT_TRAVEL_FILE = DEFAULT_MATCH_CONTEXT_DIR / "team_travel_fatigue.csv"
DEFAULT_TACTICS_FILE = DEFAULT_MATCH_CONTEXT_DIR / "tactics.csv"
DEFAULT_REFEREE_FILE = DEFAULT_MATCH_CONTEXT_DIR / "referees.csv"


@dataclass(frozen=True)
class TeamContextSnapshot:
    team: str
    match_id: str = ""
    player_performance_rows: int = 0
    travel_rows: int = 0
    tactics_rows: int = 0
    attack_multiplier: float = 1.0
    defense_multiplier: float = 1.0
    fatigue_multiplier: float = 1.0
    player_attack_multiplier: float = 1.0
    player_defense_multiplier: float = 1.0
    tactic_attack_multiplier: float = 1.0
    tactic_defense_multiplier: float = 1.0
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MatchContextAdjustment:
    match_id: str
    home_team: str
    away_team: str
    lambda_home_multiplier: float
    lambda_away_multiplier: float
    total_goals_multiplier: float = 1.0
    discipline_index: float = 1.0
    set_piece_index: float = 1.0
    home_context: TeamContextSnapshot = field(default_factory=lambda: TeamContextSnapshot(team=""))
    away_context: TeamContextSnapshot = field(default_factory=lambda: TeamContextSnapshot(team=""))
    weather_context: dict[str, object] = field(default_factory=dict)
    referee_context: dict[str, object] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _key(value: object) -> str:
    return _clean(value).lower().replace(" ", "_").replace("-", "_")


def _num(row: dict[str, str], *names: str, default: float | None = None) -> float | None:
    for name in names:
        text = _clean(row.get(name))
        if not text:
            continue
        try:
            return float(text)
        except ValueError:
            continue
    return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _parse_dt(value: str) -> datetime | None:
    text = _clean(value)
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


class MatchContextAgent:
    """Optional non-odds match context that changes goal lambdas when data exists."""

    def __init__(
        self,
        player_performance_file: Path | str | None = None,
        weather_file: Path | str | None = None,
        travel_file: Path | str | None = None,
        tactics_file: Path | str | None = None,
        referee_file: Path | str | None = None,
        data_dir: Path | str = DEFAULT_DATA_DIR,
    ):
        self.data_dir = Path(data_dir)
        self.player_rows = self._load_optional(player_performance_file)
        self.weather_rows = self._load_optional(weather_file)
        self.travel_rows = self._load_optional(travel_file)
        self.tactics_rows = self._load_optional(tactics_file)
        self.referee_rows = self._load_optional(referee_file)
        self.fixture_by_id = self._load_fixtures()
        self.stadium_aliases = self._load_stadium_aliases()

    @property
    def enabled(self) -> bool:
        return any([self.player_rows, self.weather_rows, self.travel_rows, self.tactics_rows, self.referee_rows])

    @staticmethod
    def _load_optional(path: Path | str | None) -> list[dict[str, str]]:
        if not path:
            return []
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"Context input file not found: {source}")
        return read_csv(source)

    def _load_fixtures(self) -> dict[str, dict[str, str]]:
        path = self.data_dir / "fixtures_2026.csv"
        if not path.exists():
            return {}
        return {row.get("match_id", ""): row for row in read_csv(path) if row.get("match_id")}

    def _load_stadium_aliases(self) -> dict[str, set[str]]:
        path = self.data_dir / "stadiums_2026.csv"
        aliases: dict[str, set[str]] = {}
        if not path.exists():
            return aliases
        for row in read_csv(path):
            names = {_clean(row.get("stadium_name")), _clean(row.get("fifa_name"))}
            names = {name for name in names if name}
            for name in names:
                aliases.setdefault(_key(name), set()).update({_key(item) for item in names})
        return aliases

    def match_adjustment(self, home: str, away: str, match_id: str = "") -> MatchContextAdjustment:
        home = normalize_team(home)
        away = normalize_team(away)
        fixture = self.fixture_by_id.get(str(match_id), {})
        home_context = self._team_context(home, str(match_id))
        away_context = self._team_context(away, str(match_id))
        weather_context = self._weather_context(str(match_id), fixture)
        referee_context = self._referee_context(str(match_id))

        total_goals_multiplier = _clamp(
            float(weather_context["total_goals_multiplier"]) * float(referee_context["total_goals_multiplier"]),
            0.82,
            1.16,
        )
        lambda_home_multiplier = _clamp(
            total_goals_multiplier * home_context.attack_multiplier / away_context.defense_multiplier,
            0.62,
            1.55,
        )
        lambda_away_multiplier = _clamp(
            total_goals_multiplier * away_context.attack_multiplier / home_context.defense_multiplier,
            0.62,
            1.55,
        )
        warnings = home_context.warnings + away_context.warnings
        warnings.extend(weather_context.get("warnings", []))
        warnings.extend(referee_context.get("warnings", []))
        evidence = [
            f"context total goals multiplier {total_goals_multiplier:.3f}",
            f"{home} context attack {home_context.attack_multiplier:.3f} vs {away} defense {away_context.defense_multiplier:.3f}",
            f"{away} context attack {away_context.attack_multiplier:.3f} vs {home} defense {home_context.defense_multiplier:.3f}",
        ]
        evidence.extend(weather_context.get("evidence", []))
        evidence.extend(referee_context.get("evidence", []))
        return MatchContextAdjustment(
            match_id=str(match_id),
            home_team=home,
            away_team=away,
            lambda_home_multiplier=round(lambda_home_multiplier, 4),
            lambda_away_multiplier=round(lambda_away_multiplier, 4),
            total_goals_multiplier=round(total_goals_multiplier, 4),
            discipline_index=round(float(referee_context["discipline_index"]), 4),
            set_piece_index=round(float(weather_context["set_piece_index"]) * float(referee_context["set_piece_index"]), 4),
            home_context=home_context,
            away_context=away_context,
            weather_context={key: value for key, value in weather_context.items() if key not in {"warnings", "evidence"}},
            referee_context={key: value for key, value in referee_context.items() if key not in {"warnings", "evidence"}},
            evidence=evidence,
            warnings=warnings,
        )

    def _team_context(self, team: str, match_id: str) -> TeamContextSnapshot:
        performance = self._player_performance_context(team, match_id)
        travel = self._travel_context(team, match_id)
        tactics = self._tactics_context(team, match_id)
        fatigue_multiplier = travel["fatigue_multiplier"]
        attack_multiplier = _clamp(
            performance["attack_multiplier"] * tactics["attack_multiplier"] * fatigue_multiplier,
            0.78,
            1.28,
        )
        defense_multiplier = _clamp(
            performance["defense_multiplier"] * tactics["defense_multiplier"] * (1.0 - (1.0 - fatigue_multiplier) * 0.70),
            0.78,
            1.28,
        )
        evidence = performance["evidence"] + travel["evidence"] + tactics["evidence"]
        warnings = performance["warnings"] + travel["warnings"] + tactics["warnings"]
        return TeamContextSnapshot(
            team=team,
            match_id=match_id,
            player_performance_rows=performance["rows"],
            travel_rows=travel["rows"],
            tactics_rows=tactics["rows"],
            attack_multiplier=round(attack_multiplier, 4),
            defense_multiplier=round(defense_multiplier, 4),
            fatigue_multiplier=round(fatigue_multiplier, 4),
            player_attack_multiplier=round(performance["attack_multiplier"], 4),
            player_defense_multiplier=round(performance["defense_multiplier"], 4),
            tactic_attack_multiplier=round(tactics["attack_multiplier"], 4),
            tactic_defense_multiplier=round(tactics["defense_multiplier"], 4),
            evidence=evidence,
            warnings=warnings,
        )

    def _team_rows(self, rows: list[dict[str, str]], team: str, match_id: str) -> list[dict[str, str]]:
        team = normalize_team(team)
        selected = []
        for row in rows:
            row_team = row.get("national_team") or row.get("team")
            if normalize_team(row_team) != team:
                continue
            row_match = _clean(row.get("match_id"))
            if row_match and row_match != match_id:
                continue
            selected.append(row)
        return selected

    def _player_performance_context(self, team: str, match_id: str) -> dict[str, object]:
        rows = self._team_rows(self.player_rows, team, match_id)
        if not rows:
            return {
                "rows": 0,
                "attack_multiplier": 1.0,
                "defense_multiplier": 1.0,
                "evidence": [f"{team} has no player-performance rows; neutral player form"],
                "warnings": [],
            }

        attack_sum = defense_sum = discipline_sum = minutes_sum = 0.0
        rating_sum = rating_weight = 0.0
        club_rows = national_rows = 0
        for row in rows:
            minutes = _num(row, "minutes", default=0.0) or 0.0
            if minutes <= 0:
                continue
            row_weight = 0.70 if _key(row.get("team_type")) == "club" else 1.0
            if _key(row.get("team_type")) == "club":
                club_rows += 1
            else:
                national_rows += 1
            weighted_minutes = minutes * row_weight
            attack_events = (
                0.90 * (_num(row, "goals", default=0.0) or 0.0)
                + 0.70 * (_num(row, "assists", default=0.0) or 0.0)
                + 0.60 * (_num(row, "xg", default=0.0) or 0.0)
                + 0.40 * (_num(row, "xa", default=0.0) or 0.0)
                + 0.08 * (_num(row, "shots_on_target", default=0.0) or 0.0)
                + 0.05 * (_num(row, "key_passes", default=0.0) or 0.0)
                + 0.03 * (_num(row, "touches_box", default=0.0) or 0.0)
            )
            defense_events = (
                0.12 * (_num(row, "tackles", default=0.0) or 0.0)
                + 0.12 * (_num(row, "interceptions", default=0.0) or 0.0)
                + 0.10 * (_num(row, "blocks", default=0.0) or 0.0)
                + 0.08 * (_num(row, "clearances", default=0.0) or 0.0)
                + 0.06 * (_num(row, "aerial_duels_won", default=0.0) or 0.0)
                + 0.04 * (_num(row, "duels_won", default=0.0) or 0.0)
                + 0.08 * (_num(row, "keeper_saves", default=0.0) or 0.0)
            )
            discipline_events = (
                (_num(row, "yellow_cards", default=0.0) or 0.0)
                + 2.5 * (_num(row, "red_cards", default=0.0) or 0.0)
            )
            attack_sum += attack_events * row_weight
            defense_sum += defense_events * row_weight
            discipline_sum += discipline_events * row_weight
            minutes_sum += weighted_minutes
            rating = _num(row, "match_rating", default=None)
            if rating is not None:
                rating_sum += rating * weighted_minutes
                rating_weight += weighted_minutes

        if minutes_sum <= 0:
            return {
                "rows": len(rows),
                "attack_multiplier": 1.0,
                "defense_multiplier": 1.0,
                "evidence": [f"{team} player-performance rows have no usable minutes"],
                "warnings": [f"{team} player-performance rows found but no minutes; neutral player form"],
            }

        attack_per90 = attack_sum / minutes_sum * 90.0
        defense_per90 = defense_sum / minutes_sum * 90.0
        discipline_per90 = discipline_sum / minutes_sum * 90.0
        rating_avg = rating_sum / rating_weight if rating_weight else None
        rating_attack = ((rating_avg - 6.8) * 0.025) if rating_avg is not None else 0.0
        rating_defense = ((rating_avg - 6.8) * 0.018) if rating_avg is not None else 0.0
        attack_delta = _clamp((attack_per90 - 0.65) * 0.050 + rating_attack - discipline_per90 * 0.006, -0.10, 0.10)
        defense_delta = _clamp((defense_per90 - 1.40) * 0.035 + rating_defense - discipline_per90 * 0.004, -0.10, 0.10)
        warnings = []
        if minutes_sum < 900:
            warnings.append(f"{team} player-performance sample has only {minutes_sum:.0f} weighted minutes")
        evidence = [
            f"{team} player rows={len(rows)} national={national_rows} club={club_rows}",
            f"{team} player attack_per90={attack_per90:.3f}, defense_per90={defense_per90:.3f}",
        ]
        if rating_avg is not None:
            evidence.append(f"{team} player match_rating_avg={rating_avg:.3f}")
        return {
            "rows": len(rows),
            "attack_multiplier": _clamp(1.0 + attack_delta, 0.90, 1.10),
            "defense_multiplier": _clamp(1.0 + defense_delta, 0.90, 1.10),
            "evidence": evidence,
            "warnings": warnings,
        }

    def _travel_context(self, team: str, match_id: str) -> dict[str, object]:
        rows = self._team_rows(self.travel_rows, team, match_id)
        if not rows:
            return {"rows": 0, "fatigue_multiplier": 1.0, "evidence": [], "warnings": []}
        row = rows[-1]
        travel_km = _num(row, "travel_km", "distance_km", default=0.0) or 0.0
        rest_days = _num(row, "rest_days", default=5.0)
        timezone_shift = abs(_num(row, "timezone_shift_hours", default=0.0) or 0.0)
        disruption = _clamp(_num(row, "training_disruption_score", default=0.0) or 0.0, 0.0, 1.0)
        rest_penalty = max(0.0, 5.0 - (rest_days if rest_days is not None else 5.0)) * 0.018
        penalty = min(0.14, travel_km / 10000.0 * 0.035 + timezone_shift / 8.0 * 0.025 + rest_penalty + disruption * 0.040)
        return {
            "rows": len(rows),
            "fatigue_multiplier": _clamp(1.0 - penalty, 0.86, 1.02),
            "evidence": [f"{team} travel_km={travel_km:.0f}, rest_days={rest_days}, timezone_shift={timezone_shift:.1f}"],
            "warnings": [],
        }

    def _tactics_context(self, team: str, match_id: str) -> dict[str, object]:
        rows = self._team_rows(self.tactics_rows, team, match_id)
        if not rows:
            return {"rows": 0, "attack_multiplier": 1.0, "defense_multiplier": 1.0, "evidence": [], "warnings": []}
        row = rows[-1]

        def score(name: str, default: float = 50.0) -> float:
            return _clamp(_num(row, name, default=default) or default, 0.0, 100.0)

        pressing = score("pressing_intensity")
        width = score("attacking_width")
        set_piece = score("set_piece_strength")
        counter = score("counter_attack_threat")
        line_height = score("defensive_line_height")
        possession = score("possession_bias")
        attack_delta = (
            (pressing - 50.0) * 0.0007
            + (width - 50.0) * 0.0005
            + (set_piece - 50.0) * 0.0008
            + (counter - 50.0) * 0.0008
            + (possession - 50.0) * 0.0004
        )
        defense_delta = (50.0 - line_height) * 0.0007 + (pressing - 50.0) * 0.0004 - max(0.0, width - 70.0) * 0.0005
        return {
            "rows": len(rows),
            "attack_multiplier": _clamp(1.0 + attack_delta, 0.92, 1.08),
            "defense_multiplier": _clamp(1.0 + defense_delta, 0.92, 1.08),
            "evidence": [
                f"{team} formation={_clean(row.get('formation')) or 'unknown'} pressing={pressing:.0f} set_piece={set_piece:.0f}"
            ],
            "warnings": [],
        }

    def _weather_context(self, match_id: str, fixture: dict[str, str]) -> dict[str, object]:
        row, warning = self._select_weather_row(match_id, fixture)
        if not row:
            return {
                "rows": 0,
                "total_goals_multiplier": 1.0,
                "set_piece_index": 1.0,
                "evidence": [],
                "warnings": [warning] if warning else [],
            }
        temp = _num(row, "temperature_c", "temperature_2m", default=20.0) or 20.0
        humidity = _num(row, "humidity_pct", "relative_humidity_2m", default=55.0) or 55.0
        precipitation = _num(row, "precipitation_mm", "precipitation", default=0.0) or 0.0
        wind = _num(row, "wind_kph", "wind_speed_10m", default=0.0) or 0.0
        heat_penalty = max(0.0, temp - 28.0) * 0.006
        cold_penalty = max(0.0, 4.0 - temp) * 0.004
        rain_penalty = min(0.055, precipitation * 0.012)
        wind_penalty = max(0.0, wind - 22.0) * 0.004
        humidity_penalty = max(0.0, humidity - 80.0) * 0.001
        total = _clamp(1.0 - heat_penalty - cold_penalty - rain_penalty - wind_penalty - humidity_penalty, 0.86, 1.05)
        set_piece = _clamp(1.0 + min(0.08, precipitation * 0.010 + max(0.0, wind - 18.0) * 0.004), 0.96, 1.10)
        warnings = [warning] if warning else []
        basis = _key(row.get("weather_basis"))
        if basis and basis not in {"kickoff_forecast", "observed_pre_match", "official_forecast"}:
            warnings.append(f"weather row basis is {row.get('weather_basis')}; refresh exact kickoff forecast when available")
        return {
            "rows": 1,
            "stadium": row.get("stadium", fixture.get("stadium", "")),
            "time_utc": row.get("time_utc", ""),
            "weather_basis": row.get("weather_basis", ""),
            "temperature_c": round(temp, 2),
            "humidity_pct": round(humidity, 2),
            "precipitation_mm": round(precipitation, 3),
            "wind_kph": round(wind, 2),
            "total_goals_multiplier": total,
            "set_piece_index": set_piece,
            "evidence": [f"weather temp={temp:.1f}C rain={precipitation:.2f} wind={wind:.1f}kph"],
            "warnings": warnings,
        }

    def _select_weather_row(self, match_id: str, fixture: dict[str, str]) -> tuple[dict[str, str] | None, str]:
        if not self.weather_rows:
            return None, ""
        by_match = [row for row in self.weather_rows if _clean(row.get("match_id")) == match_id]
        if by_match:
            return by_match[-1], ""
        stadium = _key(fixture.get("stadium"))
        aliases = self.stadium_aliases.get(stadium, {stadium}) if stadium else set()
        candidates = [row for row in self.weather_rows if _key(row.get("stadium")) in aliases]
        if not candidates:
            return None, f"no weather row matched match_id={match_id} stadium={fixture.get('stadium', '')}"
        kickoff = _parse_dt(fixture.get("kickoff_utc", ""))
        if not kickoff:
            return candidates[-1], "weather matched by stadium without kickoff timestamp"
        with_dt = [(row, _parse_dt(row.get("time_utc", ""))) for row in candidates]
        with_dt = [(row, dt) for row, dt in with_dt if dt is not None]
        if not with_dt:
            return candidates[-1], "weather matched by stadium without comparable weather timestamp"
        row, dt = min(with_dt, key=lambda item: abs((item[1] - kickoff).total_seconds()))
        hour_gap = abs((dt - kickoff).total_seconds()) / 3600.0
        warning = f"weather nearest timestamp is {hour_gap:.1f} hours from kickoff" if hour_gap > 6 else ""
        return row, warning

    def _referee_context(self, match_id: str) -> dict[str, object]:
        rows = [row for row in self.referee_rows if _clean(row.get("match_id")) in {"", match_id}]
        if not rows:
            return {
                "rows": 0,
                "total_goals_multiplier": 1.0,
                "discipline_index": 1.0,
                "set_piece_index": 1.0,
                "evidence": [],
                "warnings": [],
            }
        row = rows[-1]
        cards = _num(row, "cards_per_match", default=4.0) or 4.0
        reds = _num(row, "red_cards_per_match", default=0.15) or 0.15
        fouls = _num(row, "fouls_per_match", default=25.0) or 25.0
        penalties = _num(row, "penalties_per_match", default=0.25) or 0.25
        goal_delta = _clamp((penalties - 0.25) * 0.060 - max(0.0, cards - 4.5) * 0.008 - max(0.0, reds - 0.25) * 0.020, -0.05, 0.06)
        discipline_index = _clamp(1.0 + (cards - 4.0) * 0.050 + (reds - 0.15) * 0.30, 0.75, 1.45)
        set_piece_index = _clamp(1.0 + (fouls - 25.0) * 0.008, 0.88, 1.18)
        return {
            "rows": len(rows),
            "referee": row.get("referee", ""),
            "cards_per_match": cards,
            "red_cards_per_match": reds,
            "fouls_per_match": fouls,
            "penalties_per_match": penalties,
            "total_goals_multiplier": 1.0 + goal_delta,
            "discipline_index": discipline_index,
            "set_piece_index": set_piece_index,
            "evidence": [f"referee={row.get('referee', '') or 'unknown'} cards={cards:.2f} penalties={penalties:.2f}"],
            "warnings": [],
        }
