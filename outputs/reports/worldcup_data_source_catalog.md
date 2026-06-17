# 世界杯预测模型数据源目录

Generated: 2026-06-17

这份目录记录 `worldcup_predictor` 当前使用和已验证可接入的数据来源。重点区分三件事：

- `已获得`：本地已有可读取文件或已验证可匿名/API 获取。
- `已进入模型`：当前 CLI 预测实际会读取并影响概率。
- `赛前安全`：在开球前可以使用，不依赖赛后结果、赛中统计或已知终场比分。

## 数据源总表

| 数据域 | 数据类型 | 上游来源 | 本地文件 | 进入 Agent | 已获得 | 已进入模型 | 赛前安全 | 当前用途 | 主要缺口 |
|---|---|---|---|---|---|---|---|---|---|
| 2026 赛程 | 赛程、组别、阶段、开球时间、球场 | TheStatsAPI fixtures JSON；worldcup26.ir games/groups | `worldcup_data_audit/data/processed/fixtures_2026.csv`、`worldcup26_games.csv` | `DataAgent` | 是，104 场 | 是 | 是 | 单场 match_id、小组赛、淘汰赛 bracket | 需要赛程变更时刷新 |
| 2026 球队 | 48 队、FIFA code、分组 | worldcup26.ir teams/groups | `teams_2026.csv`、`worldcup26_group_table.csv` | `DataAgent` | 是，48 队 | 是 | 是 | 队名规范化、分组模拟 | 队名别名仍需人工维护 |
| 球场 | 球场、城市、经纬度、容量 | worldcup26.ir stadiums；本地经纬度 fallback | `stadiums_2026.csv` | `DataAgent`、`MatchContextAgent` | 是 | 间接使用 | 是 | 天气、旅行距离、时区估计 | 部分球场坐标靠本地 fallback |
| 世界杯历史赛果 | 世界杯历史比分、胜平负、进球 | martj42 international_results | `international_results_worldcup_only.csv` | `StrengthAgent`、`ScorelineAgent`、`Backtest` | 是，1036 行 | 是 | 是 | 基础进球率、世界杯历史强度、回测 | 新军或少参赛球队会回退全局均值 |
| 国际比赛近期状态 | 近期进球、失球、积分 | martj42 international_results 派生 | `derived_recent_form.csv` | `StrengthAgent` | 是 | 是 | 是 | 近期攻防状态 | 覆盖取决于公开国际赛记录 |
| Elo | 国家队 Elo 快照 | 本地从国际赛结果派生 | `derived_elo_snapshot.csv` | `StrengthAgent`、`TournamentAgent` | 是 | 是 | 是 | 强弱差、淘汰赛点球倾斜 | 缺失球队 fallback 1500 |
| FIFA 排名 | 官方排名、积分、排名日期 | FIFA official rankings API | `fifa_ranking_snapshot.csv`、`raw/fifa_rankings_men_latest.json` | `StrengthAgent` | 是，211 队 | 是 | 是 | 小幅修正球队强度 | 与 Elo 信息重叠，权重很小 |
| 官方首发/替补 | 官方比赛名单、首发、替补、队长、号码、位置 | FIFA match centre live API `/live/football/...` | `inputs/lineups/match20_austria_jordan_fifa_official.csv` | `LineupAgent` | 是，奥地利-约旦 52 人 | 传入 `--lineup-file` 后是 | 是，需赛前快照 | 首发质量、替补默认分钟、球员评分 fallback | 只针对已拉取比赛；伤停未单独暴露 |
| 国家队名单 | 赛事赛季 48 队名单、球员 ID、号码、位置 | FIFA `/teams/squads/all/17/285023` | `raw/fifa_api/season_teams_squads.json`、`processed/fifa_match20_squad.csv` | 暂作审计/匹配 | 是，48 队；match20 52 人 | 否，除非转成 lineup | 是 | 球员身份、名单校验、后续批量匹配 | 不等同于首发；需按比赛 live endpoint 确认 |
| FIFA 球员资料 | 身高、体重、生日、国家队出场/进球、FIFA 统计 | FIFA `/players/{id}`、`/individualstatistics/player/{id}` | `inputs/player_performance/fifa_match20_player_profiles.csv` | 暂作审计/匹配 | 是，match20 52 人 | 否 | 是 | 身份补全、国家队履历参考 | 不是完整俱乐部+国家队逐场表现 |
| EA FC 球员评分 | 静态游戏能力评分、位置、俱乐部、国籍 | EA ratings page 验证；GitHub/Kaggle mirror CSV | `inputs/player_ratings/eafc26_player_ratings.csv` | `PlayerRatingsAgent` | 是，18405 行 | 仅传入 `--player-ratings-file` 后是 | 是，静态赛前评分 | lineup 缺 rating 时按姓名/国籍/俱乐部回填 | 不是 FIFA 官方评分；镜像许可未完全验证 |
| 球员表现样本 | 球员逐场事件、分钟、射门、xG、防守动作、牌 | StatsBomb Open Data events/lineups | `inputs/player_performance/player_match_performance.csv` | `MatchContextAgent` | 是，433 行 | `--use-generated-context` 后是 | 是，作为历史样本 | 球员表现转球队攻防上下文 | 覆盖不完整；奥地利有样本，约旦无样本 |
| 阵容到表现匹配 | 官方阵容球员与本地表现样本的匹配汇总 | FIFA lineup + StatsBomb sample 派生 | `processed/fifa_match20_lineup_player_performance_join.csv` | 审计表 | 是 | 否 | 是 | 说明哪些首发/替补有历史事件样本 | match20 奥地利 14 人匹配，约旦 0 人匹配 |
| 球队级事件样本 | 半场黄牌、红牌、角球、任意球、点球 | StatsBomb Open Data events | `statsbomb_event_half_team_summary.csv` | `EventAgent` | 是，64 行 | 是 | 是 | 事件数量按上下半场预测 | 奥地利 16 个半场；约旦 0，回退全局均值 |
| 天气 | 开球小时温度、湿度、降水、风速 | Open-Meteo forecast API | `inputs/match_context/weather_forecast.csv` | `MatchContextAgent` | 是，36 行 | `--use-generated-context` 后是 | 是，需临近开球刷新 | 总进球环境、定位球环境 | 预报会变化；只有 match20 已精确到 kickoff hour |
| 旅行疲劳 | 旅行距离、休息天、时区、训练干扰 | 赛程+球场坐标本地派生 | `inputs/match_context/team_travel_fatigue.csv` | `MatchContextAgent` | 是，144 行 | `--use-generated-context` 后是 | 是 | 疲劳乘数 | 首场默认中性；淘汰赛需路径确定后再算 |
| 战术先验 | 压迫、宽度、定位球、反击、防线、控球 | Elo+近期状态本地派生 | `inputs/match_context/tactics.csv` | `MatchContextAgent` | 是，48 行 | `--use-generated-context` 后是 | 是 | 攻防上下文乘数 | 启发式先验，不是官方战术计划 |
| 官方阵型 | 赛前阵型文本 | FIFA live API `HomeTeam.Tactics` / `AwayTeam.Tactics` | `raw/fifa_api/match20_live.json` | 暂作审计 | 是，match20 奥地利 `4-2-3-1`、约旦 `3-4-3` | 否 | 是 | 校验阵容结构，后续可转战术输入 | 当前尚未覆盖到 `tactics.csv` 计算 |
| 裁判 | 指派裁判、全局判罚先验 | FIFA calendar officials；StatsBomb 事件样本 | `raw/fifa_api/match20_calendar.json`、`inputs/match_context/referees.csv` | `MatchContextAgent` | 指派裁判已获得；历史判罚仅全局 prior | 全局 prior 已进入 | 是 | 牌、犯规、点球、总进球环境 | Dahane BEIDA 的个人历史判罚未接入 |
| 赔率 | 1X2、大小球、角球等商业赔率 | TheStatsAPI odds page/API | `raw/thestatsapi_odds_page.html` | 无 | 页面已保存；API 需 key | 否 | 理论上是赛前安全 | 当前明确不使用真实赔率 | 需要合法 API key 且用户改范围 |
| 伤停/停赛 | 伤病、停赛、限制出场 | 未找到 FIFA live 独立字段 | 无正式输入 | `LineupAgent` 可读取 `role=unavailable` | 否 | 否 | 仅可信赛前源安全 | 可影响伤停损失 | 需要球队官方/FIFA/商业源单独提供 |
| 替补策略 | 预计换人时间、计划替补分钟 | 当前由 lineup 默认规则生成 | `inputs/lineups/*.csv` | `LineupAgent` | 部分，替补名单已获得 | 是，默认替补 25 分钟 | 是，但只是模型假设 | 替补深度和预期分钟 | 真实换人计划赛前通常非官方 |
| 赛中球员统计 | 本场 live player stats | FIFA `/playerstatistics/match/...` | 验证为赛前 `null` | 无 | 端点存在，赛前为空 | 否 | 赛前不能用赛中数据 | 赛后复盘可用 | 不能进入赛前预测 |

## Match 20 当前补齐状态

奥地利 vs 约旦已经完成一次赛前数据补齐：

- FIFA 官方比赛名单：52 行，22 名首发，30 名替补。
- FIFA 球员资料/统计：52 人可取到。
- Open-Meteo 精确开球小时天气：`2026-06-17T04:00:00Z`，Levi's Stadium。
- StatsBomb 球队事件样本：奥地利 16 个半场，约旦 0 个半场。
- StatsBomb 球员表现匹配：奥地利 14 人匹配到本地样本，约旦 0 人。
- FIFA timeline 赛前事件：0，说明不能拿它当赛前事件统计。

补齐命令：

```powershell
python worldcup_data_audit\scripts\build_match20_gap_inputs.py
```

预测命令：

```powershell
python -m worldcup_predictor predict-match --home Austria --away Jordan --match-id 20 `
  --use-generated-context `
  --lineup-file inputs\lineups\match20_austria_jordan_fifa_official.csv `
  --lineup-allowed-source fifa_api_live_match `
  --player-ratings-file inputs\player_ratings\eafc26_player_ratings.csv
```

## 使用边界

- 赛前预测不得使用终场比分、赛后评分、赛中 live player stats。
- EA FC 评分只能叫静态游戏评分 fallback，不能叫 FIFA 官方球员评分。
- FIFA 球员 profile 不是完整表现数据；它不能替代俱乐部+国家队逐场表现样本。
- 官方首发可以接入；伤停和停赛必须有独立可信来源后才写入 `unavailable`。
- 约旦目前缺少球队事件样本和球员表现样本，因此对应特征仍会回退。
