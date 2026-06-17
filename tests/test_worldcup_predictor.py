from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from worldcup_predictor.backtest import run_backtest
from worldcup_predictor.context import MatchContextAgent
from worldcup_predictor.data import DataAgent, read_csv
from worldcup_predictor.events import EventAgent
from worldcup_predictor.lineups import LineupAgent
from worldcup_predictor.ratings import DEFAULT_PLAYER_RATINGS_FILE, PlayerRatingsAgent
from worldcup_predictor.scoreline import ScorelineAgent
from worldcup_predictor.strength import StrengthAgent
from worldcup_predictor.tournament import TournamentAgent


class WorldCupPredictorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = DataAgent()
        cls.strength = StrengthAgent(cls.data.data_dir)
        cls.scoreline = ScorelineAgent(cls.strength)

    def test_data_loads_expected_fixture_and_team_counts(self):
        self.assertEqual(len(self.data.fixtures()), 104)
        self.assertEqual(len(self.data.teams()), 48)
        groups = self.data.teams_by_group()
        self.assertEqual(len(groups), 12)
        self.assertTrue(all(len(teams) == 4 for teams in groups.values()))

    def test_unplayed_raw_zero_scores_do_not_become_actual_scores(self):
        rows = read_csv(self.data.data_dir / "worldcup26_games.csv")
        bad_rows = [
            row
            for row in rows
            if row["finished"] != "TRUE" and (row["actual_home_score"] or row["actual_away_score"])
        ]
        self.assertEqual(bad_rows, [])

    def test_match_prediction_probabilities_sum_to_one_and_scorelines_sorted(self):
        pred = self.scoreline.predict("France", "Senegal")
        total = pred.p_home_win + pred.p_draw + pred.p_away_win
        self.assertAlmostEqual(total, 1.0, delta=0.001)
        probs = [item["probability"] for item in pred.top_scorelines]
        self.assertEqual(probs, sorted(probs, reverse=True))
        self.assertIn("headline", pred.explanation)
        self.assertIn("method", pred.explanation)
        self.assertIn("team_strength", pred.explanation["factors"])
        self.assertIn("lineup_and_availability", pred.explanation["factors"])
        self.assertIn("match_context", pred.explanation["factors"])
        self.assertIn("event_counts", pred.explanation["factors"])
        self.assertIn("data_quality", pred.explanation["factors"])

    def test_missing_team_elo_uses_fallback_warning(self):
        pred = self.scoreline.predict("Atlantis", "France")
        self.assertTrue(any("fallback 1500" in warning for warning in pred.warnings))
        total = pred.p_home_win + pred.p_draw + pred.p_away_win
        self.assertAlmostEqual(total, 1.0, delta=0.001)

    def test_fifa_ranking_snapshot_is_available_and_used(self):
        rows = read_csv(self.data.data_dir / "fifa_ranking_snapshot.csv")
        self.assertGreaterEqual(len([row for row in rows if row.get("is_2026_team") == "TRUE"]), 48)
        france = self.strength.team_strength("France")
        self.assertIsNotNone(france.fifa_rank)
        self.assertIsNotNone(france.fifa_points)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "derived_elo_snapshot.csv").write_text("team,elo\nAlpha,1500\nBeta,1500\n", encoding="utf-8")
            (root / "derived_recent_form.csv").write_text(
                "\n".join(
                    [
                        "team,recent_points_per_match,recent_goals_for_per_match,recent_goals_against_per_match",
                        "Alpha,1.5,1.2,1.2",
                        "Beta,1.5,1.2,1.2",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "international_results_worldcup_only.csv").write_text(
                "date,home_team,away_team,home_score,away_score\n2022-01-01,Alpha,Beta,1,1\n",
                encoding="utf-8",
            )
            (root / "fifa_ranking_snapshot.csv").write_text(
                "\n".join(
                    [
                        "team,fifa_rank,fifa_previous_rank,fifa_points,fifa_previous_points",
                        "Alpha,1,2,2000,1980",
                        "Beta,100,95,1000,1010",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            strength = StrengthAgent(root)
            alpha_lambda, beta_lambda, _warnings = strength.expected_lambdas("Alpha", "Beta")
            self.assertGreater(alpha_lambda, beta_lambda)

    def test_lineup_file_adjusts_lambdas_and_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lineups.csv"
            lines = [
                "match_id,team,player,role,position,rating,rating_basis,status,expected_minutes,sub_minute,official,source,notes",
            ]
            france_positions = ["GK", "CB", "CB", "LB", "RB", "DM", "CM", "AM", "LW", "RW", "ST"]
            senegal_positions = ["GK", "CB", "CB", "LB", "RB", "DM", "CM", "AM", "LW", "RW", "ST"]
            for idx, position in enumerate(france_positions, 1):
                lines.append(f"900,France,France Starter {idx},starter,{position},90,prematch,available,90,,true,test,")
            for idx, position in enumerate(senegal_positions, 1):
                lines.append(f"900,Senegal,Senegal Starter {idx},starter,{position},65,prematch,available,90,,true,test,")
            lines.append("900,France,France Sub 1,substitute,FW,88,prematch,available,,60,true,test,")
            lines.append("900,Senegal,Senegal Injured CB,unavailable,CB,90,prematch,injured,90,,true,test,")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            lineup_scoreline = ScorelineAgent(self.strength, lineup=LineupAgent(path))
            base = self.scoreline.predict("France", "Senegal")
            adjusted = lineup_scoreline.predict("France", "Senegal", match_id="900")

            self.assertGreater(adjusted.lambda_home, base.lambda_home)
            self.assertLess(adjusted.lambda_away, base.lambda_away)
            self.assertEqual(adjusted.lineup_adjustment["home_context"]["starter_count"], 11)
            self.assertEqual(adjusted.lineup_adjustment["away_context"]["unavailable_count"], 1)

    def test_lineup_rejects_post_match_rating_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "leaky_lineups.csv"
            path.write_text(
                "\n".join(
                    [
                        "match_id,team,player,role,position,rating,rating_basis,status,expected_minutes,sub_minute,official,source,notes",
                        "1,France,Leaky Starter,starter,ST,99,post_match,available,90,,true,sofascore-postmatch,",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                LineupAgent(path)

    def test_unavailable_substitute_does_not_count_as_full_starter_loss(self):
        row = {"role": "substitute", "status": "injured"}
        self.assertEqual(LineupAgent._expected_minutes(row, "substitute", "injured"), 25.0)

    def test_player_ratings_lookup_and_lineup_fill_missing_rating(self):
        rating = PlayerRatingsAgent(DEFAULT_PLAYER_RATINGS_FILE).lookup("Jude Bellingham", nationality="England")[0]
        self.assertIsNotNone(rating)
        self.assertGreaterEqual(rating.overall, 85)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lineups.csv"
            lines = [
                "match_id,team,player,role,position,rating,rating_basis,status,expected_minutes,sub_minute,official,source,nationality,club,notes",
            ]
            starters = [
                ("Jude Bellingham", "CAM", "England", "Real Madrid"),
                ("England Starter 2", "GK", "England", ""),
                ("England Starter 3", "CB", "England", ""),
                ("England Starter 4", "CB", "England", ""),
                ("England Starter 5", "LB", "England", ""),
                ("England Starter 6", "RB", "England", ""),
                ("England Starter 7", "DM", "England", ""),
                ("England Starter 8", "CM", "England", ""),
                ("England Starter 9", "LW", "England", ""),
                ("England Starter 10", "RW", "England", ""),
                ("England Starter 11", "ST", "England", ""),
            ]
            for player, position, nationality, club in starters:
                rating_value = "" if player == "Jude Bellingham" else "75"
                basis = "" if player == "Jude Bellingham" else "prematch"
                lines.append(f"901,England,{player},starter,{position},{rating_value},{basis},available,90,,true,test,{nationality},{club},")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            lineup = LineupAgent(path, player_ratings_file=DEFAULT_PLAYER_RATINGS_FILE)
            context = lineup.team_context("England", "901")
            self.assertGreater(context.attack_rating, 75.0)
            self.assertTrue(any("rating filled from" in warning for warning in context.warnings))

    def test_match_context_uses_non_odds_inputs_to_adjust_lambdas(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            performance = root / "performance.csv"
            performance.write_text(
                "\n".join(
                    [
                        "snapshot_date,match_id,match_date,source,source_timestamp,player_id,player_name,national_team,team,club,team_type,competition,opponent,home_away_neutral,position,minutes,started,goals,assists,xg,xa,shots,shots_on_target,key_passes,progressive_passes,progressive_carries,touches_box,pressures,tackles,interceptions,blocks,clearances,aerial_duels_won,duels_won,yellow_cards,red_cards,keeper_saves,keeper_goals_prevented,match_rating,rating_basis",
                        "2026-06-01,902,2026-05-20,test,2026-06-01,1,France Star,France,Paris Club,Paris Club,club,League,Opponent,home,ST,900,TRUE,12,6,10,5,40,25,20,0,0,70,0,1,1,0,0,0,3,1,0,0,0,0,7.4,season_average",
                        "2026-06-01,902,2026-05-20,test,2026-06-01,2,Senegal Defender,Senegal,Senegal,,national,Friendly,Opponent,away,CB,900,TRUE,0,0,0,0,1,0,0,0,0,1,0,18,14,10,20,8,15,4,0,0,0,0,6.8,season_average",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            weather = root / "weather.csv"
            weather.write_text(
                "\n".join(
                    [
                        "match_id,stadium,time_utc,source,source_timestamp,temperature_c,humidity_pct,precipitation_mm,wind_kph,weather_basis,notes",
                        "902,Test Stadium,2026-06-11T19:00:00Z,open-meteo,2026-06-10,34,85,3,28,forecast,",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            travel = root / "travel.csv"
            travel.write_text(
                "\n".join(
                    [
                        "match_id,team,source,source_timestamp,travel_km,rest_days,timezone_shift_hours,training_disruption_score,fatigue_basis,notes",
                        "902,France,test,2026-06-10,500,6,1,0,derived,",
                        "902,Senegal,test,2026-06-10,9000,3,5,0.5,derived,",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            tactics = root / "tactics.csv"
            tactics.write_text(
                "\n".join(
                    [
                        "match_id,team,source,source_timestamp,formation,pressing_intensity,attacking_width,set_piece_strength,counter_attack_threat,defensive_line_height,possession_bias,style_basis,notes",
                        "902,France,test,2026-06-10,4-3-3,75,70,80,65,45,65,scouted,",
                        "902,Senegal,test,2026-06-10,4-4-2,45,45,45,50,65,45,scouted,",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            referee = root / "referee.csv"
            referee.write_text(
                "\n".join(
                    [
                        "match_id,referee,source,source_timestamp,cards_per_match,red_cards_per_match,fouls_per_match,penalties_per_match,home_bias_index,strictness_basis,notes",
                        "902,Strict Ref,test,2026-06-10,6,0.3,31,0.45,0,historical,",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            context = MatchContextAgent(
                player_performance_file=performance,
                weather_file=weather,
                travel_file=travel,
                tactics_file=tactics,
                referee_file=referee,
                data_dir=self.data.data_dir,
            )
            contextual_scoreline = ScorelineAgent(self.strength, context=context)
            base = self.scoreline.predict("France", "Senegal")
            adjusted = contextual_scoreline.predict("France", "Senegal", match_id="902")

            self.assertNotEqual(adjusted.lambda_home, base.lambda_home)
            self.assertNotEqual(adjusted.lambda_away, base.lambda_away)
            payload = adjusted.context_adjustment
            self.assertEqual(payload["home_context"]["player_performance_rows"], 1)
            self.assertEqual(payload["away_context"]["travel_rows"], 1)
            self.assertEqual(payload["home_context"]["tactics_rows"], 1)
            self.assertEqual(payload["weather_context"]["rows"], 1)
            self.assertEqual(payload["referee_context"]["rows"], 1)

    def test_event_agent_predicts_requested_counts_by_half(self):
        events = EventAgent(self.data.data_dir)
        pred = ScorelineAgent(self.strength, events=events).predict("Spain", "Japan", match_id="902")
        payload = pred.event_prediction
        self.assertGreaterEqual(payload["sample_rows"], 1)
        for metric in ["yellow_cards", "red_cards", "corners", "free_kicks", "penalties"]:
            item = payload["match_totals"][metric]
            self.assertIn("first_half_expected", item)
            self.assertIn("second_half_expected", item)
            self.assertIn("total_expected", item)
            self.assertIn("most_likely_total", item)
            self.assertGreaterEqual(item["total_expected"], 0)

    def test_generated_non_odds_context_inputs_are_usable(self):
        root = Path(__file__).resolve().parents[1]
        performance = root / "inputs" / "player_performance" / "player_match_performance.csv"
        weather = root / "inputs" / "match_context" / "weather_forecast.csv"
        travel = root / "inputs" / "match_context" / "team_travel_fatigue.csv"
        tactics = root / "inputs" / "match_context" / "tactics.csv"
        referee = root / "inputs" / "match_context" / "referees.csv"

        self.assertGreaterEqual(len(read_csv(performance)), 200)
        self.assertGreaterEqual(len(read_csv(weather)), 30)
        self.assertEqual(len(read_csv(travel)), 144)
        self.assertEqual(len(read_csv(tactics)), 48)
        self.assertEqual(len(read_csv(referee)), 1)

        context = MatchContextAgent(
            player_performance_file=performance,
            weather_file=weather,
            travel_file=travel,
            tactics_file=tactics,
            referee_file=referee,
            data_dir=self.data.data_dir,
        )
        pred = ScorelineAgent(self.strength, context=context).predict("Uruguay", "Spain", match_id="66")
        payload = pred.context_adjustment

        self.assertEqual(payload["home_context"]["travel_rows"], 1)
        self.assertEqual(payload["home_context"]["tactics_rows"], 1)
        self.assertGreater(payload["away_context"]["player_performance_rows"], 0)
        self.assertEqual(payload["weather_context"]["rows"], 1)
        self.assertEqual(payload["referee_context"]["rows"], 1)
        self.assertNotEqual(payload["lambda_home_multiplier"], 1.0)
        self.assertNotEqual(payload["lambda_away_multiplier"], 1.0)
        self.assertTrue(pred.explanation["factors"]["match_context"]["used"])
        self.assertIn("player_performance", pred.explanation["factors"]["match_context"])
        self.assertIn("travel_fatigue", pred.explanation["factors"]["match_context"])
        self.assertIn("tactics", pred.explanation["factors"]["match_context"])
        self.assertIn("weather", pred.explanation["factors"]["match_context"])
        self.assertIn("referee", pred.explanation["factors"]["match_context"])

    def test_backtest_reports_core_metrics_and_calibration(self):
        result = run_backtest(start_year=2018, min_prior_matches=1)
        self.assertGreater(result["matches_evaluated"], 0)
        self.assertGreater(result["log_loss"], 0)
        self.assertGreater(result["brier_score"], 0)
        self.assertGreater(result["ranked_probability_score"], 0)
        self.assertLess(result["log_loss"], 1.2)
        self.assertLess(result["brier_score"], 0.75)
        self.assertTrue(result["calibration"])
        self.assertTrue(result["config"]["time_safe"])

    def test_tournament_simulation_invariants(self):
        tournament = TournamentAgent(data=self.data, scoreline=self.scoreline, seed=2026)
        outcomes, groups = tournament.simulate(runs=200)
        self.assertEqual(len(outcomes), 48)
        self.assertEqual(len(groups), 48)
        self.assertAlmostEqual(sum(row.p_champion for row in outcomes), 1.0, delta=0.001)
        self.assertAlmostEqual(sum(row.p_round_of_32 for row in outcomes), 32.0, delta=0.001)

    def test_tournament_simulation_is_seed_stable(self):
        a = TournamentAgent(data=self.data, scoreline=self.scoreline, seed=2026).simulate(runs=50)[0]
        b = TournamentAgent(data=self.data, scoreline=self.scoreline, seed=2026).simulate(runs=50)[0]
        self.assertEqual([row.team for row in a[:10]], [row.team for row in b[:10]])
        self.assertEqual([row.p_champion for row in a[:10]], [row.p_champion for row in b[:10]])


if __name__ == "__main__":
    unittest.main()
