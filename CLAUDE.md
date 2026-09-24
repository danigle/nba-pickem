# NBA Pick'em — Project Brief

## What This Is
A simple, $0 NBA pick'em league for a small group of friends (2–5 players, maybe more).
Each week, 7 NBA games are selected automatically. Players pick straight-up winners.
The system scores picks and tracks weekly + season standings with zero commissioner work.

Priority: **ease of use** over features. Friends-first; build clean enough to grow later.

## Hard Deadline
2026–27 NBA regular season opens **Tuesday, Oct 20, 2026**. Target a working V1 by then.
Preseason (starts Oct 3) is the test window.

## Locked Decisions
- **Week:** Monday–Sunday (use America/Los_Angeles for week boundaries)
- **Slate size:** 7 games per week
- **Pick type:** straight-up winner only (no spreads, no confidence points)
- **Scoring:** 1 point per correct pick
- **Lock:** each pick locks at that game's tip-off
- **Budget:** $0 (free tiers only)

## Slate Selection Rules
1. Pull all games Mon–Sun for the upcoming week
2. Rank teams by win % → "top teams" = top 6 (placeholder, easy to change)
3. Include at least 1 game featuring a top team
4. Fill the remaining 6 at random
5. No team appears twice in one week
6. Seeded random (seed = season + week number) so any slate can be regenerated
7. Generate Sunday night before Monday's first tip
8. Weeks 1–3: use LAST season's final records; after that, current records

## Stack ($0)
| Layer | Tool |
|---|---|
| Database | Supabase Free (Postgres) |
| NBA data | balldontlie API, free tier (Teams + Games endpoints only) |
| Scheduled jobs | GitHub Actions cron (Python) |
| Front end | Static site on GitHub Pages, mobile-first |

## Constraints & Gotchas
- **balldontlie free tier:** ~5 req/min; API key required in `Authorization` header (no Bearer). Standings endpoint is PAID — compute W-L ourselves from the Games table.
- **Supabase free tier:** pauses after ~7 days of inactivity. The daily results job keeps it awake in-season.
- **Pick locks MUST be enforced in the database** (RLS policy or Postgres function comparing now() to tip-off), never only in the UI.
- **No logins.** Each player gets a private link with a unique token. Proper auth only if this grows.
- Secrets (API key, Supabase service key) live in GitHub Actions secrets, never in the repo.
- Verify balldontlie's game object includes a usable tip-off datetime before building lock logic.

## Data Model (starting sketch)
- `teams` (id, name, abbreviation)
- `games` (id, season, game_date, tipoff_utc, home_team_id, away_team_id, home_score, away_score, status)
- `weeks` (id, season, week_num, start_date, end_date)
- `slate_games` (week_id, game_id)
- `players` (id, display_name, access_token)
- `picks` (player_id, game_id, picked_team_id, created_at) — unique(player_id, game_id)
- views: `team_records`, `weekly_standings`, `season_standings`

## Build Order
1. Supabase schema + lock policy
2. Python ingestion job: teams, full-season schedule, daily score updates
3. Slate generator (Python), runs Sunday night
4. Pick page: view this week's 7 games, tap a team, see locked state
5. Standings page: weekly + season
6. Preseason test with friends; fix what breaks

## Out of Scope for V1
Spreads, confidence points, tiebreakers, chat, native app, multiple leagues, public signup, AI features.

## Working Style
- Owner: Daniel. Comfortable with SQL and Python; prefers direct, concise explanations.
- Keep code simple and readable over clever.
- Ask before adding dependencies or anything that could cost money.
