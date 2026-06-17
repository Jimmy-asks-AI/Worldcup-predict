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
   - Run this skill's `scripts/health_check.py --root <repo>` when a quick data health check is useful.
2. Refresh or rebuild data only when the user asks for current/latest data or the local data is missing:
   - `python -m worldcup_predictor refresh-data`
   - `python -m worldcup_predictor build-context-data`
3. For one match, run the CLI instead of estimating manually:
   - Basic: `python -m worldcup_predictor predict-match --home France --away Senegal`
   - With generated non-odds context: `python -m worldcup_predictor predict-match --home France --away Senegal --match-id 97 --use-generated-context`
   - With official lineup file: add `--lineup-file <csv> --lineup-allowed-source <source> --player-ratings-file inputs/player_ratings/eafc26_player_ratings.csv`.
   - Read the returned `explanation` object and use it as the primary source for any user-facing reasoning.
4. For tournament output, run:
   - `python -m worldcup_predictor simulate-tournament --runs 20000 --use-generated-context`
   - `python -m worldcup_predictor report --runs 20000 --use-generated-context`
5. Validate after model edits:
   - `python -m unittest discover -s tests -v`
   - For probability quality, run `python -m worldcup_predictor backtest --start-year 2018 --min-prior-matches 1`.

## Explanation Contract

Answer user-facing explanations in plain Chinese. Use the prediction JSON `explanation` object when present. Do not stop at a short result-only explanation.

Every match explanation must cover:

- Prediction result: win/draw/loss probabilities, most likely score, expected goals, champion/advancement probabilities, or event counts.
- Method: historical goal baseline -> team strength -> goal lambdas -> Poisson score matrix -> W/D/L aggregation; add Monte Carlo tournament simulation only for tournament outputs.
- Team strength: Elo, FIFA rank/points, recent goals for/against, recent points, World Cup historical goals for/against.
- Lambda path: base goal expectations and final goal expectations after lineup/context multipliers.
- Lineup and availability: whether official starters, injuries, suspensions, substitutes, expected minutes, and player ratings were used; if no lineup file is present, say they did not affect the run.
- Non-odds context: player performance, travel/fatigue, tactics, weather, and referee environment, including each row count or neutral fallback when available from `explanation.factors.match_context`.
- Event counts: yellow cards, red cards, corners, free kicks, and penalties by half when `event_prediction` or `explanation.factors.event_counts` exists.
- Data quality: state which data actually entered this run, which sources were missing, and which values used fallback.
- Warnings: relay or translate CLI JSON `warnings`, especially missing lineup, non-exact kickoff weather, small player/event samples, missing World Cup history, or Elo fallback.
- Boundaries: do not describe probabilities as certainties; do not claim real betting odds were used; do not call EA FC game ratings official FIFA player ratings.

## References

Read only the needed reference:

- `references/model-overview.md`: multi-agent architecture, agent roles, and prediction logic.
- `references/data-contracts.md`: local data files, baseline row counts, model usage, and caveats.
- `references/commands-and-validation.md`: CLI examples, output files, validation, and troubleshooting.

## Guardrails

- Pre-match prediction must not use post-match/live ratings or known final results unless the user explicitly asks for post-match review.
- Official starters, injuries, and substitution strategy only affect the model when a trusted pre-kickoff `--lineup-file` is supplied.
- `--use-generated-context` uses generated priors and samples; treat it as useful context, not complete live feed coverage.
- Real betting odds are intentionally excluded from the local model unless the user explicitly changes the scope and provides a legal source.
- If the user asks for latest/current facts, browse or refresh source data before answering.
