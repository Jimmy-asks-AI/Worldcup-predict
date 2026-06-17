# pravindurgani 项目对比改进记录：append-only 预测审计日志

Generated: 2026-06-17

## 本轮只针对的项目

- 项目：pravindurgani/wc26-matchday-intelligence
- 链接：https://github.com/pravindurgani/wc26-matchday-intelligence
- 可借鉴点：README 显示该项目的 matchday intelligence 会把每次决策追加到 `data/live/matchday_intelligence_log.jsonl`，形成 append-only audit log。

## 本轮吸收的能力

只吸收一个能力：append-only 预测审计日志。

本轮新增：

- `worldcup_predictor/audit.py`
- `outputs/audit/prediction_runs.jsonl`
- `predict-match` 自动追加一条审计记录。
- `report` 自动追加一条 sample match 审计记录。
- CLI 输出新增 `audit_log` 路径。

没有在本轮吸收：

- API-Football injuries。
- API-Football lineups。
- API-Football live statistics。
- OpenWeather live workflow。
- GitHub Actions 定时刷新。
- Vercel/dashboard。
- Cloudflare worker。
- matchday adjustment caps。

这些不在本轮做，避免把 pravindurgani 的整套 live 系统一次性搬进来。

## 改动文件

模型代码：

- `worldcup_predictor/audit.py`
- `worldcup_predictor/cli.py`

测试：

- `tests/test_worldcup_predictor.py`

skill 文档：

- `C:\Users\81901\.codex\skills\worldcup-predict\SKILL.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\README.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\model-overview.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\commands-and-validation.md`

## 新增行为

运行：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal
```

会追加写入：

```powershell
outputs\audit\prediction_runs.jsonl
```

查看最后一条：

```powershell
Get-Content -Encoding UTF8 outputs\audit\prediction_runs.jsonl -Tail 1
```

每条记录包含：

- `timestamp_utc`
- `run_type`
- `command`
- `argv`
- `cli_options`
- `pre_match_safe_boundary`
- `data_files`
- `prediction`
- `explanation_summary`

`data_files` 会记录：

- 输入文件路径。
- 文件是否存在。
- 文件大小。
- SHA256。
- CSV 行数。

## 方法边界

审计日志不改变预测。

它只记录：

- 本地命令。
- 本地文件元数据。
- 模型参数。
- 输出概率。
- warning。

它不会：

- 拉取 live API。
- 判断伤停严重程度。
- 自动获取官方首发。
- 让赛中/赛后数据变成赛前安全数据。
- 接入真实赔率。

## 检查结果

已执行：

```powershell
python -m unittest discover -s tests -v
python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root E:\Vibe-coding\小红书
python -m worldcup_predictor predict-match --home France --away Senegal --match-id 97 --include-uncertainty --uncertainty-samples 80
python -m worldcup_predictor report --runs 20 --sample-home France --sample-away Senegal --include-uncertainty --uncertainty-samples 80
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --include-uncertainty --uncertainty-samples 80
```

结果：

- 单元测试：18 项全部通过。
- 健康检查：通过。
- `predict-match`：成功追加 `predict_match` 审计记录。
- `report`：成功追加 `report_sample` 审计记录。
- 正式报告：已用 20,000 次模拟重新生成，避免保留 20 次检查输出。
- skill 同步：主 `SKILL.md`、skill `README.md`、`model-overview.md`、`commands-and-validation.md` 均已更新。

最后一次审计记录验证：

| 字段 | 值 |
|---|---|
| run_type | `predict_match` / `report_sample` |
| command | `predict-match` / `report` |
| fixture rows | 104 |
| fixture hash | 已记录 |
| uses_real_betting_odds | `false` |
| uncertainty_used | `true` when enabled |

## 下一轮建议

下一轮继续选择一个项目、一个改进点：

1. `kamil-kucharski/world-cup-2026-prediction`：只做 FIFA ranking Poisson baseline sanity check。
2. `rivu-intel45/FIFA-2026-Winner-Prediction`：只做 ML calibration 的实验开关，不默认启用。
3. `javierruanohdez/world-cup-2026-prediction`：只改报告里对 2026 赛制随机性的解释，不引入 Gradient Boosting。

按用户要求，每一轮继续执行：

- 单项目对比。
- 单一改进范围。
- 模型代码改动。
- skill 同步。
- 测试/CLI/报告检查。
- 独立迭代记录。
