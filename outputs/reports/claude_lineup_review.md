# Claude review of lineup-based prediction changes

## Review conclusion

Claude's review concluded that lineup, injury, player-rating, and substitution inputs are directionally useful, but the first implementation was not enough to prove better out-of-sample accuracy. The architecture was acceptable because `StrengthAgent` produces baseline lambdas and `LineupAgent` applies match-specific multipliers before the Poisson scoreline model. The weak points were calibration, leakage risk, arbitrary scaling constants, and the lack of a backtest harness.

## Main risks identified

- A lineup multiplier on top of an uncalibrated baseline can add noise instead of improving forecasts.
- Player ratings are leakage-prone if they come from post-match or live-match sources.
- The previous unavailable-player logic could treat an injured substitute as a full 90-minute starter loss.
- The previous Elo effect used a linear ad hoc transform.
- Existing tests checked structure, not predictive quality, calibration, or leakage.

## Actions implemented

- Added `worldcup_predictor/backtest.py` with rolling historical Elo and scoring history, plus Brier score, log loss, ranked probability score, and confidence calibration buckets.
- Added `python -m worldcup_predictor backtest`.
- Added lineup leakage guardrails: non-empty source, pre-kickoff `rating_basis`, rejection of post-match/live rating markers, optional source whitelist, and default official-starter requirement.
- Fixed unavailable substitute minutes so an injured substitute defaults to 25 lost minutes, not 90.
- Replaced the linear Elo lambda multiplier with a centered logistic multiplier.
- Replaced the linear penalty shootout prior with a shrunk logistic Elo prior.
- Added tests for backtest metrics, post-match rating rejection, unavailable substitute minutes, and lineup multiplier evidence.

## Remaining work

- Backtest lineup multipliers against historical pre-kickoff lineups once such data is available.
- Fit position weights and lineup scaling constants from data instead of hand-setting them.
- Add a learned ensemble that can down-weight lineup adjustments if backtests show weak signal.
- Consider betting-market priors and Dixon-Coles or bivariate Poisson modeling after the measurement loop is stable.
