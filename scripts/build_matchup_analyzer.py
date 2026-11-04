"""Matchup Analyzer data (display only). Reads existing NFL Hub data only: data/players/*.json game logs,
data/v2.json (injuries, kickoff weather, posted lines), data/nfl.json (schedule). Writes data/matchup_an.json.
Nothing is estimated: a stat with no logged games is omitted, and the page hides that tile."""
import json, glob, os, collections, datetime as dt, urllib.request
from concurrent.futures import ThreadPoolExecutor
D = os.path.join(os.path.dirname(__file__), "..", "data")
def L(f): return json.load(open(os.path.join(D, f)))
nfl, v2 = L("nfl.json"), L("v2.json")
SEASON = nfl.get("season") or 2026
G = lambda g, k: g.get(k) or 0
# stat: (label, kind, numerator, denominator) kind: pg = per game sum, rt = ratio of sums (x100 if pct)
STATS = {
 "QB": [("pass_yds","Pass yds","pg","passing_yards",None),("att","Attempts","pg","attempts",None),("cmp_pct","Comp %","pct","completions","attempts"),
        ("ypa","Yds / att","rt","passing_yards","attempts"),("pass_td","Pass TD","pg","passing_tds",None),("air","Air yds","pg","passing_air_yards",None),
        ("sacked","Sacks taken","pg","sacks_suffered",None),("rush_yds","Rush yds","pg","rushing_yards",None)],
 "RB": [("rush_yds","Rush yds","pg","rushing_yards",None),("car","Carries","pg","carries",None),("ypc","Yds / carry","rt","rushing_yards","carries"),
        ("rush_td","Rush TD","pg","rushing_tds",None),("tgt","Targets","pg","targets",None),("rec","Receptions","pg","receptions",None),("rec_yds","Rec yds","pg","receiving_yards",None)],
 "WR": [("rec_yds","Rec yds","pg","receiving_yards",None),("tgt","Targets","pg","targets",None),("rec","Receptions","pg","receptions",None),
        ("catch","Catch %","pct","receptions","targets"),("ypr","Yds / catch","rt","receiving_yards","receptions"),("air","Air yds","pg","receiving_air_yards",None),
        ("yac","Yds after catch","pg","receiving_yards_after_catch",None),("rec_td","Rec TD","pg","receiving_tds",None)],
}
STATS["TE"] = STATS["WR"]
KEY = {"QB": ("pass_yds", "Passing Yards"), "RB": ("rush_yds", "Rushing Yards"), "WR": ("rec_yds", "Receiving Yards"), "TE": ("rec_yds", "Receiving Yards")}
USE = {"QB": lambda g: G(g,"attempts") >= 10, "RB": lambda g: G(g,"carries")+G(g,"targets") >= 5, "WR": lambda g: G(g,"targets") >= 2, "TE": lambda g: G(g,"targets") >= 2}
def agg(games, grp):
    """games: list of dicts of summed raw fields; returns {stat: value} (None when no denominator)."""
    out = {}
    n = len(games)
    if not n: return out
    for k, lab, kind, a, b in STATS[grp]:
        A = sum(G(g, a) for g in games)
        if kind == "pg": out[k] = round(A / n, 2)
        else:
            B = sum(G(g, b) for g in games)
            if B: out[k] = round(A / B * (100 if kind == "pct" else 1), 2)
    return out
P = {}
for f in glob.glob(os.path.join(D, "players", "*.json")):
    p = json.load(open(f))
    if p.get("grp") in ("QB","RB","WR","TE","DEF"): P[p["id"]] = p
# ---- what each defense allows, per game, to each position group (2026 regular season, from every logged player) ----
FIELDS = {x[3] for v in STATS.values() for x in v} | {x[4] for v in STATS.values() for x in v if x[4]}
allow = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: collections.Counter())))  # def -> grp -> (w,g) -> sums
for p in P.values():
    grp = p["grp"]
    if grp == "DEF": continue
    for g in p["log"]:
        if g["s"] != SEASON: continue
        c = allow[g["o"]][grp][(g["w"], g["g"])]
        for k in FIELDS: c[k] += G(g, k)
# ---- athlete game logs: count every game he appeared in, including zero-stat appearances ----
UA = {"User-Agent": "Mozilla/5.0"}
def jget(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20))
    except Exception: return None
def gamelog(pid):
    d = jget("https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/%s/gamelog?season=%s" % (pid, SEASON))
    if not d: return None
    ev = d.get("events") or {}
    out = {}
    for st in d.get("seasonTypes") or []:
        if "Regular" not in (st.get("displayName") or ""): continue
        for c in st.get("categories") or []:
            for e in c.get("events") or []:
                x = ev.get(e.get("eventId")) or {}
                if x.get("week"): out[int(x["week"])] = {"date": (x.get("gameDate") or "")[:10], "opp": ((x.get("opponent") or {}).get("abbreviation"))}
    return out
OFF = [pid for pid, p in P.items() if p["grp"] in STATS]
with ThreadPoolExecutor(16) as ex: GL = dict(zip(OFF, ex.map(gamelog, OFF)))
GL = {k: v for k, v in GL.items() if v is not None}
ABBR = {"WSH": "WAS", "LAR": "LA"}
stubs = 0
for pid, gl in GL.items():
    p = P[pid]
    have = {g["w"] for g in p["log"] if g["s"] == SEASON}
    for w, x in gl.items():
        if w in have: continue
        p["log"].append({"s": SEASON, "w": w, "o": ABBR.get(x["opp"], x["opp"]), "t": p["team"], "g": "%s_%02d_zero" % (SEASON, w), "zero": 1, "date": x["date"]})
        stubs += 1
    for g in p["log"]:
        if g["s"] == SEASON and g["w"] in gl: g["date"] = gl[g["w"]]["date"]
    p["log"].sort(key=lambda g: (g["s"], g["w"]), reverse=True)
print("gamelogs", len(GL), "zero-stat games added", stubs)
def team_allow(t, grp, last=None):
    wk = sorted(allow[t][grp], reverse=True)
    if last: wk = wk[:last]
    return agg([allow[t][grp][k] for k in wk], grp), len(wk)
WIN = {"L3": 3, "L6": 6, "All": None}
TA = {}  # grp -> win -> team -> stats
for grp in STATS:
    TA[grp] = {}
    for w, n in WIN.items():
        TA[grp][w] = {t: team_allow(t, grp, n)[0] for t in allow}
def rank_allowed(grp, w, stat, t):
    """1 = allows the least (toughest), n = allows the most. Sacks taken: 1 = fewest sacks forced."""
    vals = sorted((v[stat], tt) for tt, v in TA[grp][w].items() if stat in v)
    if not any(tt == t for _, tt in vals): return None, len(vals)
    lo = [tt for _, tt in vals]
    return lo.index(t) + 1, len(vals)
def pctile(x, arr):
    if x is None or not arr: return None
    return round(100 * sum(1 for a in arr if a < x) / len(arr) + 50 * sum(1 for a in arr if a == x) / len(arr))
# ---- player pools by window (qualified usage, 2026 + last season for L10 tails) ----
def pwin(p, w):
    cur = [g for g in p["log"] if g["s"] == SEASON]  # current season only; prior-season games never mix into a window
    return cur if w == "All" else cur[: {"L3":3,"L6":6,"L10":10}[w]]
PW = ("L3","L6","L10","All")
pool = {grp: {w: collections.defaultdict(list) for w in PW} for grp in STATS}
pstat = {}
for pid, p in P.items():
    grp = p["grp"]
    if grp not in STATS: continue
    pstat[pid] = {}
    for w in PW:
        lg = pwin(p, w)
        st = agg(lg, grp) if lg else {}
        pstat[pid][w] = (st, len(lg))
        cur = [g for g in p["log"] if g["s"] == SEASON]
        if len(lg) >= min(3, len(lg) or 1) and cur and sum(1 for g in cur if USE[grp](g)) >= max(2, len(cur) // 2):
            for k, v in st.items(): pool[grp][w][k].append(v)
# ---- slate context ----
games = {}
for g in nfl.get("games", []):
    if g.get("state") != "pre": continue
    for side, oth in (("home","away"),("away","home")):
        games[g[side]["abbr"]] = {"opp": g[oth]["abbr"], "home": side == "home", "date": g["date"], "venue": g.get("venue"), "id": g["id"]}
wx = {}
lines = collections.defaultdict(dict)
for r in v2.get("rows", []):
    if r.get("wx") and r["team"] not in wx: wx[r["team"]] = r["wx"]
    if r.get("line") is not None and r["market"] != "Anytime TD": lines[r["aid"]][r["market"]] = {"line": r["line"], "book": r.get("bbook")}
inj = v2.get("inj", {})
def injsum(t):
    c = collections.Counter()
    out = []
    for x in inj.get(t, []):
        s = x.get("st") or ""
        if s and s != "Active":
            k = "IR" if "Reserve" in s else s
            c[k] += 1
            out.append({"n": x.get("n"), "pos": x.get("pos"), "st": s, "d": x.get("d") or ""})
    return {"counts": dict(c), "list": out}
# ---- athlete-level status (catches players the league injury feed leaves out) ----
BAD = ("Out", "Injured Reserve", "Doubtful", "Suspended", "Physically Unable to Perform", "Non-Football Injury")
def athstat(pid):
    d = jget("https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/%s" % pid)
    if not d: return None
    a = d.get("athlete") or {}
    s = ((a.get("status") or {}).get("name") or "")
    ij = (a.get("injuries") or [{}])[0]
    st = ij.get("status") or ""
    if "Suspend" in s: st = "Suspended"
    if not st: return {"st": s or "Active"}
    return {"st": st, "d": ((ij.get("details") or {}).get("type") or ""), "dt": (ij.get("date") or "")[:10]}
SLATE = [pid for pid, p in P.items() if p.get("team") in games and (p["grp"] in STATS or p["grp"] == "DEF")]
with ThreadPoolExecutor(16) as ex: AS = {k: v for k, v in zip(SLATE, ex.map(athstat, SLATE)) if v}
def badge(st):
    st = st or ""
    if "Reserve" in st or st.startswith("Physically") or st.startswith("Non-Football"): return "IR"
    for k in ("Out", "Doubtful", "Suspended", "Questionable"):
        if st.startswith(k): return k
    return None
for pid, a in AS.items():
    p = P[pid]
    if badge(a["st"]) and not (p.get("inj") or {}).get("status"):
        p["inj"] = {"status": a["st"], "detail": a.get("d", ""), "date": a.get("dt", "")}
        if not any(x.get("id") == pid for x in inj.setdefault(p["team"], [])):
            inj[p["team"]].append({"n": p["name"], "pos": p["pos"], "st": a["st"], "d": a.get("d", ""), "id": pid})
print("athlete status checked", len(AS), "flagged", sum(1 for pid, a in AS.items() if badge(a["st"])))
starters = {}
for p in P.values():
    d = p.get("depth") or {}
    if p["grp"] == "QB" and d.get("rank") == 1: starters[p["team"]] = p
def qbflag(t):
    p = starters.get(t)
    if not p: return None
    s = (p.get("inj") or {}).get("status") or ""
    return {"name": p["name"], "st": s} if s in ("Out", "Doubtful") or "Reserve" in s else None
# opposing defensive unit for the position
UNIT = {"QB": ("DE","DT","NT","LB","OLB","ILB","CB","SAF","S","FS","SS"), "RB": ("DE","DT","NT","LB","OLB","ILB","MLB"), "WR": ("CB","SAF","S","FS","SS","NB"), "TE": ("LB","OLB","ILB","MLB","SAF","S","FS","SS")}
DSTATS = [("tkl","Tackles"),("tfl","TFL"),("sk","Sacks"),("qbh","QB hits"),("pd","Passes defended"),("int","INT"),("snap","Snap %")]
def dline(p):
    cur = [g for g in p["log"] if g["s"] == SEASON]
    if not cur: return None
    n = len(cur); sn = [g["snap"] for g in cur[:3] if g.get("snap") is not None]
    return {"gp": n, "tkl": round(sum(G(g,"def_tackles_solo")+G(g,"def_tackle_assists") for g in cur)/n,1), "tfl": round(sum(G(g,"def_tackles_for_loss") for g in cur),1),
            "sk": round(sum(G(g,"def_sacks") for g in cur),1), "qbh": round(sum(G(g,"def_qb_hits") for g in cur),1), "pd": round(sum(G(g,"def_pass_defended") for g in cur),1),
            "int": round(sum(G(g,"def_interceptions") for g in cur),1), "snap": round(sum(sn)/len(sn)) if sn else None}
dpool = collections.defaultdict(lambda: collections.defaultdict(list))
DL = {}
for pid, p in P.items():
    if p["grp"] != "DEF": continue
    x = dline(p)
    if not x or x["gp"] < 3: continue
    DL[pid] = x
    for k, _ in DSTATS:
        if x.get(k) is not None: dpool[p["pos"]][k].append(x[k] / (1 if k in ("tkl","snap") else x["gp"]))
def unit(t, grp):
    rows = []
    for pid, p in P.items():
        if p["grp"] != "DEF" or p["team"] != t or p["pos"] not in UNIT[grp] or pid not in DL: continue
        d = p.get("depth") or {}
        if d.get("rank") and d["rank"] > 2: continue
        x = dict(DL[pid]); x.update({"id": pid, "n": p["name"], "pos": p["pos"], "dr": d.get("rank"), "st": (p.get("inj") or {}).get("status") or "Active"})
        x["pct"] = {k: pctile(x[k] / (1 if k in ("tkl","snap") else x["gp"]), dpool[p["pos"]][k]) for k, _ in DSTATS if x.get(k) is not None}
        rows.append(x)
    rows.sort(key=lambda r: (-(r.get("snap") or 0)))
    return rows[:12]
out = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "season": SEASON, "week": nfl.get("week"),
       "stats": {g: [[k, lab] for k, lab, *_ in v] for g, v in STATS.items()}, "dstats": DSTATS, "players": {}}
for pid, p in P.items():
    grp = p["grp"]
    if grp not in STATS or not p.get("team") or p["team"] not in games: continue
    cur = [g for g in p["log"] if g["s"] == SEASON]
    if len(cur) < 2 or sum(1 for g in cur if USE[grp](g)) < 2: continue
    gm = games[p["team"]]; o = gm["opp"]
    if o not in allow: continue
    ast = (AS.get(pid) or {}).get("st") or (p.get("inj") or {}).get("status") or "Active"
    rec = {"st": ast, "bdg": badge(ast), "stx": (AS.get(pid) or {}).get("d") or (p.get("inj") or {}).get("detail") or "", "grp": grp, "team": p["team"], "opp": o, "home": gm["home"], "date": gm["date"], "venue": gm["venue"],
           "wx": wx.get(gm["opp"] if not gm["home"] else p["team"]) or wx.get(p["team"]), "inj": {p["team"]: injsum(p["team"]), o: injsum(o)},
           "qbout": {k: v for k, v in ((p["team"], qbflag(p["team"])), (o, qbflag(o))) if v}, "win": {}, "owin": {}}
    for w in PW:
        st, n = pstat[pid][w]
        rec["win"][w] = {"n": n, "v": st, "p": {k: pctile(v, pool[grp][w][k]) for k, v in st.items()}}
    for w in ("L3","L6","All"):
        st = TA[grp][w].get(o, {})
        allv = {k: [v[k] for v in TA[grp][w].values() if k in v] for k in st}
        rec["owin"][w] = {"n": team_allow(o, grp, WIN[w])[1], "v": st, "p": {k: pctile(v, allv[k]) for k, v in st.items()},
                          "r": {k: rank_allowed(grp, w, k, o)[0] for k in st}, "of": len(TA[grp][w])}
    # opponent by-week allowed (key stat) for the strip
    ks = KEY[grp][0]; spec = [x for x in STATS[grp] if x[0] == ks][0]
    rec["oweek"] = [[w, round(allow[o][grp][(w, g)][spec[3]])] for (w, g) in sorted(allow[o][grp])]
    rec["unit"] = unit(o, grp)
    # similar players vs this opponent: same group, 2026 key-stat average within 30% of his, games vs this opponent this season
    me = pstat[pid]["All"][0].get(ks)
    sim = []
    bm = lines.get(pid, {}).get(KEY[grp][1])
    if me:
        for qid, q in P.items():
            if qid == pid or q["grp"] != grp or qid not in pstat: continue
            qa = pstat[qid]["All"][0].get(ks)
            if not qa or abs(qa - me) / me > 0.30: continue
            for g in q["log"]:
                if g["s"] == SEASON and g["o"] == o and USE[grp](g):
                    sim.append({"w": g["w"], "d": g.get("date") or "", "id": qid, "n": q["name"], "t": g["t"], "res": round(G(g, spec[3]), 1), "avg": round(qa, 1)})
    sim.sort(key=lambda r: -r["w"])
    rec["sim"] = {"stat": KEY[grp][1], "me": round(me, 1) if me else None, "bench": bm, "rows": sim[:15]}
    out["players"][pid] = rec
json.dump(out, open(os.path.join(D, "matchup_an.json"), "w"), separators=(",", ":"))
print("players", len(out["players"]))
