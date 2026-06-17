# Player Performance Data Audit

Generated: 2026-06-17T03:10:45.597442+00:00

## Verdict

`not_sufficient_for_model_gate`

The next step was data acquisition and validation, not model integration. The audit found usable public event data, but not the complete, historical, pre-kickoff-safe club and national-team player-performance dataset needed to prove out-of-sample improvement.

## Local Outputs

- Source manifest: `E:\Vibe-coding\小红书\inputs\player_performance\source_manifest.csv`
- Empty contract file: `E:\Vibe-coding\小红书\inputs\player_performance\player_match_performance.csv`
- Empty identity contract: `E:\Vibe-coding\小红书\inputs\player_performance\player_identity_map.csv`
- StatsBomb sample performance rows: `E:\Vibe-coding\小红书\worldcup_data_audit\data\processed\statsbomb_player_match_performance_sample.csv`
- StatsBomb sample identities: `E:\Vibe-coding\小红书\worldcup_data_audit\data\processed\statsbomb_player_identity_sample.csv`
- StatsBomb coverage table: `E:\Vibe-coding\小红书\worldcup_data_audit\data\processed\player_performance_source_coverage.csv`

## Coverage Summary

- StatsBomb open-data match metadata rows discovered: 3961
- Male non-youth competition-season rows discovered: 66
- Local StatsBomb event files currently available: 16
- Player-match sample rows generated from local event files: 494
- Unique player identities in sample: 323
- Teams represented in local sample: 18

## Source Findings

- StatsBomb Open Data is legal for public research with attribution, and it provides JSON competitions, matches, events, and lineups. It is the only source that could be processed locally without credentials.
- The local StatsBomb sample is useful for parser development, but it is not enough to validate a player-performance model across all 2026 World Cup players.
- TheStatsAPI advertises confirmed lineups, substitutions, live player stats, and xG, but the JSON endpoint requires an API key, so it is not available as a local model input yet.
- The international goalscorers file is player-level but only covers goals, minutes, own-goal flags, and penalties. It is not enough to represent full player form.

## Gate Result

Do not enable player-performance adjustments in live predictions yet.

Required before implementation:

- A legally usable player-performance feed with historical club and national-team coverage.
- Pre-kickoff-safe source timestamps for each player-match row.
- Stable player identity mapping across club and national-team data.
- A time-safe backtest showing lower log loss and no Brier/calibration regression versus the current baseline.

## Fetch Results

| Source | Status | Note |
|---|---:|---|
| statsbomb_competitions | ok | 80 competition seasons |
| statsbomb_matches_9_281 | ok | 34 matches |
| statsbomb_matches_9_27 | ok | 34 matches |
| statsbomb_matches_1267_107 | ok | 52 matches |
| statsbomb_matches_16_4 | ok | 1 matches |
| statsbomb_matches_16_1 | ok | 1 matches |
| statsbomb_matches_16_2 | ok | 1 matches |
| statsbomb_matches_16_27 | ok | 1 matches |
| statsbomb_matches_16_26 | ok | 1 matches |
| statsbomb_matches_16_25 | ok | 1 matches |
| statsbomb_matches_16_24 | ok | 1 matches |
| statsbomb_matches_16_23 | ok | 1 matches |
| statsbomb_matches_16_22 | ok | 1 matches |
| statsbomb_matches_16_21 | ok | 1 matches |
| statsbomb_matches_16_41 | ok | 1 matches |
| statsbomb_matches_16_39 | ok | 1 matches |
| statsbomb_matches_16_37 | ok | 1 matches |
| statsbomb_matches_16_44 | ok | 1 matches |
| statsbomb_matches_16_76 | ok | 1 matches |
| statsbomb_matches_16_277 | ok | 1 matches |
| statsbomb_matches_16_71 | ok | 1 matches |
| statsbomb_matches_16_276 | ok | 1 matches |
| statsbomb_matches_223_282 | ok | 32 matches |
| statsbomb_matches_87_84 | ok | 1 matches |
| statsbomb_matches_87_268 | ok | 1 matches |
| statsbomb_matches_87_279 | ok | 1 matches |
| statsbomb_matches_37_281 | ok | 132 matches |
| statsbomb_matches_37_90 | ok | 131 matches |
| statsbomb_matches_37_42 | ok | 87 matches |
| statsbomb_matches_37_4 | ok | 107 matches |
| statsbomb_matches_1470_274 | ok | 1 matches |
| statsbomb_matches_43_106 | ok | 64 matches |
| statsbomb_matches_43_3 | ok | 64 matches |
| statsbomb_matches_43_55 | ok | 1 matches |
| statsbomb_matches_43_54 | ok | 3 matches |
| statsbomb_matches_43_51 | ok | 6 matches |
| statsbomb_matches_43_272 | ok | 6 matches |
| statsbomb_matches_43_270 | ok | 1 matches |
| statsbomb_matches_43_269 | ok | 2 matches |
| statsbomb_matches_135_281 | ok | 132 matches |
| statsbomb_matches_1238_108 | ok | 115 matches |
| statsbomb_matches_11_90 | ok | 35 matches |
| statsbomb_matches_11_42 | ok | 33 matches |
| statsbomb_matches_11_4 | ok | 34 matches |
| statsbomb_matches_11_1 | ok | 36 matches |
| statsbomb_matches_11_2 | ok | 34 matches |
| statsbomb_matches_11_27 | ok | 380 matches |
| statsbomb_matches_11_26 | ok | 38 matches |
| statsbomb_matches_11_25 | ok | 31 matches |
| statsbomb_matches_11_24 | ok | 32 matches |
| statsbomb_matches_11_23 | ok | 37 matches |
| statsbomb_matches_11_22 | ok | 33 matches |
| statsbomb_matches_11_21 | ok | 35 matches |
| statsbomb_matches_11_41 | ok | 31 matches |
| statsbomb_matches_11_40 | ok | 27 matches |
| statsbomb_matches_11_39 | ok | 26 matches |
| statsbomb_matches_11_38 | ok | 17 matches |
| statsbomb_matches_11_37 | ok | 7 matches |
| statsbomb_matches_11_278 | ok | 1 matches |
| statsbomb_matches_182_281 | ok | 240 matches |
| statsbomb_matches_81_48 | ok | 1 matches |
| statsbomb_matches_81_275 | ok | 1 matches |
| statsbomb_matches_7_235 | ok | 32 matches |
| statsbomb_matches_7_108 | ok | 26 matches |
| statsbomb_matches_7_27 | ok | 377 matches |
| statsbomb_matches_44_107 | ok | 6 matches |
| statsbomb_matches_116_68 | ok | 1 matches |
| statsbomb_matches_49_107 | ok | 137 matches |
| statsbomb_matches_49_3 | ok | 36 matches |
| statsbomb_matches_2_27 | ok | 380 matches |
| statsbomb_matches_2_44 | ok | 38 matches |
| statsbomb_matches_12_27 | ok | 380 matches |
| statsbomb_matches_12_86 | ok | 1 matches |
| statsbomb_matches_131_281 | ok | 130 matches |
| statsbomb_matches_55_282 | ok | 51 matches |
| statsbomb_matches_55_43 | ok | 51 matches |
| statsbomb_matches_35_75 | ok | 3 matches |
| statsbomb_matches_53_315 | ok | 31 matches |
| statsbomb_matches_53_106 | ok | 31 matches |
| statsbomb_matches_72_107 | ok | 64 matches |
| statsbomb_matches_72_30 | ok | 52 matches |
