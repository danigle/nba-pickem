-- Security tests for the pick rules. Runs in CI after the migrations on an
-- empty Postgres 16. Any failed check raises an exception and fails the job.
--   psql -v ON_ERROR_STOP=1 -f supabase/tests/security_test.sql

-- ---------- Fixtures (as the owner) ----------
insert into teams values
  (26, 'SAC', 'Sacramento', 'Kings', 'Sacramento Kings'),
  (14, 'LAL', 'Los Angeles', 'Lakers', 'Los Angeles Lakers'),
  (2,  'BOS', 'Boston', 'Celtics', 'Boston Celtics'),
  (20, 'NYK', 'New York', 'Knicks', 'New York Knicks');

insert into weeks (id, season, week_num, start_date, end_date)
values (1, 2026, 1, current_date - 1, current_date + 5);

-- 1: open, on the slate     2: final, NYK won     3: final but played outside its week (void)
-- 4: open, NOT on the slate 5: postponed
-- 6: tipped off 10 min ago but status not refreshed yet (still 'scheduled'), the
--    real-world gap between tip-off and the next score update: the clock must lock it
insert into games (id, season, game_date, tipoff_utc, home_team_id, away_team_id, home_score, away_score, status) values
  (1, 2026, current_date,      now() + interval '2 hours',  26, 14, null, null, 'scheduled'),
  (2, 2026, current_date,      now() - interval '3 hours',  2,  20, 99,   110,  'final'),
  (3, 2026, current_date + 30, now() + interval '30 days',  26, 2,  120,  100,  'final'),
  (4, 2026, current_date,      now() + interval '2 hours',  2,  26, null, null, 'scheduled'),
  (5, 2026, current_date,      now() + interval '1 hour',   14, 20, null, null, 'postponed'),
  (6, 2026, current_date,      now() - interval '10 minutes', 20, 14, null, null, 'scheduled');
insert into slate_games values (1, 1), (1, 2), (1, 3), (1, 5), (1, 6);

insert into players (id, display_name, access_token) values (1, 'Daniel', 'tokD'), (2, 'Pat', 'tokP');
insert into picks (player_id, game_id, picked_team_id) values
  (1, 2, 20),   -- Daniel right
  (2, 2, 2),    -- Pat wrong
  (1, 3, 26);   -- void game: must never score

-- ---------- As the public website (anon) ----------
set role anon;

-- Direct table access is denied.
do $$ begin
  begin perform * from picks;        raise exception 'FAIL: anon read picks';        exception when insufficient_privilege then null; end;
  begin perform * from players;      raise exception 'FAIL: anon read players';      exception when insufficient_privilege then null; end;
  begin perform * from pick_results; raise exception 'FAIL: anon read pick_results'; exception when insufficient_privilege then null; end;
  begin insert into picks values (1, 1, 26);
        raise exception 'FAIL: anon inserted a pick directly'; exception when insufficient_privilege then null; end;
  begin update games set home_score = 0;
        raise exception 'FAIL: anon updated games';  exception when insufficient_privilege then null; end;
  begin delete from teams;
        raise exception 'FAIL: anon deleted teams';  exception when insufficient_privilege then null; end;
  raise notice 'ok: anon cannot read or write picks/players or change data';
end $$;

-- Safe reads work, and never expose tokens.
do $$ begin
  if (select count(*) from players_public) <> 2 then raise exception 'FAIL: players_public'; end if;
  if exists (select 1 from information_schema.columns
             where table_name = 'players_public' and column_name = 'access_token')
  then raise exception 'FAIL: players_public exposes access_token'; end if;
  if (select count(*) from games) <> 6 then raise exception 'FAIL: anon cannot read games'; end if;
  raise notice 'ok: public reads work, no tokens exposed';
end $$;

-- submit_pick rejects everything it should, with the right message.
do $$
declare
  cases text[][] := array[
    array['nope', '1', '26', 'Invalid player link'],
    array['tokD', '2', '20', 'Pick is locked'],                  -- final
    array['tokD', '6', '20', 'Pick is locked'],                  -- tipped off, status not updated yet
    array['tokD', '5', '14', 'Pick is locked'],                  -- postponed
    array['tokD', '1', '2',  'Team is not playing in this game'],
    array['tokD', '4', '26', 'Game is not on a slate'],
    array['tokD', '99','26', 'Game not found']
  ];
  c text[];
  got text;
begin
  foreach c slice 1 in array cases loop
    got := null;
    begin
      perform submit_pick(c[1], c[2]::bigint, c[3]::int);
    exception when raise_exception then got := sqlerrm;
    end;
    if got is distinct from c[4] then
      raise exception 'FAIL: submit_pick(%, %, %) expected "%", got "%"', c[1], c[2], c[3], c[4], coalesce(got, 'success');
    end if;
  end loop;
  raise notice 'ok: submit_pick rejects bad token, final, tipped-off (by clock), postponed, wrong team, off-slate, missing game';
end $$;

-- A valid pick saves, and can be changed before tip-off.
select submit_pick('tokP', 1, 14);
select submit_pick('tokP', 1, 26);
do $$ begin
  if (select picked_team_id from get_my_picks('tokP', 1) where game_id = 1) <> 26
  then raise exception 'FAIL: pick edit did not stick'; end if;
  if (select count(*) from get_me('tokP')) <> 1 or (select count(*) from get_me('nope')) <> 0
  then raise exception 'FAIL: get_me'; end if;
  raise notice 'ok: picks save and can be edited before tip-off';
end $$;

-- Hidden picks: others' picks appear only for games that have tipped off.
do $$ begin
  if exists (select 1 from get_week_picks(1) where game_id = 1)
  then raise exception 'FAIL: unlocked pick visible to everyone'; end if;
  if (select count(*) from get_week_picks(1) where game_id = 2) <> 2
  then raise exception 'FAIL: locked picks not visible'; end if;
  raise notice 'ok: picks hidden until tip-off';
end $$;

-- Scoring: correct pick = 1 point; wrong = 0; void game never scores.
do $$ begin
  if (select points from weekly_standings where display_name = 'Daniel') <> 1
  then raise exception 'FAIL: Daniel should have 1 point (void game must not count)'; end if;
  if (select points from weekly_standings where display_name = 'Pat') <> 0
  then raise exception 'FAIL: Pat should have 0 points'; end if;
  if (select points from season_standings where display_name = 'Daniel') <> 1
  then raise exception 'FAIL: season standings'; end if;
  raise notice 'ok: scoring and standings';
end $$;

reset role;
