# Player ratings inputs

Current source:

- `eafc26_player_ratings.csv`: normalized FC26/FIFA26-style player ratings generated from the downloaded GitHub/Kaggle mirror.
- `source_manifest.csv`: source and license caveats.

Important boundaries:

- These are EA SPORTS FC game ratings, not official FIFA federation performance ratings.
- The complete CSV source is a GitHub mirror whose README points to Kaggle. The mirror has no LICENSE file, so licensing is unverified.
- Ratings are static priors. They are not live form, not match-event performance, and not a substitute for club/national-team player-match data.

Model use:

- Ratings are only used as an optional `LineupAgent` fallback when a lineup row has a player name but no `rating`.
- Enable explicitly with `--player-ratings-file`.
- Ratings do not change predictions unless a lineup file is provided.

Example:

```powershell
python -m worldcup_predictor predict-match --home England --away Germany --match-id 999 --lineup-file inputs\lineups\example_with_missing_ratings.csv --lineup-allowed-source manual-template --player-ratings-file inputs\player_ratings\eafc26_player_ratings.csv
```
