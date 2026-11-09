# Passing TD ladder — Low Hurdles preview (no publish)

Branch: `preview/passtd-ladder-1109` (nfl-lab + bet-lab worktrees under `/workspace/wt`)

## What changed
- Added **Passing TDs** category to NFL Low Hurdles (`1+ / 2+ / 3+` presets).
- Calibrated each rung with the existing Poisson mean blend (`0.65×L10 + 0.35×season`), same family as `pro_analytics.tail_prob`.
- **Recommend** = highest rung clearing model ≥60%, L10 ≥60%, and +2% edge when a live alt price exists.
- Dark rounded **rung pills** (44px) replace the numeric floor input when Passing TDs is selected; per-card 1+/2+/3+ switchers.
- Consolidated **collapsible results** panel at the bottom with Week 9 / Nov 8 finals backtest.
- Other props and Ask/spot gating unchanged. Nothing to Discord. Preview only.

## Backtest (Week 9 finals = Nov 8, 2026)
See `/workspace/passtd-ladder-1109/BACKTEST.json`.

## Blocked / gaps
- Live alt-line prices mostly missing in the `prop_prices` sidecar (sparse/stale Oct 29 snapshot) — rungs still show model probs; UI discloses “Alt price unavailable”.
- Ask 5-Pillar board gating not changed (per brief); ladder UX lives on Low Hurdles.
