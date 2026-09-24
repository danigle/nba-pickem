"""Load or refresh every game for a season: schedule, tip-offs, scores, status.

Runs daily in-season (a full refresh is ~13 API calls, ~3 minutes), which
also picks up reschedules and keeps Supabase from pausing.

    python jobs/ingest_schedule.py               # current season
    python jobs/ingest_schedule.py --season 2025 # last season (for weeks 1–3)
"""
import argparse
from collections import Counter

import config
from bdl import BallDontLie, normalize_game
from db import Supabase


def main():
    league = config.load_league()
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=league["season"])
    args = parser.parse_args()

    api, db = BallDontLie(), Supabase()
    opener = config.season_opener(league, args.season)
    cup_final_ids = set(league.get("cup_final_game_ids", []))

    print(f"Fetching season {args.season}")
    team_ids = {t["id"] for t in db.select("teams", [("select", "id")])}
    if not team_ids:
        raise SystemExit("No teams loaded. Run: python jobs/ingest_teams.py")
    rows = [normalize_game(g, opener, cup_final_ids) for g in api.games(args.season)]

    # Skip games involving non-NBA teams (e.g. preseason exhibitions).
    skipped = [r for r in rows if not {r["home_team_id"], r["away_team_id"]} <= team_ids]
    rows = [r for r in rows if r not in skipped]
    if skipped:
        print(f"Skipped {len(skipped)} games with non-NBA teams")
    db.upsert("games", rows, on_conflict="id")

    by_status = Counter(r["status"] for r in rows)
    by_type = Counter(r["game_type"] for r in rows)
    missing_tipoff = sum(1 for r in rows if r["tipoff_utc"] is None and r["status"] == "scheduled")
    print(f"Upserted {len(rows)} games | status {dict(by_status)} | type {dict(by_type)}")
    if missing_tipoff:
        print(f"WARNING: {missing_tipoff} scheduled games have no tip-off time (can't be picked)")


if __name__ == "__main__":
    main()
