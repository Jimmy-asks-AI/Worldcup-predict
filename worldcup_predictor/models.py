from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentResult:
    agent: str
    match_id: str
    payload: dict[str, Any]
    confidence: float
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Fixture:
    match_id: str
    stage: str
    group: str
    home_team: str
    away_team: str
    kickoff_utc: str = ""
    stadium: str = ""


@dataclass(frozen=True)
class ActualResult:
    match_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int


@dataclass(frozen=True)
class TeamStrength:
    team: str
    elo: float
    recent_goals_for: float
    recent_goals_against: float
    recent_points_per_match: float
    wc_goals_for: float
    wc_goals_against: float
    fifa_rank: int | None = None
    fifa_points: float | None = None
    fifa_previous_rank: int | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LineupContext:
    team: str
    match_id: str = ""
    row_count: int = 0
    starter_count: int = 0
    substitute_count: int = 0
    unavailable_count: int = 0
    attack_rating: float = 75.0
    defense_rating: float = 75.0
    attack_multiplier: float = 1.0
    defense_multiplier: float = 1.0
    bench_minutes: float = 0.0
    official_starter_count: int = 0
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LineupMatchAdjustment:
    match_id: str
    home_team: str
    away_team: str
    lambda_home_multiplier: float
    lambda_away_multiplier: float
    home_context: LineupContext
    away_context: LineupContext
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MatchPrediction:
    home_team: str
    away_team: str
    lambda_home: float
    lambda_away: float
    p_home_win: float
    p_draw: float
    p_away_win: float
    top_scorelines: list[dict[str, float | str]]
    expected_goals: float
    warnings: list[str] = field(default_factory=list)
    match_id: str = ""
    lineup_adjustment: dict[str, Any] = field(default_factory=dict)
    context_adjustment: dict[str, Any] = field(default_factory=dict)
    event_prediction: dict[str, Any] = field(default_factory=dict)
    explanation: dict[str, Any] = field(default_factory=dict)
    score_model: str = "independent_poisson"
    score_model_parameters: dict[str, Any] = field(default_factory=dict)
    uncertainty: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TournamentOutcome:
    team: str
    p_group_winner: float
    p_round_of_32: float
    p_round_of_16: float
    p_quarter_final: float
    p_semi_final: float
    p_final: float
    p_champion: float
    expected_points: float
    expected_goal_difference: float
