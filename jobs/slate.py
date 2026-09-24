"""Slate selection rules. Pure logic, no network or database.

The job that feeds this real data lives in generate_slate.py.
Teams are identified by abbreviation (e.g. "SAC") throughout.
"""
import random
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

PT = ZoneInfo("America/Los_Angeles")
SLATE_SIZE = 7
FILL_ATTEMPTS = 200


@dataclass(frozen=True)
class Game:
    id: int
    home: str
    away: str
    tipoff_utc: datetime

    @property
    def teams(self):
        return (self.home, self.away)


@dataclass
class Prefs:
    top_teams: int = 6
    weights: dict = field(default_factory=dict)
    top_team_max_rank: dict = field(default_factory=dict)
    repeat_priority: list = field(default_factory=list)
    never_repeat: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d):
        return cls(
            top_teams=d.get("top_teams", 6),
            weights=d.get("weights", {}),
            top_team_max_rank=d.get("top_team_max_rank", {}),
            repeat_priority=d.get("repeat_priority", []),
            never_repeat=d.get("never_repeat", []),
        )

    def team_names(self):
        return (set(self.weights) | set(self.top_team_max_rank)
                | set(self.repeat_priority) | set(self.never_repeat))

    def weight(self, team):
        return float(self.weights.get(team, 1.0))

    def game_weight(self, game):
        return self.weight(game.home) * self.weight(game.away)


# ---------- Weeks ----------

def week_dates(week1_monday, week_num):
    """(Monday, Sunday) for a week number. Week 1 starts on week1_monday."""
    monday = week1_monday + timedelta(weeks=week_num - 1)
    return monday, monday + timedelta(days=6)


def week_num_for(week1_monday, day):
    """Week number containing `day`. Can be <= 0 before the season."""
    return (day - week1_monday).days // 7 + 1


def slate_window(monday):
    """UTC [start, end) for Thu 00:00 through Sun 23:59 PT of the week."""
    start = datetime.combine(monday + timedelta(days=3), time(0), PT)
    end = datetime.combine(monday + timedelta(days=7), time(0), PT)
    return start.astimezone(ZoneInfo("UTC")), end.astimezone(ZoneInfo("UTC"))


# ---------- Ranking ----------

def rank_teams(records, all_teams):
    """Teams ordered best to worst by win %, then wins, then abbreviation.

    records: {abbr: (wins, losses)}. Teams with no record rank as 0-0.
    """
    def key(team):
        wins, losses = records.get(team, (0, 0))
        pct = wins / (wins + losses) if wins + losses else 0.0
        return (-pct, -wins, team)
    return sorted(all_teams, key=key)


def top_teams(ranking, prefs):
    tops = set()
    for rank, team in enumerate(ranking, start=1):
        cutoff = min(prefs.top_teams, prefs.top_team_max_rank.get(team, prefs.top_teams))
        if rank <= cutoff:
            tops.add(team)
    return tops


# ---------- Slate ----------

def pick_slate(pool, ranking, prefs, seed, size=SLATE_SIZE):
    """Choose up to `size` games. Returns (games sorted by tip-off, notes)."""
    pool = sorted(pool, key=lambda g: g.id)  # stable order → reproducible
    rng = random.Random(seed)
    notes = []

    # Rule 3: one game featuring a top team. Weights don't apply, but a
    # weight-0 team may only appear here if it is itself a top team.
    tops = top_teams(ranking, prefs)
    top_games = [
        g for g in pool
        if tops & set(g.teams)
        and all(prefs.weight(t) > 0 or t in tops for t in g.teams)
    ]
    slate = []
    if top_games:
        slate.append(rng.choice(top_games))
    elif pool:
        notes.append("No top-team game available")

    # Rules 4–5: weighted random fill, no team twice.
    slate = _fill_without_repeats(slate, pool, prefs, rng, size)

    # Rule 7: still short → allow repeats, priority teams first.
    if len(slate) < size:
        slate = _fill_with_repeats(slate, pool, prefs, rng, size, notes)

    if len(slate) < size:
        notes.append(f"Only {len(slate)} eligible games (pool had {len(pool)})")

    return sorted(slate, key=lambda g: (g.tipoff_utc, g.id)), notes


def _fill_without_repeats(base, pool, prefs, rng, size):
    best = list(base)
    for _ in range(FILL_ATTEMPTS):
        chosen = list(base)
        used = {t for g in chosen for t in g.teams}
        while len(chosen) < size:
            candidates = [
                g for g in pool
                if g not in chosen
                and prefs.game_weight(g) > 0
                and not used & set(g.teams)
            ]
            if not candidates:
                break
            game = rng.choices(candidates, weights=[prefs.game_weight(g) for g in candidates])[0]
            chosen.append(game)
            used |= set(game.teams)
        if len(chosen) > len(best):
            best = chosen
        if len(best) >= size or len(chosen) == len(base):
            break
    return best


def _fill_with_repeats(slate, pool, prefs, rng, size, notes):
    slate = list(slate)
    while len(slate) < size:
        counts = Counter(t for g in slate for t in g.teams)
        candidates = [
            g for g in pool
            if g not in slate
            and prefs.game_weight(g) > 0
            and not any(counts[t] and t in prefs.never_repeat for t in g.teams)
        ]
        if not candidates:
            break

        preferred = []
        for team in prefs.repeat_priority:
            preferred = [g for g in candidates if team in g.teams]
            if preferred:
                break
        group = preferred or candidates

        # Fewest repeated teams first, then weighted random.
        fewest = min(sum(1 for t in g.teams if counts[t]) for g in group)
        group = [g for g in group if sum(1 for t in g.teams if counts[t]) == fewest]
        game = rng.choices(group, weights=[prefs.game_weight(g) for g in group])[0]

        repeated = [t for t in game.teams if counts[t]]
        notes.append(f"Relaxed no-repeat: {', '.join(repeated)} appear twice")
        slate.append(game)
    return slate
