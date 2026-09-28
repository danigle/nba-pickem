"""Confirm the GitHub secrets work. Prints no secret values.

    python jobs/check_connection.py
"""
import os

import requests

from bdl import BASE_URL
from db import Supabase


def main():
    ok = True

    try:
        db = Supabase()
        teams = db.select("teams", [("select", "id")])
        players = db.select("players", [("select", "id")])
        print(f"Supabase: OK ({len(teams)} teams, {len(players)} players)")
    except (SystemExit, Exception) as e:
        ok = False
        print(f"Supabase: FAILED - {e}")

    key = os.environ.get("BALLDONTLIE_API_KEY")
    if not key:
        print("balldontlie: key not set yet (skipped)")
    else:
        resp = requests.get(f"{BASE_URL}/teams", headers={"Authorization": key}, timeout=30)
        if resp.ok:
            print(f"balldontlie: OK ({len(resp.json()['data'])} teams returned)")
        else:
            ok = False
            print(f"balldontlie: FAILED - HTTP {resp.status_code}")

    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
