"""NFL betting trends (display data only). Sources: nflverse public schedules (scores, closing spread/total, rest, division)
and nflverse public play-by-play (score by quarter, deficits). Team codes are ESPN-style (LAR, WSH) to match the hub."""
import csv, gzip, io, json, urllib.request, datetime, collections
PBP = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.csv.gz"
SCHED = "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
TM = {"LA": "LAR", "WAS": "WSH", "LV": "LV", "OAK": "LV", "SD": "LAC", "STL": "LAR"}
tm = lambda t: TM.get(t, t)
UA = {"User-Agent": "SportsLabs/1.0"}
def get(u, t=180): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
def season_now():
    t = datetime.date.today(); return t.year if t.month >= 8 else t.year - 1

# ---------------- quarter / comeback (play-by-play) ----------------
def pbp_games(yr):
    raw = get(PBP.format(yr)); G = {}
    for r in csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), encoding="utf-8")):
        try: q = int(float(r["qtr"])); h = int(float(r["total_home_score"])); a = int(float(r["total_away_score"]))
        except (ValueError, KeyError): continue
        g = G.setdefault(r["game_id"], {"home": tm(r["home_team"]), "away": tm(r["away_team"]), "end": {}, "seq": []})
        g["end"][q] = (h, a); g["seq"].append((q, h - a))
    return G
def qblank(): return {"g": 0, "cb": 0, "cb7": 0, "cb10": 0, "cb4": 0, "big": 0, "blown": 0, "l1q": [0, 0], "lht": [0, 0], "t3q": [0, 0],
                      "q": {k: {"f": 0, "a": 0, "w": 0} for k in ["1Q", "2Q", "3Q", "4Q", "1H", "2H"]}}
def q_stats(G):
    T = collections.defaultdict(qblank)
    for g in G.values():
        E = g["end"]
        if 4 not in E: continue
        last = E[max(E)]; prev = (0, 0); per = {}
        for q in (1, 2, 3, 4):
            cur = E.get(q, prev); per[q] = (cur[0] - prev[0], cur[1] - prev[1]); prev = cur
        per["1H"] = (per[1][0] + per[2][0], per[1][1] + per[2][1]); per["2H"] = (last[0] - E[2][0], last[1] - E[2][1]) if 2 in E else (0, 0)
        for side, sgn in (("home", 1), ("away", -1)):
            t = T[g[side]]; t["g"] += 1
            for k, lab in ((1, "1Q"), (2, "2Q"), (3, "3Q"), (4, "4Q"), ("1H", "1H"), ("2H", "2H")):
                f, a = per[k] if sgn == 1 else per[k][::-1]; t["q"][lab]["f"] += f; t["q"][lab]["a"] += a; t["q"][lab]["w"] += f > a
            final = sgn * (last[0] - last[1]); diffs = [sgn * d for _, d in g["seq"]]; d4 = [sgn * d for q, d in g["seq"] if q >= 4]
            for key, qq in (("l1q", 1), ("lht", 2), ("t3q", 3)):  # led at end of 1Q / halftime / 3Q -> won?
                if qq in E and sgn * (E[qq][0] - E[qq][1]) > 0: t[key][0] += 1; t[key][1] += final > 0
            if final > 0 and min(diffs) < 0:
                t["cb"] += 1; t["big"] = max(t["big"], -min(diffs))
                if min(diffs) <= -7: t["cb7"] += 1
                if min(diffs) <= -10: t["cb10"] += 1
                if d4 and min(d4) < 0: t["cb4"] += 1
            if final < 0 and max(diffs) >= 7: t["blown"] += 1
    for t in T.values():
        for x in t["q"].values():
            n = max(t["g"], 1); x["f"] = round(x["f"] / n, 2); x["a"] = round(x["a"] / n, 2); x["m"] = round(x["f"] - x["a"], 2); x["w"] = round(x["w"] / n, 3)
    return T

# ---------------- SU / ATS / O-U with situational splits (schedules) ----------------
SPL = ["all", "home", "away", "fav", "dog", "div", "nondiv", "after_loss", "after_win", "rest_adv", "rest_dis", "short_rest", "off_bye"]
def rblank(): return {"su": [0, 0, 0], "ats": [0, 0, 0], "ou": [0, 0, 0], "mov": 0.0, "n": 0}
def sched(rows, yr):
    T = collections.defaultdict(lambda: {k: rblank() for k in SPL}); last = {}; recent = collections.defaultdict(list)
    G = sorted([r for r in rows if r["season"] == str(yr) and r["home_score"] not in ("", "NA")], key=lambda r: (r["gameday"], r["gametime"]))
    for r in G:
        hs, as_ = int(r["home_score"]), int(r["away_score"])
        sp = float(r["spread_line"]) if r["spread_line"] not in ("", "NA") else None   # + = home favored
        tl = float(r["total_line"]) if r["total_line"] not in ("", "NA") else None
        for side in ("home", "away"):
            t, o = (tm(r["home_team"]), tm(r["away_team"])) if side == "home" else (tm(r["away_team"]), tm(r["home_team"]))
            pf, pa = (hs, as_) if side == "home" else (as_, hs)
            line = (sp if side == "home" else -sp) if sp is not None else None   # points this team is favored by
            rest, orest = (int(r["home_rest"] or 7), int(r["away_rest"] or 7)) if side == "home" else (int(r["away_rest"] or 7), int(r["home_rest"] or 7))
            keys = ["all", side]
            if line is not None and line != 0: keys.append("fav" if line > 0 else "dog")
            keys.append("div" if r["div_game"] == "1" else "nondiv")
            if t in last: keys.append("after_loss" if last[t] < 0 else "after_win" if last[t] > 0 else "after_tie")
            if rest > orest: keys.append("rest_adv")
            elif rest < orest: keys.append("rest_dis")
            if rest <= 5: keys.append("short_rest")
            if rest >= 13 and r["week"] != "1": keys.append("off_bye")
            m = pf - pa
            for k in keys:
                if k not in SPL: continue
                x = T[t][k]; x["n"] += 1; x["mov"] += m
                x["su"][0 if m > 0 else 1 if m < 0 else 2] += 1
                if line is not None:
                    c = m - line; x["ats"][0 if c > 0 else 1 if c < 0 else 2] += 1
                if tl is not None:
                    tt = pf + pa; x["ou"][0 if tt > tl else 1 if tt < tl else 2] += 1
            last[t] = m
            recent[t].append({"wk": int(r["week"]), "opp": o, "ha": "vs" if side == "home" else "@", "pf": pf, "pa": pa, "line": line, "tl": tl,
                              "ats": None if line is None else ("W" if m - line > 0 else "L" if m - line < 0 else "P"),
                              "ou": None if tl is None else ("O" if pf + pa > tl else "U" if pf + pa < tl else "P")})
    for t in T.values():
        for x in t.values(): x["mov"] = round(x["mov"] / x["n"], 1) if x["n"] else None
    return T, recent

def upcoming(rows, yr):
    today = datetime.date.today().isoformat(); out = []
    for r in rows:
        if r["season"] != str(yr) or r["home_score"] not in ("", "NA") or r["gameday"] < today: continue
        if (datetime.date.fromisoformat(r["gameday"]) - datetime.date.today()).days > 7: continue
        sp = float(r["spread_line"]) if r["spread_line"] not in ("", "NA") else None
        out.append({"week": int(r["week"]), "day": r["gameday"], "time": r["gametime"], "home": tm(r["home_team"]), "away": tm(r["away_team"]),
                    "spread_home": sp, "total": float(r["total_line"]) if r["total_line"] not in ("", "NA") else None, "div": r["div_game"] == "1",
                    "home_rest": int(r["home_rest"] or 7), "away_rest": int(r["away_rest"] or 7), "espn": r["espn"]})
    return sorted(out, key=lambda g: (g["day"], g["time"]))

def main():
    s = season_now()
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "seasons": [], "teams": {}, "records": {}, "recent": {}, "upcoming": [],
           "splits": SPL, "src": "nflverse public schedules (closing spread/total) + play-by-play"}
    rows = list(csv.DictReader(io.TextIOWrapper(io.BytesIO(get(SCHED)), encoding="utf-8")))
    for yr in (s - 2, s - 1, s):
        try:
            R, rec = sched(rows, yr)
            for t, v in R.items(): out["records"].setdefault(t, {})[str(yr)] = v
            if yr == s: out["recent"] = {t: v[-6:] for t, v in rec.items()}
        except Exception as e: print("sched skip", yr, e)
        try: T = q_stats(pbp_games(yr))
        except Exception as e: print("pbp skip", yr, e); T = {}
        if T or yr == s: out["seasons"].append(str(yr))
        for t, v in T.items(): out["teams"].setdefault(t, {})[str(yr)] = v
    out["upcoming"] = upcoming(rows, s)
    json.dump(out, open("data/trends.json", "w"), separators=(",", ":")); print(out["seasons"], len(out["records"]), len(out["upcoming"]))
if __name__ == "__main__": main()
