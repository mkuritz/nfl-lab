#!/usr/bin/env python3
"""Display-only alternate floor dataset; no model/pick inputs modified.

Passing TDs ladder: presets 1/2/3 for QBs. Poisson calibrated from the same
per-game mean the board already uses (L10/season blend). Optional live alt
prices joined when a prop_prices sidecar is present. Recommend highest rung
clearing existing confidence/edge floors. Display-only.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
# Optional Bet Lab price/props sidecars (never required; never written back).
SIDECARS = [
    Path("/workspace/bet-lab/data"),
    Path("/workspace/wt/bet-passtd-ladder-1109/data"),
    D,
]

MIN_MODEL = 0.60  # Confirmed Spot / Low Hurdles L10 floor
MIN_EMP = 0.60
MIN_EDGE = 0.02


def load(n):
    if n == "v2.json":
        return json.loads((D / "v2.json").read_text())
    if n == "nba_hub.json":
        return json.loads((D / "nba_hub.json").read_text())
    if n == "plogs_nba.json":
        return json.loads((D / "plogs_nba.json").read_text())
    raise ValueError("Unsupported data filename")


def _sidecar(name):
    for root in SIDECARS:
        p = root / name
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                continue
    return None


def _norm(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())


def poisson_tail(lam, k_min):
    """P(X >= k_min) under Poisson(lam). Matches engines/nfl betmath usage."""
    if k_min <= 0:
        return 1.0
    if lam <= 0:
        return 0.0
    cdf = 0.0
    for k in range(int(k_min)):
        cdf += math.exp(-lam) * (lam ** k) / math.factorial(k)
    return max(1e-4, min(1 - 1e-4, 1.0 - cdf))


def projected_mean(values):
    """0.65*L10 + 0.35*all — same blend as pro_analytics.tail_prob."""
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not vals:
        return None
    recent = vals[:10]
    return 0.65 * (sum(recent) / len(recent)) + 0.35 * (sum(vals) / len(vals))


def am_to_imp(am):
    if am is None:
        return None
    am = float(am)
    if am >= 100:
        return 100.0 / (am + 100.0)
    if am <= -100:
        return (-am) / ((-am) + 100.0)
    return None


def build_pass_td_rungs(values, price_map, player):
    """Calibrated 1+/2+/3+ rungs + recommended floor."""
    mu = projected_mean(values)
    if mu is None:
        return None, None, []
    played = [float(v) for v in values if v is not None]
    rungs = []
    for k in (1, 2, 3):
        model_p = poisson_tail(mu, k)
        emp_n = min(len(played), 10)
        emp_h = sum(1 for v in played[:10] if v >= k)
        emp_p = (emp_h / emp_n) if emp_n else None
        # Blend like board: 0.6 parametric + 0.4 empirical Laplace
        if emp_n:
            p_emp = (emp_h + 1.5 * model_p) / (emp_n + 1.5)
            p = 0.6 * model_p + 0.4 * p_emp
        else:
            p = model_p
        line = k - 0.5
        q = price_map.get((_norm(player), line)) if price_map else None
        px = q.get("best") if q else None
        nv = None
        if q:
            nv = q.get("fair") if q.get("fair") is not None else q.get("nv")
        edge = None
        if nv is not None:
            edge = round(p - float(nv), 4)
        elif px is not None:
            imp = am_to_imp(px)
            if imp is not None:
                # light 6% one-sided de-vig approx when fair missing
                nv = round(imp / 1.06, 4)
                edge = round(p - nv, 4)
        clears = (p >= MIN_MODEL) and (emp_p is None or emp_p >= MIN_EMP or emp_n < 4)
        if edge is not None and px is not None and -500 < float(px) < 500:
            clears = clears and edge >= MIN_EDGE
        rungs.append(
            {
                "k": k,
                "line": line,
                "mu": round(mu, 3),
                "model_p": round(model_p, 4),
                "emp_p": round(emp_p, 4) if emp_p is not None else None,
                "p": round(p, 4),
                "price": px,
                "book": (q or {}).get("book") if q else None,
                "nv": round(float(nv), 4) if nv is not None else None,
                "edge": edge,
                "clears": bool(clears),
                "price_missing": px is None,
            }
        )
    recommend = 1
    for r in reversed(rungs):
        if r["clears"]:
            recommend = r["k"]
            break
    return mu, recommend, rungs


def load_pass_td_prices():
    """Map (norm_player, line) -> quote from prop_prices sidecar when present."""
    pp = _sidecar("prop_prices.json") or {}
    rows = pp.get("rows") if isinstance(pp, dict) else None
    out = {}
    if not isinstance(rows, dict):
        return out
    for key, q in rows.items():
        if not isinstance(key, str) or "|Passing Touchdowns|" not in key:
            continue
        parts = key.split("|")
        if len(parts) < 4:
            continue
        try:
            line = float(parts[3])
        except ValueError:
            continue
        out[(parts[2], line)] = q
    return out


def build():
    SPORT = "nfl"
    rows = []
    if SPORT == "nfl":
        v = load("v2.json")
        week = int(v["week"])
        updated = v["updated"]
        cats = {
            "Receiving yards": ("receiving_yards", [10, 15, 20, 25, 30, 40, 50, 60, 70]),
            "Receptions": ("receptions", [1, 2, 3, 4, 5, 6, 7]),
            "Rushing yards": ("rushing_yards", [5, 10, 15, 20, 25, 40, 50, 60, 70]),
            "Passing yards": ("passing_yards", [150, 170, 175, 180, 200, 210, 225, 250, 260]),
            "Passing TDs": ("passing_tds", [1, 2, 3]),
            "Rush + Rec yards": ("combo", [20, 40, 60, 80, 100]),
            "Kicking points": ("kick", [3, 4, 5, 6, 7, 8]),
        }
        price_map = load_pass_td_prices()
        for f in sorted((D / "players").glob("*.json")):
            p = json.load(open(f))
            nxt = p.get("next") or {}
            if not nxt or p.get("team") == "FA":
                continue
            logs = sorted(
                [g for g in p.get("log", []) if g.get("s") == 2026 and g.get("w", 99) <= week],
                key=lambda g: g["w"],
                reverse=True,
            )
            for cat, (stat, presets) in cats.items():
                if cat in ("Passing yards", "Passing TDs") and p.get("pos") != "QB":
                    continue
                if cat == "Kicking points" and p.get("pos") != "K":
                    continue
                if cat != "Kicking points" and p.get("pos") not in ["QB", "RB", "WR", "TE", "FB"]:
                    continue
                games = []
                for g in logs:
                    value = g.get(stat)
                    if stat == "combo":
                        value = (
                            (g.get("rushing_yards") or 0) + (g.get("receiving_yards") or 0)
                            if g.get("rushing_yards") is not None and g.get("receiving_yards") is not None
                            else None
                        )
                    if stat == "kick":
                        value = (
                            3 * g["fg_made"] + g["pat_made"]
                            if g.get("fg_made") is not None and g.get("pat_made") is not None
                            else None
                        )
                    # Passing TDs: omitted zero when the QB attempted passes → treat as 0
                    if stat == "passing_tds" and value is None and g.get("attempts") is not None:
                        value = 0.0
                    games.append(
                        {
                            "label": "W" + str(g["w"]) + " " + str(g.get("o", "")),
                            "value": value,
                            "dnp": g.get("snap") == 0,
                            "week": g.get("w"),
                        }
                    )
                if not any(g["value"] is not None for g in games):
                    continue
                row = dict(
                    id=p["id"],
                    name=p["name"],
                    team=p["team"],
                    pos=p["pos"],
                    category=cat,
                    presets=presets,
                    games=games,
                    opp=nxt.get("opp"),
                    time=nxt.get("date"),
                    status=(p.get("inj") or {}).get("status") or "No designation in snapshot",
                )
                if cat == "Passing TDs":
                    vals = [g["value"] for g in games if not g.get("dnp")]
                    mu, recommend, rungs = build_pass_td_rungs(vals, price_map, p["name"])
                    if mu is not None:
                        row["mu"] = round(mu, 3)
                        row["recommend"] = recommend
                        row["rungs"] = rungs
                        # Easy presets still drive streak math; defaultFloor prefers recommend.
                        row["presets"] = [1, 2, 3]
                rows.append(row)
    else:
        h = load("nba_hub.json")
        logs = load("plogs_nba.json")
        updated = h["updated"]
        week = None
        cats = {
            "Points": ("points", [5, 10, 15, 20, 25, 30]),
            "Rebounds": ("totalRebounds", [2, 3, 4, 5, 6, 8, 10]),
            "Assists": ("assists", [1, 2, 3, 4, 5, 6, 8]),
            "Threes": ("threePointFieldGoalsMade-threePointFieldGoalsAttempted", [1, 2, 3, 4]),
        }
        people = {}
        injuries = {str(x["id"]): x.get("status") for x in h.get("injuries", [])}
        for unit in h.get("units", []):
            for side in ["first", "second"]:
                for p in unit.get(side, {}).get("players", []):
                    people[str(p["id"])] = p
        for p in h.get("props", []):
            people.setdefault(
                str(p["aid"]),
                dict(id=p["aid"], name=p["player"], team=p["team"], pos=p.get("pos", "Unknown")),
            )
        for aid, p in people.items():
            slate = next((g for g in h["slate"] if p["team"] in [g.get("home"), g.get("away")]), {})
            gl = sorted(
                [g for g in logs.get(aid, []) if "2026-10-20" <= g.get("d", "") < "2027-07-01"],
                key=lambda g: g["d"],
                reverse=True,
            )
            for cat, (stat, presets) in cats.items():
                games = [
                    dict(
                        label=g["d"] + " " + str(g.get("o", "")),
                        value=(g.get("s") or {}).get(stat),
                        dnp=(g.get("s") or {}).get("minutes") == 0,
                    )
                    for g in gl
                ]
                if not any(g["value"] is not None for g in games):
                    continue
                rows.append(
                    dict(
                        id=aid,
                        name=p["name"],
                        team=p["team"],
                        pos=p.get("pos", "Unknown"),
                        category=cat,
                        presets=presets,
                        games=games,
                        opp=slate.get("away") if p["team"] == slate.get("home") else slate.get("home"),
                        time=slate.get("time"),
                        status=injuries.get(aid) or p.get("status") or "No designation in snapshot",
                    )
                )
    out = dict(
        window="2026 NFL through completed slate-week logs" if SPORT == "nfl" else "2026-10-20 through 2027-06-30",
        sport=SPORT,
        season="2026 NFL" if SPORT == "nfl" else "2026–27 NBA",
        updated=updated,
        categories=list(cats),
        thresholds={"min_model": MIN_MODEL, "min_emp": MIN_EMP, "min_edge": MIN_EDGE},
        rows=rows,
    )
    (D / "low_hurdles_alternates.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(SPORT, len(rows), {c: sum(r["category"] == c for r in rows) for c in cats})
    if SPORT == "nfl":
        from collections import Counter
        ptd = [r for r in rows if r["category"] == "Passing TDs"]
        print("pass_td_recommend", dict(Counter(r.get("recommend") for r in ptd)))
        missing_px = sum(1 for r in ptd for x in (r.get("rungs") or []) if x.get("price_missing"))
        print("pass_td_rungs_price_missing", missing_px, "of", sum(len(r.get("rungs") or []) for r in ptd))


if __name__ == "__main__":
    build()
