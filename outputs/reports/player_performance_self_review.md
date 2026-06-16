# Player performance self-review

## Verdict

DO_NOT_IMPLEMENT_LIVE_MODEL_ADJUSTMENT

## Review Standard

The feature should only be connected to live predictions if current evidence shows that club and national-team player-performance features can reliably improve out-of-sample prediction quality versus the existing baseline.

Minimum acceptable evidence:

- Historical player-match rows are available before each predicted match.
- Player rows cover both club and national-team performance for the relevant teams.
- Player identities are stable across club, national team, and source provider.
- A time-safe backtest shows better log loss and no Brier/calibration regression.

## Current Evidence

- `inputs/player_performance/player_match_performance.csv` has 0 rows.
- `inputs/player_performance/player_identity_map.csv` has 0 rows.
- `inputs/player_performance/source_manifest.csv` has 3 source rows.
- `worldcup_data_audit/data/processed/player_performance_source_coverage.csv` has 80 StatsBomb competition-season rows and 3961 match metadata rows.
- Local event-level player sample has 248 player-match rows from 8 StatsBomb World Cup event files.
- The sample only covers FIFA World Cup events, 11 teams, and 182 player identities.
- The sample uses `rating_basis=historical_event_counts_snapshot`, not a true historical pre-kickoff snapshot.
- The sample `source_timestamp` is the current audit date, so it cannot prove what would have been available before historical kickoffs.

## Assessment

The current data is useful for parser development and feature-contract testing, but it is not sufficient to prove predictive improvement.

The largest blockers are:

- No complete historical pre-kickoff player-performance dataset.
- No validated provider with broad club and national-team player coverage for 2026 players.
- No stable identity map between club and national-team rows.
- No time-safe backtest comparing baseline versus candidate player-performance features.
- No learned and validated feature weights.

Connecting the current sample to `ScorelineAgent` would create a hand-tuned multiplier, not an evidence-backed model improvement. It would likely add noise and could introduce look-ahead bias.

## Decision

Do not implement player-performance adjustments into live prediction probabilities now.

Safe work that can continue:

- Improve parsers and validators.
- Build a `PlayerPerformanceAgent` in diagnostics-only mode after real input files exist.
- Extend backtest support to compare baseline versus player-feature candidates.
- Keep live predictions unchanged until the backtest gate passes.

## Implementation Gate

Enable live prediction adjustment only after all conditions are met:

- `player_match_performance.csv` contains historical, pre-kickoff-safe player-match rows for relevant club and national-team competitions.
- `player_identity_map.csv` resolves players across providers and teams.
- `source_manifest.csv` marks sources as legally usable and pre-kickoff safe.
- Candidate model improves log loss by at least 1 percent versus baseline.
- Candidate model does not worsen Brier score.
- Candidate model does not materially degrade high-confidence calibration buckets.
