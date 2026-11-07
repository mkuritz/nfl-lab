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

## Usability revision — verified for release
Compact primary visual tabs with active item always visible; other native tools retained under More Hub tools. Dark legible44px controls, immediate filters/reset, summary metric cards, collapsed dense data/methodology, readable secondary text and source-backed SVG tooltips. Historical probability points/selectors expose actual recorded window summaries.110 cross-hub DOM/data/security/usability assertions passed, including reset/active-tab/real-chart selection;20-file delta Aikido scan0 issues. Publication is tracked by release commits and workflow status; browser visual QA remains pending. No new access-entitlement or model changes.

Native shared account bootstrap (`https://sportslabshq.com/sl/sl.js?v=12`) is retained on each new route, matching original Hub pages; no plan, allowance or shared entitlement implementation was changed. DOM tests do not run external account/authentication scripts.

## Final coordinated NFL design port
Reviewed design6926fe97 was applied onto the integrated branch and ported to safe DOM nodes/text/attributes, not imported HTML templates. cand-grid structure, inert/sl-locked protection and canonical SLGateState allowances are retained. Reset/sort cannot briefly unlock another row before the shared observer reapplies gating; detached/stale history cannot open a profile. Anonymous1teaser/285locked, existing member2teasers and paid allowance verified against the current public gate functions in an isolated DOM. No auth/session data used. Gate test: `NODE_PATH=/workspace/visual-preview-tests/node_modules node tests/low_hurdles_gate.cjs`; prerequisite public source cache: `curl -fsS 'https://sportslabshq.com/sl/sl.js?v=12' -o /workspace/visual-preview-work/release-tests/public-shared-gate.js`. Last18-file integration scan0 issues. Native player/team profiles and all source-required credits retained. No browser visual QA claimed for this integrated version.

Final modal/access integration polish: native account bootstrap retained; native HTML dialogs reserve bottom access-banner space. Final27-file scoped scan0 issues.110 combined Hub assertions still pass. No browser visual QA is claimed.

Requested standalone polish ported without replacing safe JS: teaser spans full width; metadata enlarged; modal reserves bottom banner space. NFL JS and CSS both reference1106layout2; standalone mount sets lhx-active. Static version/layout assertions and actual gate contract tests passed against the identical v13 public gate.
