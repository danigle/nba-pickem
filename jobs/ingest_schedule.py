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


def build_rows(raw_games, league, team_ids):
    """Normalize balldontlie games into table rows, skipping non-NBA opponents.

    Uses each game's own season for the opener/season-end cutoffs, so it works
    for any mix of games (a full season or a few dates).
    """
    cup_final_ids = set(league.get("cup_final_game_ids", []))
    rows, skipped = [], 0
    for g in raw_games:
        row = normalize_game(g, config.season_opener(league, g["season"]), cup_final_ids,
                             config.season_end(league, g["season"]))
        if {row["home_team_id"], row["away_team_id"]} <= team_ids:
            rows.append(row)
        else:
            skipped += 1  # e.g. preseason exhibitions vs. non-NBA clubs
    return rows, skipped


def load_team_ids(db):
    team_ids = {t["id"] for t in db.select("teams", [("select", "id")])}
    if not team_ids:
        raise SystemExit("No teams loaded. Run: python jobs/ingest_teams.py")
    return team_ids


def main():
    league = config.load_league()
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=league["season"])
    args = parser.parse_args()

    api, db = BallDontLie(), Supabase()
    print(f"Fetching season {args.season}")
    rows, skipped = build_rows(api.games(season=args.season), league, load_team_ids(db))
    if skipped:
        print(f"Skipped {skipped} games with non-NBA teams")
    db.upsert("games", rows, on_conflict="id")

    by_status = Counter(r["status"] for r in rows)
    by_type = Counter(r["game_type"] for r in rows)
    missing_tipoff = sum(1 for r in rows if r["tipoff_utc"] is None and r["status"] == "scheduled")
    print(f"Upserted {len(rows)} games | status {dict(by_status)} | type {dict(by_type)}")
    regular_dates = sorted(r["game_date"] for r in rows if r["game_type"] == "regular")
    if regular_dates:
        print(f"Regular season dates: {regular_dates[0]} to {regular_dates[-1]}"
              + ("" if config.season_end(league, args.season) else " (season_ends not set in league.toml)"))
    if missing_tipoff:
        print(f"WARNING: {missing_tipoff} scheduled games have no tip-off time (can't be picked)")


if __name__ == "__main__":
    main()
