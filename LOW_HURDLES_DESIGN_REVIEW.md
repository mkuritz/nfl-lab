# Low Hurdles design candidate — local only

No publish until parent visual review and explicit integration ownership. Scoped presentation redesign only; evaluated thresholds, presets, data, hit-rate denominators and model/Highlighted logic unchanged.

Replaces dense text banners and unstyled controls with dark/teal Sports Labs hierarchy, wrapped category and position chips, labeled floor/minimum inputs, contextual floor help, instant rows/unique-player counts and reset. Each player card emphasizes identity, chosen floor, consecutive clears, known-game hit rate, real recent clear/miss markers and injury context. Preserves the full list and existing shared account gate, including 1 teaser / 427 gated NBA rows. No pagination-based entitlement changes. The repeated-card grid is re-created on filter updates so the shared gate reapplies; locked/inert card actions do not open history.

History uses actual last 12 totals oldest-to-newest, a text description of every chart value and clear/miss outcome, all-game expandable log, explicit missing/DNP counts, selected-floor context, and native profile action. Negative totals labeled at the baseline, not fabricated positive bars. Native dialog supports Escape; close restores focus. Category chips keep focus after filtering. Responsive single-column cards, 44px mobile chips, scoped typography and strong focus outlines; no animation required.

Verification: DOM tests cover chips/focus, filters, entitlement-compatible list, reset, invalid/empty thresholds, result counts, real-log chart, selected history, native callback and focus restoration. Static responsive/style review only. Browser visual QA remains blocked; parent screenshots still awaited. No proxy, firewall, policy or browser bypass.

NFL patch applies atop held adjustable release 5bc85e21; production integrator must also include that base release if not already integrated. New CSS and engine plus small NFL HTML cleanup only—no nav/visual-tab/propintel edits. NBA patch applies atop released adjustable board 8b75fe098.

Public desktop screenshots reviewed. Fixes address white native controls, overlong disclaimers, tiny dense cards, cramped history and hidden active tab. On Low Hurdles only, top KPI strip is hidden, tab labels wrap instead of horizontal burial and desktop width is expanded. No entitlement rules or shared gate code modified. No mobile visual review claimed.

Final verification: Aikido scoped scans clear (NBA 5 files, NFL 4). Public gate implementation tested unchanged in an isolated DOM: NBA 1 teaser + 427 locked; NFL 1 teaser + 285 locked; reset reapplies locks and inert row clicks cannot open details. No authentication/session data used.
