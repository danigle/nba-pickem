from collections import Counter
from datetime import date, datetime, timedelta, timezone

import config
import slate
from slate import Game, Prefs

TEAMS = ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
         "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
         "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]
T0 = datetime(2026, 10, 22, 23, 0, tzinfo=timezone.utc)
PREFS = Prefs.from_dict(config.load_prefs())


def make_pool(pairs):
    return [Game(i + 1, h, a, T0 + timedelta(hours=i)) for i, (h, a) in enumerate(pairs)]


def full_week_pool():
    """30 games: every team plays twice across Thu–Sun."""
    pairs = [(TEAMS[i], TEAMS[(i + 1) % 30]) for i in range(30)]
    return make_pool(pairs)


def top_six_then_rest(top):
    return top + [t for t in TEAMS if t not in top]


def teams_in(games):
    return Counter(t for g in games for t in g.teams)


# ---------- Weeks ----------

def test_week_numbers():
    week1 = date(2026, 10, 19)
    assert slate.week_num_for(week1, date(2026, 10, 20)) == 1   # opening night
    assert slate.week_num_for(week1, date(2026, 10, 25)) == 1   # Sunday
    assert slate.week_num_for(week1, date(2026, 10, 26)) == 2   # next Monday
    assert slate.week_num_for(week1, date(2026, 10, 18)) == 0   # before season
    assert slate.week_dates(week1, 2) == (date(2026, 10, 26), date(2026, 11, 1))


def test_slate_window_is_thu_through_sun_pacific():
    start, end = slate.slate_window(date(2026, 10, 19))
    assert start == datetime(2026, 10, 22, 7, 0, tzinfo=timezone.utc)   # Thu 00:00 PDT
    assert end == datetime(2026, 10, 26, 7, 0, tzinfo=timezone.utc)     # Mon 00:00 PDT


def test_slate_window_handles_standard_time():
    start, _ = slate.slate_window(date(2026, 11, 30))
    assert start == datetime(2026, 12, 3, 8, 0, tzinfo=timezone.utc)    # Thu 00:00 PST


# ---------- Ranking ----------

def test_rank_teams_by_pct_then_wins():
    records = {"BOS": (10, 2), "SAC": (5, 1), "OKC": (12, 2)}
    ranking = slate.rank_teams(records, ["BOS", "SAC", "OKC", "ATL"])
    assert ranking == ["OKC", "BOS", "SAC", "ATL"]  # .857, .833 (10 W), .833 (5 W), 0-0


def test_lakers_top_team_only_if_top_three():
    ranking = ["OKC", "BOS", "DEN", "LAL", "CLE", "NYK", "SAC"]
    assert "LAL" not in slate.top_teams(ranking, PREFS)
    assert slate.top_teams(ranking, PREFS) == {"OKC", "BOS", "DEN", "CLE", "NYK"}
    ranking = ["OKC", "LAL", "BOS", "DEN", "CLE", "NYK"]
    assert "LAL" in slate.top_teams(ranking, PREFS)


# ---------- Slate ----------

def test_full_week_has_seven_games_no_repeats():
    games, notes = slate.pick_slate(full_week_pool(), TEAMS, PREFS, "2026-5")
    assert len(games) == 7
    assert max(teams_in(games).values()) == 1
    assert not any("Relaxed" in n for n in notes)


def test_same_seed_same_slate():
    pool = full_week_pool()
    a, _ = slate.pick_slate(pool, TEAMS, PREFS, "2026-5")
    b, _ = slate.pick_slate(list(reversed(pool)), TEAMS, PREFS, "2026-5")
    assert [g.id for g in a] == [g.id for g in b]


def test_different_seeds_differ():
    pool = full_week_pool()
    slates = {tuple(g.id for g in slate.pick_slate(pool, TEAMS, PREFS, f"2026-{w}")[0])
              for w in range(1, 10)}
    assert len(slates) > 1


def test_includes_a_top_team_game():
    ranking = top_six_then_rest(["OKC", "BOS", "DEN", "CLE", "NYK", "HOU"])
    for week in range(1, 30):
        games, _ = slate.pick_slate(full_week_pool(), ranking, PREFS, f"2026-{week}")
        assert teams_in(games).keys() & set(ranking[:6])


def test_lakers_never_in_random_fill():
    for week in range(1, 60):
        games, _ = slate.pick_slate(full_week_pool(), TEAMS, PREFS, f"2026-{week}")
        assert "LAL" not in teams_in(games)


def test_lakers_can_be_top_team_game_when_top_three():
    pool = make_pool([("LAL", "ATL"), ("BOS", "CHA"), ("CHI", "CLE"), ("DAL", "DEN"),
                      ("DET", "GSW"), ("HOU", "IND"), ("LAC", "MEM"), ("MIA", "MIL")])
    ranking = top_six_then_rest(["LAL", "OKC", "SAS", "POR", "UTA", "WAS"])  # none of the others play
    games, _ = slate.pick_slate(pool, ranking, PREFS, "2026-5")
    assert "LAL" in teams_in(games)


def test_lakers_game_not_pulled_in_by_opponent_top_team():
    # BOS is a top team but its only game is vs LAL (not top 3) → not eligible.
    pool = make_pool([("BOS", "LAL"), ("CHI", "CLE"), ("DAL", "DEN")])
    ranking = top_six_then_rest(["OKC", "SAS", "BOS", "POR", "UTA", "LAL"])
    games, notes = slate.pick_slate(pool, ranking, PREFS, "2026-5")
    assert "LAL" not in teams_in(games)
    assert "No top-team game available" in notes


def test_kings_weight_favors_kings():
    kings_weeks = 0
    for week in range(1, 201):
        games, _ = slate.pick_slate(full_week_pool(), TEAMS, PREFS, f"2026-{week}")
        kings_weeks += "SAC" in teams_in(games)
    neutral = Prefs(never_repeat=["LAL"], weights={"LAL": 0.0}, top_team_max_rank={"LAL": 3})
    neutral_weeks = sum(
        "SAC" in teams_in(slate.pick_slate(full_week_pool(), TEAMS, neutral, f"2026-{w}")[0])
        for w in range(1, 201))
    assert kings_weeks > neutral_weeks


def test_light_week_uses_every_eligible_game():
    pool = make_pool([("SAC", "BOS"), ("CHI", "CLE"), ("DAL", "DEN"), ("DET", "GSW")])
    games, notes = slate.pick_slate(pool, TEAMS, PREFS, "2026-20")
    assert len(games) == 4


def test_light_week_still_excludes_lakers():
    pool = make_pool([("LAL", "BOS"), ("CHI", "CLE"), ("DAL", "DEN")])
    games, _ = slate.pick_slate(pool, TEAMS, PREFS, "2026-20")
    assert len(games) == 2 and "LAL" not in teams_in(games)


def test_empty_week():
    games, notes = slate.pick_slate([], TEAMS, PREFS, "2026-18")
    assert games == []


def test_relaxing_prefers_kings():
    # Only 6 games avoid repeats; 7th must repeat a team. SAC is priority.
    pairs = [("ATL", "BOS"), ("CHA", "CHI"), ("CLE", "DAL"), ("DEN", "DET"),
             ("GSW", "HOU"), ("SAC", "IND"),
             ("SAC", "ATL"), ("CHA", "DEN")]
    games, notes = slate.pick_slate(make_pool(pairs), TEAMS, PREFS, "2026-9")
    assert len(games) == 7
    assert teams_in(games)["SAC"] == 2
    assert any("Relaxed" in n for n in notes)


def test_lakers_never_repeat():
    # LAL is the only top-team game (rank 1); the other LAL game can't be added.
    pairs = [("LAL", "ATL"), ("LAL", "BOS"), ("CHA", "CHI")]
    ranking = top_six_then_rest(["LAL", "OKC", "SAS", "POR", "UTA", "WAS"])
    games, _ = slate.pick_slate(make_pool(pairs), ranking, PREFS, "2026-9")
    assert teams_in(games)["LAL"] == 1
