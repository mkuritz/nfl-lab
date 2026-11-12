#!/usr/bin/env python3
"""Invariant checks for data/usage_board.json and data/unit_impact.json (run after the builders)."""
import json, math, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
D = json.loads((root / 'data/usage_board.json').read_text()); U = json.loads((root / 'data/unit_impact.json').read_text())
fails = []
def ok(c, m):
    if not c: fails.append(m)
W = D['through_week']
for t, T in D['usage']['teams'].items():
    weeks = {g[0]: g for g in T['games']}
    for w, g in weeks.items():
        if g[3] is not None:
            got = sum(x[2] for p in T['players'] for x in p['g'] if x[0] == w)
            ok(got <= g[3] + 0.5, f'{t} W{w}: player targets {got} exceed team total {g[3]}')
        ok(sum(x[3] for p in T['players'] for x in p['g'] if x[0] == w) <= g[4], f'{t} W{w}: carries exceed team total')
    for p in T['players']:
        for x in p['g']:
            ok(x[0] in weeks, f'{t} {p["n"]}: logged week {x[0]} not a team game')
for pos, plist in D['rank']['positions'].items():
    for m in ('season', 'form'):
        for w in range(W):
            rk = sorted(p['rk'][m][w] for p in plist if p['rk'][m][w] is not None)
            ok(not rk or rk[0] == 1, f'{pos} {m} W{w + 1}: board must start at rank 1')
for g, items in D['defense'].items():
    ok(all(len(p['rk']) == W for p in items), f'defense {g}: rank length')
F = U['fit']
for k, f in F.items():
    ok(all(math.isfinite(f[x]) for x in ('a', 'k_off', 'k_def', 'r2')), f'fit {k} not finite')
    ok(f['n'] >= 150, f'fit {k} too few games')
ok(F['points']['k_off'] > 0 and F['points']['k_def'] > 0, 'points slopes must be positive')
for t, x in U['teams'].items():
    ok(1 <= x['rk']['pass_o'] <= 32, f'{t} rank range')
print('FAIL' if fails else 'PASS', len(fails))
for m in fails[:20]: print(' -', m)
sys.exit(1 if fails else 0)
