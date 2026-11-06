#!/usr/bin/env python3
"""NFL Hub Low Hurdles (display-only).

Builds data/low_hurdles.json from published Hub prop rows (data/v2.json)
and player game logs (data/players/*.json).

Does not change picks, Highlighted-play logic, model weights, or projections.
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ET = ZoneInfo("America/New_York")
SEASON = 2026

# Prefer min 5 when the board is not empty. Passing is thinner at published
# main lines (reference boards go to 2). Rushing / rush+rec are empty at
# min 5 against this week's published main lines, so those use 3.
MIN_STREAK = {
    "Receiving Yards": 5,
    "Receptions": 5,
    "Rushing Yards": 3,
    "Passing Yards": 2,
    "Rushing Plus Receiving Yards": 3,
}

MARKETS = {
    "Receiving Yards": {
        "section": "rec_yds",
        "stat": "receiving_yards",
        "label": "Receiving yards",
        "short": "Rec Yards",
    },
    "Receptions": {
        "section": "receptions",
        "stat": "receptions",
        "label": "Receptions",
        "short": "Receptions",
    },
    "Rushing Yards": {
        "section": "rush_yds",
        "stat": "rushing_yards",
        "label": "Rushing yards",
        "short": "Rush Yards",
    },
    "Passing Yards": {
        "section": "pass_yds",
        "stat": "passing_yards",
        "label": "Passing yards",
        "short": "Pass Yards",
    },
    "Rushing Plus Receiving Yards": {
        "section": "rush_rec",
        "stat": "rush_rec",
        "label": "Rush + Rec yards",
        "short": "Rush + Rec Yards",
    },
}

SECTION_ORDER = ["rec_yds", "receptions", "rush_yds", "pass_yds", "rush_rec"]
TITLES = {
    "rec_yds": "Receiving yards",
    "receptions": "Receptions",
    "rush_yds": "Rushing yards",
    "pass_yds": "Passing yards",
    "rush_rec": "Alternate · Rush + Rec yards",
}


def floor_from_line(line: float) -> tuple[int, int]:
    """Return (display_floor, clear_min).

    Half-line 24.5 needs 25 → display 25+. Integer 15 needs 15 → display 15+.
    """
    line = float(line)
    if line == int(line):
        n = int(line)
        return n, n
    n = math.floor(line) + 1
    return n, n


def game_total(g: dict, stat: str):
    if stat == "rush_rec":
        ry = g.get("rushing_yards")
        rc = g.get("receiving_yards")
        if ry is None and rc is None:
            return None
        return float(ry or 0) + float(rc or 0)
    v = g.get(stat)
    return None if v is None else float(v)


def season_games_before_week(plog: dict, before_week: int) -> list:
    """Current-season completed games strictly before the slate week.

    Bye weeks are absent from the log (not counted as misses). Sorted
    newest → oldest by week.
    """
    games = [
        g
        for g in (plog.get("log") or [])
        if g.get("s") == SEASON and isinstance(g.get("w"), int) and g["w"] < before_week
    ]
    return sorted(games, key=lambda g: g["w"], reverse=True)


def active_streak(games: list, stat: str, clear_min: int):
    """Consecutive most-recent games clearing clear_min. No skips inside the run.

    0-snap DNPs are ignored (same idea as NBA minutes==0). First miss or
    missing total stops the streak.
    """
    streak = 0
    totals = []
    meta = []
    for g in games:
        snap = g.get("snap")
        if snap is not None and snap == 0:
            continue
        val = game_total(g, stat)
        if val is None:
            break
        if val >= clear_min:
            streak += 1
            totals.append(val)
            meta.append(
                {
                    "week": g.get("w"),
                    "opp": g.get("o"),
                    "home": bool(g.get("home")),
                    "total": val,
                }
            )
        else:
            break
    return streak, totals, meta


def main() -> None:
    v2 = json.load(open(os.path.join(DATA, "v2.json")))
    week = int(v2.get("week") or 0)
    rows_in = v2.get("rows") or []
    now = datetime.now(timezone.utc)

    sections = {k: [] for k in SECTION_ORDER}
    coverage = {k: Counter() for k in SECTION_ORDER}
    excluded = {
        k: {
            "missing_line": 0,
            "missing_logs": 0,
            "short_streak": 0,
            "missing_player_file": 0,
        }
        for k in SECTION_ORDER
    }

    player_cache: dict[str, dict | None] = {}

    def load_player(aid: str):
        if aid not in player_cache:
            path = os.path.join(DATA, "players", f"{aid}.json")
            if os.path.exists(path):
                player_cache[aid] = json.load(open(path))
            else:
                player_cache[aid] = None
        return player_cache[aid]

    # Only markets we actually have published lines for.
    present_markets = {r.get("market") for r in rows_in}
    omitted = []
    if "Kicking Points" not in present_markets and "Field Goals" not in present_markets:
        omitted.append(
            "Kicking points — no published kicking-points (or FG) prop lines in this week's Hub data."
        )

    for r in rows_in:
        market = r.get("market")
        if market not in MARKETS:
            continue
        meta = MARKETS[market]
        sec = meta["section"]
        coverage[sec]["candidates"] += 1

        line = r.get("line")
        if line is None:
            excluded[sec]["missing_line"] += 1
            continue

        aid = str(r.get("aid") or "")
        plog = load_player(aid)
        if not plog:
            excluded[sec]["missing_player_file"] += 1
            continue

        games = season_games_before_week(plog, week)
        if not games:
            excluded[sec]["missing_logs"] += 1
            continue

        floor, clear_min = floor_from_line(line)
        streak, totals, game_meta = active_streak(games, meta["stat"], clear_min)
        min_n = MIN_STREAK[market]
        if streak < min_n:
            excluded[sec]["short_streak"] += 1
            coverage[sec][f"streak_{streak}"] += 1
            continue

        tip = None
        tip_s = r.get("time")
        if tip_s:
            try:
                tip = datetime.fromisoformat(str(tip_s).replace("Z", "+00:00"))
            except ValueError:
                tip = None
        played = bool(tip and tip < now)
        tip_et = tip.astimezone(ET) if tip else None

        row = {
            "aid": aid,
            "player": r.get("name"),
            "team": r.get("team"),
            "pos": r.get("pos"),
            "opp": r.get("opp"),
            "oa": r.get("oa"),
            "home": bool(r.get("home")),
            "game": str(r.get("game") or ""),
            "time": tip.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ") if tip else None,
            "time_et": (
                tip_et.strftime("%a %b %-d · %-I:%M %p ET") if tip_et else None
            ),
            "played": played,
            "market": market,
            "market_label": meta["label"],
            "line": float(line),
            "floor": floor,
            "floor_label": f"{floor}+ {meta['short']}",
            "streak": streak,
            "min_required": min_n,
            "recent_totals": totals,
            "recent_games": game_meta,
            "head": r.get("head"),
        }
        sections[sec].append(row)
        coverage[sec]["qualify"] += 1

    for sec, rows in sections.items():
        # Upcoming first, then streak length descending, then floor, then kickoff.
        rows.sort(
            key=lambda r: (
                1 if r.get("played") else 0,
                -r["streak"],
                -r["floor"],
                r.get("time") or "9999",
                r.get("player") or "",
            )
        )

    # Drop empty alternate section from order if nothing qualifies AND no candidates
    order = []
    for sec in SECTION_ORDER:
        if sec == "rush_rec" and not sections[sec] and coverage[sec]["candidates"] == 0:
            omitted.append(
                "Rush + Rec yards — no published Rushing Plus Receiving Yards lines this week."
            )
            continue
        order.append(sec)

    out = {
        "updated": v2.get("updated"),
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "built_et": datetime.now(ET).strftime("%b %-d · %-I:%M %p ET"),
        "week": week,
        "season": SEASON,
        "definition": {
            "tonight_number": "Published NFL Hub prop line for that player/market on this week's slate (data/v2.json).",
            "clear": "Completed-game total must be strictly greater than a half-line (24.5→25), or ≥ an integer threshold. Display floor is that integer with a + suffix.",
            "active_streak": "Count of consecutive most-recent current-season completed games (snap > 0) before this slate week that cleared the same published number; stop at first miss. No skipped games inside the run. Bye weeks are absent from logs. No prior season.",
            "minimum_streaks": MIN_STREAK,
            "minimum_note": (
                "Receiving yards and Receptions use a minimum of 5 (aligned with the NBA Low Hurdles board and the skill-position reference boards). "
                "Rushing yards and Rush + Rec use 3 because published main lines leave the board empty at 5 this early in the season. "
                "Passing yards uses 2 to match the thinner reference passing board (and because min 5 qualifies nobody against published pass-yard lines)."
            ),
            "display_only": True,
            "omitted_sections": omitted,
        },
        "order": order,
        "titles": {k: TITLES[k] for k in order},
        "sections": {k: sections[k] for k in order},
        "coverage": {
            sec: {
                "candidates": int(coverage[sec].get("candidates", 0)),
                "qualify": int(coverage[sec].get("qualify", 0)),
                "excluded": excluded[sec],
                "short_streak_breakdown": {
                    k: int(v)
                    for k, v in sorted(coverage[sec].items())
                    if str(k).startswith("streak_")
                },
            }
            for sec in order
        },
        "total_highlighted": sum(len(sections[k]) for k in order),
    }

    path = os.path.join(DATA, "low_hurdles.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print(
        f"wrote {path} · week {week} · highlighted {out['total_highlighted']} · "
        + ", ".join(f"{k}:{len(sections[k])}" for k in order)
    )
    if omitted:
        print("omitted:", "; ".join(omitted))


if __name__ == "__main__":
    main()
