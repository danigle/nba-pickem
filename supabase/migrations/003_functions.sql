-- 003_functions.sql
-- The ONLY way the website touches players and picks.
-- SECURITY DEFINER = runs as the owner, so it can read/write tables anon can't.
-- Every function pins search_path so it can't be hijacked.

-- Who am I? Returns the player for a token (empty if the token is bad).
create function get_me(p_token text)
returns table (player_id int, display_name text)
language sql stable security definer set search_path = public
as $$
  select id, display_name from players where access_token = p_token;
$$;

-- Make or change a pick. The lock lives here, not in the UI.
create function submit_pick(p_token text, p_game_id bigint, p_team_id int)
returns void
language plpgsql security definer set search_path = public
as $$
declare
  v_player_id int;
  v_game      games%rowtype;
begin
  select id into v_player_id from players where access_token = p_token;
  if v_player_id is null then
    raise exception 'Invalid player link';
  end if;

  select * into v_game from games where id = p_game_id;
  if not found then
    raise exception 'Game not found';
  end if;

  if not exists (select 1 from slate_games where game_id = p_game_id) then
    raise exception 'Game is not on a slate';
  end if;

  if p_team_id not in (v_game.home_team_id, v_game.away_team_id) then
    raise exception 'Team is not playing in this game';
  end if;

  if v_game.tipoff_utc is null
     or now() >= v_game.tipoff_utc
     or v_game.status <> 'scheduled' then
    raise exception 'Pick is locked';
  end if;

  insert into picks (player_id, game_id, picked_team_id)
  values (v_player_id, p_game_id, p_team_id)
  on conflict (player_id, game_id)
  do update set picked_team_id = excluded.picked_team_id,
                updated_at     = now();
end;
$$;

-- My own picks for a week, including ones that haven't locked yet.
create function get_my_picks(p_token text, p_week_id int)
returns table (game_id bigint, picked_team_id int, is_correct boolean)
language sql stable security definer set search_path = public
as $$
  select r.game_id, r.picked_team_id, r.is_correct
  from pick_results r
  join players pl on pl.id = r.player_id
  where pl.access_token = p_token
    and r.week_id = p_week_id;
$$;

-- Everyone's picks for a week, but only for games that have tipped off.
create function get_week_picks(p_week_id int)
returns table (player_id int, game_id bigint, picked_team_id int, is_correct boolean)
language sql stable security definer set search_path = public
as $$
  select r.player_id, r.game_id, r.picked_team_id, r.is_correct
  from pick_results r
  join games g on g.id = r.game_id
  where r.week_id = p_week_id
    and g.tipoff_utc <= now();
$$;
