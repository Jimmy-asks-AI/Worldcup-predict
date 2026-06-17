# GitHub 世界杯预测项目逐项改进状态

## 已吸收并落地

| 项目 | 落地内容 | 当前状态 |
|---|---|---|
| Hicruben/world-cup-2026-prediction-model | 可选 Dixon-Coles 低比分修正 | 已实现，默认仍为 independent Poisson |
| lbenz730/world_cup_2026 | 单场 p05/p50/p95 不确定性区间 | 已实现，需显式 `--include-uncertainty` |
| pameldas/FIFA-World-Cup-2026-Prediction-Framework | exact score、top-3 scoreline、goal MAE/RMSE 回测指标 | 已实现 |
| pravindurgani/wc26-matchday-intelligence | append-only 预测审计日志 | 已实现 |
| kamil-kucharski/world-cup-2026-prediction | FIFA ranking/points Poisson sanity baseline | 已实现，非生产模型 |
| javierruanohdez/world-cup-2026-prediction | 2026 新赛制随机性报告解释 | 已实现，报告层能力 |
| rivu-intel45/FIFA-2026-Winner-Prediction | W/D/L calibration gate | 已实现，默认关闭，作为后续接入门禁 |
| alan-turing-institute/WorldCupPrediction | Dixon-Coles rho tuning gate | 已实现，默认关闭，当前不建议切默认模型 |

## 明确不直接吸收

| 项目 | 不直接吸收的原因 |
|---|---|
| EhteshamBahoo/Fifa-WorldCup-Data-Analysis-1930-2026 | 教学型 Random Forest Regressor 不适合作为离散比分主模型；我们已有更完整的数据契约、CSV/Markdown 输出和审计日志 |
| ysadre/FifaWC_Predictions | 2022 分类实验；不覆盖 2026 赛制、比分分布、阵容、事件数量和中文 skill 工作流 |
| jieguangzhou/FIFA-World-Cup-2022 | FLAML/下注工作流偏 2022 和 betting；当前模型明确不接入真实赔率，不采用下注链路 |
| neaorin/PredictTheWorldCup | R 语言教学项目；对当前 Python CLI + skill 系统没有足够新增价值 |
| neelabhsinha/fifa-world-cup-prediction-ml | 多算法分类思路已通过 `calibration-backtest` 吸收为校准门禁；不直接替代 Poisson score matrix |
| lblommesteyn/WorldCupPrediction | 当前不可访问，不能作为有效证据改模型 |

## 当前新增命令

```powershell
python -m worldcup_predictor tune-dixon-coles --start-year 2018 --min-prior-matches 1
python -m worldcup_predictor calibration-backtest --start-year 2018 --min-prior-matches 1
python -m worldcup_predictor ranking-baseline --home France --away Senegal
```

## 最新验证

- `python -m unittest discover -s tests -v`
  - Result: 22 tests passed.
- `python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root .`
  - Result: status `ok`; no warnings.
- `python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --sample-match-id 97 --use-generated-context --include-uncertainty --uncertainty-samples 80`
  - Result: generated `outputs/reports/worldcup_prediction_report.md` with `2026 赛制随机性`.

## 结论

当前不建议把任何 GitHub 项目的黑盒分类器或教学型回归模型直接替换为主模型。正确方向是继续保留本地多 Agent 架构：比分分布由 Poisson/Dixon-Coles 系列负责，概率质量由 backtest/calibration/tuning gate 证明，数据可靠性由 audit log 和数据契约控制。
