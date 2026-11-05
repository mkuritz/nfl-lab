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
    if p.get("grp") in ("QB", "RB", "WR", "TE") and p.get("team") and p["team"] != "FA": P[p["id"]] = (f, p)
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
    return {"status": st, "note": ij.get("longComment") or ij.get("shortComment"), "date": ij.get("date"), "detail": ((ij.get("details") or {}).get("type") or "")}
ids = list(P)
with ThreadPoolExecutor(16) as ex: OWN = dict(zip(ids, ex.map(own, ids)))
added = stale = 0
for pid, (f, p) in P.items():
    cur = p.get("inj")
    new = OWN.get(pid)
    pick = new if new else cur          # own entry first, team list (already on profile) as fallback
    if pick and pick.get("status") and (pick.get("date") or "")[:10] and last_game(p) > (pick.get("date") or "")[:10]:
        pick = None; stale += 1          # played since the status date
    if pick and pick.get("status") == "Active": pick = None
    dd = (pick or {}).get("date") or ""
    if pick and new and (dd[:10] < "%d-08-01" % SEASON or (pick["status"] in ("Questionable", "Probable") and dd[:10] < (dt.date.today() - dt.timedelta(days=10)).isoformat())):
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
SCRUB = re.compile(r"\b(?:ESPN(?:'s)?|NFL Network(?:'s)?|Rotoworld|PFT|ProFootballTalk|KFAN|Adam Schefter|Schefter|Ian Rapoport|Rapoport|Tom Pelissero|Pelissero|Field Yates|Yates)\b('s)?", re.I)
def scrub(t):
    if not t: return t
    t = re.sub(r"(^|(?<=[.!?]\s))[Aa]ccording to (?:[A-Z][\w'.]+\s?){1,4},\s*(\w)", lambda m: m.group(1) + m.group(2).upper(), t)
    t = re.sub(r",?\s*(?:according to|per|sources told)\s+(?:[A-Z][\w'.]+\s?){1,4}(?:and\s+(?:[A-Z][\w'.]+\s?){1,4})?(?=[,.;])", "", t)
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
season_out = 0; moved = 0
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
        moved += 1; print("roster move:", q["name"], q["move"]["label"], "official team", q["team"])
        json.dump(q, open(f, "w"), separators=(",", ":"))
scrubbed = 0
for f in glob.glob(os.path.join(D, "players", "*.json")):
    q = json.load(open(f)); ch = False
    ij = q.get("inj") or {}
    if ij.get("note"):
        s = scrub(ij["note"]); ch |= s != ij["note"]; ij["note"] = s
    if ij.get("status") in ("Out", "Injured Reserve", "Doubtful") and not ij.get("season"):
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
