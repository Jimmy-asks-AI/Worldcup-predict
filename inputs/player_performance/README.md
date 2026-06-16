# Player performance inputs

This directory is the data contract for player-performance modeling. It is now
connected to prediction through `MatchContextAgent`, but it is neutral unless a
non-empty CSV is passed with `--player-performance-file`.

Current files:

- `player_match_performance.csv`: empty contract file for historical pre-kickoff-safe player match rows.
- `player_identity_map.csv`: empty contract file for stable player identity mapping across providers, clubs, and national teams.
- `source_manifest.csv`: audited source inventory.

Generated audit artifacts:

- `worldcup_data_audit/data/processed/player_performance_source_coverage.csv`
- `worldcup_data_audit/data/processed/statsbomb_player_match_performance_sample.csv`
- `worldcup_data_audit/data/processed/statsbomb_player_identity_sample.csv`
- `outputs/reports/player_performance_data_audit.md`

The StatsBomb sample is useful for parser development only. It is not sufficient
as a full live model feed because the current local data does not cover all club
and national-team matches for 2026 players and does not provide historical
pre-kickoff snapshots for backtesting.

## Model use

Enable explicitly:

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --match-id 1 --player-performance-file inputs\player_performance\player_match_performance.csv
```

Rows are grouped by `national_team` first, then by `team`. This allows club
performance rows to affect a national-team prediction when the row includes a
stable national-team mapping.

The model converts prior player-match rows into attack and defensive-resistance
multipliers using minutes-weighted goals, assists, xG, xA, shots on target, key
passes, box touches, tackles, interceptions, blocks, clearances, aerial wins,
duels, saves, cards, and optional match ratings.

Current caveat: the local contract has been populated with the available
StatsBomb open-data sample by
`python worldcup_data_audit\scripts\build_non_odds_context_inputs.py`. It is a
working model input, but it is not full club and national-team coverage. A
full-coverage feed should be followed by a time-safe backtest before using the
feature as a default.
