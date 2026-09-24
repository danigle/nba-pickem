"""Generate a week's slate. Runs Monday morning PT, after Sunday's games are final.

    python jobs/generate_slate.py              # this week (PT)
    python jobs/generate_slate.py --week 5     # a specific week
    python jobs/generate_slate.py --dry-run    # show the slate, write nothing
    python jobs/generate_slate.py --force      # replace an existing slate
"""
import argparse
from datetime import date, datetime

import config
import slate
from db import Supabase


def iso_z(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    league = config.load_league()
    prefs_raw = config.load_prefs()
    prefs = slate.Prefs.from_dict(prefs_raw)
    season = league["season"]
    week1 = league["week1_monday"]

    today = datetime.now(slate.PT).date()
    week_num = args.week or slate.week_num_for(week1, today)
    if week_num < 1:
        print(f"Season hasn't started (week {week_num}). Nothing to do.")
        return
    monday, sunday = slate.week_dates(week1, week_num)

    db = Supabase()
    teams = {t["id"]: t["abbreviation"] for t in db.select("teams", [("select", "id,abbreviation")])}
    unknown = prefs.team_names() - set(teams.values())
    if unknown:
        raise SystemExit(f"slate_prefs.toml has unknown teams: {sorted(unknown)}")

    last_game = db.select("games", [
        ("select", "game_date"), ("season", f"eq.{season}"), ("game_type", "eq.regular"),
        ("is_test", "eq.false"), ("order", "game_date.desc"), ("limit", 1),
    ])
    if last_game and monday > date.fromisoformat(last_game[0]["game_date"]):
        print(f"Regular season is over (week {week_num}). Nothing to do.")
        return

    # Rule 10: weeks 1–3 rank by last season's records.
    records_season = league["last_season"] if week_num <= league["use_last_season_through_week"] else season
    records = {
        teams[r["team_id"]]: (r["wins"], r["losses"])
        for r in db.select("team_records", [("season", f"eq.{records_season}")])
    }
    ranking = slate.rank_teams(records, teams.values())

    start_utc, end_utc = slate.slate_window(monday)
    rows = db.select("games", [
        ("select", "id,home_team_id,away_team_id,tipoff_utc"),
        ("season", f"eq.{season}"), ("game_type", "eq.regular"),
        ("status", "eq.scheduled"), ("is_test", "eq.false"),
        ("tipoff_utc", f"gte.{iso_z(start_utc)}"), ("tipoff_utc", f"lt.{iso_z(end_utc)}"),
    ])
    pool = [
        slate.Game(r["id"], teams[r["home_team_id"]], teams[r["away_team_id"]],
                   datetime.fromisoformat(r["tipoff_utc"]))
        for r in rows
    ]

    seed = f"{season}-{week_num}"
    chosen, notes = slate.pick_slate(pool, ranking, prefs, seed)

    print(f"Week {week_num} ({monday} – {sunday}) | seed {seed} | records from {records_season}")
    print(f"Top teams: {sorted(slate.top_teams(ranking, prefs))} | pool: {len(pool)} games")
    for g in chosen:
        print(f"  {g.tipoff_utc.astimezone(slate.PT):%a %b %d %I:%M %p} PT  {g.away} @ {g.home}")
    for n in notes:
        print(f"  note: {n}")

    if args.dry_run:
        print("Dry run: nothing written.")
        return

    existing = db.select("weeks", [("season", f"eq.{season}"), ("week_num", f"eq.{week_num}")])
    if existing and existing[0]["slate_generated_at"] and not args.force:
        raise SystemExit(f"Week {week_num} already has a slate. Use --force to replace it.")

    week = db.upsert("weeks", [{
        "season": season,
        "week_num": week_num,
        "start_date": monday.isoformat(),
        "end_date": sunday.isoformat(),
        "slate_generated_at": datetime.now(slate.PT).isoformat(),
        "slate_inputs": {
            "seed": seed,
            "records_season": records_season,
            "ranking": ranking,
            "top_teams": sorted(slate.top_teams(ranking, prefs)),
            "prefs": prefs_raw,
            "pool_size": len(pool),
            "notes": notes,
        },
    }], on_conflict="season,week_num", returning=True)[0]

    db.delete("slate_games", [("week_id", f"eq.{week['id']}")])
    if chosen:
        db.insert("slate_games", [{"week_id": week["id"], "game_id": g.id} for g in chosen])
    print(f"Saved week {week_num} slate: {len(chosen)} games")


if __name__ == "__main__":
    main()
