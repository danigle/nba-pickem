"""Load a backup (from the `backups` branch) into a fresh database.

Run AFTER the migrations and `load-data` (picks and slates reference games).
Players get new access tokens, so send everyone a new link afterwards
(`python jobs/make_player.py --list`).

    git fetch origin backups && git worktree add /tmp/bk origin/backups
    python jobs/restore.py --dir /tmp/bk

Then reset the id counters in the Supabase SQL editor (printed at the end).
"""
import argparse
import json
from pathlib import Path

from db import Supabase

ORDER = [  # parents before children
    ("players", "id", lambda r: {"id": r["id"], "display_name": r["display_name"]}),
    ("weeks", "id", lambda r: r),
    ("slate_games", "week_id,game_id", lambda r: r),
    ("picks", "player_id,game_id", lambda r: r),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()
    db = Supabase()
    for table, key, shape in ORDER:
        rows = [shape(r) for r in json.loads((Path(args.dir) / f"{table}.json").read_text())]
        if rows:
            db.upsert(table, rows, on_conflict=key)
        print(f"{table}: restored {len(rows)} rows")
    print("\nNow run in the Supabase SQL editor so new players/weeks get fresh ids:\n"
          "  select setval('players_id_seq', (select coalesce(max(id), 1) from players));\n"
          "  select setval('weeks_id_seq', (select coalesce(max(id), 1) from weeks));")


if __name__ == "__main__":
    main()
