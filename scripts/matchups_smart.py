"""Matchup Board smart refresh (Nov 3). 'check': fingerprint the inputs that move the board - live NFL injury statuses
(newest timestamp wins), Bet Lab game lines / prop lines + O-U prices, and the adjusted-defense inputs (finished games,
weekly snap counts, game-log freshness) - and say whether a rebuild is due.
'settle': keep data/matchups.json only if the board itself changed (ignoring the 'updated' stamp)."""
import json, sys, os, hashlib, subprocess, urllib.request, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); FP = ROOT + "/data/matchups_fp.json"
BL = "https://betlab.sportslabshq.com/data/"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u + ("&" if "?" in u else "?") + "t=%d" % time.time(), headers={"User-Agent": "Mozilla/5.0"}), timeout=40) as r: return json.load(r)
def parts():
    P = {}
    try:
        d = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"); L = []
        for t in d.get("injuries", []):
            for i in t.get("injuries", []): L.append(((i.get("athlete") or {}).get("displayName", ""), i.get("status"), i.get("date")))
        P["inj"] = sorted(map(list, L))
    except Exception as e: print("inj feed", e)
    try: P["games"] = sorted([g.get("id"), g.get("spread"), g.get("total"), g.get("mla"), g.get("mlh")] for g in get(BL + "games_nfl.json"))
    except Exception as e: print("games", e)
    try:
        pr = get(BL + "props_nfl.json"); pr = pr if isinstance(pr, list) else pr.get("props", [])
        P["props"] = sorted([str(p.get("aid")), str(p.get("market")), str(p.get("line")), str(p.get("ov") or p.get("over") or p.get("price")), str(p.get("un") or p.get("under"))] for p in pr)
    except Exception as e: print("props", e)
    # adjusted-defense inputs (Nov 3): finished games (box scores), weekly snap counts, game-log freshness
    try:
        sb = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"); wk = (sb.get("week") or {}).get("number") or 1
        evs = sb.get("events", []) + get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week=%d&dates=2026" % max(1, wk - 1)).get("events", [])
        P["finals"] = sorted({e["id"] for e in evs if ((e.get("status") or {}).get("type") or {}).get("completed")})
    except Exception as e: print("finals", e)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import adjdef
        with urllib.request.urlopen(urllib.request.Request(adjdef.SNAPS, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r: P["snaps"] = hashlib.sha256(r.read()).hexdigest()
    except Exception as e: print("snaps", e)
    try:
        pl = get(BL + "plogs_nfl.json"); P["plogs"] = [sum(map(len, pl.values())), max((g["d"] for L in pl.values() for g in L), default="")]
    except Exception as e: print("plogs", e)
    return {k: hashlib.sha256(json.dumps(v).encode()).hexdigest()[:16] for k, v in P.items()}
def out(k, v):
    if os.environ.get("GITHUB_OUTPUT"): open(os.environ["GITHUB_OUTPUT"], "a").write("%s=%s\n" % (k, v))
    print(k, "=", v)
if sys.argv[1] == "check":
    new = parts(); old = json.load(open(FP)) if os.path.exists(FP) else {}
    ch = [k for k in new if new[k] != old.get(k)]
    if os.environ.get("FORCE") == "true": ch = ch or ["forced"]
    out("changed", "true" if ch else "false"); print("changed inputs:", ch or "none")
    json.dump(new, open(FP, "w"), sort_keys=True)
else:  # settle
    try: head = json.loads(subprocess.check_output(["git", "show", "HEAD:data/matchups.json"], cwd=ROOT))
    except Exception: head = {}
    cur = json.load(open(ROOT + "/data/matchups.json"))
    strip = lambda d: {k: v for k, v in d.items() if k != "updated"}
    if strip(head) == strip(cur): subprocess.call(["git", "checkout", "--", "data/matchups.json"], cwd=ROOT); out("board", "same")
    else: out("board", "changed")
