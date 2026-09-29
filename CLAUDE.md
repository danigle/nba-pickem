# NBA Pick'em — Project Brief

## What This Is
A simple, $0 NBA pick'em league for a small group of friends (2–5 players, maybe more).
Each week, 7 NBA games are selected automatically. Players pick straight-up winners.
The system scores picks and tracks weekly + season standings with zero commissioner work.

Priority: **ease of use** over features. Friends-first; build clean enough to grow later.

## Hard Deadline
2026–27 NBA regular season opens **Tuesday, Oct 20, 2026**. Target a working V1 by then.
Preseason (starts Oct 3) is NOT a hard target. Testing uses fake seeded games (a script creates test games with tip-offs a few hours out; a wipe script removes them before launch). Preseason games never count toward the league.

## Setup Status
See README.md for the full setup steps.
- [x] GitHub repo is public (required for free GitHub Pages)
- [x] Schema, pick functions, jobs, slate generator, site, workflows built and tested
- [x] Supabase project; migrations 001–004 run; anon access verified (Sep 28)
- [x] balldontlie key; Actions secrets `BALLDONTLIE_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- [x] `site/config.js`: real Supabase URL + publishable key
- [x] `load-data` run (Sep 29): 30 teams; 2025–26 = 1,322 games; 2026–27 = 1,200 scheduled (the last 30 are scheduled in December after the Cup group stage)
- [x] Live balldontlie data verified: every 2026–27 game has a tip-off time; statuses parse; historical teams filtered; no preseason games on the free tier; Play-In and Cup Final are NOT flagged as postseason, so they're handled via `season_ends` / `cup_final_game_ids` in `jobs/league.toml`
- [x] Reload verified: 2025–26 = 1,230 regular + 1 Cup Final + 91 postseason (incl. 6 Play-In); 2026–27 regular season Oct 20 – Apr 11
- [x] Pages deployed; `PICKEM_ENABLED=true`; 3 players added; Week 1 slate preview passes every rule
- [ ] Fake test week with friends
- [ ] December: add the 2026–27 Cup Final id to `cup_final_game_ids` in `jobs/league.toml`

## Locked Decisions
- **Games:** regular season only. No preseason, Play-In, playoffs, or NBA Cup Final (the Cup Final doesn't count toward NBA standings either).
- **Week:** Monday–Sunday (use America/Los_Angeles for week boundaries)
- **Slate window:** only games tipping off Thu 00:00 – Sun 23:59 America/Los_Angeles. Mon–Wed is the pick window (football pick'em rhythm).
- **Slate size:** 7 games per week (fewer if the pool can't supply 7; see Slate Selection Rules)
- **Pick type:** straight-up winner only (no spreads, no confidence points)
- **Scoring:** 1 point per correct pick
- **Lock:** each pick locks at that game's tip-off
- **Pick edits:** players may change a pick any time until that game's tip-off
- **Pick flow:** each tap saves instantly (no Submit button). Every game card says "✓ Pick saved", "Saving…" or "No pick yet"; the banner confirms each save with team + time, and a failed save is shown in red with the previous pick kept.
- **Pick visibility:** other players' picks are hidden until that game locks
- **Postponed/cancelled games:** voided — no point, no penalty
- **Reminders:** manual (group text) for V1
- **Onboarding:** Daniel sends each player their private link by text or Discord. A script generates tokens + prints links.
- **Late joiners:** allowed; they start at 0 points.
- **Budget:** $0 (free tiers only)

## Design (locked Sep 29)
- **Dark only** ("Arena" theme): navy `#0b1020` background, cards `#141b2d`, sky-blue accent `#38bdf8`. No purple.
- **Fonts:** Oswald (headings, team abbreviations) + Inter (text), self-hosted in `site/fonts/` (SIL OFL). No font CDN.
- **Results:** correct = green fill + **✓**, wrong = rose fill + **✗**, dark text on both. Never color alone.
- **Background:** subtle hexagon pattern (stroke `rgba(147,160,184,0.08)`) behind cards only.
- **Standings:** points bar sized to the leader, leader stripe + bold, "Back" column (points behind the leader). Season and weekly tables.
- **Weekly Picks:** players are rows (league can grow to 10–12+), games are columns (≤7). Player name + weekly Pts are pinned; games scroll sideways on phones. Rows sorted by the week's points, then name. Game headers are compact (small matchup + score/time).
- **Accessibility:** every text/background pair meets WCAG AA (4.5:1). Check new colors before shipping.
- Title stays "NBA Pick'em" for now.

## Slate Selection Rules
1. Pull all eligible regular-season games tipping off Thu–Sun (PT) of the week
2. Rank teams by win % → "top teams" = top 6 (placeholder, easy to change)
3. Include at least 1 game featuring a top team
4. Fill the remaining slots at random, weighted by team preferences (see below)
5. No team appears twice in one week
6. **Light weeks:** if the pool has fewer than 7 games, use every eligible game. If the pool has 0 games (e.g., All-Star break), the week has no slate — UI and standings must handle an empty week.
7. **Relaxing rule 5:** if 7 games can't be found without a repeat team, relax the no-repeat rule before cutting games. Which team gets the repeat is decided by team preferences.
8. Seeded random (seed = season + week number) so any slate can be regenerated. Sort the candidate games by id before shuffling. Store the generated slate plus a snapshot of the inputs (top-6 list, preferences) — don't rely on regeneration matching after records change.
9. Generate Monday morning (PT), after Sunday's games are final
10. Weeks 1–3: use LAST season's final records; after that, current records

### Team Preferences (commissioner's thumb on the scale)
Daniel can add his own rules and favoritism. Preferences live in a versioned config file in the repo (e.g., `slate_prefs.toml`, read with Python's stdlib `tomllib` — no new dependency), not hard-coded in the generator.
- **Per-team weight:** 1.0 = neutral, >1 = favored in the random fill, 0 = never picked in the random fill. A game's weight is derived from its two teams; if either team has weight 0, the game is excluded from the random fill.
- **Weights apply to the random fill only (rule 4).** The top-team game (rule 3) ignores weights, unless a team has a per-team top-team override (below).
- **Top-team override:** optional per-team rank cutoff for rule 3 (e.g., team only qualifies as a "top team" if ranked top N, where N < 6).
- **Repeat priority:** ordered list of who gets a second appearance first when rule 5 must be relaxed; a blocklist of teams that never get a repeat
- Current preferences:
  - **Sacramento Kings:** weight 2.0 (placeholder, tunable) in the random fill, and first in repeat priority — always get the nod when rules are relaxed.
  - **Los Angeles Lakers:** weight 0 (never in the random fill) and on the repeat blocklist. Only eligible as the rule-3 top-team game if ranked **top 3** by win %.
- New rule types get added to the config + generator as needed; each one must stay deterministic under the seed.

## Stack ($0)
| Layer | Tool |
|---|---|
| Database | Supabase Free (Postgres) |
| NBA data | balldontlie API, free tier (Teams + Games endpoints only) |
| Scheduled jobs | GitHub Actions cron (Python) |
| Front end | Static site on GitHub Pages, mobile-first, dark only |

## Constraints & Gotchas
- **balldontlie free tier:** ~5 req/min; API key required in `Authorization` header (no Bearer). Standings endpoint is PAID — compute W-L ourselves from the Games table.
- **Supabase free tier:** pauses after ~7 days of inactivity. The daily results job keeps it awake in-season.
- **Pick locks MUST be enforced in the database**, never only in the UI. With no logins, RLS can't identify the player — use a `SECURITY DEFINER` function (e.g., `submit_pick(token, game_id, team_id)`) that checks the token, `now() < tipoff_utc`, that the game is in the slate, and that the team plays in that game. Revoke direct INSERT/UPDATE on `picks` from anon.
- **Never expose `access_token`.** Anon must not SELECT from `players` directly — expose a view without the token.
- **Hidden picks must be enforced in the database too** — anon reads picks only through a view/function that filters to locked games (plus the caller's own picks via their token).
- **No logins.** Each player gets a private link with a unique token. Proper auth only if this grows.
- Secrets (API key, Supabase service key) live in GitHub Actions secrets, never in the repo.
- Verify balldontlie's game object includes a usable tip-off datetime before building lock logic.
- Verify how balldontlie flags preseason and NBA Cup Final games so they can be excluded (and whether preseason games are returned at all on the free tier — affects the test plan).
- **GitHub Actions cron:** runs in UTC, can start late, and scheduled workflows are disabled after 60 days without repo activity.
- **GitHub Pages (free)** requires a public repo — only the Supabase anon key may appear in front-end code.

## Data Model (see `supabase/migrations/`)
- `teams` (id = balldontlie id, abbreviation, city, name, full_name)
- `games` (id = balldontlie id, season, game_date, tipoff_utc, home/away team + score, status, game_type, is_test)
  - status: scheduled | in_progress | final | postponed; game_type: regular | preseason | postseason | cup_final
- `weeks` (season, week_num, start_date, end_date, slate_generated_at, slate_inputs jsonb, is_test)
- `slate_games` (week_id, game_id)
- `players` (display_name, access_token) — never readable by anon
- `picks` (player_id, game_id, picked_team_id, created_at, updated_at) — PK(player_id, game_id); never readable by anon
- views: `players_public`, `team_records`, `pick_results` (internal), `weekly_standings`, `season_standings`
- functions (the only way the site touches picks): `get_me`, `submit_pick`, `get_my_picks`, `get_week_picks`
- Test data: season 0, negative game ids, is_test = true (`jobs/fake_week.py wipe` removes it)

## Build Order
1. Supabase schema + lock/pick functions
2. Python ingestion job: teams, full-season schedule, daily score updates
3. Slate generator (Python) + team preferences config, runs Monday morning
4. Pick page: view this week's games, tap a team, see locked state
5. Standings page (standings only: weekly + season points) and weekly picks page (every player's picks per week, shown only for locked games)
6. Test with friends on fake seeded games; fix what breaks
7. Wipe test data, load real data, generate Week 1 slate Mon Oct 19

## Out of Scope for V1
Spreads, confidence points, tiebreakers, chat, native app, multiple leagues, public signup, AI features, automated reminders.

## Working Style
- Owner: Daniel. Comfortable with SQL and Python; prefers direct, concise explanations.
- Keep code simple and readable over clever.
- Ask before adding dependencies or anything that could cost money.
- Approved dependencies: `requests` (Python jobs), `pytest` (dev only). Front end uses plain `fetch()` — no JS libraries.
