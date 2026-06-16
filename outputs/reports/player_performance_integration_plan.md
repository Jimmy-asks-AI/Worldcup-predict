# Player club and national-team performance integration plan

## Decision Gate

Do not implement this feature into live predictions unless a reviewer agrees that the plan has a credible path to improving out-of-sample predictive accuracy and that the implementation gate requires measured improvement on a time-safe backtest.

The intended decision rule is:

- Build ingestion and offline backtest support first.
- Keep live predictions on the current team-level + lineup model until historical player-performance features reduce out-of-sample log loss and/or Brier score versus the baseline.
- Reject or quarantine any row that is not known to be available before kickoff.

## Why Player Performance Could Help

Team-level Elo and recent form compress all squad information into a few team features. Player match performance can add signal when:

- A national team has improved or declined because key players' club form changed faster than the team Elo captures.
- A lineup includes high-usage attackers, creators, ball winners, or goalkeepers whose recent club/national performance differs from their long-run reputation.
- A team is missing players whose workload, minutes, or output are hard to see from team-level results alone.
- Club-level minutes and performance reveal match fitness before national-team samples are large enough.

The feature is only useful if it is measured from pre-match snapshots. Post-match player ratings or post-match event aggregates would leak the result.

## Data Contract

Create a new input directory:

- `inputs/player_performance/player_match_performance.csv`
- `inputs/player_performance/player_identity_map.csv`
- `inputs/player_performance/source_manifest.csv`

`player_match_performance.csv` required columns:

- `snapshot_date`: date when this row became available to the model.
- `match_date`: date of the club or national-team match being summarized.
- `source`: provider name or URL.
- `source_timestamp`: timestamp when the source data was pulled or published.
- `player_id`: stable internal player id.
- `player_name`
- `team`: club or national team represented in that match.
- `team_type`: `club` or `national`.
- `competition`
- `opponent`
- `home_away_neutral`
- `position`
- `minutes`
- `started`
- `goals`
- `assists`
- `xg`
- `xa`
- `shots`
- `shots_on_target`
- `key_passes`
- `progressive_passes`
- `progressive_carries`
- `touches_box`
- `pressures`
- `tackles`
- `interceptions`
- `blocks`
- `clearances`
- `aerial_duels_won`
- `duels_won`
- `yellow_cards`
- `red_cards`
- `keeper_saves`
- `keeper_goals_prevented`
- `match_rating`
- `rating_basis`: must be `prematch_safe_historical` for rows used by prediction.

`player_identity_map.csv` required columns:

- `player_id`
- `player_name`
- `birth_date`
- `national_team`
- `club_team`
- `provider_player_id`
- `provider`
- `valid_from`
- `valid_to`

`source_manifest.csv` required columns:

- `source`
- `license`
- `coverage_start`
- `coverage_end`
- `competitions`
- `player_metrics_available`
- `pre_kickoff_safe`
- `notes`

## Leakage Guardrails

`PlayerPerformanceAgent` must reject or quarantine rows when:

- `snapshot_date` is after the predicted match kickoff.
- `source_timestamp` is after the predicted match kickoff.
- `rating_basis` is missing or not equal to `prematch_safe_historical`.
- `source` is not listed in `source_manifest.csv`.
- `source_manifest.pre_kickoff_safe` is not true.
- The row appears to represent the same match being predicted.
- A player identity mapping is ambiguous.

The model should report `used_rows`, `quarantined_rows`, and quarantine reasons.

## Feature Engineering

Create a `PlayerPerformanceAgent` that converts player match rows into team-match features:

1. Filter to rows available before kickoff.
2. Split club and national-team history.
3. Apply recency weights:
   - Last 30 days
   - Last 90 days
   - Last 365 days
4. Apply minutes weighting and shrink low-minute players toward positional averages.
5. Normalize metrics by position and competition strength.
6. Build lineup-weighted features when a lineup file is present:
   - expected attacking contribution
   - expected chance creation
   - expected ball progression
   - expected defensive disruption
   - expected goalkeeper contribution
   - expected discipline risk
   - expected fatigue / workload risk
7. Build squad-level fallback features when no lineup is present:
   - top 14 likely player weighted average
   - player availability-adjusted squad depth
   - recent club minutes concentration

Competition strength adjustment:

- Use team Elo or club Elo when available.
- If club competition strength is missing, shrink club performance more heavily toward the player's national-team or positional average.
- Do not treat lower-league club production as equivalent to elite competition production.

## Model Integration

Do not directly multiply lambdas with raw player ratings.

Instead, use a two-stage approach:

1. Offline training/backtest:
   - Baseline model: current team-level `StrengthAgent` + optional `LineupAgent`.
   - Candidate model: baseline features + `PlayerPerformanceAgent` features.
   - Time-based split only.
   - Compare log loss, Brier score, RPS, and calibration.
2. Live prediction:
   - Only enable player-performance adjustment if the candidate model beats baseline on held-out matches.
   - Store the learned feature weights and shrinkage parameters in a config file.
   - If no trained weights exist, output player-performance diagnostics but do not alter lambdas.

Recommended first model:

- Multinomial logistic calibration layer for win/draw/loss probabilities.
- Inputs:
  - baseline logit probabilities
  - Elo difference
  - baseline lambda difference
  - lineup attack/defense multipliers
  - player attacking contribution difference
  - player chance creation difference
  - player defensive contribution difference
  - goalkeeper contribution difference
  - fatigue/workload difference
  - discipline risk difference
- Output:
  - calibrated home/draw/away probabilities.

Scoreline model:

- Keep the Poisson scoreline matrix as the score distribution.
- If the calibrated WDL layer materially changes probabilities, adjust `lambda_home` and `lambda_away` with a bounded calibration step and re-normalize.
- Do not make raw player features directly override exact score probabilities.

## Backtest Extension

Extend `worldcup_predictor/backtest.py`:

- Add `--player-performance-file`.
- Add `--player-map-file`.
- Add `--source-manifest`.
- Add `--compare-player-features`.
- Report baseline and candidate metrics:
  - `baseline_log_loss`
  - `candidate_log_loss`
  - `delta_log_loss`
  - `baseline_brier`
  - `candidate_brier`
  - `delta_brier`
  - `baseline_rps`
  - `candidate_rps`
  - calibration tables for both models.
- Refuse to enable live player-performance adjustment unless:
  - candidate log loss improves by at least 1 percent, and
  - candidate Brier score does not get worse, and
  - calibration does not materially deteriorate in high-confidence buckets.

## CLI Plan

Add later only if the backtest gate passes:

```powershell
python -m worldcup_predictor backtest --player-performance-file inputs\player_performance\player_match_performance.csv --player-map-file inputs\player_performance\player_identity_map.csv --source-manifest inputs\player_performance\source_manifest.csv --compare-player-features

python -m worldcup_predictor predict-match --home Spain --away "Cape Verde" --match-id 1 --lineup-file inputs\lineups\spain_cape_verde.csv --player-performance-file inputs\player_performance\player_match_performance.csv
```

## Tests

Add tests before live use:

- Reject rows with `snapshot_date` after kickoff.
- Reject rows with post-match rating basis.
- Reject rows from non-whitelisted sources.
- Quarantine ambiguous player identity mappings.
- Verify low-minute players shrink toward positional averages.
- Verify club and national-team features are separate.
- Verify candidate model is not enabled when backtest does not beat baseline.
- Verify live predictions remain unchanged when no trained player-performance weights exist.

## Implementation Phases

Phase 1: Data and validation only.

- Add input templates and validators.
- Add `PlayerPerformanceAgent` feature generation.
- Do not modify predictions.

Phase 2: Backtest comparison.

- Extend the backtest to compare baseline vs candidate.
- Save metrics and learned weights only if candidate beats baseline.

Phase 3: Controlled live integration.

- Load learned weights.
- Apply bounded calibrated adjustment.
- Emit evidence and warnings.

Phase 4: Improve data quality.

- Add provider-specific importers only for sources that provide legally usable, pre-kickoff-safe historical player data.
- Add richer competition-strength adjustment.
- Add goalkeeper and discipline submodels if backtests show signal.

## Expected Outcome

This plan does not claim guaranteed improvement from simply adding more player features. It claims improvement is plausible only if the player-performance features pass a time-safe backtest. If they do not pass, the system should surface player diagnostics but leave prediction probabilities unchanged.
