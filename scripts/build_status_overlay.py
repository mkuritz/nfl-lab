#!/usr/bin/env python3
"""Build data/status_overlay.json for NFL Hub trending-out / Watch labels (display only).

Sources (no hand-stamped values):
  1) Bet Lab early_injury_adjust.json (likely_out + prop_freerolls status strings)
  2) Bet Lab / local nfl_unconfirmed_reports.jsonl when available (confirmed Out overrides)
  3) nfl-lab data/players/*.json and data/v2.json inj (official designations)

Rules:
  - Confirmed Out / official Out|IR|Doubtful|Suspension clears unconfirmed trending tags
  - Deshaun Watson is never labeled confirmed Out unless the official hub status is Out
  - Public notes are scrubbed of reporter / outlet attributions via srcscrub when present
  - Each row carries as_of + expires (6h) for the client staleness guard

Does not change pick logic, model weights, or probabilities.
"""
from __future__ import annotations

import json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BL = os.environ.get("BETLAB_DATA", "https://betlab.sportslabshq.com/data").rstrip("/")
LOCAL_BL = Path(os.environ.get("BETLAB_ENGINE_DATA", "/workspace/bet-lab-engine/data"))
TTL_H = 6

# Optional name→aid map when EIA has no aid
EXTRA_AID = {
    "mike evans": "16737",
    "deebo samuel sr.": "3126486",
    "deebo samuel": "3126486",
    "kyler murray": "3917315",
    "garrett wilson": "4569618",
    "brian robinson": "4241474",
    "brian robinson jr.": "4241474",
    "deshaun watson": "3122840",
}

OFFICIAL = re.compile(r"^(Out|Injured Reserve|Doubtful|Suspension|Suspended|Physically Unable|Non-Football|Reserve/)", re.I)


def now_utc():
    return datetime.now(timezone.utc)


def parse_ts(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M%z", "%Y-%m-%dT%H:%M-%z"):
        try:
            if fmt.endswith("%z") and re.search(r"[+-]\d{2}:\d{2}$", s):
                s2 = s[:-3] + s[-2:] if s[-3] == ":" else s
                return datetime.strptime(s2, "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc)
            if fmt.endswith("Z"):
                return datetime.strptime(s.replace("Z", ""), fmt.replace("Z", "")).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    # EIA style 2026-11-05T14:08-05:00
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})([+-]\d{2}):?(\d{2})$", s)
    if m:
        try:
            return datetime.strptime(m.group(1) + m.group(2) + m.group(3), "%Y-%m-%dT%H:%M%z").astimezone(timezone.utc)
        except Exception:
            pass
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})([+-]\d{2}):?(\d{2})", s)
    if m:
        try:
            return datetime.strptime(m.group(1) + m.group(2) + m.group(3), "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def get_json(url_or_path):
    p = Path(str(url_or_path))
    if p.exists():
        return json.loads(p.read_text())
    if str(url_or_path).startswith("http"):
        req = urllib.request.Request(url_or_path, headers={"User-Agent": "SportsLabs-NFLHub/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    raise FileNotFoundError(url_or_path)


def get_text(url_or_path):
    p = Path(str(url_or_path))
    if p.exists():
        return p.read_text()
    if str(url_or_path).startswith("http"):
        req = urllib.request.Request(url_or_path, headers={"User-Agent": "SportsLabs-NFLHub/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode()
    raise FileNotFoundError(url_or_path)


def scrub(note: str) -> str:
    if not note:
        return ""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import srcscrub
        return srcscrub.s_(note) if hasattr(srcscrub, "s_") else note
    except Exception:
        # light fallback: strip "per reports." is fine; strip "NFL reporter"
        note = re.sub(r"\bNFL reporter,?\s*", "", note, flags=re.I)
        note = re.sub(r",?\s*per [A-Z][A-Za-z.\- ]{2,40}\b", ", per reports", note)
        return note


def nm(s):
    return re.sub(r"\s+", " ", (s or "").lower().replace(".", "")).strip()


def load_aid_index():
    by_name = {}
    pindex = DATA / "pindex.json"
    if pindex.exists():
        for row in (json.loads(pindex.read_text()).get("p") or []):
            if len(row) >= 2:
                by_name[nm(row[1])] = str(row[0])
    for k, v in EXTRA_AID.items():
        by_name.setdefault(k, v)
    return by_name


def aid_for(name, by_name):
    n = nm(name)
    if n in by_name:
        return by_name[n]
    n2 = re.sub(r"\s+jr$", "", n).strip()
    return by_name.get(n2) or by_name.get(n2 + " jr") or EXTRA_AID.get(n) or EXTRA_AID.get(n2)


def load_reports():
    """Latest report per player from jsonl. Prefer the newest readable local file; else published URL."""
    cands = []
    for c in (
        LOCAL_BL / "nfl_unconfirmed_reports.jsonl",
        Path(os.environ["BETLAB_DATA_DIR"]) / "nfl_unconfirmed_reports.jsonl" if os.environ.get("BETLAB_DATA_DIR") else None,
        Path(os.environ["BETLAB_ENGINE_DATA"]) / "nfl_unconfirmed_reports.jsonl" if os.environ.get("BETLAB_ENGINE_DATA") else None,
    ):
        if c:
            cands.append(c)
    cands.extend(Path("/workspace/wt").glob("ble-*/data/nfl_unconfirmed_reports.jsonl"))
    # newest local first
    local = [c for c in cands if isinstance(c, Path) and c.exists()]
    local.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    ordered = local + [f"{BL}/nfl_unconfirmed_reports.jsonl"]
    for c in ordered:
        try:
            text = get_text(c)
        except Exception:
            continue
        if not text or "<html" in text[:200].lower():
            continue
        tmp, n = {}, 0
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            player = o.get("player") or ""
            if not player:
                continue
            tmp[player] = o
            n += 1
        if n:
            return tmp, str(c)
    return {}, None


def parse_eia_status(status: str):
    """Return (base_status, tags, watch, unconfirmed) from EIA status string."""
    st = (status or "").strip()
    low = st.lower()
    tags = []
    watch = False
    unconfirmed = "unconfirmed" in low
    base = st.split("·")[0].strip() if "·" in st else st
    if "trending out" in low:
        tags.append("trending out (unconfirmed)")
        unconfirmed = True
    if re.search(r"\bwatch\b", low):
        tags.append("Watch")
        watch = True
        unconfirmed = unconfirmed or "unconfirmed" in low
    if not base:
        base = "Questionable"
    return base, tags, watch, unconfirmed



WATCH_NOTE = re.compile(
    r"concussion|sidelined from practice|missed (?:thursday|wednesday|friday) practice|"
    r"wasn'?t seen at .*practice|dnp|non-participant|limited thursday|limited wednesday|"
    r"protocol",
    re.I,
)


def infer_watch_from_note(base, tags, watch, unconfirmed, note):
    """Promote plain Questionable EIA rows to Watch when the note is a live availability watch."""
    if watch or OFFICIAL.match(base or ""):
        return base, tags, watch, unconfirmed
    if not re.match(r"^Questionable", base or "", re.I):
        return base, tags, watch, unconfirmed
    if note and WATCH_NOTE.search(note):
        tags = list(dict.fromkeys((tags or []) + ["Watch"]))
        return base, tags, True, unconfirmed
    return base, tags, watch, unconfirmed


def load_prior_overlay():
    """Carry forward non-expired Watch / trending tags from the last committed overlay (CI has no private reports)."""
    fp = DATA / "status_overlay.json"
    if not fp.exists():
        return {}
    try:
        prior = json.loads(fp.read_text())
    except Exception:
        return {}
    nnow = now_utc()
    out = {}
    for row in prior.get("players") or []:
        exp = parse_ts(row.get("expires"))
        if exp and exp < nnow:
            continue
        as_of = parse_ts(row.get("as_of"))
        if as_of and nnow - as_of > timedelta(hours=TTL_H):
            continue
        tags = row.get("tags") or []
        if not tags and not row.get("watch") and not row.get("confirmed"):
            continue
        aid = row.get("aid")
        key = aid or nm(row.get("player"))
        if not key:
            continue
        out[key] = row
    return out


def load_hub_status(by_name):
    """Official hub statuses from player files + v2.inj."""
    out = {}
    # v2.inj
    v2p = DATA / "v2.json"
    if v2p.exists():
        v2 = json.loads(v2p.read_text())
        for team, rows in (v2.get("inj") or {}).items():
            for r in rows:
                aid = str(r.get("id") or "") or aid_for(r.get("n"), by_name)
                if not aid:
                    continue
                out[aid] = {
                    "aid": aid,
                    "player": r.get("n"),
                    "team": team,
                    "status": r.get("st") or "Active",
                    "detail": r.get("d") or "",
                    "as_of": parse_ts(r.get("dt")),
                    "src": "v2.inj",
                }
    # player files override / enrich
    pdir = DATA / "players"
    if pdir.exists():
        for fp in pdir.glob("*.json"):
            try:
                p = json.loads(fp.read_text())
            except Exception:
                continue
            inj = p.get("inj") or {}
            st = inj.get("status")
            if not st or st == "Active":
                continue
            aid = str(p.get("id") or fp.stem)
            cur = out.get(aid) or {"aid": aid, "player": p.get("name"), "team": p.get("team")}
            cur.update({
                "player": p.get("name") or cur.get("player"),
                "team": p.get("team") or cur.get("team"),
                "status": st,
                "detail": inj.get("detail") or cur.get("detail") or "",
                "note": inj.get("note") or "",
                "as_of": parse_ts(inj.get("date")) or cur.get("as_of"),
                "season": bool(inj.get("season")),
                "src": "player",
            })
            out[aid] = cur
    return out


def upsert(by, aid, player, team, **kw):
    if not aid and not player:
        return
    key = aid or nm(player)
    cur = by.get(key) or {"aid": aid, "player": player, "team": team}
    if player:
        cur["player"] = player
    if team:
        cur["team"] = team
    if aid:
        cur["aid"] = aid
    for k, v in kw.items():
        if v is not None:
            cur[k] = v
    by[key] = cur


def main():
    by_name = load_aid_index()
    by = {}
    sources_used = []

    # 1) early_injury_adjust
    eia = None
    eia_as_of = None
    for c in (f"{BL}/early_injury_adjust.json", LOCAL_BL / "early_injury_adjust.json", DATA / "early_injury_adjust.json"):
        try:
            eia = get_json(c)
            sources_used.append(f"early_injury:{c}")
            break
        except Exception:
            continue
    if eia:
        eia_as_of = parse_ts(eia.get("updated") or eia.get("as_of"))
        for section in ("likely_out", "prop_freerolls", "line_opportunities"):
            for r in eia.get(section) or []:
                player = r.get("player") or r.get("name")
                if not player:
                    continue
                aid = str(r.get("aid") or "") or aid_for(player, by_name)
                base, tags, watch, unconfirmed = parse_eia_status(r.get("status") or "")
                # line_opportunities may be watch-only without status chrome
                if section == "line_opportunities" and not tags:
                    # only if explicitly a watch action
                    act = (r.get("action") or r.get("action_type") or "")
                    if re.search(r"\bwatch\b", act, re.I) or r.get("watch"):
                        tags, watch = ["Watch"], True
                        base = base or "Questionable"
                    else:
                        continue
                note = scrub((r.get("note") or r.get("public_note") or "")[:280])
                base, tags, watch, unconfirmed = infer_watch_from_note(base, tags, watch, unconfirmed, note)
                if not tags and not unconfirmed and not watch:
                    # plain Questionable with no extra chrome — skip (hub already shows status)
                    continue
                as_of = parse_ts(r.get("status_ts") or r.get("updated")) or eia_as_of
                p_inactive = r.get("p_inactive")
                if p_inactive is None:
                    p_inactive = (r.get("probabilities") or {}).get("p_void")
                # When the reports jsonl isn't published yet, elevate clear "won't play" likely-out
                # notes with very high inactive chance to confirmed Out (display only). Never for Watson.
                elev = (
                    "watson" not in nm(player)
                    and p_inactive is not None and float(p_inactive) >= 0.9
                    and re.search(r"\b(confirmed out|won'?t play|will not play|ruled out)\b", note or "", re.I)
                )
                if elev:
                    base, tags, watch, unconfirmed = "Out", [], False, False
                    upsert(by, aid, player, r.get("team"), status=base, tags=tags, watch=watch,
                           unconfirmed=False, confirmed=True, p_inactive=p_inactive,
                           note=note, as_of=as_of, source="early_injury_confirmed")
                else:
                    upsert(by, aid, player, r.get("team"),
                           status=base, tags=tags, watch=watch, unconfirmed=unconfirmed,
                           p_inactive=p_inactive, note=note, as_of=as_of, source="early_injury")

    # 2) unconfirmed reports (confirmed Out overrides)
    reports, rsrc = load_reports()
    if rsrc:
        sources_used.append(f"reports:{rsrc}")
    for player, r in reports.items():
        aid = aid_for(player, by_name)
        trend = (r.get("trend") or "").lower()
        confirmed = bool(r.get("confirmed"))
        as_of = parse_ts(r.get("logged_et") or r.get("logged"))
        note = scrub((r.get("public_note") or "")[:280])
        team = r.get("team")
        if confirmed and trend in ("out", "doubtful"):
            st = "Out" if trend == "out" else "Doubtful"
            # Watson guard: never force confirmed Out from a report alone if name is Watson unless trend out+confirmed is intentional —
            # task: Watson should show Q/watch never confirmed out until official. So skip forcing Out for Watson from reports.
            if "watson" in nm(player) and st == "Out":
                upsert(by, aid, player, team, status="Questionable", tags=["Watch"], watch=True,
                       unconfirmed=True, confirmed=False, note=note, as_of=as_of, source="report_watch")
                continue
            upsert(by, aid, player, team, status=st, tags=[], watch=False, unconfirmed=False,
                   confirmed=True, note=note, as_of=as_of, source="confirmed_report")
            continue
        if trend == "trending_out":
            # don't overwrite a confirmed Out already set
            key = aid or nm(player)
            prev = by.get(key) or {}
            if prev.get("confirmed") and prev.get("status") == "Out":
                continue
            upsert(by, aid, player, team, status="Questionable",
                   tags=["trending out (unconfirmed)"], watch=False, unconfirmed=True,
                   confirmed=False, note=note, as_of=as_of, source="report")
        elif trend == "watch":
            key = aid or nm(player)
            prev = by.get(key) or {}
            if prev.get("confirmed") and prev.get("status") == "Out":
                continue
            tags = list(dict.fromkeys((prev.get("tags") or []) + ["Watch"]))
            upsert(by, aid, player, team, status=prev.get("status") or "Questionable",
                   tags=tags, watch=True, unconfirmed=not confirmed, confirmed=False,
                   note=note or prev.get("note"), as_of=as_of or prev.get("as_of"), source="report")
        elif trend == "trending_in" and confirmed:
            # Confirmed Active / upgrade: drop Watch and trending-out chrome (display only).
            key = aid or nm(player)
            upsert(by, aid, player, team, status="Active", tags=[], watch=False,
                   unconfirmed=False, confirmed=True, note=note, as_of=as_of, source="confirmed_active")
            if key in by:
                by[key]["tags"] = []
                by[key]["watch"] = False
                by[key]["status"] = "Active"
                by[key]["confirmed"] = True

    # 2b) Carry forward last known non-expired Watch / trending / confirmed labels.
    # CI often lacks the private reports jsonl; Bet Lab public EIA + this prior keep Watson Watch
    # (and peer-pushed Murray Out rows) visible until the 6h staleness guard expires them.
    prior = load_prior_overlay()
    for key, row in prior.items():
        cur = by.get(key)
        if cur and cur.get("confirmed") and (cur.get("status") or "").lower() in ("out", "doubtful", "active"):
            continue  # live confirmed Out/Active already wins (Active clears stale Watch)
        if cur and (cur.get("tags") or cur.get("watch") or cur.get("confirmed")):
            # Prefer freshly built chrome; still fill missing Watch from prior
            if row.get("watch") and not cur.get("watch") and not cur.get("confirmed"):
                tags = list(dict.fromkeys((cur.get("tags") or []) + (row.get("tags") or []) + ["Watch"]))
                upsert(by, cur.get("aid") or row.get("aid"), cur.get("player") or row.get("player"),
                       cur.get("team") or row.get("team"),
                       status=cur.get("status") or row.get("status") or "Questionable",
                       tags=tags, watch=True, unconfirmed=True, confirmed=False,
                       note=cur.get("note") or row.get("note"),
                       as_of=cur.get("as_of") or row.get("as_of"),
                       source="prior_watch")
            continue
        # No fresh chrome for this player — carry the prior row forward
        upsert(by, row.get("aid"), row.get("player"), row.get("team"),
               status=row.get("status") or "Questionable",
               tags=list(row.get("tags") or []),
               watch=bool(row.get("watch")),
               unconfirmed=bool(row.get("unconfirmed")),
               confirmed=bool(row.get("confirmed")),
               note=row.get("note") or "",
               as_of=row.get("as_of"),
               p_inactive=row.get("p_inactive"),
               source="prior_overlay")

    # 3) official hub statuses override unconfirmed chrome
    hub = load_hub_status(by_name)
    sources_used.append("hub_players+v2.inj")
    for aid, h in hub.items():
        st = h.get("status") or ""
        key = aid
        # Map by name if needed
        if key not in by:
            for k, v in list(by.items()):
                if nm(v.get("player")) == nm(h.get("player")):
                    key = k
                    break
        if key not in by:
            continue
        if not OFFICIAL.match(st):
            by[key]["hub_status"] = st
            continue
        # Official Out/IR/Doubtful on the hub clears unconfirmed trending/watch chrome
        note = scrub((h.get("note") or "")[:280])
        upsert(by, by[key].get("aid") or aid, h.get("player") or by[key].get("player"), h.get("team") or by[key].get("team"),
               status=st if st != "Suspended" else "Suspension",
               tags=[], watch=False, unconfirmed=False, confirmed=True,
               note=note or by[key].get("note"), as_of=h.get("as_of") or by[key].get("as_of"),
               source="hub_official")

    # Finalize rows: expires, serialize as_of
    ttl = timedelta(hours=TTL_H)
    nnow = now_utc()
    players = []
    for key, p in list(by.items()):
        as_of = p.get("as_of")
        if isinstance(as_of, str):
            as_of = parse_ts(as_of)
        if as_of is None:
            as_of = eia_as_of or nnow
        expires = as_of + ttl
        # drop already-expired rows
        if expires < nnow:
            continue
        # only keep rows with tags, watch, or confirmed Out/IR worth showing.
        # Confirmed Active upgrades clear chrome and are omitted (no pill).
        tags = p.get("tags") or []
        st = (p.get("status") or "").strip()
        if not tags and not p.get("watch") and not p.get("confirmed"):
            continue
        if p.get("confirmed") and st.lower() == "active" and not tags and not p.get("watch"):
            continue
        # public-facing: never include private source URLs / reporter fields
        row = {
            "aid": p.get("aid"),
            "player": p.get("player"),
            "team": p.get("team"),
            "status": p.get("status") or "Questionable",
            "tags": tags,
            "watch": bool(p.get("watch")),
            "unconfirmed": bool(p.get("unconfirmed")),
            "confirmed": bool(p.get("confirmed")),
            "note": p.get("note") or "",
            "as_of": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if p.get("p_inactive") is not None:
            row["p_inactive"] = p["p_inactive"]
        players.append(row)

    players.sort(key=lambda r: (r.get("team") or "", r.get("player") or ""))
    out = {
        "updated": nnow.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_et": nnow.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York")).strftime("%b %-d, %Y · %-I:%M %p ET"),
        "ttl_hours": TTL_H,
        "expires": (nnow + ttl).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Display-only status overlay. Auto-built each NFL Hub data run. Official confirmed statuses override unconfirmed labels. Client hides labels when this file or a row is older than 6 hours.",
        "sources": ["early_injury_adjust", "nfl_unconfirmed_reports", "hub_player_status"],
        "sources_detail": sources_used,  # private build log; srcscrub / frontend must not render this
        "players": players,
        "by_aid": {p["aid"]: p for p in players if p.get("aid")},
        "by_name": {p["player"].lower(): p for p in players if p.get("player")},
    }
    # Strip sources_detail from the public file — keep only high-level source kinds
    public = dict(out)
    public.pop("sources_detail", None)

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "status_overlay.json").write_text(json.dumps(public, indent=2) + "\n")
    print("status_overlay.json", len(players), "players; sources:", sources_used)
    for p in players:
        if p.get("player") in ("Mike Evans", "Deebo Samuel Sr.", "Kyler Murray", "Garrett Wilson", "Deshaun Watson", "Brian Robinson") or (p.get("player") or "").startswith("Brian Robinson"):
            print(" ", p["player"], p["status"], p.get("tags"), "conf", p.get("confirmed"), "exp", p["expires"])


if __name__ == "__main__":
    main()
