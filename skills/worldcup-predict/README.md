# worldcup-predict

这是一个基于 Codex 的世界杯预测模型 skill，用来操作当前本地的 `worldcup_predictor` 多 Agent 系统。

## 这个 skill 做什么

- 运行单场比赛预测：胜平负概率、最可能比分、预期进球。
- 运行整届世界杯模拟：小组排名、晋级概率、淘汰赛路径、冠军概率。
- 生成中文报告：`outputs/reports/worldcup_prediction_report.md`。
- 检查数据是否齐全：赛程、球队、世界杯历史赛果、Elo、FIFA 排名、球员评分、阵容接口、天气、旅行疲劳、战术、裁判和事件样本。
- 输出全面中文解释：球队强度、lambda 变化、阵容/伤停/替补、球员表现、天气、旅行疲劳、战术、裁判、事件数量和数据缺口。

## 主要文件

- `SKILL.md`：Codex 调用这个 skill 时优先读取的执行规则。
- `references/model-overview.md`：多 Agent 架构和预测方法。
- `references/data-contracts.md`：数据来源、文件路径、当前可用状态和 caveat。
- `references/commands-and-validation.md`：常用命令、输出文件和验证流程。
- `scripts/health_check.py`：快速检查本地预测模型是否具备运行条件。

## 解释输出要求

`predict-match` 的 JSON 会包含 `explanation` 字段。使用这个 skill 时，应优先读取该字段，并在中文回答中覆盖：

- 胜平负、比分、预期进球。
- Elo、FIFA 排名、近期状态、世界杯历史。
- 基础进球期望到最终进球期望的变化。
- 官方阵容、伤停、替补策略和球员评分是否进入计算。
- 球员表现、天气、旅行疲劳、战术和裁判上下文。
- 黄牌、红牌、角球、任意球、点球的上下半场预测。
- 缺失数据和 fallback。

## 推荐用法

在包含 `worldcup_predictor/` 的项目根目录运行：

```powershell
python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root .
python -m worldcup_predictor predict-match --home France --away Senegal --match-id 97 --use-generated-context
python -m worldcup_predictor report --runs 20000 --use-generated-context
```

如果要让阵容、伤停和替补策略进入模型，需要提供赛前可信的 lineup CSV：

```powershell
python -m worldcup_predictor predict-match --home Spain --away "Cape Verde" --match-id 1 `
  --lineup-file inputs\lineups\template.csv `
  --lineup-allowed-source manual-template `
  --player-ratings-file inputs\player_ratings\eafc26_player_ratings.csv `
  --use-generated-context
```

## 当前边界

- 真实赔率没有进入模型。
- EA FC 球员评分可以作为阵容评分 fallback，但不是 FIFA 官方球员评分。
- 官方首发、伤停和替补策略已经有接口，但必须由赛前可信数据填入。
- 天气、裁判、球员表现和事件样本目前有可运行的本地数据，但覆盖度仍需在正式预测前复核。
