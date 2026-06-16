# World Cup Prediction Data Audit

Generated: 2026-06-16T08:36:18.414940+00:00

## Fetch Results

| Source | Status | Local path | Note |
|---|---:|---|---|
| thestatsapi_fixtures | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\thestatsapi_fixtures.json` | 41729 bytes |
| worldcup26_games | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\worldcup26_games.json` | 47668 bytes |
| worldcup26_groups | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\worldcup26_groups.json` | 7007 bytes |
| worldcup26_teams | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\worldcup26_teams.json` | 8434 bytes |
| worldcup26_stadiums | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\worldcup26_stadiums.json` | 4834 bytes |
| international_results | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\international_results.csv` | 3724375 bytes |
| international_goalscorers | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\international_goalscorers.csv` | 3256517 bytes |
| international_shootouts | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\international_shootouts.csv` | 28809 bytes |
| statsbomb_competitions | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_competitions.json` | 34887 bytes |
| statsbomb_wc2022_matches | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_wc2022_matches.json` | 119132 bytes |
| fifa_ranking_men_page | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\fifa_ranking_men_page.html` | 216653 bytes |
| thestatsapi_lineups_page | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\thestatsapi_lineups_page.html` | 133711 bytes |
| thestatsapi_odds_page | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\thestatsapi_odds_page.html` | 116888 bytes |
| open_meteo_weather_sample | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\processed\weather_hourly_sample.csv` | 144 hourly rows |
| statsbomb_events_3857276 | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_events_3857276.json` | 2811450 bytes |
| statsbomb_events_3857271 | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_events_3857271.json` | 3063347 bytes |
| statsbomb_events_3857296 | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_events_3857296.json` | 3493039 bytes |
| statsbomb_events_3857274 | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_events_3857274.json` | 3054360 bytes |
| statsbomb_events_3857255 | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_events_3857255.json` | 3753326 bytes |
| statsbomb_events_3857272 | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_events_3857272.json` | 2962761 bytes |
| statsbomb_events_3857278 | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_events_3857278.json` | 3036508 bytes |
| statsbomb_events_3857277 | ok | `E:\Vibe-coding\小红书\worldcup_data_audit\data\raw\statsbomb_events_3857277.json` | 3090039 bytes |

## Processed Tables

| Table | Rows | Use |
|---|---:|---|
| `fixtures_2026.csv` | 104 | 2026 full schedule base table |
| `worldcup26_games.csv` | 104 | live or current match scores from non-official source |
| `worldcup26_group_table.csv` | 48 | current group standings from non-official source |
| `teams_2026.csv` | 48 | team names and FIFA codes |
| `stadiums_2026.csv` | 16 | venue metadata and manually mapped coordinates |
| `weather_hourly_sample.csv` | 144 | hourly weather feature sample from Open-Meteo |
| `international_results_worldcup_only.csv` | 1036 | World Cup historical scoreline training and backtesting |
| `derived_elo_snapshot.csv` | 336 | self-computed national-team Elo from international results |
| `derived_recent_form.csv` | 336 | recent form, goals for, goals against features |
| `international_goalscorers.csv` | 47098 | goal minute and penalty flags where available |
| `international_shootouts.csv` | 678 | penalty shootout winner modeling |
| `statsbomb_worldcup_seasons.csv` | 11 | which World Cup seasons are available in StatsBomb open data |
| `statsbomb_wc2022_matches.csv` | 64 | StatsBomb match IDs for event download |
| `statsbomb_event_match_summary.csv` | 8 | event-level match coverage sample |
| `statsbomb_event_half_team_summary.csv` | 32 | team-half event counts for goals, cards, corners, free kicks, penalties |

## Requirement Coverage

| Requirement | Current coverage | Result |
|---|---|---|
| 2026 schedule | 104 rows from TheStatsAPI fixtures plus team/stadium tables | sufficient for fixture base, cross-check recommended |
| historical matches | international results CSV and StatsBomb World Cup matches/events; current scores must use actual_* fields only | sufficient for scoreline, 1X2, Elo, and event model training |
| FIFA ranking | official FIFA ranking page saved as HTML, not parsed into stable table yet | partially sufficient; needs parser/cache or manual export |
| Elo | derived Elo snapshot computed locally from international results | sufficient for a reproducible baseline |
| lineups | TheStatsAPI lineup page saved; JSON API requires key; confirmed lineups appear about 75 minutes pre-kickoff | not sufficient without API key for automated live system |
| odds | TheStatsAPI odds page saved; API requires key; page claims 1X2, totals, BTTS, corners | not sufficient without API key for automated model input |
| weather | Open-Meteo hourly sample downloaded for mapped stadiums | sufficient for rolling forecast features; far-future exact forecast still time-limited |
| exact score and 1X2 prediction | historical scorelines, derived Elo, recent form, StatsBomb event samples | sufficient for baseline Poisson/ML models |
| group ranking and champion simulation | fixture base plus scoreline simulation inputs available | sufficient after implementing 2026 tournament rules |
| goals, goal difference, cards, free kicks, corners, penalties by half | StatsBomb event half-team sample contains goals, shots, fouls, cards, corners, free-kick passes, penalties | sufficient for historical event model training; 2026 live requires event feed/API |

## Key Findings

- Free sources can support a working baseline for schedule, historical results, Elo, recent form, weather, scoreline simulation, group ranking, and champion odds.
- The largest blocking gap for the requested rich prediction set is live 2026 event data: confirmed lineups, odds, corners, free kicks, cards, and penalties need an API key or commercial feed.
- StatsBomb open data is strong enough to train half-level event-count models, but it is historical open data, not a 2026 live feed.
- worldcup26.ir fills raw score fields with 0-0 for unplayed fixtures; processed files expose actual_home_score and actual_away_score only for finished matches.
- FIFA ranking can be validated against the official page snapshot, but it still needs a robust parser or a maintained export before it becomes a clean model input.
- Self-computed Elo is the most reproducible team-strength input because it does not rely on fragile web-table scraping.
