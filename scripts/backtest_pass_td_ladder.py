#!/usr/bin/env python3
"""Nov 8 / Week 9 finals backtest for Passing TD ladder recommendations."""
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
d = json.loads((ROOT / "data/low_hurdles_alternates.json").read_text())
WEEK = 9
rows = [r for r in d["rows"] if r["category"] == "Passing TDs"]

details = []
for r in rows:
    g = next((x for x in r["games"] if not x.get("dnp") and x.get("week") == WEEK and x.get("value") is not None), None)
    if not g:
        continue
    td = float(g["value"])
    rec = int(r.get("recommend") or 1)
    details.append({
        "player": r["name"], "team": r["team"], "pass_td": td,
        "recommend": rec, "mu": r.get("mu"),
        "hit1": td >= 1, "hit2": td >= 2, "hit3": td >= 3,
        "hit_rec": td >= rec,
    })

n1 = sum(1 for x in details if x["hit1"])
h2 = sum(1 for x in details if x["hit1"] and x["hit2"])
h3 = sum(1 for x in details if x["hit1"] and x["hit3"])
by_rec = defaultdict(lambda: {"n": 0, "hit": 0})
for x in details:
    by_rec[x["recommend"]]["n"] += 1
    by_rec[x["recommend"]]["hit"] += int(x["hit_rec"])

out = {
    "week": WEEK,
    "label": "2026 Week 9 finals (Nov 8 Sunday slate)",
    "qb_with_week9_log": len(details),
    "among_1plus_hitters": {
        "n": n1, "also_2plus": h2, "also_3plus": h3,
        "pct_2plus": round(100 * h2 / n1, 1) if n1 else None,
        "pct_3plus": round(100 * h3 / n1, 1) if n1 else None,
    },
    "recommended_rung_record": {
        f"{k}+": {"n": v["n"], "hit": v["hit"], "pct": round(100 * v["hit"] / v["n"], 1) if v["n"] else None}
        for k, v in sorted(by_rec.items())
    },
    "recommend_distribution": dict(Counter(x["recommend"] for x in details)),
    "sample": sorted(details, key=lambda x: (-x["pass_td"], x["player"]))[:15],
    "price_note": "Most alt-line prices missing in sidecar (prop_prices snapshot sparse/stale); recommendation used model+empirical thresholds only when unpriced.",
}
Path("/workspace/passtd-ladder-1109").mkdir(parents=True, exist_ok=True)
Path("/workspace/passtd-ladder-1109/BACKTEST.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
