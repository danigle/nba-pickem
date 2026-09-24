"""Add a player and print their private link (send it by text or Discord).

    python jobs/make_player.py "Daniel"
    python jobs/make_player.py --list      # reprint everyone's links
"""
import argparse
import secrets

import config
from db import Supabase


def link(site_url, token):
    return f"{site_url.rstrip('/')}/?t={token}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    site_url = config.load_league()["site_url"]
    db = Supabase()

    if args.list:
        for p in db.select("players", [("select", "display_name,access_token"), ("order", "display_name")]):
            print(f"{p['display_name']}: {link(site_url, p['access_token'])}")
        return

    if not args.name:
        parser.error("give a player name, or --list")

    player = db.insert("players", [{
        "display_name": args.name.strip(),
        "access_token": secrets.token_urlsafe(16),
    }])[0]
    print(f"{player['display_name']}: {link(site_url, player['access_token'])}")


if __name__ == "__main__":
    main()
