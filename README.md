# Worldcup-predict

基于 Codex 的世界杯多 Agent 预测模型。这个仓库保存模型代码、数据拉取/审计脚本、测试、输入契约、审计报告和 `worldcup-predict` skill；不提交原始数据、处理后数据和大体量生成数据。

## 本次预测快照

运行日期：2026-06-16  
命令：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --match-id 97 --use-generated-context
```

预测结果：

- 对局：France vs Senegal
- 最可能比分：France 2-0 Senegal，概率 11.16%
- 胜平负：France 胜 67.40%，平局 18.88%，Senegal 胜 13.73%
- 预期总进球：3.0794
- 事件数量预期：黄牌 1.80，红牌 0.00，角球 7.71，任意球 30.85，点球 0.08

重要边界：

- 本次使用了本地生成的非赔率上下文，但没有官方赛前首发文件，所以阵容、伤停、替补策略没有进入本场计算。
- 本次没有匹配到 `match_id=97` 的 Gillette Stadium 精确天气行，天气没有直接修正该场概率。
- France 和 Senegal 没有球队级事件样本，事件数量预测回退到全局半场事件率。
- 模型没有使用真实博彩赔率；EA FC 球员评分只作为阵容评分 fallback，不是 FIFA 官方球员评分。

## 模型方法

单场预测流程：

1. `DataAgent` 加载赛程、球队、已完赛比分和本地 CSV。
2. `StrengthAgent` 使用 Elo、近期状态、世界杯历史表现和 FIFA 排名生成球队强度。
3. `LineupAgent` 可在提供赛前官方阵容 CSV 时加入首发、伤停和替补策略。
4. `MatchContextAgent` 可加入球员表现、天气、旅行疲劳、战术和裁判倾向。
5. `ScorelineAgent` 把强度和上下文转成两队进球期望，用 Poisson 比分矩阵得到比分概率和胜平负概率。
6. `EventAgent` 预测黄牌、红牌、角球、任意球、点球的上下半场数量。
7. `TournamentAgent` 用 Monte Carlo 模拟小组赛、最佳第三名、淘汰赛路径和冠军概率。

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
```

生成中文总报告：

```powershell
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --sample-match-id 97 --use-generated-context
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
