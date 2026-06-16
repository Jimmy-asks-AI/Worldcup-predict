# World Cup lineup input

Use `template.csv` as the input contract for `LineupAgent`.

Required columns:

- `match_id`: optional. Use the fixture match id when the lineup is match-specific.
- `team`: team name. Existing team aliases are normalized by the predictor.
- `player`: player name.
- `role`: `starter`, `substitute`, `reserve`, or `unavailable`.
- `position`: one of `GK`, `CB`, `LB`, `RB`, `DF`, `DM`, `CM`, `AM`, `LW`, `RW`, `FW`, `ST`.
- `rating`: 0-100 player rating. Missing values fall back to 75 with a warning.
- `rating_basis`: required in pre-kickoff mode. Use `prematch`, `pre_kickoff`, `season_average`, `projected`, `scouted_prematch`, or `market_pre`. Do not use post-match player ratings.
- `status`: `available`, `limited`, `doubtful`, `injured`, `suspended`, `out`, or `unavailable`.
- `expected_minutes`: expected minutes played. For unavailable players this is treated as lost expected minutes.
- `sub_minute`: planned substitution minute. If `expected_minutes` is empty, substitute minutes become `90 - sub_minute`.
- `official`: `true` when a starter is confirmed by an official lineup source.
- `source`: source name or URL.
- `notes`: free text.
- `nationality`: optional. Used to match player ratings when `--player-ratings-file` is passed. Defaults to `team`.
- `club`: optional. Used to disambiguate player ratings when `--player-ratings-file` is passed.

Example:

```powershell
python -m worldcup_predictor predict-match --home Spain --away "Cape Verde" --match-id 1 --lineup-file inputs\lineups\template.csv --lineup-allowed-source manual-template
```

The model is neutral when no lineup file is passed. When a lineup file is passed, starters, unavailable players, ratings, and planned substitutes change the two Poisson goal lambdas before scoreline probabilities are calculated.

Optional player-rating fallback:

- Pass `--player-ratings-file inputs\player_ratings\eafc26_player_ratings.csv`.
- If a lineup row has no `rating`, the model tries to fill it from the rating table by player name and nationality.
- If matching is ambiguous or missing, the row falls back to 75 and emits a warning.

Leakage guardrails:

- Each row must have a non-empty `source`.
- In default pre-kickoff mode, each row must have a pre-match `rating_basis`.
- Starter rows must be marked `official=true`. Use `--allow-projected-lineups` only for explicit scenario analysis.
- Use `--lineup-allowed-source` to whitelist accepted sources.
