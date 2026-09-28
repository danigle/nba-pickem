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

## Weekly (automatic)

- **Daily 10:00 UTC:** refreshes scores and the schedule.
- **Monday 14:00 UTC:** refreshes, then generates the Thu–Sun slate.
- Preview a slate without saving it: `python jobs/generate_slate.py --dry-run --week 1`

## Tests

```
pip install -r jobs/requirements-dev.txt
pytest
```
