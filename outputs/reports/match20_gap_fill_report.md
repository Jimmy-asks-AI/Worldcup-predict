# Austria vs Jordan Gap Fill Report

Generated: 2026-06-17T03:17:28+00:00

## What Was Filled

- Official FIFA live lineup CSV: `E:\Vibe-coding\小红书\inputs\lineups\match20_austria_jordan_fifa_official.csv`
- FIFA 26-player squad extract: `E:\Vibe-coding\小红书\worldcup_data_audit\data\processed\fifa_match20_squad.csv`
- FIFA player profile/stat extract: `E:\Vibe-coding\小红书\inputs\player_performance\fifa_match20_player_profiles.csv`
- FIFA player identity map: `E:\Vibe-coding\小红书\inputs\player_performance\fifa_match20_player_identity_map.csv`
- Official lineup to local player-performance join: `E:\Vibe-coding\小红书\worldcup_data_audit\data\processed\fifa_match20_lineup_player_performance_join.csv`
- Exact kickoff-hour weather row updated: `E:\Vibe-coding\小红书\inputs\match_context\weather_forecast.csv`

## Coverage

- FIFA lineup rows: 52 (22 starters, 30 substitutes).
- FIFA player profile rows: 52.
- FIFA player detail fetches: {'detail_ok': 52, 'detail_null': 0, 'statistics_ok': 52, 'statistics_null': 0}.
- FIFA timeline events currently available: 0.
- Local StatsBomb lineup-player matches: 14 of 52.
- Local StatsBomb player matches by team: {'Austria': 14, 'Jordan': 0}.
- Team-half event sample rows: 64; target-team rows: {'Austria': 16, 'Jordan': 0}.
- Exact weather updated: True; row: `{'match_id': '20', 'stadium': "Levi's Stadium", 'time_utc': '2026-06-17T04:00:00Z', 'source': 'open_meteo_hourly_forecast', 'source_timestamp': '2026-06-17T03:17:28+00:00', 'temperature_c': 15.8, 'humidity_pct': 86, 'precipitation_mm': 0.0, 'wind_kph': 12.0, 'weather_basis': 'exact_kickoff_hour_forecast', 'notes': 'https://api.open-meteo.com/v1/forecast?latitude=37.403&longitude=-121.97&hourly=temperature_2m%2Crelative_humidity_2m%2Cprecipitation%2Cwind_speed_10m&start_date=2026-06-17&end_date=2026-06-17&timezone=UTC'}`

## Remaining Gaps

- Injury/suspension rows are not separately exposed by this FIFA live endpoint. They should be added only from a trusted pre-kickoff injury or squad-availability source.
- Substitution strategy is not official before kickoff. The CSV marks official bench players and default expected minutes, but it does not know the coach's planned substitutions.
- FIFA player profiles provide national/FIFA profile statistics, not full club plus national player-match performance.
- StatsBomb open data now covers Austria event samples from public Euro matches, but Jordan still has no local team-event sample.
- `playerstatistics/match/...` is null before the match has live stats; it must not be used for a pre-match prediction.
