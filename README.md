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

### Supabase (~15 min)
1. Sign up at supabase.com → **New project**. Free plan; region **West US**; save the database password in your password manager. Leave the Data API enabled.
2. **SQL Editor → New query:** paste and **Run** each file in `supabase/migrations/`, in order: `001` → `002` → `003` → `004`. Each should say "Success. No rows returned."
3. **Check:** Table Editor lists 6 tables, none flagged "RLS disabled". (RLS is switched on by `004`; nothing to toggle by hand.) Security Advisor may flag the views as "Security Definer View". That's intentional: it's how the views show standings without exposing tokens.
4. **Keys:** Project Settings → API Keys. Note the project URL, the **publishable** key (or legacy anon), and the **secret** key (or legacy service_role).

### GitHub (~10 min)
5. **Secrets** (Settings → Secrets and variables → Actions → Secrets):
   `BALLDONTLIE_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (the secret key).
6. **Site config:** put the project URL and **publishable** key in `site/config.js`.
7. **Pages:** Settings → Pages → Source: **GitHub Actions**.
8. **Turn it on:** Settings → Secrets and variables → Actions → Variables → `PICKEM_ENABLED` = `true`.
   Until this exists, the scheduled jobs and the Pages deploy skip themselves.

### Data and players
9. **Load data:** Actions → **Admin** → Run workflow → `load-data` (~6 min: teams, last season, this season).
10. **Players:** in the Supabase SQL editor (keeps tokens out of public logs):
    ```sql
    insert into players (display_name) values ('Daniel'), ('Pat')
    returning display_name, 'https://danigle.github.io/nba-pickem/?t=' || access_token as link;
    ```
    Or locally: `python jobs/make_player.py "Name"` (needs the three env vars).

## Testing with fake games

Actions → **Admin** → `fake-week-create` / `fake-week-finish` / `fake-week-wipe`, or locally:

```
python jobs/fake_week.py create --start-in 30 --spacing 20   # 7 fake games, first tips in 30 min
python jobs/fake_week.py finish                               # final scores for games that tipped
python jobs/fake_week.py wipe                                 # delete all test data before launch
```

## Automatic jobs

| Job | When | What |
|---|---|---|
| **Daily scores** | Daily ~2:23 AM PT | Full season refresh: scores, statuses, reschedules. Keeps Supabase awake. |
| **Live scores** | Every 30 min, Thu–Sun nights | Same-night results for games in progress. Exits without API calls when nothing is on. |
| **Weekly slate** | Mondays ~6:37 AM PT (retries Mon ~12:37 PM, Tue ~6:37 AM) | Refresh, then generate the Thu–Sun slate. Fails loudly on missing data; a retry after success does nothing. |

- **Failures** (including GitHub failing to start a job) open a GitHub issue that @mentions the commissioner, via the separate **Failure alert** workflow (one issue per job; repeat failures add comments). Close it once fixed.
- **Timing:** GitHub can start scheduled jobs late, sometimes by hours; schedules avoid the top of the hour, which is the worst.
- Preview a slate without saving: Actions → Admin → `slate-preview`, or `python jobs/generate_slate.py --dry-run --week 1`

## Backups

**Weekly backup** (Tuesdays ~3:41 AM PT, or Actions → Weekly backup → Run workflow) commits
`players.json`, `weeks.json`, `slate_games.json` and `picks.json` to the **`backups`** branch.
Each week is a commit, so git history holds every version. Backups are public-safe: **no access
tokens**, and only picks for games that had already tipped off.

### Restoring from a backup
1. Set up a fresh Supabase project and run migrations `001`–`004` (Setup steps 1–3).
2. Run Admin → `load-data` so the teams and games exist (picks reference them).
3. Restore (locally, with the three env vars set):
   ```
   git fetch origin backups && git worktree add /tmp/bk origin/backups
   python jobs/restore.py --dir /tmp/bk
   ```
   It loads players → weeks → slate_games → picks, keeping ids, then prints two `setval` lines to
   run in the SQL editor so the id counters catch up.
4. Players get **new tokens**: `python jobs/make_player.py --list` and send everyone their new link.

## Tests

- `pytest`: slate rules, API parsing, live-score gating, backup filtering.
- **Database security tests** (`supabase/tests/security_test.sql`) run in CI on a clean Postgres 16:
  pick locks (including a game that tipped off before its status updated), hidden picks, token
  privacy and scoring.

```
pip install -r jobs/requirements-dev.txt
pytest
```
