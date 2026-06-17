from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from .audit import append_prediction_audit
from .backtest import run_backtest, tune_dixon_coles_rho, write_backtest_report, write_dixon_coles_tuning_report
from .baselines import RankingBaselineAgent, compare_with_main_prediction, write_ranking_baseline_report
from .calibration import run_calibration_backtest, write_calibration_report
from .context import (
    DEFAULT_PLAYER_PERFORMANCE_FILE,
    DEFAULT_REFEREE_FILE,
    DEFAULT_TACTICS_FILE,
    DEFAULT_TRAVEL_FILE,
    DEFAULT_WEATHER_FILE,
    MatchContextAgent,
)
from .data import DataAgent, refresh_data
from .events import EventAgent
from .lineups import LineupAgent
from .report import ReportAgent
from .scoreline import ScorelineAgent
from .strength import StrengthAgent
from .tournament import TournamentAgent
from .uncertainty import UncertaintyAgent


def build_agents(
    lineup_file: str | None = None,
    lineup_allowed_sources: list[str] | None = None,
    allow_projected_lineups: bool = False,
    player_ratings_file: str | None = None,
    player_performance_file: str | None = None,
    weather_file: str | None = None,
    travel_file: str | None = None,
    tactics_file: str | None = None,
    referee_file: str | None = None,
    use_generated_context: bool = False,
    score_model: str = "independent_poisson",
    dixon_coles_rho: float = -0.08,
    include_uncertainty: bool = False,
    uncertainty_samples: int = 500,
):
    data = DataAgent()
    strength = StrengthAgent(data.data_dir)
    if use_generated_context:
        player_performance_file = player_performance_file or str(DEFAULT_PLAYER_PERFORMANCE_FILE)
        weather_file = weather_file or str(DEFAULT_WEATHER_FILE)
        travel_file = travel_file or str(DEFAULT_TRAVEL_FILE)
        tactics_file = tactics_file or str(DEFAULT_TACTICS_FILE)
        referee_file = referee_file or str(DEFAULT_REFEREE_FILE)
    lineup = (
        LineupAgent(
            lineup_file,
            allowed_sources=lineup_allowed_sources,
            require_official_starters=not allow_projected_lineups,
            player_ratings_file=player_ratings_file,
        )
        if lineup_file
        else None
    )
    context = (
        MatchContextAgent(
            player_performance_file=player_performance_file,
            weather_file=weather_file,
            travel_file=travel_file,
            tactics_file=tactics_file,
            referee_file=referee_file,
            data_dir=data.data_dir,
        )
        if any([player_performance_file, weather_file, travel_file, tactics_file, referee_file])
        else None
    )
    events = EventAgent(data.data_dir)
    uncertainty = UncertaintyAgent(samples=uncertainty_samples) if include_uncertainty else None
    scoreline = ScorelineAgent(
        strength,
        lineup=lineup,
        context=context,
        events=events,
        score_model=score_model,
        dixon_coles_rho=dixon_coles_rho,
        uncertainty=uncertainty,
    )
    tournament = TournamentAgent(data=data, scoreline=scoreline)
    report = ReportAgent()
    return data, scoreline, tournament, report


def predict_all_group_matches(data: DataAgent, scoreline: ScorelineAgent):
    return [scoreline.predict(f.home_team, f.away_team, match_id=f.match_id) for f in data.group_fixtures()]


def cmd_refresh_data(_args) -> int:
    return refresh_data()


def cmd_build_context_data(_args) -> int:
    script = Path(__file__).resolve().parents[1] / "worldcup_data_audit" / "scripts" / "build_non_odds_context_inputs.py"
    return subprocess.call([sys.executable, str(script)], cwd=str(script.parents[2]))


def cmd_predict_match(args) -> int:
    _data, scoreline, _tournament, _report = build_agents(
        args.lineup_file,
        args.lineup_allowed_source,
        args.allow_projected_lineups,
        args.player_ratings_file,
        args.player_performance_file,
        args.weather_file,
        args.travel_file,
        args.tactics_file,
        args.referee_file,
        args.use_generated_context,
        score_model=args.score_model,
        dixon_coles_rho=args.dixon_coles_rho,
        include_uncertainty=args.include_uncertainty,
        uncertainty_samples=args.uncertainty_samples,
    )
    pred = scoreline.predict(args.home, args.away, match_id=args.match_id)
    audit_path = append_prediction_audit(pred, "predict-match", args)
    payload = asdict(pred)
    payload["audit_log"] = str(audit_path)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_simulate_tournament(args) -> int:
    _data, _scoreline, tournament, report = build_agents(
        args.lineup_file,
        args.lineup_allowed_source,
        args.allow_projected_lineups,
        args.player_ratings_file,
        args.player_performance_file,
        args.weather_file,
        args.travel_file,
        args.tactics_file,
        args.referee_file,
        args.use_generated_context,
        score_model=args.score_model,
        dixon_coles_rho=args.dixon_coles_rho,
    )
    outcomes, groups = tournament.simulate(runs=args.runs)
    odds_path, group_path = report.write_tournament(outcomes, groups)
    print(json.dumps({"tournament_odds": str(odds_path), "group_rankings": str(group_path)}, indent=2, ensure_ascii=False))
    return 0


def cmd_report(args) -> int:
    data, scoreline, tournament, report = build_agents(
        args.lineup_file,
        args.lineup_allowed_source,
        args.allow_projected_lineups,
        args.player_ratings_file,
        args.player_performance_file,
        args.weather_file,
        args.travel_file,
        args.tactics_file,
        args.referee_file,
        args.use_generated_context,
        score_model=args.score_model,
        dixon_coles_rho=args.dixon_coles_rho,
        include_uncertainty=args.include_uncertainty,
        uncertainty_samples=args.uncertainty_samples,
    )
    match_predictions = predict_all_group_matches(data, scoreline)
    outcomes, groups = tournament.simulate(runs=args.runs)
    match_path = report.write_match_predictions(match_predictions)
    odds_path, group_path = report.write_tournament(outcomes, groups)
    sample = scoreline.predict(args.sample_home, args.sample_away, match_id=args.sample_match_id)
    report_path = report.write_report(sample, outcomes, groups, args.runs)
    audit_path = append_prediction_audit(sample, "report", args, run_type="report_sample")
    print(
        json.dumps(
            {
                "match_predictions": str(match_path),
                "tournament_odds": str(odds_path),
                "group_rankings": str(group_path),
                "report": str(report_path),
                "audit_log": str(audit_path),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def cmd_backtest(args) -> int:
    result = run_backtest(
        start_year=args.start_year,
        end_year=args.end_year,
        min_prior_matches=args.min_prior_matches,
        score_model=args.score_model,
        dixon_coles_rho=args.dixon_coles_rho,
    )
    path = write_backtest_report(result, args.output)
    print(json.dumps({"backtest": str(path), "metrics": result}, indent=2, ensure_ascii=False))
    return 0


def cmd_tune_dixon_coles(args) -> int:
    result = tune_dixon_coles_rho(
        start_year=args.start_year,
        end_year=args.end_year,
        min_prior_matches=args.min_prior_matches,
        rho_values=_parse_float_csv(args.rho_values),
    )
    path = write_dixon_coles_tuning_report(result, args.output)
    print(json.dumps({"dixon_coles_rho_tuning": str(path), "metrics": result}, indent=2, ensure_ascii=False))
    return 0


def cmd_calibration_backtest(args) -> int:
    result = run_calibration_backtest(
        start_year=args.start_year,
        end_year=args.end_year,
        min_prior_matches=args.min_prior_matches,
        min_training_matches=args.min_training_matches,
        score_model=args.score_model,
        dixon_coles_rho=args.dixon_coles_rho,
    )
    path = write_calibration_report(result, args.output)
    print(json.dumps({"calibration_backtest": str(path), "metrics": result}, indent=2, ensure_ascii=False))
    return 0


def cmd_ranking_baseline(args) -> int:
    data, scoreline, _tournament, _report = build_agents(
        score_model=args.score_model,
        dixon_coles_rho=args.dixon_coles_rho,
    )
    baseline_agent = RankingBaselineAgent(
        data.data_dir,
        score_model=args.score_model,
        dixon_coles_rho=args.dixon_coles_rho,
    )
    baseline = baseline_agent.predict(args.home, args.away, match_id=args.match_id)
    main_prediction = scoreline.predict(args.home, args.away, match_id=args.match_id)
    payload = {
        "home_team": main_prediction.home_team,
        "away_team": main_prediction.away_team,
        "match_id": args.match_id,
        "purpose": "kamil_kucharski_inspired_fifa_ranking_poisson_sanity_check",
        "main_model": asdict(main_prediction),
        "ranking_baseline": baseline,
        "comparison": compare_with_main_prediction(baseline, main_prediction),
        "caveats": [
            "The ranking baseline is a simple comparison tool and does not replace the main model.",
            "The ranking baseline uses the current FIFA ranking snapshot, so it is not a time-safe historical backtest.",
        ],
    }
    path = write_ranking_baseline_report(payload, args.output)
    payload["output"] = str(path)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="World Cup multi-agent prediction system")
    sub = parser.add_subparsers(dest="command", required=True)

    refresh = sub.add_parser("refresh-data", help="Refresh processed source data")
    refresh.set_defaults(func=cmd_refresh_data)

    context_data = sub.add_parser("build-context-data", help="Build generated non-odds context input files")
    context_data.set_defaults(func=cmd_build_context_data)

    predict = sub.add_parser("predict-match", help="Predict one match")
    predict.add_argument("--home", required=True)
    predict.add_argument("--away", required=True)
    predict.add_argument("--match-id", default="")
    predict.add_argument("--lineup-file", default=None)
    predict.add_argument("--lineup-allowed-source", action="append", default=None)
    predict.add_argument("--allow-projected-lineups", action="store_true")
    predict.add_argument("--player-ratings-file", default=None)
    predict.add_argument("--player-performance-file", default=None)
    predict.add_argument("--weather-file", default=None)
    predict.add_argument("--travel-file", default=None)
    predict.add_argument("--tactics-file", default=None)
    predict.add_argument("--referee-file", default=None)
    predict.add_argument("--use-generated-context", action="store_true")
    add_score_model_arguments(predict)
    add_uncertainty_arguments(predict)
    predict.set_defaults(func=cmd_predict_match)

    simulate = sub.add_parser("simulate-tournament", help="Run tournament Monte Carlo")
    simulate.add_argument("--runs", type=int, default=20000)
    simulate.add_argument("--lineup-file", default=None)
    simulate.add_argument("--lineup-allowed-source", action="append", default=None)
    simulate.add_argument("--allow-projected-lineups", action="store_true")
    simulate.add_argument("--player-ratings-file", default=None)
    simulate.add_argument("--player-performance-file", default=None)
    simulate.add_argument("--weather-file", default=None)
    simulate.add_argument("--travel-file", default=None)
    simulate.add_argument("--tactics-file", default=None)
    simulate.add_argument("--referee-file", default=None)
    simulate.add_argument("--use-generated-context", action="store_true")
    add_score_model_arguments(simulate)
    simulate.set_defaults(func=cmd_simulate_tournament)

    report = sub.add_parser("report", help="Generate prediction files and Chinese report")
    report.add_argument("--runs", type=int, default=20000)
    report.add_argument("--sample-home", default="France")
    report.add_argument("--sample-away", default="Senegal")
    report.add_argument("--sample-match-id", default="")
    report.add_argument("--lineup-file", default=None)
    report.add_argument("--lineup-allowed-source", action="append", default=None)
    report.add_argument("--allow-projected-lineups", action="store_true")
    report.add_argument("--player-ratings-file", default=None)
    report.add_argument("--player-performance-file", default=None)
    report.add_argument("--weather-file", default=None)
    report.add_argument("--travel-file", default=None)
    report.add_argument("--tactics-file", default=None)
    report.add_argument("--referee-file", default=None)
    report.add_argument("--use-generated-context", action="store_true")
    add_score_model_arguments(report)
    add_uncertainty_arguments(report)
    report.set_defaults(func=cmd_report)

    backtest = sub.add_parser("backtest", help="Run historical rolling backtest")
    backtest.add_argument("--start-year", type=int, default=1954)
    backtest.add_argument("--end-year", type=int, default=None)
    backtest.add_argument("--min-prior-matches", type=int, default=3)
    backtest.add_argument("--output", default=None)
    add_score_model_arguments(backtest)
    backtest.set_defaults(func=cmd_backtest)

    tune_dc = sub.add_parser("tune-dixon-coles", help="Tune Dixon-Coles rho with historical backtests")
    tune_dc.add_argument("--start-year", type=int, default=2018)
    tune_dc.add_argument("--end-year", type=int, default=None)
    tune_dc.add_argument("--min-prior-matches", type=int, default=3)
    tune_dc.add_argument("--rho-values", default="-0.16,-0.12,-0.08,-0.04,0.0,0.04")
    tune_dc.add_argument("--output", default=None)
    tune_dc.set_defaults(func=cmd_tune_dixon_coles)

    calibration = sub.add_parser("calibration-backtest", help="Evaluate optional W/D/L probability calibration")
    calibration.add_argument("--start-year", type=int, default=2018)
    calibration.add_argument("--end-year", type=int, default=None)
    calibration.add_argument("--min-prior-matches", type=int, default=3)
    calibration.add_argument("--min-training-matches", type=int, default=50)
    calibration.add_argument("--output", default=None)
    add_score_model_arguments(calibration)
    calibration.set_defaults(func=cmd_calibration_backtest)

    ranking = sub.add_parser("ranking-baseline", help="Compare main model with a FIFA ranking Poisson baseline")
    ranking.add_argument("--home", required=True)
    ranking.add_argument("--away", required=True)
    ranking.add_argument("--match-id", default="")
    ranking.add_argument("--output", default=None)
    add_score_model_arguments(ranking)
    ranking.set_defaults(func=cmd_ranking_baseline)
    return parser


def add_score_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--score-model",
        choices=["independent_poisson", "dixon_coles"],
        default="independent_poisson",
        help="Scoreline probability model",
    )
    parser.add_argument(
        "--dixon-coles-rho",
        type=float,
        default=-0.08,
        help="Dixon-Coles low-score correlation parameter; used only with --score-model dixon_coles",
    )


def _parse_float_csv(value: str) -> list[float]:
    try:
        return [float(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid comma-separated float list: {value}") from exc


def add_uncertainty_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--include-uncertainty",
        action="store_true",
        help="Add lightweight p05/p50/p95 probability intervals around final lambdas",
    )
    parser.add_argument(
        "--uncertainty-samples",
        type=int,
        default=500,
        help="Number of lambda perturbation samples for --include-uncertainty",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
