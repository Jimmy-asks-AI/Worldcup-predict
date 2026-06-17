---
name: worldcup-predict
description: Local Codex skill for operating the `worldcup_predictor` World Cup multi-agent prediction system. Use when the user asks to run, explain, audit, extend, refresh, validate, or report on match score prediction, win/draw/loss probabilities, comprehensive factor explanations, group and tournament simulation, data-source checks, lineup/player/context integration, event-count forecasts, backtests, or Chinese prediction reports.
---

# Worldcup Predict

## Core Rule

Use the local Python package `worldcup_predictor` as the source of truth. Do not invent predictions from chat context when the package can be run. Prefer current local files and CLI outputs, then explain the result in Chinese with clear caveats.

Default repo root is the current workspace. If `worldcup_predictor/` is not present, locate it with `rg --files -g "worldcup_predictor"` or ask for the repo path only after a reasonable search fails.

## Standard Workflow

1. Inspect local state before answering:
   - Check `worldcup_predictor/`, `worldcup_data_audit/data/processed/`, `inputs/`, and `outputs/`.
   - For source audits, read `outputs/reports/worldcup_data_source_catalog.md` when present, then `references/data-contracts.md`.
   - Run this skill's `scripts/health_check.py --root <repo>` when a quick data health check is useful.
2. Refresh or rebuild data only when the user asks for current/latest data or the local data is missing:
   - `python -m worldcup_predictor refresh-data`
   - `python -m worldcup_predictor build-context-data`
   - For the Austria-Jordan match-20 gap fill: `python worldcup_data_audit\scripts\build_match20_gap_inputs.py`.
3. For one match, run the CLI instead of estimating manually:
   - Basic: `python -m worldcup_predictor predict-match --home France --away Senegal`
   - Hicruben-inspired low-score correction: add `--score-model dixon_coles`.
   - lbenz730-inspired uncertainty intervals: add `--include-uncertainty`.
   - With generated non-odds context: `python -m worldcup_predictor predict-match --home France --away Senegal --match-id 97 --use-generated-context`
   - With official lineup file: add `--lineup-file <csv> --lineup-allowed-source <source> --player-ratings-file inputs/player_ratings/eafc26_player_ratings.csv`.
   - Read the returned `explanation` object and use it as the primary source for any user-facing reasoning.
   - `predict-match` appends a pravindurgani-inspired audit entry to `outputs/audit/prediction_runs.jsonl`; read this file when the user asks what data/model snapshot a prediction used.
4. For tournament output, run:
   - `python -m worldcup_predictor simulate-tournament --runs 20000 --use-generated-context`
   - `python -m worldcup_predictor report --runs 20000 --use-generated-context`
   - Use `--score-model dixon_coles` only when you want the optional Dixon-Coles low-score correlation model instead of the default independent Poisson model.
   - Use `--include-uncertainty` on `report` when the sample match should include p05/p50/p95 uncertainty intervals.
   - The Markdown report includes a javierruanohdez-inspired 2026 format randomness section derived from current Monte Carlo champion probabilities. It explains 48 teams, 12 groups, Round of 32, extra knockout volatility, and champion-probability concentration metrics.
   - `report` appends one sample-match audit entry to `outputs/audit/prediction_runs.jsonl`.
5. Validate after model edits:
   - `python -m unittest discover -s tests -v`
   - For probability quality, run `python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1`.
   - When testing the Hicruben-inspired model, also run `python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1 --score-model dixon_coles`.
   - For Alan-Turing-inspired Dixon-Coles parameter review, run `python -m worldcup_predictor tune-dixon-coles --start-year 2018 --min-prior-matches 1`.
   - For pameldas-inspired score evaluation, inspect `exact_score_accuracy`, `top3_scoreline_accuracy`, `combined_goal_mae`, and `combined_goal_rmse` in the backtest output.
   - For kamil-kucharski-inspired sanity checks, run `python -m worldcup_predictor ranking-baseline --home France --away Senegal`.
   - For rivu-intel45-inspired W/D/L calibration review, run `python -m worldcup_predictor calibration-backtest --start-year 2018 --min-prior-matches 1`. Treat this as an optional gate; it does not change default predictions.

## Explanation Contract

Answer user-facing explanations in plain Chinese. Use the prediction JSON `explanation` object when present. Do not stop at a short result-only explanation.

Every match explanation must cover:

- Prediction result: win/draw/loss probabilities, most likely score, expected goals, champion/advancement probabilities, or event counts.
- Method: historical goal baseline -> team strength -> goal lambdas -> scoreline matrix -> W/D/L aggregation. The default scoreline matrix is independent Poisson; `--score-model dixon_coles` applies a Hicruben-inspired Dixon-Coles low-score correction. Add Monte Carlo tournament simulation only for tournament outputs.
- Team strength: Elo, FIFA rank/points, recent goals for/against, recent points, World Cup historical goals for/against.
- Lambda path: base goal expectations and final goal expectations after lineup/context multipliers.
- Lineup and availability: whether official starters, injuries, suspensions, substitutes, expected minutes, and player ratings were used; if no lineup file is present, say they did not affect the run.
- Non-odds context: player performance, travel/fatigue, tactics, weather, and referee environment, including each row count or neutral fallback when available from `explanation.factors.match_context`.
- Event counts: yellow cards, red cards, corners, free kicks, and penalties by half when `event_prediction` or `explanation.factors.event_counts` exists.
- Data quality: state which data actually entered this run, which sources were missing, and which values used fallback.
- Score model: state whether the run used `independent_poisson` or `dixon_coles`, and if Dixon-Coles was used explain that it only changes low-score correlation, not team strength inputs.
- Dixon-Coles tuning: `tune-dixon-coles` is an Alan Turing Institute inspired rho grid-search backtest. Use it to justify or reject a rho candidate; it does not change default predictions by itself.
- Uncertainty: if `explanation.factors.uncertainty.used` is true, explain the p05/p50/p95 intervals and say this is a lbenz730-inspired lightweight lambda perturbation proxy, not a full Bayesian bivariate Poisson posterior.
- Data source/type audit: when the user asks where data came from, explicitly separate source, data type, local file, model agent, whether it was obtained, whether it entered the model, and whether it is pre-kickoff safe.
- Warnings: relay or translate CLI JSON `warnings`, especially missing lineup, non-exact kickoff weather, small player/event samples, missing World Cup history, or Elo fallback.
- Boundaries: do not describe probabilities as certainties; do not claim real betting odds were used; do not call EA FC game ratings official FIFA player ratings.
- Backtest interpretation: use log-loss/Brier/RPS/calibration for probability quality and exact score accuracy/top-3 scoreline accuracy/goal MAE/RMSE for scoreline quality. Do not claim a model improved just because one metric moved favorably.
- Calibration gate: `calibration-backtest` is a rivu-intel45-inspired classification-calibration review. It fits only a lightweight temperature plus draw-multiplier calibration on historical predictions, then evaluates out-of-sample. Do not present it as XGBoost, and do not enable it by default unless the gate recommends it.
- Audit log: when present, use `outputs/audit/prediction_runs.jsonl` to explain the exact command, model parameters, input file hashes/row counts, pre-match safety flags, output probabilities, and warnings for a run. This log is append-only and does not affect predictions.
- Baselines: `ranking-baseline` is a kamil-kucharski-inspired FIFA ranking/points Poisson sanity check. Use it to compare against the main model, not as the production prediction. It uses the current FIFA ranking snapshot and is not a time-safe historical backtest.
- Tournament format randomness: for report/tournament answers, explain the 2026 format effect using the report's computed metrics: highest champion probability, Top 3/Top 10 champion-probability concentration, count of teams at or above 5%/1%, and effective champion contenders. This is a javierruanohdez-inspired explanation layer, not a data source or point-estimate model change.

## References

Read only the needed reference:

- `references/model-overview.md`: multi-agent architecture, agent roles, and prediction logic.
- `references/data-contracts.md`: local data files, baseline row counts, model usage, and caveats.
- `references/commands-and-validation.md`: CLI examples, output files, validation, and troubleshooting.

## Guardrails

- Pre-match prediction must not use post-match/live ratings or known final results unless the user explicitly asks for post-match review.
- Official starters, injuries, and substitution strategy only affect the model when a trusted pre-kickoff `--lineup-file` is supplied.
- FIFA live match `Status=1/2` can be mapped to starter/substitute only after checking each team has 11 starters and a plausible bench. It does not by itself prove injuries or suspensions.
- FIFA player profiles and individual statistics are identity/profile data, not complete club plus national-team performance samples.
- FIFA live `playerstatistics/match/...` is not pre-match safe when populated after kickoff; if it is `null` before kickoff, record it as unavailable rather than filling guesses.
- `--use-generated-context` uses generated priors and samples; treat it as useful context, not complete live feed coverage.
- `--include-uncertainty` does not add new match data or change point estimates; it adds interval estimates around final lambdas. Do not call it a full Bayesian model.
- The audit log records local file metadata and output probabilities; it does not fetch live data, prove injury severity, or make post-match data safe for pre-match use.
- `ranking-baseline` does not use Elo, recent form, lineup, player ratings, weather, travel, tactics, referee context, or events; do not present it as the full model.
- The 2026 format randomness report section does not change single-match probabilities; it only summarizes how the tournament bracket and Monte Carlo outcomes disperse championship odds.
- `calibration-backtest` is default-off and report-only. It must not be described as changing scorelines, event counts, tournament sampling, or the production match prediction unless a future implementation explicitly wires it in after passing the gate.
- `tune-dixon-coles` is also default-off and report-only. A favorable rho backtest is evidence for a future default change, not an automatic production change.
- Real betting odds are intentionally excluded from the local model unless the user explicitly changes the scope and provides a legal source.
- If the user asks for latest/current facts, browse or refresh source data before answering.
