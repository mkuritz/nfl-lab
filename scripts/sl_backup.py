"""Backup scores (used ONLY when the primary scoreboard fails). Reads the Sports Labs scheduler's cached backup feed
(per-sport daily cap enforced server-side). Requires env SL_BACKUP_KEY; returns [] if absent. Never logs the key."""
import json, os, re, unicodedata, urllib.request
URL = "https://sl-scheduler.kuritzmike.workers.dev/scores/%s?date=%s"
_C = {}
def scores(sport, day):
    k = os.environ.get("SL_BACKUP_KEY"); key = (sport, str(day))
    if not k: return []
    if key in _C: return _C[key]
    try:
        r = urllib.request.urlopen(urllib.request.Request(URL % (sport, str(day)[:10]), headers={"X-SL-Backup": k, "User-Agent": "sports-labs"}), timeout=15)
        g = json.load(r).get("games") or []
    except Exception as e:
        print("backup scores unavailable for", sport, type(e).__name__); g = []
    _C[key] = g; return g
def _n(s): return re.sub(r"[^a-z0-9 ]", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).replace(" fc", "").replace("fc ", "").strip()
def same_team(a, b):
    a, b = _n(a), _n(b)
    if not a or not b: return False
    if a == b or a in b or b in a: return True
    wa, wb = a.split(), b.split()
    return wa[-1] == wb[-1] and len(wa[-1]) > 3   # nickname match (e.g. "Rangers")
def find(games, home, away):
    for g in games:
        if same_team(g.get("home"), home) and same_team(g.get("away"), away): return g
    return None
_A = None
def team_name(sport, abbr):
    global _A
    if _A is None:
        try: _A = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "team_abbr.json")))
        except Exception: _A = {}
    return (_A.get(sport) or {}).get(abbr) or abbr
def find_abbr(sport, games, home_abbr, away_abbr):
    return find(games, team_name(sport, home_abbr), team_name(sport, away_abbr))
