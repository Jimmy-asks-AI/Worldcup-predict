# Non-odds match context inputs

These CSV files feed `MatchContextAgent`. They are optional, but when passed to
the CLI they change the Poisson goal lambdas used by match prediction and
tournament simulation.

## CLI

Generate the current non-odds context files:

```powershell
python -m worldcup_predictor build-context-data
```

Use all generated context files in one flag:

```powershell
python -m worldcup_predictor predict-match --home Uruguay --away Spain --match-id 66 --use-generated-context
```

Or pass files explicitly:

```powershell
python -m worldcup_predictor predict-match --home France --away Senegal --match-id 1 `
  --weather-file inputs\match_context\weather_forecast.csv `
  --travel-file inputs\match_context\team_travel_fatigue.csv `
  --tactics-file inputs\match_context\tactics.csv `
  --referee-file inputs\match_context\referees.csv `
  --player-performance-file inputs\player_performance\player_match_performance.csv
```

Use `source_manifest.csv` for source, acquisition, access, and model-argument
tracking. Real odds are intentionally excluded from this contract.

## Files

- `worldcup_data_audit/data/processed/fifa_ranking_snapshot.csv`: official FIFA
  men's ranking snapshot. `StrengthAgent` reads it automatically and applies a
  small bounded correction alongside Elo.
- `worldcup_data_audit/data/processed/statsbomb_event_half_team_summary.csv`:
  half-level event sample. `EventAgent` reads it automatically to forecast
  yellow cards, red cards, corners, free kicks, and penalties for the first and
  second half.
- `weather_forecast.csv`: match weather at or near kickoff. The generated rows
  currently reuse available stadium samples and are marked
  `stadium_sample_not_exact_kickoff_forecast`; refresh exact Open-Meteo
  forecasts close to kickoff.
- `team_travel_fatigue.csv`: travel distance, rest days, timezone shift, and
  training disruption. These reduce a team's attack and defensive resistance.
  Generate the current group-stage version with
  `python worldcup_data_audit\scripts\build_non_odds_context_inputs.py`.
- `tactics.csv`: pre-match formation and 0-100 tactical scores. The generated
  rows are 48 team style priors derived from recent form and Elo. A score of 50
  is neutral. Higher pressing, set-piece strength, counter threat, and width can
  raise attack; high defensive line can lower defensive resistance.
- `referees.csv`: assigned referee and historical cards, fouls, and penalties
  per match. The generated row is a global World Cup event-environment prior
  from the StatsBomb sample; replace it with assigned-referee history when known.

## Guardrails

- Every row should include `source` and `source_timestamp`.
- Do not use post-match or live-updated fields for pre-match predictions.
- Match-specific rows should use `match_id`; global rows are allowed only for
  scenario analysis or broad priors.
- Empty files are neutral. Missing data does not silently fabricate an edge.
