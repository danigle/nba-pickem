-- 001_tables.sql
-- Core tables. Run in the Supabase SQL editor, in file order (001 → 004).

create table teams (
  id            int primary key,          -- balldontlie team id
  abbreviation  text not null unique,     -- e.g. SAC, LAL
  city          text not null,
  name          text not null,            -- e.g. Kings
  full_name     text not null             -- e.g. Sacramento Kings
);

create table games (
  id            bigint primary key,       -- balldontlie game id; test games use negative ids
  season        int not null,             -- season start year (2026 = 2026–27); 0 = test data
  game_date     date not null,            -- date as reported by balldontlie
  tipoff_utc    timestamptz,              -- null until balldontlie reports a start time
  home_team_id  int not null references teams(id),
  away_team_id  int not null references teams(id),
  home_score    int,
  away_score    int,
  status        text not null default 'scheduled'
                check (status in ('scheduled', 'in_progress', 'final', 'postponed')),
  game_type     text not null default 'regular'
                check (game_type in ('regular', 'preseason', 'postseason', 'cup_final')),
  is_test       boolean not null default false,
  updated_at    timestamptz not null default now()
);

create index games_season_tipoff_idx on games (season, tipoff_utc);

create table weeks (
  id                  serial primary key,
  season              int not null,       -- 0 = test data
  week_num            int not null,
  start_date          date not null,      -- Monday (America/Los_Angeles)
  end_date            date not null,      -- Sunday
  slate_generated_at  timestamptz,
  slate_inputs        jsonb,              -- snapshot: top teams, prefs, seed, notes
  is_test             boolean not null default false,
  unique (season, week_num)
);

create table slate_games (
  week_id  int not null references weeks(id) on delete cascade,
  game_id  bigint not null references games(id) on delete cascade,
  primary key (week_id, game_id)
);

create table players (
  id            serial primary key,
  display_name  text not null unique,
  access_token  text not null unique default replace(gen_random_uuid()::text, '-', ''),
  created_at    timestamptz not null default now()
);

create table picks (
  player_id       int not null references players(id) on delete cascade,
  game_id         bigint not null references games(id) on delete cascade,
  picked_team_id  int not null references teams(id),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  primary key (player_id, game_id)
);
