"""Build data/dvp_viz.json for the Defense vs Position pop-up: weekly yards allowed
per defense/position (from player game logs) and each team's next-game skill players."""
import json, glob, os, collections as C
R = os.path.join(os.path.dirname(__file__), "..", "data")
season = json.load(open(os.path.join(R, "nfl.json"))).get("season")
BAD = ("out", "injured", "reserve", "suspend", "doubtful", "pup")
def yds(l, g):
    f = lambda k: l.get(k) or 0
    return f("passing_yards") if g == "QB" else f("rushing_yards") + f("receiving_yards") if g == "RB" else f("receiving_yards")
wk = C.defaultdict(lambda: C.defaultdict(float)); pl = []; nxt = {}
for fn in glob.glob(os.path.join(R, "players", "*.json")):
    try: q = json.load(open(fn))
    except Exception: continue
    g = q.get("grp")
    if g not in ("QB", "RB", "WR", "TE"): continue
    ls = [l for l in q.get("log") or [] if l.get("s") == season and l.get("o")]
    for l in ls: wk[(l["o"], g)][l["w"]] += yds(l, g)
    n = q.get("next") or {}
    if n.get("opp"): nxt[q["team"]] = {"opp": n["opp"], "home": n.get("home"), "date": n.get("date")}
    rank = (q.get("depth") or {}).get("rank") or 99
    inj = ((q.get("inj") or {}).get("status") or "").strip()
    if rank > {"QB": 1, "RB": 2, "WR": 3, "TE": 1}[g] or not ls or not n.get("opp"): continue
    if any(b in inj.lower() for b in BAD): continue
    ypg = round(sum(yds(l, g) for l in ls) / len(ls), 1)
    if ypg < 10: continue
    pl.append({"id": q["id"], "n": q["name"], "t": q["team"], "g": g, "opp": n["opp"], "ypg": ypg,
               "inj": None if inj.lower() in ("", "active") else inj})
tr = {}
for (o, g), m in wk.items(): tr.setdefault(o, {})[g] = sorted([w, round(v)] for w, v in m.items())
upd = json.load(open(os.path.join(R, "nfl.json"))).get("updated")
json.dump({"updated": upd, "season": season, "trend": tr, "players": pl, "next": nxt}, open(os.path.join(R, "dvp_viz.json"), "w"), separators=(",", ":"))
print("dvp_viz:", len(pl), "players,", len(nxt), "teams with games")
