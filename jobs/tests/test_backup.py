from datetime import datetime, timezone

from backup import locked_picks

NOW = datetime(2026, 10, 24, 3, 0, tzinfo=timezone.utc)
GAMES = [
    {"id": 1, "tipoff_utc": "2026-10-23T02:00:00+00:00", "is_test": False},  # tipped off
    {"id": 2, "tipoff_utc": "2026-10-25T02:00:00+00:00", "is_test": False},  # still open
    {"id": -1, "tipoff_utc": "2026-10-20T02:00:00+00:00", "is_test": True},  # test data
    {"id": 3, "tipoff_utc": None, "is_test": False},                         # no time yet
]
PICKS = [{"player_id": 1, "game_id": g} for g in (1, 2, -1, 3)]


def test_only_real_tipped_off_picks_are_backed_up():
    assert [p["game_id"] for p in locked_picks(PICKS, GAMES, NOW)] == [1]
