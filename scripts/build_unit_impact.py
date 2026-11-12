#!/usr/bin/env python3
"""Unit Board impact layer: turns team efficiency (EPA/play, sack rate) into things a bettor can read:
points, passing yards, rushing yards and sacks versus an average opponent, for any offense vs any defense.

HOW THE CONVERSIONS ARE DERIVED (nothing hand-set):
  * Same team-game history the Hub already stores (data/pbp_v2.json, 2025 + current season) joined to final
    scores (schedule file the v2 build already downloads to $SL_RAW/games.csv) and to weekly player logs for yards.
  * For every team-game from week 4 on, features use ONLY games before it (season-to-date, no look-ahead):
    offense edge = (team season-to-date EPA/play - league season-to-date EPA/play); defense edge likewise for EPA allowed
    by the opponent.  Targets: points scored, team passing yards, team rushing yards, sacks taken.
  * Ordinary least squares: target = a + k_off * offense_edge + k_def * opponent_defense_edge.  The slopes ARE the
    conversion (e.g. +0.10 pass EPA/play on offense is worth k_off * 0.10 * pass plays/game yards).  Because the
    features are noisy season-to-date estimates the slopes are already shrunk toward zero, which is what a bettor needs.
  * Points use the model's own unit: Hub power rating = EPA per game (data/teams_v2.json), so total EPA/game is the
    regressor and each unit's points = its share of that EPA (EPA/play edge x plays/game).
  * The fit (n, R^2, slopes) is stored in the output and shown on the page.  If the schedule file is missing the last
    committed fit is reused; if there is none the page says impact is unavailable.  Never invented.
Display-only: no model, schedule or pricer is touched.  Output: data/unit_impact.json (atomic).
"""
from pathlib import Path
from collections import defaultdict
import json, math, os, tempfile
from datetime import datetime, timezone
import numpy as np

root = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get('SL_RAW', '/tmp/nflraw'))
CANON = {'LA': 'LAR', 'WAS': 'WSH'}
canon = lambda t: CANON.get(t, t)
VALID = set('ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LV LAC LAR MIA MIN NE NO NYG NYJ PHI PIT SF SEA TB TEN WSH'.split())
MIN_PRIOR_WEEK = 4

pbp = json.loads((root / 'data/pbp_v2.json').read_text())
seasons = sorted(int(s) for s in pbp['tw'] if pbp['tw'][s])
season = seasons[-1]
if not 2020 <= season <= datetime.now(timezone.utc).year:
    raise SystemExit('Bad season; preserving prior output')
prior_out = {}
try: prior_out = json.loads((root / 'data/unit_impact.json').read_text())
except Exception: pass

# team-game table
TW = {}
for s in seasons:
    for key, r in pbp['tw'][str(s)].items():
        t, w = key.split('|'); t = canon(t)
        if t in VALID: TW[(s, t, int(w))] = r
# yards from weekly player logs
YARDS = defaultdict(lambda: [0.0, 0.0])
for f in (root / 'data/players').glob('*.json'):
    try: p = json.loads(f.read_text())
    except Exception: continue
    for l in p.get('log') or []:
        t = canon(l.get('t', ''))
        if t in VALID and l.get('s') in seasons:
            YARDS[(l['s'], t, l['w'])][0] += l.get('passing_yards') or 0
            YARDS[(l['s'], t, l['w'])][1] += l.get('rushing_yards') or 0
# points
PTS = {}
games_csv = RAW / 'games.csv'
if games_csv.exists():
    import csv
    for r in csv.DictReader(open(games_csv)):
        if r['game_type'] != 'REG' or r['home_score'] in ('', 'NA') or int(r['season']) not in seasons: continue
        s, w = int(r['season']), int(r['week'])
        PTS[(s, canon(r['home_team']), w)] = int(r['home_score']); PTS[(s, canon(r['away_team']), w)] = int(r['away_score'])

FIELDS = ['n', 'epa', 'pn', 'pepa', 'rn', 'repa', 'dn', 'depa', 'dpn', 'dpepa', 'drn', 'drepa', 'sk', 'dsk']


def cum(s, t, upto):
    a = defaultdict(float); g = 0
    for w in range(1, upto + 1):
        r = TW.get((s, t, w))
        if r:
            g += 1
            for k in FIELDS: a[k] += r[k]
    a['g'] = g
    return a


def league(s, upto):
    a = defaultdict(float)
    for t in VALID:
        c = cum(s, t, upto)
        for k in FIELDS + ['g']: a[k] += c[k]
    return a


def edges(s, t, o, upto):
    """(offense edge, opponent-defense edge) per feature set using games <= upto only."""
    T, O, L = cum(s, t, upto), cum(s, o, upto), league(s, upto)
    if T['g'] < 3 or O['g'] < 3: return None
    f = {}
    # per game total EPA (model's own unit)
    f['pts_o'] = T['epa'] / T['g'] - L['epa'] / L['g']
    f['pts_d'] = O['depa'] / O['g'] - L['depa'] / L['g']
    f['pass_o'] = T['pepa'] / T['pn'] - L['pepa'] / L['pn']; f['pass_d'] = O['dpepa'] / O['dpn'] - L['dpepa'] / L['dpn']
    f['rush_o'] = T['repa'] / T['rn'] - L['repa'] / L['rn']; f['rush_d'] = O['drepa'] / O['drn'] - L['drepa'] / L['drn']
    f['sack_o'] = T['sk'] / T['pn'] - L['sk'] / L['pn']; f['sack_d'] = O['dsk'] / O['dpn'] - L['dsk'] / L['dpn']
    return f


def ols(X, y):
    X = np.asarray(X, float); y = np.asarray(y, float)
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ beta; n, k = A.shape
    s2 = res @ res / max(1, n - k)
    cov = s2 * np.linalg.pinv(A.T @ A)
    r2 = 1 - (res @ res) / (((y - y.mean()) ** 2).sum() or 1)
    return {'a': float(beta[0]), 'k_off': float(beta[1]), 'k_def': float(beta[2]), 'se_off': float(math.sqrt(cov[1, 1])), 'se_def': float(math.sqrt(cov[2, 2])),
            'n': int(n), 'r2': float(r2), 'rmse': float(math.sqrt(res @ res / n))}


rows = []
for (s, t, w), r in TW.items():
    if w < MIN_PRIOR_WEEK or not r.get('opp'): continue
    o = canon(r['opp']); f = edges(s, t, o, w - 1)
    if not f: continue
    rows.append((s, t, w, f))
fit = {}
def run(name, ko, kd, target):
    X, y = [], []
    for s, t, w, f in rows:
        v = target(s, t, w)
        if v is None: continue
        X.append([f[ko], f[kd]]); y.append(v)
    if len(y) >= 150:
        fit[name] = ols(X, y)
        fit[name]['seasons'] = seasons; fit[name]['from_week'] = MIN_PRIOR_WEEK
run('points', 'pts_o', 'pts_d', lambda s, t, w: PTS.get((s, t, w)))
run('pass_yds', 'pass_o', 'pass_d', lambda s, t, w: YARDS[(s, t, w)][0] if (s, t, w) in YARDS else None)
run('rush_yds', 'rush_o', 'rush_d', lambda s, t, w: YARDS[(s, t, w)][1] if (s, t, w) in YARDS else None)
run('sacks', 'sack_o', 'sack_d', lambda s, t, w: TW[(s, t, w)]['sk'])
if 'points' not in fit and prior_out.get('fit', {}).get('points'):
    fit['points'] = prior_out['fit']['points']; fit['points']['reused'] = True
# Sanity: slopes must have the sensible sign or the conversion is withheld rather than shown.
for k in list(fit):
    f = fit[k]
    sign = 1 if k != 'sacks' else 1
    if not (f['k_off'] > 0 and f['k_def'] > 0):
        fit[k]['withheld'] = True

# team season-to-date table
maxw = max(w for (s, t, w) in TW if s == season)
L = league(season, maxw)
league_out = {'pass_epa': L['pepa'] / L['pn'], 'rush_epa': L['repa'] / L['rn'], 'epa_pg': L['epa'] / L['g'], 'sack_rate': L['sk'] / L['pn'],
              'pass_pg': L['pn'] / L['g'], 'rush_pg': L['rn'] / L['g'], 'pass_def_epa': L['dpepa'] / L['dpn'], 'rush_def_epa': L['drepa'] / L['drn'], 'def_epa_pg': L['depa'] / L['g'], 'sack_rate_def': L['dsk'] / L['dpn']}
T = {}
for t in sorted(VALID):
    c = cum(season, t, maxw)
    if not c['g']: continue
    T[t] = {'g': int(c['g']), 'pass_pg': c['pn'] / c['g'], 'rush_pg': c['rn'] / c['g'],
            'pass_o': c['pepa'] / c['pn'], 'rush_o': c['repa'] / c['rn'], 'epa_pg': c['epa'] / c['g'],
            'pass_d': c['dpepa'] / c['dpn'], 'rush_d': c['drepa'] / c['drn'], 'depa_pg': c['depa'] / c['g'],
            'sack_o': c['sk'] / c['pn'], 'sack_d': c['dsk'] / c['dpn']}
def ranks(key, reverse):
    order = sorted(T, key=lambda t: T[t][key], reverse=reverse)
    for i, t in enumerate(order, 1): T[t].setdefault('rk', {})[key] = i
# rank 1 = best: offense high EPA / low sack taken; defense low EPA allowed / high sack rate
for k in ('pass_o', 'rush_o', 'epa_pg', 'sack_d'): ranks(k, True)
for k in ('pass_d', 'rush_d', 'depa_pg', 'sack_o'): ranks(k, False)
for t in T:
    for k in list(T[t]):
        if isinstance(T[t][k], float): T[t][k] = round(T[t][k], 5)
league_out = {k: round(v, 5) for k, v in league_out.items()}

slate = []
try:
    tr = json.loads((root / 'data/trends.json').read_text())
    wk = max((g['week'] for g in tr.get('upcoming', [])), default=None)
    for g in tr.get('upcoming', []):
        if canon(g['home']) in VALID and canon(g['away']) in VALID:
            slate.append({'week': g['week'], 'day': g.get('day'), 'time': g.get('time'), 'home': canon(g['home']), 'away': canon(g['away']), 'spread_home': g.get('spread_home'), 'total': g.get('total')})
except Exception:
    pass

fit = {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in fit.items()}
out = {'season': season, 'through_week': maxw, 'league': league_out, 'teams': T, 'fit': fit, 'slate': slate,
       'method': 'Least-squares fit on 2025 + current-season team games from week 4 on, using only prior games. See scripts/build_unit_impact.py.',
       'attribution': {'creator': 'Contributors', 'license': 'CC-BY-4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/', 'changes': 'Aggregated and fitted; no raw plays in this output.'},
       'derived_at': datetime.now(timezone.utc).isoformat()}
if not T or not fit:
    raise SystemExit('No usable data; preserving prior output')
payload = json.dumps(out, separators=(',', ':'), allow_nan=False) + '\n'
with tempfile.NamedTemporaryFile(mode='w', dir=root / 'data', prefix='.unit_impact', delete=False) as f:
    f.write(payload); tmp = f.name
os.replace(tmp, root / 'data/unit_impact.json')
for k, v in fit.items(): print(k, v)
print('unit_impact.json', len(payload) // 1024, 'KB; teams', len(T), 'slate', len(slate))
