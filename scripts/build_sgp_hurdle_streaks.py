#!/usr/bin/env python3
"""NFL Hub Same Game Hurdle Streak Bundle (display-only preview).

For each published slate prop (volume markets) pick the HIGHEST hurdle the
player has cleared this season at a chosen rate (default 100%), using posted
alt lines when present, else standard increments. Bundle qualifying legs into
per-game parlays. Does not change models, picks, or other Hub tabs.
Never writes sportsbook names or deep links into the output.
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ET = ZoneInfo("America/New_York")
SEASON = 2026
THRESHOLDS = (100, 90, 80, 75)  # percent; default is 100
MIN_GAMES = 6
DEFAULT_THRESHOLD = 100

# Optional already-built price sidecar (never required; never written back).
# Hub CI does not mount Bet Lab; v2 published lines + standard increments still work.
PRICE_SIDECARS = [
    DATA / "prop_prices.json",
    Path("/workspace/bet-lab-engine/data/prop_prices.json"),
    Path("/workspace/bet-lab/data/prop_prices.json"),
]
INJURY_ROOTS = [
    DATA,
    Path("/workspace/bet-lab-engine/data"),
]

MARKETS = {
    "Passing Yards": {"stat": "passing_yards", "kind": "yards", "step": 5, "short": "Pass Yds", "family": "pass", "dvp_pos": "QB", "dvp_field": "yds", "dvp_label": "QBs"},
    "Pass Completions": {"stat": "completions", "kind": "count", "step": 1, "short": "Completions", "family": "pass", "dvp_pos": "QB", "dvp_field": "yds", "dvp_label": "QBs"},
    "Passing Attempts": {"stat": "attempts", "kind": "count", "step": 1, "short": "Attempts", "family": "pass", "dvp_pos": "QB", "dvp_field": "yds", "dvp_label": "QBs"},
    "Rushing Yards": {"stat": "rushing_yards", "kind": "yards", "step": 5, "short": "Rush Yds", "family": "rush", "dvp_pos": "RB", "dvp_field": "yds", "dvp_label": "RBs"},
    "Carries": {"stat": "carries", "kind": "count", "step": 1, "short": "Carries", "family": "rush", "dvp_pos": "RB", "dvp_field": "yds", "dvp_label": "RBs"},
    "Receiving Yards": {"stat": "receiving_yards", "kind": "yards", "step": 5, "short": "Rec Yds", "family": "rec", "dvp_pos": None, "dvp_field": "yds", "dvp_label": None},
    "Receptions": {"stat": "receptions", "kind": "count", "step": 1, "short": "Receptions", "family": "rec", "dvp_pos": None, "dvp_field": "rec", "dvp_label": None},
    "Rushing Plus Receiving Yards": {"stat": "rush_rec", "kind": "yards", "step": 5, "short": "Rush+Rec Yds", "family": "rush_rec", "dvp_pos": None, "dvp_field": "yds", "dvp_label": None},
}

BAD_ST = ("out", "doubtful", "ir", "injured reserve", "inactive", "suspended", "pup", "nfi")
# same-player families that should not both appear in a parlay
FAMILY_BLOCK = {
    "pass": {"pass"},
    "rush": {"rush", "rush_rec"},
    "rec": {"rec", "rush_rec"},
    "rush_rec": {"rush", "rec", "rush_rec"},
}


def ld(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return default


def norm_name(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())


def st_key(s):
    return " ".join((s or "").lower().replace("-", " ").split())


def is_out(st):
    t = st_key(st)
    return any(b == t or t.startswith(b + " ") or f" {b} " in f" {t} " for b in BAD_ST) or t in ("injured reserve", "physically unable to perform")


def floor_from_line(line):
    """Display floor and clear minimum for an over line."""
    line = float(line)
    if line == int(line):
        n = int(line)
        return n, n
    n = math.floor(line) + 1
    return n, n


def game_total(g, stat):
    if stat == "rush_rec":
        ry, rc = g.get("rushing_yards"), g.get("receiving_yards")
        if ry is None and rc is None:
            return None
        return float(ry or 0) + float(rc or 0)
    v = g.get(stat)
    return None if v is None else float(v)


def book_label_from_quote(q):
    """Return (price, 'Book X') using lettered book codes only. Never copies raw book names."""
    if not isinstance(q, dict):
        return None, None
    best = q.get("best")
    bks = q.get("bks") if isinstance(q.get("bks"), dict) else {}
    letter = None
    if bks:
        for k, v in bks.items():
            if best is not None and v == best and len(str(k)) == 1 and str(k).isalpha():
                letter = str(k).upper()
                break
        if letter is None:
            for k in bks:
                if len(str(k)) == 1 and str(k).isalpha():
                    letter = str(k).upper()
                    if best is None:
                        best = bks[k]
                    break
    if best is None:
        return None, None
    # If we only have a price and no letter, still return the price with no name.
    book = f"Book {letter}" if letter else None
    try:
        best = int(best) if float(best) == int(float(best)) else float(best)
    except Exception:
        pass
    return best, book


def load_price_index():
    """(norm_player, market, line) -> sanitized {price, book}."""
    out = {}
    for p in PRICE_SIDECARS:
        d = ld(p, None)
        if not d or not isinstance(d.get("rows"), dict):
            continue
        for key, q in d["rows"].items():
            parts = str(key).split("|")
            if len(parts) < 4 or parts[0] != "nfl":
                continue
            mk, who, ln = parts[1], parts[2], parts[3]
            try:
                line = float(ln)
            except ValueError:
                continue
            price, book = book_label_from_quote(q)
            if price is None:
                continue
            out[(who, mk, line)] = {"price": price, "book": book}
        break
    return out


def load_injury_maps():
    """name-norm / aid -> status from engine gold + manual + availability."""
    by_n, by_aid = {}, {}
    for root in INJURY_ROOTS:
        av = ld(root / "availability.json", {}) or {}
        for n, row in (av.get("nfl") or {}).items():
            if isinstance(row, dict) and row.get("st"):
                by_n[n] = row.get("st")
        st = ld(root / "nfl_status.json", {}) or {}
        for row in st.get("players") or []:
            if isinstance(row, (list, tuple)) and len(row) >= 3:
                by_n[norm_name(row[0])] = row[2]
        man = ld(root / "nfl_injuries_manual.json", {}) or {}
        today = datetime.now(ET).date().isoformat()
        for x in man.get("players") or []:
            until = x.get("expires") or x.get("until")
            if until and today > str(until)[:10]:
                continue
            if x.get("aid"):
                by_aid[str(x["aid"])] = x.get("st")
            if x.get("player"):
                by_n[norm_name(x["player"])] = x.get("st")
        if by_n or by_aid:
            break
    return by_n, by_aid


def player_status(row, plog, by_n, by_aid):
    inj = row.get("inj") if isinstance(row.get("inj"), dict) else {}
    st = inj.get("st") or inj.get("status")
    if not st and isinstance(plog, dict) and isinstance(plog.get("inj"), dict):
        st = plog["inj"].get("status") or plog["inj"].get("st")
    if by_aid.get(str(row.get("aid") or "")):
        st = by_aid[str(row["aid"])]
    nm = norm_name(row.get("name") or (plog or {}).get("name"))
    if by_n.get(nm):
        st = by_n[nm]
    detail = inj.get("d") or inj.get("detail") or ((plog or {}).get("inj") or {}).get("detail")
    return st, detail


def dvp_bucket(pos, meta):
    if meta.get("dvp_pos"):
        return meta["dvp_pos"], meta.get("dvp_label") or meta["dvp_pos"] + "s"
    pos = (pos or "").upper()
    if pos == "QB":
        return "QB", "QBs"
    if pos == "RB":
        return "RB", "RBs"
    if pos == "TE":
        return "TE", "TEs"
    return "WR", "WRs"


def tier_from_rank(rank):
    if rank is None:
        return None
    r = int(rank)
    if r <= 10:
        return "tougher"
    if r >= 23:
        return "easier"
    return "middle"


def season_games(plog, week):
    games = [
        g for g in (plog.get("log") or [])
        if g.get("s") == SEASON and isinstance(g.get("w"), int) and g["w"] <= week
    ]
    return sorted(games, key=lambda g: g["w"])


def eligible_games(games, stat):
    """Completed appearances with a total; skip 0-snap DNPs. No mid-game injury flag in logs."""
    out = []
    for g in games:
        snap = g.get("snap")
        if snap is not None and snap == 0:
            continue
        val = game_total(g, stat)
        if val is None:
            continue
        out.append((g, val))
    return out


def clear_rate(elig, clear_min):
    if not elig:
        return 0, 0, 0.0, 0
    hits = sum(1 for _, v in elig if v >= clear_min)
    n = len(elig)
    # current streak from most recent
    streak = 0
    for _, v in reversed(elig):
        if v >= clear_min:
            streak += 1
        else:
            break
    return hits, n, hits / n if n else 0.0, streak


def standard_rungs(kind, step, values, published=None):
    if not values:
        return []
    mx = max(values)
    rungs = []
    if kind == "yards":
        # half-lines at step-0.5 (10.5, 15.5...) plus integers used as 15+
        top = int(math.floor(mx / step) * step) + step
        x = step
        while x <= top:
            rungs.append(x - 0.5)
            x += step
    else:
        top = int(math.floor(mx)) + 1
        for k in range(1, top + 1):
            rungs.append(k - 0.5)
    if published is not None:
        rungs.append(float(published))
    return sorted(set(rungs))


def pick_rung(rungs, elig, threshold, published, alts_only_first=True):
    """Highest rung with clear rate >= threshold. Prefer posted alts; extend below if none qualify."""
    need = threshold / 100.0
    posted = sorted(rungs)
    def ok(line):
        _, n, rate, _ = clear_rate(elig, floor_from_line(line)[1])
        return n >= MIN_GAMES and rate + 1e-12 >= need

    qualify = [ln for ln in posted if ok(ln)]
    if qualify:
        return max(qualify), "posted"
    # extend downward with standard increments so a 100% floor can still show
    values = [v for _, v in elig]
    kind = "yards" if (posted and min(posted) >= 5) or (values and max(values) >= 15) else "count"
    # kind decided by caller better — use values magnitude
    step = 5 if values and max(values) >= 15 else 1
    kind = "yards" if step == 5 else "count"
    extra = standard_rungs(kind, step, values, published)
    qualify = [ln for ln in extra if ok(ln)]
    if qualify:
        return max(qualify), "extended"
    return None, None


def am_parlay(prices):
    """Naive straight-leg parlay from American prices. Not an official SGP quote."""
    if not prices or any(p is None for p in prices):
        return None
    dec = 1.0
    for a in prices:
        a = float(a)
        if a > 0:
            dec *= 1 + a / 100.0
        elif a < 0:
            dec *= 1 + 100.0 / abs(a)
        else:
            return None
    am = round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1))
    return int(am)


def team_weeks(all_logs, team, week):
    weeks = set()
    for pl in all_logs:
        if (pl.get("team") or "") != team:
            continue
        for g in pl.get("log") or []:
            if g.get("s") == SEASON and isinstance(g.get("w"), int) and 1 <= g["w"] < week:
                weeks.add(g["w"])
    return weeks


def build_narrative(player, market, line, hits, n, rate, streak, elig, meta_games, upcoming, missed, bye, wx, status, status_detail, pos_label):
    parts = []
    pct = int(round(rate * 100))
    parts.append(
        f"{player} has cleared Over {line:g} {market} in {hits} of {n} games this season ({pct}%)."
    )
    if streak and streak == n:
        parts.append(f"That is every game in the log — a {streak}-game streak.")
    elif streak and streak > 1:
        parts.append(f"The current streak is {streak} straight.")
    # snap share
    snaps = [g["snap"] for g in meta_games if g.get("snap") is not None and g["snap"] > 0]
    if snaps:
        med = median(snaps)
        # treat values > 100 as snap counts; otherwise as percent
        unit = "snaps" if med > 100 else "%"
        low = []
        for g in meta_games:
            s = g.get("snap")
            if s is None:
                continue
            if unit == "%" and med >= 50 and s <= 50 and s < med - 15:
                low.append(g)
            elif unit == "snaps" and med >= 20 and s <= med * 0.5:
                low.append(g)
        if low:
            bits = []
            for g in low:
                bits.append(
                    f"Week {g['w']} vs {g['o']} ({g['snap']:g}{unit}; typical {med:g}{unit})"
                )
            parts.append("Lower snap share than usual in " + "; ".join(bits) + ". Those games stay in the rate — the log does not flag whether he left with an injury.")
    if bye:
        parts.append("Bye week" + ("s " if len(bye) > 1 else " ") + ", ".join(f"{w}" for w in bye) + " " + ("are" if len(bye) > 1 else "is") + " not counted.")
    if missed:
        parts.append(
            "No game log for Week "
            + ", ".join(str(w) for w in missed)
            + " even though the team played — not counted in the rate. The log does not say why."
        )
    # upcoming vs prior defenses
    if upcoming and upcoming.get("rank") is not None and upcoming.get("faced_ranks"):
        faced = upcoming["faced_ranks"]
        med_r = upcoming.get("faced_median")
        rk = upcoming["rank"]
        oa = upcoming.get("opp") or "this week's opponent"
        label = upcoming.get("pos_label") or pos_label
        allowed = upcoming.get("allowed")
        allowed_lbl = upcoming.get("allowed_label") or "per game allowed"
        g_n = upcoming.get("dvp_games")
        clause = f"{oa} ranks {rk} of 32 vs {label} this season"
        if allowed is not None:
            clause += f" ({allowed:g} {allowed_lbl}"
            if g_n:
                clause += f" over {g_n} games"
            clause += ")"
        clause += f". Defenses in the games that built this mark have a median season rank of {med_r} of 32 vs {label}"
        if rk <= med_r - 3:
            clause += f", so this matchup is tougher than those games (lower rank allows less)."
        elif rk >= med_r + 3:
            clause += f", so this matchup is easier than those games (higher rank allows more)."
        else:
            clause += f", so this matchup is similar in rank to those games."
        parts.append(clause)
    elif upcoming and upcoming.get("rank") is not None:
        oa = upcoming.get("opp") or "this week's opponent"
        label = upcoming.get("pos_label") or pos_label
        parts.append(f"This week vs {oa}: season rank {upcoming['rank']} of 32 vs {label}. Not enough prior-opponent ranks to compare.")
    if wx:
        if wx.get("dome"):
            parts.append("This week's game is scheduled indoors.")
        else:
            bits = []
            if wx.get("temp") is not None:
                bits.append(f"{round(wx['temp'])}°")
            if wx.get("wind") is not None and wx["wind"] >= 10:
                bits.append(f"wind {round(wx['wind'])} mph")
            if bits:
                parts.append("This week's forecast: " + ", ".join(bits) + ".")
    if status and st_key(status) not in ("", "active") and not is_out(status):
        msg = f"Listed {status} this week"
        if status_detail:
            msg += f" ({status_detail})"
        msg += "."
        parts.append(msg)
    return " ".join(parts)


def main():
    v2 = json.loads((DATA / "v2.json").read_text())
    week = int(v2.get("week") or 0)
    rows_in = v2.get("rows") or []
    dvp = ld(DATA / "nfl_dvp.json", {}) or {}
    dvp_teams = dvp.get("teams") or {}
    viz = ld(DATA / "dvp_viz.json", {}) or {}
    trend = viz.get("trend") or {}
    prices = load_price_index()
    by_n, by_aid = load_injury_maps()

    # player cache
    player_cache = {}

    def load_player(aid):
        aid = str(aid)
        if aid not in player_cache:
            p = DATA / "players" / f"{aid}.json"
            player_cache[aid] = json.loads(p.read_text()) if p.exists() else None
        return player_cache[aid]

    # all logs for bye detection
    team_played = {}

    def played_weeks(team):
        if team not in team_played:
            weeks = set()
            for r in rows_in:
                if r.get("team") != team:
                    continue
                pl = load_player(r.get("aid"))
                if not pl:
                    continue
                for g in pl.get("log") or []:
                    if g.get("s") == SEASON and isinstance(g.get("w"), int) and g["w"] < week:
                        weeks.add(g["w"])
            team_played[team] = weeks
        return team_played[team]

    # unique slate props (aid, market) — keep first row
    seen = set()
    slate = []
    for r in rows_in:
        mk = r.get("market")
        if mk not in MARKETS:
            continue
        key = (str(r.get("aid")), mk)
        if key in seen:
            continue
        seen.add(key)
        slate.append(r)

    # compute legs once; rungs per threshold
    legs_by_thr = {t: [] for t in THRESHOLDS}
    skipped = defaultdict(int)

    for r in slate:
        mk = r["market"]
        meta = MARKETS[mk]
        aid = str(r.get("aid") or "")
        plog = load_player(aid)
        st, detail = player_status(r, plog, by_n, by_aid)
        if is_out(st):
            skipped["unavailable"] += 1
            continue
        if not plog:
            skipped["no_log"] += 1
            continue
        games = season_games(plog, week)
        elig = eligible_games(games, meta["stat"])
        if len(elig) < MIN_GAMES:
            skipped["short_sample"] += 1
            continue

        published = r.get("line")
        who = norm_name(r.get("name"))
        alt_lines = sorted({ln for (n, m, ln) in prices if n == who and m == mk})
        if published is not None:
            alt_lines = sorted(set(alt_lines + [float(published)]))
        values = [v for _, v in elig]
        if alt_lines:
            rungs = alt_lines
        else:
            rungs = standard_rungs(meta["kind"], meta["step"], values, published)

        # per-game meta for popup / narrative
        gmeta = []
        for g, val in elig:
            snap = g.get("snap")
            gmeta.append({
                "w": g.get("w"),
                "s": SEASON,
                "o": g.get("o"),
                "home": bool(g.get("home")),
                "v": val,
                "snap": snap,
            })

        team_w = played_weeks(r.get("team"))
        logged_w = {g["w"] for g, _ in elig}
        bye, missed = [], []
        for w in range(1, week):
            if w in logged_w:
                continue
            if w not in team_w:
                bye.append(w)
            else:
                # 0-snap already excluded from elig; check if present as DNP
                raw = [g for g in games if g.get("w") == w]
                if raw and raw[0].get("snap") == 0:
                    missed.append(w)
                elif not raw:
                    missed.append(w)

        # DvP upcoming + prior
        pos = r.get("pos") or plog.get("pos")
        bucket, pos_label = dvp_bucket(pos, meta)
        if mk in ("Receiving Yards", "Receptions", "Rushing Plus Receiving Yards"):
            bucket, pos_label = dvp_bucket(pos, {"dvp_pos": None})
        oa = r.get("oa")
        dvp_row = (dvp_teams.get(oa) or {}).get(bucket) or {}
        upcoming = {
            "opp": oa,
            "home": bool(r.get("home")),
            "rank": r.get("dvr") if r.get("dvr") is not None else dvp_row.get("r"),
            "rank_source": "stat" if r.get("dvr") is not None else "position",
            "grade": r.get("grade"),
            "ratio": r.get("ratio"),
            "allowed": dvp_row.get(meta["dvp_field"]) if meta.get("dvp_field") in dvp_row else dvp_row.get("yds"),
            "allowed_label": (
                "receptions/game allowed" if meta["dvp_field"] == "rec" and "rec" in dvp_row
                else "yards/game allowed"
            ),
            "dvp_games": (dvp_teams.get(oa) or {}).get("g"),
            "pos_label": pos_label,
            "pos_bucket": bucket,
        }
        # prior opponent season ranks (same position table — comparable across games)
        faced = []
        for gm in gmeta:
            opp = gm["o"]
            opp_row = (dvp_teams.get(opp) or {}).get(bucket) or {}
            rk = opp_row.get("r")
            week_allowed = None
            tr = (trend.get(opp) or {}).get(bucket) or []
            for pair in tr:
                if isinstance(pair, (list, tuple)) and len(pair) >= 2 and pair[0] == gm["w"]:
                    week_allowed = pair[1]
                    break
            gm["dvp_rank"] = rk
            gm["dvp_tier"] = tier_from_rank(rk)
            gm["week_allowed"] = week_allowed
            if rk is not None:
                faced.append(rk)
        upcoming["faced_ranks"] = faced
        upcoming["faced_median"] = int(round(median(faced))) if faced else None

        wx = r.get("wx") if isinstance(r.get("wx"), dict) else None

        for thr in THRESHOLDS:
            line, src = pick_rung(rungs, elig, thr, published)
            if line is None:
                continue
            clear_min = floor_from_line(line)[1]
            hits, n, rate, streak = clear_rate(elig, clear_min)
            px = prices.get((who, mk, float(line))) or {}
            # also check published row price if the rung equals the published line
            if not px and published is not None and float(line) == float(published) and r.get("best") is not None:
                bbook = r.get("bbook")
                book = bbook if isinstance(bbook, str) and bbook.startswith("Book ") or (isinstance(bbook, str) and bbook.startswith("Exchange")) else None
                # v2 already anonymizes; pass through only Book/Exchange labels
                if isinstance(bbook, str) and (bbook.startswith("Book ") or bbook.startswith("Exchange")):
                    book = bbook
                px = {"price": r.get("best"), "book": book}
            narrative = build_narrative(
                r.get("name"), mk, line, hits, n, rate, streak, elig, gmeta,
                upcoming, missed, bye, wx, st, detail, pos_label,
            )
            tip = r.get("time")
            legs_by_thr[thr].append({
                "id": f"{aid}|{mk}|{line}",
                "aid": aid,
                "player": r.get("name"),
                "team": r.get("team"),
                "pos": pos,
                "opp": r.get("opp"),
                "oa": oa,
                "home": bool(r.get("home")),
                "game": str(r.get("game") or ""),
                "time": tip,
                "head": r.get("head"),
                "market": mk,
                "market_short": meta["short"],
                "family": meta["family"],
                "line": float(line),
                "floor": clear_min,
                "floor_label": f"{clear_min}+ {meta['short']}",
                "published_line": float(published) if published is not None else None,
                "rung_source": src,
                "hits": hits,
                "games": n,
                "rate": round(rate, 4),
                "rate_pct": int(round(rate * 100)),
                "streak": streak,
                "price": px.get("price"),
                "book": px.get("book"),
                "status": st if st and st_key(st) not in ("", "active") else None,
                "status_detail": detail,
                "games_log": gmeta,
                "upcoming": upcoming,
                "narrative": narrative,
            })

    MARKET_RANK = {
        "Passing Yards": 0,
        "Rushing Yards": 1,
        "Rushing Plus Receiving Yards": 1,
        "Receiving Yards": 2,
        "Receptions": 3,
        "Carries": 4,
        "Pass Completions": 5,
        "Passing Attempts": 6,
    }

    def score(leg):
        # Prefer season rate, then yards markets over count floors, then higher hurdle.
        return (
            -leg["rate"],
            MARKET_RANK.get(leg["market"], 9),
            -float(leg["floor"]),
            -leg["games"],
            -leg["streak"],
            leg["player"] or "",
        )

    def parlay_ok(leg):
        fl, mk = float(leg["floor"]), leg["market"]
        if mk == "Passing Yards":
            return fl >= 100
        if mk in ("Rushing Yards", "Rushing Plus Receiving Yards"):
            return fl >= 25
        if mk == "Receiving Yards":
            return fl >= 15
        if mk in ("Receptions", "Carries", "Pass Completions", "Passing Attempts"):
            return fl >= 3
        return True

    def bundle(game_legs):
        """2–4 legs, best rates, one leg per player, no correlated family repeats."""
        picked = []
        used_players, used_families = set(), defaultdict(set)
        pool = [x for x in sorted(game_legs, key=score) if parlay_ok(x)]
        if len(pool) < 2:
            pool = sorted(game_legs, key=score)
        for leg in pool:
            if len(picked) >= 4:
                break
            if leg["aid"] in used_players:
                continue
            fams = used_families[leg["aid"]]
            blocked = FAMILY_BLOCK.get(leg["family"], {leg["family"]})
            if fams & blocked:
                continue
            picked.append(leg)
            used_players.add(leg["aid"])
            fams.add(leg["family"])
        if len(picked) < 2:
            return None
        rates = [p["rate"] for p in picked]
        prod = 1.0
        for x in rates:
            prod *= x
        prices_ = [p["price"] for p in picked]
        books = sorted({p["book"] for p in picked if p.get("book")})
        return {
            "legs": [
                {k: p[k] for k in (
                    "aid", "player", "team", "pos", "market", "market_short", "line",
                    "floor_label", "hits", "games", "rate", "rate_pct", "streak",
                    "price", "book", "head", "family",
                )}
                for p in picked
            ],
            "n_legs": len(picked),
            "combined_rate": round(prod, 4),
            "combined_pct": int(round(prod * 100)),
            "combined_note": "Combined historical clear rate is the product of each leg's season rate. Legs are not independent (same game, and often the same script).",
            "parlay_price": am_parlay(prices_) if all(p is not None for p in prices_) else None,
            "books": books,
            "price_note": (
                "Straight-leg parlay price from the listed books at these exact rungs — not an official same-game parlay quote."
                if all(p is not None for p in prices_) else
                "No full parlay price: at least one rung has no listed book price (often an alt below the main line)."
            ),
        }

    def game_label(legs):
        teams = sorted({p["team"] for p in legs if p.get("team")})
        # home/away
        home = next((p["team"] for p in legs if p.get("home")), None)
        away = next((p["team"] for p in legs if p.get("team") and p["team"] != home), None)
        if home and away:
            return f"{away} @ {home}"
        if len(teams) == 2:
            return f"{teams[0]} vs {teams[1]}"
        return " / ".join(teams) or "Game"

    def fmt_time(t):
        if not t:
            return None
        try:
            d = datetime.fromisoformat(str(t).replace("Z", "+00:00")).astimezone(ET)
            return d.strftime("%a %-I:%M %p ET")
        except Exception:
            return None

    payload_thr = {}
    for thr in THRESHOLDS:
        legs = legs_by_thr[thr]
        by_game = defaultdict(list)
        for p in legs:
            by_game[p["game"]].append(p)
        games_out = []
        for gid, gl in by_game.items():
            parlay = bundle(gl)
            t0 = gl[0]
            games_out.append({
                "game": gid,
                "label": game_label(gl),
                "time": t0.get("time"),
                "time_et": fmt_time(t0.get("time")),
                "parlay": parlay,
                "legs": sorted(gl, key=score),
                "n_qualify": len(gl),
            })
        games_out.sort(key=lambda g: (g.get("time") or "9999", g["label"]))
        # by player
        by_pl = defaultdict(list)
        for p in legs:
            by_pl[(p["aid"], p["player"], p["team"], p.get("pos"), p.get("head"), p.get("game"), p.get("time"), p.get("opp"))].append(p)
        players_out = []
        for (aid, name, team, pos, head, game, time, opp), pl in by_pl.items():
            players_out.append({
                "aid": aid,
                "player": name,
                "team": team,
                "pos": pos,
                "head": head,
                "game": game,
                "time": time,
                "time_et": fmt_time(time),
                "opp": opp,
                "legs": sorted(pl, key=score),
            })
        players_out.sort(key=lambda p: (p.get("time") or "9999", p["team"] or "", p["player"] or ""))
        payload_thr[str(thr)] = {
            "games": games_out,
            "players": players_out,
            "n_legs": len(legs),
            "n_games": sum(1 for g in games_out if g.get("parlay")),
            "n_games_total": len(games_out),
        }

    now = datetime.now(timezone.utc)
    out = {
        "updated": v2.get("updated"),
        "built_at": now.strftime("%Y-%m-%dT%H:%MZ"),
        "built_et": datetime.now(ET).strftime("%b %-d · %-I:%M %p ET"),
        "week": week,
        "season": SEASON,
        "slate_note": f"Hub slate is Week {week} (Sunday Nov 15, 2026). Request mentioned Week 11; this preview follows the Hub week number.",
        "default_threshold": DEFAULT_THRESHOLD,
        "thresholds": list(THRESHOLDS),
        "min_games": MIN_GAMES,
        "definition": {
            "view": "Season (current-season completed games with a snap, excluding 0-snap DNPs). Bye weeks are not counted.",
            "clear": "Over a half-line (24.5 → 25+) or ≥ an integer line. The board shows the HIGHEST qualifying rung, not the lowest.",
            "rungs": "Posted alt lines and the published main line when we already have them; if no posted rung qualifies, standard increments (5 yards or 1 count) extend below so a true season floor can still show. No new odds pulls.",
            "threshold": "Default 100% (cleared in every game). UI also offers 90, 80, and 75. Minimum 6 games played.",
            "parlay": "2–4 legs per game, best season rates then streak then higher rung. At most one correlated family per player (pass volume, rush volume, receiving volume, or rush+rec). Combined rate is the product of individual season rates and is not independent.",
            "injuries": "Out, Doubtful, IR, inactive, and similar holds are dropped, including manual official Outs. Questionable stays.",
            "injury_exits": "Game logs do not flag mid-game injury exits. 0-snap DNPs are excluded; unusually low snap share is noted in the narrative but still counted.",
            "display_only": True,
        },
        "skipped": dict(skipped),
        "by_threshold": payload_thr,
    }
    path = DATA / "sgp_hurdle_streaks.json"
    # Strip nothing else; games_log is needed for the popup. Keep file readable.
    path.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    dflt = payload_thr[str(DEFAULT_THRESHOLD)]
    print(
        f"wrote {path} · week {week} · default {DEFAULT_THRESHOLD}% · "
        f"{dflt['n_legs']} legs · {dflt['n_games']} parlays / {dflt['n_games_total']} games · skipped {dict(skipped)}"
    )
    # sample 3 games at 100% for the log (no book names beyond Book X already sanitized)
    for g in dflt["games"][:3]:
        p = g.get("parlay")
        if not p:
            print(f"  {g['label']} {g.get('time_et')}: no parlay ({g['n_qualify']} qualifying legs)")
            continue
        legs = ", ".join(
            f"{x['player']} {x['floor_label']} {x['hits']}/{x['games']}"
            for x in p["legs"]
        )
        print(f"  {g['label']} {g.get('time_et')}: {p['n_legs']} legs · combined {p['combined_pct']}% · {legs}")


if __name__ == "__main__":
    main()
