"""Refresh scores for games that are on now (or just finished).

Runs every 30 minutes on game nights so results show up the same night
instead of after the next morning's full refresh. Does nothing (and makes no
balldontlie calls) when no game is in its live window.

    python jobs/live_scores.py
"""
from datetime import datetime, timedelta, timezone

import config
from bdl import BallDontLie
from db import Supabase
from ingest_schedule import build_rows, load_team_ids

LIVE_WINDOW = timedelta(hours=6)  # tip-off up to 6h ago and not final yet


def iso_z(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    db = Supabase()
    now = datetime.now(timezone.utc)
    live = db.select("games", [
        ("select", "id,game_date"), ("is_test", "eq.false"),
        ("status", "in.(scheduled,in_progress)"),
        ("tipoff_utc", f"gte.{iso_z(now - LIVE_WINDOW)}"),
        ("tipoff_utc", f"lte.{iso_z(now + timedelta(minutes=5))}"),
    ])
    if not live:
        print("No games in their live window. Nothing to do.")
        return

    dates = sorted({g["game_date"] for g in live})
    print(f"{len(live)} games live or just finished; refreshing {', '.join(dates)}")
    rows, _ = build_rows(BallDontLie().games(dates=dates), config.load_league(), load_team_ids(db))
    db.upsert("games", rows, on_conflict="id")
    finals = sum(1 for r in rows if r["status"] == "final")
    print(f"Upserted {len(rows)} games ({finals} final)")


if __name__ == "__main__":
    main()
