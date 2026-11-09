# NFL Spots — local preview only

Worktree: `/workspace/wt/nfl-spots-preview-1106` · branch `preview/nfl-spots-1106` · base `41f91648` (latest main at task start). No push, deployment, workflow, schedule, model, pricer, estimator or existing Highlighted change. The only existing source file edited is `navcfg.js`: one Spots link. Existing NFL areas are otherwise untouched.

## One area, all nine views
Open `spots.html`. Switch via the grouped controls; no other pages or tabs are needed for these screens. `?view=` values and actual default supported card counts (existing paid access):

| View | Parameter | Actual supported cards |
|---|---|---:|
| TD Watch WR / TE | td-wrte | 97 |
| TD Watch RB | td-rb | 34 |
| TE Line Checks | line-te | 22 |
| WR Line Checks | line-wr | 48 |
| RB Line Checks | line-rb | 31 |
| QB Line Checks | line-qb | 25 |
| Rising Roles | roles | 45 positive target changes |
| Matchups at a Glance | matchups | 14 scheduled games |
| Soft Spots | soft | 28 opponent/WR allowance contexts |

Counts change with selected market/position/metric and current-game/freshness checks. Twelve cards render initially; Show more adds twelve without changing teaser authorization. There are 507 normalized player/market/game rows across 167 verified native IDs, not507distinct players. Internal game filters retain their selection when switching views. `market=Carries` works with `view=line-rb`; `game=401873038` filters CIN/ATL. All navigation remains on spots.html. Native player/team controls open existing in-hub modals with exact IDs. Chart bars support click, Enter and Space with visible actual-game details.

## Data and honesty
`python3 scripts/build_spots_preview.py` is an OFFLINE manual adapter reading existing `data/v2.json`, `data/nfl.json`, `data/nfl_dvp.json`, and exact `data/players/{id}.json` records. It makes no requests and activates no jobs. Output `data/spots_preview.json` includes input hashes, source timestamps and explicit coverage gaps. Sources were recorded6November2026 at9:50PM ET; fourteen future games remain after excluding the completed JAX/BAL game. Fifty-six noncurrent/inconsistent rows are not included. Freshness expires90minutes after the older player/game snapshot; no command-line clock override exists. A stale producer fails before replacing output, and a newer output is preserved over older input. Rebuild only from refreshed, approved native inputs. Runtime checks fail closed on source timestamp changes, old/future snapshots, season/week/game mismatches, kickoff or cancellation in the loaded native game snapshot. One-shot client expiry timers hide rows at source expiry/kickoff; no polling feed or cron exists. Everything is labeled recorded, not live.

Line Checks use **native reference lines**, not verified bookmaker lines: the source supplies no bookmaker provenance for non-TD lines. Actual offered-line verification remains a blocker before any stronger market claim. Explicit numeric native profile fields—not inherited zero-filled `v2.vals` summaries—produce the2026 histories. Missing fields, DNP-less absence and incomplete combined-stat components are not filled with zero; older seasons and current/future weeks are excluded. Equality is a push; the displayed over rate excludes pushes. Comparisons to today's reference are not an official graded betting record.

TD Watch retains existing probabilities and supplied quoted prices, including raw American implied probability. No new model or calibration is claimed; native market-blended estimates are labeled. Existing Highlighted booleans are copied without new criteria. Red-zone splits, touch coordinates and calibrated observed TD rates are not inferred from incomplete fields. Incomplete TD components therefore can leave historical scoring comparison unavailable.

Rising Roles uses the latest three vs preceding three explicit same-team observations (actual weeks shown), not causal injury redistribution or an automatic future forecast. Soft Spots uses recorded positional allowance fields and an explicitly unweighted mean of supplied team averages; this is not an inferred player forecast. RB yardage split is not verified, so no rush/receiving split is claimed. Matchups show only supplied lines/totals. No line movement claim is made without timestamped opening/current inputs. Existing data credits are retained via the same `data-credits.html` link and unchanged shared SDK.

## Access and safety
Anonymous one and existing free-member two teaser identities are selected **before** filters/sorting/paging within each view. Those controls cannot rotate into new protected player details. Paid access comes only from the existing `SLGateState()`. Locked placeholder cards never contain protected performance or native profile controls, even if the shared gate changes their visual mask. Unknown gate state fails closed to the anonymous allowance. Refresh access re-renders after the native account state updates. Native profile handlers recheck eligibility, current game, connection and inert/locked status after asynchronous loading. No query string, reset or paging control grants access.

Optional shared timing/Top10 modules are suppressed only on this new recorded area. The canonical shared SDK, account controls and existing core pages remain unchanged. Safe DOM text nodes/attribute allowlists are used throughout; no data templates or innerHTML.

## Verification and acceptance limits
-86Spots DOM/data/access assertions,5Python builder cases,61existing NFL visual assertions passed.
-Existing canonical shared-gate test still anonymous1+285locked, member2, paid unchanged; propintel freshness test passed.
-Aikido final scoped scan:9files, zero findings, no ignored warnings.
-Actual player examples and source hashes: `audit/spots-preview.json`.
-No browser, local port, tunnel or policy workaround used. Responsive styling is implemented but actual visual/browser QA is pending.

The nine exact JPG filenames were absent from ordinary authorized attachment/workspace locations. A contact sheet of29recent parent JPGs was inspected; none was identified as the requested nine Spots designs, and no unrelated photo was substituted or copied into Git. Transcript lookups returned no record of the preceding detailed dispatch; durable memory confirms the nine-view single-area scope but not the full column-level acceptance criteria. This is a useful functional nine-view preview, **not a claim of exact reference/brief fidelity or production readiness**. Recover/re-attach the originals and preceding full brief for that acceptance pass. Supported attachment checks: https://docs.x.ai/grok-bot/troubleshooting#an-attachment-cannot-be-read . No computer recovery/reset or external message was performed.
