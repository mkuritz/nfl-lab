# NFL RB expected rush yards — LOCAL PREVIEW ONLY

Branch: `preview/nfl-rb-expected-yards`  
Formula (whiteboard): **RB avg rush attempts × opponent yards allowed per rush attempt**

Display-only matchup layer. Does **not** replace Sports Labs rush-yards projection, change pick logic, High Hurdles ranking, or pricer constants. Nothing pushed / not live.

## Preview

```sh
python3 scripts/build_rb_expected_rush.py
python3 -m unittest tests.test_rb_expected_rush -v
python3 -m http.server 8767 --bind 127.0.0.1
# Open Hub, click an RB (e.g. Derrick Henry or Jahmyr Gibbs) → Expected rush yards card
# Matchup Board → Rushing tab shows the same one-line math under Projection
```

## Data

- Snapshot: `data/meta.json` / `matchups.json` week 9, updated **2026-11-06 ~2:50–2:52 PM ET**
- Player attempts: season avg carries from published logs (matchups `adv.car` when on the rush board)
- Opponent rate: matchups board **Yds/car** when published; otherwise YPC from aggregated 2026 player-log rush yards ÷ rush attempts faced
- If attempts faced are missing, the estimate is hidden

## Coverage

See `data/rb_expected_rush.json` → `coverage`.
