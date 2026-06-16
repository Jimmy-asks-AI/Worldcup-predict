# Non-Odds Data Sources And Acquisition

This report records the non-odds data that the predictor can use after the
latest model integration. Real market odds are intentionally excluded.

Generate current derived inputs:

```powershell
python -m worldcup_predictor build-context-data
```

Use all generated non-odds context in predictions:

```powershell
python -m worldcup_predictor predict-match --home Uruguay --away Spain --match-id 66 --use-generated-context
```

| Data | Local contract | How to acquire | Model argument | Current usability |
|---|---|---|---|---|
| FIFA men's world ranking | `worldcup_data_audit/data/processed/fifa_ranking_snapshot.csv` | Run `python worldcup_data_audit/scripts/build_non_odds_context_inputs.py`; it fetches the public FIFA API and caches raw JSON | automatic `StrengthAgent` input | Connected; official API returned full ranking table |
| Half-level event counts | `worldcup_data_audit/data/processed/statsbomb_event_half_team_summary.csv` | Run `python worldcup_data_audit/scripts/pull_and_audit_worldcup_data.py` to rebuild from StatsBomb event JSON | automatic `EventAgent` input | Connected; predicts yellow cards, red cards, corners, free kicks, penalties by half |
| Official lineups, injuries, substitutes | `inputs/lineups/template.csv` | Fill from official team sheets or an API such as TheStatsAPI confirmed lineups before kickoff | `--lineup-file` | Connected; needs trusted match rows |
| Player ability ratings | `inputs/player_ratings/eafc26_player_ratings.csv` | Generated from downloaded EA FC 26 GitHub/Kaggle mirror; EA official page saved for public-page evidence | `--player-ratings-file` | Connected as optional lineup rating fallback; license unverified |
| Player club and national-team performance | `inputs/player_performance/player_match_performance.csv` | Run `python worldcup_data_audit/scripts/build_non_odds_context_inputs.py` to copy the StatsBomb player-match sample into the model contract; replace with full club/national feed when available | `--player-performance-file` | Connected; 248 partial sample rows generated |
| Weather | `inputs/match_context/weather_forecast.csv` | Run `python worldcup_data_audit/scripts/build_non_odds_context_inputs.py` to align available Open-Meteo stadium samples by `match_id`; refresh exact forecasts near kickoff | `--weather-file` | Connected; 35 sample-based match rows generated |
| Travel and fatigue | `inputs/match_context/team_travel_fatigue.csv` | Run `python worldcup_data_audit/scripts/build_non_odds_context_inputs.py`; derives group-stage rows from fixture order and stadium coordinates | `--travel-file` | Connected; 144 group team-match rows generated |
| Coach tactics and formation | `inputs/match_context/tactics.csv` | Run `python worldcup_data_audit/scripts/build_non_odds_context_inputs.py` to generate 48 team style priors from recent form and Elo; replace with scouting/provider rows | `--tactics-file` | Connected; 48 team priors generated |
| Referee tendencies | `inputs/match_context/referees.csv` | Run `python worldcup_data_audit/scripts/build_non_odds_context_inputs.py` to generate a global World Cup event prior from StatsBomb sample; replace with assigned referee history | `--referee-file` | Connected; global prior generated |

## Acquisition Notes

- Use exact `match_id` whenever possible. The model supports global rows, but
  match-specific rows are safer and more explainable.
- Keep pre-kickoff timestamps. A row created after kickoff can leak match
  information into the prediction.
- For club performance rows, populate `national_team` so the model can attach
  the player's club form to the World Cup team.
- FIFA ranking is intentionally a light correction on top of Elo, not a
  replacement for Elo or player-level inputs.
- Event-count predictions are sample-based priors. They provide usable
  half-level forecasts now, but should be replaced with a larger event feed for
  production-grade card/corner/free-kick/penalty calibration.
- Empty contracts are neutral; the generated files are not empty and will change
  probabilities when passed through the CLI.
- Travel/fatigue currently uses fixture-to-fixture venue movement, not team base
  camps. First group matches are neutral, and knockout travel must be generated
  after simulated teams are known.
- Tactics, referee, weather, and player-performance rows are usable priors, not
  final live feeds. Replace them with official or licensed pre-kickoff rows when
  those become available.
