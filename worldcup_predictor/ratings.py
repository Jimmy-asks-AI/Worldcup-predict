from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .aliases import normalize_team
from .data import ROOT, read_csv


DEFAULT_PLAYER_RATINGS_FILE = ROOT / "inputs" / "player_ratings" / "eafc26_player_ratings.csv"


@dataclass(frozen=True)
class PlayerRating:
    player_id: str
    player_name: str
    nationality: str
    club: str
    positions: str
    overall: float
    potential: float
    source: str
    basis: str


def player_key(name: str) -> str:
    text = unicodedata.normalize("NFKD", (name or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _float(value: str | None, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except ValueError:
        return default


def _name_variants(short_name: str, long_name: str) -> set[str]:
    variants = {player_key(short_name), player_key(long_name)}
    tokens = player_key(long_name).split()
    if len(tokens) >= 2:
        variants.add(f"{tokens[0]} {tokens[-1]}")
        variants.add(f"{tokens[0][0]} {tokens[-1]}")
        variants.add(" ".join(tokens[-2:]))
    return {variant for variant in variants if variant}


class PlayerRatingsAgent:
    def __init__(self, ratings_file: Path | str = DEFAULT_PLAYER_RATINGS_FILE):
        self.ratings_file = Path(ratings_file)
        if not self.ratings_file.exists():
            raise FileNotFoundError(f"Player ratings file not found: {self.ratings_file}")
        self.rows = read_csv(self.ratings_file)
        self._by_key: dict[tuple[str, str], list[PlayerRating]] = {}
        self._build_index()

    def _build_index(self) -> None:
        for row in self.rows:
            rating = PlayerRating(
                player_id=row.get("player_id", ""),
                player_name=row.get("long_name") or row.get("short_name", ""),
                nationality=normalize_team(row.get("nationality_name", "")),
                club=row.get("club_name", ""),
                positions=row.get("player_positions", ""),
                overall=_float(row.get("overall")),
                potential=_float(row.get("potential")),
                source=row.get("rating_source", ""),
                basis=row.get("rating_basis", ""),
            )
            for key in _name_variants(row.get("short_name", ""), row.get("long_name", "")):
                self._by_key.setdefault((key, rating.nationality), []).append(rating)

    def lookup(self, player_name: str, nationality: str = "", club: str = "") -> tuple[PlayerRating | None, str]:
        key = player_key(player_name)
        if not key:
            return None, "missing player name"
        nationality = normalize_team(nationality)
        candidates: list[PlayerRating] = []
        if nationality:
            candidates = list(self._by_key.get((key, nationality), []))
        if not candidates:
            for (candidate_key, _candidate_nationality), ratings in self._by_key.items():
                if candidate_key == key:
                    candidates.extend(ratings)
        if not candidates:
            return None, f"no rating match for {player_name}"
        if club:
            club_key = player_key(club)
            club_matches = [rating for rating in candidates if player_key(rating.club) == club_key]
            if len(club_matches) == 1:
                return club_matches[0], ""
            if len(club_matches) > 1:
                candidates = club_matches
        unique_ids = {rating.player_id for rating in candidates}
        if len(unique_ids) > 1:
            return None, f"ambiguous rating match for {player_name}: {len(unique_ids)} candidates"
        return candidates[0], ""
