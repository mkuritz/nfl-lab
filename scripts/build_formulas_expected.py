#!/usr/bin/env python3
"""Build display-only expected-yards JSON for NFL Hub Formulas tab.

Sections:
  qb_pass — QB avg pass attempts × opponent pass yards allowed per pass attempt
  wr_rec  — WR avg targets × opponent receiving yards allowed per target (to WRs)
  te_rec  — TE avg targets × opponent receiving yards allowed per target (to TEs)

RB rush yards stay in data/rb_expected_rush.json (already shipped). This file does
not replace Sports Labs projections or change pick logic.
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
OUT = os.path.join(DATA, "formulas_expected.json")
ET = ZoneInfo("America/New_York")


def jload(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def round1(x):
    return None if x is None else round(float(x) + 1e-9, 1)


def round2(x):
    return None if x is None else round(float(x) + 1e-12, 2)


def load_players_by_id():
    out = {}
    for fn in os.listdir(os.path.join(DATA, "players")):
        if not fn.endswith(".json"):
            continue
        p = jload(os.path.join("players", fn))
        out[str(p.get("id") or fn[:-5])] = p
    return out


def opp_pass_rates(players):
    """Aggregate opponent pass yards / attempts faced from QB logs."""
    D = collections.defaultdict(lambda: {"py": 0.0, "pa": 0.0, "g": set()})
    for p in players.values():
        if (p.get("pos") or p.get("grp")) != "QB":
            continue
        for g in p.get("log") or []:
            if g.get("s") != 2026:
                continue
            o = g.get("o")
            if not o:
                continue
            att = float(g.get("attempts") or 0)
            py = float(g.get("passing_yards") or 0)
            if att or py:
                D[o]["py"] += py
                D[o]["pa"] += att
                D[o]["g"].add(str(g.get("g") or f"{g.get('w')}-{o}"))
    teams = {}
    for t, d in D.items():
        if d["pa"] < 10:
            continue
        teams[t] = {
            "rate": round2(d["py"] / d["pa"]),
            "yds": round1(d["py"]),
            "vol": round1(d["pa"]),
            "g": len(d["g"]),
            "source": "2026 player-log pass attempts & yards allowed",
        }
    return teams


def opp_rec_rates(players, pos):
    """Aggregate opponent receiving yards / targets faced from pos logs."""
    D = collections.defaultdict(lambda: {"ry": 0.0, "tg": 0.0, "rc": 0.0, "g": set()})
    for p in players.values():
        if (p.get("pos") or p.get("grp")) != pos:
            continue
        for g in p.get("log") or []:
            if g.get("s") != 2026:
                continue
            o = g.get("o")
            if not o:
                continue
            tg = float(g.get("targets") or 0)
            ry = float(g.get("receiving_yards") or 0)
            rc = float(g.get("receptions") or 0)
            if tg or ry:
                D[o]["ry"] += ry
                D[o]["tg"] += tg
                D[o]["rc"] += rc
                D[o]["g"].add(str(g.get("g") or f"{g.get('w')}-{o}"))
    teams = {}
    for t, d in D.items():
        if d["tg"] < 10:
            continue
        teams[t] = {
            "rate": round2(d["ry"] / d["tg"]),
            "yds": round1(d["ry"]),
            "vol": round1(d["tg"]),
            "rec": round1(d["rc"]),
            "g": len(d["g"]),
            "source": f"2026 player-log targets & receiving yards allowed to {pos}s",
        }
    return teams


def board_pass_ypa(matchups):
    out = {}
    for r in matchups.get("cats", {}).get("pass", {}).get("best", []):
        for c in r.get("cols") or []:
            if c and c[0] == "Yds/att" and c[1] is not None:
                out[r["opp"]] = {
                    "rate": float(c[1]),
                    "raw": float(c[4]) if len(c) > 4 and c[4] is not None else None,
                    "rank": c[2],
                    "source": "matchups.json pass Yds/att (published board)",
                }
                break
    return out


def index_ids(pindex, pos):
    return {str(r[0]) for r in pindex if len(r) > 3 and r[3] == pos}


def resolve_matchup(p, board):
    nxt = p.get("next")
    if nxt and nxt.get("opp"):
        return nxt["opp"], bool(nxt.get("home")), nxt.get("date")
    if board:
        return board["opp"], board.get("site") == "vs", board.get("time")
    return None, None, None


def build_qb(players, pindex, matchups):
    pass_rows = [
        r
        for r in matchups.get("cats", {}).get("pass", {}).get("best", [])
        if r.get("pos") == "QB"
    ]
    by_aid = {str(r["aid"]): r for r in pass_rows}
    log_rates = opp_pass_rates(players)
    board_rates = board_pass_ypa(matchups)
    ids = index_ids(pindex, "QB") | set(by_aid)
    shown = {}
    hidden = collections.Counter()
    for pid in sorted(ids):
        p = players.get(pid)
        if not p:
            hidden["missing_player_file"] += 1
            continue
        if (p.get("pos") or p.get("grp")) != "QB" and by_aid.get(pid, {}).get("pos") != "QB":
            hidden["not_qb"] += 1
            continue
        board = by_aid.get(pid)
        opp, home, kick = resolve_matchup(p, board)
        if not opp:
            hidden["no_upcoming_opponent"] += 1
            continue
        season = p.get("season") or 2026
        cur = [g for g in (p.get("log") or []) if g.get("s") == season]
        atts = [float(g["attempts"]) for g in cur if g.get("attempts") is not None]
        if atts:
            avg_vol = statistics.mean(atts)
            window = f"2026 season ({len(atts)} games with pass attempts logged)"
            vol_games = len(atts)
        else:
            hidden["no_attempt_history"] += 1
            continue
        rate_info = None
        if opp in board_rates:
            rate_info = dict(board_rates[opp])
        elif opp in log_rates:
            rate_info = dict(log_rates[opp])
        else:
            hidden["missing_opp_rate"] += 1
            continue
        rate = float(rate_info["rate"])
        expected = round1(avg_vol * rate)
        row = {
            "id": pid,
            "name": p.get("name") or (board or {}).get("name"),
            "team": p.get("team") or (board or {}).get("team"),
            "pos": "QB",
            "market": "Passing yards",
            "opp": opp,
            "home": home,
            "kickoff": kick,
            "avg_vol": round1(avg_vol),
            "vol_label": "avg att",
            "vol_window": window,
            "vol_games": vol_games,
            "opp_rate": round(rate, 2) if rate >= 10 else round2(rate),
            "opp_rate_label": "yds allowed/att",
            "opp_rate_source": rate_info.get("source"),
            "opp_yds": rate_info.get("yds") or (log_rates.get(opp) or {}).get("yds"),
            "opp_vol": rate_info.get("vol") or (log_rates.get(opp) or {}).get("vol"),
            "opp_g": rate_info.get("g") or (log_rates.get(opp) or {}).get("g"),
            "expected": expected,
            "formula": f"{round1(avg_vol)} att × {round2(rate)} yds allowed/att = {expected} yds",
            "label": "Attempts × opponent rate estimate",
            "on_board": bool(board),
        }
        if board:
            if board.get("line") is not None:
                row["line"] = board["line"]
                row["line_src"] = board.get("src")
            if board.get("proj") is not None:
                row["sl_proj"] = board["proj"]
        shown[pid] = row
    return {
        "id": "qb_pass",
        "title": "QB · Passing yards",
        "method": "QB average pass attempts × opponent pass yards allowed per pass attempt",
        "volume_label": "Avg pass attempts",
        "rate_label": "Opp yds allowed/att",
        "scope": "Quarterbacks only.",
        "coverage": {
            "index": len(index_ids(pindex, "QB")),
            "shown": len(shown),
            "hidden": dict(hidden),
            "matchup_board": len(pass_rows),
            "matchup_board_shown": sum(1 for p in shown.values() if p.get("on_board")),
            "defs_with_rate": len(log_rates),
            "board_rate_teams": len(board_rates),
        },
        "teams": log_rates,
        "board_rate": {k: v["rate"] for k, v in board_rates.items()},
        "players": shown,
    }


def build_rec(players, pindex, matchups, pos, section_id, title):
    rec_rows = [
        r
        for r in matchups.get("cats", {}).get("rec", {}).get("best", [])
        if r.get("pos") == pos
    ]
    by_aid = {str(r["aid"]): r for r in rec_rows}
    log_rates = opp_rec_rates(players, pos)
    ids = index_ids(pindex, pos) | set(by_aid)
    shown = {}
    hidden = collections.Counter()
    for pid in sorted(ids):
        p = players.get(pid)
        if not p:
            hidden["missing_player_file"] += 1
            continue
        if (p.get("pos") or p.get("grp")) != pos and by_aid.get(pid, {}).get("pos") != pos:
            hidden[f"not_{pos.lower()}"] += 1
            continue
        board = by_aid.get(pid)
        opp, home, kick = resolve_matchup(p, board)
        if not opp:
            hidden["no_upcoming_opponent"] += 1
            continue
        season = p.get("season") or 2026
        cur = [g for g in (p.get("log") or []) if g.get("s") == season]
        tgts = [float(g["targets"]) for g in cur if g.get("targets") is not None]
        if board and board.get("adv", {}).get("tgt") is not None:
            avg_vol = float(board["adv"]["tgt"][0])
            window = "2026 season avg targets (matchups adv)"
            vol_games = len(tgts) or None
        elif tgts:
            avg_vol = statistics.mean(tgts)
            window = f"2026 season ({len(tgts)} games with targets logged)"
            vol_games = len(tgts)
        else:
            # fall back to receptions only if targets missing entirely
            recs = [float(g["receptions"]) for g in cur if g.get("receptions") is not None]
            if not recs:
                hidden["no_target_history"] += 1
                continue
            # need rate per reception if using receptions — only if we have rec-based rate
            # Prefer skip rather than mismatch: we have targets for virtually all WR/TE.
            hidden["no_target_history"] += 1
            continue
        if opp not in log_rates:
            hidden["missing_opp_rate"] += 1
            continue
        rate_info = dict(log_rates[opp])
        rate = float(rate_info["rate"])
        expected = round1(avg_vol * rate)
        row = {
            "id": pid,
            "name": p.get("name") or (board or {}).get("name"),
            "team": p.get("team") or (board or {}).get("team"),
            "pos": pos,
            "market": "Receiving yards",
            "opp": opp,
            "home": home,
            "kickoff": kick,
            "avg_vol": round1(avg_vol),
            "vol_label": "avg tgt",
            "vol_window": window,
            "vol_games": vol_games,
            "opp_rate": round2(rate),
            "opp_rate_label": "yds allowed/tgt",
            "opp_rate_source": rate_info.get("source"),
            "opp_yds": rate_info.get("yds"),
            "opp_vol": rate_info.get("vol"),
            "opp_g": rate_info.get("g"),
            "expected": expected,
            "formula": f"{round1(avg_vol)} tgt × {round2(rate)} yds allowed/tgt = {expected} yds",
            "label": "Targets × opponent rate estimate",
            "on_board": bool(board),
        }
        if board:
            if board.get("line") is not None:
                row["line"] = board["line"]
                row["line_src"] = board.get("src")
            if board.get("proj") is not None:
                row["sl_proj"] = board["proj"]
        shown[pid] = row
    return {
        "id": section_id,
        "title": title,
        "method": f"{pos} average targets × opponent receiving yards allowed per target (to {pos}s)",
        "volume_label": "Avg targets",
        "rate_label": "Opp yds allowed/tgt",
        "scope": f"{pos}s only.",
        "coverage": {
            "index": len(index_ids(pindex, pos)),
            "shown": len(shown),
            "hidden": dict(hidden),
            "matchup_board": len(rec_rows),
            "matchup_board_shown": sum(1 for p in shown.values() if p.get("on_board")),
            "defs_with_rate": len(log_rates),
        },
        "teams": log_rates,
        "players": shown,
    }


def main():
    meta = jload("meta.json")
    pindex = jload("pindex.json")["p"]
    matchups = jload("matchups.json")
    players = load_players_by_id()

    sections = [
        build_qb(players, pindex, matchups),
        build_rec(players, pindex, matchups, "WR", "wr_rec", "WR · Receiving yards"),
        build_rec(players, pindex, matchups, "TE", "te_rec", "TE · Receiving yards"),
    ]

    out = {
        "updated": meta.get("updated") or matchups.get("updated"),
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "built_et": datetime.now(ET).strftime("%Y-%m-%d %-I:%M %p ET"),
        "season": 2026,
        "week": matchups.get("week"),
        "note": "Display-only matchup layer. Does not replace Sports Labs projections or change picks. RB rush yards live in rb_expected_rush.json.",
        "sections": {s["id"]: s for s in sections},
    }
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
        f.write("\n")
    for s in sections:
        sample = next(iter(s["players"].values()), None)
        print(
            s["id"],
            "shown",
            s["coverage"]["shown"],
            "hidden",
            s["coverage"]["hidden"],
            "sample",
            (sample or {}).get("formula"),
            (sample or {}).get("name"),
        )


if __name__ == "__main__":
    main()
