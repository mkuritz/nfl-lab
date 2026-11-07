# Low Hurdles alternate floors — local preview

No pushes, deployments, model/pick/Highlighted changes, or estimator changes.

The new dataset is built from Hub player logs, not restricted to players with a published main line. NBA identities come from current Hub rotation units plus prop identities. NFL uses player files with a next game; players without a next game are omitted. No screenshot names are hardcoded. Screenshots are UX references, not proof of 2026 totals.

Default is current season only: NFL 2026 games through completed slate week 9 (including finished Thursday games); NBA dates 2026-10-20 through 2027-06-30. Default minimum is 5 across categories. Per-player floor is the highest category easy preset clearing that minimum; users can override to any positive integer and lower the minimum (including 2 for passing). Override applies globally to the filtered board. Category/position filters, position/category/name/streak sorting, and reset are provided. Counts are player/category rows, not unique players. Lowering minimum may change the per-player default floor; set an override for a fixed-threshold comparison.

Names open an in-hub threshold-history profile with season clears/known games, percentage, active run, all game totals, missing counts and explicit DNP counts. Threshold stays in this profile heading and every log result. The optional full-profile button opens the existing standard Hub profile; its standard metrics are unchanged.

Missing stat totals stop active streaks and are excluded from known-game hit-rate denominators, with their count visible. Zero is a miss at positive floors. Explicit zero-minute NBA / zero-snap NFL DNP entries are excluded and counted separately. Byes do not count. Missing whole games cannot be reconstructed from player logs alone. Rush+rec requires BOTH logged components; neither absent component is invented as zero. Kicking points require logged FG made and PAT made: 3×FG + PAT. No odds are generated. Sparse component coverage deliberately suppresses some screenshot players.

References can include prior-season runs longer than the current season. We do not silently merge seasons to reproduce them. For example, NFL Gibbs at 20+ receiving has a current latest-game miss (15), Reichard/Szmyt kicking totals have missing components, Nacua combo totals have missing components, and Charbonnet only has one current-season logged rushing game. They are not forced into qualifying rows. NBA Brown 15+ points and Williamson 15+ each verify at 7 games; Embiid 7+ rebounds at 6; Tatum 6+ assists at 7; Doncic 4+ threes at 5.

## Rebuild / tests

`python3 scripts/build_low_hurdles_alternates.py`

DOM/control tests require jsdom, installed outside repository in /workspace/lh-control-tests. Run:
`NODE_PATH=/workspace/lh-control-tests/node_modules node tests/low_hurdles_controls.cjs`

Verified: category/position filters, sort changes, positive-number validation, global threshold empty state, reset defaults, clickable threshold-history profile, missing-file state, missing-total stop, zero miss, DNP exclusion. These are DOM tests, not a visual browser QA pass. Raw-log trace spot checks match generated values. Existing native full-profile wiring is reused, not rewritten.

## Final local release check

Refreshed from latest published main datasets; NFL snapshot 5:55 PM ET and NBA snapshot 5:38 PM ET, Nov 6. All qualifying rows have a scheduled time. Historical qualifiers with injury designations remain visible with the designation; streak status is not a participation guarantee. NBA 439 rows / 187 unique players; NFL 282 rows / 178 unique players. Includes completed NFL Week 9 logs to avoid skipping a Thursday miss.

Scoped Aikido scans completed. Profile interpolation finding fixed using DOM text nodes; numeric floors hardened. Remaining generic Python file-read finding is a reviewed false positive: load() rejects every name except three fixed literal dataset filenames under the fixed repository data directory; there is no user-controlled path. No finding was suppressed in Aikido.

Responsive CSS statically checked: controls wrap and stack on narrow widths, touch targets 44px, wrapping rows, dialog max-width/height and scroll. DOM tests include full-profile callback invocation and threshold injection rejection. Visual/browser QA remains blocked by sandbox local-port policy; no policy changes or browser workarounds attempted. No deployment authorized by this review.

## Tonight release integration
Fresh production-base worktree. Reviewed Low Hurdles files only; existing production nav, models, schedules, Formulas, propintel and visual tabs left untouched. NFL is held for parent integration; NBA authorized for publication. Data rebuilt from production-base normal collector outputs, not live in-progress totals. NBA snapshot 8:03 PM ET Nov 6 includes completed logs through Nov 5; scheduled starts already passed are labeled. NFL snapshot 8:05 PM ET includes completed Week 9 logs. Prior preview counts above are historical, not tonight's release counts. Browser QA still blocked; DOM and public-asset verification only.
