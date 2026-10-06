import sys

import generate_slate


class FakeDb:
    def __init__(self):
        self.calls = []

    def select(self, table, params=()):
        self.calls.append(table)
        if table == "weeks":
            return [{"id": 3, "slate_generated_at": "2026-10-19T06:40:00-07:00"}]
        raise AssertionError(f"should not read {table} once the slate exists")

    def upsert(self, *a, **k):
        raise AssertionError("must not write")

    insert = delete = upsert


def test_rerun_with_existing_slate_is_a_quiet_success(monkeypatch, capsys):
    db = FakeDb()
    monkeypatch.setattr(generate_slate, "Supabase", lambda: db)
    monkeypatch.setattr(sys, "argv", ["generate_slate.py", "--week", "1"])
    generate_slate.main()  # no SystemExit
    assert db.calls == ["weeks"]
    assert "already has a slate" in capsys.readouterr().out
