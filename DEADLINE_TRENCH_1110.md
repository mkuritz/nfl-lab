# Trenches through the Nov 10, 2026 trade deadline (preview, NOT published)

Sources: NFL.com trade tracker, ESPN deadline tracker, theScore, PFT, Pro Football Rumors (all confirmed deals).

Missing from the live Hub before this branch:
- DT Jordan Davis PHI -> JAX (Nov 9; 2027 1st + 2029 2nd). The Nov 9 preview had marked it rumor-only; it was confirmed later that day. 2026 PBP while on PHI: 2 sk, 3 QBH, 3 run stuffs.
- C Ryan Neuzil ATL -> BAL for G Andrew Vorhees + 2028 6th (Nov 10). Neuzil 100% ATL snaps all 9 weeks; Vorhees 36% recent snaps (below starter gate, moves nothing).
Not counted: EDGE Arnold Ebiketie PHI -> CIN (agreed, then called off).

Same inputs (nflverse thru Week 9, live injury feed), before -> after:
| Team | DL | Pass rush | Run D | OL | Pass block | Run block |
|---|---|---|---|---|---|---|
| JAX | 66 -> 72 | 41 -> 50 | 97 -> 100 | 78 -> 79 | 74 | 83 -> 84 |
| PHI | 9 -> 7 | 9 -> 6 | 9 | 22 -> 21 | 31 -> 30 | 12 |
| BAL | 59 -> 57 | 50 -> 47 | 69 | 41 -> 55 | 25 -> 40 | 57 -> 70 |
| ATL | 46 | 38 | 56 | 80 -> 74 | 80 -> 79 | 80 -> 69 |
Power rating: JAX 16.20 -> 16.65, PHI -13.15 -> -13.55 (BAL/ATL unchanged; OL move only shifts unit inputs).
Tests: scripts/v2/tests/test_deadline_trench_1110.py (4) + updated test_godchaux_trench.py (5).
