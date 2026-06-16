# Non-Odds Context Integration Audit

Generated: 2026-06-16

## Verdict

`model_integration_complete_with_partial_generated_inputs`

The prediction model can now use all requested non-odds data categories through
CLI inputs or `--use-generated-context`. Local generated priors exist for
player performance, weather samples, travel/fatigue, tactics, and referee/event
environment, half-level event-count forecasts, and the official FIFA men's
ranking is connected to team strength.
Official match-specific lineups, injuries, substitutes, exact
kickoff weather, and assigned referee history still need to be replaced with
trusted pre-kickoff sources when available.

## Coverage

| Data category | Model path | Local data status | Prediction effect | Caveat |
|---|---|---|---|---|
| FIFA men's ranking | `StrengthAgent` reads `fifa_ranking_snapshot.csv` | Official API snapshot available | Small bounded attack-lambda correction alongside Elo | Can overlap with Elo, so weight is intentionally small |
| Half-level event counts | `EventAgent` reads `statsbomb_event_half_team_summary.csv` | 32 team-half sample rows | Predicts yellow cards, red cards, corners, free kicks, penalties by half | Sample is partial and should be replaced with a larger event feed |
| Official starters | `--lineup-file` / `LineupAgent` | Contract and example available | Changes team attack/defense lambdas | Real official team sheets must be filled before kickoff |
| Injuries/suspensions | `--lineup-file` status field | Contract available | Reduces expected available player strength | No automated free live injury feed is populated |
| Substitute strategy | `--lineup-file` expected minutes/sub minute | Contract available | Bench minutes affect team context | Requires user/provider expected-minutes input |
| Player ratings | `--player-ratings-file` | 18,405 EA FC 26 rows | Fills missing lineup player ratings | Game ratings; license caveat |
| Player performance | `--player-performance-file` | 248 StatsBomb sample rows | Changes player attack/defense multipliers | Partial national-team sample, not full club/national coverage |
| Weather | `--weather-file` | 35 sample-based match rows | Changes total-goal and set-piece multipliers | Not exact kickoff forecast yet |
| Travel/fatigue | `--travel-file` | 144 group team-match rows | Changes fatigue multiplier | Derived from venue sequence, not base camps |
| Tactics/formation | `--tactics-file` | 48 team style-prior rows | Changes team attack/defense multipliers | Heuristic from recent form/Elo, not confirmed plan |
| Referee/event environment | `--referee-file` | 1 global prior row | Changes discipline, set-piece, total-goal environment | Not assigned-referee specific |
| Real odds | intentionally excluded | none | none | Excluded by user request |

## Commands

Generate derived non-odds inputs:

```powershell
python -m worldcup_predictor build-context-data
```

Use generated context in a match:

```powershell
python -m worldcup_predictor predict-match --home Uruguay --away Spain --match-id 66 --use-generated-context
```

Use generated context in tournament simulation:

```powershell
python -m worldcup_predictor simulate-tournament --runs 20000 --use-generated-context
```

## Evidence

- `python -m unittest discover -s tests -v` passes 13 tests.
- `build-context-data` generated:
  - FIFA men's ranking snapshot from the official API.
  - StatsBomb half-team event sample used for event-count predictions.
  - 144 travel/fatigue rows.
  - 48 tactics rows.
  - 1 referee/event prior row.
  - 35 weather sample rows.
  - 248 player-performance rows.
- `predict-match --use-generated-context` writes `context_adjustment` with
  player, travel, tactic, weather, and referee evidence.

## Next Replacement Sources

- Official lineups/injuries/substitutes: official team sheets, FIFA match
  centre, federation posts, or TheStatsAPI confirmed lineups endpoint.
- Exact weather: Open-Meteo forecast pulled close to kickoff for each stadium.
- Assigned referee history: official referee assignment plus historical card,
  foul, red-card, and penalty rates.
- Full player performance: licensed provider or complete legal feed with club
  and national-team player-match rows and stable player IDs.
