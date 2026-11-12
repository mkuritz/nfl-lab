# NFL Hub usage + Unit Board preview (branch preview/nfl-usage-1112) — NOT published

Display-only. No model, schedule, pricer or other-sport change. Open `injury-cascade.html` (Opportunity Board) and `unit-board.html`.

## What was added
| Piece | Where | Data (all already refreshed by the Hub update) |
|---|---|---|
| Opportunity Share (All / Targets / Rushes, callout, share bar, with/without each starting QB, last-3 trend) | `usage-board.js` on Opportunity Board | `data/usage_board.json` ← `data/players/*.json` weekly logs |
| Position Rank Movement (QB/WR/RB/TE, season avg or last 3, vs last week or 3 weeks ago, "Why" drop-down, rank history line) | same | PPR points, snap %, targets/carries vs team totals, starting QB per game, teammates with no recorded appearance, red-zone touches |
| Defensive Playmakers (DL+OLB sacks / QB hits / TFL; CB+S INT / PD / tackles; same rank movement and "Why") | same | defensive stats in weekly logs, depth-chart slot |
| Matchup Impact (points, pass yds, rush yds, sacks vs average; slate board; method panel) | `unit-impact.js` on Unit Board | `data/unit_impact.json` ← team-game EPA, schedule scores, weekly logs |
| Rising Roles link to the new section | `spots.js` (one appended link) | n/a |

## New build steps (in `update.yml`, one step after the Spots snapshot, continue-on-error)
`build_opportunity_history.py`, `build_unit_board.py` (these two were manual-only before, so the old Unit/Opportunity data went stale), `build_usage_board.py`, `build_unit_impact.py`. Each writes atomically and leaves the previous file on failure. No new schedule, secret or request.

## Conversions (Unit Board)
Least-squares slopes fitted on 2025 + current-season team games from week 4 on, features use only earlier games (no look-ahead). Points use the Hub power rating's own unit (EPA per game). Fit n, share explained and slopes are shown on the page. If the schedule file is missing the last committed points fit is reused; otherwise impact is withheld.

## Gaps (labelled on the page)
- No pass-rush pressure data: QB hits stand in. Snap % is blank where the feed has none. Teammate "out" notes say "no recorded appearance" (plus the current report when one exists); they are not causal claims.
- Edge/OLB group uses the position or depth-chart slot in the feed (LDE/RDE/SLB/WLB).
- Unit impact excludes QB/injury changes, special teams, home field, weather.
- Rank movement is descriptive, not a forecast.

Tests: `python3 tests/test_usage_board.py`; existing `supported_visual_release.cjs` (page-wide SVG counts scoped to `#preview-app`), `hub_spots.cjs`, `spots_preview.cjs` pass.
