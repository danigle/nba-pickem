"""Fake games for testing with friends before the real season.

Test data uses season 0, negative game ids, and is_test = true, so it never
touches real records or standings.

    python jobs/fake_week.py create                 # 7 games, first tips in 60 min
    python jobs/fake_week.py create --start-in 10 --spacing 15
    python jobs/fake_week.py finish                 # final scores for tipped-off games
    python jobs/fake_week.py wipe                   # delete ALL test data (before launch)
"""
import argparse
import random
from datetime import datetime, timedelta, timezone

from db import Supabase
from slate import PT


def create(db, n_games, start_in, spacing):
    teams = [t["id"] for t in db.select("teams", [("select", "id")])]
    if len(teams) < n_games * 2:
        raise SystemExit("Load teams first: python jobs/ingest_teams.py")
    picked = random.sample(teams, n_games * 2)

    lowest = db.select("games", [("select", "id"), ("order", "id.asc"), ("limit", 1)])
    next_id = min(lowest[0]["id"], 0) - 1 if lowest else -1

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    games = []
    for i in range(n_games):
        tip = now + timedelta(minutes=start_in + i * spacing)
        games.append({
            "id": next_id - i,
            "season": 0,
            "game_date": tip.astimezone(PT).date().isoformat(),
            "tipoff_utc": tip.isoformat(),
            "home_team_id": picked[2 * i],
            "away_team_id": picked[2 * i + 1],
            "status": "scheduled",
            "game_type": "regular",
            "is_test": True,
        })
    db.insert("games", games)

    last_week = db.select("weeks", [("select", "week_num"), ("season", "eq.0"),
                                    ("order", "week_num.desc"), ("limit", 1)])
    today = datetime.now(PT).date()
    last_tip = max(g["tipoff_utc"] for g in games)
    end = max(today + timedelta(days=6), datetime.fromisoformat(last_tip).astimezone(PT).date())
    week = db.insert("weeks", [{
        "season": 0,
        "week_num": last_week[0]["week_num"] + 1 if last_week else 1,
        "start_date": today.isoformat(),
        "end_date": end.isoformat(),
        "slate_generated_at": datetime.now(timezone.utc).isoformat(),
        "slate_inputs": {"test": True},
        "is_test": True,
    }])[0]
    db.insert("slate_games", [{"week_id": week["id"], "game_id": g["id"]} for g in games])
    print(f"Created test week {week['week_num']} with {n_games} games, "
          f"first tip-off {games[0]['tipoff_utc']}")


def finish(db):
    now = datetime.now(timezone.utc).isoformat()
    games = db.select("games", [("is_test", "eq.true"), ("status", "eq.scheduled"),
                                ("tipoff_utc", f"lte.{now}")])
    for g in games:
        home, away = random.sample(range(95, 131), 2)  # distinct → no ties
        db.update("games", [("id", f"eq.{g['id']}")],
                  {"home_score": home, "away_score": away, "status": "final"})
    print(f"Finished {len(games)} test games")


def wipe(db):
    weeks = db.delete("weeks", [("is_test", "eq.true")])
    games = db.delete("games", [("is_test", "eq.true")])  # cascades to picks + slate_games
    print(f"Deleted {len(weeks)} test weeks and {len(games)} test games (and their picks)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "finish", "wipe"])
    parser.add_argument("--games", type=int, default=7)
    parser.add_argument("--start-in", type=int, default=60, help="minutes until first tip-off")
    parser.add_argument("--spacing", type=int, default=30, help="minutes between tip-offs")
    args = parser.parse_args()

    db = Supabase()
    if args.action == "create":
        create(db, args.games, args.start_in, args.spacing)
    elif args.action == "finish":
        finish(db)
    else:
        wipe(db)


if __name__ == "__main__":
    main()
