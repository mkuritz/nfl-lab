#!/usr/bin/env python3
"""Build data/h2h.json: for every game on this week's slate (from data/v2.json), each current-roster
player's game log vs that opponent, injury flags, vacated head-to-head production and an
injury-adjusted projection compared with the current prop line. Display only; no Highlighted logic.
Usage: build_h2h.py [--overrides path/to/confirmed_injuries.json]  (raw files cached in $H2H_CACHE)"""
import os, json, argparse, urllib.request, datetime, re
import pandas as pd
B = "https://github.com/nflverse/nflverse-data/releases/download"
ap = argparse.ArgumentParser(); ap.add_argument("--season", type=int, default=2026); ap.add_argument("--first", type=int, default=2012)
ap.add_argument("--overrides", default=""); ap.add_argument("--only", default=""); ap.add_argument("--out", default="data/h2h.json")
a = ap.parse_args()
C = os.environ.get("H2H_CACHE", "/tmp/h2hcache"); os.makedirs(C, exist_ok=True)
def get(url, fn, fresh=False):
    p = os.path.join(C, fn)
    if fresh or not os.path.exists(p): urllib.request.urlretrieve(url, p)
    return p
W = pd.concat([pd.read_parquet(get(f"{B}/stats_player/stats_player_week_{y}.parquet", f"w{y}.parquet", y == a.season)) for y in range(a.first, a.season + 1)])
R = pd.read_parquet(get(f"{B}/weekly_rosters/roster_weekly_{a.season}.parquet", f"r{a.season}.parquet", True))
R = R[R.week == R.week.max()]
S = pd.read_csv(get("https://github.com/nflverse/nfldata/raw/master/data/games.csv", "sched.csv", True), usecols=["game_id", "gameday"])
W = W.merge(S, on="game_id", how="left")
NV = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA", "WSH": "WAS"}   # any code -> stats code
HUB = {"WAS": "WSH", "LA": "LAR"}                                          # stats code -> hub code
nv = lambda t: NV.get(t, t); hub = lambda t: HUB.get(t, t)
W["opp"] = W.opponent_team.map(nv); W["team"] = W.team.map(nv)
V2 = json.load(open("data/v2.json")); EIA = json.load(open("data/early_injury_adjust.json")) if os.path.exists("data/early_injury_adjust.json") else {}
N = lambda s: re.sub(r"[^a-z]", "", re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", (s or "").lower()))
# ---- injury status: hub feed, then early-injury file, then confirmed overrides (win) ----
ST = {}
for t, L in V2.get("inj", {}).items():
    for x in L: ST[(nv(t), N(x["n"]))] = {"st": x["st"], "d": x.get("d", ""), "src": "report"}
for p in EIA.get("prop_freerolls", []):
    s = p.get("status", "")
    if p.get("unconfirmed"): continue
    k = (nv(p["team"]), N(p["player"]))
    if k not in ST or ST[k]["st"] == "Active": ST[k] = {"st": s.split(" ·")[0], "d": p.get("injury", ""), "src": "report"}
if a.overrides and os.path.exists(a.overrides):
    today = datetime.date.today().isoformat()
    for p in json.load(open(a.overrides)).get("players", []):
        if not p.get("confirmed") or (p.get("expires") and p["expires"] < today): continue
        ST[(nv(p["team"]), N(p["player"]))] = {"st": p["st"], "d": (p.get("why") or "").split(";")[0], "src": "confirmed"}
OUT = {"Out", "Injured Reserve", "IR", "Suspended", "PUP", "Physically Unable to Perform", "Non-Football Injury"}
isout = lambda s: s in OUT or s.startswith("Injured Reserve")
SK = {"QB", "RB", "FB", "WR", "TE"}; DEFP = {"DE", "DT", "NT", "LB", "OLB", "ILB", "MLB", "CB", "S", "SS", "FS", "DB", "EDGE"}
STAGE = {"REG": "", "WC": "Wild Card", "DIV": "Divisional", "CON": "Conf. Championship", "SB": "Super Bowl", "POST": "Playoffs"}
cur = W[(W.season == a.season)]
i = lambda x: int(x) if pd.notna(x) else 0
MK = {"Receiving Yards": "recy", "Receptions": "rec", "Rushing Yards": "ry", "Passing Yards": "py", "Rushing Plus Receiving Yards": "rry", "Carries": "car", "Pass Completions": "cmp", "Passing Attempts": "att"}
LINES = {}
for r in V2["rows"]:
    if r["market"] in MK: LINES.setdefault((nv(r["team"]), N(r["name"])), {})[r["market"]] = {"line": r["line"], "avg": r.get("avg")}
def season(gid):
    c = cur[cur.player_id == gid]; n = len(c)
    if not n: return None
    f = lambda col: float(c[col].fillna(0).sum())
    return {"last": int(c.week.max()), "g": n, "tg": f("targets") / n, "ca": f("carries") / n, "recy": f("receiving_yards"), "ry": f("rushing_yards"), "tgt": f("targets"), "car": f("carries"),
            "rec": f("receptions"), "att": f("attempts"), "py": f("passing_yards"), "def": f("def_tackles_solo") + f("def_tackle_assists") + 4 * f("def_sacks")}
def team_block(team, opp):
    ros = R[R.team == team]; rows = []
    for _, p in ros.iterrows():
        pos = p.position; gid = p.gsis_id
        if pos not in SK and pos not in DEFP: continue
        stt = ST.get((team, N(p.full_name)))
        if stt is None and p.status in ("RES", "INA", "PUP", "SUS", "NFI"): stt = {"st": {"RES": "Injured Reserve", "INA": "Inactive", "PUP": "PUP", "SUS": "Suspended", "NFI": "Non-Football Injury"}[p.status], "d": "", "src": "roster"}
        g = W[(W.player_id == gid) & (W.opp == opp)].sort_values(["season", "week"])
        se = season(gid); isdef = pos in DEFP
        games = []
        for _, r in g.iterrows():
            d = {"date": r.gameday, "season": i(r.season), "week": i(r.week), "stage": STAGE.get(r.season_type, ""), "team": hub(r.team)}
            if isdef:
                d.update(tk=i(r.def_tackles_solo) + i(r.def_tackle_assists), sk=float(r.def_sacks or 0), int=i(r.def_interceptions), pd=i(r.def_pass_defended))
                if d["tk"] + d["sk"] + d["int"] + d["pd"] == 0: continue
            else:
                d.update(cmp=i(r.completions), att=i(r.attempts), py=i(r.passing_yards), ptd=i(r.passing_tds), pint=i(r.passing_interceptions), car=i(r.carries), ry=i(r.rushing_yards),
                         rtd=i(r.rushing_tds), tgt=i(r.targets), rec=i(r.receptions), recy=i(r.receiving_yards), rectd=i(r.receiving_tds))
            games.append(d)
        row = {"name": p.full_name, "pos": pos, "pid": str(int(p.espn_id)) if pd.notna(p.espn_id) else None, "def": isdef, "status": stt, "out": bool(stt and isout(stt["st"])),
               "season": se, "games": games[::-1]}
        if isdef:
            row["use"] = se["def"] if se else 0
            if games:
                row["summary"] = {"g": len(games), "tk": sum(x["tk"] for x in games), "sk": sum(x["sk"] for x in games), "int": sum(x["int"] for x in games)}
        else:
            row["use"] = (se["att"] + 1.5 * se["car"] + 2 * se["tgt"]) if se else 0
            if games:
                ng = len(games); s = lambda k: sum(x[k] for x in games)
                row["summary"] = {"g": ng, "py_g": round(s("py") / ng, 1), "ry_g": round(s("ry") / ng, 1), "recy_g": round(s("recy") / ng, 1), "rec_g": round(s("rec") / ng, 1),
                    "tgt_g": round(s("tgt") / ng, 1), "car_g": round(s("car") / ng, 1), "cmp_g": round(s("cmp") / ng, 1), "att_g": round(s("att") / ng, 1),
                    "td": s("ptd"), "skill_td": s("rtd") + s("rectd"), "int": s("pint"), "scr80": sum(1 for x in games if x["ry"] + x["recy"] >= 80),
                    "scr100": sum(1 for x in games if x["ry"] + x["recy"] >= 100), "p250": sum(1 for x in games if x["py"] >= 250), "p300": sum(1 for x in games if x["py"] >= 300)}
        rows.append(row)
    # ---- vacated production (players out tonight) ----
    off = [r for r in rows if not r["def"]]; outs = [r for r in off if r["out"] and (r["season"] or r.get("summary"))]
    act = [r for r in off if not r["out"] and r["season"]]
    tw = int(cur[cur.team == team].week.max()) if len(cur[cur.team == team]) else 0
    # only fresh absences move volume: a player who already missed the last 2 games is baked into everyone's recent numbers and lines
    fresh = [o for o in outs if o["season"] and o["season"]["last"] >= tw - 1 and (o["season"]["tg"] >= 1 or o["season"]["ca"] >= 1)]
    for o in outs: o["fresh"] = o in fresh
    vac_tg = sum(r["season"]["tg"] for r in fresh); vac_ca = sum(r["season"]["ca"] for r in fresh if r["pos"] in ("RB", "FB"))
    eia = {N(p["player"]): p for p in EIA.get("prop_freerolls", []) if nv(p["team"]) == team}
    bump = {}
    for o in fresh:
        e = eia.get(N(o["name"]))
        if e and e.get("beneficiaries"):
            for b in e["beneficiaries"]:
                k = N(b["player"]); x = bump.setdefault(k, {"tg": 0, "ca": 0, "from": []}); x["tg"] += b.get("d_tg") or 0; x["ca"] += b.get("d_ca") or 0; x["from"].append(o["name"])
        elif o["season"]:
            tot_t = sum(r["season"]["tgt"] for r in act) or 1; tot_c = sum(r["season"]["car"] for r in act if r["pos"] in ("RB", "FB")) or 1
            for r in act:
                x = bump.setdefault(N(r["name"]), {"tg": 0, "ca": 0, "from": []})
                x["tg"] += o["season"]["tg"] * r["season"]["tgt"] / tot_t
                if r["pos"] in ("RB", "FB") and o["pos"] in ("RB", "FB"): x["ca"] += o["season"]["ca"] * r["season"]["car"] / tot_c
                if x["tg"] or x["ca"]: x["from"].append(o["name"])
    missing = {"players": [{"name": o["name"], "pos": o["pos"], "status": o["status"]["st"], "pid": o["pid"], "h2h": o.get("summary"),
                            "fresh": o["fresh"], "tg_g26": round(o["season"]["tg"], 1) if o["season"] else None, "ca_g26": round(o["season"]["ca"], 1) if o["season"] else None} for o in outs],
               "tg_g": round(vac_tg, 1), "ca_g": round(vac_ca, 1)}
    hs = [o.get("summary") for o in outs if o.get("summary")]
    if hs:
        missing["h2h_recy_g"] = round(sum(h["recy_g"] for h in hs), 1); missing["h2h_ry_g"] = round(sum(h["ry_g"] for h in hs), 1)
        missing["h2h_tgt_g"] = round(sum(h["tgt_g"] for h in hs), 1); missing["h2h_td"] = sum(h["skill_td"] for h in hs); missing["h2h_g"] = sum(h["g"] for h in hs)
    benef = []
    for r in act:
        b = bump.get(N(r["name"]))
        if b and (b["tg"] >= 0.3 or b["ca"] >= 0.5):
            se = r["season"]; ypt = se["recy"] / se["tgt"] if se["tgt"] else 0; ypc = se["ry"] / se["car"] if se["car"] else 0; cr = se["rec"] / se["tgt"] if se["tgt"] else 0
            r["adj"] = {"tg": round(b["tg"], 1), "ca": round(b["ca"], 1), "recy": round(b["tg"] * ypt, 1), "ry": round(b["ca"] * ypc, 1), "rec": round(b["tg"] * cr, 1), "from": sorted(set(b["from"]))}
            benef.append({"name": r["name"], "pos": r["pos"], "tg": round(b["tg"], 1), "ca": round(b["ca"], 1), "yds": round(b["tg"] * ypt + b["ca"] * ypc, 1)})
    missing["beneficiaries"] = sorted(benef, key=lambda x: -x["yds"])[:6]
    return rows, missing
def defense_factor(def_rows):
    """Opponent defenders out tonight who play a real role (≥3 games, ≥3 tackles/g equivalent). +3% per DB (pass), +3% per DL/LB (rush), capped at 10%."""
    o = [r for r in def_rows if r["out"] and r["season"] and r["season"]["g"] >= 3 and r["season"]["def"] / r["season"]["g"] >= 3]
    db = [r for r in o if r["pos"] in ("CB", "S", "SS", "FS", "DB")]; fr = [r for r in o if r not in db]
    return {"pass": min(0.03 * len(db), 0.10), "rush": min(0.03 * len(fr), 0.10), "out": [{"name": r["name"], "pos": r["pos"], "status": r["status"]["st"]} for r in o]}
def finish(team, opp, rows, dfac):
    res = []
    for r in rows:
        L = LINES.get((team, N(r["name"])), {}); r["props"] = []
        if not r["def"] and not r["out"]:
            sm = r.get("summary") or {}; ad = r.get("adj") or {}
            for mk, key in MK.items():
                if mk not in L: continue
                base = L[mk]["avg"]
                if base is None: continue
                h = {"recy": sm.get("recy_g"), "rec": sm.get("rec_g"), "ry": sm.get("ry_g"), "py": sm.get("py_g"), "car": sm.get("car_g"), "cmp": sm.get("cmp_g"), "att": sm.get("att_g"),
                     "rry": (sm.get("ry_g", 0) + sm.get("recy_g", 0)) if sm else None}[key]
                add = {"recy": ad.get("recy", 0), "rec": ad.get("rec", 0), "ry": ad.get("ry", 0), "rry": ad.get("recy", 0) + ad.get("ry", 0), "car": ad.get("ca", 0)}.get(key, 0)
                f = dfac["pass"] if key in ("recy", "rec", "py", "cmp") else dfac["rush"] if key in ("ry", "car") else (dfac["pass"] + dfac["rush"]) / 2
                proj = round((base + add) * (1 + f), 1)
                res_ = {"market": mk, "line": L[mk]["line"], "base": round(base, 1), "inj_add": round(add, 1), "def_pct": round(f * 100), "proj": proj, "h2h": h, "h2h_g": sm.get("g", 0)}
                res_["adv"] = bool(proj > L[mk]["line"] and h is not None and sm.get("g", 0) >= 2 and h > L[mk]["line"])
                r["props"].append(res_)
        if r.get("summary") or r["props"] or (r["out"] and r["season"]):
            if r["def"] and r.get("summary") and r["summary"]["sk"] == 0 and r["summary"]["int"] == 0: continue
            if r["def"] and not r.get("summary"): continue
            r.pop("season", None); res.append(r)
    res.sort(key=lambda r: (r["def"], r["out"], -r["use"]))
    return res
games = {}
for r in V2["rows"]:
    games.setdefault(r["game"], {"time": r["time"], "teams": set()})["teams"].add((r["team"], r["home"]))
out = {"updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).strftime("%a %b %-d, %-I:%M %p ET"), "since": a.first, "week": V2.get("week"), "games": []}
for gid, g in sorted(games.items(), key=lambda kv: (kv[1]["time"], kv[0])):
    tm = sorted(g["teams"], key=lambda x: x[1]); 
    if len(tm) != 2: continue
    away, home = nv(tm[0][0]), nv(tm[1][0])
    if a.only and a.only not in (hub(away), hub(home)): continue
    A, Am = team_block(away, home); H, Hm = team_block(home, away)
    Ad = defense_factor([r for r in H if r["def"]]); Hd = defense_factor([r for r in A if r["def"]])
    kick = datetime.datetime.strptime(g["time"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-5)))
    out["games"].append({"key": gid, "game": f"{hub(away)} @ {hub(home)}", "kick": kick.strftime("%a %-I:%M %p ET"), "time": g["time"], "teams": {
        hub(away): {"opp": hub(home), "missing": Am, "opp_def_out": Ad, "players": finish(away, home, A, Ad)},
        hub(home): {"opp": hub(away), "missing": Hm, "opp_def_out": Hd, "players": finish(home, away, H, Hd)}}})
json.dump(out, open(a.out, "w"), separators=(",", ":"), default=float)
for gm in out["games"]:
    print(gm["game"], {t: (len(v["players"]), len(v["missing"]["players"])) for t, v in gm["teams"].items()})
