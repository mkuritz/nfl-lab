"""Precompute NFL Hub advanced analytics (display only).

Builds data/advanced.json from:
  - nflverse play-by-play parquet (when present under SL_RAW), else data/pbp_v2.json
  - data/players/*.json (target share, air yards, snaps, RZ)
  - data/trends.json upcoming (rest days) + data/stadiums.json (coords)

Never feeds models, weights, or Highlighted plays. Source names stay off public pages
(srcscrub runs on data/). Provenance for stadiums is noted inside stadiums.json only.
"""
from __future__ import annotations
import os, json, math, glob, datetime as dt
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("SL_RAW", "/tmp/nflraw")
OUT = os.path.join(ROOT, "data", "advanced.json")
SEASON = 2026
MIN_PLAYS = 40          # hide team window charts below this
MIN_PASS = 15
MIN_RUSH = 12
MIN_PLAYER_G = 2        # hide player metric if fewer games in window


def V(t):
    t = str(t or "").upper()
    return {"LA": "LAR", "WAS": "WSH"}.get(t, t)


def K(t):
    t = str(t or "").upper()
    return {"LAR": "LA", "WSH": "WAS"}.get(t, t)


def haversine_mi(lat1, lon1, lat2, lon2):
    R = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * R * math.asin(math.sqrt(a)), 1)


def tz_offset_hours(tz_name, when):
    try:
        from zoneinfo import ZoneInfo
        z = ZoneInfo(tz_name)
        # std offset at that instant
        return z.utcoffset(when).total_seconds() / 3600.0
    except Exception:
        return None


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def week_agg(plays):
    """Aggregate a list of play dicts into offense/defense rates."""
    if not plays:
        return None
    n = len(plays)
    epa = sum(p["epa"] for p in plays)
    suc = sum(p["suc"] for p in plays)
    pas = [p for p in plays if p["ispass"]]
    run = [p for p in plays if not p["ispass"]]
    early = [p for p in plays if p["down"] in (1, 2)]
    early_pass = [p for p in early if p["ispass"]]
    rz = [p for p in plays if p["rz"]]
    rz_td = sum(1 for p in rz if p.get("td"))
    # RZ efficiency: TD rate on RZ plays (proxy); also success rate
    o = {
        "n": n,
        "epa": round(epa / n, 4) if n else None,
        "suc": round(suc / n, 4) if n else None,
        "pass_rate": round(len(pas) / n, 4) if n else None,
        "early_pass_rate": round(len(early_pass) / len(early), 4) if len(early) >= 8 else None,
        "pepa": round(sum(p["epa"] for p in pas) / len(pas), 4) if pas else None,
        "repa": round(sum(p["epa"] for p in run) / len(run), 4) if run else None,
        "psuc": round(sum(p["suc"] for p in pas) / len(pas), 4) if pas else None,
        "rsuc": round(sum(p["suc"] for p in run) / len(run), 4) if run else None,
        "pn": len(pas), "rn": len(run),
        "skr": round(sum(p["sack"] for p in pas) / len(pas), 4) if pas else None,
        "qhr": round(sum(p["qh"] for p in pas) / len(pas), 4) if pas else None,
        "rz_n": len(rz),
        "rz_td_rate": round(rz_td / len(rz), 4) if len(rz) >= 4 else None,
        "rz_suc": round(sum(p["suc"] for p in rz) / len(rz), 4) if len(rz) >= 4 else None,
    }
    return o


def build_from_parquet():
    import pandas as pd
    path = os.path.join(RAW, f"pbp_{SEASON}.parquet")
    if not os.path.exists(path):
        return None
    cols = ["season_type", "week", "posteam", "defteam", "play_type", "epa", "success",
            "down", "yardline_100", "sack", "qb_hit", "pass_touchdown", "rush_touchdown",
            "touchdown"]
    d = pd.read_parquet(path)
    if "season_type" in d.columns:
        d = d[d.season_type == "REG"]
    sc = d[d.play_type.isin(["pass", "run"]) & d.epa.notna() & d.posteam.notna()].copy()
    sc["ispass"] = (sc.play_type == "pass").astype(int)
    sc["suc"] = sc.success.fillna(0).astype(float)
    sc["sack"] = sc.sack.fillna(0).astype(int) if "sack" in sc.columns else 0
    sc["qh"] = sc.qb_hit.fillna(0).astype(int) if "qb_hit" in sc.columns else 0
    sc["rz"] = (sc.yardline_100 <= 20).astype(int) if "yardline_100" in sc.columns else 0
    if "touchdown" in sc.columns:
        sc["td"] = sc.touchdown.fillna(0).astype(int)
    else:
        sc["td"] = ((sc.get("pass_touchdown", 0).fillna(0) if "pass_touchdown" in sc.columns else 0)
                    + (sc.get("rush_touchdown", 0).fillna(0) if "rush_touchdown" in sc.columns else 0)).astype(int)

    # per team-week offense and defense play lists
    off = defaultdict(list)  # (team, week) -> plays
    deff = defaultdict(list)
    for r in sc.itertuples(index=False):
        p = {
            "epa": float(r.epa), "suc": float(r.suc), "ispass": int(r.ispass),
            "down": int(r.down) if pd.notna(r.down) else None,
            "rz": int(r.rz), "sack": int(r.sack), "qh": int(r.qh), "td": int(r.td),
        }
        t, w = str(r.posteam), int(r.week)
        off[(t, w)].append(p)
        dtm = str(r.defteam) if pd.notna(r.defteam) else None
        if dtm:
            deff[(dtm, w)].append(p)

    teams = sorted({V(t) for (t, _) in off})
    by_team = {}
    for t0 in teams:
        # collect weeks for both K and V forms
        weeks = sorted({w for (t, w) in off if V(t) == t0})
        week_rows = []
        for w in weeks:
            # prefer posteam key as stored (BAL not LAR quirk)
            op, dp = [], []
            for t in {t0, K(t0), V(t0)}:
                op = off.get((t, w)) or off.get((K(t), w)) or op
                dp = deff.get((t, w)) or deff.get((K(t), w)) or dp
            # try raw keys from parquet (LA/WAS style)
            for raw_t in list({t0, K(t0), V(t0)}):
                if (raw_t, w) in off:
                    op = off[(raw_t, w)]
                if (raw_t, w) in deff:
                    dp = deff[(raw_t, w)]
            # also try all keys matching V
            if not op:
                for (tt, ww), plays in off.items():
                    if ww == w and V(tt) == t0:
                        op = plays; break
            if not dp:
                for (tt, ww), plays in deff.items():
                    if ww == w and V(tt) == t0:
                        dp = plays; break
            oa, da = week_agg(op), week_agg(dp)
            if not oa:
                continue
            week_rows.append({"wk": w, "off": oa, "def": da})
        by_team[t0] = week_rows
    return by_team


def build_from_pbp_v2():
    """Fallback without early-down / RZ (those need parquet)."""
    pb = load_json(os.path.join(ROOT, "data", "pbp_v2.json"), {})
    tw = (pb.get("tw") or {}).get(str(SEASON)) or (pb.get("tw") or {}).get(SEASON) or {}
    by = defaultdict(list)
    for key, v in tw.items():
        t, w = key.split("|")
        w = int(w)
        n = v.get("n") or 0
        pn = v.get("pn") or 0
        rn = v.get("rn") or 0
        dn = v.get("dn") or 0
        dpn = v.get("dpn") or 0
        drn = v.get("drn") or 0
        off = {
            "n": n,
            "epa": round(v["epa"] / n, 4) if n else None,
            "suc": round(v["suc"] / n, 4) if n else None,
            "pass_rate": round(pn / n, 4) if n else None,
            "early_pass_rate": None,
            "pepa": round(v["pepa"] / pn, 4) if pn else None,
            "repa": round(v["repa"] / rn, 4) if rn else None,
            "psuc": round(v["psuc"] / pn, 4) if pn else None,
            "rsuc": round(v["rsuc"] / rn, 4) if rn else None,
            "pn": pn, "rn": rn,
            "skr": round(v.get("sk", 0) / pn, 4) if pn else None,
            "qhr": round(v.get("qh", 0) / pn, 4) if pn else None,
            "rz_n": None, "rz_td_rate": None, "rz_suc": None,
        }
        de = None
        if dn:
            de = {
                "n": dn,
                "epa": round(v["depa"] / dn, 4),
                "suc": round(v["dsuc"] / dn, 4),
                "pass_rate": round(dpn / dn, 4) if dn else None,
                "early_pass_rate": None,
                "pepa": round(v["dpepa"] / dpn, 4) if dpn else None,
                "repa": round(v["drepa"] / drn, 4) if drn else None,
                "psuc": None, "rsuc": None,
                "pn": dpn, "rn": drn,
                "skr": round(v.get("dsk", 0) / dpn, 4) if dpn else None,
                "qhr": round(v.get("dqh", 0) / dpn, 4) if dpn else None,
                "rz_n": None, "rz_td_rate": None, "rz_suc": None,
            }
        by[V(t)].append({"wk": w, "off": off, "def": de, "opp": V(v.get("opp")) if v.get("opp") else None})
    for t in by:
        by[t].sort(key=lambda r: r["wk"])
    return dict(by)


def window_agg(weeks, side, last_n=None):
    rows = weeks if last_n is None else weeks[-last_n:]
    plays = []
    # re-aggregate from per-week rates weighted by n
    tot_n = 0
    acc = defaultdict(float)
    counts = defaultdict(int)
    keys_rate = ["epa", "suc", "pass_rate", "early_pass_rate", "pepa", "repa", "psuc", "rsuc", "skr", "qhr", "rz_td_rate", "rz_suc"]
    weight_map = {
        "epa": "n", "suc": "n", "pass_rate": "n", "early_pass_rate": "n",
        "pepa": "pn", "psuc": "pn", "skr": "pn", "qhr": "pn",
        "repa": "rn", "rsuc": "rn",
        "rz_td_rate": "rz_n", "rz_suc": "rz_n",
    }
    for r in rows:
        s = r.get(side)
        if not s or not s.get("n"):
            continue
        for k in keys_rate:
            wkey = weight_map[k]
            w = s.get(wkey)
            if s.get(k) is None or not w:
                continue
            acc[k] += s[k] * w
            counts[k] += w
        tot_n += s["n"]
        acc["pn"] += s.get("pn") or 0
        acc["rn"] += s.get("rn") or 0
        acc["rz_n"] += s.get("rz_n") or 0
    if tot_n < (MIN_PLAYS if last_n != 3 else 25):
        return None
    out = {"n": tot_n, "g": len(rows), "pn": int(acc["pn"]), "rn": int(acc["rn"]), "rz_n": int(acc["rz_n"])}
    for k in keys_rate:
        out[k] = round(acc[k] / counts[k], 4) if counts[k] else None
    # hide thin rate metrics
    if out.get("pn", 0) < MIN_PASS:
        out["pepa"] = out["psuc"] = out["skr"] = out["qhr"] = None
    if out.get("rn", 0) < MIN_RUSH:
        out["repa"] = out["rsuc"] = None
    if out.get("rz_n", 0) < 4:
        out["rz_td_rate"] = out["rz_suc"] = None
    return out


def league_avgs(team_windows, key_side_window):
    # key_side_window like ('off','season')
    side, win = key_side_window
    vals = defaultdict(list)
    for t, tw in team_windows.items():
        wmap = tw.get(win) or {}
        s = wmap.get(side)
        if not s:
            continue
        for k, v in s.items():
            if isinstance(v, (int, float)) and k not in ("n", "g", "pn", "rn", "rz_n") and v is not None:
                vals[k].append(v)
    return {k: round(sum(v) / len(v), 4) for k, v in vals.items() if v}


def build_teams(by_week):
    teams = {}
    for t, weeks in by_week.items():
        weeks = sorted(weeks, key=lambda r: r["wk"])
        windows = {}
        for label, n in (("l3", 3), ("l5", 5), ("season", None)):
            if n and len(weeks) < n:
                windows[label] = {"off": None, "def": None}
                continue
            windows[label] = {
                "off": window_agg(weeks, "off", n),
                "def": window_agg(weeks, "def", n),
            }
        # weekly series for charts (offense epa/suc)
        series = []
        for r in weeks:
            o, d = r.get("off") or {}, r.get("def") or {}
            series.append({
                "wk": r["wk"],
                "opp": r.get("opp"),
                "o_epa": o.get("epa"), "o_suc": o.get("suc"),
                "d_epa": d.get("epa"), "d_suc": d.get("suc"),
                "pass_rate": o.get("pass_rate"),
                "early_pass_rate": o.get("early_pass_rate"),
                "skr": o.get("skr"), "d_skr": d.get("skr"),
                "rz_suc": o.get("rz_suc"),
                "n": o.get("n"), "dn": d.get("n"),
            })
        teams[t] = {"weeks": series, "windows": windows, "g": len(weeks)}
    # league avgs per window/side
    # reshape for helper
    tw_for_lg = {t: v["windows"] for t, v in teams.items()}
    lg = {}
    for win in ("l3", "l5", "season"):
        lg[win] = {
            "off": league_avgs({t: {win: tw_for_lg[t].get(win)} for t in tw_for_lg}, ("off", win)),
            "def": league_avgs({t: {win: tw_for_lg[t].get(win)} for t in tw_for_lg}, ("def", win)),
        }
    return teams, lg


def build_players():
    """Enhanced usage metrics from player profile files."""
    out = {}
    for fp in glob.glob(os.path.join(ROOT, "data", "players", "*.json")):
        p = load_json(fp)
        if not p:
            continue
        pid = str(p.get("id") or os.path.basename(fp).replace(".json", ""))
        pos = p.get("pos") or p.get("grp")
        if pos not in ("QB", "RB", "WR", "TE", "FB"):
            continue
        log = [g for g in (p.get("log") or []) if g.get("s") == SEASON]
        if len(log) < MIN_PLAYER_G:
            continue
        log = sorted(log, key=lambda g: g.get("w") or 0)

        def avg(L, k, scale=1):
            vals = [g[k] * scale for g in L if g.get(k) is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        def sum_(L, k):
            return round(sum(g.get(k) or 0 for g in L), 2)

        def adot(L):
            tg = sum(g.get("targets") or 0 for g in L)
            ay = sum(g.get("receiving_air_yards") or 0 for g in L)
            return round(ay / tg, 2) if tg >= 3 else None

        def pack(L):
            if len(L) < MIN_PLAYER_G:
                return None
            o = {
                "g": len(L),
                "snap": avg(L, "snap"),
                "targets": avg(L, "targets"),
                "target_share": avg(L, "target_share"),
                "air_yards_share": avg(L, "air_yards_share"),
                "adot": adot(L),
                "rz_targets": None,
                "rz_carries": None,
                "rz_touches": avg(L, "rz"),
                "carries": avg(L, "carries"),
            }
            # rz is total touches in zone per game in our logs; keep as rz_touches
            # hide empty
            if o["target_share"] is None and o["targets"] is None and o["carries"] is None and o["snap"] is None:
                return None
            return o

        season = pack(log)
        l3 = pack(log[-3:]) if len(log) >= 3 else None
        l5 = pack(log[-5:]) if len(log) >= 3 else None
        snap_trend = [{"w": g.get("w"), "snap": g.get("snap"), "ts": g.get("target_share"),
                       "ay": g.get("air_yards_share"), "rz": g.get("rz"),
                       "tg": g.get("targets"), "ca": g.get("carries"),
                       "ayds": g.get("receiving_air_yards")} for g in log]
        # hide charts with no series
        out[pid] = {
            "name": p.get("name"), "team": V(p.get("team")), "pos": pos,
            "season": season, "l3": l3, "l5": l5,
            "trend": snap_trend,
        }
    return out


def build_travel():
    stad = load_json(os.path.join(ROOT, "data", "stadiums.json"), {})
    teams = (stad or {}).get("teams") or {}
    tr = load_json(os.path.join(ROOT, "data", "trends.json"), {})
    upcoming = tr.get("upcoming") or []
    # also try games.csv for richer rest if present
    games_rest = {}
    gcp = os.path.join(RAW, "games.csv")
    if os.path.exists(gcp):
        try:
            import pandas as pd
            g = pd.read_csv(gcp)
            g = g[(g.season == SEASON) & (g.game_type == "REG") & g.result.isna()]
            for _, r in g.iterrows():
                key = f"{V(r.away_team)}@{V(r.home_team)}"
                games_rest[key] = {
                    "home_rest": int(r.home_rest) if pd.notna(r.home_rest) else None,
                    "away_rest": int(r.away_rest) if pd.notna(r.away_rest) else None,
                    "day": str(r.gameday),
                    "neutral": str(r.location).lower() == "neutral",
                    "stadium": r.stadium if pd.notna(getattr(r, "stadium", None)) else None,
                }
        except Exception:
            pass

    def stadium_of(t):
        return teams.get(V(t)) or teams.get(K(t))

    out = {}
    now = dt.datetime.now(dt.timezone.utc)
    for g in upcoming:
        home, away = V(g.get("home")), V(g.get("away"))
        key = f"{away}@{home}"
        hs, aws = stadium_of(home), stadium_of(away)
        if not hs or not aws:
            continue
        gr = games_rest.get(key) or {}
        neutral = gr.get("neutral") or False
        # destination = home stadium unless neutral (use home coords as venue proxy)
        dest = hs
        # miles: away travels from their stadium to dest; home travels 0 unless neutral
        away_mi = haversine_mi(aws["lat"], aws["lon"], dest["lat"], dest["lon"])
        home_mi = 0.0 if not neutral else haversine_mi(hs["lat"], hs["lon"], dest["lat"], dest["lon"])
        # time zones crossed (absolute hour offset difference / ~1 zone per hour-ish; report hour delta)
        when = now
        try:
            day = gr.get("day") or g.get("day")
            if day:
                when = dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone.utc)
        except Exception:
            pass
        ho = tz_offset_hours(hs["tz"], when.replace(tzinfo=None) if when.tzinfo else when)
        ao = tz_offset_hours(aws["tz"], when.replace(tzinfo=None) if when.tzinfo else when)
        # For the traveling team, zones crossed = |home_tz - away_tz| in hours (east/west)
        tz_delta = None if ho is None or ao is None else abs(ho - ao)

        home_rest = g.get("home_rest") if g.get("home_rest") is not None else gr.get("home_rest")
        away_rest = g.get("away_rest") if g.get("away_rest") is not None else gr.get("away_rest")

        def reason(side, miles, rest, is_home):
            parts = []
            if miles and miles >= 1:
                parts.append(f"{miles:.0f} miles traveled")
            elif is_home and not neutral:
                parts.append("playing at home (0 miles)")
            if tz_delta is not None and not is_home:
                z = int(round(tz_delta))
                if z >= 1:
                    parts.append(f"{z} time zone{'s' if z != 1 else ''} crossed")
                else:
                    parts.append("same time zone")
            elif is_home and not neutral:
                parts.append("no time-zone change")
            if rest is not None:
                if rest >= 13:
                    parts.append(f"coming off a bye ({rest} days rest)")
                elif rest <= 5:
                    parts.append(f"short week ({rest} days rest)")
                else:
                    parts.append(f"{rest} days rest")
            # display-only score hint for momentum (not written into MW; UI decides)
            pts = 0.0
            if rest is not None:
                if rest >= 13:
                    pts += 1.0
                elif rest <= 5:
                    pts -= 1.0
                elif rest >= 9:
                    pts += 0.3
            if not is_home:
                if miles >= 2000:
                    pts -= 1.0
                elif miles >= 1200:
                    pts -= 0.6
                elif miles >= 600:
                    pts -= 0.3
                if tz_delta is not None and tz_delta >= 2:
                    pts -= 0.4
            else:
                pts += 0.3  # home rest advantage of venue
            label = "Travel & rest"
            return {
                "label": label,
                "detail": " · ".join(parts) if parts else None,
                "miles": miles,
                "rest_days": rest,
                "tz_hours": tz_delta if not is_home else 0.0,
                "home": bool(is_home and not neutral),
                "short_week": bool(rest is not None and rest <= 5),
                "off_bye": bool(rest is not None and rest >= 13),
                "pts": round(pts, 2),
                "stadium": dest.get("stadium"),
                "city": dest.get("city"),
            }

        out[home] = reason(home, home_mi, home_rest, True)
        out[away] = reason(away, away_mi, away_rest, False)
        out[key] = {"home": home, "away": away, "day": g.get("day"), "neutral": neutral}
    return out


def main():
    src = "parquet"
    by = build_from_parquet()
    if not by:
        src = "pbp_v2"
        by = build_from_pbp_v2()
    # attach opp from pbp_v2 when parquet path lacked it
    pb = load_json(os.path.join(ROOT, "data", "pbp_v2.json"), {})
    tw = (pb.get("tw") or {}).get(str(SEASON)) or (pb.get("tw") or {}).get(SEASON) or {}
    for key, v in tw.items():
        t, w = key.split("|")
        t, w = V(t), int(w)
        if t in by:
            for row in by[t]:
                if row["wk"] == w and not row.get("opp") and v.get("opp"):
                    row["opp"] = V(v["opp"])

    teams, lg = build_teams(by)
    players = build_players()
    travel = build_travel()
    # next opponent map for team advanced compare
    tr = load_json(os.path.join(ROOT, "data", "trends.json"), {})
    nxt = {}
    for g in tr.get("upcoming") or []:
        h, a = V(g["home"]), V(g["away"])
        nxt[h] = {"opp": a, "home": True, "day": g.get("day")}
        nxt[a] = {"opp": h, "home": False, "day": g.get("day")}

    out = {
        "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "season": SEASON,
        "display_only": True,
        "teams": teams,
        "league": lg,
        "players": players,
        "travel": travel,
        "next": nxt,
        "min": {"team_plays": MIN_PLAYS, "player_games": MIN_PLAYER_G},
    }
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("advanced.json", "teams", len(teams), "players", len(players), "travel", len([k for k in travel if "@" not in k]), "src", src)


if __name__ == "__main__":
    main()
