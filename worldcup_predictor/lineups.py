from __future__ import annotations

from pathlib import Path

from .aliases import normalize_team
from .data import read_csv
from .models import LineupContext, LineupMatchAdjustment
from .ratings import PlayerRatingsAgent


UNAVAILABLE_STATUSES = {"out", "injured", "suspended", "unavailable", "not_available"}
LIMITED_STATUSES = {"limited", "doubtful", "questionable"}
STARTER_ROLES = {"starter", "starting", "start", "xi", "starting_xi", "首发"}
SUBSTITUTE_ROLES = {"sub", "substitute", "bench", "replacement", "替补"}
RESERVE_ROLES = {"reserve", "squad", "unused", "depth"}
PREMATCH_RATING_BASES = {"prematch", "pre_kickoff", "season_average", "projected", "scouted_prematch", "market_pre"}
POSTMATCH_MARKERS = {"postmatch", "post_match", "post_match_rating", "post", "after_match", "final_rating", "live_rating"}

ATTACK_WEIGHTS = {
    "GK": 0.00,
    "G": 0.00,
    "DF": 0.10,
    "CB": 0.05,
    "LB": 0.15,
    "RB": 0.15,
    "WB": 0.25,
    "DM": 0.25,
    "MF": 0.45,
    "CM": 0.45,
    "AM": 0.80,
    "LW": 0.95,
    "RW": 0.95,
    "FW": 1.00,
    "ST": 1.00,
}

DEFENSE_WEIGHTS = {
    "GK": 1.00,
    "G": 1.00,
    "DF": 0.85,
    "CB": 0.90,
    "LB": 0.65,
    "RB": 0.65,
    "WB": 0.50,
    "DM": 0.70,
    "MF": 0.35,
    "CM": 0.35,
    "AM": 0.15,
    "LW": 0.10,
    "RW": 0.10,
    "FW": 0.05,
    "ST": 0.05,
}


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _key(value: str | None) -> str:
    return _clean(value).lower().replace(" ", "_").replace("-", "_")


def _truthy(value: str | None) -> bool:
    return _key(value) in {"1", "true", "yes", "y", "official"}


def _float(value: str | None, default: float | None = None) -> float | None:
    text = _clean(value)
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _position(value: str | None) -> str:
    text = _clean(value).upper()
    if not text:
        return "MF"
    if text in ATTACK_WEIGHTS:
        return text
    if "GK" in text or "GOAL" in text:
        return "GK"
    if "BACK" in text or "DEF" in text:
        return "DF"
    if "MID" in text:
        return "MF"
    if "WING" in text:
        return "LW"
    if "FORWARD" in text or "STRIKER" in text:
        return "FW"
    return "MF"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class LineupAgent:
    """Loads optional match lineup inputs and turns them into lambda multipliers."""

    def __init__(
        self,
        lineup_file: Path | str | None = None,
        pre_kickoff_only: bool = True,
        allowed_sources: set[str] | list[str] | tuple[str, ...] | None = None,
        require_official_starters: bool = True,
        player_ratings_file: Path | str | None = None,
    ):
        self.lineup_file = Path(lineup_file) if lineup_file else None
        self.pre_kickoff_only = pre_kickoff_only
        self.allowed_sources = {_key(item) for item in allowed_sources} if allowed_sources else None
        self.require_official_starters = require_official_starters
        self.player_ratings = PlayerRatingsAgent(player_ratings_file) if player_ratings_file else None
        self.rows: list[dict[str, str]] = []
        if self.lineup_file:
            if not self.lineup_file.exists():
                raise FileNotFoundError(f"Lineup file not found: {self.lineup_file}")
            self.rows = read_csv(self.lineup_file)
            self._validate_rows()

    @property
    def enabled(self) -> bool:
        return bool(self.lineup_file)

    def match_adjustment(self, home: str, away: str, match_id: str = "") -> LineupMatchAdjustment:
        home = normalize_team(home)
        away = normalize_team(away)
        home_context = self.team_context(home, match_id)
        away_context = self.team_context(away, match_id)

        lambda_home_multiplier = _clamp(home_context.attack_multiplier / away_context.defense_multiplier, 0.65, 1.45)
        lambda_away_multiplier = _clamp(away_context.attack_multiplier / home_context.defense_multiplier, 0.65, 1.45)
        evidence = [
            f"{home} attack {home_context.attack_multiplier:.3f} vs {away} defense {away_context.defense_multiplier:.3f}",
            f"{away} attack {away_context.attack_multiplier:.3f} vs {home} defense {home_context.defense_multiplier:.3f}",
        ]
        warnings = home_context.warnings + away_context.warnings
        return LineupMatchAdjustment(
            match_id=match_id,
            home_team=home,
            away_team=away,
            lambda_home_multiplier=round(lambda_home_multiplier, 4),
            lambda_away_multiplier=round(lambda_away_multiplier, 4),
            home_context=home_context,
            away_context=away_context,
            evidence=evidence,
            warnings=warnings,
        )

    def team_context(self, team: str, match_id: str = "") -> LineupContext:
        team = normalize_team(team)
        rows = self._select_rows(team, match_id)
        if not rows:
            return LineupContext(
                team=team,
                match_id=match_id,
                evidence=[f"{team} has no lineup rows; neutral 1.000 multipliers applied"],
                warnings=[f"{team} missing lineup input; no lineup adjustment applied"],
            )

        warnings: list[str] = []
        attack_num = defense_num = 0.0
        attack_den = defense_den = 0.0
        attack_injury_loss = defense_injury_loss = 0.0
        starter_count = substitute_count = unavailable_count = official_starter_count = 0
        bench_minutes = 0.0

        for idx, row in enumerate(rows, 1):
            role = _key(row.get("role"))
            status = _key(row.get("status") or "available")
            position = _position(row.get("position"))
            player = _clean(row.get("player")) or f"row {idx}"
            rating = _float(row.get("rating"), None)
            if rating is None:
                rating, rating_warning = self._rating_from_external_source(row, team, player)
                if rating_warning:
                    warnings.append(rating_warning)
            rating = _clamp(rating, 40.0, 100.0)

            is_unavailable = status in UNAVAILABLE_STATUSES or role in UNAVAILABLE_STATUSES
            is_starter = role in STARTER_ROLES
            is_substitute = role in SUBSTITUTE_ROLES
            if is_starter:
                starter_count += 1
                if _truthy(row.get("official")):
                    official_starter_count += 1
            if is_substitute:
                substitute_count += 1

            minutes = self._expected_minutes(row, role, status)
            if status == "doubtful":
                minutes *= 0.50
            elif status in LIMITED_STATUSES:
                minutes *= 0.75

            attack_weight = ATTACK_WEIGHTS.get(position, 0.45)
            defense_weight = DEFENSE_WEIGHTS.get(position, 0.35)
            if is_unavailable:
                unavailable_count += 1
                lost_minutes = minutes or 90.0
                attack_injury_loss += max(0.0, rating - 75.0) * lost_minutes * attack_weight / 990.0
                defense_injury_loss += max(0.0, rating - 75.0) * lost_minutes * defense_weight / 990.0
                continue

            if is_substitute:
                bench_minutes += minutes
            if minutes <= 0:
                continue

            attack_num += rating * minutes * attack_weight
            attack_den += minutes * attack_weight
            defense_num += rating * minutes * defense_weight
            defense_den += minutes * defense_weight

        attack_rating = attack_num / attack_den if attack_den else 75.0
        defense_rating = defense_num / defense_den if defense_den else 75.0
        attack_delta = (attack_rating - 75.0) - attack_injury_loss
        defense_delta = (defense_rating - 75.0) - defense_injury_loss
        attack_multiplier = _clamp(1.0 + attack_delta / 120.0, 0.75, 1.25)
        defense_multiplier = _clamp(1.0 + defense_delta / 120.0, 0.75, 1.25)

        if starter_count and starter_count != 11:
            warnings.append(f"{team} starter count is {starter_count}, expected 11")
        if starter_count and official_starter_count != starter_count:
            warnings.append(f"{team} lineup is not fully marked official; treating unmarked starters as projected")

        evidence = [
            f"{team} rows={len(rows)}, starters={starter_count}, substitutes={substitute_count}, unavailable={unavailable_count}",
            f"{team} attack_rating={attack_rating:.2f}, defense_rating={defense_rating:.2f}, bench_minutes={bench_minutes:.1f}",
        ]
        sources = sorted({_clean(row.get("source")) for row in rows if _clean(row.get("source"))})
        if sources:
            evidence.append(f"{team} lineup sources: {', '.join(sources[:3])}")
        if self.player_ratings:
            evidence.append(f"{team} missing lineup ratings can be filled from {self.player_ratings.ratings_file}")

        return LineupContext(
            team=team,
            match_id=match_id,
            row_count=len(rows),
            starter_count=starter_count,
            substitute_count=substitute_count,
            unavailable_count=unavailable_count,
            attack_rating=round(attack_rating, 3),
            defense_rating=round(defense_rating, 3),
            attack_multiplier=round(attack_multiplier, 4),
            defense_multiplier=round(defense_multiplier, 4),
            bench_minutes=round(bench_minutes, 1),
            official_starter_count=official_starter_count,
            evidence=evidence,
            warnings=warnings,
        )

    def _select_rows(self, team: str, match_id: str) -> list[dict[str, str]]:
        team = normalize_team(team)
        team_rows = [row for row in self.rows if normalize_team(row.get("team", "")) == team]
        if not match_id:
            return team_rows
        global_rows = [row for row in team_rows if not _clean(row.get("match_id"))]
        match_rows = [row for row in team_rows if _clean(row.get("match_id")) == str(match_id)]
        return global_rows + match_rows if match_rows else global_rows

    def _validate_rows(self) -> None:
        errors: list[str] = []
        for line_no, row in enumerate(self.rows, 2):
            team = _clean(row.get("team")) or "<missing team>"
            player = _clean(row.get("player")) or f"line {line_no}"
            source = _clean(row.get("source"))
            source_key = _key(source)
            role = _key(row.get("role"))
            if not source:
                errors.append(f"line {line_no} {team} {player}: source is required for lineup data")
            if self.allowed_sources is not None and source_key not in self.allowed_sources:
                errors.append(f"line {line_no} {team} {player}: source '{source}' is not whitelisted")
            if self.require_official_starters and role in STARTER_ROLES and not _truthy(row.get("official")):
                errors.append(f"line {line_no} {team} {player}: starter must be marked official=true")
            if self.pre_kickoff_only:
                rating_basis = _key(row.get("rating_basis") or row.get("rating_source") or row.get("basis"))
                has_external_rating_fallback = bool(self.player_ratings and not _clean(row.get("rating")))
                if not rating_basis and not has_external_rating_fallback:
                    errors.append(f"line {line_no} {team} {player}: rating_basis is required in pre-kickoff mode")
                elif rating_basis not in PREMATCH_RATING_BASES:
                    if rating_basis:
                        errors.append(f"line {line_no} {team} {player}: rating_basis '{rating_basis}' is not pre-kickoff safe")
                marker_text = f"{source_key} {rating_basis}"
                if any(marker in marker_text for marker in POSTMATCH_MARKERS):
                    errors.append(f"line {line_no} {team} {player}: post-match/live rating sources are not allowed")
        if errors:
            raise ValueError("Invalid lineup input:\n" + "\n".join(errors[:20]))

    def _rating_from_external_source(self, row: dict[str, str], team: str, player: str) -> tuple[float, str]:
        if not self.player_ratings:
            return 75.0, f"{team} {player} missing rating, fallback 75"
        nationality = _clean(row.get("nationality")) or team
        club = _clean(row.get("club"))
        rating, warning = self.player_ratings.lookup(player, nationality=nationality, club=club)
        if rating is None:
            return 75.0, f"{team} {player} missing rating, fallback 75; player ratings lookup failed: {warning}"
        return rating.overall, f"{team} {player} rating filled from {rating.source}: {rating.overall:.0f}"

    @staticmethod
    def _expected_minutes(row: dict[str, str], role: str, status: str) -> float:
        explicit = _float(row.get("expected_minutes"), None)
        if explicit is not None:
            return _clamp(explicit, 0.0, 120.0)
        sub_minute = _float(row.get("sub_minute"), None)
        if sub_minute is not None:
            return _clamp(90.0 - sub_minute, 0.0, 90.0)
        if status in UNAVAILABLE_STATUSES or role in UNAVAILABLE_STATUSES:
            if role in SUBSTITUTE_ROLES:
                return 25.0
            if role in RESERVE_ROLES:
                return 10.0
            return 90.0
        if role in STARTER_ROLES:
            return 90.0
        if role in SUBSTITUTE_ROLES:
            return 25.0
        return 0.0
