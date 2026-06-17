# worldcup-predict

这是一个基于 Codex 的世界杯预测模型 skill，用来操作当前本地的 `worldcup_predictor` 多 Agent 系统。

## 这个 skill 做什么

- 运行单场比赛预测：胜平负概率、最可能比分、预期进球。
- 运行整届世界杯模拟：小组排名、晋级概率、淘汰赛路径、冠军概率。
- 生成中文报告：`outputs/reports/worldcup_prediction_report.md`。
- 解释 2026 新赛制随机性：报告会基于 Monte Carlo 冠军概率，输出最高冠军概率、Top 3/Top 10 集中度、有效争冠球队数，以及 48 队/12 组/32 强/5 轮淘汰赛带来的概率分散。
- 输出单场不确定性区间：可用 `--include-uncertainty` 生成胜平负和预期总进球的 p05/p50/p95 区间。
- 追加预测审计日志：`outputs/audit/prediction_runs.jsonl` 记录命令、模型参数、输入文件 hash/行数、输出概率和 warning。
- 运行简单对照 baseline：`ranking-baseline` 使用 FIFA rank/points + Poisson 做 sanity check。
- 运行胜平负概率校准门禁：`calibration-backtest` 受 rivu-intel45 的分类模型思路启发，用 time-safe 回测判断一个轻量校准层是否值得后续接入。
- 运行 Dixon-Coles 参数调参：`tune-dixon-coles` 受 Alan Turing Institute 项目的 Dixon-Coles 标杆启发，用 time-safe 回测比较多个 `rho` 候选。
- 检查数据是否齐全：赛程、球队、世界杯历史赛果、Elo、FIFA 排名、球员评分、阵容接口、天气、旅行疲劳、战术、裁判和事件样本。
- 评估模型质量：回测输出 log-loss、Brier、RPS、校准桶、胜平负 accuracy、exact score accuracy、top-3 scoreline accuracy、goal MAE/RMSE。
- 记录数据来源和数据类型：`outputs/reports/worldcup_data_source_catalog.md`。
- 输出全面中文解释：球队强度、lambda 变化、阵容/伤停/替补、球员表现、天气、旅行疲劳、战术、裁判、事件数量和数据缺口。

## 主要文件

- `SKILL.md`：Codex 调用这个 skill 时优先读取的执行规则。
- `references/model-overview.md`：多 Agent 架构和预测方法。
- `references/data-contracts.md`：数据来源、文件路径、当前可用状态和 caveat。
- `references/commands-and-validation.md`：常用命令、输出文件和验证流程。
- `scripts/health_check.py`：快速检查本地预测模型是否具备运行条件。
- `outputs/audit/prediction_runs.jsonl`：pravindurgani 启发的 append-only 预测审计日志。

## 解释输出要求

`predict-match` 的 JSON 会包含 `explanation` 字段。使用这个 skill 时，应优先读取该字段，并在中文回答中覆盖：

- 胜平负、比分、预期进球。
- Elo、FIFA 排名、近期状态、世界杯历史。
- 基础进球期望到最终进球期望的变化。
- 官方阵容、伤停、替补策略和球员评分是否进入计算。
- 球员表现、天气、旅行疲劳、战术和裁判上下文。
- 黄牌、红牌、角球、任意球、点球的上下半场预测。
- 整届赛事报告里的 2026 赛制随机性：这是 javierruanohdez 项目启发的解释层，只总结当前模拟结果，不改变单场概率。
- 缺失数据和 fallback。
- 比分模型和不确定性区间；不确定性区间是 lbenz730 Bayesian 思路启发的轻量 lambda 扰动代理，不是完整 Bayesian 模型。

## 推荐用法

在包含 `worldcup_predictor/` 的项目根目录运行：

```powershell
python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root .
python -m worldcup_predictor predict-match --home France --away Senegal --match-id 97 --use-generated-context
python -m worldcup_predictor predict-match --home France --away Senegal --include-uncertainty
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1
python -m worldcup_predictor tune-dixon-coles --start-year 2018 --min-prior-matches 1
python -m worldcup_predictor calibration-backtest --start-year 2018 --min-prior-matches 1
python -m worldcup_predictor ranking-baseline --home France --away Senegal
python -m worldcup_predictor report --runs 20000 --use-generated-context
```

查看预测审计日志最后一条：

```powershell
Get-Content -Encoding UTF8 outputs\audit\prediction_runs.jsonl -Tail 1
```

查看数据源目录：

```powershell
Get-Content -Encoding UTF8 outputs\reports\worldcup_data_source_catalog.md
```

如果要让阵容、伤停和替补策略进入模型，需要提供赛前可信的 lineup CSV：

```powershell
python -m worldcup_predictor predict-match --home Spain --away "Cape Verde" --match-id 1 `
  --lineup-file inputs\lineups\template.csv `
  --lineup-allowed-source manual-template `
  --player-ratings-file inputs\player_ratings\eafc26_player_ratings.csv `
  --use-generated-context
```

奥地利 vs 约旦 match20 已有专门的赛前补齐脚本：

```powershell
python worldcup_data_audit\scripts\build_match20_gap_inputs.py
python -m worldcup_predictor predict-match --home Austria --away Jordan --match-id 20 `
  --use-generated-context `
  --lineup-file inputs\lineups\match20_austria_jordan_fifa_official.csv `
  --lineup-allowed-source fifa_api_live_match `
  --player-ratings-file inputs\player_ratings\eafc26_player_ratings.csv
```

## 当前边界

- 真实赔率没有进入模型。
- EA FC 球员评分可以作为阵容评分 fallback，但不是 FIFA 官方球员评分。
- FIFA 官方首发和替补可以从 live match 接口落到 lineup CSV；伤停和停赛必须有独立可信来源后才填入。
- FIFA 球员资料不是完整俱乐部+国家队逐场表现，不能替代球员表现样本。
- 天气、裁判、球员表现和事件样本目前有可运行的本地数据，但覆盖度仍需在正式预测前复核。
- `--include-uncertainty` 只给点估计外的区间，不改变胜平负点估计，也不是完整 Bayesian bivariate Poisson 后验。
- 审计日志只记录本地命令、文件元数据和模型输出，不会自动拉取 live API，也不会改变预测结果。
- `ranking-baseline` 是 kamil-kucharski 启发的简单对照工具，只用当前 FIFA ranking/points，不是生产模型，也不是 time-safe 历史回测。
- `calibration-backtest` 是默认关闭的评估工具，只输出是否值得后续接入校准层；当前不会改变比分、胜平负、事件数或赛事模拟。
- `tune-dixon-coles` 是默认关闭的调参报告；即使某个 rho 表现更好，也需要显式使用 `--score-model dixon_coles --dixon-coles-rho <value>` 才会影响预测。
- 2026 赛制随机性段落只解释赛事结构和 Monte Carlo 输出的分散程度，不是新增数据源，也不会改变胜平负/比分点估计。
