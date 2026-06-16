from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .data import OUTPUT_DIR, DataAgent, write_csv
from .events import EventAgent
from .lineups import LineupAgent
from .models import MatchPrediction, TournamentOutcome
from .scoreline import ScorelineAgent
from .strength import StrengthAgent
from .tournament import TournamentAgent


class ReportAgent:
    def __init__(self, output_dir: Path | str = OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.pred_dir = self.output_dir / "predictions"
        self.report_dir = self.output_dir / "reports"

    def write_match_predictions(self, predictions: list[MatchPrediction]) -> Path:
        self.pred_dir.mkdir(parents=True, exist_ok=True)
        path = self.pred_dir / "match_predictions.json"
        path.write_text(json.dumps([asdict(p) for p in predictions], indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def write_tournament(self, outcomes: list[TournamentOutcome], group_rows: list[dict]) -> tuple[Path, Path]:
        self.pred_dir.mkdir(parents=True, exist_ok=True)
        odds_path = self.pred_dir / "tournament_odds.csv"
        group_path = self.pred_dir / "group_rankings.csv"
        write_csv(odds_path, [asdict(item) for item in outcomes], list(asdict(outcomes[0]).keys()))
        write_csv(
            group_path,
            group_rows,
            ["group", "team", "p_group_winner", "p_round_of_32", "expected_points", "expected_goal_difference"],
        )
        return odds_path, group_path

    def write_report(
        self,
        sample_prediction: MatchPrediction,
        outcomes: list[TournamentOutcome],
        group_rows: list[dict],
        runs: int,
    ) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        top_champions = outcomes[:10]
        context = sample_prediction.context_adjustment or {}
        lines = [
            "# 世界杯多 Agent 预测报告",
            "",
            f"模拟次数：{runs:,}",
            "",
            "## 单场示例",
            "",
            f"- 比赛：{sample_prediction.home_team} vs {sample_prediction.away_team}",
            f"- 最可能比分：{sample_prediction.top_scorelines[0]['scoreline']}，概率 {sample_prediction.top_scorelines[0]['probability']:.2%}",
            f"- 胜平负：{sample_prediction.home_team} 胜 {sample_prediction.p_home_win:.1%}，平 {sample_prediction.p_draw:.1%}，{sample_prediction.away_team} 胜 {sample_prediction.p_away_win:.1%}",
            f"- 预期总进球：{sample_prediction.expected_goals}",
            "",
            "## 冠军概率 Top 10",
            "",
            "| 排名 | 球队 | 冠军概率 | 进决赛概率 | 进四强概率 |",
            "|---:|---|---:|---:|---:|",
        ]
        for idx, team in enumerate(top_champions, 1):
            lines.append(
                f"| {idx} | {team.team} | {team.p_champion:.1%} | {team.p_final:.1%} | {team.p_semi_final:.1%} |"
            )
        if context:
            lines.extend(
                [
                    "",
                    "## 非赔率上下文调整",
                    "",
                    f"- 主队 lambda multiplier：{context.get('lambda_home_multiplier')}",
                    f"- 客队 lambda multiplier：{context.get('lambda_away_multiplier')}",
                    f"- 总进球环境 multiplier：{context.get('total_goals_multiplier')}",
                    f"- 纪律强度 index：{context.get('discipline_index')}",
                    f"- 定位球环境 index：{context.get('set_piece_index')}",
                ]
            )
            evidence = context.get("evidence") or []
            if evidence:
                lines.append("- 关键证据：" + "；".join(str(item) for item in evidence[:4]))
            warnings = context.get("warnings") or []
            if warnings:
                lines.append("- 警告：" + "；".join(str(item) for item in warnings[:4]))
        events = sample_prediction.event_prediction or {}
        match_totals = events.get("match_totals") or {}
        if match_totals:
            names = {
                "yellow_cards": "黄牌",
                "red_cards": "红牌",
                "corners": "角球",
                "free_kicks": "任意球",
                "penalties": "点球",
            }
            lines.extend(
                [
                    "",
                    "## 事件数量预测",
                    "",
                    "| 事件 | 上半场预期 | 下半场预期 | 全场预期 | 最可能全场数量 |",
                    "|---|---:|---:|---:|---:|",
                ]
            )
            for key in ["yellow_cards", "red_cards", "corners", "free_kicks", "penalties"]:
                item = match_totals.get(key, {})
                lines.append(
                    f"| {names[key]} | {float(item.get('first_half_expected', 0)):.2f} | "
                    f"{float(item.get('second_half_expected', 0)):.2f} | "
                    f"{float(item.get('total_expected', 0)):.2f} | {item.get('most_likely_total', 0)} |"
                )
        lines.extend(
            [
                "",
                "## 小组排名概率摘要",
                "",
                "| 小组 | 球队 | 小组第一概率 | 晋级 32 强概率 | 预期积分 | 预期净胜球 |",
                "|---|---|---:|---:|---:|---:|",
            ]
        )
        for row in group_rows:
            lines.append(
                f"| {row['group']} | {row['team']} | {float(row['p_group_winner']):.1%} | "
                f"{float(row['p_round_of_32']):.1%} | {row['expected_points']} | {row['expected_goal_difference']} |"
            )
        lines.extend(
            [
                "",
                "## 数据说明",
                "",
                "- 基础模型使用赛程、历史世界杯赛果、自算 Elo、近期国家队状态、已完赛真实比分。",
                "- 可选非赔率上下文包括官方阵容/伤停/替补、EA FC 球员评分、球员历史表现、天气、旅行疲劳、战术阵型和裁判倾向。",
                "- 事件数量预测使用 StatsBomb 半场事件样本，输出黄牌、红牌、角球、任意球、点球的上下半场预期。",
                "- 真实赔率数据被明确排除；不会进入当前概率计算。",
                "- 中文解释只解释结构化模型输出，不使用 LLM 自行判断比赛结果。",
            ]
        )
        path = self.report_dir / "worldcup_prediction_report.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path


def build_report(runs: int = 20000, lineup_file: str | None = None) -> dict[str, str]:
    data = DataAgent()
    strength = StrengthAgent(data.data_dir)
    lineup = LineupAgent(lineup_file) if lineup_file else None
    scoreline = ScorelineAgent(strength, lineup=lineup, events=EventAgent(data.data_dir))
    tournament = TournamentAgent(data=data, scoreline=scoreline)
    sample = scoreline.predict("France", "Senegal")
    outcomes, groups = tournament.simulate(runs=runs)
    report = ReportAgent()
    report.write_match_predictions([sample])
    odds_path, group_path = report.write_tournament(outcomes, groups)
    report_path = report.write_report(sample, outcomes, groups, runs)
    return {"odds": str(odds_path), "groups": str(group_path), "report": str(report_path)}
