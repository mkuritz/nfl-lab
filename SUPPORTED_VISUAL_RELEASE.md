# Supported visual release — Nov6,2026

## Supported visual routes
- `unit-board.html?off=BUF&def=MIN`:32-team actual pass/rush/overall EPA and sack-rate aggregates; unchanged existing `hl` TD flags only, no invented flag or pressure/explosive proxy.
- `injury-cascade.html?off=BUF&window=1|4|all` (Opportunity Board): actual2373 source player-week rows across32 teams, descriptive attributed carry/target shares. Current injury roster is separate. Exact historical GSIS details remain local dialogs, never guessed ESPN routes.
- Existing native team/player modals are used only for supported exact IDs. LA/LAR and WAS/WSH aliases are normalized.
## Rights / freshness
Dataset-specific official `nflverse/nflverse-data/main/LICENSE.md` is CC BY4.0; repository DESCRIPTION explicitly applies this to automated data releases. This is distinct from the R package MIT license. Source producer `scripts/v2/analytics.py` builds this cache from that play-by-play dataset. No new raw retrieval or logos. Required nflverse contributor/source/license/modification credit is retained in `data-credits.html`, visible feature footers and JSON metadata; full upstream license/disclaimer is retained under `licenses/`. This mandatory credit overrides the general request to omit source names. Dataset licensing does not grant league trademarks/publicity/endorsement rights or guarantee all upstream rights.
Manual derived snapshots include source SHA256, derivation time, actual through-week and unknown source-refresh time; they DO NOT auto-refresh with the player feed. Atomic builders reject empty/future/malformed season/team/week/count inputs. No schedule installed. No precise red-zone event map, calibration, measured prop movement or causal redistribution tab.
## Coordinated additions
Low Hurdles staged commit5bc85e21 and propintel freshness commit9dd23eec were cherry-picked separately on this branch, preserving their tests and controls. No model/pricer/Highlighted logic changes.

## Verification and limits
91 cross-hub DOM/runtime/data/identity/security assertions passed against these exact release worktrees. Run one hub independently with `NODE_PATH=/workspace/visual-preview-tests/node_modules node tests/supported_visual_release.cjs`; `jsdom` is required. Browser/local-port visual verification remains pending under sandbox policy; no layout screenshot or PDF inspection claimed. No firewall/proxy/tunnel/browser workaround used.

Initial40-file Aikido scan reported10 pre-existing template warnings in legacy CBB `players.html` (the only proposed change was a profile-entry script). That modification was removed entirely; native modal invocation now occurs directly from Matchup Duel. No warnings were ignored or rules suppressed. Final combined47-file scan:0 issues. Evidence is under `audit/supported-release-aikido-*.json`. The intermediate combined scan found prop-intel HTML rendering and a dynamic builder file read; both were replaced with DOM construction/fixed-path readers and rescanned successfully. No findings ignored. Existing native hub renderers were not globally security-audited.

No new ingestion, schedules, workflows, keys, paid access, pick weights or pricing changes in this release. Unsupported menus are absent rather than empty landing pages. Original hub nav/features remain; only additive supported entries.

Combined NFL validation also passed existing Low Hurdles controls/filter/sort/reset/empty/threshold history/missing/zero/DNP tests, unchanged freshness-gate tests, new hostile-string DOM tests and long-open prop-intel expiry in both native profile slots. Low Hurdles/prop-intel rendering was hardened without changing threshold math or availability-gate rules. Required historical-count credit is also visible on Low Hurdles.
