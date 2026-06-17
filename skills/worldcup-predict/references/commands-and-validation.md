# 命令和验证

## 快速健康检查

从任意目录运行：

```powershell
python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root E:\Vibe-coding\小红书
```

如果已经在项目根目录：

```powershell
python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root .
```

## 数据源目录

先查看项目级数据来源和数据类型目录：

```powershell
Get-Content -Encoding UTF8 outputs\reports\worldcup_data_source_catalog.md
```

这份目录应记录：

- 数据类型：赛程、球队、历史赛果、Elo、FIFA 排名、官方阵容、球员资料、球员表现、事件、天气、旅行、战术、裁判、赔率、伤停等。
- 上游来源：FIFA API、StatsBomb Open Data、Open-Meteo、martj42 international results、TheStatsAPI、worldcup26.ir、EA FC ratings mirror、本地派生等。
- 本地文件：模型实际读取或审计保存的位置。
- 模型入口：`DataAgent`、`StrengthAgent`、`LineupAgent`、`MatchContextAgent`、`EventAgent` 等。
- 状态：已获得、已进入模型、赛前安全、当前缺口。

## 预测审计日志

`predict-match` 和 `report` 会追加写入：

```powershell
outputs\audit\prediction_runs.jsonl
```

查看最后一条：

```powershell
Get-Content -Encoding UTF8 outputs\audit\prediction_runs.jsonl -Tail 1
```

每条 JSONL 记录包含：

- `timestamp_utc`
- `run_type`
- `command`
- `argv`
- `cli_options`
- `pre_match_safe_boundary`
- `data_files`：输入文件路径、是否存在、hash、CSV 行数
- `prediction`：胜平负、lambda、Top scorelines、比分模型、不确定性、warnings
- `explanation_summary`

这个日志受 `pravindurgani/wc26-matchday-intelligence` 的 append-only audit log 思路启发。它只追踪本地预测运行，不会自动拉取 live API，也不改变预测概率。

## 单场预测

基础预测：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal
```

使用 Hicruben 启发的 Dixon-Coles 低比分修正：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --score-model dixon_coles
```

使用 lbenz730 启发的轻量不确定性区间：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --include-uncertainty
```

使用生成的非赔率上下文：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --match-id 97 --use-generated-context
```

加入赛前官方阵容和球员评分 fallback：

```powershell
python -m worldcup_predictor predict-match --home Spain --away "Cape Verde" --match-id 1 `
  --lineup-file inputs\lineups\template.csv `
  --lineup-allowed-source manual-template `
  --player-ratings-file inputs\player_ratings\eafc26_player_ratings.csv `
  --use-generated-context
```

奥地利 vs 约旦 match20 的赛前补齐流程：

```powershell
python worldcup_data_audit\scripts\build_match20_gap_inputs.py

python -m worldcup_predictor predict-match --home Austria --away Jordan --match-id 20 `
  --use-generated-context `
  --lineup-file inputs\lineups\match20_austria_jordan_fifa_official.csv `
  --lineup-allowed-source fifa_api_live_match `
  --player-ratings-file inputs\player_ratings\eafc26_player_ratings.csv `
  --score-model dixon_coles `
  --include-uncertainty
```

该补齐脚本会拉取或刷新：

- FIFA live match：官方首发、替补、阵型、裁判。
- FIFA season squads：48 队赛季名单。
- FIFA player profile / individual statistics：球员身份和国家队/FIFA 统计。
- Open-Meteo：本场 exact kickoff hour weather。
- 阵容到本地 StatsBomb 球员表现样本的匹配报告。

读取输出 JSON 时重点看：

- `lambda_home` / `lambda_away`
- `p_home_win` / `p_draw` / `p_away_win`
- `top_scorelines`
- `lineup_adjustment`
- `context_adjustment`
- `event_prediction`
- `explanation`
- `warnings`
- `score_model`
- `score_model_parameters`
- `uncertainty`
- `audit_log`

解释用户结果时，优先使用 `explanation`：

- `explanation.headline` 写结论。
- `explanation.lambda_path` 写基础进球期望如何变成最终进球期望。
- `explanation.factors.team_strength` 写 Elo、FIFA、近期状态、世界杯历史。
- `explanation.factors.lineup_and_availability` 写首发、伤停、替补和球员评分是否进入模型。
- `explanation.factors.match_context` 写球员表现、旅行疲劳、战术、天气和裁判。
- `explanation.factors.event_counts` 写黄牌、红牌、角球、任意球、点球数量。
- `explanation.factors.data_quality` 写缺失数据和 fallback。
- `explanation.caveats` 写概率边界和未使用真实赔率。
- `explanation.score_model` 写本次用的是 `independent_poisson` 还是 `dixon_coles`；Dixon-Coles 只修正低比分相关性，不代表接入了新的球队数据。
- `explanation.factors.uncertainty` 写是否启用 p05/p50/p95 区间；启用时要说明这是 lbenz730 Bayesian 思路启发的轻量 lambda 扰动代理，不是完整 Bayesian 后验。

如果用户追问数据源，额外说明：

- FIFA official lineup/squad/profile 已获得，但只有 lineup CSV 会直接影响 lambda。
- StatsBomb 球员表现和事件样本是部分覆盖，不能说成全量。
- 伤停/停赛没有单独来源时，不要从未进首发或未进名单推断。
- 替补策略若没有官方换人计划，只能解释为默认 expected minutes，而不是教练真实计划。

## 整届赛事模拟

```powershell
python -m worldcup_predictor simulate-tournament --runs 20000 --use-generated-context
```

如需让赛事模拟也使用 Dixon-Coles 比分矩阵抽样：

```powershell
python -m worldcup_predictor simulate-tournament --runs 20000 --use-generated-context --score-model dixon_coles
```

输出：

- `outputs/predictions/tournament_odds.csv`
- `outputs/predictions/group_rankings.csv`

注意：这里的 `tournament_odds.csv` 是模拟概率，不是博彩赔率。

## 中文报告

```powershell
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --sample-match-id 97 --use-generated-context
```

生成 Dixon-Coles 版本中文报告：

```powershell
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --sample-match-id 97 --use-generated-context --score-model dixon_coles
```

生成包含单场不确定性区间的中文报告：

```powershell
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --sample-match-id 97 --use-generated-context --include-uncertainty
```

输出：

- `outputs/predictions/match_predictions.json`
- `outputs/predictions/group_rankings.csv`
- `outputs/predictions/tournament_odds.csv`
- `outputs/reports/worldcup_prediction_report.md`

报告中应包含：

- `## 单场示例`
- `## 单场解释`
- `## 2026 赛制随机性`
- `## 冠军概率 Top 10`
- `## 小组排名概率摘要`

其中 `2026 赛制随机性` 段落受 `javierruanohdez/world-cup-2026-prediction` 启发，只解释当前 Monte Carlo 模拟下的冠军概率分散程度。它会显示最高冠军概率、Top 3/Top 10 冠军概率集中度、冠军概率不低于 5%/1% 的球队数和有效争冠球队数；它不改变单场胜平负、比分或 tournament sampling。

## 回测

```powershell
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1
```

Dixon-Coles 回测：

```powershell
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1 --score-model dixon_coles
```

重点指标：

- `log_loss`
- `brier_score`
- `ranked_probability_score`
- `calibration`
- `config.score_model`
- `outcome_accuracy`
- `exact_score_accuracy`
- `top3_scoreline_accuracy`
- `home_goal_mae` / `away_goal_mae` / `total_goal_mae` / `combined_goal_mae`
- `home_goal_rmse` / `away_goal_rmse` / `total_goal_rmse` / `combined_goal_rmse`

如果新增数据特征或比分模型，只有在 time-safe 回测或前向验证改善这些指标时，才应默认开启。当前 `dixon_coles` 是可选模型，默认仍是 `independent_poisson`。评估时不要只看一个指标：概率质量看 log-loss/Brier/RPS/calibration，比分质量看 exact score accuracy、top-3 scoreline accuracy 和 goal MAE/RMSE。

## Dixon-Coles rho tuning

受 `alan-turing-institute/WorldCupPrediction` 的 Dixon-Coles 标杆启发，当前系统提供一个 `rho` 参数网格回测：

```powershell
python -m worldcup_predictor tune-dixon-coles --start-year 2018 --min-prior-matches 1
```

指定候选参数：

```powershell
python -m worldcup_predictor tune-dixon-coles --start-year 2018 --min-prior-matches 1 --rho-values "-0.16,-0.12,-0.08,-0.04,0.0"
```

输出文件：

```powershell
outputs\reports\dixon_coles_rho_tuning.json
```

读取重点：

- `results`
- `best_by_log_loss`
- `best_by_ranked_probability_score`
- `deltas_vs_independent`
- `gate.default_enable_recommended`
- `gate.reason`

解释口径：

- 这是调参报告，不会自动改变默认预测。
- 它只调 Dixon-Coles 低比分相关性的 `rho`，不新增球队、阵容、天气、裁判或球员数据。
- 若 gate 不推荐，默认仍用 `independent_poisson`。
- 若 gate 推荐，也应显式传入 `--score-model dixon_coles --dixon-coles-rho <value>` 才能影响预测。

## W/D/L calibration gate

受 `rivu-intel45/FIFA-2026-Winner-Prediction` 的 XGBoost 分类模型思路启发，当前系统提供一个默认关闭的胜平负概率校准回测门禁：

```powershell
python -m worldcup_predictor calibration-backtest --start-year 2018 --min-prior-matches 1
```

输出文件：

```powershell
outputs\reports\calibration_backtest.json
```

读取重点：

- `training.uncalibrated`
- `training.temperature_calibrated`
- `evaluation.uncalibrated`
- `evaluation.temperature_calibrated`
- `deltas`
- `gate.default_enable_recommended`
- `gate.reason`

解释口径：

- 这是可选校准评估，不是 XGBoost 主模型。
- 它只用历史预测概率拟合 `temperature + draw_multiplier`，再做 out-of-sample 评估。
- 它不会改变当前生产预测的胜平负、比分、事件数量或赛事模拟。
- 只有当 log-loss/Brier/RPS 至少两个改善，且 ECE 没有明显变差，才可以考虑后续接入。

## FIFA ranking baseline

受 `kamil-kucharski/world-cup-2026-prediction` 启发，当前系统提供一个简单 baseline：

```powershell
python -m worldcup_predictor ranking-baseline --home France --away Senegal
```

输出文件：

```powershell
outputs\reports\ranking_baseline_sanity_check.json
```

读取重点：

- `main_model`
- `ranking_baseline`
- `comparison`
- `ranking_baseline.features`
- `ranking_baseline.caveats`

解释口径：

- 这是 sanity check，不是正式预测。
- 它只使用当前 FIFA rank/points 和世界杯历史平均进球。
- 它不使用 Elo、近期状态、世界杯球队历史、阵容、球员评分、天气、旅行、战术、裁判、事件样本。
- 它使用当前 FIFA ranking snapshot，因此不是 time-safe 历史回测。
- 如果主模型和 baseline 差异很大，应解释差异来自哪些额外因素，而不是直接说 baseline 错了。

## 测试

```powershell
python -m unittest discover -s tests -v
```

关键不变量：

- 赛程必须 104 场。
- 球队必须 48 支。
- 未完赛 raw 0-0 不能成为真实比分。
- 胜平负概率和约等于 1。
- Top scorelines 按概率降序。
- 缺 Elo 时 fallback 1500 且 warning。
- 单场预测必须包含 `explanation`，且至少包含 `team_strength`、`lineup_and_availability`、`match_context`、`event_counts`、`data_quality`。
- 单场预测必须包含 `score_model` 和 `score_model_parameters`。
- 当传入 `--include-uncertainty` 时，单场预测必须包含 `uncertainty.intervals`，并且 `p05 <= p50 <= p95`。
- 回测必须包含 pameldas-inspired 指标：`exact_score_accuracy`、`top3_scoreline_accuracy`、`combined_goal_mae`、`combined_goal_rmse`。
- `tune-dixon-coles` 必须输出 `results`、`best_by_log_loss`、`deltas_vs_independent` 和 `gate.default_enable_recommended`，且 `config.default_changes_prediction=false`。
- `calibration-backtest` 必须输出 `evaluation.uncalibrated`、`evaluation.temperature_calibrated`、`deltas` 和 `gate.default_enable_recommended`，且 `config.default_changes_prediction=false`。
- `ranking-baseline` 输出必须包含 `main_model`、`ranking_baseline`、`comparison`，且 baseline 的胜平负概率和约等于 1。
- 中文报告必须包含 `2026 赛制随机性`、`冠军概率集中度` 和 `有效争冠球队数`。
- 小组前二加 8 个最佳第三名共 32 队晋级。
- 每次赛事模拟必须唯一冠军。

## 常见排错

- `FileNotFoundError`：先运行 `refresh-data` 或 `build-context-data`，再做健康检查。
- 阵容文件报错：检查 `source`、`rating_basis`、`official=true` 和 `--lineup-allowed-source`。
- 预测结果看起来太确定：检查是否误用了赛后数据或实际比分。
- 事件数量 warnings 很多：说明该队没有事件样本，模型退回全局半场 rates。
- 天气 warning：说明没有匹配到本场精确 kickoff 天气，应在赛前刷新或显式提供天气文件。
- 数据源目录缺失：先运行相关数据刷新/补齐脚本，再将来源、类型、文件、Agent、赛前安全性补入 `outputs/reports/worldcup_data_source_catalog.md` 和 `references/data-contracts.md`。
