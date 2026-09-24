"""Minimal Supabase client: PostgREST over HTTP with the service role key.

The service key bypasses RLS. It lives in GitHub Actions secrets (or your
local shell) — never in the repo.
"""
import os

import requests

PAGE_SIZE = 1000  # Supabase's default max rows per request


class Supabase:
    def __init__(self, url=None, key=None):
        url = url or os.environ.get("SUPABASE_URL")
        key = key or os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.base = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _request(self, method, path, params=None, json=None, prefer=None):
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        resp = requests.request(method, f"{self.base}/{path}", headers=headers,
                                params=params, json=json, timeout=60)
        if not resp.ok:
            raise RuntimeError(f"{method} {path} failed ({resp.status_code}): {resp.text}")
        return resp.json() if resp.content else None

    def select(self, table, params=()):
        """All matching rows. params: list of (key, value) PostgREST filters."""
        params = list(params)
        if any(k == "limit" for k, _ in params):
            return self._request("GET", table, params)
        rows, offset = [], 0
        while True:
            page = self._request("GET", table, params + [("limit", PAGE_SIZE), ("offset", offset)])
            rows.extend(page)
            if len(page) < PAGE_SIZE:
                return rows
            offset += PAGE_SIZE

    def upsert(self, table, rows, on_conflict=None, returning=False):
        params = [("on_conflict", on_conflict)] if on_conflict else []
        prefer = "resolution=merge-duplicates," + ("return=representation" if returning else "return=minimal")
        result = []
        for i in range(0, len(rows), 500):
            out = self._request("POST", table, params, rows[i:i + 500], prefer)
            result.extend(out or [])
        return result

    def insert(self, table, rows):
        return self._request("POST", table, json=rows, prefer="return=representation")

    def update(self, table, params, values):
        return self._request("PATCH", table, params, values, "return=representation")

    def delete(self, table, params):
        return self._request("DELETE", table, params, prefer="return=representation")
