from __future__ import annotations

import math
from dataclasses import asdict
from typing import TYPE_CHECKING

from .aliases import normalize_team
from .events import EventAgent
from .models import MatchPrediction, TeamStrength
from .score_models import aggregate_wdl, poisson_pmf, sample_scoreline, scoreline_matrix, sorted_scorelines, validate_score_model
from .strength import StrengthAgent

if TYPE_CHECKING:
    from .context import MatchContextAgent
    from .lineups import LineupAgent
    from .uncertainty import UncertaintyAgent


class ScorelineAgent:
    def __init__(
        self,
        strength: StrengthAgent,
        max_goals: int = 7,
        lineup: "LineupAgent | None" = None,
        context: "MatchContextAgent | None" = None,
        events: EventAgent | None = None,
        score_model: str = "independent_poisson",
        dixon_coles_rho: float = -0.08,
        uncertainty: "UncertaintyAgent | None" = None,
    ):
        self.strength = strength
        self.max_goals = max_goals
        self.lineup = lineup
        self.context = context
        self.events = events
        self.score_model = validate_score_model(score_model)
        self.dixon_coles_rho = dixon_coles_rho
        self.uncertainty = uncertainty

    @staticmethod
    def poisson_pmf(k: int, lam: float) -> float:
        return poisson_pmf(k, lam)

    def predict(self, home: str, away: str, match_id: str = "") -> MatchPrediction:
        home = normalize_team(home)
        away = normalize_team(away)
        (
            home_strength,
            away_strength,
            base_lam_h,
            base_lam_a,
            lam_h,
            lam_a,
            lineup_payload,
            context_payload,
            warnings,
        ) = self._prediction_inputs(home, away, match_id)
        matrix = scoreline_matrix(
            lam_h,
            lam_a,
            max_goals=self.max_goals,
            score_model=self.score_model,
            dixon_coles_rho=self.dixon_coles_rho,
        )
        p_home, p_draw, p_away = aggregate_wdl(matrix)
        scorelines = sorted_scorelines(matrix)
        event_payload = (
            self.events.predict(home, away, lam_h, lam_a, context_payload) if self.events else {}
        )
        uncertainty_payload = self._uncertainty_payload(lam_h, lam_a)
        explanation = self._build_explanation(
            home=home,
            away=away,
            match_id=match_id,
            home_strength=home_strength,
            away_strength=away_strength,
            base_lam_h=base_lam_h,
            base_lam_a=base_lam_a,
            final_lam_h=lam_h,
            final_lam_a=lam_a,
            p_home=p_home,
            p_draw=p_draw,
            p_away=p_away,
            scorelines=scorelines,
            lineup_payload=lineup_payload,
            context_payload=context_payload,
            event_payload=event_payload,
            uncertainty_payload=uncertainty_payload,
            warnings=warnings,
        )
        return MatchPrediction(
            home_team=home,
            away_team=away,
            lambda_home=lam_h,
            lambda_away=lam_a,
            p_home_win=round(p_home, 6),
            p_draw=round(p_draw, 6),
            p_away_win=round(p_away, 6),
            top_scorelines=scorelines[:10],
            expected_goals=round(lam_h + lam_a, 4),
            warnings=warnings,
            match_id=match_id,
            lineup_adjustment=lineup_payload,
            context_adjustment=context_payload,
            event_prediction=event_payload,
            explanation=explanation,
            score_model=self.score_model,
            score_model_parameters=self._score_model_parameters(),
            uncertainty=uncertainty_payload,
        )

    def _prediction_inputs(self, home: str, away: str, match_id: str):
        home_strength = self.strength.team_strength(home)
        away_strength = self.strength.team_strength(away)
        lam_h, lam_a, warnings = self.strength.expected_lambdas(home, away)
        base_lam_h, base_lam_a = lam_h, lam_a
        lineup_payload = {}
        context_payload = {}
        if self.lineup:
            adjustment = self.lineup.match_adjustment(home, away, match_id)
            lam_h = round(max(0.15, min(4.5, lam_h * adjustment.lambda_home_multiplier)), 4)
            lam_a = round(max(0.15, min(4.5, lam_a * adjustment.lambda_away_multiplier)), 4)
            warnings.extend(adjustment.warnings)
            lineup_payload = asdict(adjustment)
        if self.context:
            adjustment = self.context.match_adjustment(home, away, match_id)
            lam_h = round(max(0.15, min(4.5, lam_h * adjustment.lambda_home_multiplier)), 4)
            lam_a = round(max(0.15, min(4.5, lam_a * adjustment.lambda_away_multiplier)), 4)
            warnings.extend(adjustment.warnings)
            context_payload = adjustment.as_payload()
        return (
            home_strength,
            away_strength,
            base_lam_h,
            base_lam_a,
            lam_h,
            lam_a,
            lineup_payload,
            context_payload,
            warnings,
        )

    def sample_score(self, rng, home: str, away: str, match_id: str = "") -> tuple[int, int]:
        home = normalize_team(home)
        away = normalize_team(away)
        *_unused, lam_h, lam_a, _lineup_payload, _context_payload, _warnings = self._prediction_inputs(home, away, match_id)
        matrix = scoreline_matrix(
            lam_h,
            lam_a,
            max_goals=self.max_goals,
            score_model=self.score_model,
            dixon_coles_rho=self.dixon_coles_rho,
        )
        return sample_scoreline(rng, matrix)

    @staticmethod
    def _poisson_sample(rng, lam: float) -> int:
        limit = math.exp(-lam)
        k = 0
        p = 1.0
        while p > limit:
            k += 1
            p *= rng.random()
        return k - 1

    def _score_model_parameters(self) -> dict[str, float | int | str]:
        payload: dict[str, float | int | str] = {
            "score_model": self.score_model,
            "max_goals": self.max_goals,
        }
        if self.score_model == "dixon_coles":
            payload["dixon_coles_rho"] = self.dixon_coles_rho
        return payload

    def _uncertainty_payload(self, lam_h: float, lam_a: float) -> dict[str, object]:
        if not self.uncertainty:
            return {}
        return self.uncertainty.estimate(
            lam_h,
            lam_a,
            max_goals=self.max_goals,
            score_model=self.score_model,
            dixon_coles_rho=self.dixon_coles_rho,
        )

    def _build_explanation(
        self,
        home: str,
        away: str,
        match_id: str,
        home_strength: TeamStrength,
        away_strength: TeamStrength,
        base_lam_h: float,
        base_lam_a: float,
        final_lam_h: float,
        final_lam_a: float,
        p_home: float,
        p_draw: float,
        p_away: float,
        scorelines: list[dict[str, float | str]],
        lineup_payload: dict,
        context_payload: dict,
        event_payload: dict,
        uncertainty_payload: dict,
        warnings: list[str],
    ) -> dict[str, object]:
        winner = home if p_home >= max(p_draw, p_away) else away if p_away >= p_draw else "平局"
        if winner == "平局":
            headline = f"模型认为 {home} vs {away} 最主要风险是平局，平局概率为 {p_draw:.1%}。"
        else:
            probability = p_home if winner == home else p_away
            headline = f"模型认为 {winner} 是更可能获胜的一方，胜率约 {probability:.1%}。"

        strength_section = self._strength_section(home_strength, away_strength)
        lineup_section = self._lineup_section(lineup_payload)
        context_section = self._context_section(context_payload)
        event_section = self._event_section(event_payload)
        uncertainty_section = self._uncertainty_section(uncertainty_payload)
        data_quality = self._data_quality_section(
            lineup_payload=lineup_payload,
            context_payload=context_payload,
            event_payload=event_payload,
            warnings=warnings,
        )

        return {
            "language": "zh-CN",
            "headline": headline,
            "score_model": self._score_model_parameters(),
            "method": [
                "先用世界杯历史赛果得到基础进球率。",
                "再用 Elo、FIFA 排名、近期进失球、世界杯历史表现修正两队进球期望。",
                "如果提供赛前阵容、伤停、替补计划和球员评分，再把这些转成攻防乘数。",
                "如果启用上下文数据，再加入球员表现、旅行疲劳、战术、天气和裁判环境。",
                self._score_model_method_text(),
            ],
            "outcome": {
                "home_team": home,
                "away_team": away,
                "match_id": match_id,
                "p_home_win": round(p_home, 6),
                "p_draw": round(p_draw, 6),
                "p_away_win": round(p_away, 6),
                "most_likely_scoreline": scorelines[0],
                "top_scorelines": scorelines[:5],
                "expected_goals": {
                    home: round(final_lam_h, 4),
                    away: round(final_lam_a, 4),
                    "total": round(final_lam_h + final_lam_a, 4),
                },
            },
            "lambda_path": {
                "base": {home: base_lam_h, away: base_lam_a},
                "final": {home: final_lam_h, away: final_lam_a},
                "home_change_pct": round((final_lam_h / base_lam_h - 1.0) * 100.0, 2) if base_lam_h else 0.0,
                "away_change_pct": round((final_lam_a / base_lam_a - 1.0) * 100.0, 2) if base_lam_a else 0.0,
                "plain_text": (
                    f"基础进球期望为 {home} {base_lam_h:.2f}、{away} {base_lam_a:.2f}；"
                    f"叠加阵容/上下文后为 {home} {final_lam_h:.2f}、{away} {final_lam_a:.2f}。"
                ),
            },
            "factors": {
                "team_strength": strength_section,
                "lineup_and_availability": lineup_section,
                "match_context": context_section,
                "event_counts": event_section,
                "uncertainty": uncertainty_section,
                "data_quality": data_quality,
            },
            "warnings": [self._zh_warning(warning) for warning in warnings],
            "caveats": [
                "这是概率模型输出，不是确定赛果。",
                "当前模型不使用真实博彩赔率。",
                "EA FC 球员评分只在阵容文件缺少 rating 时作为 fallback，不是 FIFA 官方球员评分。",
            ],
        }

    @staticmethod
    def _strength_section(home: TeamStrength, away: TeamStrength) -> dict[str, object]:
        elo_diff = round(home.elo - away.elo, 1)
        fifa_rank_diff = None
        if home.fifa_rank is not None and away.fifa_rank is not None:
            fifa_rank_diff = away.fifa_rank - home.fifa_rank
        return {
            "summary": (
                f"Elo 差为 {elo_diff:+.1f}，FIFA 排名差为 {fifa_rank_diff:+d}（正数代表主队排名更靠前）。"
                if fifa_rank_diff is not None
                else f"Elo 差为 {elo_diff:+.1f}，FIFA 排名信息不完整。"
            ),
            "home": {
                "team": home.team,
                "elo": home.elo,
                "fifa_rank": home.fifa_rank,
                "fifa_points": home.fifa_points,
                "recent_goals_for": home.recent_goals_for,
                "recent_goals_against": home.recent_goals_against,
                "recent_points_per_match": home.recent_points_per_match,
                "worldcup_goals_for": home.wc_goals_for,
                "worldcup_goals_against": home.wc_goals_against,
                "warnings": list(home.warnings),
            },
            "away": {
                "team": away.team,
                "elo": away.elo,
                "fifa_rank": away.fifa_rank,
                "fifa_points": away.fifa_points,
                "recent_goals_for": away.recent_goals_for,
                "recent_goals_against": away.recent_goals_against,
                "recent_points_per_match": away.recent_points_per_match,
                "worldcup_goals_for": away.wc_goals_for,
                "worldcup_goals_against": away.wc_goals_against,
                "warnings": list(away.warnings),
            },
        }

    def _score_model_method_text(self) -> str:
        if self.score_model == "dixon_coles":
            return (
                "最后用 0-0 到 7-7 的 Dixon-Coles 修正 Poisson 比分矩阵汇总比分概率和胜平负概率，"
                "其中低比分平局会按 rho 参数做相关性修正。"
            )
        return "最后用 0-0 到 7-7 的独立 Poisson 比分矩阵汇总比分概率和胜平负概率。"

    @staticmethod
    def _lineup_section(lineup_payload: dict) -> dict[str, object]:
        if not lineup_payload:
            return {
                "used": False,
                "summary": "本次没有传入赛前官方阵容文件，首发、伤停、停赛和替补策略没有改变进球期望。",
            }
        return {
            "used": True,
            "summary": (
                f"阵容乘数：主队 {lineup_payload.get('lambda_home_multiplier')}，"
                f"客队 {lineup_payload.get('lambda_away_multiplier')}。"
            ),
            "home_context": lineup_payload.get("home_context", {}),
            "away_context": lineup_payload.get("away_context", {}),
            "evidence": lineup_payload.get("evidence", []),
            "warnings": lineup_payload.get("warnings", []),
        }

    @staticmethod
    def _context_section(context_payload: dict) -> dict[str, object]:
        if not context_payload:
            return {
                "used": False,
                "summary": "本次没有启用非赔率上下文文件，球员表现、天气、旅行、战术和裁判没有额外修正。",
            }
        home_context = context_payload.get("home_context", {})
        away_context = context_payload.get("away_context", {})
        weather = context_payload.get("weather_context", {})
        referee = context_payload.get("referee_context", {})
        return {
            "used": True,
            "summary": (
                f"上下文乘数：主队 {context_payload.get('lambda_home_multiplier')}，"
                f"客队 {context_payload.get('lambda_away_multiplier')}，"
                f"总进球环境 {context_payload.get('total_goals_multiplier')}。"
            ),
            "player_performance": {
                "home_rows": home_context.get("player_performance_rows", 0),
                "away_rows": away_context.get("player_performance_rows", 0),
                "summary": "有球员表现行时会按分钟、进攻事件、防守事件和评分生成攻防乘数；没有行则保持中性。",
            },
            "travel_fatigue": {
                "home_rows": home_context.get("travel_rows", 0),
                "away_rows": away_context.get("travel_rows", 0),
                "home_fatigue_multiplier": home_context.get("fatigue_multiplier"),
                "away_fatigue_multiplier": away_context.get("fatigue_multiplier"),
            },
            "tactics": {
                "home_rows": home_context.get("tactics_rows", 0),
                "away_rows": away_context.get("tactics_rows", 0),
                "home_attack_multiplier": home_context.get("tactic_attack_multiplier"),
                "away_attack_multiplier": away_context.get("tactic_attack_multiplier"),
                "home_defense_multiplier": home_context.get("tactic_defense_multiplier"),
                "away_defense_multiplier": away_context.get("tactic_defense_multiplier"),
            },
            "weather": weather,
            "referee": referee,
            "evidence": context_payload.get("evidence", []),
            "warnings": context_payload.get("warnings", []),
        }

    @staticmethod
    def _event_section(event_payload: dict) -> dict[str, object]:
        if not event_payload:
            return {
                "used": False,
                "summary": "本次没有事件预测 Agent 输出。",
            }
        totals = event_payload.get("match_totals", {})
        return {
            "used": True,
            "summary": (
                f"事件预测样本行数 {event_payload.get('sample_rows', 0)}；"
                "输出黄牌、红牌、角球、任意球、点球的上下半场预期。"
            ),
            "context": event_payload.get("context", {}),
            "match_totals": totals,
            "warnings": [ScorelineAgent._zh_warning(warning) for warning in event_payload.get("warnings", [])],
        }

    @staticmethod
    def _uncertainty_section(uncertainty_payload: dict) -> dict[str, object]:
        if not uncertainty_payload:
            return {
                "used": False,
                "summary": "本次没有启用不确定性区间，输出的是单点概率。",
            }
        intervals = uncertainty_payload.get("intervals", {})
        return {
            "used": True,
            "summary": (
                f"使用 {uncertainty_payload.get('samples')} 次 lambda 扰动样本生成 p05/p50/p95 区间；"
                "这是轻量不确定性代理，不是完整 Bayesian 后验。"
            ),
            "method": uncertainty_payload.get("method"),
            "bayesian_status": uncertainty_payload.get("bayesian_status"),
            "intervals": intervals,
            "warnings": uncertainty_payload.get("warnings", []),
        }

    @staticmethod
    def _zh_warning(warning: str) -> str:
        text = str(warning)
        if "missing event sample, fallback global half rates" in text:
            team = text.split(" missing event sample", 1)[0]
            return f"{team} 缺少球队事件样本，事件数量回退到全局半场均值"
        if text.startswith("no weather row matched"):
            return "缺少本场精确天气行，天气因素保持中性"
        if "missing World Cup history, fallback global average" in text:
            team = text.split(" missing World Cup history", 1)[0]
            return f"{team} 缺少世界杯历史样本，世界杯历史强度使用全局均值"
        if "fallback 1500" in text:
            return text.replace("missing Elo, fallback 1500", "缺少 Elo，使用 1500 作为回退值")
        return text

    @staticmethod
    def _data_quality_section(
        lineup_payload: dict,
        context_payload: dict,
        event_payload: dict,
        warnings: list[str],
    ) -> dict[str, object]:
        gaps = []
        if not lineup_payload:
            gaps.append("缺少赛前官方阵容/伤停/替补策略文件")
        if context_payload:
            weather = context_payload.get("weather_context", {})
            if not weather.get("rows"):
                gaps.append("缺少本场精确 kickoff 天气")
            for side in ("home_context", "away_context"):
                team_context = context_payload.get(side, {})
                if not team_context.get("player_performance_rows", 0):
                    gaps.append(f"{team_context.get('team', side)} 缺少球员表现样本")
        else:
            gaps.append("未启用非赔率上下文")
        if event_payload and event_payload.get("warnings"):
            gaps.extend(ScorelineAgent._zh_warning(warning) for warning in event_payload.get("warnings", []))
        return {
            "summary": "；".join(gaps) if gaps else "关键数据均已进入本次预测。",
            "gaps": gaps,
            "warnings": [ScorelineAgent._zh_warning(warning) for warning in warnings],
        }
