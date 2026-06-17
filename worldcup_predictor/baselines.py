from __future__ import annotations

import json
from pathlib import Path

from .aliases import normalize_team
from .data import DEFAULT_DATA_DIR, OUTPUT_DIR, read_csv
from .score_models import aggregate_wdl, scoreline_matrix, sorted_scorelines, validate_score_model
from .strength import HOST_NATIONS


class RankingBaselineAgent:
    def __init__(
        self,
        data_dir: Path | str = DEFAULT_DATA_DIR,
        max_goals: int = 7,
        score_model: str = "independent_poisson",
        dixon_coles_rho: float = -0.08,
    ):
        self.data_dir = Path(data_dir)
        self.max_goals = max_goals
        self.score_model = validate_score_model(score_model)
        self.dixon_coles_rho = dixon_coles_rho
        self.rankings = self._load_rankings()
        self.global_goal_average = self._load_global_goal_average()

    def predict(self, home: str, away: str, match_id: str = "") -> dict:
        home = normalize_team(home)
        away = normalize_team(away)
        lam_h, lam_a, warnings, feature_payload = self.expected_lambdas(home, away)
        matrix = scoreline_matrix(
            lam_h,
            lam_a,
            max_goals=self.max_goals,
            score_model=self.score_model,
            dixon_coles_rho=self.dixon_coles_rho,
        )
        p_home, p_draw, p_away = aggregate_wdl(matrix)
        return {
            "baseline": "fifa_ranking_poisson",
            "source_inspiration": "kamil-kucharski/world-cup-2026-prediction FIFA ranking Poisson baseline",
            "match_id": match_id,
            "home_team": home,
            "away_team": away,
            "lambda_home": round(lam_h, 4),
            "lambda_away": round(lam_a, 4),
            "p_home_win": round(p_home, 6),
            "p_draw": round(p_draw, 6),
            "p_away_win": round(p_away, 6),
            "expected_goals": round(lam_h + lam_a, 4),
            "top_scorelines": sorted_scorelines(matrix)[:10],
            "features": feature_payload,
            "score_model": self.score_model,
            "score_model_parameters": self._score_model_parameters(),
            "warnings": warnings,
            "caveats": [
                "This is a simple current FIFA ranking/points Poisson sanity-check baseline, not the production model.",
                "It does not use Elo, recent form, World Cup team history, lineups, player ratings, weather, travel, tactics, referee context, or event samples.",
                "It uses the current FIFA ranking snapshot and is not a time-safe historical backtest baseline.",
            ],
        }

    def expected_lambdas(self, home: str, away: str) -> tuple[float, float, list[str], dict]:
        h = self.rankings.get(home)
        a = self.rankings.get(away)
        warnings = []
        if h is None:
            h = {"rank": None, "points": None}
            warnings.append(f"{home} missing FIFA ranking, baseline uses neutral strength")
        if a is None:
            a = {"rank": None, "points": None}
            warnings.append(f"{away} missing FIFA ranking, baseline uses neutral strength")
        edge = self._ranking_edge(h, a)
        host_h = 1.08 if home in HOST_NATIONS else 1.0
        host_a = 1.08 if away in HOST_NATIONS else 1.0
        lam_h = max(0.2, min(3.8, self.global_goal_average * (1.0 + edge) * host_h))
        lam_a = max(0.2, min(3.8, self.global_goal_average * (1.0 - edge) * host_a))
        features = {
            "home_fifa_rank": h["rank"],
            "away_fifa_rank": a["rank"],
            "home_fifa_points": h["points"],
            "away_fifa_points": a["points"],
            "ranking_edge": round(edge, 6),
            "global_goal_average": round(self.global_goal_average, 6),
            "home_host_multiplier": host_h,
            "away_host_multiplier": host_a,
        }
        return lam_h, lam_a, warnings, features

    def _load_rankings(self) -> dict[str, dict[str, float | None]]:
        rankings = {}
        for row in read_csv(self.data_dir / "fifa_ranking_snapshot.csv"):
            team = normalize_team(row.get("team", ""))
            if not team:
                continue
            rankings[team] = {
                "rank": _float_or_none(row.get("fifa_rank")),
                "points": _float_or_none(row.get("fifa_points")),
            }
        return rankings

    def _load_global_goal_average(self) -> float:
        rows = read_csv(self.data_dir / "international_results_worldcup_only.csv")
        total_goals = 0
        team_games = 0
        for row in rows:
            try:
                hg = int(row["home_score"])
                ag = int(row["away_score"])
            except (KeyError, TypeError, ValueError):
                continue
            total_goals += hg + ag
            team_games += 2
        return total_goals / team_games if team_games else 1.35

    @staticmethod
    def _ranking_edge(home: dict[str, float | None], away: dict[str, float | None]) -> float:
        if home.get("points") is not None and away.get("points") is not None:
            return max(-0.22, min(0.22, ((home["points"] or 0.0) - (away["points"] or 0.0)) / 500.0 * 0.18))
        if home.get("rank") is not None and away.get("rank") is not None:
            return max(-0.18, min(0.18, ((away["rank"] or 0.0) - (home["rank"] or 0.0)) / 100.0 * 0.12))
        return 0.0

    def _score_model_parameters(self) -> dict:
        payload = {
            "score_model": self.score_model,
            "max_goals": self.max_goals,
        }
        if self.score_model == "dixon_coles":
            payload["dixon_coles_rho"] = self.dixon_coles_rho
        return payload


def compare_with_main_prediction(baseline: dict, main_prediction) -> dict:
    return {
        "p_home_win_delta_main_minus_baseline": round(main_prediction.p_home_win - baseline["p_home_win"], 6),
        "p_draw_delta_main_minus_baseline": round(main_prediction.p_draw - baseline["p_draw"], 6),
        "p_away_win_delta_main_minus_baseline": round(main_prediction.p_away_win - baseline["p_away_win"], 6),
        "lambda_home_delta_main_minus_baseline": round(main_prediction.lambda_home - baseline["lambda_home"], 6),
        "lambda_away_delta_main_minus_baseline": round(main_prediction.lambda_away - baseline["lambda_away"], 6),
        "same_top_scoreline": main_prediction.top_scorelines[0]["scoreline"] == baseline["top_scorelines"][0]["scoreline"],
    }


def write_ranking_baseline_report(payload: dict, output_path: Path | str | None = None) -> Path:
    path = Path(output_path) if output_path else OUTPUT_DIR / "reports" / "ranking_baseline_sanity_check.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _float_or_none(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None
