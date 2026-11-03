"""Opponent- and personnel-adjusted defense numbers for the Matchup Board (display only; never feeds Highlighted plays).
Method, per defense game in 2026:
 1) Opponent quality: what the defense allowed minus how far above/below league average that offense is in its OTHER games
    (shrunk 2 games toward average). Holding a top offense to average yards is good; a bad offense putting up average yards is not.
 2) Who played (weekly snap counts; game-log presence when a week has no snaps yet):
    - the offense: its QB1 (most 2026 pass attempts) and its top RB/WR/TE. Holding a short-handed offense down counts less
      (QB1 out: half weight; each missing top skill player: x0.8). Getting beaten by a short-handed offense counts fully.
    - the defense: its current depth-chart starters who are healthy now. A game where some of them sat (under 35% of defensive
      snaps) counts less when the defense gave up a lot (x0.8 per missing starter, floor 0.4). A good game while short-handed counts fully.
 Adjusted value = weighted mean of the per-game adjusted numbers. Raw values are kept alongside for the Advanced stats view."""
import csv, io, re, os, json, collections, datetime as dt, urllib.request, statistics as st
SNAPS = "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_2026.csv"
TEAM_FIX = {"LA": "LAR", "WAS": "WSH", "JAC": "JAX", "LVR": "LV", "OAK": "LV", "SD": "LAC", "STL": "LAR"}
DEFP = {"DE", "DT", "NT", "DL", "LB", "ILB", "OLB", "MLB", "WLB", "SLB", "LILB", "RILB", "CB", "LCB", "RCB", "NB", "S", "FS", "SS", "SAF", "DB", "LDE", "RDE", "LDT", "RDT", "EDGE"}
OUT = ("Out", "Doubtful", "Suspended", "Injured Reserve", "Physically Unable to Perform", "Reserve")
def nm(s): return re.sub(r"[^a-z]", "", re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", (s or "").lower()))
def week_of(d): return (dt.date.fromisoformat(d[:10]) - dt.date(2026, 9, 8)).days // 7 + 1
def load_snaps(cache=None):
    txt = None
    if cache and os.path.exists(cache) and (dt.datetime.now().timestamp() - os.path.getmtime(cache)) < 6 * 3600: txt = open(cache).read()
    if txt is None:
        try:
            with urllib.request.urlopen(SNAPS, timeout=60) as r: txt = r.read().decode()
            if cache: open(cache, "w").write(txt)
        except Exception as e:
            print("snap counts unavailable", e); txt = open(cache).read() if cache and os.path.exists(cache) else ""
    S = collections.defaultdict(dict)   # (team, week) -> {namekey: (off_pct, def_pct)}
    for r in csv.DictReader(io.StringIO(txt)):
        if r.get("game_type") != "REG": continue
        t = TEAM_FIX.get(r["team"], r["team"])
        S[(t, int(r["week"]))][nm(r["player"])] = (float(r["offense_pct"] or 0), float(r["defense_pct"] or 0))
    return S
STATK = ("ry", "ra", "py", "pa", "td", "rec_WR", "rec_TE", "rec_RB", "td_WR", "td_TE", "td_RB")
def build(plogs, P, inj, cache=None, min_rows=15):
    S = load_snaps(cache); snap_weeks = {w for (_, w) in S}
    TG = collections.defaultdict(lambda: collections.defaultdict(float)); rows = collections.Counter(); meta = {}
    present = collections.defaultdict(set)   # (team,event) -> aids with a log row
    for aid, L in plogs.items():
        pos = (P.get(aid) or {}).get("pos")
        for g in L:
            if g["d"] < "2026-09-01": continue
            k = (g["t"], g["e"]); s = g["s"]; d = TG[k]; rows[k] += 1; meta[k] = (g["o"], g["d"]); present[k].add(aid)
            d["ry"] += s.get("rushingYards", 0); d["ra"] += s.get("rushingAttempts", 0); d["py"] += s.get("passingYards", 0); d["pa"] += s.get("passingAttempts", 0)
            td = s.get("rushingTouchdowns", 0) + s.get("receivingTouchdowns", 0); d["td"] += td
            if pos in ("WR", "TE", "RB"): d["rec_" + pos] += s.get("receivingYards", 0); d["td_" + pos] += td
            d["pa_" + aid] = s.get("passingAttempts", 0)
    keys = [k for k in TG if rows[k] >= min_rows]
    def val(d, m):
        if m == "ypc": return d["ry"] / d["ra"] if d["ra"] else None
        if m == "ypa": return d["py"] / d["pa"] if d["pa"] else None
        return d[{"rush_g": "ry", "pass_g": "py", "td_g": "td"}.get(m, m)]
    MET = ("rush_g", "ypc", "pass_g", "ypa", "td_g", "rec_WR", "rec_TE", "rec_RB", "td_WR", "td_TE", "td_RB")
    off = collections.defaultdict(list)
    for k in keys: off[k[0]].append(k)
    lg = {m: st.mean([v for k in keys if (v := val(TG[k], m)) is not None]) for m in MET}
    # offense key players (2026, by production with this team)
    tot = collections.defaultdict(lambda: collections.Counter())
    for aid, L in plogs.items():
        pos = (P.get(aid) or {}).get("pos")
        if pos not in ("QB", "RB", "WR", "TE"): continue
        for g in L:
            if g["d"] < "2026-09-01": continue
            s = g["s"]; tot[(g["t"], pos)][aid] += s.get("passingAttempts", 0) if pos == "QB" else s.get("receivingYards", 0) + s.get("rushingYards", 0)
    KEY = {}
    for (t, pos), c in tot.items():
        if c: KEY.setdefault(t, {})[pos] = c.most_common(1)[0][0]
    # defense regular starters, rebuilt from 2026 snap counts (not the depth chart): played 50%+ of defensive snaps in 60%+
    # of the team games he was active for (3+ games), still with this team in one of its last 2 snap weeks, not Out/IR now.
    STINT = {}
    STR = collections.defaultdict(list); NAME = {}
    tw = collections.defaultdict(list)
    for (t, w) in S: tw[t].append(w)
    for t in tw: tw[t].sort()
    byname = {}
    for aid, d in P.items():
        if d.get("team"): byname[(nm(d.get("name")), d["team"])] = aid
    for t, W in tw.items():
        cnt = collections.defaultdict(list)
        for w in W:
            for n, (op, dp) in S[(t, w)].items():
                if dp > 0: cnt[n].append((w, dp))
        for n, L in cnt.items():
            if len(L) < 3 or sum(dp >= 0.5 for _, dp in L) < 0.6 * len(L): continue
            if max(w for w, _ in L) < W[-2 if len(W) > 1 else -1]: continue   # gone from this team / not active lately
            aid = byname.get((n, t))
            stt = (inj.get(aid) or ("", ""))[1] if aid else ""
            if any((stt or "").startswith(o) for o in OUT): continue
            key = aid or ("snap:" + n); STR[t].append(key); NAME[key] = (P.get(aid) or {}).get("name") or n
            STINT[(key, t)] = (min(w for w, _ in L), max(w for w, _ in L))
    def onfield(aid, team, e, date, side):
        if str(aid).startswith('snap:') or side == 1: return dfield(aid, team, e, date)
        """True/False/None (unknown). side 0 = offense pct, 1 = defense pct."""
        w = week_of(date); n = nm((P.get(aid) or {}).get("name"))
        if w in snap_weeks and (team, w) in S:
            r = S[(team, w)].get(n)
            if r is not None: return r[side] >= 0.35
            # not in this week's snap table: missing only if he logged snaps for this team in another week
            if any(n in S[(team, ww)] for ww in snap_weeks if (team, ww) in S and ww != w): return False
            return None
        if aid in present[(team, e)]: return True
        seen = any(g["t"] == team and g["d"] >= "2026-09-01" for g in plogs.get(aid, []))
        return False if seen else None
    def dfield(key, team, e, date):
        w = week_of(date); lo, hi = STINT.get((key, team), (0, 99)); n = nm(NAME.get(key, "")) if str(key).startswith("snap:") else nm((P.get(key) or {}).get("name"))
        if str(key).startswith("snap:"): n = key[5:]
        if (team, w) in S:
            if w < lo: return None   # before he joined / became a regular
            r = S[(team, w)].get(n)
            return r is not None and r[1] >= 0.35
        if str(key).startswith("snap:"): return None
        if key in present.get((team, e), set()): return True
        return False if any(g["t"] == team and g["d"] >= "2026-09-01" for g in plogs.get(key, [])) else None
    ADJ = {}; INFO = collections.defaultdict(list)
    defs = collections.defaultdict(list)
    for k in keys: defs[meta[k][0]].append(k)   # games where meta opp = defense
    for D, G in defs.items():
        acc = {m: [0.0, 0.0, 0.0, 0] for m in MET}   # wsum, w, raw sum, n
        for k in G:
            O, e = k; date = meta[k][1]; d = TG[k]
            # offense depletion
            miss_o = []; qb = (KEY.get(O) or {}).get("QB")
            if qb:
                qa = d.get("pa_" + qb, 0)
                if qa < 10: miss_o.append(("QB", qb))
            for p in ("RB", "WR", "TE"):
                a = (KEY.get(O) or {}).get(p)
                if a and onfield(a, O, e, date, 0) is False: miss_o.append((p, a))
            wo = (0.5 if any(p == "QB" for p, _ in miss_o) else 1.0) * (0.8 ** sum(p != "QB" for p, _ in miss_o)); wo = max(wo, 0.4)
            miss_d = [a for a in STR.get(D, []) if onfield(a, D, e, date, 1) is False]
            wd = max(0.4, 0.8 ** len(miss_d))
            gi = dict(e=e, d=date, o=O, miss_o=[(p, (P.get(a) or {}).get("name")) for p, a in miss_o], miss_d=[NAME.get(a, a) for a in miss_d])
            for m in MET:
                x = val(d, m)
                if x is None: continue
                other = [v for kk in off[O] if kk != k and (v := val(TG[kk], m)) is not None]
                oq = (st.mean(other) - lg[m]) * len(other) / (len(other) + 2) if other else 0.0
                adj = x - oq   # what an average offense would have produced
                good_for_def = adj < lg[m]
                w = (wo if good_for_def else 1.0) * (1.0 if good_for_def else wd)
                a = acc[m]; a[0] += w * adj; a[1] += w; a[2] += x; a[3] += 1
                if m == "pass_g": gi.update(raw=round(x), adj=round(adj), w=round(w, 2), oq=round(oq, 1))
            INFO[D].append(gi)
        ADJ[D] = {m: (a[0] / a[1] if a[1] else None) for m, a in acc.items()}
        ADJ[D]["_n"] = len(G)
    return ADJ, INFO, lg, KEY, {t: [NAME.get(a, a) for a in L] for t, L in STR.items()}

def fill_recent(plogs, days=10):
    """Complete box scores for finished games in the last `days` days (same public scoreboard/summary feed as the injury data).
    Game-log rows for those games are replaced by the full box score so a game isn't missing players while logs catch up."""
    UA = {"User-Agent": "Mozilla/5.0"}
    def get(u):
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r: return json.load(r)
    now = dt.datetime.now(dt.timezone.utc); ET = dt.timezone(dt.timedelta(hours=-5))
    try:
        cur = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"); wk = (cur.get("week") or {}).get("number") or 1
        evs = list(cur.get("events", []))
        for w in range(max(1, wk - 2), wk):
            evs += get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week=%d&dates=2026" % w).get("events", [])
    except Exception as e: print("recent box scores unavailable", e); return []
    evs = [e for e in {e["id"]: e for e in evs}.values() if dt.datetime.fromisoformat(e["date"].replace("Z", "+00:00")) >= now - dt.timedelta(days=days)]
    done = []
    for ev in evs:
        if not ev.get("status", {}).get("type", {}).get("completed"): continue
        try: sm = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=" + ev["id"])
        except Exception as e: print("box", ev["id"], e); continue
        comp = sm["header"]["competitions"][0]; tms = {c["team"]["abbreviation"]: c.get("homeAway") for c in comp["competitors"]}
        if len(tms) != 2: continue
        d = dt.datetime.fromisoformat(comp["date"].replace("Z", "+00:00")).astimezone(ET).date().isoformat()
        rows = collections.defaultdict(dict)
        for tb in sm.get("boxscore", {}).get("players", []):
            t = tb["team"]["abbreviation"]; o = [x for x in tms if x != t][0]
            for cat in tb.get("statistics", []):
                for a in cat.get("athletes", []):
                    aid = a["athlete"]["id"]; s = rows[aid].setdefault("s", {}); rows[aid].update(t=t, o=o)
                    for k, v in zip(cat["keys"], a.get("stats", [])):
                        try:
                            if "/" in k:
                                k1, k2 = k.split("/"); v1, v2 = v.split("/") if "/" in v else (v, 0)
                                s[k1] = float(v1); s[k2] = float(v2)
                            else: s[k] = float(v)
                        except Exception: pass
        if not rows: continue
        for aid in plogs: plogs[aid] = [g for g in plogs[aid] if g["e"] != ev["id"]]
        for aid, r in rows.items():
            plogs.setdefault(aid, []).append(dict(at="vs" if tms[r["t"]] == "home" else "@", d=d, e=ev["id"], o=r["o"], s=r["s"], t=r["t"]))
        done.append((d, ev.get("shortName"), len(rows)))
    return done
