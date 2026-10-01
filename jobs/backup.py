"""Export the data that can't be rebuilt from balldontlie: players, weeks,
slates, and picks. Writes one JSON file per table.

PUBLIC-SAFE ON PURPOSE (the backups branch is public): no access tokens, and
only picks for games that have tipped off, which the site already shows.
Test data is skipped. Games themselves are rebuilt by load-data.

    python jobs/backup.py --out backup/
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from db import Supabase


def locked_picks(picks, games, now):
    """Picks for real games that have tipped off (unlocked picks stay secret)."""
    tipped = {
        g["id"] for g in games
        if not g["is_test"] and g["tipoff_utc"]
        and datetime.fromisoformat(g["tipoff_utc"]) <= now
    }
    return [p for p in picks if p["game_id"] in tipped]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="backup")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    db = Supabase()
    now = datetime.now(timezone.utc)
    weeks = db.select("weeks", [("is_test", "eq.false"), ("order", "id")])
    week_ids = {w["id"] for w in weeks}
    games = db.select("games", [("select", "id,tipoff_utc,is_test")])
    tables = {
        "players": db.select("players", [("select", "id,display_name,created_at"), ("order", "id")]),
        "weeks": weeks,
        "slate_games": [s for s in db.select("slate_games", [("order", "week_id,game_id")])
                        if s["week_id"] in week_ids],
        "picks": locked_picks(db.select("picks", [("order", "player_id,game_id")]), games, now),
    }
    for name, rows in tables.items():
        (out / f"{name}.json").write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
        print(f"{name}: {len(rows)} rows")
    (out / "README.md").write_text(
        f"NBA Pick'em backup, {now:%Y-%m-%d %H:%M} UTC.\n\n"
        "No access tokens, and only picks for games that had tipped off.\n"
        "Restore steps: see the main branch README, \"Restoring from a backup\".\n")


if __name__ == "__main__":
    main()
