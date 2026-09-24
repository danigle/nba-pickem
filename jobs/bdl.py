"""balldontlie API client (free tier: Teams + Games, ~5 requests/minute)."""
import os
import re
import time
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import requests

BASE_URL = "https://api.balldontlie.io/v1"
SECONDS_BETWEEN_CALLS = 13  # stays under 5/minute
ET = ZoneInfo("America/New_York")


class BallDontLie:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("BALLDONTLIE_API_KEY")
        if not self.api_key:
            raise SystemExit("BALLDONTLIE_API_KEY is not set")
        self._last_call = 0.0

    def _get(self, path, params=None):
        for _ in range(5):
            wait = self._last_call + SECONDS_BETWEEN_CALLS - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            resp = requests.get(
                BASE_URL + path,
                headers={"Authorization": self.api_key},  # no "Bearer"
                params=params,
                timeout=30,
            )
            if resp.status_code == 429:
                print("Rate limited; waiting 60s")
                time.sleep(60)
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"Gave up on {path} after repeated rate limits")

    def teams(self):
        return self._get("/teams")["data"]

    def games(self, season):
        """All games for a season (follows cursor pagination)."""
        games, cursor = [], None
        while True:
            params = {"seasons[]": season, "per_page": 100}
            if cursor:
                params["cursor"] = cursor
            page = self._get("/games", params)
            games.extend(page["data"])
            cursor = page.get("meta", {}).get("next_cursor")
            print(f"  fetched {len(games)} games")
            if not cursor:
                return games


# ---------- Normalizing API objects into table rows ----------

def normalize_team(t):
    """Row for the teams table, or None for historical franchises (no conference)."""
    if not t.get("conference", "").strip():
        return None
    return {
        "id": t["id"],
        "abbreviation": t["abbreviation"],
        "city": t["city"],
        "name": t["name"],
        "full_name": t["full_name"],
    }


def _parse_iso(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _parse_et_clock(status, game_date):
    """'7:30 pm ET' on a given date → UTC datetime."""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})\s*([ap]m)\s*ET", status.strip(), re.IGNORECASE)
    if not m:
        return None
    hour = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0)
    local = datetime.combine(game_date, datetime.min.time(), ET).replace(hour=hour, minute=int(m.group(2)))
    return local.astimezone(timezone.utc)


def parse_tipoff(g):
    """Best available tip-off time (UTC), or None.

    Tries the `datetime` field, then an ISO timestamp in `status`, then
    '7:30 pm ET' in `status`. VERIFY against live data once we have a key.
    """
    game_date = date.fromisoformat(g["date"][:10])
    status = g.get("status") or ""
    return (_parse_iso(g.get("datetime"))
            or _parse_iso(status)
            or _parse_et_clock(status, game_date))


def parse_status(g):
    raw = (g.get("status") or "").strip()
    lower = raw.lower()
    if lower == "final":
        return "final"
    if "postpon" in lower or "cancel" in lower:
        return "postponed"
    if not raw or _parse_iso(raw) or lower.endswith(" et") or not g.get("period"):
        return "scheduled"
    return "in_progress"


def normalize_game(g, season_opener=None, cup_final_ids=()):
    """Row for the games table."""
    status = parse_status(g)
    tipoff = parse_tipoff(g)
    game_date = g["date"][:10]

    if g["id"] in cup_final_ids:
        game_type = "cup_final"
    elif g.get("postseason"):
        game_type = "postseason"
    elif season_opener and game_date < season_opener.isoformat():
        game_type = "preseason"
    else:
        game_type = "regular"

    started = status in ("final", "in_progress")
    return {
        "id": g["id"],
        "season": g["season"],
        "game_date": game_date,
        "tipoff_utc": tipoff.isoformat() if tipoff else None,
        "home_team_id": g["home_team"]["id"],
        "away_team_id": g["visitor_team"]["id"],
        "home_score": g.get("home_team_score") if started else None,
        "away_score": g.get("visitor_team_score") if started else None,
        "status": status,
        "game_type": game_type,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
