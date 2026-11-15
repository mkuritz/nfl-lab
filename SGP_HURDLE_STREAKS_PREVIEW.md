# Same Game Hurdle Streak Bundle — preview (not live)

Branch: `preview/nfl-over-streaks-1115`. Display-only. Nothing merged or published to the public Hub.

## What already existed
- **NFL Hub left nav** already has High Hurdles (smash / plus-money, model + review) and Low Hurdles (active streaks over the *published main* line, adjustable alt floors). Those tabs are unchanged.
- **Bet Lab** already has Perfect Streaks and dashboard “active over streaks” vs today’s listed line, plus “easy hurdles” parlays at L10 rates. Different product (not a season-long *highest* clear, not Hub left-nav).
- This tab reuses Hub `data/v2.json` slate rows, `data/players/*.json` game logs (same as Low Hurdles), already-built alt rungs in the prices sidecar when present, `nfl_dvp.json` / `dvp_viz.json` for defense ranks, and engine availability / official manual Outs (e.g. David Montgomery). No new odds pulls.

## How to view
- Local: from this checkout, serve the folder and open `/sgp-hurdle-streaks.html`.
- Left nav label: **SGP Hurdle Streaks**. Page title: **Same Game Hurdle Streak Bundle**.
- Screenshots: `/workspace/previews/nfl-over-streaks-1115/`.

## Defaults
- Season view, **100%** clear rate (every game played), min 6 games. UI: 100 / 90 / 80 / 75.
- Highest qualifying rung (posted alts first; standard increments only extend below if no posted rung qualifies).
- Parlays: 2–4 legs, one leg per player, yards markets preferred over tiny count floors. Combined rate is the product of season rates, labeled not independent.

## Known limits
- The Hub slate for Sunday Nov 15, 2026 is **Week 10**, not Week 11.
- Logs do not flag mid-game injury exits; 0-snap DNPs are excluded; low snap share is mentioned, not assumed to be an injury.
- Past-game defense marks use each opponent’s *current* season rank vs that position (not a week-by-week rank, which we don’t have). This week’s matchup also shows the slate’s stat rank when present.
- Most 100% rungs sit below the main line, so listed book prices are often missing. No official SGP quotes.
