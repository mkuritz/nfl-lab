#!/usr/bin/env python3
"""Build display-only RB expected-rush-yards JSON for NFL Hub profiles.

expected = season avg rush attempts × opponent rush yards allowed per rush attempt

Uses published Hub player logs + matchups.json (for book line / Sports Labs proj
when present). Does not change pick logic, grades, or projections.
"""
from __future__ import annotations

import collections
import json
import os
import statistics
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "rb_expected_rush.json")
ET = ZoneInfo("America/New_York")


def jload(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def round1(x):
    return None if x is None else round(float(x) + 1e-9, 1)


def main():
    meta = jload("meta.json")
    pindex = jload("pindex.json")["p"]
    matchups = jload("matchups.json")
    rush_rows = [
        r
        for r in matchups.get("cats", {}).get("rush", {}).get("best", [])
        if r.get("pos") == "RB"
    ]
    by_aid = {str(r["aid"]): r for r in rush_rows}

    D = collections.defaultdict(lambda: {"ry": 0.0, "ra": 0.0, "g": set()})
    for fn in os.listdir(os.path.join(DATA, "players")):
        if not fn.endswith(".json"):
            continue
        p = jload(os.path.join("players", fn))
        for g in p.get("log") or []:
            if g.get("s") != 2026:
                continue
            o = g.get("o")
            if not o:
                continue
            car = float(g.get("carries") or 0)
            ry = float(g.get("rushing_yards") or 0)
            if car or ry:
                D[o]["ry"] += ry
                D[o]["ra"] += car
                D[o]["g"].add(str(g.get("g") or f"{g.get('w')}-{o}"))

    teams = {}
    for t, d in D.items():
        if d["ra"] < 10:
            continue
        teams[t] = {
            "ypc": round(d["ry"] / d["ra"], 2),
            "ry": round(d["ry"], 1),
            "ra": round(d["ra"], 1),
            "g": len(d["g"]),
            "source": "2026 player-log rush attempts & yards allowed",
        }

    board_ypc = {}
    for r in rush_rows:
        for c in r.get("cols") or []:
            if c and c[0] == "Yds/car" and c[1] is not None:
                board_ypc[r["opp"]] = {
                    "ypc": float(c[1]),
                    "raw_ypc": float(c[4]) if len(c) > 4 and c[4] is not None else None,
                    "rank": c[2],
                    "source": "matchups.json rush Yds/car (published board)",
                }
                break

    players = {}
    hidden = collections.Counter()
    rbs = [r for r in pindex if len(r) > 3 and r[3] == "RB"]
    rb_ids = {str(r[0]) for r in rbs}
    # Also ensure every matchup-board RB is considered (even if next already kicked)
    for aid in by_aid:
        rb_ids.add(aid)

    for pid in sorted(rb_ids):
        try:
            p = jload(os.path.join("players", f"{pid}.json"))
        except FileNotFoundError:
            hidden["missing_player_file"] += 1
            continue
        if (p.get("pos") or p.get("grp")) not in ("RB",):
            # Board can include QB rush; skip non-RB for this preview
            if by_aid.get(pid, {}).get("pos") != "RB":
                hidden["not_rb"] += 1
                continue
        board = by_aid.get(pid)
        nxt = p.get("next")
        if nxt and nxt.get("opp"):
            opp = nxt["opp"]
            home = bool(nxt.get("home"))
            kick = nxt.get("date")
        elif board:
            opp = board["opp"]
            home = board.get("site") == "vs"
            kick = board.get("time")
        else:
            hidden["no_upcoming_opponent"] += 1
            continue

        season = p.get("season") or 2026
        cur = [g for g in (p.get("log") or []) if g.get("s") == season]
        cars = [float(g["carries"]) for g in cur if g.get("carries") is not None]
        if board and board.get("adv", {}).get("car"):
            avg_att = float(board["adv"]["car"][0])
            window = "2026 season avg carries (matchups adv)"
            att_games = len(cars) or None
        elif cars:
            avg_att = statistics.mean(cars)
            window = f"2026 season ({len(cars)} games with carries logged)"
            att_games = len(cars)
        else:
            hidden["no_attempt_history"] += 1
            continue

        ypc_info = None
        if opp in board_ypc:
            ypc_info = dict(board_ypc[opp])
        elif opp in teams:
            ypc_info = dict(teams[opp])
        else:
            hidden["missing_opp_attempts_faced"] += 1
            continue
        ypc = float(ypc_info["ypc"])
        expected = round1(avg_att * ypc)
        row = {
            "id": pid,
            "name": p.get("name") or (board or {}).get("name"),
            "team": p.get("team") or (board or {}).get("team"),
            "pos": "RB",
            "opp": opp,
            "home": home,
            "kickoff": kick,
            "avg_att": round1(avg_att),
            "att_window": window,
            "att_games": att_games,
            "opp_ypc": round(ypc, 2),
            "opp_ypc_source": ypc_info.get("source"),
            "opp_ry": ypc_info.get("ry") or (teams.get(opp) or {}).get("ry"),
            "opp_ra": ypc_info.get("ra") or (teams.get(opp) or {}).get("ra"),
            "opp_g": ypc_info.get("g") or (teams.get(opp) or {}).get("g"),
            "expected": expected,
            "formula": f"{round1(avg_att)} att × {round(ypc, 2)} yds allowed/att = {expected} yds",
            "label": "Attempts × opponent rate estimate",
            "on_board": bool(board),
        }
        if board:
            if board.get("line") is not None:
                row["line"] = board["line"]
                row["line_src"] = board.get("src")
            if board.get("proj") is not None:
                row["sl_proj"] = board["proj"]
        players[pid] = row

    # Recount hides for index RBs without a row
    for r in rbs:
        if str(r[0]) not in players:
            # already counted during loop when we saw them... ensure board-only extras don't skew
            pass

    out = {
        "updated": meta.get("updated") or matchups.get("updated"),
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "built_et": datetime.now(ET).strftime("%Y-%m-%d %-I:%M %p ET"),
        "season": 2026,
        "week": matchups.get("week"),
        "method": "RB average rush attempts × opponent rush yards allowed per rush attempt",
        "scope": "Running backs only. Rushing QBs omitted in this preview.",
        "note": "Display-only matchup layer. Does not replace Sports Labs rush-yards projection or change picks.",
        "coverage": {
            "rb_index": len(rbs),
            "shown": len(players),
            "hidden": dict(hidden),
            "matchup_board_rbs": len(rush_rows),
            "matchup_board_rbs_shown": sum(1 for p in players.values() if p.get("on_board")),
            "defs_with_ypc": len(teams),
        },
        "teams": teams,
        "board_ypc": {k: v["ypc"] for k, v in board_ypc.items()},
        "players": players,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    h = players.get("3043078")
    print(
        "wrote",
        OUT,
        "shown",
        len(players),
        "hidden",
        dict(hidden),
        "henry",
        (h or {}).get("formula"),
        (h or {}).get("kickoff"),
    )


if __name__ == "__main__":
    main()
