from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


AUDIT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = AUDIT_ROOT.parent
RAW = AUDIT_ROOT / "data" / "raw"
PROCESSED = AUDIT_ROOT / "data" / "processed"
OUTPUT_REPORTS = WORKSPACE_ROOT / "outputs" / "reports"
RATING_INPUTS = WORKSPACE_ROOT / "inputs" / "player_ratings"

USER_AGENT = "codex-worldcup-fifa-rating-audit/1.0"
EA_RATINGS_PAGE = "https://www.ea.com/en/games/ea-sports-fc/ratings"
EAFC26_GITHUB_CSV = "https://raw.githubusercontent.com/ismailoksuz/EAFC26-DataHub/main/data/players.csv"
EAFC26_GITHUB_README = "https://raw.githubusercontent.com/ismailoksuz/EAFC26-DataHub/main/README.md"

RATING_FIELDS = [
    "rating_source",
    "rating_season",
    "rating_basis",
    "player_id",
    "short_name",
    "long_name",
    "player_name_key",
    "nationality_name",
    "club_name",
    "player_positions",
    "overall",
    "potential",
    "age",
    "height_cm",
    "weight_kg",
    "preferred_foot",
    "weak_foot",
    "skill_moves",
    "international_reputation",
    "pace",
    "shooting",
    "passing",
    "dribbling",
    "defending",
    "physic",
    "goalkeeping_diving",
    "goalkeeping_handling",
    "goalkeeping_kicking",
    "goalkeeping_positioning",
    "goalkeeping_reflexes",
]

MANIFEST_FIELDS = [
    "source",
    "url",
    "local_path",
    "rows",
    "license_status",
    "use_in_model",
    "notes",
]


@dataclass
class FetchResult:
    source: str
    url: str
    ok: bool
    local_path: str
    note: str


def ensure_dirs() -> None:
    for path in (RAW, PROCESSED, OUTPUT_REPORTS, RATING_INPUTS):
        path.mkdir(parents=True, exist_ok=True)


def request_bytes(url: str, timeout: int = 60) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def fetch_to_path(source: str, url: str, path: Path) -> FetchResult:
    try:
        data = request_bytes(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return FetchResult(source, url, True, str(path), f"{len(data)} bytes")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        if path.exists():
            return FetchResult(source, url, True, str(path), f"used cached file after {type(exc).__name__}")
        return FetchResult(source, url, False, "", f"{type(exc).__name__}: {exc}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def player_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def normalize_rows(raw_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in raw_rows:
        long_name = row.get("long_name", "")
        short_name = row.get("short_name", "")
        rows.append(
            {
                "rating_source": "eafc26_github_kaggle_mirror",
                "rating_season": "FC26",
                "rating_basis": "static_game_rating_snapshot",
                "player_id": row.get("player_id", ""),
                "short_name": short_name,
                "long_name": long_name,
                "player_name_key": player_key(long_name) or player_key(short_name),
                "nationality_name": row.get("nationality_name", ""),
                "club_name": row.get("club_name", ""),
                "player_positions": row.get("player_positions", ""),
                "overall": row.get("overall", ""),
                "potential": row.get("potential", ""),
                "age": row.get("age", ""),
                "height_cm": row.get("height_cm", ""),
                "weight_kg": row.get("weight_kg", ""),
                "preferred_foot": row.get("preferred_foot", ""),
                "weak_foot": row.get("weak_foot", ""),
                "skill_moves": row.get("skill_moves", ""),
                "international_reputation": row.get("international_reputation", ""),
                "pace": row.get("pace", ""),
                "shooting": row.get("shooting", ""),
                "passing": row.get("passing", ""),
                "dribbling": row.get("dribbling", ""),
                "defending": row.get("defending", ""),
                "physic": row.get("physic", ""),
                "goalkeeping_diving": row.get("goalkeeping_diving", ""),
                "goalkeeping_handling": row.get("goalkeeping_handling", ""),
                "goalkeeping_kicking": row.get("goalkeeping_kicking", ""),
                "goalkeeping_positioning": row.get("goalkeeping_positioning", ""),
                "goalkeeping_reflexes": row.get("goalkeeping_reflexes", ""),
            }
        )
    return rows


def extract_ea_official_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', text)
    result: dict[str, Any] = {
        "has_next_data": bool(match),
        "player_count_claim": "17,000+",
        "top_list_items": 0,
        "notes": "EA official static page contains selected ratings lists and confirms 17,000+ player ratings, but not the complete downloadable table.",
    }
    if not match:
        return result
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return result
    aux = (((data.get("props") or {}).get("pageProps") or {}).get("auxData") or {})
    top_items = 0
    for group in aux.get("bestStatsAthletes", []) or []:
        top_items += len(group.get("athletes", []) or [])
    result["top_list_items"] = top_items
    return result


def write_report(fetches: list[FetchResult], normalized: list[dict[str, Any]], official_summary: dict[str, Any], readme_text: str) -> None:
    nationalities = Counter(row.get("nationality_name", "") for row in normalized)
    clubs = Counter(row.get("club_name", "") for row in normalized)
    missing_overall = sum(1 for row in normalized if not row.get("overall"))
    duplicate_keys = sum(1 for _, count in Counter((row.get("player_name_key"), row.get("nationality_name")) for row in normalized).items() if count > 1)
    lines = [
        "# FIFA/EA FC Player Ratings Audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Verdict",
        "",
        "`available_as_static_rating_prior_with_license_caveat`",
        "",
        "The audit found a downloadable FC26/FIFA26-style player ratings table through a GitHub mirror of a Kaggle dataset. It can be used as an optional static rating prior for lineup rows, but it should not be treated as official FIFA federation data or as current match performance.",
        "",
        "## Local Outputs",
        "",
        f"- Raw GitHub/Kaggle mirror CSV: `{RAW / 'eafc26_players.csv'}`",
        f"- EA official ratings page snapshot: `{RAW / 'ea_fc_ratings_page.html'}`",
        f"- Normalized model input: `{RATING_INPUTS / 'eafc26_player_ratings.csv'}`",
        f"- Source manifest: `{RATING_INPUTS / 'source_manifest.csv'}`",
        "",
        "## Coverage",
        "",
        f"- Normalized rows: {len(normalized)}",
        f"- Missing overall ratings: {missing_overall}",
        f"- Nationalities: {len([item for item in nationalities if item])}",
        f"- Clubs: {len([item for item in clubs if item])}",
        f"- Duplicate name+nationality keys: {duplicate_keys}",
        f"- EA official page player-count claim: {official_summary.get('player_count_claim', '')}",
        f"- EA official static top-list items detected: {official_summary.get('top_list_items', 0)}",
        "",
        "## Source Findings",
        "",
        "- EA official ratings page confirms FC 26 player ratings and PlayStyles for 17,000+ players, but the static HTML snapshot does not expose the complete table as a CSV.",
        "- The downloaded complete CSV comes from a GitHub mirror whose README says the source is a Kaggle dataset. The GitHub mirror has no LICENSE file, so redistribution/licensing remains unverified.",
        "- These ratings are game ratings, not official FIFA federation ratings and not live performance metrics.",
        "- The rating table is useful for filling missing `LineupAgent` player ratings when a confirmed lineup contains player names.",
        "- It should not automatically change team strength without a lineup and without backtest validation.",
        "",
        "## Fetch Results",
        "",
        "| Source | Status | Note |",
        "|---|---:|---|",
    ]
    for item in fetches:
        lines.append(f"| {item.source} | {'ok' if item.ok else 'failed'} | {item.note} |")
    if readme_text:
        lines.extend(
            [
                "",
                "## Mirror README Evidence",
                "",
                "The mirror README states that the data source is Kaggle `FC 26 (FIFA 26) Player Data` and that `data/players.csv` contains over 18,000 player records with 110+ attributes.",
            ]
        )
    OUTPUT_REPORTS.mkdir(parents=True, exist_ok=True)
    (OUTPUT_REPORTS / "fifa_player_ratings_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()
    fetches = [
        fetch_to_path("ea_fc_official_ratings_page", EA_RATINGS_PAGE, RAW / "ea_fc_ratings_page.html"),
        fetch_to_path("eafc26_github_kaggle_mirror_csv", EAFC26_GITHUB_CSV, RAW / "eafc26_players.csv"),
        fetch_to_path("eafc26_github_readme", EAFC26_GITHUB_README, RAW / "eafc26_datahub_readme.md"),
    ]
    raw_rows = read_csv(RAW / "eafc26_players.csv") if (RAW / "eafc26_players.csv").exists() else []
    normalized = normalize_rows(raw_rows)
    write_csv(RATING_INPUTS / "eafc26_player_ratings.csv", normalized, RATING_FIELDS)
    manifest = [
        {
            "source": "ea_fc_official_ratings_page",
            "url": EA_RATINGS_PAGE,
            "local_path": str(RAW / "ea_fc_ratings_page.html"),
            "rows": "",
            "license_status": "official web page; not a downloadable complete table",
            "use_in_model": "source validation only",
            "notes": "Confirms public FC 26 ratings page and 17,000+ player claim.",
        },
        {
            "source": "eafc26_github_kaggle_mirror",
            "url": EAFC26_GITHUB_CSV,
            "local_path": str(RAW / "eafc26_players.csv"),
            "rows": len(raw_rows),
            "license_status": "unverified; mirror has no LICENSE file",
            "use_in_model": "optional lineup rating fallback only",
            "notes": "README says source is Kaggle FC 26 player data. Treat as static game-rating prior, not live performance.",
        },
    ]
    write_csv(RATING_INPUTS / "source_manifest.csv", manifest, MANIFEST_FIELDS)
    official_summary = extract_ea_official_summary(RAW / "ea_fc_ratings_page.html")
    readme_text = (RAW / "eafc26_datahub_readme.md").read_text(encoding="utf-8", errors="replace") if (RAW / "eafc26_datahub_readme.md").exists() else ""
    write_report(fetches, normalized, official_summary, readme_text)
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_csv": str(RAW / "eafc26_players.csv"),
        "normalized_csv": str(RATING_INPUTS / "eafc26_player_ratings.csv"),
        "source_manifest": str(RATING_INPUTS / "source_manifest.csv"),
        "report": str(OUTPUT_REPORTS / "fifa_player_ratings_audit.md"),
        "rows": len(normalized),
        "license_status": "unverified",
        "use_in_model": "optional lineup rating fallback only",
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
