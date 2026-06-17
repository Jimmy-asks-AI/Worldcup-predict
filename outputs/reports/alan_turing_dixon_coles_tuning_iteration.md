# Alan Turing Institute 项目对比改进记录：Dixon-Coles rho tuning

## 本轮只针对的项目

- 项目：`alan-turing-institute/WorldCupPrediction`
- 链接：https://github.com/alan-turing-institute/WorldCupPrediction
- 已验证可借鉴点：README 说明其原始模型是 Dixon and Coles 的一个版本，并提供 tournament simulation CLI；其 AIrgentina 模型曾参加 2022 World Cup Sophisticated Prediction Contest。

## 本轮吸收了什么

我们已经在前序 Hicruben 迭代中加入了 Dixon-Coles 低比分修正。本轮只补一个更严谨的调参/验证入口：

```powershell
python -m worldcup_predictor tune-dixon-coles --start-year 2018 --min-prior-matches 1
```

输出：

```powershell
outputs/reports/dixon_coles_rho_tuning.json
```

它会比较：

- independent Poisson baseline。
- 多个 Dixon-Coles `rho` 候选。
- log-loss、Brier、RPS、outcome accuracy、exact score accuracy、top-3 scoreline accuracy、goal MAE/RMSE。
- 是否达到“实质改善”门槛。

## 本轮没有吸收什么

- 没有引入 numpyro/Bayesian 依赖。
- 没有迁移 Alan Turing 的完整训练框架。
- 没有改变默认 score model。
- 没有改变 tournament simulation 逻辑。

## 本轮结果

命令：

```powershell
python -m worldcup_predictor tune-dixon-coles --start-year 2018 --min-prior-matches 1
```

结果摘要：

- independent Poisson log-loss: 1.054189
- best Dixon-Coles rho: 0.04
- best Dixon-Coles log-loss: 1.052173
- log-loss delta: -0.002016
- Brier delta: -0.000126
- RPS delta: -0.000021
- top-3 scoreline accuracy delta: 0.0
- gate default enable recommended: false

解释：

- `rho=0.04` 在数值上略优，但改善太小。
- 当前 gate 使用实质改善阈值：
  - log-loss 至少改善 0.005
  - Brier 至少改善 0.002
  - RPS 至少改善 0.001
- 本轮没有达到阈值，因此默认模型继续保持 `independent_poisson`。
- 如果用户想试验，可以显式传 `--score-model dixon_coles --dixon-coles-rho 0.04`，但不能说它已经被证明应默认替代主模型。

## 文件变更

- `worldcup_predictor/backtest.py`
- `worldcup_predictor/cli.py`
- `tests/test_worldcup_predictor.py`
- `C:\Users\81901\.codex\skills\worldcup-predict\SKILL.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\README.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\model-overview.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\commands-and-validation.md`

## 验证

- `python -m unittest discover -s tests -v`
  - Result: 22 tests passed.
- `python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root .`
  - Result: status `ok`; no warnings.
- `python -m worldcup_predictor tune-dixon-coles --start-year 2018 --min-prior-matches 1`
  - Result: generated `outputs/reports/dixon_coles_rho_tuning.json`.

## 下一步边界

这个改进提升的是模型治理能力：以后可以稳定比较 rho 候选。它没有证明 Dixon-Coles 应默认开启，也没有改变生产预测。
