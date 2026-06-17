# 世界杯预测模型架构

## 定位

`worldcup_predictor` 是本地可重复运行的 CLI + 报告型世界杯预测系统。核心输出是概率，不是确定结论。

## Agent 列表

- `DataAgent`：加载和校验本地 CSV；统一队名；要求 104 场赛程和 48 支球队；只把 `finished=TRUE` 且有 `actual_home_score/actual_away_score` 的比赛当作真实赛果。
- `StrengthAgent`：生成球队强度。使用自算 Elo、近期国家队进失球/积分、世界杯历史进失球、FIFA 男足排名，并给主办国轻量修正。
- `LineupAgent`：可选。读取赛前首发、伤停、停赛、替补、预计出场时间和球员评分；默认要求首发 `official=true`，拒绝 post-match/live rating。
- `PlayerRatingsAgent`：可选。读取 EA FC 26/FIFA26-style 球员评分，只在 lineup 行缺少 rating 时做 fallback。
- `MatchContextAgent`：可选。读取球员历史表现、天气、旅行疲劳、战术、裁判倾向，输出对两队进球 lambda 的乘数调整。
- `EventAgent`：自动读取半场事件样本，预测黄牌、红牌、角球、任意球、点球的上半场、下半场和全场数量。
- `ScorelineAgent`：把球队强度、阵容和上下文调整转换成两队进球期望；用 0-0 到 7-7 的比分矩阵计算比分概率和胜平负概率；默认是独立 Poisson，可用 `--score-model dixon_coles` 启用 Dixon-Coles 低比分相关性修正；同时输出 `explanation` 结构化中文解释。
- `UncertaintyAgent`：可选。用 `--include-uncertainty` 围绕最终 lambda 做固定种子的轻量扰动，输出胜平负和预期总进球的 p05/p50/p95 区间；这是 lbenz730 Bayesian bivariate Poisson 思路启发的代理，不是完整 Bayesian 后验。
- `TournamentAgent`：用单场模型跑 Monte Carlo。锁定已完赛真实结果，模拟小组积分、最佳第三名、32 强到决赛；淘汰赛平局用 Elo 倾斜点球概率决胜。
- `ReportAgent`：写 JSON/CSV/Markdown 输出，把 `explanation` 写入 Markdown 的“单场解释”部分，并加入 javierruanohdez 启发的“2026 赛制随机性”摘要。
- `BacktestAgent`：用历史世界杯赛果做 rolling backtest，输出 log loss、Brier score、RPS、校准桶、胜平负 accuracy、exact score accuracy、top-3 scoreline accuracy、goal MAE/RMSE。
- `DixonColesTuning`：受 Alan Turing Institute 的 Dixon-Coles 标杆启发，使用 `tune-dixon-coles` 对多个 rho 候选做 time-safe backtest；只输出推荐证据，不自动改变默认模型。
- `CalibrationAgent`：受 rivu-intel45 的分类预测思路启发，默认关闭。它只做 time-safe W/D/L 概率校准门禁：在历史预测上拟合轻量 temperature + draw multiplier，再评估 log-loss、Brier、RPS、ECE 是否改善。
- `AuditAgent`：受 pravindurgani matchday intelligence audit log 启发，把 `predict-match` 和 `report` 的样例预测追加写入 `outputs/audit/prediction_runs.jsonl`；记录命令、模型参数、输入文件元数据、pre-match safety flags、输出概率和 warnings，不参与概率计算。
- `RankingBaselineAgent`：受 kamil-kucharski 项目启发，只用 FIFA rank/points 和世界杯历史平均进球生成简单 Poisson baseline，用来和主模型做 sanity check；不参与默认预测。

## 单场预测方法

1. 从世界杯历史赛果得到基础进球率。
2. 用近期状态、世界杯历史表现、Elo 差和 FIFA 排名得到两队基础进球期望 `lambda_home` / `lambda_away`。
3. 如果传入 lineup，把首发质量、伤停损失、替补预计分钟和球员评分变成攻防乘数。
4. 如果传入 context，把球员表现、天气、旅行疲劳、战术和裁判变成攻防/总进球/定位球/纪律乘数。
5. 用比分模型计算 0-0 到 7-7 的比分概率，并归一化。默认 `independent_poisson`；可选 `dixon_coles` 会按 rho 参数修正 0-0、0-1、1-0、1-1 这类低比分相关性。
6. 把比分矩阵按主胜、平、客胜汇总成胜平负概率。
7. 如果启用 `--include-uncertainty`，对最终 lambda 做 lognormal 扰动样本，输出 p05/p50/p95 区间；这不改变胜平负点估计。
8. 用事件样本和上下文指数输出卡牌、角球、任意球、点球数量预测。
9. 生成 `explanation` 字段，统一解释结论、方法、球队强度、lambda 路径、阵容、上下文、事件数量、不确定性和数据缺口。
10. CLI 运行 `predict-match` 或 `report` 时追加审计日志，方便之后追溯该次预测使用的数据和模型参数。

## Baseline sanity check

`ranking-baseline` 不是正式预测模型。它只用于回答一个工程问题：如果只看当前 FIFA 排名/积分和历史平均进球，一个极简 Poisson baseline 会给出什么结果，主模型和它差在哪里。

它不会使用：

- Elo。
- 近期状态。
- 世界杯球队历史。
- 阵容/伤停。
- 球员评分。
- 天气、旅行、战术、裁判。
- 事件样本。

因此它只能作为 sanity check，不能作为 time-safe 历史回测，也不能替代主模型。

## Calibration gate

`calibration-backtest` 不是生产预测模型。它回答的问题是：如果借鉴 XGBoost/分类器项目的“胜平负概率校准”思路，一个很轻量的校准层是否能在 time-safe 回测中改善概率质量。

当前实现只使用：

- 主比分模型输出的未校准胜平负概率。
- temperature scaling。
- draw multiplier。
- rolling World Cup-only historical predictions and actual results。

它不会使用：

- XGBoost 或 Random Forest。
- 新的球队/球员数据。
- 阵容、天气、裁判、事件样本。
- 精确比分矩阵重构。

解释时应看 `gate.default_enable_recommended`。只有当校准层至少改善两个概率损失指标，并且 ECE 没有明显变差，才可以把它视为后续接入候选；否则继续默认关闭。

## Dixon-Coles rho tuning

`tune-dixon-coles` 回答的问题是：如果使用 Dixon-Coles 低比分相关性修正，哪个 `rho` 值在历史 rolling backtest 中更稳。

它会输出：

- independent Poisson baseline。
- 多个 Dixon-Coles `rho` 候选的 log-loss、Brier、RPS、accuracy、exact score accuracy、top-3 scoreline accuracy、goal MAE/RMSE。
- `best_by_log_loss`。
- `best_by_ranked_probability_score`。
- `deltas_vs_independent`。
- `gate.default_enable_recommended`。

这个调参报告不会自动改默认预测。若要让某次预测使用候选 rho，必须显式传入 `--score-model dixon_coles --dixon-coles-rho <value>`。

## 单场解释字段

`predict-match` 的 JSON 应优先读取 `explanation`：

- `headline`：一句话结论，例如哪队更可能赢，以及概率。
- `method`：模型链路，不允许只说“AI 预测”。
- `outcome`：胜平负、最可能比分、Top 比分、预期进球。
- `lambda_path`：基础进球期望到最终进球期望的变化。
- `factors.team_strength`：Elo、FIFA 排名/积分、近期进失球、世界杯历史表现。
- `factors.lineup_and_availability`：官方首发、伤停、停赛、替补策略、球员评分是否进入模型。
- `factors.match_context`：球员表现、旅行疲劳、战术、天气、裁判。
- `factors.event_counts`：黄牌、红牌、角球、任意球、点球的上下半场预测。
- `factors.uncertainty`：是否启用不确定性区间，以及胜平负/预期总进球的 p05/p50/p95 区间。
- `factors.data_quality`：缺失数据、fallback 和本场可信度边界。
- `warnings` / `caveats`：必须向用户解释，不要隐藏。

## 整届赛事模拟方法

1. 每次 Monte Carlo 按赛程模拟所有小组赛。
2. 已完赛比赛使用真实比分，不重新模拟。
3. 小组积分规则：胜 3 分、平 1 分、负 0 分；排名按积分、净胜球、进球数，再用固定随机种子处理完全并列。
4. 每组前二加 8 个最佳第三名晋级 32 强。
5. 最佳第三名分配按赛程 slot 的允许小组回溯分配，不随机乱配。
6. 淘汰赛继续用单场比分模型抽样；如果启用 Dixon-Coles，Monte Carlo 抽样也使用修正后的比分矩阵；打平则用 Elo 倾斜的点球概率决胜。
7. 汇总所有模拟次数得到晋级概率、进决赛概率、冠军概率、预期积分和预期净胜球。
8. 中文报告会从冠军概率分布中派生赛制随机性指标：最高冠军概率、Top 3/Top 10 冠军概率集中度、冠军概率不低于 5%/1% 的球队数、Herfindahl 指数折算的有效争冠球队数。这个解释层只总结模拟输出，不改变单场或赛事抽样逻辑。

## 解释口径

对用户解释时，用“这个模型认为”“概率上更可能”这类表达。不要说“必胜”“确定比分”。最可能比分通常单个概率不高，应同时给胜平负和 Top scorelines。解释必须覆盖主要影响因素；如果某个因素没有进入计算，要明确说“接口支持，但本次没有可信输入，所以保持中性”。还要说明本次使用的比分模型：默认独立 Poisson，或 Hicruben 启发的 Dixon-Coles 低比分修正。若启用了不确定性区间，要说明它是 lbenz730 启发的轻量 lambda 扰动区间，不是完整 Bayesian bivariate Poisson。若解释整届赛事，要说明 2026 新赛制会让冠军概率天然更分散，但这个判断必须来自报告中已计算的集中度指标，而不是主观描述。
