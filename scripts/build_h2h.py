#!/usr/bin/env python3
"""Build data/h2h.json: current-roster players' game logs vs tonight's opponent.
Usage: build_h2h.py AWAY HOME [--label "..."] [--kick "..."]  (raw files cached in $H2H_CACHE)"""
import os, sys, json, argparse, urllib.request, datetime
import pandas as pd
B = "https://github.com/nflverse/nflverse-data/releases/download"
ap = argparse.ArgumentParser(); ap.add_argument("away"); ap.add_argument("home")
ap.add_argument("--season", type=int, default=2026); ap.add_argument("--first", type=int, default=2012)
ap.add_argument("--kick", default=""); ap.add_argument("--out", default="data/h2h.json")
a = ap.parse_args()
C = os.environ.get("H2H_CACHE", "/workspace/h2hdata"); os.makedirs(C, exist_ok=True)
def get(url, fn):
    p = os.path.join(C, fn)
    if not os.path.exists(p) or fn.startswith(("w%d" % a.season, "r%d" % a.season)):
        urllib.request.urlretrieve(url, p)
    return p
W = pd.concat([pd.read_parquet(get(f"{B}/stats_player/stats_player_week_{y}.parquet", f"w{y}.parquet")) for y in range(a.first, a.season + 1)])
R = pd.read_parquet(get(f"{B}/weekly_rosters/roster_weekly_{a.season}.parquet", f"r{a.season}.parquet"))
R = R[R.week == R.week.max()]
S = pd.read_csv(get("https://github.com/nflverse/nfldata/raw/master/data/games.csv", "sched.csv"), usecols=["game_id", "gameday"])
W = W.merge(S, on="game_id", how="left")
ALIAS = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}
W["opp"] = W.opponent_team.replace(ALIAS)
SK = {"QB", "RB", "FB", "WR", "TE"}
DEFP = {"DE", "DT", "NT", "LB", "OLB", "ILB", "MLB", "CB", "S", "SS", "FS", "DB", "EDGE"}
STAGE = {"REG": "", "WC": "Wild Card", "DIV": "Divisional", "CON": "Conf. Championship", "SB": "Super Bowl", "POST": "Playoffs"}
cur = W[W.season == a.season]
def i(x): return int(x) if pd.notna(x) else 0
out = {"updated": datetime.datetime.now().strftime("%Y-%m-%d %-I:%M %p ET"), "game": f"{a.away} @ {a.home}", "kick": a.kick, "since": a.first, "teams": {}}
for team, opp in ((a.away, a.home), (a.home, a.away)):
    ros = R[R.team == team]; rows = []
    for _, p in ros.iterrows():
        pos = p.position; gid = p.gsis_id
        if pos not in SK and pos not in DEFP: continue
        g = W[(W.player_id == gid) & (W.opp == opp)].sort_values(["season", "week"])
        if g.empty: continue
        isdef = pos in DEFP
        games = []
        for _, r in g.iterrows():
            d = {"date": r.gameday, "season": i(r.season), "week": i(r.week), "stage": STAGE.get(r.season_type, ""), "team": r.team}
            if isdef:
                d.update(tk=i(r.def_tackles_solo) + i(r.def_tackle_assists), sk=float(r.def_sacks or 0), int=i(r.def_interceptions), pd=i(r.def_pass_defended))
                if d["tk"] + d["sk"] + d["int"] + d["pd"] == 0: continue
            else:
                d.update(cmp=i(r.completions), att=i(r.attempts), py=i(r.passing_yards), ptd=i(r.passing_tds), pint=i(r.passing_interceptions),
                         car=i(r.carries), ry=i(r.rushing_yards), rtd=i(r.rushing_tds), tgt=i(r.targets), rec=i(r.receptions), recy=i(r.receiving_yards), rectd=i(r.receiving_tds))
            games.append(d)
        if not games: continue
        c = cur[cur.player_id == gid]; n = max(len(c), 1)
        if isdef:
            use = (c.def_tackles_solo.fillna(0).sum() + c.def_tackle_assists.fillna(0).sum() + 4 * c.def_sacks.fillna(0).sum())
            sk = sum(x["sk"] for x in games); itc = sum(x["int"] for x in games)
            if sk == 0 and itc == 0: continue  # defenders only when they have sacks/INTs vs this opponent
            summ = {"g": len(games), "tk": sum(x["tk"] for x in games), "sk": sk, "int": itc}
        else:
            use = (c.attempts.fillna(0).sum() * 1.0 + c.carries.fillna(0).sum() * 1.5 + c.targets.fillna(0).sum() * 2.0)  # season volume
            ng = len(games); py = sum(x["py"] for x in games); ry = sum(x["ry"] for x in games); recy = sum(x["recy"] for x in games)
            summ = {"g": ng, "py_g": round(py / ng, 1), "ry_g": round(ry / ng, 1), "recy_g": round(recy / ng, 1), "rec_g": round(sum(x["rec"] for x in games) / ng, 1),
                    "td": sum(x["ptd"] for x in games), "skill_td": sum(x["rtd"] + x["rectd"] for x in games), "int": sum(x["pint"] for x in games),
                    "scr80": sum(1 for x in games if x["ry"] + x["recy"] >= 80), "scr100": sum(1 for x in games if x["ry"] + x["recy"] >= 100),
                    "p250": sum(1 for x in games if x["py"] >= 250), "p300": sum(1 for x in games if x["py"] >= 300)}
        rows.append({"name": p.full_name, "pos": pos, "pid": str(int(p.espn_id)) if pd.notna(p.espn_id) else None, "def": isdef,
                     "use": round(float(use), 2), "games26": int(len(c)), "summary": summ, "games": games[::-1]})
    rows.sort(key=lambda r: (r["def"], -r["use"]))
    out["teams"][team] = {"opp": opp, "players": rows}
HUB = {"WAS": "WSH"}  # hub display codes
h = lambda t: HUB.get(t, t)
out["game"] = f"{h(a.away)} @ {h(a.home)}"
out["teams"] = {h(t): {"opp": h(v["opp"]), "players": [dict(pl, games=[dict(g, team=h(g["team"])) for g in pl["games"]]) for pl in v["players"]]} for t, v in out["teams"].items()}
open(a.out, "w").write(json.dumps(out, separators=(",", ":")))
for t, v in out["teams"].items():
    print(t, "vs", v["opp"], len(v["players"]), "players (", sum(not p["def"] for p in v["players"]), "offense )")
