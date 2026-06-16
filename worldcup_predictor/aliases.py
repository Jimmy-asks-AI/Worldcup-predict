from __future__ import annotations

import unicodedata


ALIASES = {
    "cabo verde": "Cape Verde",
    "cape verde": "Cape Verde",
    "bosnia and herzegovina": "Bosnia and Herzegovina",
    "cote d'ivoire": "Ivory Coast",
    "côte d'ivoire": "Ivory Coast",
    "ivory coast": "Ivory Coast",
    "congo dr": "Democratic Republic of the Congo",
    "dr congo": "Democratic Republic of the Congo",
    "democratic republic of congo": "Democratic Republic of the Congo",
    "democratic republic of the congo": "Democratic Republic of the Congo",
    "new zealand": "New Zealand",
    "saudi arabia": "Saudi Arabia",
    "curacao": "Curaçao",
    "curaçao": "Curaçao",
    "czechia": "Czech Republic",
    "czech republic": "Czech Republic",
    "ir iran": "Iran",
    "iran": "Iran",
    "korea republic": "South Korea",
    "south korea": "South Korea",
    "turkiye": "Turkey",
    "türkiye": "Turkey",
    "turkey": "Turkey",
    "usa": "United States",
    "united states": "United States",
    "u.s.a.": "United States",
}


def _key(name: str) -> str:
    text = unicodedata.normalize("NFKD", (name or "").strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.replace("’", "'").lower().split())


def normalize_team(name: str) -> str:
    key = _key(name)
    if not key:
        return ""
    return ALIASES.get(key, " ".join(part.capitalize() for part in key.split()))
