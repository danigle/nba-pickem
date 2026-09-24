# NBA Pick'em

A $0 pick'em league for friends. Each week there are 7 Thu–Sun regular-season games, picked straight up, 1 point each.
The project brief and rules are in [`CLAUDE.md`](CLAUDE.md).

## Layout

| Path | What |
|---|---|
| `supabase/migrations/` | Database: tables, views, pick functions, security. Run in order. |
| `jobs/` | Python jobs: load teams and games, generate slates, add players, fake test weeks |
| `jobs/league.toml` | Season settings (season, week 1 Monday, site URL, Cup Final ids) |
| `jobs/slate_prefs.toml` | Commissioner preferences (Kings 2.0, Lakers 0, …) |
| `site/` | Static website: My Picks, Weekly Picks, Standings |
| `.github/workflows/` | Daily scores, Monday slate, Pages deploy, tests |

## Setup (one time)

1. **Supabase:** create a free project. In the SQL editor, run `supabase/migrations/001` → `004` in order.
2. **balldontlie:** create a free account and copy the API key.
3. **GitHub secrets** (Settings → Secrets and variables → Actions → Secrets):
   `BALLDONTLIE_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (the service_role key).
4. **Site config:** put the project URL and **anon** key in `site/config.js`.
5. **GitHub Pages:** Settings → Pages → Source: **GitHub Actions**.
6. **Turn it on:** Settings → Secrets and variables → Actions → Variables → add `PICKEM_ENABLED` = `true`.
   Until this exists, the scheduled jobs and the Pages deploy skip themselves.
7. **Load data** (locally, with the three env vars set, or via the workflows' "Run workflow" button):
   ```
   pip install -r jobs/requirements.txt
   python jobs/ingest_teams.py
   python jobs/ingest_schedule.py --season 2025   # last season (weeks 1–3 rankings)
   python jobs/ingest_schedule.py                 # this season
   ```
8. **Players:** `python jobs/make_player.py "Name"` prints the private link to send.

## Testing with fake games

```
python jobs/fake_week.py create --start-in 30 --spacing 20   # 7 fake games, first tips in 30 min
python jobs/fake_week.py finish                               # final scores for games that tipped
python jobs/fake_week.py wipe                                 # delete all test data before launch
```

## Weekly (automatic)

- **Daily 10:00 UTC:** refreshes scores and the schedule.
- **Monday 14:00 UTC:** refreshes, then generates the Thu–Sun slate.
- Preview a slate without saving it: `python jobs/generate_slate.py --dry-run --week 1`

## Tests

```
pip install -r jobs/requirements-dev.txt
pytest
```
