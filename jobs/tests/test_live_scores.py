import live_scores


class FakeDb:
    def __init__(self, live):
        self.live, self.upserts, self.queries = live, [], []

    def select(self, table, params=()):
        self.queries.append((table, list(params)))
        return self.live if table == "games" else [{"id": 1}, {"id": 2}]

    def upsert(self, table, rows, on_conflict=None):
        self.upserts.append((table, rows))


class FakeApi:
    calls = []

    def games(self, dates=None, season=None):
        FakeApi.calls.append(dates)
        return [{"id": 7, "season": 2026, "date": "2026-10-24", "status": "Final", "period": 4,
                 "home_team": {"id": 1}, "visitor_team": {"id": 2},
                 "home_team_score": 101, "visitor_team_score": 99}]


def run(monkeypatch, live):
    db = FakeDb(live)
    FakeApi.calls = []
    monkeypatch.setattr(live_scores, "Supabase", lambda: db)
    monkeypatch.setattr(live_scores, "BallDontLie", FakeApi)
    live_scores.main()
    return db


def test_no_live_games_means_no_api_calls(monkeypatch):
    db = run(monkeypatch, live=[])
    assert FakeApi.calls == [] and db.upserts == []


def test_live_games_refresh_their_dates(monkeypatch):
    db = run(monkeypatch, live=[{"id": 7, "game_date": "2026-10-24"}, {"id": 8, "game_date": "2026-10-24"}])
    assert FakeApi.calls == [["2026-10-24"]]          # one date, fetched once
    (table, rows), = db.upserts
    assert table == "games" and rows[0]["status"] == "final"


def test_live_window_query_excludes_test_and_final_games(monkeypatch):
    db = run(monkeypatch, live=[])
    params = dict(db.queries[0][1][:3])
    assert params["is_test"] == "eq.false" and params["status"] == "in.(scheduled,in_progress)"
