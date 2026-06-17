# pameldas 项目对比改进记录：比分与进球误差回测指标

Generated: 2026-06-17

## 本轮只针对的项目

- 项目：pameldas/FIFA-World-Cup-2026-Prediction-Framework
- 链接：https://github.com/pameldas/FIFA-World-Cup-2026-Prediction-Framework
- 可借鉴点：README 中公开了 Poisson goal modeling、Random Forest evaluation、权重选择，以及 `Combined Goal MAE`、`Combined Goal RMSE`、`Rounded Exact Score Accuracy` 等评估指标。

## 本轮吸收的能力

只吸收一个能力：更完整的回测评估指标。

本轮新增：

- `outcome_accuracy`
- `exact_score_accuracy`
- `top3_scoreline_accuracy`
- `home_goal_mae`
- `away_goal_mae`
- `total_goal_mae`
- `combined_goal_mae`
- `home_goal_rmse`
- `away_goal_rmse`
- `total_goal_rmse`
- `combined_goal_rmse`

没有在本轮吸收：

- Random Forest。
- Poisson/Random Forest hybrid weight tuning。
- F1/precision/recall 分类报告。
- 新训练数据。
- 模型融合。

这些不在本轮做，避免一次性混入 ML 分类器和权重调参。

## 改动文件

模型代码：

- `worldcup_predictor/backtest.py`

测试：

- `tests/test_worldcup_predictor.py`

skill 文档：

- `C:\Users\81901\.codex\skills\worldcup-predict\SKILL.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\README.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\model-overview.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\commands-and-validation.md`

## 新增模型行为

回测命令不变：

```powershell
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1
```

输出会额外包含比分和进球误差指标。

指标解释：

- `outcome_accuracy`：胜平负预测结果是否命中。
- `exact_score_accuracy`：Top 1 比分是否精确命中。
- `top3_scoreline_accuracy`：真实比分是否落在 Top 3 scorelines。
- `combined_goal_mae`：主客队进球预测的平均绝对误差。
- `combined_goal_rmse`：主客队进球预测的均方根误差。
- `total_goal_mae` / `total_goal_rmse`：总进球预测误差。

## 为什么这轮重要

之前我们的回测更偏概率质量：

- log-loss。
- Brier。
- RPS。
- calibration buckets。

这些指标能说明“胜平负概率是否靠谱”，但不能充分说明：

- 精确比分是否靠谱。
- Top 比分排序是否靠谱。
- 预期进球是否偏高或偏低。

用户明确关心“确切比分”和“最终进球数”，所以回测必须包含比分层面的指标。

## 检查结果

已执行：

```powershell
python -m unittest discover -s tests -v
python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1 --output outputs\reports\backtest_metrics_pameldas_eval.json
```

结果：

- 单元测试：17 项全部通过。
- 回测输出：新增指标存在。
- skill 同步：主 `SKILL.md`、skill `README.md`、`model-overview.md`、`commands-and-validation.md` 均已更新。

当前 2018+ 回测结果：

| 指标 | 数值 |
|---|---:|
| outcome_accuracy | 0.514706 |
| exact_score_accuracy | 0.095588 |
| top3_scoreline_accuracy | 0.242647 |
| combined_goal_mae | 0.997225 |
| combined_goal_rmse | 1.279184 |
| total_goal_mae | 1.448381 |
| total_goal_rmse | 1.873439 |

## 使用口径

以后判断一个改动是否真的提高模型，不要只看一个指标。

概率质量看：

- log-loss。
- Brier。
- RPS。
- calibration。

比分质量看：

- exact score accuracy。
- top-3 scoreline accuracy。
- combined goal MAE/RMSE。
- total goal MAE/RMSE。

如果某个改动只让 exact score accuracy 轻微变好，但 log-loss、RPS 或 calibration 明显变差，不能说它整体提高了预测模型。

## 下一轮建议

下一轮继续选择一个项目、一个改进点：

1. `pravindurgani/wc26-matchday-intelligence`：只吸收 append-only prediction audit log。
2. `kamil-kucharski/world-cup-2026-prediction`：只做 FIFA ranking Poisson baseline sanity check。
3. `rivu-intel45/FIFA-2026-Winner-Prediction`：只做 ML calibration 的计划或实验开关，不默认启用。

按用户要求，每一轮继续执行：

- 单项目对比。
- 单一改进范围。
- 模型代码改动。
- skill 同步。
- 测试/CLI/报告检查。
- 独立迭代记录。
