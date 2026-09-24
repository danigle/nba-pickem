from datetime import date, datetime, timezone

import bdl


def game(**overrides):
    g = {
        "id": 101, "season": 2026, "date": "2026-10-22", "datetime": None,
        "status": "2026-10-23T02:00:00Z", "period": 0, "postseason": False,
        "home_team": {"id": 26}, "visitor_team": {"id": 14},
        "home_team_score": 0, "visitor_team_score": 0,
    }
    g.update(overrides)
    return g


def test_scheduled_game_iso_status():
    row = bdl.normalize_game(game(), season_opener=date(2026, 10, 20))
    assert row["status"] == "scheduled"
    assert row["tipoff_utc"] == "2026-10-23T02:00:00+00:00"
    assert row["game_type"] == "regular"
    assert row["home_score"] is None


def test_datetime_field_preferred():
    row = bdl.normalize_game(game(datetime="2026-10-23T02:30:00.000Z"))
    assert row["tipoff_utc"] == "2026-10-23T02:30:00+00:00"


def test_et_clock_status():
    row = bdl.normalize_game(game(status="7:30 pm ET"))
    assert row["status"] == "scheduled"
    assert row["tipoff_utc"] == "2026-10-22T23:30:00+00:00"  # 7:30 pm EDT


def test_final_game():
    row = bdl.normalize_game(game(status="Final", period=4,
                                  home_team_score=110, visitor_team_score=99))
    assert row["status"] == "final"
    assert (row["home_score"], row["away_score"]) == (110, 99)


def test_in_progress():
    assert bdl.normalize_game(game(status="3rd Qtr", period=3))["status"] == "in_progress"


def test_postponed():
    assert bdl.normalize_game(game(status="Postponed"))["status"] == "postponed"


def test_game_types():
    assert bdl.normalize_game(game(postseason=True))["game_type"] == "postseason"
    assert bdl.normalize_game(game(date="2026-10-05"),
                              season_opener=date(2026, 10, 20))["game_type"] == "preseason"
    assert bdl.normalize_game(game(), cup_final_ids={101})["game_type"] == "cup_final"


def test_historical_teams_skipped():
    assert bdl.normalize_team({"id": 37, "conference": " ", "abbreviation": "CHS",
                               "city": "Chicago", "name": "Stags", "full_name": "Chicago Stags"}) is None
    assert bdl.normalize_team({"id": 26, "conference": "West", "abbreviation": "SAC",
                               "city": "Sacramento", "name": "Kings",
                               "full_name": "Sacramento Kings"})["abbreviation"] == "SAC"
