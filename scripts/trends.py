"""Comeback and quarter/half trends from nflverse public play-by-play (scores only)."""
import csv, gzip, io, json, urllib.request, datetime, collections
URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.csv.gz"
def season_now():
    t = datetime.date.today(); return t.year if t.month >= 8 else t.year - 1
def games(yr):
    raw = urllib.request.urlopen(urllib.request.Request(URL.format(yr), headers={"User-Agent": "SportsLabs/1.0"}), timeout=180).read()
    G = {}
    for r in csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), encoding="utf-8")):
        try: q = int(float(r["qtr"])); h = int(float(r["total_home_score"])); a = int(float(r["total_away_score"]))
        except (ValueError, KeyError): continue
        g = G.setdefault(r["game_id"], {"home": r["home_team"], "away": r["away_team"], "end": {}, "seq": []})
        g["end"][q] = (h, a); g["seq"].append((q, h - a))
    return G
def blank(): return {"g": 0, "cb": 0, "cb4": 0, "big": 0, "blown": 0, "q": {k: {"f": 0, "a": 0, "w": 0} for k in ["1Q","2Q","3Q","4Q","1H","2H"]}}
def season_stats(G):
    T = collections.defaultdict(blank)
    for g in G.values():
        E = g["end"]
        if 4 not in E: continue
        last = E[max(E)]; prev = (0, 0); per = {}
        for q in (1, 2, 3, 4):
            cur = E.get(q, prev); per[q] = (cur[0] - prev[0], cur[1] - prev[1]); prev = cur
        per["1H"] = (per[1][0] + per[2][0], per[1][1] + per[2][1]); per["2H"] = (last[0] - E[2][0], last[1] - E[2][1]) if 2 in E else (0, 0)
        for side, sgn in (("home", 1), ("away", -1)):
            t = T[g["home"] if side == "home" else g["away"]]; t["g"] += 1
            for k, lab in ((1,"1Q"),(2,"2Q"),(3,"3Q"),(4,"4Q"),("1H","1H"),("2H","2H")):
                f, a = per[k] if sgn == 1 else per[k][::-1]; t["q"][lab]["f"] += f; t["q"][lab]["a"] += a; t["q"][lab]["w"] += f > a
            final = sgn * (last[0] - last[1]); diffs = [sgn * d for _, d in g["seq"]]; d4 = [sgn * d for q, d in g["seq"] if q >= 4]
            if final > 0 and min(diffs) < 0:
                t["cb"] += 1; t["big"] = max(t["big"], -min(diffs))
                if d4 and min(d4) < 0: t["cb4"] += 1
            if final < 0 and max(diffs) >= 7: t["blown"] += 1
    for t in T.values():
        for x in t["q"].values():
            n = max(t["g"], 1); x["f"] = round(x["f"] / n, 2); x["a"] = round(x["a"] / n, 2); x["m"] = round(x["f"] - x["a"], 2); x["w"] = round(x["w"] / n, 3)
    return T
def main():
    s = season_now(); out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "seasons": [], "teams": {}}
    for yr in (s - 2, s - 1, s):
        try: T = season_stats(games(yr))
        except Exception as e: print("skip", yr, e); continue
        out["seasons"].append(str(yr))
        for tm, v in T.items(): out["teams"].setdefault(tm, {})[str(yr)] = v
    json.dump(out, open("data/trends.json", "w"), separators=(",", ":")); print(out["seasons"], len(out["teams"]))
if __name__ == "__main__": main()
