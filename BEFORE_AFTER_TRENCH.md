# Trenches before/after — Nov 9, 2026 (NOT published)

## Trade verification
- **Jordan Davis (PHI DT) was NOT traded.** Public trackers (NFL.com trade deadline tracker, Eagles Wire Nov 9) list only speculation / proposed offers. Live ESPN roster + Sleeper still show Davis on PHI. No PHI/JAX change prepared for Davis.
- **Actual DL move today:** Davon Godchaux, NO → JAX (Nov 9), conditional 2028 6th. Also Jessie Bates III ATL → JAX (secondary, not trenches).

## Live Hub BEFORE (nfllab.sportslabshq.com/data/teams_v2.json, thru week 9, checked ~5:00 PM ET Nov 9)
| Team | DL % | Pass rush % | Run D % | Trades note |
|------|------|-------------|---------|-------------|
| PHI  | 9    | 9           | 9       | Ojomo Q only; Davis still counted for PHI |
| JAX  | 71   | 50          | 97      | no Godchaux note; Hamilton IR not applied |
| NO   | 52   | 75          | 25      | Godchaux still counted for NO |

Published `trades[]` still ends at Oct 29 Simmons / Oct 27 Buckner+Nelson.

## Simulated AFTER on local 2026 PBP (thru week 6 snapshot; injury-unadjusted; same `_player_trench` method as Simmons)
Godchaux 2026 contribution while on NO: **0 sk, 0 QBH, 2 run stuffs** (small sample / soft year).

| Team | DL % before → after | PR | RD |
|------|---------------------|----|----|
| JAX  | 60 → 62             | 34→34 | 91→97 |
| NO   | 27 → 25             | 41→41 | 9→6 |
| PHI  | 10 → 10 (unchanged) | 3→3 | 19→19 |

Counterfactual if Davis had actually gone PHI→JAX (he did not): JAX DL 60→65; PHI DL stayed 10 (unit already bottom-tier).

Hamilton IR (confirmed athlete IR since Nov 4; missing from league injury board feed): applying trench_avail 0.5 backup weight on his JAX contribution drops simulated JAX DL **60 → 53**. Overlay adds him so the next Hub v2 rebuild applies this.

## What the prepared branch changes (no push/publish)
1. `scripts/v2/analytics.py` — move Godchaux PBP trench stats NO→JAX; DL notes; trades[] entry dated 2026-11-09.
2. `scripts/profiles.py` — TRADE_OV belt-and-suspenders for Godchaux (3115383→JAX), Bates (3919512→JAX), Brissett (2578570→BAL). Live profiles already correct via Sleeper.
3. `data/trench_overlay.json` + `trench_avail.py` — Hamilton IR overlay with espn_id; overlay can carry espn_id links so DL path resolves.
4. Tests: `scripts/v2/tests/test_godchaux_trench.py` (5 passing).

Live AFTER numbers will differ slightly once week-9 PBP + injury overlay run in Hub v2 (`bash scripts/v2/run.sh` on the next approved data refresh).
