# Worldcup-predict

基于 Codex 的世界杯多 Agent 预测模型。这个仓库保存模型代码、数据拉取/审计脚本、测试、输入契约、审计报告和 `worldcup-predict` skill；不提交原始数据、处理后数据和大体量生成数据。

## 当前能力快照

这次更新把 GitHub 世界杯预测项目的可借鉴点逐项吸收到本地模型和 `worldcup-predict` skill 中，但没有把黑盒分类器或教学型回归模型直接替换为主模型。

新增/强化能力：

- 可选 Dixon-Coles 低比分修正：`--score-model dixon_coles`。
- Dixon-Coles `rho` 调参门禁：`tune-dixon-coles`。
- 单场不确定性区间：`--include-uncertainty`。
- 胜平负概率校准门禁：`calibration-backtest`。
- FIFA ranking/points 简单 sanity baseline：`ranking-baseline`。
- append-only 预测审计日志：`outputs/audit/prediction_runs.jsonl`。
- 中文报告中的 `2026 赛制随机性`：解释 48 队、12 组、32 强和 5 轮淘汰赛如何让冠军概率分散。

最近一次正式报告命令：

```powershell
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --sample-match-id 97 --use-generated-context --include-uncertainty --uncertainty-samples 80
```

报告输出：

- `outputs/reports/worldcup_prediction_report.md`
- `outputs/reports/github_project_improvement_status.md`
- `outputs/reports/dixon_coles_rho_tuning.json`
- `outputs/reports/calibration_backtest.json`

重要边界：

- `tune-dixon-coles` 和 `calibration-backtest` 都是默认关闭的评估门禁，不会自动改变生产预测。
- 当前默认比分模型仍是 `independent_poisson`。
- 模型没有使用真实博彩赔率。
- EA FC 球员评分只作为阵容评分 fallback，不是 FIFA 官方球员评分。

## 模型方法

单场预测流程：

1. `DataAgent` 加载赛程、球队、已完赛比分和本地 CSV。
2. `StrengthAgent` 使用 Elo、近期状态、世界杯历史表现和 FIFA 排名生成球队强度。
3. `LineupAgent` 可在提供赛前官方阵容 CSV 时加入首发、伤停和替补策略。
4. `MatchContextAgent` 可加入球员表现、天气、旅行疲劳、战术和裁判倾向。
5. `ScorelineAgent` 把强度和上下文转成两队进球期望，用 Poisson/Dixon-Coles 比分矩阵得到比分概率和胜平负概率。
6. `EventAgent` 预测黄牌、红牌、角球、任意球、点球的上下半场数量。
7. `TournamentAgent` 用 Monte Carlo 模拟小组赛、最佳第三名、淘汰赛路径和冠军概率。
8. `ReportAgent` 输出中文报告，并解释 2026 新赛制下的冠军概率分散。

## 快速开始

先拉取或生成本地数据：

```powershell
python -m worldcup_predictor refresh-data
python -m worldcup_predictor build-context-data
```

运行健康检查：

```powershell
python skills\worldcup-predict\scripts\health_check.py --root .
```

预测单场比赛：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --match-id 97 --use-generated-context
python -m worldcup_predictor predict-match --home France --away Senegal --include-uncertainty
```

生成中文总报告：

```powershell
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --sample-match-id 97 --use-generated-context
```

运行模型评估/门禁：

```powershell
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1
python -m worldcup_predictor tune-dixon-coles --start-year 2018 --min-prior-matches 1
python -m worldcup_predictor calibration-backtest --start-year 2018 --min-prior-matches 1
python -m worldcup_predictor ranking-baseline --home France --away Senegal
```

运行测试：

```powershell
python -m unittest discover -s tests -v
```

## 仓库包含

- `worldcup_predictor/`：核心预测包。
- `worldcup_data_audit/scripts/`：数据拉取、审计和上下文生成脚本。
- `tests/`：模型不变量和回测相关测试。
- `inputs/`：输入契约、模板和来源说明；不含大体量数据。
- `outputs/reports/`：模型审计和说明性报告；不含 `outputs/predictions/` 概率数据表。
- `skills/worldcup-predict/`：可安装到 Codex 的预测 skill。

## 数据排除规则

以下内容不提交到仓库：

- `worldcup_data_audit/data/`
- `outputs/predictions/`
- `inputs/player_ratings/eafc26_player_ratings.csv`
- `inputs/player_performance/player_match_performance.csv`
- `inputs/player_performance/player_identity_map.csv`
- `inputs/match_context/weather_forecast.csv`
- `inputs/match_context/team_travel_fatigue.csv`
- `inputs/match_context/tactics.csv`
- `inputs/match_context/referees.csv`

这些文件需要通过数据脚本重新拉取或生成。
