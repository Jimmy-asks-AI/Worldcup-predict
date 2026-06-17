from __future__ import annotations

import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from .aliases import normalize_team
from .data import DEFAULT_DATA_DIR, DataAgent
from .models import MatchPrediction, TournamentOutcome
from .score_models import sample_scoreline, scoreline_matrix
from .scoreline import ScorelineAgent
from .strength import StrengthAgent, elo_win_probability


GROUPS = "ABCDEFGHIJKL"


@dataclass
class TeamTable:
    team: str
    points: int = 0
    gf: int = 0
    ga: int = 0

    @property
    def gd(self) -> int:
        return self.gf - self.ga


class TournamentAgent:
    def __init__(
        self,
        data: DataAgent | None = None,
        scoreline: ScorelineAgent | None = None,
        seed: int = 2026,
    ):
        self.data = data or DataAgent(DEFAULT_DATA_DIR)
        strength = StrengthAgent(self.data.data_dir)
        self.scoreline = scoreline or ScorelineAgent(strength)
        self.seed = seed
        self._prediction_cache: dict[tuple[str, str, str], MatchPrediction] = {}
        self._score_matrix_cache: dict[tuple[str, str, str], list[list[float]]] = {}

    def _prediction(self, match_id: str, home: str, away: str) -> MatchPrediction:
        key = (str(match_id), normalize_team(home), normalize_team(away))
        if key not in self._prediction_cache:
            self._prediction_cache[key] = self.scoreline.predict(key[1], key[2], match_id=key[0])
        return self._prediction_cache[key]

    def _sample_match(self, rng: random.Random, match_id: str, home: str, away: str) -> tuple[int, int]:
        key = (str(match_id), normalize_team(home), normalize_team(away))
        if key not in self._score_matrix_cache:
            pred = self._prediction(match_id, home, away)
            self._score_matrix_cache[key] = scoreline_matrix(
                pred.lambda_home,
                pred.lambda_away,
                max_goals=self.scoreline.max_goals,
                score_model=self.scoreline.score_model,
                dixon_coles_rho=self.scoreline.dixon_coles_rho,
            )
        return sample_scoreline(rng, self._score_matrix_cache[key])

    def _penalty_home_win(self, home: str, away: str) -> float:
        h = self.scoreline.strength.team_strength(home)
        a = self.scoreline.strength.team_strength(away)
        return max(0.35, min(0.65, 0.5 + (elo_win_probability(h.elo - a.elo) - 0.5) * 0.30))

    @staticmethod
    def _apply_result(table: dict[str, TeamTable], home: str, away: str, hg: int, ag: int) -> None:
        table[home].gf += hg
        table[home].ga += ag
        table[away].gf += ag
        table[away].ga += hg
        if hg > ag:
            table[home].points += 3
        elif hg < ag:
            table[away].points += 3
        else:
            table[home].points += 1
            table[away].points += 1

    @staticmethod
    def _rank_group(table: dict[str, TeamTable], rng: random.Random) -> list[TeamTable]:
        return sorted(
            table.values(),
            key=lambda t: (t.points, t.gd, t.gf, rng.random()),
            reverse=True,
        )

    def _simulate_groups(self, rng: random.Random):
        actuals = self.data.actual_results()
        groups = self.data.teams_by_group()
        fixtures = self.data.group_fixtures()
        ranked_by_group: dict[str, list[TeamTable]] = {}
        points_sum: Counter[str] = Counter()
        gd_sum: Counter[str] = Counter()

        for group, teams in groups.items():
            table = {team: TeamTable(team=team) for team in teams}
            for fixture in [f for f in fixtures if f.group == group]:
                actual = actuals.get(fixture.match_id)
                if actual:
                    hg, ag = actual.home_score, actual.away_score
                else:
                    hg, ag = self._sample_match(rng, fixture.match_id, fixture.home_team, fixture.away_team)
                self._apply_result(table, fixture.home_team, fixture.away_team, hg, ag)
            ranked = self._rank_group(table, rng)
            ranked_by_group[group] = ranked
            for team in ranked:
                points_sum[team.team] += team.points
                gd_sum[team.team] += team.gd
        return ranked_by_group, points_sum, gd_sum

    @staticmethod
    def _allowed_groups(text: str) -> list[str]:
        match = re.search(r"Group ([A-L/]+) third place", text, re.IGNORECASE)
        return [group.upper() for group in match.group(1).split("/")] if match else []

    @staticmethod
    def _assign_third_slots(third_by_group: dict[str, str], slot_refs: list[str]) -> dict[str, str]:
        slots = [(ref, TournamentAgent._allowed_groups(ref)) for ref in slot_refs]
        slots.sort(key=lambda item: len(item[1]))
        assigned: dict[str, str] = {}
        used: set[str] = set()

        def backtrack(idx: int) -> bool:
            if idx == len(slots):
                return True
            ref, allowed = slots[idx]
            for group in allowed:
                if group in third_by_group and group not in used:
                    used.add(group)
                    assigned[ref] = third_by_group[group]
                    if backtrack(idx + 1):
                        return True
                    assigned.pop(ref, None)
                    used.remove(group)
            return False

        if not backtrack(0):
            for ref, allowed in slots:
                for group in allowed:
                    if group in third_by_group and group not in used:
                        used.add(group)
                        assigned[ref] = third_by_group[group]
                        break
        return assigned

    @staticmethod
    def _resolve_placeholder(text: str, ranked_by_group: dict[str, list[TeamTable]], thirds: dict[str, str]) -> str:
        if not text:
            return ""
        winner = re.match(r"Group ([A-L]) winners", text, re.IGNORECASE)
        if winner:
            return ranked_by_group[winner.group(1).upper()][0].team
        runner = re.match(r"Group ([A-L]) runners-up", text, re.IGNORECASE)
        if runner:
            return ranked_by_group[runner.group(1).upper()][1].team
        if "third place" in text:
            return thirds[text]
        return normalize_team(text)

    def _choose_knockout_winner(self, rng: random.Random, match_id: str, home: str, away: str) -> tuple[str, str]:
        actual = self.data.actual_results().get(match_id)
        if actual and actual.home_score != actual.away_score:
            winner = home if actual.home_score > actual.away_score else away
            return winner, away if winner == home else home
        hg, ag = self._sample_match(rng, match_id, home, away)
        if hg > ag:
            return home, away
        if ag > hg:
            return away, home
        winner = home if rng.random() < self._penalty_home_win(home, away) else away
        return winner, away if winner == home else home

    def _simulate_knockouts(
        self,
        rng: random.Random,
        ranked_by_group: dict[str, list[TeamTable]],
        qualified_thirds: dict[str, str],
    ) -> tuple[str, Counter[str]]:
        knockout_fixtures = sorted(self.data.knockout_fixtures(), key=lambda f: int(f.match_id))
        third_refs = []
        for fixture in knockout_fixtures:
            for text in (fixture.home_team, fixture.away_team):
                if "third place" in text and text not in third_refs:
                    third_refs.append(text)
        third_slots = self._assign_third_slots(qualified_thirds, third_refs)

        winners: dict[str, str] = {}
        losers: dict[str, str] = {}
        reached: Counter[str] = Counter()

        for fixture in knockout_fixtures:
            home = self._resolve_knockout_ref(fixture.home_team, ranked_by_group, third_slots, winners, losers)
            away = self._resolve_knockout_ref(fixture.away_team, ranked_by_group, third_slots, winners, losers)
            winner, loser = self._choose_knockout_winner(rng, fixture.match_id, home, away)
            winners[fixture.match_id] = winner
            losers[fixture.match_id] = loser
            match_no = int(fixture.match_id)
            if 73 <= match_no <= 88:
                reached[(winner, "round_of_16")] += 1
            elif 89 <= match_no <= 96:
                reached[(winner, "quarter_final")] += 1
            elif 97 <= match_no <= 100:
                reached[(winner, "semi_final")] += 1
            elif 101 <= match_no <= 102:
                reached[(winner, "final")] += 1
            elif match_no == 104:
                reached[(winner, "champion")] += 1
        return winners.get("104", ""), reached

    def _resolve_knockout_ref(
        self,
        text: str,
        ranked_by_group: dict[str, list[TeamTable]],
        thirds: dict[str, str],
        winners: dict[str, str],
        losers: dict[str, str],
    ) -> str:
        win = re.match(r"Winner Match ([0-9]+)", text)
        if win:
            return winners[win.group(1)]
        lose = re.match(r"Loser Match ([0-9]+)", text)
        if lose:
            return losers[lose.group(1)]
        return self._resolve_placeholder(text, ranked_by_group, thirds)

    def simulate(self, runs: int = 20000) -> tuple[list[TournamentOutcome], list[dict]]:
        rng = random.Random(self.seed)
        teams = sorted(self.data.teams().keys())
        group_winner = Counter()
        round_of_32 = Counter()
        reached = Counter()
        expected_points = Counter()
        expected_gd = Counter()

        for _ in range(runs):
            ranked, pts, gd = self._simulate_groups(rng)
            for team, value in pts.items():
                expected_points[team] += value
            for team, value in gd.items():
                expected_gd[team] += value
            thirds = []
            third_by_group = {}
            for group, table in ranked.items():
                group_winner[table[0].team] += 1
                round_of_32[table[0].team] += 1
                round_of_32[table[1].team] += 1
                third = table[2]
                thirds.append((group, third))
            thirds.sort(key=lambda item: (item[1].points, item[1].gd, item[1].gf, rng.random()), reverse=True)
            for group, team_table in thirds[:8]:
                third_by_group[group] = team_table.team
                round_of_32[team_table.team] += 1
            _, ko_reached = self._simulate_knockouts(rng, ranked, third_by_group)
            reached.update(ko_reached)

        outcomes = []
        for team in teams:
            outcomes.append(
                TournamentOutcome(
                    team=team,
                    p_group_winner=round(group_winner[team] / runs, 6),
                    p_round_of_32=round(round_of_32[team] / runs, 6),
                    p_round_of_16=round(reached[(team, "round_of_16")] / runs, 6),
                    p_quarter_final=round(reached[(team, "quarter_final")] / runs, 6),
                    p_semi_final=round(reached[(team, "semi_final")] / runs, 6),
                    p_final=round(reached[(team, "final")] / runs, 6),
                    p_champion=round(reached[(team, "champion")] / runs, 6),
                    expected_points=round(expected_points[team] / runs, 3),
                    expected_goal_difference=round(expected_gd[team] / runs, 3),
                )
            )
        outcomes.sort(key=lambda row: row.p_champion, reverse=True)
        group_rows = self._group_rows(outcomes)
        return outcomes, group_rows

    def _group_rows(self, outcomes: list[TournamentOutcome]) -> list[dict]:
        outcome_by_team = {item.team: item for item in outcomes}
        groups = self.data.teams_by_group()
        rows = []
        for group, teams in groups.items():
            for team in sorted(teams, key=lambda t: outcome_by_team[t].expected_points, reverse=True):
                outcome = outcome_by_team[team]
                rows.append(
                    {
                        "group": group,
                        "team": team,
                        "p_group_winner": outcome.p_group_winner,
                        "p_round_of_32": outcome.p_round_of_32,
                        "expected_points": outcome.expected_points,
                        "expected_goal_difference": outcome.expected_goal_difference,
                    }
                )
        return rows
