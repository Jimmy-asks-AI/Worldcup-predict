# Claude review: player performance integration plan

## Verdict

DO_NOT_IMPLEMENT

## Reason

Claude reviewed `outputs/reports/player_performance_integration_plan.md` against the current local codebase and concluded that the plan is architecturally sound, but should not be implemented now under the user's condition.

The blocking reasons:

- The repository does not contain the required historical pre-kickoff player-performance dataset.
- The planned `inputs/player_performance/player_match_performance.csv` does not exist.
- Existing player-level data is limited and not enough to validate club-and-national-team rolling player features.
- No confirmed data provider exists locally for the required fields such as minutes, xG, xA, pressures, progressive actions, goalkeeper metrics, and pre-kickoff-safe ratings.
- Because the data is missing, the time-safe backtest gate cannot be run, so out-of-sample improvement cannot be proven.

## Required evidence before implementation

- A legal and usable player-performance data provider or local dataset.
- Historical club and national-team player-match rows with pre-kickoff-safe timestamps.
- Stable player identity mapping across clubs, national teams, and providers.
- A time-safe backtest showing the player-performance candidate model improves log loss by at least 1 percent versus baseline, does not worsen Brier score, and does not materially harm calibration.

## Action taken

No live model code was implemented for player-performance features. The plan remains saved for later use once the required data evidence exists.
