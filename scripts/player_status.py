"""Per-player status check (runs after profiles.py). The league injury feed sometimes leaves players out
(e.g. a starter placed on IR after surgery). For every QB/RB/WR/TE on a roster, read the player's own status entry
first; if it is empty, keep the team injury-list status already on the profile. A status dated before the
player's most recent logged game is stale and ignored. Patches data/players/<id>.json "inj" in place. Display only."""
import json, glob, os, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor
D = os.path.join(os.path.dirname(__file__), "..", "data")
UA = {"User-Agent": "Mozilla/5.0"}
FIX = {"WSH": "WSH", "WAS": "WSH", "LA": "LAR"}
def js(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20))
    except Exception: return None
P = {}
for f in glob.glob(os.path.join(D, "players", "*.json")):
    p = json.load(open(f))
    if p.get("grp") in ("QB", "RB", "WR", "TE", "K", "DEF") and p.get("team") and p["team"] != "FA": P[p["id"]] = (f, p)   # every position (Nov 5: Malone, reserve/PUP)
SEASON = next((p["season"] for _, p in P.values() if p.get("season")), dt.date.today().year)
# (team, week) -> game date, for the stale check
WD = {}
def wk(w):
    d = js("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week=%d&dates=%d" % (w, SEASON)) or {}
    out = {}
    for e in d.get("events", []):
        for c in e["competitions"][0]["competitors"]:
            a = c["team"]["abbreviation"]; out[(FIX.get(a, a), w)] = e["date"][:10]
    return out
with ThreadPoolExecutor(8) as ex:
    for o in ex.map(wk, range(1, 19)): WD.update(o)
def last_game(p):
    ds = [WD.get((FIX.get(g["t"], g["t"]), g["w"]), "") for g in p.get("log", []) if g.get("s") == SEASON]
    return max(ds) if ds else ""
def own(pid):
    d = js("https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/%s" % pid)
    if not d: return None
    a = d.get("athlete") or {}
    ij = (a.get("injuries") or [{}])[0]
    st = ij.get("status") or ""
    if "Suspend" in ((a.get("status") or {}).get("name") or ""): st = "Suspended"
    if not st: return {}
    # reserve lists (PUP / NFI / IR / suspended) come as a fantasy-status code; they are season-long designations, not game statuses
    fs = (((ij.get("details") or {}).get("fantasyStatus") or {}).get("abbreviation") or "").upper()
    RES = {"PUP-R": "Reserve/PUP", "PUP": "Reserve/PUP", "NFI-R": "Reserve/NFI", "NFI": "Reserve/NFI", "IR": "Injured Reserve", "SUSP": "Suspended", "COV": "Reserve/COVID"}
    res = RES.get(fs) if fs != "IR" else None   # IR is already a status; PUP/NFI/suspension are reserve-list labels
    if not res:
        lc = (ij.get("longComment") or "") + " " + (ij.get("shortComment") or "")
        m = __import__("re").search(r"(?:reserve/|on the )(PUP|non-football injury|NFI)\b", lc, __import__("re").I)
        if m and st == "Out": res = "Reserve/PUP" if m.group(1).upper() == "PUP" else "Reserve/NFI"
    _ret = (ij.get("details") or {}).get("returnDate") or ""
    _cur = bool(_ret) and _ret[:10] > dt.date.today().isoformat()   # official return date still ahead = current status, whatever its post date
    return {"current": _cur, "status": res or st, "note": ij.get("longComment") or ij.get("shortComment"), "date": ij.get("date"), "detail": ((ij.get("details") or {}).get("type") or ""),
            "reserve": bool(res), "ret": (ij.get("details") or {}).get("returnDate")}
ids = list(P)
with ThreadPoolExecutor(24) as ex: OWN = dict(zip(ids, ex.map(own, ids)))
added = stale = 0
for pid, (f, p) in P.items():
    cur = p.get("inj")
    new = OWN.get(pid)
    pick = new if new else cur          # own entry first, team list (already on profile) as fallback
    if pick and not pick.get("reserve") and not pick.get("current") and pick.get("status") and (pick.get("date") or "")[:10] and last_game(p) > (pick.get("date") or "")[:10]:
        pick = None; stale += 1          # played since the status date
    if pick and pick.get("status") == "Active": pick = None
    dd = (pick or {}).get("date") or ""
    if pick and new and not pick.get("reserve") and not pick.get("current") and (dd[:10] < "%d-08-01" % SEASON or (pick["status"] in ("Questionable", "Probable") and dd[:10] < (dt.date.today() - dt.timedelta(days=10)).isoformat())):
        pick = cur if cur is not new else None   # old preseason or week-old game-status entry: not current
    if (pick or None) != (cur or None):
        if pick and not cur: added += 1; print("status added:", p["name"], p["team"], pick["status"])
        p["inj"] = pick
        json.dump(p, open(f, "w"), separators=(",", ":"))
print("player status: checked", len(ids), "own entries", sum(1 for v in OWN.values() if v), "added", added, "stale ignored", stale)

# ---- v2 (Nov 5): roster moves, season-ending outs, reported pending trades, and source-name scrub. Display only. ----
# Official moves come from the league transactions feed (last 21 days). A trade reported in team news but not yet in
# transactions is "reported, pending": the player stays on his official team, with a pending note. A season-ending
# out comes from the newest status note or team news ("rest of the season", "season-ending", "out for the season").
import re
SCRUB = re.compile(r"\b(?:ESPN(?:'s)?|NFL Network(?:'s)?|Rotoworld|PFT|ProFootballTalk|KFAN|Adam Schefter|Schefter|Ian Rapoport|Rapoport|Tom Pelissero|Pelissero|Field Yates|Yates|The Athletic|Athletic|Wacker)\b('s)?", re.I)
def scrub(t):
    if not t: return t
    t = re.sub(r"(^|(?<=[.!?]\s))[Aa]ccording to (?:[A-Z][\w'.]+\s?){1,4},\s*(\w)", lambda m: m.group(1) + m.group(2).upper(), t)
    t = re.sub(r",?\s*(?:according to|per|sources told)\s+(?:[A-Z][\w'.]+\s?){1,4}(?:and\s+(?:[A-Z][\w'.]+\s?){1,4})?(?=[,.;])", "", t)
    t = re.sub(r"(?:[A-Z][\w'.-]+\s){1,3}(?:and\s(?:[A-Z][\w'.-]+\s){1,3})?of\s(?:The\s)?(?:Athletic|NFL Network|ESPN|CBS Sports|NBC Sports|Fox Sports|SI|Yahoo Sports|USA Today|[A-Z][\w.]+\s(?:Post|Times|Tribune|Sun|Star|Herald|Journal|Globe|News)|)\s?", "reporters ", t)
    t = re.sub(r"reporters (reports|relays|says|notes|adds)\b", lambda m: "reporters " + m.group(1)[:-1], t).replace("reporters report that", "reports say that")
    t = SCRUB.sub("", t); t = re.sub(r"\s{2,}", " ", t).replace(" 's", "").replace(" ,", ",").replace(" .", ".")
    return re.sub(r"\b(\w+) report suggests", "reports suggest", t).strip()
SEASON_END = re.compile(r"(rest of the (?:20\d\d )?season|season[- ]ending|out for the season|miss (?:the )?(?:rest|remainder) of)", re.I)
byname = {}
for f in glob.glob(os.path.join(D, "players", "*.json")):
    q = json.load(open(f)); byname.setdefault(q.get("name", "").lower(), []).append((f, q))
tx = (js("https://site.api.espn.com/apis/site/v2/sports/football/nfl/transactions?limit=400") or {}).get("transactions", [])
cut = (dt.date.today() - dt.timedelta(days=21)).isoformat()
MOVES = {}
for t in tx:
    if (t.get("date") or "")[:10] < cut: continue
    ab = FIX.get(t["team"]["abbreviation"], t["team"]["abbreviation"]); desc = t.get("description") or ""
    for m in re.finditer(r"(?:Acquired|Traded for|Claimed)\s+(?:[A-Z]{1,3}\s+)?([A-Z][\w.'-]+(?:\s[A-Z][\w.'-]+){1,2})", desc):
        MOVES[m.group(1).lower()] = {"to": ab, "state": "official", "date": t["date"][:10]}
    for m in re.finditer(r"Traded\s.*?\bfor\s+(?:[A-Z]{1,3}\s+)([A-Z][\w.'-]+(?:\s[A-Z][\w.'-]+){1,2})", desc):
        MOVES[m.group(1).lower()] = {"to": ab, "state": "official", "date": t["date"][:10]}
# reported trades: team news headlines "<team> finalizing/acquire trade ... QB <Name>"
teams_js = (js("https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams") or {}).get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
NEWS = {}
def tnews(t):
    ab = FIX.get(t["team"]["abbreviation"], t["team"]["abbreviation"])
    return ab, (js("https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?team=%s&limit=30" % t["team"]["id"]) or {}).get("articles", [])
with ThreadPoolExecutor(8) as ex:
    for ab, arts in ex.map(tnews, teams_js): NEWS[ab] = [a for a in arts if (a.get("published") or "")[:10] >= cut]
NICK = {}
for t in teams_js:
    NICK[t["team"]["name"].lower()] = FIX.get(t["team"]["abbreviation"], t["team"]["abbreviation"])
for _src, arts in NEWS.items():
    for a in arts:
        h = a.get("headline") or ""
        m = re.search(r"(finaliz\w+|agree\w*|complet\w+|acquir\w+)\s+(?:a\s+)?trade.*?\b(?:QB|RB|WR|TE)\s+([A-Z][\w.'-]+\s[A-Z][\w.'-]+)", h) or re.search(r"trade\s+for\s+(?:QB|RB|WR|TE)\s+([A-Z][\w.'-]+\s[A-Z][\w.'-]+)", h)
        if not m: continue
        nm = m.group(m.lastindex).lower()
        pre = h[:m.start()].lower()   # the acquiring team is the one named before the verb
        ab = next((v for k, v in NICK.items() if k in pre), None)
        if not ab: continue
        if nm in MOVES and MOVES[nm]["to"] == ab: continue
        if "finaliz" in h.lower() or "sources" in h.lower():
            MOVES.setdefault(nm, {"to": ab, "state": "pending", "date": (a.get("published") or "")[:10]})
def _depth_on(ab, pid):
    tid = next((t["team"]["id"] for t in teams_js if FIX.get(t["team"]["abbreviation"], t["team"]["abbreviation"]) == ab), None)
    d = js("https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/%s/depthcharts" % tid) if tid else None
    for f in (d or {}).get("depthchart", []):
        for k, v in (f.get("positions") or {}).items():
            for i, a in enumerate(v.get("athletes") or []):
                if str(a.get("id")) == str(pid): return {"pos": (v.get("position") or {}).get("abbreviation") or k.upper(), "rank": i + 1, "unit": f.get("name"), "team": ab}
    return None
season_out = 0; moved = 0
NEXT = {}   # team -> next game, from players whose team was not moved
for f in glob.glob(os.path.join(D, "players", "*.json")):
    x = json.load(open(f))
    if x.get("next") and x.get("team") and not x.get("move") and x.get("grp") == "QB": NEXT.setdefault(x["team"], x["next"])
for nm, mv in MOVES.items():
    for f, q in byname.get(nm, []):
        espn_team = None
        d = js("https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/%s" % q["id"]) or {}
        _ea = ((d.get("athlete") or {}).get("team") or {}).get("abbreviation") or ""
        espn_team = FIX.get(_ea, _ea) or None
        if mv["state"] == "pending" and espn_team and espn_team != mv["to"]:
            q["team"] = espn_team   # official team until the deal is in the transactions feed
            q["move"] = {"to": mv["to"], "from": espn_team, "state": "pending", "date": mv["date"],
                         "label": "Trade to %s reported, not yet official" % mv["to"]}
        else:
            q["move"] = {"to": mv["to"], "state": "official", "date": mv["date"], "label": "Acquired by %s" % mv["to"]}
            q["team"] = mv["to"]
        # next game follows the official team (copy from a teammate's profile)
        if NEXT.get(q["team"]): q["next"] = NEXT[q["team"]]
        q["depth"] = _depth_on(q["team"], q["id"])   # slot on his official team's depth chart (None if not listed)
        moved += 1; print("roster move:", q["name"], q["move"]["label"], "official team", q["team"])
        json.dump(q, open(f, "w"), separators=(",", ":"))
        try:   # player index (search, team lists) uses the official team too
            PI = os.path.join(D, "pindex.json"); pi = json.load(open(PI))
            for r in pi.get("p", []):
                if isinstance(r, list) and str(r[0]) == str(q["id"]):
                    for k, v in enumerate(r):
                        if v == mv["to"] and q["team"] != mv["to"]: r[k] = q["team"]
            json.dump(pi, open(PI, "w"), separators=(",", ":"))
        except Exception as e: print("pindex patch skipped:", e)
scrubbed = 0
for f in glob.glob(os.path.join(D, "players", "*.json")):
    q = json.load(open(f)); ch = False
    ij = q.get("inj") or {}
    if ij.get("note"):
        s = scrub(ij["note"]); ch |= s != ij["note"]; ij["note"] = s
    _r = (ij.get("ret") or "")[:10]
    if _r and ij.get("season") and _r < "%d-02-01" % (SEASON + 1):   # official return date inside this season: not season-ending
        ij.pop("season", None); ij.pop("label", None); ch = True; print("return date in season, not season-ending:", q["name"], _r)
    elif _r and _r >= "%d-02-01" % (SEASON + 1) and ij.get("status") in ("Out", "Injured Reserve", "Reserve/PUP", "Reserve/NFI") and not ij.get("season"):
        ij["season"] = True; ij["label"] = "Out for season"; ch = True; season_out += 1
    if ij.get("status") in ("Out", "Injured Reserve", "Doubtful") and not ij.get("season") and not (_r and _r < "%d-02-01" % (SEASON + 1)):
        nm = (q.get("name") or "").lower(); last = nm.split()[-1] if nm else "~"
        txts = [ij.get("note") or ""] + [(a.get("headline") or "") + " " + (a.get("description") or "") for a in NEWS.get(q.get("team"), []) if last in ((a.get("headline") or "") + (a.get("description") or "")).lower()]
        def _hit(x):   # sentence-level, and not hedged ("potentially season-ending" stays a plain Out)
            for sn in re.split(r"(?<=[.!?])\s+", x):
                if SEASON_END.search(sn) and not re.search(r"potential|possibl|could|may |might|fear|if ", sn, re.I) and (x is txts[0] or last in sn.lower()): return True
            return False
        if any(_hit(x) for x in txts):
            ij["season"] = True; ij["label"] = "Out for season"; ch = True; season_out += 1
            print("season-ending:", q["name"], q.get("team"))
    for n in q.get("news") or []:
        for k in ("h", "d"):
            if n.get(k):
                s = scrub(n[k]); ch |= s != n[k]; n[k] = s
    if ch:
        scrubbed += 1; json.dump(q, open(f, "w"), separators=(",", ":"))
print("v2: roster moves", moved, "season-ending", season_out, "profiles scrubbed", scrubbed)
# team injury lists on the hub (data/v2.json "inj"): mark season-ending outs and scrub notes
try:
    V2 = os.path.join(D, "v2.json"); v2 = json.load(open(V2)); n2 = 0
    for f in glob.glob(os.path.join(D, "players", "*.json")):
        q = json.load(open(f)); ij = q.get("inj") or {}
        if not ij.get("season"): continue
        for r in (v2.get("inj") or {}).get(q.get("team"), []):
            if str(r.get("id")) == str(q["id"]) and r.get("st") != "Out for season": r["st"] = "Out for season"; n2 += 1
    for L in (v2.get("inj") or {}).values():
        for r in L:
            for k in ("d", "note"):
                if isinstance(r.get(k), str): r[k] = scrub(r[k])
    json.dump(v2, open(V2, "w"), separators=(",", ":")); print("v2.json team lists: season-ending marked", n2)
except Exception as e: print("v2.json patch skipped:", e)
# ---- v3 (Nov 5): reconcile with the 32 official rosters ----
# - active-roster players with no profile get a minimal one (name/team/pos/status), so they can be searched and shown
# - a profile whose player is on no roster at all (released / unsigned) shows team "FA" instead of his old team
# - practice-squad players stay out (no profile by design: no NFL snaps to show) unless they already have one
# - pindex.json is rebuilt from the profile files so the two always match
try:
    ROS = {}
    def _ro(t):
        ab = FIX.get(t["team"]["abbreviation"], t["team"]["abbreviation"])
        r = js("https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/%s/roster" % t["team"]["id"]) or {}
        return ab, [a for g in r.get("athletes", []) for a in g.get("items", [])]
    with ThreadPoolExecutor(8) as ex:
        for ab, L in ex.map(_ro, teams_js):
            for a in L: ROS[str(a["id"])] = (ab, a)
    if len(ROS) < 1500: raise RuntimeError("roster pull incomplete (%d)" % len(ROS))
    files = {}
    for f in glob.glob(os.path.join(D, "players", "*.json")):
        q = json.load(open(f)); files[str(q["id"])] = (f, q)
    made = fa = 0
    for pid, (ab, a) in ROS.items():
        if pid in files or (a.get("status") or {}).get("name") == "Practice Squad": continue
        pos = (a.get("position") or {}).get("abbreviation") or ""
        grp = "QB" if pos == "QB" else "RB" if pos in ("RB", "FB") else "WR" if pos == "WR" else "TE" if pos == "TE" else "K" if pos in ("K", "PK", "P") else "DEF"
        ij = (a.get("injuries") or [{}])[0]
        q = {"id": pid, "name": a.get("fullName"), "team": ab, "pos": pos, "grp": grp, "num": a.get("jersey"), "head": "https://a.espncdn.com/i/headshots/nfl/players/full/%s.png" % pid,
             "age": a.get("age"), "exp": str((a.get("experience") or {}).get("years", "")), "college": (a.get("college") or {}).get("name"), "draft": None, "depth": None,
             "inj": ({"status": ij["status"], "date": ij.get("date"), "detail": ""} if ij.get("status") else None), "next": NEXT.get(ab), "dvp": None, "news": [], "log": [], "season": SEASON}
        fp = os.path.join(D, "players", "%s.json" % pid); json.dump(q, open(fp, "w"), separators=(",", ":")); files[pid] = (fp, q); made += 1
    for pid, (f, q) in files.items():
        if pid not in ROS and q.get("team") not in ("FA", None) and not q.get("move"):
            q["team"] = "FA"; q["depth"] = None; q["next"] = None; json.dump(q, open(f, "w"), separators=(",", ":")); fa += 1
        elif pid in ROS and q.get("team") == "FA":
            q["team"] = ROS[pid][0]; json.dump(q, open(f, "w"), separators=(",", ":"))
    PI = os.path.join(D, "pindex.json"); pi = json.load(open(PI))
    pi["p"] = sorted([[pid, q["name"], q["team"], q.get("pos")] for pid, (f, q) in files.items() if q.get("name")], key=lambda x: x[1])
    json.dump(pi, open(PI, "w"), separators=(",", ":"))
    print("v3 rosters: on rosters", len(ROS), "practice squad", sum(1 for _, a in ROS.values() if (a.get("status") or {}).get("name") == "Practice Squad"), "profiles made", made, "set FA (on no roster)", fa, "pindex", len(pi["p"]))
except Exception as e: print("v3 roster reconcile skipped:", e)
