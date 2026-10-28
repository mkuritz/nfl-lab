"""NFL Hub player profiles: one display JSON per player (data/players/<espn id>.json) + data/pindex.json.
Free public data only: weekly player stats, snap counts and play-by-play (open nflverse releases), ESPN depth charts,
same-day injuries/practice notes, team news and schedule. Display text never names a data source."""
import csv, gzip, io, json, os, sys, urllib.request, datetime as dt, collections
from concurrent.futures import ThreadPoolExecutor
UA = {"User-Agent": "SportsLabs/1.0"}
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
NV = "https://github.com/nflverse/nflverse-data/releases/download/"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/"
FIX = {"LA": "LAR", "WAS": "WSH"}
def raw(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90).read()
def js(u):
    try: return json.loads(raw(u))
    except Exception as e: print("fail", u, e); return None
def rows(u, gz=False):
    try: b = raw(u)
    except Exception as e: print("fail", u, e); return []
    if gz: b = gzip.decompress(b)
    return list(csv.DictReader(io.StringIO(b.decode("utf-8", "replace"))))
def num(x):
    try: return float(x)
    except Exception: return 0.0
today = dt.date.today(); SEASON = today.year if today.month >= 8 else today.year - 1
players = rows(NV + "players/players.csv")
G2E = {p["gsis_id"]: p["espn_id"] for p in players if p.get("espn_id")}
PFR2E = {p["pfr_id"]: p["espn_id"] for p in players if p.get("espn_id") and p.get("pfr_id")}
BIO = {p["espn_id"]: p for p in players if p.get("espn_id")}
weekly = collections.defaultdict(list)
for yr in (SEASON, SEASON - 1):
    for r in rows(NV + "stats_player/stats_player_week_%d.csv" % yr):
        if r["season_type"] != "REG": continue
        e = G2E.get(r["player_id"])
        if e: weekly[e].append(r)
snaps = {}
for yr in (SEASON, SEASON - 1):
    for r in rows(NV + "snap_counts/snap_counts_%d.csv" % yr):
        e = PFR2E.get(r["pfr_player_id"])
        if e: snaps[(e, int(r["season"]), int(r["week"]))] = (num(r["offense_pct"]), num(r["defense_pct"]), num(r["st_pct"]))
rz = collections.Counter()
for r in rows(NV + "pbp/play_by_play_%d.csv.gz" % SEASON, gz=True):
    if r.get("season_type") != "REG" or num(r.get("yardline_100") or 99) > 20: continue
    for k in ("rusher_player_id", "receiver_player_id"):
        e = G2E.get(r.get(k) or "")
        if e: rz[(e, int(r["week"]))] += 1
# ESPN: teams, depth charts, injuries, news, schedule
teams = {t["team"]["abbreviation"]: t["team"]["id"] for t in (js(ESPN + "teams") or {}).get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])}
depth, news = {}, {}
def team_pull(ab):
    tid = teams[ab]; d = js(ESPN + "teams/%s/depthcharts" % tid) or {}
    out = {}
    for ch in d.get("depthchart", []) or d.get("items", []):
        for pos, v in (ch.get("positions") or {}).items():
            for i, a in enumerate(v.get("athletes", [])):
                aid = str(a.get("id") or "")
                SPEC = {"PR", "KR", "H", "LS", "P", "PK"}
                ab_ = ((v.get("position") or {}).get("abbreviation", pos) or "").upper()
                if aid and (aid not in out or (out[aid]["pos"] in SPEC and ab_ not in SPEC)): out[aid] = {"pos": (v.get("position") or {}).get("abbreviation", pos).upper(), "rank": i + 1, "unit": ch.get("name", "")}
    n = js(ESPN + "news?team=%s&limit=40" % tid) or {}
    return ab, out, [{"h": a.get("headline"), "d": a.get("description"), "t": a.get("published")} for a in n.get("articles", [])]
with ThreadPoolExecutor(6) as ex:
    for ab, dp, nw in ex.map(team_pull, list(teams)):
        for k, v in dp.items(): depth[k] = dict(v, team=ab)
        news[ab] = nw
inj = {}
for t in (js("https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/injuries") or {}).get("injuries", []):
    for i in t.get("injuries", []):
        href = ((i.get("athlete") or {}).get("links") or [{}])[0].get("href", "")
        aid = href.split("/id/")[1].split("/")[0] if "/id/" in href else None
        if aid: inj[aid] = {"status": i.get("status"), "note": i.get("longComment") or i.get("shortComment"), "date": i.get("date"), "detail": ((i.get("details") or {}).get("type") or "")}
nextopp = {}
for k in range(0, 10):
    day = (today + dt.timedelta(days=k)).strftime("%Y%m%d")
    for e in (js(ESPN + "scoreboard?dates=" + day) or {}).get("events", []):
        c = e["competitions"][0]
        if c["status"]["type"]["state"] != "pre": continue
        t = {x["homeAway"]: x["team"]["abbreviation"] for x in c["competitors"]}
        for side, o in (("home", "away"), ("away", "home")):
            nextopp.setdefault(t[side], {"opp": t[o], "home": side == "home", "date": e["date"]})
try: dvp = json.loads(raw("https://betlab.sportslabshq.com/data/nfl_dvp.json"))
except Exception: dvp = {}
KEEP = ["completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions", "passing_epa", "passing_cpoe", "sacks_suffered", "passing_air_yards",
        "carries", "rushing_yards", "rushing_tds", "rushing_epa", "receptions", "targets", "receiving_yards", "receiving_tds", "receiving_air_yards",
        "receiving_yards_after_catch", "target_share", "air_yards_share", "receiving_epa", "def_tackles_solo", "def_tackle_assists", "def_tackles_for_loss",
        "def_sacks", "def_qb_hits", "def_interceptions", "def_pass_defended", "def_fumbles_forced", "fg_made", "fg_att", "fg_long", "pat_made", "pat_att", "fantasy_points_ppr"]
# Live Sleeper + trade overrides for mid-season trades & practice-squad/active promotions
TRADE_OV = {"2971282": "SF", "3129308": "SEA", "4361196": "IND", "4685970": "IND", "4838270": "IND", "4371336": "IND", "4689989": "IND", "3929641": "SF", "4362135": "FA"}
TRADE_POS = {"2971282": "DT", "3129308": "G", "4361196": "CB", "4685970": "CB", "4838270": "G", "4371336": "CB", "4689989": "CB", "3929641": "DT", "4362135": "G"}
sl_team, sl_name, sl_pos = {}, {}, {}
try:
    for _sp in (js("https://api.sleeper.app/v1/players/nfl") or {}).values():
        _eid = str(_sp.get("espn_id") or "")
        if _eid and _sp.get("active") and _sp.get("team"):
            sl_team[_eid] = FIX.get(_sp["team"], _sp["team"])
            if _sp.get("full_name"): sl_name[_eid] = _sp["full_name"]
            if _sp.get("position"): sl_pos[_eid] = _sp["position"]
except Exception as _e: print("sleeper warn:", _e)
inj.setdefault("4361196", {"status": "Injured Reserve", "note": "Placed on Injured Reserve on Oct 27, 2026 due to a groin injury (out at least 4 games).", "date": "2026-10-27T23:40Z", "detail": "Groin"})
ids = set(weekly) | set(depth) | set(TRADE_OV)
idx = []
os.makedirs(os.path.join(OUT, "players"), exist_ok=True)
for e in ids:
    W = sorted(weekly.get(e, []), key=lambda r: (int(r["season"]), int(r["week"])), reverse=True)
    b = BIO.get(e, {}); dp = depth.get(e, {})
    name = (W[0]["player_display_name"] if W else None) or b.get("display_name") or sl_name.get(e)
    if not name: continue
    # Prioritize today's live depth chart / Sleeper active team / trade overrides over completed game logs so mid-week trades update immediately
    team = TRADE_OV.get(e) or dp.get("team") or sl_team.get(e) or (FIX.get(W[0]["team"], W[0]["team"]) if W and int(W[0]["season"]) == SEASON else FIX.get(b.get("latest_team", ""), b.get("latest_team", "")))
    pos = TRADE_POS.get(e) or (W[0]["position"] if W else None) or b.get("position") or dp.get("pos", "") or sl_pos.get(e, "")
    log = []
    for r in W:
        s, w = int(r["season"]), int(r["week"]); sn = snaps.get((e, s, w))
        g = {"s": s, "w": w, "o": FIX.get(r["opponent_team"], r["opponent_team"]), "t": FIX.get(r["team"], r["team"]), "g": r["game_id"]}
        g.update({k: round(num(r[k]), 3) for k in KEEP if r.get(k) not in (None, "", "NA") and num(r[k]) != 0})
        if sn: g["snap"] = round(sn[0] * 100) if sn[0] else round(sn[1] * 100) if sn[1] else None; g["st"] = round(sn[2] * 100)
        if rz.get((e, w)) and s == SEASON: g["rz"] = rz[(e, w)]
        g["home"] = r["game_id"].endswith("_" + r["team"])
        log.append(g)
    no = nextopp.get(team)
    grp = "QB" if pos == "QB" else "RB" if pos in ("RB", "FB") else "WR" if pos == "WR" else "TE" if pos == "TE" else "K" if pos in ("K", "PK", "P") else "DEF"
    dv = None
    if no and grp in ("QB", "RB", "WR", "TE"):
        x = ((dvp.get("teams") or {}).get(no["opp"]) or {}).get(grp)
        if x: dv = dict(x, n=dvp.get("n", 32), g=((dvp.get("teams") or {}).get(no["opp"]) or {}).get("g"))
    nn = name.lower(); last = nn.split()[-1]
    nw = [a for a in news.get(team, []) if nn in ((a["h"] or "") + " " + (a["d"] or "")).lower()][:5]
    P = {"id": e, "name": name, "team": team, "pos": pos, "grp": grp, "num": b.get("jersey_number"), "head": "https://a.espncdn.com/i/headshots/nfl/players/full/%s.png" % e,
         "age": None, "exp": b.get("years_of_experience"), "college": b.get("college_name"), "draft": [b.get("draft_year"), b.get("draft_round"), b.get("draft_pick")] if b.get("draft_year") else None,
         "depth": dp or None, "inj": inj.get(e), "next": no, "dvp": dv, "news": nw, "log": log, "season": SEASON}
    if b.get("birth_date"):
        try: bd = dt.date.fromisoformat(b["birth_date"]); P["age"] = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        except Exception: pass
    json.dump(P, open(os.path.join(OUT, "players", e + ".json"), "w"), separators=(",", ":"))
    idx.append([e, name, team, pos])
json.dump({"updated": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "p": sorted(idx, key=lambda x: x[1])}, open(os.path.join(OUT, "pindex.json"), "w"), separators=(",", ":"))
print("profiles", len(idx), "with games", sum(1 for e in ids if weekly.get(e)), "depth", len(depth), "inj", len(inj), "next", len(nextopp))
