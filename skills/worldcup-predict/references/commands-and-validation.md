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

## 单场预测

基础预测：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal
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

读取输出 JSON 时重点看：

- `lambda_home` / `lambda_away`
- `p_home_win` / `p_draw` / `p_away_win`
- `top_scorelines`
- `lineup_adjustment`
- `context_adjustment`
- `event_prediction`
- `warnings`

## 整届赛事模拟

```powershell
python -m worldcup_predictor simulate-tournament --runs 20000 --use-generated-context
```

输出：

- `outputs/predictions/tournament_odds.csv`
- `outputs/predictions/group_rankings.csv`

注意：这里的 `tournament_odds.csv` 是模拟概率，不是博彩赔率。

## 中文报告

```powershell
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --sample-match-id 97 --use-generated-context
```

输出：

- `outputs/predictions/match_predictions.json`
- `outputs/predictions/group_rankings.csv`
- `outputs/predictions/tournament_odds.csv`
- `outputs/reports/worldcup_prediction_report.md`

## 回测

```powershell
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1
```

重点指标：

- `log_loss`
- `brier_score`
- `ranked_probability_score`
- `calibration`

如果新增数据特征，只有在 time-safe 回测或前向验证改善这些指标时，才应默认开启。

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
- 小组前二加 8 个最佳第三名共 32 队晋级。
- 每次赛事模拟必须唯一冠军。

## 常见排错

- `FileNotFoundError`：先运行 `refresh-data` 或 `build-context-data`，再做健康检查。
- 阵容文件报错：检查 `source`、`rating_basis`、`official=true` 和 `--lineup-allowed-source`。
- 预测结果看起来太确定：检查是否误用了赛后数据或实际比分。
- 事件数量 warnings 很多：说明该队没有事件样本，模型退回全局半场 rates。
- 天气 warning：说明没有匹配到本场精确 kickoff 天气，应在赛前刷新或显式提供天气文件。
