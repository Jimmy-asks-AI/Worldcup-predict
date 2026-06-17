# GitHub 世界杯预测项目与本地 worldcup_predictor 对比

Generated: 2026-06-17

## 对比对象

| 项目 | 类型 | 核心方法 | 链接 |
|---|---|---|---|
| Hicruben/world-cup-2026-prediction-model | 透明统计模型 | Elo -> Dixon-Coles bivariate Poisson -> Monte Carlo | https://github.com/Hicruben/world-cup-2026-prediction-model |
| lbenz730/world_cup_2026 | 学术/贝叶斯统计模型 | Bayesian bivariate Poisson -> 10,000 tournament simulations | https://github.com/lbenz730/world_cup_2026 |
| pameldas/FIFA-World-Cup-2026-Prediction-Framework | 混合 ML/统计框架 | Elo + recent form + Random Forest evaluation + Poisson + Monte Carlo | https://github.com/pameldas/FIFA-World-Cup-2026-Prediction-Framework |
| rivu-intel45/FIFA-2026-Winner-Prediction | ML 分类器 | XGBoost + Elo + form + H2H + tournament simulation | https://github.com/rivu-intel45/FIFA-2026-Winner-Prediction |
| EhteshamBahoo/Fifa-WorldCup-Data-Analysis-1930-2026 | Notebook/教学型 ML | Wikipedia World Cup data + Random Forest Regressor + knockout simulation | https://github.com/EhteshamBahoo/Fifa-WorldCup-Data-Analysis-1930-2026 |
| kamil-kucharski/world-cup-2026-prediction | Notebook/Poisson | FIFA ranking/points + Poisson regression + Monte Carlo | https://github.com/kamil-kucharski/world-cup-2026-prediction |
| pravindurgani/wc26-matchday-intelligence | 生产型 live dashboard | Elo baseline + live injury/weather/lineup/stats adjustments + audit log + dashboard | https://github.com/pravindurgani/wc26-matchday-intelligence |
| ysadre/FifaWC_Predictions | 2022 分类模型 | Kaggle international results + classification model | https://github.com/ysadre/FifaWC_Predictions |
| jieguangzhou/FIFA-World-Cup-2022 | MLOps/工作流 | FLAML training + prediction + betting workflow | https://github.com/jieguangzhou/FIFA-World-Cup-2022 |

## 我们的模型定位

`worldcup_predictor` 是本地 CLI + 报告型多 Agent 系统：

- `DataAgent`：赛程、球队、已完赛比分校验。
- `StrengthAgent`：Elo、FIFA 排名、近期状态、世界杯历史强度。
- `LineupAgent`：官方首发、替补、伤停/停赛、expected minutes、球员评分 fallback。
- `MatchContextAgent`：球员表现、天气、旅行疲劳、战术、裁判。
- `EventAgent`：黄牌、红牌、角球、任意球、点球上下半场预测。
- `ScorelineAgent`：独立 Poisson 0-0 到 7-7 比分矩阵。
- `TournamentAgent`：20,000 Monte Carlo，锁定已完赛结果，模拟 32 强到冠军。
- `ReportAgent`：中文 Markdown/JSON/CSV 报告。
- `BacktestAgent`：历史 rolling backtest。

## 总体结论

我们的模型不是单纯“更强”或“更弱”，而是定位不同：

- 在透明度和可解释性上，我们接近 Hicruben/lbenz 这类统计模型，但目前没有 Dixon-Coles 或 Bayesian bivariate Poisson。
- 在数据覆盖上，我们比多数 Notebook 型项目更广，已经接入官方阵容、天气、旅行、战术、裁判、球员表现、事件数量。
- 在 live 自动化和生产 dashboard 上，pravindurgani 的项目更强，有 GitHub Actions、API-Football、Vercel dashboard 和 append-only audit log。
- 在机器学习分类上，rivu/pameldas 更偏 XGBoost/Random Forest；我们的主模型更保守，强调概率、比分矩阵和赛前数据防泄漏。
- 在赛事规则上，我们实现了 2026 的 104 场、48 队、最佳第三名、32 强 bracket；这一点比很多 2022/Notebook 项目完整。
- 最大短板是：没有完整球员表现商业数据、没有真实赔率、没有指定裁判历史、没有全量伤停源、没有 Dixon-Coles draw correction。

## 核心维度对比

| 维度 | 我们的 worldcup_predictor | GitHub 项目整体表现 | 判断 |
|---|---|---|---|
| 单场胜平负 | Poisson score matrix 汇总 | Elo/Poisson/XGBoost/Random Forest 都有 | 我们稳定、透明；不追求黑盒分类精度 |
| 精确比分 | 输出 0-0 到 7-7 Top scorelines | Hicruben/lbenz/kamil/pameldas 有；XGBoost 项目通常弱一些 | 我们具备，但独立 Poisson 低比分相关性不足 |
| Draw correction | 暂无 Dixon-Coles | Hicruben 明确使用 Dixon-Coles | 我们应补 |
| Bayesian uncertainty | 暂无 | lbenz 使用 Bayesian bivariate Poisson | 我们应补置信区间/后验不确定性 |
| 赛事模拟 | 20,000 Monte Carlo，锁定已完赛 | 多数项目有 Monte Carlo；Hicruben 50,000，lbenz 10,000 | 我们够用，但可提高模拟数和输出置信区间 |
| 2026 bracket | 已支持 104 场、最佳第三名、32 强 | 部分项目支持；有些只 notebook 简化 | 我们较强 |
| 回测 | 有 rolling backtest 指标 | Hicruben/pameldas/pravindurgani 有较强评估；Notebook 型较弱 | 我们已有框架，但新增特征仍需单独回测 |
| 数据源审计 | 已有 `worldcup_data_source_catalog.md` | 大多 README 简述数据源 | 我们较强 |
| 官方阵容 | 已能从 FIFA live endpoint 生成 lineup CSV | pravindurgani 使用 API-Football lineups；多数项目没有 | 我们较强，但只做了 match20 示例 |
| 伤停 | 只留接口，未获取稳定源 | pravindurgani 有 API-Football injuries + manual overlay | 对方强 |
| 球员表现 | StatsBomb open sample，覆盖不全 | 多数项目没有；pravindurgani 用 stats proxy，不是真 xG | 我们有入口，但数据覆盖弱 |
| 天气 | Open-Meteo exact kickoff / sample | pravindurgani 有 weather live layer；其他少见 | 我们较强 |
| 裁判 | 全局 prior，非指定裁判历史 | pravindurgani 明确未建模；多数没有 | 我们有雏形，但还弱 |
| 事件数量 | 黄牌/红牌/角球/任意球/点球分半场 | 多数项目只预测胜负/冠军 | 我们明显更广 |
| 中文解释 | 结构化 explanation + 中文报告 | GitHub 项目一般是英文 README/notebook | 我们强 |
| MLOps/live | 本地 CLI，少自动化 | pravindurgani/jieguangzhou 更强 | 我们弱 |

## 分项目对比

### Hicruben/world-cup-2026-prediction-model

强项：

- Elo -> Dixon-Coles bivariate Poisson -> Monte Carlo，方法干净。
- 有 walk-forward out-of-sample backtest，使用 RPS/log-loss/Brier/ECE。
- 生产模型会锁定已完赛结果，模拟剩余赛程。

相对我们：

- 它的比分模型更专业，Dixon-Coles 能修正低比分平局。
- 我们的数据上下文更广，有阵容、天气、事件数量和中文解释。
- 我们应该借鉴它的 Dixon-Coles、校准评估和更清晰的 track record。

### lbenz730/world_cup_2026

强项：

- Bayesian bivariate Poisson，统计建模更严谨。
- 有 10,000 次 tournament simulation。
- 自动更新 live scores，完整 pipeline 较清晰。

相对我们：

- 它在不确定性建模上更强。
- 我们在多源赛前上下文、官方阵容、事件数量预测上更广。
- 我们应借鉴 Bayesian uncertainty 或至少输出预测区间。

### pameldas/FIFA-World-Cup-2026-Prediction-Framework

强项：

- 有数据清洗、特征工程、Elo、recent form、Poisson、Random Forest evaluation。
- 报告给出 accuracy、F1、log loss、score MAE/RMSE、exact score accuracy。
- 最终选择 Poisson 100%、Random Forest 0%，说明做过权重选择。

相对我们：

- 它的评估报告比普通 Notebook 规范。
- 我们的数据契约和模型解释更完整。
- 我们应学习它把 exact score accuracy、MAE/RMSE 加入报告。

### rivu-intel45/FIFA-2026-Winner-Prediction

强项：

- XGBoost 分类器，特征包括 Elo、近期状态、进失球、H2H、neutral、tournament weight。
- 适合做胜平负分类，容易扩展特征。

相对我们：

- 它的分类模型可能在 W/D/L 上拟合能力更强，但不天然给精确比分分布。
- 我们的 Poisson score matrix 对比分、总进球、赛事模拟更自然。
- 可以把 XGBoost 作为校准层，而不是替代 Poisson。

### EhteshamBahoo/Fifa-WorldCup-Data-Analysis-1930-2026

强项：

- 入门完整：Wikipedia scraping、清洗、Random Forest Regressor、淘汰赛模拟、CSV 输出。

相对我们：

- 它更像教学项目，历史数据范围主要是世界杯 1930-2022。
- 我们更接近实际可运行预测系统，数据源、赛前安全和解释边界更完整。

### kamil-kucharski/world-cup-2026-prediction

强项：

- 简洁：FIFA rank/points、rank diff、points diff、host/neutral -> Poisson regression。
- 完整模拟 group stage、best third-placed teams、R32 到 final。

相对我们：

- 它方法轻量，容易理解。
- 我们数据更多、Agent 更多、输出更多；代价是复杂度更高。
- 可借鉴其简单特征作为 baseline sanity check。

### pravindurgani/wc26-matchday-intelligence

强项：

- 最接近生产系统：dashboard、GitHub Actions、live results、injuries、weather、lineups、match stats、audit log。
- 有 caps：injury/weather/lineup/stats 都转成 Elo adjustment，并有总上限，避免过拟合。
- 有夜间重训、live workflows、pre-launch validation。

相对我们：

- 它的 live/MLOps 能力明显强于我们。
- 我们的事件数量预测和官方 FIFA lineup 接入更直接；但它的 injury/lineup automation 更实用。
- 我们应优先借鉴：append-only audit log、matchday intelligence caps、自动刷新机制。

### 2022 类项目：ysadre / jieguangzhou / lblommesteyn

共同特点：

- 多为 2022 赛前/赛中实验。
- 强调 ML 分类、工作流或下注策略。
- 数据大多来自 Kaggle/international results，模型以分类器或 FLAML 为主。

相对我们：

- 它们对“工作流”和“分类器实验”有参考价值。
- 但多数不具备 2026 赛制、官方阵容、天气、事件数量、数据契约和中文解释。

## 我们应该吸收的改进

优先级从高到低：

1. 加 Dixon-Coles correction：修正 0-0、1-1 这类低比分平局，直接提升比分矩阵合理性。
2. 增加校准报告：每次回测输出 RPS/log-loss/Brier/ECE、reliability curve、exact score accuracy、goal MAE/RMSE。
3. 建 matchday intelligence 层：把伤停、天气、官方阵容、旅行、裁判变成有上限的 Elo/lambda adjustment，并记录每次调整原因。
4. 建 append-only 数据审计日志：每次数据刷新写 JSONL，记录 source、timestamp、row count、字段、是否进入模型。
5. 扩展官方阵容脚本：从 match20 扩到所有 match_id，赛前 90/60/30 分钟可重复刷新。
6. 明确新增特征 gate：任何新特征默认关闭，只有 rolling backtest 改善 log-loss/RPS/Brier 后才默认开启。
7. 若用户接受商业数据：接 API-Football/StatsBomb/Opta/Sportradar 之一，补完整伤停、lineups、球员表现和指定裁判历史。

## 最终判断

- 如果目标是“数学上干净的冠军概率”：Hicruben 和 lbenz 的建模更值得借鉴。
- 如果目标是“临场预测系统”：pravindurgani 的 live matchday intelligence 架构最值得借鉴。
- 如果目标是“中文可解释、多数据源、Codex 本地可运行 skill”：我们当前模型更贴近这个定位。
- 下一步最有价值的不是继续堆数据，而是把新增数据通过回测验证权重，并补 Dixon-Coles / calibration / live audit log。
