-- 002_views.sql
-- Records, pick grading, and standings.
-- Views run with the owner's privileges, so they can read players/picks even
-- though anon cannot. Only views that are safe to expose get granted in 004.

-- Safe player list (no access_token).
create view players_public as
select id, display_name
from players;

-- Win/loss per team per season. Regular season, final games only.
create view team_records as
with results as (
  select season, home_team_id as team_id,
         (home_score > away_score)::int as win,
         (home_score < away_score)::int as loss
  from games
  where game_type = 'regular' and status = 'final' and not is_test
  union all
  select season, away_team_id,
         (away_score > home_score)::int,
         (away_score < home_score)::int
  from games
  where game_type = 'regular' and status = 'final' and not is_test
)
select season,
       team_id,
       sum(win)::int  as wins,
       sum(loss)::int as losses,
       round(sum(win)::numeric / nullif(sum(win) + sum(loss), 0), 3) as win_pct
from results
group by season, team_id;

-- Every pick, graded. NOT exposed to anon (it includes unlocked picks).
-- is_correct is null until the game is final. A game that isn't played within
-- its slate week (postponed/cancelled/rescheduled) is void: always null.
create view pick_results as
select p.player_id,
       sg.week_id,
       p.game_id,
       p.picked_team_id,
       case
         when g.status = 'final'
          and (g.tipoff_utc at time zone 'America/Los_Angeles')::date
              between w.start_date and w.end_date
         then p.picked_team_id = case when g.home_score > g.away_score
                                      then g.home_team_id
                                      else g.away_team_id end
       end as is_correct
from picks p
join slate_games sg on sg.game_id = p.game_id
join weeks w        on w.id = sg.week_id
join games g        on g.id = p.game_id;

-- Points per player per week. Everyone appears in every week (late joiners get 0).
create view weekly_standings as
select w.id      as week_id,
       w.season,
       w.week_num,
       pl.id     as player_id,
       pl.display_name,
       count(*) filter (where r.is_correct)::int as points
from weeks w
cross join players pl
left join pick_results r on r.week_id = w.id and r.player_id = pl.id
group by w.id, w.season, w.week_num, pl.id, pl.display_name;

create view season_standings as
select season,
       player_id,
       display_name,
       sum(points)::int as points
from weekly_standings
group by season, player_id, display_name;
