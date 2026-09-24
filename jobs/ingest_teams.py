"""Load the 30 NBA teams. Run once (safe to re-run).

    python jobs/ingest_teams.py
"""
from bdl import BallDontLie, normalize_team
from db import Supabase


def main():
    api, db = BallDontLie(), Supabase()
    rows = [r for r in map(normalize_team, api.teams()) if r]
    db.upsert("teams", rows, on_conflict="id")
    print(f"Upserted {len(rows)} teams")
    if len(rows) != 30:
        print(f"WARNING: expected 30 teams, got {len(rows)}")


if __name__ == "__main__":
    main()
