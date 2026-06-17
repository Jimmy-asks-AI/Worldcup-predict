# kamil-kucharski 项目对比改进记录：FIFA ranking Poisson baseline

Generated: 2026-06-17

## 本轮只针对的项目

- 项目：kamil-kucharski/world-cup-2026-prediction
- 链接：https://github.com/kamil-kucharski/world-cup-2026-prediction
- 可借鉴点：README 显示该项目使用历史国际赛、FIFA ranking data、FIFA rank/points、points diff、host/neutral 等特征训练 Poisson 模型，并用 Monte Carlo 模拟 2026 赛事。

## 本轮吸收的能力

只吸收一个能力：建立一个简单的 FIFA ranking/points Poisson baseline，用来做 sanity check。

本轮新增：

- `RankingBaselineAgent`
- `python -m worldcup_predictor ranking-baseline`
- `outputs/reports/ranking_baseline_sanity_check.json`

没有在本轮吸收：

- Poisson regression 训练流程。
- 1000 次 Monte Carlo baseline 模拟。
- Notebook 结构。
- injury 缺口处理。
- advanced Elo history。
- neutral/location 更复杂建模。

这些不在本轮做，避免把 baseline 工具扩展成另一个预测系统。

## 改动文件

模型代码：

- `worldcup_predictor/baselines.py`
- `worldcup_predictor/cli.py`

测试：

- `tests/test_worldcup_predictor.py`

skill 文档：

- `C:\Users\81901\.codex\skills\worldcup-predict\SKILL.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\README.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\model-overview.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\commands-and-validation.md`

## 新增命令

```powershell
python -m worldcup_predictor ranking-baseline --home France --away Senegal
```

输出文件：

```powershell
outputs\reports\ranking_baseline_sanity_check.json
```

输出包含：

- `main_model`
- `ranking_baseline`
- `comparison`
- `ranking_baseline.features`
- `ranking_baseline.caveats`

## baseline 方法

这个 baseline 只使用：

- 当前 FIFA rank。
- 当前 FIFA points。
- 世界杯历史平均每队进球。
- 主办国轻量 host multiplier。
- Poisson 比分矩阵。

它不使用：

- Elo。
- 近期状态。
- 世界杯球队历史攻防。
- 官方阵容。
- 伤停。
- 球员评分。
- 天气。
- 旅行。
- 战术。
- 裁判。
- 事件样本。

## 为什么这轮重要

随着主模型接入 Elo、FIFA、近期状态、世界杯历史、阵容、上下文、事件和不确定性，模型复杂度在上升。

一个简单 baseline 可以回答：

- 如果只看 FIFA 排名/积分，结论是什么？
- 主模型比 baseline 更激进还是更保守？
- 主模型和 baseline 的 Top scoreline 是否一致？
- 额外特征是否让输出偏离直觉太远？

这不是为了替代主模型，而是为了防止复杂模型跑偏后没有参照物。

## 检查结果

已执行：

```powershell
python -m unittest discover -s tests -v
python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root E:\Vibe-coding\小红书
python -m worldcup_predictor ranking-baseline --home France --away Senegal --match-id 97 --output outputs\reports\ranking_baseline_sanity_check.json
```

结果：

- 单元测试：19 项全部通过。
- 健康检查：通过。
- `ranking-baseline`：通过。
- 输出 JSON：已生成。
- baseline 胜平负概率和：1.0。
- skill 同步：主 `SKILL.md`、skill `README.md`、`model-overview.md`、`commands-and-validation.md` 均已更新。

## 当前样例：France vs Senegal

| 指标 | 主模型 | FIFA ranking baseline | 主模型 - baseline |
|---|---:|---:|---:|
| France 胜 | 0.663645 | 0.417646 | +0.245999 |
| 平局 | 0.195038 | 0.250259 | -0.055221 |
| Senegal 胜 | 0.141317 | 0.332095 | -0.190778 |
| France lambda | 2.1266 | 1.5078 | +0.6188 |
| Senegal lambda | 0.8635 | 1.3180 | -0.4545 |

解释：

- ranking baseline 只看到 FIFA rank/points，认为法国只是中等幅度占优。
- 主模型额外加入 Elo、近期状态、世界杯历史攻防等因素，因此更明显偏向法国。
- 这不说明 baseline 错，也不说明主模型一定对；它提供了一个简洁参照。

## 使用边界

- baseline 使用当前 FIFA ranking snapshot，因此不是 time-safe 历史回测。
- baseline 不接入真实赔率。
- baseline 不接入官方首发、伤停或球员表现。
- baseline 不应出现在正式预测结论前面，只能作为“对照模型”解释。

## 下一轮建议

下一轮继续选择一个项目、一个改进点：

1. `rivu-intel45/FIFA-2026-Winner-Prediction`：只做 ML calibration 的实验开关，不默认启用。
2. `javierruanohdez/world-cup-2026-prediction`：只改报告里对 2026 新赛制随机性的解释。
3. `alan-turing-institute/WorldCupPrediction`：只补 Dixon-Coles rho 网格搜索，不引入完整包结构。

按用户要求，每一轮继续执行：

- 单项目对比。
- 单一改进范围。
- 模型代码改动。
- skill 同步。
- 测试/CLI/报告检查。
- 独立迭代记录。
