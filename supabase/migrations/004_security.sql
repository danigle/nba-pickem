-- 004_security.sql
-- Lock everything down, then open only what the website needs.
-- anon = the public website (anon key). The Python jobs use the service role
-- key, which bypasses RLS.

-- 1. RLS on every table. No policy = no access.
alter table teams       enable row level security;
alter table games       enable row level security;
alter table weeks       enable row level security;
alter table slate_games enable row level security;
alter table players     enable row level security;
alter table picks       enable row level security;

-- 2. Strip Supabase's default grants from the public roles.
revoke all on all tables    in schema public from anon, authenticated;
revoke all on all functions in schema public from public, anon, authenticated;

-- 3. Public, read-only data.
grant select on teams, games, weeks, slate_games to anon;
create policy "public read" on teams       for select to anon using (true);
create policy "public read" on games       for select to anon using (true);
create policy "public read" on weeks       for select to anon using (true);
create policy "public read" on slate_games for select to anon using (true);

-- 4. Safe views. (pick_results is deliberately NOT granted.)
grant select on players_public, team_records, weekly_standings, season_standings to anon;

-- 5. Pick functions.
grant execute on function get_me(text)                    to anon;
grant execute on function submit_pick(text, bigint, int)  to anon;
grant execute on function get_my_picks(text, int)         to anon;
grant execute on function get_week_picks(int)             to anon;

-- players and picks: no grants, no policies. anon cannot read or write them directly.
