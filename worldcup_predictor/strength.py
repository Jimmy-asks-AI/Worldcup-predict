from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from .aliases import normalize_team
from .data import DEFAULT_DATA_DIR, read_csv
from .models import TeamStrength


HOST_NATIONS = {"Mexico", "Canada", "United States"}


class StrengthAgent:
    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.elo = self._load_elo()
        self.form = self._load_form()
        self.fifa_rankings = self._load_fifa_rankings()
        self.wc_stats, self.global_wc_goals = self._load_worldcup_stats()

    def _load_elo(self) -> dict[str, float]:
        rows = read_csv(self.data_dir / "derived_elo_snapshot.csv")
        return {normalize_team(row["team"]): float(row["elo"]) for row in rows if row.get("team")}

    def _load_form(self) -> dict[str, dict[str, float]]:
        rows = read_csv(self.data_dir / "derived_recent_form.csv")
        return {
            normalize_team(row["team"]): {
                "points": float(row.get("recent_points_per_match") or 1.2),
                "gf": float(row.get("recent_goals_for_per_match") or 1.2),
                "ga": float(row.get("recent_goals_against_per_match") or 1.2),
            }
            for row in rows
            if row.get("team")
        }

    def _load_fifa_rankings(self) -> dict[str, dict[str, float]]:
        path = self.data_dir / "fifa_ranking_snapshot.csv"
        if not path.exists():
            return {}
        rankings = {}
        for row in read_csv(path):
            team = normalize_team(row.get("team", ""))
            if not team:
                continue
            rankings[team] = {
                "rank": _float_or_none(row.get("fifa_rank")),
                "points": _float_or_none(row.get("fifa_points")),
                "previous_rank": _float_or_none(row.get("fifa_previous_rank")),
            }
        return rankings

    def _load_worldcup_stats(self) -> tuple[dict[str, dict[str, float]], float]:
        rows = read_csv(self.data_dir / "international_results_worldcup_only.csv")
        stats: dict[str, dict[str, float]] = defaultdict(lambda: {"matches": 0.0, "gf": 0.0, "ga": 0.0})
        total_goals = 0
        team_games = 0
        for row in rows:
            if row.get("home_score") in ("", "NA") or row.get("away_score") in ("", "NA"):
                continue
            try:
                hg, ag = int(row["home_score"]), int(row["away_score"])
            except ValueError:
                continue
            home, away = normalize_team(row["home_team"]), normalize_team(row["away_team"])
            stats[home]["matches"] += 1
            stats[home]["gf"] += hg
            stats[home]["ga"] += ag
            stats[away]["matches"] += 1
            stats[away]["gf"] += ag
            stats[away]["ga"] += hg
            total_goals += hg + ag
            team_games += 2
        global_avg = total_goals / team_games if team_games else 1.35
        for item in stats.values():
            matches = max(1.0, item["matches"])
            item["gf"] /= matches
            item["ga"] /= matches
        return dict(stats), global_avg

    def team_strength(self, team: str) -> TeamStrength:
        name = normalize_team(team)
        warnings = []
        elo = self.elo.get(name)
        if elo is None:
            elo = 1500.0
            warnings.append(f"{name} missing Elo, fallback 1500")
        form = self.form.get(name)
        if form is None:
            form = {"points": 1.2, "gf": self.global_wc_goals, "ga": self.global_wc_goals}
            warnings.append(f"{name} missing recent form, fallback global average")
        wc = self.wc_stats.get(name)
        if wc is None:
            wc = {"gf": self.global_wc_goals, "ga": self.global_wc_goals}
            warnings.append(f"{name} missing World Cup history, fallback global average")
        fifa = self.fifa_rankings.get(name, {})
        if self.fifa_rankings and not fifa:
            warnings.append(f"{name} missing FIFA ranking, no FIFA ranking adjustment")
        return TeamStrength(
            team=name,
            elo=elo,
            recent_goals_for=form["gf"],
            recent_goals_against=form["ga"],
            recent_points_per_match=form["points"],
            wc_goals_for=wc["gf"],
            wc_goals_against=wc["ga"],
            fifa_rank=int(fifa["rank"]) if fifa.get("rank") is not None else None,
            fifa_points=fifa.get("points"),
            fifa_previous_rank=int(fifa["previous_rank"]) if fifa.get("previous_rank") is not None else None,
            warnings=tuple(warnings),
        )

    def expected_lambdas(self, home: str, away: str) -> tuple[float, float, list[str]]:
        h = self.team_strength(home)
        a = self.team_strength(away)
        base = self.global_wc_goals

        def capped(value: float, low: float = 0.45, high: float = 1.9) -> float:
            return max(low, min(high, value))

        h_attack = capped((0.55 * h.recent_goals_for + 0.45 * h.wc_goals_for) / base)
        a_attack = capped((0.55 * a.recent_goals_for + 0.45 * a.wc_goals_for) / base)
        h_def_vuln = capped((0.55 * h.recent_goals_against + 0.45 * h.wc_goals_against) / base)
        a_def_vuln = capped((0.55 * a.recent_goals_against + 0.45 * a.wc_goals_against) / base)

        h_elo, a_elo = elo_goal_multipliers(h.elo - a.elo)
        h_fifa, a_fifa = fifa_goal_multipliers(h, a)
        host_h = 1.08 if h.team in HOST_NATIONS else 1.0
        host_a = 1.08 if a.team in HOST_NATIONS else 1.0

        lam_h = max(0.2, min(3.8, base * h_attack * a_def_vuln * h_elo * h_fifa * host_h))
        lam_a = max(0.2, min(3.8, base * a_attack * h_def_vuln * a_elo * a_fifa * host_a))
        return round(lam_h, 4), round(lam_a, 4), list(h.warnings + a.warnings)


def _float_or_none(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def elo_win_probability(elo_diff: float, scale: float = 400.0) -> float:
    return 1.0 / (1.0 + math.pow(10.0, -elo_diff / scale))


def elo_goal_multipliers(elo_diff: float) -> tuple[float, float]:
    expected_home = elo_win_probability(elo_diff)
    centered_advantage = (expected_home - 0.5) * 2.0
    home_multiplier = 1.0 + 0.30 * centered_advantage
    away_multiplier = 1.0 - 0.30 * centered_advantage
    return max(0.75, min(1.25, home_multiplier)), max(0.75, min(1.25, away_multiplier))


def fifa_goal_multipliers(home: TeamStrength, away: TeamStrength) -> tuple[float, float]:
    if home.fifa_points is not None and away.fifa_points is not None:
        edge = max(-0.06, min(0.06, (home.fifa_points - away.fifa_points) / 500.0 * 0.06))
    elif home.fifa_rank is not None and away.fifa_rank is not None:
        edge = max(-0.04, min(0.04, (away.fifa_rank - home.fifa_rank) / 100.0 * 0.04))
    else:
        edge = 0.0
    return 1.0 + edge, 1.0 - edge
