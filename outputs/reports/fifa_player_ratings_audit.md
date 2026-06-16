# FIFA/EA FC Player Ratings Audit

Generated: 2026-06-16T09:49:27.529700+00:00

## Verdict

`available_as_static_rating_prior_with_license_caveat`

The audit found a downloadable FC26/FIFA26-style player ratings table through a GitHub mirror of a Kaggle dataset. It can be used as an optional static rating prior for lineup rows, but it should not be treated as official FIFA federation data or as current match performance.

## Local Outputs

- Raw GitHub/Kaggle mirror CSV: `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\eafc26_players.csv`
- EA official ratings page snapshot: `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\ea_fc_ratings_page.html`
- Normalized model input: `E:\Vibe-coding\小红书\inputs\player_ratings\eafc26_player_ratings.csv`
- Source manifest: `E:\Vibe-coding\小红书\inputs\player_ratings\source_manifest.csv`

## Coverage

- Normalized rows: 18405
- Missing overall ratings: 0
- Nationalities: 160
- Clubs: 662
- Duplicate name+nationality keys: 16
- EA official page player-count claim: 17,000+
- EA official static top-list items detected: 30

## Source Findings

- EA official ratings page confirms FC 26 player ratings and PlayStyles for 17,000+ players, but the static HTML snapshot does not expose the complete table as a CSV.
- The downloaded complete CSV comes from a GitHub mirror whose README says the source is a Kaggle dataset. The GitHub mirror has no LICENSE file, so redistribution/licensing remains unverified.
- These ratings are game ratings, not official FIFA federation ratings and not live performance metrics.
- The rating table is useful for filling missing `LineupAgent` player ratings when a confirmed lineup contains player names.
- It should not automatically change team strength without a lineup and without backtest validation.

## Fetch Results

| Source | Status | Note |
|---|---:|---|
| ea_fc_official_ratings_page | ok | 1386775 bytes |
| eafc26_github_kaggle_mirror_csv | ok | 10978051 bytes |
| eafc26_github_readme | ok | 2388 bytes |

## Mirror README Evidence

The mirror README states that the data source is Kaggle `FC 26 (FIFA 26) Player Data` and that `data/players.csv` contains over 18,000 player records with 110+ attributes.
