# lbenz730 项目对比改进记录：单场不确定性区间

Generated: 2026-06-17

## 本轮只针对的项目

- 项目：lbenz730/world_cup_2026
- 链接：https://github.com/lbenz730/world_cup_2026
- 可借鉴点：README 显示该项目用 `fit_model.R` 估计 Bayesian bivariate Poisson，并用 `run_sim.R` 做 10,000 次 2026 世界杯赛事模拟。

## 本轮吸收的能力

只吸收一个能力：不要只输出单点概率，还要输出概率区间。

本轮实现的是轻量版：

- 新增 `UncertaintyAgent`。
- 使用固定随机种子围绕最终 `lambda_home` / `lambda_away` 做 lognormal 扰动。
- 输出：
  - `p_home_win` 的 p05/p50/p95。
  - `p_draw` 的 p05/p50/p95。
  - `p_away_win` 的 p05/p50/p95。
  - `expected_goals` 的 p05/p50/p95。

没有在本轮吸收：

- 完整 Bayesian bivariate Poisson。
- Stan/R 模型。
- attack/defense posterior。
- 赛事冠军概率区间。
- 10,000 次模拟结果表样式。

这些不在本轮做，避免一次性把 lbenz730 的整套统计系统搬进来。

## 改动文件

模型代码：

- `worldcup_predictor/uncertainty.py`
- `worldcup_predictor/scoreline.py`
- `worldcup_predictor/models.py`
- `worldcup_predictor/cli.py`
- `worldcup_predictor/report.py`

测试：

- `tests/test_worldcup_predictor.py`

skill 文档：

- `C:\Users\81901\.codex\skills\worldcup-predict\SKILL.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\README.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\model-overview.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\commands-and-validation.md`

## 新增模型行为

默认行为保持不变：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal
```

不会计算不确定性区间。

显式启用：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --include-uncertainty
```

可调样本数：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --include-uncertainty --uncertainty-samples 500
```

输出新增字段：

- `uncertainty`
- `explanation.factors.uncertainty`

## 方法边界

这不是完整 Bayesian 模型。

准确口径：

- lbenz730 启发的轻量不确定性代理。
- 围绕当前模型已经算出的最终 lambda 做扰动。
- 不改变胜平负点估计。
- 不接入新数据。
- 不产生球队 attack/defense posterior。
- 不代表真实 Bayesian bivariate Poisson 后验。

为什么先做轻量版：

- 当前项目是 Python CLI + skill，不是 R/Stan 统计项目。
- 完整 Bayesian 需要重新设计训练流程、依赖、参数存储和回测。
- 用户要求一次只针对一个项目做一个改进，因此先做可验证、可解释、可回退的区间输出。

## 检查结果

已执行：

```powershell
python -m unittest discover -s tests -v
python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root E:\Vibe-coding\小红书
python -m worldcup_predictor predict-match --home France --away Senegal --include-uncertainty --uncertainty-samples 80
python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --include-uncertainty --uncertainty-samples 80
```

结果：

- 单元测试：17 项全部通过。
- 健康检查：通过。
- 单场 CLI：输出 `uncertainty.intervals`。
- 中文报告：输出“单场不确定性区间”章节。
- skill 同步：主 `SKILL.md`、skill `README.md`、`model-overview.md`、`commands-and-validation.md` 均已更新。

## 当前样例输出

示例命令：

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --include-uncertainty --uncertainty-samples 80
```

样例区间：

| 指标 | p05 | p50 | p95 |
|---|---:|---:|---:|
| France 胜 | 0.574949 | 0.670414 | 0.750517 |
| 平局 | 0.150913 | 0.192512 | 0.225666 |
| Senegal 胜 | 0.093471 | 0.137858 | 0.194926 |
| 预期总进球 | 2.588681 | 2.997191 | 3.546441 |

注：正式报告中的样例可能因 sample match 或上下文输入不同而不同，但结构一致。

## 下一轮建议

不要继续扩大 lbenz730 的能力范围，除非明确选择“完整 Bayesian 化”。

下一轮可以选择下一个项目：

1. `pameldas/FIFA-World-Cup-2026-Prediction-Framework`：只吸收 exact score accuracy、goal MAE/RMSE 等评估指标。
2. `pravindurgani/wc26-matchday-intelligence`：只吸收 append-only audit log 或 matchday refresh，不碰 dashboard。
3. `kamil-kucharski/world-cup-2026-prediction`：只做一个轻量 ranking baseline sanity check。

按用户要求，每一轮都继续执行：

- 单项目对比。
- 单一改进范围。
- 模型代码改动。
- skill 同步。
- 测试/CLI/报告检查。
- 独立迭代记录。
