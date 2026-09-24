"""Loads league.toml and slate_prefs.toml."""
import tomllib
from pathlib import Path

HERE = Path(__file__).parent


def load_league():
    with open(HERE / "league.toml", "rb") as f:
        return tomllib.load(f)


def load_prefs():
    with open(HERE / "slate_prefs.toml", "rb") as f:
        return tomllib.load(f)


def season_opener(league, season):
    """First regular-season game date for a season, or None if not configured."""
    return league.get("openers", {}).get(str(season))
