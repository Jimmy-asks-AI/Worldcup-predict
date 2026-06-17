# GitHub 世界杯预测项目完整评审与 worldcup_predictor 改进计划

Generated: 2026-06-17

## 1. 评审范围

本报告面向一个明确目标：把已经在 GitHub 上找到的世界杯预测项目逐个评价，并和本地 `worldcup_predictor` 多 Agent 预测系统对比，最后给出能落地的改进计划。

本轮纳入 13 个可访问项目，另记录 1 个此前提到但当前不可访问的项目：

| 类别 | 项目 | 链接 | 当前评审状态 |
|---|---|---|---|
| 2026 透明统计模型 | Hicruben/world-cup-2026-prediction-model | https://github.com/Hicruben/world-cup-2026-prediction-model | 已评审 |
| 2026 Bayesian 统计模型 | lbenz730/world_cup_2026 | https://github.com/lbenz730/world_cup_2026 | 已评审 |
| 2026 混合 ML/统计框架 | pameldas/FIFA-World-Cup-2026-Prediction-Framework | https://github.com/pameldas/FIFA-World-Cup-2026-Prediction-Framework | 已评审 |
| 2026 XGBoost 分类模型 | rivu-intel45/FIFA-2026-Winner-Prediction | https://github.com/rivu-intel45/FIFA-2026-Winner-Prediction | 已评审 |
| 2026 Notebook/教学型预测 | EhteshamBahoo/Fifa-WorldCup-Data-Analysis-1930-2026 | https://github.com/EhteshamBahoo/Fifa-WorldCup-Data-Analysis-1930-2026 | 已评审 |
| 2026 Poisson Notebook | kamil-kucharski/world-cup-2026-prediction | https://github.com/kamil-kucharski/world-cup-2026-prediction | 已评审 |
| 2026 live matchday intelligence | pravindurgani/wc26-matchday-intelligence | https://github.com/pravindurgani/wc26-matchday-intelligence | 已评审 |
| 2026 Gradient Boosting + Monte Carlo | javierruanohdez/world-cup-2026-prediction | https://github.com/javierruanohdez/world-cup-2026-prediction | 补充评审 |
| 2022 分类模型 | ysadre/FifaWC_Predictions | https://github.com/ysadre/FifaWC_Predictions | 已评审 |
| 2022 FLAML 工作流 | jieguangzhou/FIFA-World-Cup-2022 | https://github.com/jieguangzhou/FIFA-World-Cup-2022 | 已评审 |
| 通用 Dixon-Coles 标杆 | alan-turing-institute/WorldCupPrediction | https://github.com/alan-turing-institute/WorldCupPrediction | 补充评审 |
| R 语言 ML 教程 | neaorin/PredictTheWorldCup | https://github.com/neaorin/PredictTheWorldCup | 补充评审 |
| 多算法分类/分组项目 | neelabhsinha/fifa-world-cup-prediction-ml | https://github.com/neelabhsinha/fifa-world-cup-prediction-ml | 补充评审 |
| 不可访问 | lblommesteyn/WorldCupPrediction | https://github.com/lblommesteyn/WorldCupPrediction | GitHub API 当前返回 404，不能作为有效证据评价 |

## 2. 我们当前模型的基准状态

本地 `worldcup_predictor` 当前不是一个单一 Notebook，而是一个 CLI + 报告型多 Agent 系统。

当前已具备：

- `DataAgent`：读取 2026 赛程、球队、已完赛比分、队名规范化。
- `StrengthAgent`：Elo、FIFA 排名、近期进失球、世界杯历史强度。
- `LineupAgent`：赛前官方首发、替补、伤停/停赛、预计出场时间、球员评分 fallback。
- `PlayerRatingsAgent`：EA FC 26/FIFA26-style 球员静态评分 fallback。
- `MatchContextAgent`：球员表现样本、天气、旅行疲劳、战术、裁判环境。
- `EventAgent`：黄牌、红牌、角球、任意球、点球的上下半场数量预测。
- `ScorelineAgent`：独立 Poisson 0-0 到 7-7 比分矩阵，汇总胜平负。
- `TournamentAgent`：Monte Carlo 模拟 2026 赛制，支持 48 队、104 场、小组前二、8 个最佳第三名、32 强到决赛。
- `ReportAgent`：中文 Markdown/JSON/CSV 报告。
- `BacktestAgent`：rolling backtest，当前已有 log-loss、Brier、RPS、校准桶。

本地健康检查结果：

- 赛程：104 场，可读。
- 球队：48 队，可读。
- 世界杯历史赛果：1036 行，可读。
- FIFA 排名：211 行，可读。
- 半场事件样本：64 行，可读。
- EA FC 球员评分：18405 行，可读。
- 球员表现样本：433 行，可读。
- 天气：36 行，可读。
- 旅行疲劳：144 行，可读。
- 战术：48 行，可读。
- 裁判 prior：1 行，可读。

当前最重要的事实：

- 我们已经不是“只有 Poisson 胜负预测”的基础模型。
- 我们已经有多源赛前上下文和中文解释。
- 但我们仍然没有 Dixon-Coles 修正、Bayesian 不确定性、完整球员表现商业源、完整伤停源、真实赔率源、指定裁判历史库。

## 3. 横向评分总表

评分范围为 1-5，分数代表对“构建可运行世界杯预测系统”的参考价值，不代表真实预测准确率。

| 项目 | 模型严谨性 | 数据覆盖 | 赛事模拟 | 回测/校准 | 工程化 | 对我们借鉴价值 | 总评 |
|---|---:|---:|---:|---:|---:|---:|---|
| Hicruben | 5 | 3 | 5 | 5 | 4 | 5 | 最值得借鉴的透明统计模型 |
| lbenz730 | 5 | 3 | 5 | 3 | 4 | 5 | 最值得借鉴的不确定性建模 |
| pravindurgani | 4 | 5 | 5 | 5 | 5 | 5 | 最值得借鉴的临场系统 |
| alan-turing-institute | 5 | 3 | 4 | 4 | 4 | 5 | Dixon-Coles 和模拟 CLI 标杆 |
| pameldas | 4 | 3 | 4 | 4 | 3 | 4 | 评估指标和模型权重选择值得学 |
| kamil-kucharski | 3 | 3 | 4 | 2 | 2 | 3 | 简洁 Poisson baseline 值得做 sanity check |
| rivu-intel45 | 3 | 3 | 3 | 2 | 2 | 3 | XGBoost 可做二层校准，不适合替代比分模型 |
| javierruanohdez | 3 | 3 | 4 | 2 | 3 | 3 | 现代展示和 Gradient Boosting 可参考 |
| neelabhsinha | 3 | 3 | 3 | 3 | 2 | 2 | 多算法比较有参考，但年代和赛制不贴近 |
| jieguangzhou | 3 | 3 | 3 | 2 | 4 | 2 | FLAML/下注工作流可借鉴，赛制过时 |
| EhteshamBahoo | 2 | 2 | 2 | 1 | 1 | 2 | 教学型，不适合直接升级我们的系统 |
| ysadre | 2 | 2 | 2 | 1 | 1 | 1 | 2022 分类实验，参考价值有限 |
| neaorin | 2 | 2 | 2 | 1 | 1 | 1 | R 教程型项目，适合教学不适合生产 |

## 4. 逐项目完整评价

### 4.1 Hicruben/world-cup-2026-prediction-model

项目定位：2026 世界杯透明统计预测模型。

公开资料显示，它的核心链路是 Elo ratings -> Dixon-Coles bivariate Poisson -> Monte Carlo simulation。README 明确强调不靠黑盒机器学习，并提供 live predictions、backtest、proper scoring rules。

强项：

- Dixon-Coles bivariate Poisson 比我们的独立 Poisson 更合理，尤其会修正 0-0、1-0、0-1、1-1 这类低比分相关性。
- Monte Carlo 次数提高到 50,000，比我们默认 20,000 更能降低冠军概率尾部噪声。
- 回测指标完整：RPS、log-loss、Brier、reliability curve、ECE。
- 代码结构直接围绕预测任务展开：`elo.mjs`、`predict.mjs`、`backtest.mjs`、`calibrate.mjs`、`track-record.mjs`。

弱项：

- 公开说明的数据上下文主要集中在球队强度和历史结果，没有我们这种阵容、球员评分、天气、旅行、裁判、事件数量的多 Agent 结构。
- 中文解释、数据源契约、赛前数据安全边界不是它的重点。
- 对球员级输入、官方首发、上下半场事件数预测支持弱于我们。

和我们的对比：

- 它的“比分概率核心模型”强于我们。
- 我们的“数据接入广度、中文解释、事件数量、阵容接口”强于它。
- 我们应该优先吸收 Dixon-Coles 和 calibration 体系，而不是照搬它的整个 JS 架构。

可吸收改进：

- 在 `ScorelineAgent` 增加 Dixon-Coles 修正开关。
- 在 `BacktestAgent` 增加 ECE、reliability curve 输出，并把回测结果写入中文报告。
- 将模拟次数配置化，赛事模拟默认保持 20,000，但报告中允许 50,000 高精度模式。

### 4.2 lbenz730/world_cup_2026

项目定位：R + Stan 风格的 2026 世界杯 Bayesian bivariate Poisson 预测。

README 显示它使用 international results since 2016 拟合 Bayesian bivariate Poisson，并通过 `run_sim.R` 做 10,000 次 48 队、12 组、R32 到决赛模拟。

强项：

- Bayesian bivariate Poisson 能输出参数不确定性，比单点 lambda 更符合真实预测场景。
- R/Stan 结构适合严谨统计建模。
- 赛事模拟结构覆盖 2026 新赛制。
- 有 `fit_model.R`、`run_sim.R`、`update_scores.R`、`auto_update.R`，说明 pipeline 不只是 Notebook。

弱项：

- 对赛前官方阵容、球员评分、天气、旅行、裁判、事件数量的公开支持不如我们。
- 对中文解释、模型数据契约、技能化使用不是重点。
- Bayesian 模型的工程复杂度更高，引入后会增加依赖和运行成本。

和我们的对比：

- 它在“不确定性表达”上明显强于我们。
- 我们在“赛前多源上下文 + 可解释报告 + Codex skill 操作”上更贴近用户需求。

可吸收改进：

- 不一定第一阶段上完整 Stan/PyMC；可以先给 lambda 加 bootstrap/历史残差扰动，输出概率区间。
- 第二阶段再考虑 Bayesian bivariate Poisson。
- 报告中增加“胜率区间”和“比分概率区间”，避免单点概率被误解成精确值。

### 4.3 pameldas/FIFA-World-Cup-2026-Prediction-Framework

项目定位：Elo + recent form + Poisson + Random Forest + Monte Carlo 的混合框架。

README 说明其目标是完整 pipeline：数据清洗、特征工程、模型评估、赛事模拟。它测试了 Random Forest 和 Poisson 权重组合，最终权重为 Poisson 100%、Random Forest 0%。

强项：

- 把机器学习分类器和 Poisson 模型做了评估对比，而不是直接相信复杂模型。
- 指标覆盖 accuracy、F1、log loss、goal MAE/RMSE、exact score accuracy。
- 有 `data`、`models`、`reports`、`src` 结构，比纯 Notebook 更规整。

弱项：

- 最终 Random Forest 权重为 0，说明复杂分类器未必真实提升。
- 对赛前阵容、球员、伤停、天气、事件数支持不足。
- 数据源和赛前安全边界不如我们的 catalog 清楚。

和我们的对比：

- 我们已经有 log-loss、Brier、RPS、校准桶，但缺 exact score accuracy 和 goal MAE/RMSE。
- 它提醒我们：新增 ML 特征必须通过回测证明，不应凭直觉开启。

可吸收改进：

- 在 `BacktestAgent` 增加 exact score accuracy、home/away goal MAE、total goals MAE、scoreline top-k hit rate。
- 新增 `ablation` 命令：baseline、+FIFA、+lineup、+context、+events 分层比较。
- 把“是否默认开启某个特征”的标准写进报告：必须改善 log-loss/RPS/Brier 中至少两个，且不显著破坏校准。

### 4.4 rivu-intel45/FIFA-2026-Winner-Prediction

项目定位：XGBoost + Elo + form + H2H 的 2026 胜负预测。

README 显示它使用历史国际比赛、Elo、进失球、近期状态、交手、neutral venue、tournament weighting，训练 XGBoost 分类器并生成 2026 fixtures prediction。

强项：

- XGBoost 能吸收非线性特征，对胜平负分类可能有帮助。
- 特征工程方向清楚：Elo、form、H2H、neutral、tournament weight。
- 对“胜平负分类”来说比简单规则更灵活。

弱项：

- XGBoost 不天然输出完整比分分布，不能自然支持精确比分、总进球、角球/牌数等派生预测。
- 概率校准风险较大，若没有 calibration，输出概率容易过度自信。
- 对赛事完整 bracket、赛前阵容、事件数量、中文解释支持弱于我们。

和我们的对比：

- 它适合做 W/D/L 分类辅助层，不适合替代我们的 Poisson score matrix。
- 我们需要的是“比分分布主模型 + ML 校准层”，而不是黑盒 winner classifier。

可吸收改进：

- 新增可选 `CalibrationAgent`：输入 Poisson 输出、Elo 差、FIFA 差、recent form、lineup/context 特征，用 XGBoost/Logistic 校准 W/D/L。
- 校准层只调整胜平负或 lambda multiplier，不直接替代比分矩阵。
- 必须用 rolling backtest 证明改善后才默认开启。

### 4.5 EhteshamBahoo/Fifa-WorldCup-Data-Analysis-1930-2026

项目定位：Wikipedia 数据抓取 + 清洗 + Random Forest Regressor + 淘汰赛模拟的教学型项目。

强项：

- 从数据抓取到清洗再到预测，流程完整，适合作为入门项目。
- 使用 Wikipedia 历史世界杯数据，容易复现。
- 有 Notebook 和 CSV 输出，对初学者友好。

弱项：

- 模型严谨性较弱，Random Forest Regressor 预测比分并不一定符合足球进球的离散分布特征。
- 对 2026 复杂赛制、最佳第三名、官方阵容、赛前数据安全、回测校准支持有限。
- 工程化程度弱，不适合作为长期可维护预测系统。

和我们的对比：

- 我们已经远超它的工程化和数据契约。
- 它对我们主要价值是提醒：数据清洗和中间 CSV 可视化要足够透明。

可吸收改进：

- 保持我们的输出 CSV/Markdown 简洁可查。
- 不建议吸收其 Random Forest Regressor 作为核心比分模型。

### 4.6 kamil-kucharski/world-cup-2026-prediction

项目定位：FIFA ranking/points + Poisson regression + 1000 次 Monte Carlo 的轻量 Notebook。

README 说明它使用历史国际赛、FIFA ranking data 和 group stage schedule；训练两个 Poisson regression 模型，并用 Poisson 抽样模拟进球。

强项：

- 简洁，容易理解。
- 特征直接：FIFA rank、rank diff、FIFA points、points diff、host、neutral。
- 覆盖 group stage、best third-placed teams、R32 到 final。

弱项：

- Monte Carlo 默认 1000 次，尾部冠军概率噪声会比较大。
- 未使用 Elo、官方阵容、球员表现、天气、裁判、事件数。
- Notebook 形态不如我们的 CLI + skill 适合长期使用。

和我们的对比：

- 我们比它复杂得多，但也更容易因特征过多产生权重不透明。
- 它适合成为我们的最小 baseline，用来检查复杂模型是否真的提升。

可吸收改进：

- 增加 `baseline-poisson-ranking` 回测模式。
- 每次新增复杂特征时，都和这个轻量 baseline 比较。

### 4.7 pravindurgani/wc26-matchday-intelligence

项目定位：最接近生产环境的 2026 matchday intelligence 系统。

README 显示它包含 dashboard、live-updating pipeline、injuries、weather、lineups、match stats、walk-forward backtests、calibration audit、sensitivity analysis、travel fatigue、injury layer、live-mode foundation。根目录包含 `.github`、`dashboard`、`scripts`、`tests`、`RUNBOOK.md`、`DEPLOY.md`。

强项：

- 工程化最强：GitHub Actions、Vercel dashboard、Cloudflare worker、runbook、deploy 文档。
- 数据层最接近临场：API-Football injuries/lineups/events/statistics，OpenWeatherMap weather。
- 有 matchday adjustment caps，例如 injuries/weather/lineups/live stats 都有上限，避免单个数据源把概率推歪。
- 有 walk-forward backtest、ablation、calibration。
- 有 append-only audit log 思路，适合追踪每次预测用了什么数据。

弱项：

- 依赖 API-Football 等外部 API，免费/付费、key、许可、稳定性都需要处理。
- injury 数据如果只有 availability，没有球员价值和严重程度，仍然需要模型解释。
- live stats 对赛前预测不安全，必须区分赛前、赛中、赛后。
- 它的事件预测和中文解释未必像我们现在这样细到上下半场黄牌/角球/任意球/点球。

和我们的对比：

- 它的“临场自动化和 MLOps”明显强于我们。
- 我们的“本地可复现、中文解释、FIFA 官方首发 CSV、事件数量 by half”更贴近当前 Codex skill 定位。

可吸收改进：

- 建 `MatchdayIntelligenceAgent`，把 lineup/injury/weather/travel/referee 都转为有上限的 lambda/Elo 调整。
- 建 `outputs/audit/prediction_runs.jsonl`，每次预测写入数据版本、输入文件、row count、hash、模型版本、输出概率。
- 建赛前 90/60/30 分钟刷新脚本，自动尝试官方首发、天气、伤停、裁判。
- 所有 live/post-match 数据必须打 `pre_match_safe=false`，赛前预测禁止读取。

### 4.8 javierruanohdez/world-cup-2026-prediction

项目定位：Gradient Boosting match model + FIFA ranking/points + Monte Carlo 的 2026 模拟项目。

强项：

- 强调 2026 新赛制随机性，适合做冠军概率可视化。
- Gradient Boosting 比线性模型更能吸收非线性特征。
- 展示和叙事较现代，适合作为报告表达参考。

弱项：

- README 中对 2026 赛制的描述需要谨慎核验，不能直接照搬。
- Gradient Boosting 同样不天然给精确比分分布。
- 对赛前阵容、伤停、球员表现、事件数量支持不足。

和我们的对比：

- 它可以启发我们的可视化和报告表达。
- 不建议用它替代我们的赛事规则实现；我们必须继续以已校验 104 场赛程和 bracket slot 为准。

可吸收改进：

- 把“赛制随机性”和“冠军概率尾部不确定性”写入中文报告。
- 可选加入 Gradient Boosting 作为胜平负校准层。

### 4.9 ysadre/FifaWC_Predictions

项目定位：2022 世界杯分类模型实验。

README 说明其数据来自 Kaggle `International Football Results from 1872 to 2022`，用历史比赛训练分类模型，并预测 2022 世界杯。

强项：

- 使用国际比赛长历史数据，数据源容易获得。
- 适合作为 2022 赛前预测实验样例。

弱项：

- 没有 2026 赛制。
- 没有完整比分矩阵。
- 没有回测/校准体系。
- 没有官方阵容、球员表现、天气、伤停、事件数。

和我们的对比：

- 我们的系统化程度明显更高。
- 该项目对当前改进参考价值很低。

可吸收改进：

- 无核心吸收项。
- 只可作为 Kaggle 数据源说明参考。

### 4.10 jieguangzhou/FIFA-World-Cup-2022

项目定位：2022 世界杯 FLAML 训练、预测和下注工作流。

README 显示它包含 `training.py`、`predict_match.py`、`predict_today_match.py`、`get_odds.py`、`betting_strategy.py`、Dockerfile 和 config。它更像一个自动训练/预测工作流，而不是单一模型论文。

强项：

- 工程工作流较完整：训练、预测、今日比赛、赔率、下注策略。
- 使用 FLAML 自动建模，可快速比较多模型。
- Dockerfile 和命令化脚本对复现有帮助。

弱项：

- 2022 项目，赛制和数据结构不适配 2026。
- 涉及 betting workflow，不符合我们当前“不使用真实赔率”的范围。
- 不强调精确比分分布、事件数量、赛前安全数据边界。

和我们的对比：

- 它在“自动训练工作流”上有参考价值。
- 我们在“赛前数据契约、中文解释、多 Agent、2026 赛制”上更强。

可吸收改进：

- 借鉴 CLI workflow 和 Docker/配置化思路。
- 不接入 betting strategy，除非用户明确改变范围并提供合法赔率源。

### 4.11 alan-turing-institute/WorldCupPrediction

项目定位：Dixon-Coles 类模型和足球赛事模拟的高质量标杆。

README 说明其原始模型是 Dixon and Coles 的一个版本，并提供 `ftpred_run_simulations` / `wcpred_run_simulations` 这类模拟 CLI。该项目还提到其 AIrgentina 模型在 2022 World Cup Sophisticated Prediction Contest 中表现强。

强项：

- 统计建模路线成熟，Dixon-Coles 是足球比分建模经典方法。
- 有可运行 CLI，不只是 Notebook。
- 对模拟内存、线程、批次等工程细节有提醒。
- 同时支持男子/女子赛事，说明抽象程度较好。

弱项：

- 不是专门为我们当前中文 Codex skill 和多源赛前上下文设计。
- 官方阵容、伤停、天气、事件数量不是其核心。
- 模型复杂度比我们现在的独立 Poisson 高，接入需要谨慎测试。

和我们的对比：

- 它是我们升级比分模型时最应该参考的统计标杆之一。
- 我们可以先实现轻量 Dixon-Coles，而不是引入它全部包结构。

可吸收改进：

- 设计 `ScorelineAgent(score_model="independent_poisson|dixon_coles")`。
- 在 backtest 中比较 independent Poisson vs Dixon-Coles。
- 把内存和模拟次数参数暴露到 CLI，避免大规模模拟时卡死。

### 4.12 neaorin/PredictTheWorldCup

项目定位：R 语言机器学习教学教程。

README 说明它面向机器学习初学者，使用模型运行多次世界杯赛事模拟，生成各队夺冠概率。

强项：

- 教学性强，适合理解完整数据科学流程。
- R 语言用户友好。

弱项：

- 年代较早，缺少 2026 赛制。
- 模型和工程化都不适合直接迁移到我们系统。
- 无赛前数据安全、官方阵容、事件预测、回测校准等现代要求。

和我们的对比：

- 我们已经不需要从它学习核心模型。
- 它对 README 教学风格有轻微参考价值。

可吸收改进：

- 可以在中文 README 加一个“从输入到预测结果”的教学流程图。

### 4.13 neelabhsinha/fifa-world-cup-prediction-ml

项目定位：多算法分类、分组和完整赛事预测项目。

README 说明它使用 Kaggle 世界杯数据、国际比赛数据和 FIFA rankings，比较多个监督学习算法，并探索用聚类做分组。

强项：

- 多算法比较，比单模型更有实验意识。
- 公开指标包括 accuracy、precision、recall、F1、ROC-AUC。
- 除比赛预测外，还探索分组平衡，是一个更宽泛的赛事工具。

弱项：

- 以胜负分类为主，不适合精确比分和进球分布。
- 数据和赛制偏旧。
- 聚类分组与我们当前预测任务关系不大。

和我们的对比：

- 它的算法比较意识值得保留，但具体算法和分组功能不属于我们近期目标。

可吸收改进：

- 如果未来要增加 ML 校准层，可以复用“多算法比较”的实验框架思想。
- 不建议做分组优化，这会偏离预测系统目标。

### 4.14 lblommesteyn/WorldCupPrediction

当前状态：此前列表中出现过该链接，但本轮 GitHub API 返回 404。

处理方式：

- 不把它作为有效证据来源。
- 不基于不可访问 README 做技术判断。
- 如果后续用户提供正确仓库 URL，再单独补评。

## 5. 我们相对 GitHub 项目的优势

### 5.1 更适合做 Codex skill

多数 GitHub 项目是 Notebook、脚本或 dashboard。我们的系统已经有稳定 CLI：

- `predict-match`
- `simulate-tournament`
- `report`
- `refresh-data`
- `build-context-data`
- `backtest`

这比 Notebook 更适合被 Codex skill 调用。

### 5.2 中文解释更完整

我们的 `explanation` 明确覆盖：

- 胜平负概率。
- Top 比分。
- 预期进球。
- Elo/FIFA/近期状态/世界杯历史。
- lambda 从基础值到最终值的变化路径。
- 阵容、伤停、替补、球员评分是否进入。
- 球员表现、天气、旅行、战术、裁判。
- 黄牌、红牌、角球、任意球、点球上下半场预测。
- 数据缺口和 fallback。

大多数 GitHub 项目只输出英文表格或 Notebook 图，不适合直接给中文用户解释。

### 5.3 数据源契约更清楚

我们的 `worldcup_data_source_catalog.md` 明确区分：

- 已获得。
- 已进入模型。
- 是否赛前安全。
- 本地文件。
- 进入哪个 Agent。
- 主要缺口。

很多项目只写“使用 Kaggle/FIFA ranking/API”，没有把赛前安全和数据泄漏边界写清楚。

### 5.4 事件数量预测更广

多数项目只预测：

- 胜平负。
- 精确比分。
- 小组排名。
- 冠军概率。

我们的 `EventAgent` 已经能预测：

- 黄牌。
- 红牌。
- 角球。
- 任意球。
- 点球。
- 并区分上半场和下半场。

虽然样本仍小，但输出范围更贴近用户最初要求。

### 5.5 2026 赛制实现更贴近需求

我们已经按 104 场、48 队、12 组、最佳第三名、32 强 bracket 来做模拟，并且要求第三名 slot 按允许组回溯分配，避免随机乱配。

## 6. 我们相对 GitHub 项目的短板

### 6.1 比分模型还不够专业

当前 `ScorelineAgent` 是独立 Poisson：

```text
P(home goals = h, away goals = a) = Pois(h; lambda_home) * Pois(a; lambda_away)
```

问题是足球比分并不完全独立，低比分之间存在相关性。Hicruben 和 Alan Turing Institute 都使用 Dixon-Coles 类方法，这是我们最应该补的核心短板。

### 6.2 不确定性表达不足

我们现在输出的是单点概率。lbenz 的 Bayesian bivariate Poisson 更能表达：

- 参数不确定。
- 小样本球队不确定。
- 晋级/冠军概率区间。
- 最可能比分的不稳定性。

### 6.3 回测还没有覆盖所有新增特征

我们已有 log-loss、Brier、RPS、校准桶，但当前回测主要验证基础球队强度模型，不充分验证：

- lineup multiplier。
- player rating fallback。
- player performance context。
- weather/travel/tactics/referee context。
- event-count predictor。
- scoreline exact accuracy。

### 6.4 临场自动化不足

pravindurgani 的 matchday intelligence 在自动化方面更强：

- GitHub Actions 定时刷新。
- live data pipeline。
- dashboard。
- audit logs。
- injuries/lineups/weather/stats layers。

我们目前是本地 CLI 驱动，缺少自动刷新、审计日志和 dashboard。

### 6.5 球员表现和伤停数据仍不完整

我们已经接入：

- FIFA 官方比赛名单示例。
- FIFA 球员 profile。
- EA FC 评分 fallback。
- StatsBomb open sample。

但还没有完整覆盖：

- 俱乐部 + 国家队逐场表现。
- 伤停严重程度。
- 停赛。
- 预计首发可信来源。
- 指定裁判历史判罚。

### 6.6 新增上下文对胜率影响小，需要建立权重验证机制

之前接入阵容/天气/旅行/战术/裁判后胜率变化不大，原因是：

- 很多新数据缺失后回退中性值。
- 当前上下文乘数有意很保守，避免未经回测就大幅改变概率。
- 球队级 Elo/FIFA/近期状态已经解释了大量强弱差，新增特征只做边际修正。
- 部分数据不是完整真实源，例如 EA FC 静态评分和 StatsBomb open sample。

这不是坏事，但说明下一步不能继续盲目加数据，而要用回测决定权重。

## 7. 改进总路线

总体原则：

1. 不用黑盒模型替代可解释比分矩阵。
2. 每个新增特征必须有数据契约、赛前安全标记和回测证据。
3. 先提升比分分布，再扩展临场自动化。
4. 真实赔率默认不接入，除非用户明确改变范围并提供合法来源。
5. 所有赛中/赛后数据必须隔离，赛前预测禁止读取。

### Phase 1：比分模型升级到 Dixon-Coles

目标：解决独立 Poisson 对低比分平局和双方进球相关性的建模缺陷。

改动范围：

- 新增 `worldcup_predictor/score_models.py`。
- 把当前 Poisson 矩阵逻辑从 `ScorelineAgent` 拆出来。
- 支持两个模型：
  - `independent_poisson`
  - `dixon_coles`
- CLI 增加：
  - `--score-model independent_poisson|dixon_coles`
  - 默认先保持 `independent_poisson`，回测通过后再切换默认。

实现要点：

- Dixon-Coles 只修正 0-0、0-1、1-0、1-1 四类低比分。
- 参数 `rho` 先通过历史 rolling backtest 网格搜索。
- 矩阵仍截断 0-0 到 7-7 后归一化。

验收标准：

- 胜平负概率和为 `1.0 ± 0.001`。
- scoreline 概率和为 `1.0 ± 0.001`。
- top scorelines 降序稳定。
- `python -m unittest discover -s tests -v` 通过。
- backtest 中 Dixon-Coles 至少不恶化 log-loss/RPS/Brier。

### Phase 2：回测和校准扩展

目标：让“是否提高预测胜率”有硬指标，而不是主观判断。

改动范围：

- 扩展 `BacktestAgent`。
- 新增 `worldcup_predictor/ablation.py`。
- CLI 新增：
  - `python -m worldcup_predictor backtest --score-model dixon_coles`
  - `python -m worldcup_predictor ablation`

新增指标：

- exact score accuracy。
- top-3 scoreline hit rate。
- home goals MAE/RMSE。
- away goals MAE/RMSE。
- total goals MAE/RMSE。
- draw calibration。
- favorite calibration。
- ECE。
- reliability table。

Ablation 分层：

- baseline：Elo + 世界杯历史 + 近期状态。
- +FIFA ranking。
- +lineup。
- +player ratings。
- +player performance。
- +weather/travel/tactics/referee。
- +Dixon-Coles。
- +ML calibration。

默认开启规则：

- 新特征只有在 rolling backtest 中改善至少两个核心指标，且不显著破坏校准，才允许默认开启。
- 若只改善某些小样本比赛，报告中只能标记为 experimental。

验收标准：

- `outputs/reports/backtest_metrics.json` 增加新指标。
- `outputs/reports/ablation_report.md` 生成中文报告。
- 每个新增特征都有“开启/关闭”对比。

### Phase 3：Matchday Intelligence 和审计日志

目标：吸收 pravindurgani 的生产化优点，让赛前数据刷新和预测有记录可追溯。

改动范围：

- 新增 `worldcup_predictor/matchday.py`。
- 新增 `worldcup_predictor/audit.py`。
- 新增 `outputs/audit/prediction_runs.jsonl`。
- 新增 `outputs/audit/data_refresh_runs.jsonl`。

每次预测记录：

- timestamp。
- command。
- match_id。
- home/away。
- model version。
- score model。
- data files。
- row counts。
- file hashes。
- pre_match_safe flags。
- warnings。
- p_home/p_draw/p_away。
- top scorelines。
- lambda path。

赛前刷新节奏：

- T-90 分钟：拉官方阵容、比赛名单、裁判、天气。
- T-60 分钟：重复拉官方阵容和天气。
- T-30 分钟：最后确认首发、替补、伤停标记。

验收标准：

- 任意一次 `predict-match` 都能追溯到输入文件和版本。
- 赛后/live 数据不能出现在 pre-match safe 预测中。
- 报告能显示“本次预测使用的数据快照”。

### Phase 4：球员和阵容数据补齐

目标：把用户关心的官方首发、伤停、球员能力、替补策略真正变成稳定输入。

改动范围：

- 扩展 `worldcup_data_audit/scripts/build_match20_gap_inputs.py` 为通用脚本。
- 新增：
  - `worldcup_data_audit/scripts/build_match_lineup_inputs.py`
  - `worldcup_data_audit/scripts/build_squad_inputs.py`
  - `worldcup_data_audit/scripts/build_injury_inputs.py`

数据层：

- FIFA official match centre：官方首发/替补。
- FIFA season squads：国家队赛事名单。
- FIFA player profile：身份、身高、生日、国家队出场/进球。
- 可选商业源/API-Football：伤停、停赛、预计首发、球员表现。
- EA FC ratings：仅作为静态能力 fallback，不能叫官方 FIFA 评分。

模型层：

- `LineupAgent` 继续负责首发质量、伤停损失、替补 expected minutes。
- 增加球员位置权重：GK/CB/DM/AM/ST 的缺阵影响不同。
- 替补策略不做“猜真实计划”，只做 bench depth 和 expected minutes prior。

验收标准：

- 任意 match_id 都能尝试生成 lineup CSV。
- 官方首发必须校验每队 11 人。
- 替补人数异常、球队名不匹配、球员评分匹配失败都要 warning。
- 伤停只有可信来源时才写 `role=unavailable`。

### Phase 5：上下文特征重新加权

目标：解决“接入数据后胜率影响不明显”的问题，但不能靠随意加大权重。

改动范围：

- 扩展 `MatchContextAgent`。
- 新增 `context_weight_config.yaml`。
- 新增 `context_weight_search` 回测脚本。

策略：

- 每个上下文特征都设最大影响上限。
- 天气主要影响总进球和定位球，不直接大幅改变胜负。
- 旅行疲劳主要影响后半场进球和防守稳定性。
- 裁判主要影响牌、任意球、点球和比赛碎片化。
- 球员表现只有覆盖率足够时才影响 lambda。

验收标准：

- 权重变化必须有回测报告。
- 对缺数据球队自动回退中性，不惩罚小数据国家。
- 报告中解释“为什么这个因素影响小/大”。

### Phase 6：ML 校准层，而不是黑盒替代

目标：吸收 XGBoost/Random Forest/FLAML 项目的优点，同时保留比分分布。

改动范围：

- 新增 `worldcup_predictor/calibration.py`。
- 支持：
  - logistic calibration。
  - isotonic calibration。
  - optional XGBoost/LightGBM calibration if dependency available。

输入：

- Poisson/Dixon-Coles 原始 W/D/L。
- Elo diff。
- FIFA rank diff。
- recent form diff。
- lineup multiplier。
- context multipliers。
- home/neutral/host。

输出：

- 校准后的 W/D/L。
- 可选反推 lambda adjustment，但必须保持 scoreline matrix 一致。

验收标准：

- 校准后 log-loss 和 ECE 改善。
- 不允许只提高 accuracy 但概率校准变差。
- 默认关闭，直到回测证明稳定。

### Phase 7：Bayesian/不确定性输出

目标：吸收 lbenz 的不确定性表达，让报告更诚实。

第一版轻量做法：

- 用 bootstrap 或 rolling residual 扰动生成 lambda 区间。
- tournament simulation 输出 p05/p50/p95。
- 单场输出 win/draw/loss 区间。

第二版严谨做法：

- Bayesian bivariate Poisson。
- team attack/defense posterior。
- home/neutral/host effect posterior。

验收标准：

- 报告中显示“点估计 + 区间”。
- 不确定性随着样本少、阵容缺失、数据 fallback 自动变大。

### Phase 8：报告和 skill 产品化

目标：把改进后的模型继续封装成 `worldcup-predict` skill 的可靠工作流。

改动范围：

- 更新 skill `SKILL.md`。
- 更新 `references/model-overview.md`。
- 更新 `references/data-contracts.md`。
- 更新 `references/commands-and-validation.md`。
- 更新项目 README。

报告新增内容：

- 本次 score model。
- 是否使用 Dixon-Coles。
- 是否使用 calibration layer。
- 数据快照和 audit id。
- 回测摘要。
- 特征消融结果。
- 概率区间。
- 主要影响因素排行。

验收标准：

- 用户问“为什么胜率变化不大”时，skill 能解释：
  - 该因素是否进入模型。
  - 覆盖率如何。
  - 权重上限是多少。
  - 回测是否支持默认开启。
- 用户问“能不能预测比分/冠军/事件数”时，skill 能引用当前模型输出，而不是凭聊天猜。

## 8. 推荐执行顺序

最值得先做的不是继续接更多数据，而是让模型有更强验证能力。

推荐顺序：

1. Phase 2：扩展回测和消融。
2. Phase 1：增加 Dixon-Coles，并用扩展回测验证。
3. Phase 3：增加 audit log，保证每次预测可追溯。
4. Phase 4：把 match20 官方阵容补齐脚本泛化到所有比赛。
5. Phase 5：上下文权重搜索，避免手动拍权重。
6. Phase 6：增加 ML 校准层。
7. Phase 7：增加不确定性区间。
8. Phase 8：更新 skill 和 README。

为什么把 Phase 2 放在 Phase 1 前面：

- 如果先改模型但没有足够指标，很难判断是否真提升。
- Hicruben、pameldas、pravindurgani 的共同启发是：模型改进必须由回测和校准证明。

## 9. 不建议做的事

### 9.1 不建议直接把 XGBoost/Random Forest 变成主模型

原因：

- 它们不天然输出完整比分分布。
- 精确比分、总进球、上下半场事件数会变得不连贯。
- 概率校准风险高。

正确方式：

- 用它们做校准层或 ablation 对照。

### 9.2 不建议把 EA FC 评分说成 FIFA 官方球员评分

原因：

- 这是游戏评分或镜像数据，不是 FIFA 官方能力评价。
- 可以作为静态能力 fallback，但必须在报告中说明来源边界。

### 9.3 不建议接入赛中数据做赛前预测

原因：

- FIFA timeline、playerstatistics、live stats 在赛前可能为空，赛后会产生数据泄漏。
- 赛前预测只能使用开球前可获得快照。

### 9.4 不建议使用真实赔率，除非用户改变范围

原因：

- 当前模型定位是免费源优先、不依赖付费 API。
- 赔率涉及合法来源、key、许可和解释边界。
- 一旦接入赔率，模型很可能变成“市场概率校准器”，定位会变化。

## 10. 最终判断

如果只看数学比分模型，Hicruben 和 Alan Turing Institute 当前比我们强，因为它们使用 Dixon-Coles 类方法。

如果看不确定性表达，lbenz730 比我们强，因为 Bayesian bivariate Poisson 更能表达概率区间。

如果看临场自动化，pravindurgani 比我们强，因为它有 live data、injury layer、dashboard、actions、audit/runbook。

如果看 Codex skill 化、本地 CLI、中文解释、多 Agent 数据契约、官方阵容接入、事件数量 by half，我们的 `worldcup_predictor` 更贴近用户当前目标。

因此下一步最正确的方向不是推翻现有模型，而是：

1. 保留我们的多 Agent 架构。
2. 用 Dixon-Coles 升级比分矩阵。
3. 用扩展回测和消融决定特征权重。
4. 用 matchday intelligence 和 audit log 提升临场可靠性。
5. 用球员/阵容/伤停数据补齐提高赛前敏感度。
6. 最后再考虑 ML 校准层和 Bayesian 区间。

## 11. 交付清单

本报告完成后，建议后续实现时按以下文件落地：

| 目标 | 建议文件 |
|---|---|
| Dixon-Coles 模型 | `worldcup_predictor/score_models.py`、`worldcup_predictor/scoreline.py` |
| 回测扩展 | `worldcup_predictor/backtest.py`、`worldcup_predictor/ablation.py` |
| 审计日志 | `worldcup_predictor/audit.py`、`outputs/audit/*.jsonl` |
| 临场刷新 | `worldcup_predictor/matchday.py`、`worldcup_data_audit/scripts/build_match_lineup_inputs.py` |
| 阵容泛化 | `worldcup_data_audit/scripts/build_squad_inputs.py`、`worldcup_data_audit/scripts/build_injury_inputs.py` |
| 上下文权重 | `inputs/config/context_weight_config.yaml`、`worldcup_predictor/context.py` |
| ML 校准 | `worldcup_predictor/calibration.py` |
| 不确定性 | `worldcup_predictor/uncertainty.py` |
| 中文报告 | `worldcup_predictor/report.py` |
| skill 更新 | `C:\Users\81901\.codex\skills\worldcup-predict\SKILL.md` 和 `references/*.md` |

## 12. 来源链接

- https://github.com/Hicruben/world-cup-2026-prediction-model
- https://github.com/lbenz730/world_cup_2026
- https://github.com/pameldas/FIFA-World-Cup-2026-Prediction-Framework
- https://github.com/rivu-intel45/FIFA-2026-Winner-Prediction
- https://github.com/EhteshamBahoo/Fifa-WorldCup-Data-Analysis-1930-2026
- https://github.com/kamil-kucharski/world-cup-2026-prediction
- https://github.com/pravindurgani/wc26-matchday-intelligence
- https://github.com/javierruanohdez/world-cup-2026-prediction
- https://github.com/ysadre/FifaWC_Predictions
- https://github.com/jieguangzhou/FIFA-World-Cup-2022
- https://github.com/alan-turing-institute/WorldCupPrediction
- https://github.com/neaorin/PredictTheWorldCup
- https://github.com/neelabhsinha/fifa-world-cup-prediction-ml
