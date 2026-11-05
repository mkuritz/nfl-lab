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
