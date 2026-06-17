# javierruanohdez Format Randomness Iteration

## Compared Project

- Repository: `javierruanohdez/world-cup-2026-prediction`
- Source: https://github.com/javierruanohdez/world-cup-2026-prediction
- Useful idea verified from README: the 2026 World Cup format introduces more randomness, so championship probabilities should be explained as a dispersed tournament distribution rather than as a direct extension of single-match strength.

## What Was Adopted

- Added a report-only explanation layer for 2026 format randomness.
- The section is derived from current Monte Carlo outputs:
  - highest champion probability
  - Top 3 champion-probability concentration
  - Top 10 champion-probability concentration
  - count of teams with champion probability at or above 5%
  - count of teams with champion probability at or above 1%
  - Herfindahl-derived effective champion contenders
- The explanation uses the local model's correct 2026 path: 48 teams, 12 groups, top two plus 8 best third-place teams into Round of 32, then 5 knockout rounds.

## What Was Not Adopted

- Did not replace the match model with Gradient Boosting.
- Did not add market odds.
- Did not add a visualization site.
- Did not change single-match scoreline probabilities or tournament sampling logic.

## Files Changed

- `worldcup_predictor/report.py`
- `tests/test_worldcup_predictor.py`
- `C:\Users\81901\.codex\skills\worldcup-predict\SKILL.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\README.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\model-overview.md`
- `C:\Users\81901\.codex\skills\worldcup-predict\references\commands-and-validation.md`

## Validation

- `python -m unittest discover -s tests -v`
  - Result: 20 tests passed.
- `python C:\Users\81901\.codex\skills\worldcup-predict\scripts\health_check.py --root .`
  - Result: status `ok`; no warnings.
- `python -m worldcup_predictor report --runs 20000 --sample-home France --sample-away Senegal --sample-match-id 97 --use-generated-context --include-uncertainty --uncertainty-samples 80`
  - Result: generated `outputs/reports/worldcup_prediction_report.md`.

## Report Check

Latest report includes:

- `## 2026 赛制随机性`
- `冠军概率集中度：最高冠军概率为 20.1%（Argentina），Top 3 合计 48.9%，Top 10 合计 88.1%。`
- `有效争冠球队数：按冠军概率 Herfindahl 指数折算约 9.0 支；冠军概率不低于 5% 的球队 6 支，不低于 1% 的球队 14 支。`

## Review

This improves user-facing understanding of tournament-level uncertainty, but it is intentionally not promoted as a predictive accuracy improvement until a time-safe backtest can show that a changed tournament model improves tournament outcome calibration.
