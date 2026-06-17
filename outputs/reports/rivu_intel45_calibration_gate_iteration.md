# rivu-intel45 项目对比改进记录：W/D/L calibration gate

## 本轮只针对的项目

- 项目：`rivu-intel45/FIFA-2026-Winner-Prediction`
- 链接：https://github.com/rivu-intel45/FIFA-2026-Winner-Prediction
- 已验证可借鉴点：README 显示该项目用 XGBoost、Elo、近期状态、H2H、neutral、tournament weight 做胜平负分类和 2026 fixture prediction。

## 本轮吸收了什么

没有把 XGBoost 直接接入主模型，而是先吸收“胜平负分类概率需要独立校准/评估”的思想，新增默认关闭的 `calibration-backtest`。

新增能力：

- `worldcup_predictor/calibration.py`
- `python -m worldcup_predictor calibration-backtest --start-year 2018 --min-prior-matches 1`
- 输出：`outputs/reports/calibration_backtest.json`
- 方法：在历史预测概率上拟合轻量 `temperature + draw_multiplier`，再在 2018 以后做 out-of-sample 评估。

## 本轮没有吸收什么

- 没有引入 XGBoost 依赖。
- 没有把分类器替代 Poisson/Dixon-Coles 比分矩阵。
- 没有改变当前生产预测的比分、胜平负、事件数量或赛事模拟。
- 没有把校准层默认开启。

## 本轮结果

命令：

```powershell
python -m worldcup_predictor calibration-backtest --start-year 2018 --min-prior-matches 1
```

结果摘要：

- training matches: 765
- evaluation matches: 136
- selected temperature: 1.7
- selected draw multiplier: 0.8
- evaluation log-loss delta: -0.036132
- evaluation Brier delta: -0.010116
- evaluation RPS delta: -0.004891
- evaluation ECE delta: -0.015233
- gate default enable recommended: true

解释：

- 这个结果说明“概率校准层”值得作为下一步候选功能继续做。
- 但当前实现仍是 gate-only，不会自动改变生产预测。
- 如果要接入生产预测，下一步必须解决比分矩阵一致性问题：不能只改胜平负概率而让 Top scorelines 保持旧分布。

## 文件变更

- `worldcup_predictor/calibration.py`
- `worldcup_predictor/cli.py`
- `tests/test_worldcup_predictor.py`
- `C:\Users\81901\.codex\skills\worldcup-predict\SKILL.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\README.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\model-overview.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\commands-and-validation.md`

## 验证

- `python -m unittest discover -s tests -v`
  - Result: 21 tests passed.
- `python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root .`
  - Result: status `ok`; no warnings.
- `python -m worldcup_predictor calibration-backtest --start-year 2018 --min-prior-matches 1`
  - Result: generated `outputs/reports/calibration_backtest.json`.

## 下一步边界

只有在后续显式实现“校准后仍保持比分矩阵一致”的可选预测模式后，才可以让该校准层影响实际预测输出。当前最多只能说：`rivu-intel45` 启发的分类校准方向，在历史概率指标上通过了初步 gate。
