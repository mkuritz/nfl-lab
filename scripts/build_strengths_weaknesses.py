#!/usr/bin/env python3
"""Strengths & Weaknesses field map data (display-only).

Builds data/strengths_weaknesses.json from free public play-by-play and weekly tracking/charting
files (downloaded to $SL_RAW by scripts/v2/fetch_inputs.sh, fetched here if missing). Nothing raw is committed.

Per team, season to date (regular season):
  pass zones  : 3 depths (air yards <10, 10-19, 20+) x 3 directions (left/middle/right, offense's view)
                defense allowed and offense produced: targets, completion %, yards/target, EPA/target
  run lanes   : 7 gaps (L end, L tackle, L guard, middle, R guard, R tackle, R end)
                carries, yards/carry, EPA/carry, 10+ yard run rate; plus 20+ yard runs overall
  pass rush   : pressure rate (pressures / opponent dropbacks), sack rate, QB hit rate
  protection  : pressure-allowed rate, sack rate, QB hits, starting QB average time to throw
EPA figures are shrunk toward the league zone average (k plays of league prior) so thin cells
don't swing wildly; raw counts are kept so the page can label thin or empty cells honestly.
"""
import json, os, subprocess, sys, datetime
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("SL_RAW", "/tmp/nflraw")
OUT = os.path.join(ROOT, "data", "strengths_weaknesses.json")
SEASON = int(os.environ.get("SL_SEASON", "2026"))
REL = "https://github.com/nflverse/nflverse-data/releases/download"
FILES = {
    "pbp": (f"pbp_{SEASON}.parquet", f"{REL}/pbp/play_by_play_{SEASON}.parquet"),
    "ngs": ("ngs_passing.parquet", f"{REL}/nextgen_stats/ngs_passing.parquet"),
    "adef": (f"advstats_def_{SEASON}.parquet", f"{REL}/pfr_advstats/advstats_week_def_{SEASON}.parquet"),
    "apass": (f"advstats_pass_{SEASON}.parquet", f"{REL}/pfr_advstats/advstats_week_pass_{SEASON}.parquet"),
}
FIX = {"LA": "LAR", "WAS": "WSH", "JAC": "JAX", "OAK": "LV", "SD": "LAC", "STL": "LAR"}
K_PASS, K_RUN, THIN = 25, 20, 10
DEPTHS = [("short", "Short", -99, 10), ("inter", "Intermediate", 10, 20), ("deep", "Deep", 20, 999)]
DIRS = ["left", "middle", "right"]
LANES = [("L-end", "left", "end"), ("L-tackle", "left", "tackle"), ("L-guard", "left", "guard"),
         ("mid", "middle", None), ("R-guard", "right", "guard"), ("R-tackle", "right", "tackle"), ("R-end", "right", "end")]


def path(key):
    name, url = FILES[key]
    p = os.path.join(RAW, name)
    alt = os.path.join(RAW, "pbp_%d.parquet" % SEASON) if key == "pbp" else None
    if alt and os.path.exists(alt):
        return alt
    if not os.path.exists(p):
        os.makedirs(RAW, exist_ok=True)
        r = subprocess.run(["curl", "-fsSL", url, "-o", p])
        if r.returncode != 0:
            if os.path.exists(p):
                os.remove(p)
            return None
    return p


def r(x, d=3):
    return None if x is None or pd.isna(x) else round(float(x), d)


def shrink(sum_, n, prior, k):
    return (sum_ + k * prior) / (n + k)


def main():
    pp = path("pbp")
    if not pp:
        sys.exit("play-by-play unavailable; leaving existing file untouched")
    cols = ["season_type", "week", "posteam", "defteam", "play_type", "pass_location", "air_yards", "run_location",
            "run_gap", "yards_gained", "epa", "sack", "qb_hit", "complete_pass", "pass_attempt", "qb_scramble",
            "qb_spike", "qb_kneel", "two_point_attempt"]
    p = pd.read_parquet(pp, columns=cols)
    p = p[(p.season_type == "REG") & p.posteam.notna() & p.defteam.notna() & (p.two_point_attempt != 1)].copy()
    p["posteam"] = p.posteam.replace(FIX); p["defteam"] = p.defteam.replace(FIX)
    week = int(p.week.max())

    tg = p[(p.play_type == "pass") & p.pass_location.notna() & p.air_yards.notna() & (p.sack != 1) & (p.qb_spike != 1)].copy()
    tg["depth"] = pd.cut(tg.air_yards, [-99, 9.5, 19.5, 999], labels=[d[0] for d in DEPTHS]).astype(str)
    tg["zone"] = tg.depth + ":" + tg.pass_location
    ru = p[(p.play_type == "run") & (p.qb_scramble != 1) & (p.qb_kneel != 1) & p.run_location.notna()].copy()
    ru["lane"] = None
    for key, loc, gap in LANES:
        m = (ru.run_location == loc) & ((ru.run_gap == gap) if gap else True)
        ru.loc[m, "lane"] = key
    ru = ru[ru.lane.notna()]
    db = p[((p.pass_attempt == 1) | (p.sack == 1) | (p.qb_scramble == 1)) & (p.qb_spike != 1)]

    # league zone baselines
    lg = {"zones": {}, "lanes": {}}
    for z, g in tg.groupby("zone"):
        lg["zones"][z] = {"n": int(len(g)), "share": r(len(g) / len(tg)), "cmp": r(g.complete_pass.mean()),
                          "ypt": r(g.yards_gained.mean(), 2), "epa": r(g.epa.mean())}
    for l, g in ru.groupby("lane"):
        lg["lanes"][l] = {"n": int(len(g)), "share": r(len(g) / len(ru)), "ypc": r(g.yards_gained.mean(), 2),
                          "epa": r(g.epa.mean()), "x10": r((g.yards_gained >= 10).mean())}

    def zone_block(g_all, team_col, team):
        g = g_all[g_all[team_col] == team]; tot = len(g); out = {}
        for z, base in lg["zones"].items():
            s = g[g.zone == z]; n = len(s)
            out[z] = {"n": n, "share": r(n / tot) if tot else None,
                      "cmp": r(s.complete_pass.mean()) if n else None,
                      "ypt": r(s.yards_gained.mean(), 2) if n else None,
                      "epa": r(shrink(s.epa.sum(), n, base["epa"], K_PASS)),
                      "d": r(shrink(s.epa.sum(), n, base["epa"], K_PASS) - base["epa"])}
        return out, tot

    def lane_block(g_all, team_col, team):
        g = g_all[g_all[team_col] == team]; tot = len(g); out = {}
        for l, base in lg["lanes"].items():
            s = g[g.lane == l]; n = len(s)
            out[l] = {"n": n, "share": r(n / tot) if tot else None,
                      "ypc": r(s.yards_gained.mean(), 2) if n else None,
                      "x10": r((s.yards_gained >= 10).mean()) if n else None,
                      "epa": r(shrink(s.epa.sum(), n, base["epa"], K_RUN)),
                      "d": r(shrink(s.epa.sum(), n, base["epa"], K_RUN) - base["epa"])}
        return out, tot, int((g.yards_gained >= 20).sum()), r((g.yards_gained >= 10).mean()) if tot else None

    # pass rush / protection (charting through its latest week; denominators use the same weeks)
    rush = {}
    ad, ap = path("adef"), path("apass")
    adv_week = None
    if ad and ap:
        a = pd.read_parquet(ad); b = pd.read_parquet(ap)
        a = a[(a.season == SEASON) & (a.game_type == "REG")]; b = b[(b.season == SEASON) & (b.game_type == "REG")]
        a["team"] = a.team.replace(FIX); b["team"] = b.team.replace(FIX)
        adv_week = int(min(a.week.max(), b.week.max()))
        dbw = db[db.week <= adv_week]
        prs = a[a.week <= adv_week].groupby("team").def_pressures.sum()
        pal = b[b.week <= adv_week].groupby("team").times_pressured.sum()
        dd = dbw.groupby("defteam").size(); od = dbw.groupby("posteam").size()
        for t in set(dd.index) | set(od.index):
            rush[t] = {"prs_gen": r(prs.get(t, 0) / dd[t]) if t in dd and t in prs else None,
                       "prs_alw": r(pal.get(t, 0) / od[t]) if t in od and t in pal else None}
    ttt = {}
    npth = path("ngs")
    if npth:
        n = pd.read_parquet(npth); n = n[(n.season == SEASON) & (n.season_type == "REG") & (n.week > 0)]
        n["team_abbr"] = n.team_abbr.replace(FIX)
        for t, g in n.groupby("team_abbr"):
            recent = g[g.week > g.week.max() - 3]  # QB with most attempts over the team's last 3 charted weeks
            q = recent.groupby("player_display_name").attempts.sum().idxmax()
            gq = g[g.player_display_name == q]
            ttt[t] = {"qb": q, "ttt": r((gq.avg_time_to_throw * gq.attempts).sum() / gq.attempts.sum(), 2),
                      "team_ttt": r((g.avg_time_to_throw * g.attempts).sum() / g.attempts.sum(), 2)}

    teams = {}
    for t in sorted(set(p.posteam) | set(p.defteam)):
        dz, dn = zone_block(tg, "defteam", t); oz, on = zone_block(tg, "posteam", t)
        dl, dr, d20, d10 = lane_block(ru, "defteam", t); ol, orr, o20, o10 = lane_block(ru, "posteam", t)
        ddb = db[db.defteam == t]; odb = db[db.posteam == t]
        gp_d = p[p.defteam == t].week.nunique(); gp_o = p[p.posteam == t].week.nunique()
        teams[t] = {
            "games": int(max(gp_d, gp_o)),
            "def": {"targets": dn, "zones": dz, "carries": dr, "lanes": dl, "runs20": d20, "x10": d10,
                    "sack": r(ddb.sack.mean()), "hit": r(ddb.qb_hit.mean()), "dropbacks": int(len(ddb)),
                    "prs": (rush.get(t) or {}).get("prs_gen")},
            "off": {"targets": on, "zones": oz, "carries": orr, "lanes": ol, "runs20": o20, "x10": o10,
                    "sack": r(odb.sack.mean()), "hit": r(odb.qb_hit.mean()), "dropbacks": int(len(odb)),
                    "prs": (rush.get(t) or {}).get("prs_alw"), **(ttt.get(t) or {})},
        }
    # league rates for the pass-rush strip
    vals = lambda side, k: [v[side][k] for v in teams.values() if v[side].get(k) is not None]
    lg["rush"] = {k: r(sum(vals(s, k)) / len(vals(s, k))) if vals(s, k) else None
                  for s, k in [("def", "prs"), ("def", "sack"), ("def", "hit")]}
    lg["ttt"] = r(sum(vals("off", "ttt")) / len(vals("off", "ttt")), 2) if vals("off", "ttt") else None
    lg["runs20_pg"] = r(sum(v["def"]["runs20"] for v in teams.values()) / sum(v["games"] for v in teams.values()), 2)

    out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "season": SEASON, "through_week": week,
           "rush_through_week": adv_week, "k": {"pass": K_PASS, "run": K_RUN, "thin": THIN},
           "depths": [[a, b] for a, b, *_ in DEPTHS], "dirs": DIRS, "lanes": [l[0] for l in LANES],
           "league": lg, "teams": teams}
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    os.replace(tmp, OUT)
    print("strengths_weaknesses: %d teams, through week %d, rush through %s, %d KB" % (len(teams), week, adv_week, os.path.getsize(OUT) // 1024))


if __name__ == "__main__":
    main()
