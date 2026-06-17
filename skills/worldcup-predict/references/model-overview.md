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
- `ScorelineAgent`：把球队强度、阵容和上下文调整转换成两队进球期望；用 0-0 到 7-7 的 Poisson 比分矩阵计算比分概率和胜平负概率；同时输出 `explanation` 结构化中文解释。
- `TournamentAgent`：用单场模型跑 Monte Carlo。锁定已完赛真实结果，模拟小组积分、最佳第三名、32 强到决赛；淘汰赛平局用 Elo 倾斜点球概率决胜。
- `ReportAgent`：写 JSON/CSV/Markdown 输出，并把 `explanation` 写入 Markdown 的“单场解释”部分。
- `BacktestAgent`：用历史世界杯赛果做 rolling backtest，输出 log loss、Brier score、RPS 和校准桶。

## 单场预测方法

1. 从世界杯历史赛果得到基础进球率。
2. 用近期状态、世界杯历史表现、Elo 差和 FIFA 排名得到两队基础进球期望 `lambda_home` / `lambda_away`。
3. 如果传入 lineup，把首发质量、伤停损失、替补预计分钟和球员评分变成攻防乘数。
4. 如果传入 context，把球员表现、天气、旅行疲劳、战术和裁判变成攻防/总进球/定位球/纪律乘数。
5. 用独立 Poisson 计算 0-0 到 7-7 的比分概率，并归一化。
6. 把比分矩阵按主胜、平、客胜汇总成胜平负概率。
7. 用事件样本和上下文指数输出卡牌、角球、任意球、点球数量预测。
8. 生成 `explanation` 字段，统一解释结论、方法、球队强度、lambda 路径、阵容、上下文、事件数量和数据缺口。

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
- `factors.data_quality`：缺失数据、fallback 和本场可信度边界。
- `warnings` / `caveats`：必须向用户解释，不要隐藏。

## 整届赛事模拟方法

1. 每次 Monte Carlo 按赛程模拟所有小组赛。
2. 已完赛比赛使用真实比分，不重新模拟。
3. 小组积分规则：胜 3 分、平 1 分、负 0 分；排名按积分、净胜球、进球数，再用固定随机种子处理完全并列。
4. 每组前二加 8 个最佳第三名晋级 32 强。
5. 最佳第三名分配按赛程 slot 的允许小组回溯分配，不随机乱配。
6. 淘汰赛继续用单场比分模型；打平则用 Elo 倾斜的点球概率决胜。
7. 汇总所有模拟次数得到晋级概率、进决赛概率、冠军概率、预期积分和预期净胜球。

## 解释口径

对用户解释时，用“这个模型认为”“概率上更可能”这类表达。不要说“必胜”“确定比分”。最可能比分通常单个概率不高，应同时给胜平负和 Top scorelines。解释必须覆盖主要影响因素；如果某个因素没有进入计算，要明确说“接口支持，但本次没有可信输入，所以保持中性”。
