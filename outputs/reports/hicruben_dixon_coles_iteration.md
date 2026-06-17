# Hicruben 项目对比改进记录：Dixon-Coles 比分模型

Generated: 2026-06-17

## 本轮只针对的项目

- 项目：Hicruben/world-cup-2026-prediction-model
- 链接：https://github.com/Hicruben/world-cup-2026-prediction-model
- 可借鉴点：`Elo ratings -> Dixon-Coles bivariate Poisson -> Monte Carlo simulation`，以及 RPS/log-loss/Brier/ECE 这类回测意识。

## 本轮吸收的能力

只吸收一个能力：Dixon-Coles 低比分相关性修正。

没有在本轮吸收：

- 50,000 次默认模拟。
- ECE/reliability curve。
- live site。
- in-tournament conditioning。
- JavaScript 项目结构。

这些留到后续项目或后续单独迭代，避免一次性混入太多变化。

## 改动文件

模型代码：

- `worldcup_predictor/score_models.py`
- `worldcup_predictor/scoreline.py`
- `worldcup_predictor/models.py`
- `worldcup_predictor/tournament.py`
- `worldcup_predictor/backtest.py`
- `worldcup_predictor/cli.py`
- `worldcup_predictor/report.py`

测试：

- `tests/test_worldcup_predictor.py`

skill 文档：

- `C:\Users\81901\.codex\skills\worldcup-predict\SKILL.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\model-overview.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\commands-and-validation.md`

## 新增模型行为

默认行为保持不变：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal
```

仍使用：

- `score_model = independent_poisson`

可选启用 Dixon-Coles：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --score-model dixon_coles
```

新增参数：

- `--score-model independent_poisson|dixon_coles`
- `--dixon-coles-rho -0.08`

Dixon-Coles 只修正：

- `0-0`
- `0-1`
- `1-0`
- `1-1`

它不会改变：

- Elo。
- FIFA 排名。
- 近期状态。
- 阵容/伤停。
- 天气/旅行/战术/裁判。
- 事件数量样本。

## 为什么没有切换默认模型

同一回测配置：

```powershell
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1 --score-model dixon_coles
```

结果：

| 模型 | Brier | Log-loss | RPS | 样本 |
|---|---:|---:|---:|---:|
| independent_poisson | 0.616127 | 1.054189 | 0.220728 | 136 |
| dixon_coles rho=-0.08 | 0.617039 | 1.059812 | 0.220880 | 136 |

结论：

- `dixon_coles` 已经可用，并会提高 0-0、1-1 等低比分平局概率。
- 但固定 `rho=-0.08` 在当前 2018+ 世界杯回测样本上没有优于默认模型。
- 因此本轮只把它作为可选模型加入，不把默认从 `independent_poisson` 切到 `dixon_coles`。
- 下一步如果继续沿 Hicruben 路线，应先做 rho 网格搜索或 ECE/reliability curve，而不是盲目提高修正强度。

## 检查结果

已执行：

```powershell
python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root E:\Vibe-coding\小红书
python -m unittest discover -s tests -v
python -m worldcup_predictor predict-match --home France --away Senegal --score-model dixon_coles
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1 --score-model dixon_coles --output outputs\reports\backtest_metrics_dixon_coles.json
python -m worldcup_predictor simulate-tournament --runs 200 --score-model dixon_coles
python -m worldcup_predictor simulate-tournament --runs 20000
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal
```

结果：

- 健康检查：通过。
- 单元测试：16 项全部通过。
- Dixon-Coles 单场预测：通过，输出 `score_model=dixon_coles` 和 `score_model_parameters`。
- Dixon-Coles 回测：通过，输出 `outputs/reports/backtest_metrics_dixon_coles.json`。
- Dixon-Coles 小规模赛事模拟：通过。
- 默认 20,000 次赛事模拟：已重新生成，避免留下检查用 200 次结果。
- 中文报告：已重新生成，并包含比分模型字段。
- skill 同步：已更新主 skill 和两个 reference 文件。

## 下一轮建议

不要直接进入所有项目的混合改造。

下一轮可以在两个方向中选一个：

1. 继续 Hicruben：补 ECE/reliability curve 和 rho 网格搜索，仍只围绕这个项目。
2. 切到 lbenz730：只做不确定性区间，不碰 live dashboard 或 ML 校准。

按用户要求，每一轮都应完成：

- 单项目对比。
- 单一改进范围。
- 模型代码改动。
- skill 同步。
- 测试/CLI/报告检查。
- 独立迭代记录。
