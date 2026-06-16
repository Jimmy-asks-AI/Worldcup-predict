# 数据契约和当前可用状态

## 自动进入基础模型的数据

| 数据 | 文件 | 当前基准 | 是否自动使用 | 用途 | Caveat |
|---|---|---:|---|---|---|
| 2026 赛程 | `worldcup_data_audit/data/processed/fixtures_2026.csv` | 104 行 | 是 | 赛程、分组、淘汰赛占位 | 需要刷新确认赛程变更 |
| 2026 球队 | `worldcup_data_audit/data/processed/teams_2026.csv` | 48 行 | 是 | 球队列表、FIFA code | 队名别名需规范化 |
| 当前比赛状态 | `worldcup_data_audit/data/processed/worldcup26_games.csv` | 104 行预期 | 是 | 锁定已完赛真实比分 | 未完赛 0-0 不能当真实比分 |
| 世界杯历史赛果 | `worldcup_data_audit/data/processed/international_results_worldcup_only.csv` | 1036 行 | 是 | 基础进球率、世界杯历史强度、回测 | 只覆盖世界杯，不是全部国家队比赛 |
| Elo 快照 | `worldcup_data_audit/data/processed/derived_elo_snapshot.csv` | 336 行左右 | 是 | 强弱差、点球倾斜 | 缺失球队 fallback 1500 并输出 warning |
| 近期状态 | `worldcup_data_audit/data/processed/derived_recent_form.csv` | 336 行左右 | 是 | 近期进球、失球、积分 | 来自可用历史比赛 |
| FIFA 男足排名 | `worldcup_data_audit/data/processed/fifa_ranking_snapshot.csv` | 211 行 | 是 | 小幅修正进球 lambda | 与 Elo 信息重叠，权重有意很小 |
| 半场事件样本 | `worldcup_data_audit/data/processed/statsbomb_event_half_team_summary.csv` | 32 行 | 是 | 黄牌、红牌、角球、任意球、点球分半场预测 | 样本很小，应替换为更大事件源 |

## 通过 `--use-generated-context` 或显式参数进入模型的数据

| 数据 | 文件 | 当前基准 | 开关 | 用途 | Caveat |
|---|---|---:|---|---|---|
| 球员表现 | `inputs/player_performance/player_match_performance.csv` | 248 行 | `--use-generated-context` 或 `--player-performance-file` | 球员进攻/防守表现转成球队攻防乘数 | 当前是 StatsBomb 样本，不是完整俱乐部+国家队覆盖 |
| 天气 | `inputs/match_context/weather_forecast.csv` | 35 行 | `--use-generated-context` 或 `--weather-file` | 温度、湿度、雨、风影响总进球和定位球 | 多为球场样本，不一定是精确 kickoff forecast |
| 旅行疲劳 | `inputs/match_context/team_travel_fatigue.csv` | 144 行 | `--use-generated-context` 或 `--travel-file` | 距离、休息天、时区、训练干扰影响疲劳 | 小组赛可生成，淘汰赛路径需模拟后才知道 |
| 战术 | `inputs/match_context/tactics.csv` | 48 行 | `--use-generated-context` 或 `--tactics-file` | 阵型、压迫、宽度、定位球、反击等先验 | 是启发式先验，不是官方战术计划 |
| 裁判 | `inputs/match_context/referees.csv` | 1 行 | `--use-generated-context` 或 `--referee-file` | 纪律、犯规、点球和总进球环境 | 当前是全局 prior，不是指定裁判历史 |

## 可选阵容和球员评分数据

| 数据 | 文件 | 当前基准 | 开关 | 用途 | Caveat |
|---|---|---:|---|---|---|
| 官方首发/伤停/替补策略 | `inputs/lineups/*.csv` | 模板和示例 | `--lineup-file` | 首发质量、伤停损失、替补分钟影响进球 lambda | 必须提供赛前可信来源；默认首发需要 `official=true` |
| EA FC 26 球员评分 | `inputs/player_ratings/eafc26_player_ratings.csv` | 18405 行 | `--player-ratings-file` 且传入 lineup | lineup 缺 rating 时按姓名、国籍、俱乐部匹配 fallback | 不是 FIFA 官方评分；许可来源需谨慎 |

## 明确未使用

- 真实博彩赔率：当前模型明确排除，不进入任何 lambda 或赛事概率计算。
- 赛后评分、实时赛中数据、已知终场比分：赛前预测时禁止使用。

## 数据刷新入口

- `python -m worldcup_predictor refresh-data`：调用 `worldcup_data_audit/scripts/pull_and_audit_worldcup_data.py`。
- `python -m worldcup_predictor build-context-data`：调用 `worldcup_data_audit/scripts/build_non_odds_context_inputs.py`。
- 刷新后先运行 `python scripts/health_check.py --root <repo>` 和 `python -m unittest discover -s tests -v`。
