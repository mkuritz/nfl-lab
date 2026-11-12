#!/usr/bin/env python3
"""Opportunity Board data: usage shares with/without each starting QB, weekly position-rank
movement (QB/WR/RB/TE), defensive pass-rush / coverage boards, and data-driven "why" notes.

Display-only. Reads only files already refreshed by the Hub update (data/players/*.json weekly logs,
data/nfl.json team names). No requests, no model/schedule/pricer changes. Every number is a count or a
ratio of counts from the weekly player logs; nothing is estimated. Missing values stay missing.
Output: data/usage_board.json (written atomically; a failed or empty run leaves the prior file).
"""
from pathlib import Path
from collections import defaultdict, Counter
import json, math, os, tempfile
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
CANON = {'LA': 'LAR', 'WAS': 'WSH'}
canon = lambda t: CANON.get(t, t)
VALID = set('ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LV LAC LAR MIA MIN NE NO NYG NYJ PHI PIT SF SEA TB TEN WSH'.split())
SKILL = {'QB', 'WR', 'RB', 'TE'}
EDGE_SLOTS = {'LDE', 'RDE', 'SLB', 'WLB'}
CB_SLOTS = {'LCB', 'RCB', 'NB'}
S_SLOTS = {'FS', 'SS'}

players = {}
for f in (root / 'data/players').glob('*.json'):
    try:
        p = json.loads(f.read_text())
    except Exception:
        continue
    if p.get('id') and p.get('log'):
        players[str(p['id'])] = p
if not players:
    raise SystemExit('No player logs; preserving prior output')

season = max((l['s'] for p in players.values() for l in p['log'] if isinstance(l.get('s'), int)), default=None)
if not season or not 2020 <= season <= datetime.now(timezone.utc).year:
    raise SystemExit('Bad season; preserving prior output')

nfl = json.loads((root / 'data/nfl.json').read_text())
nick = {}
for s in nfl.get('standings', []):
    nick[canon(s['team'])] = {'name': s['name'], 'nick': s['name'].split()[-1]}


def grp(p):
    pos = (p.get('pos') or '').upper(); g = (p.get('grp') or '').upper()
    return pos if pos in SKILL else g if g in SKILL else None


def games_of(p):
    return [l for l in p['log'] if l.get('s') == season and canon(l.get('t', '')) in VALID]


def played(l):
    return bool(l.get('snap') or l.get('targets') or l.get('carries') or l.get('attempts') or l.get('fantasy_points_ppr'))


def r1(x): return None if x is None else round(x, 1)
def r3(x): return None if x is None else round(x, 3)

# ---------- team games, starting QB, team totals ----------
teamgames = defaultdict(dict)         # team -> week -> info
for p in players.values():
    for l in games_of(p):
        t, w = canon(l['t']), l['w']
        info = teamgames[t].setdefault(w, {'w': w, 'g': l.get('g'), 'o': canon(l.get('o', '')), 'ratios': [], 'ca': 0.0, 'rz': 0.0, 'qb': None, 'qba': 0})
        info['ca'] += l.get('carries') or 0
        info['rz'] += l.get('rz') or 0
        ts = l.get('target_share')
        if ts and ts >= 0.04 and l.get('targets'):
            info['ratios'].append(round(l['targets'] / ts))
        if grp(p) == 'QB' and (l.get('attempts') or 0) > info['qba']:
            info['qba'] = l['attempts']; info['qb'] = str(p['id'])
for t, ws in teamgames.items():
    for w, info in ws.items():
        # Official per-game team target total = player targets / player target_share (modal value across players).
        info['tg'] = Counter(info['ratios']).most_common(1)[0][0] if info['ratios'] else None
        info['ca'] = int(info['ca']); info['rz'] = int(info['rz'])
maxw = max(w for ws in teamgames.values() for w in ws)
league_weeks = list(range(1, maxw + 1))

# ---------- A. usage ----------
usage_teams = {}
for t in sorted(teamgames):
    if t not in VALID: continue
    ws = sorted(teamgames[t])
    qbs = {}
    for w in ws:
        q = teamgames[t][w]['qb']
        if q: qbs.setdefault(q, players[q]['name'])
    rows = []
    for pid, p in players.items():
        gl = [l for l in games_of(p) if canon(l['t']) == t]
        if not gl: continue
        if sum((l.get('targets') or 0) + (l.get('carries') or 0) for l in gl) < 1: continue
        rows.append({'id': pid, 'n': p['name'], 'pos': grp(p) or p.get('pos'),
                     'g': [[l['w'], l.get('snap'), int(l.get('targets') or 0), int(l.get('carries') or 0), int(l.get('receiving_tds') or 0), int(l.get('rushing_tds') or 0), int(l.get('rz') or 0)] for l in sorted(gl, key=lambda x: x['w'])]})
    rows.sort(key=lambda r: -sum(x[2] + x[3] for x in r['g']))
    usage_teams[t] = {'name': nick.get(t, {}).get('name', t), 'nick': nick.get(t, {}).get('nick', t),
                      'games': [[w, teamgames[t][w]['o'], teamgames[t][w]['qb'], teamgames[t][w]['tg'], teamgames[t][w]['ca']] for w in ws],
                      'qbs': qbs, 'players': rows}

# ---------- B. rank movement (QB / WR / RB / TE) ----------
def team_windows(t, W):
    ws = [w for w in sorted(teamgames[t]) if w <= W]
    return ws[-3:], ws[:-3]


def fp_series(p):
    """Weekly PPR points. A logged game with usage but no points field is 0.0 (zero values are stripped upstream);
    weeks without a logged game stay None (bye / did not play)."""
    s = {}
    for l in games_of(p):
        if not played(l): continue
        s[l['w']] = l.get('fantasy_points_ppr') or 0.0
    return s


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


rank = {}
for pos in ('QB', 'WR', 'RB', 'TE'):
    cand = {}
    for pid, p in players.items():
        if grp(p) != pos: continue
        s = fp_series(p)
        if s: cand[pid] = s
    per = {'season': {}, 'form': {}}; ppg = {'season': {}, 'form': {}}
    for mode in per:
        for pid in cand: per[mode][pid] = [None] * maxw; ppg[mode][pid] = [None] * maxw
        for W in league_weeks:
            vals = {}
            for pid, s in cand.items():
                if mode == 'season':
                    xs = [v for w, v in s.items() if w <= W]
                    if len(xs) >= max(1, math.ceil(0.5 * W)): vals[pid] = sum(xs) / len(xs)
                else:
                    xs = [s[w] for w in (W - 2, W - 1, W) if w in s]
                    if len(xs) >= (2 if W >= 3 else 1): vals[pid] = sum(xs) / len(xs)
            order = sorted(vals.values(), reverse=True)
            for pid, v in vals.items():
                per[mode][pid][W - 1] = 1 + sum(1 for o in order if o > v + 1e-9)
                ppg[mode][pid][W - 1] = round(v, 2)
    keep = [pid for pid in cand if any((per[m][pid][i] or 99) <= 30 for m in per for i in range(maxw))]
    rank[pos] = {'cand': cand, 'per': per, 'ppg': ppg, 'keep': keep}


def usage_share(p, t, wk_list, key):
    """Player share of team total (targets or carries) in the team games he played inside wk_list."""
    num = den = 0
    for l in games_of(p):
        if l['w'] in wk_list and canon(l['t']) == t and played(l):
            den += teamgames[t][l['w']]['tg' if key == 'targets' else 'ca'] or 0
            num += l.get(key) or 0
    return (num / den) if den else None


def pct(x): return None if x is None else int(round(x * 100))


def why_skill(pid, pos, W):
    p = players[pid]; t = canon(p['team']) if canon(p.get('team', '')) in teamgames else None
    gl = [l for l in games_of(p) if l['w'] <= W]
    if not gl: return []
    t = canon(sorted(gl, key=lambda x: x['w'])[-1]['t'])
    rec, earl = team_windows(t, W)
    mine = {l['w']: l for l in gl if canon(l['t']) == t}
    R = [mine[w] for w in rec if w in mine and played(mine[w])]; E = [mine[w] for w in earl if w in mine and played(mine[w])]
    out = []
    fr = [l.get('fantasy_points_ppr') or 0 for l in R]; fe = [l.get('fantasy_points_ppr') or 0 for l in E]
    if R and E:
        a, b = sum(fr) / len(fr), sum(fe) / len(fe)
        out.append({'tag': 'Production', 'text': f'{a:.1f} PPR pts/game over the last {len(R)} played vs {b:.1f} in the {len(E)} before ({a - b:+.1f}).'})
    elif R:
        out.append({'tag': 'Production', 'text': f'{sum(fr) / len(fr):.1f} PPR pts/game over {len(R)} played; not enough earlier games to compare.'})
    sr, se = mean([l.get('snap') for l in R]), mean([l.get('snap') for l in E])
    if sr is not None and se is not None:
        out.append({'tag': 'Snaps', 'text': f'Offensive snap share {sr:.0f}% over the last {len(R)} vs {se:.0f}% before ({sr - se:+.0f} pts).'})
    if pos in ('WR', 'TE', 'RB'):
        a, b = usage_share(p, t, set(rec), 'targets'), usage_share(p, t, set(earl), 'targets')
        if a is not None and b is not None and (a > 0 or b > 0):
            out.append({'tag': 'Targets', 'text': f'Target share {pct(a)}% over the last {len(R)} vs {pct(b)}% before ({pct(a) - pct(b):+d} pts).'})
    if pos in ('RB', 'QB'):
        a, b = usage_share(p, t, set(rec), 'carries'), usage_share(p, t, set(earl), 'carries')
        if a is not None and b is not None and (a > 0 or b > 0) and pos == 'RB':
            out.append({'tag': 'Rushes', 'text': f'Share of team carries {pct(a)}% over the last {len(R)} vs {pct(b)}% before ({pct(a) - pct(b):+d} pts).'})
    if pos == 'QB':
        att = [l.get('attempts') or 0 for l in R]; epa = [l.get('passing_epa') for l in R if l.get('attempts')]
        ra = sum(att)
        if R and ra:
            out.append({'tag': 'Passing', 'text': f'{ra / len(R):.1f} attempts/game, {sum(l.get("passing_yards") or 0 for l in R) / len(R):.0f} pass yds/game, {sum(l.get("rushing_yards") or 0 for l in R) / len(R):.0f} rush yds/game over the last {len(R)} played.'})
        st_r = [w for w in rec if teamgames[t][w]['qb'] == pid]; st_e = [w for w in earl if teamgames[t][w]['qb'] == pid]
        if len(rec) and (st_r or st_e):
            out.append({'tag': 'QB', 'text': f'Started {len(st_r)} of the last {len(rec)} team games and {len(st_e)} of the {len(earl)} before.' })
    else:
        rq = [teamgames[t][w]['qb'] for w in rec]; eq = [teamgames[t][w]['qb'] for w in earl]
        if rq and eq and rq[-1] and Counter(x for x in eq if x).most_common(1) and rq[-1] != Counter(x for x in eq if x).most_common(1)[0][0]:
            old = Counter(x for x in eq if x).most_common(1)[0][0]
            n_new = sum(1 for x in rq if x == rq[-1])
            out.append({'tag': 'QB change', 'text': f'{t} switched starting QB: {players[old]["name"]} (most earlier starts) to {players[rq[-1]]["name"]} (started {n_new} of the last {len(rq)}).'})
    # teammate absence
    lost = []
    for qid, q in players.items():
        if qid == pid or canon(q.get('team', '')) != t or grp(q) not in ('WR', 'TE', 'RB'): continue
        ql = {l['w']: l for l in games_of(q) if canon(l['t']) == t}
        if len(earl) < 2: continue
        e_t = usage_share(q, t, set(earl), 'targets'); e_c = usage_share(q, t, set(earl), 'carries')
        big = (e_t is not None and e_t >= 0.15) or (e_c is not None and e_c >= 0.25 and grp(q) == 'RB')
        last2 = rec[-2:]
        absent = len(last2) == 2 and all((w not in ql) or not played(ql[w]) or (ql[w].get('snap') in (0, None) and not ql[w].get('targets') and not ql[w].get('carries')) for w in last2)
        if big and absent:
            inj = q.get('inj') or {}
            note = f' (current report: {inj["status"]})' if inj.get('current') and inj.get('status') else ''
            share = f'{pct(e_t)}% of targets' if (e_t or 0) >= 0.15 else f'{pct(e_c)}% of carries'
            lost.append(f'{q["name"]} ({grp(q)}, {share} earlier) has no recorded appearance in the last 2 team games{note}.')
    for s in lost[:2]: out.append({'tag': 'Teammate out', 'text': s})
    # red zone + TD
    rz_r = sum(l.get('rz') or 0 for l in R)
    team_rz = sum(teamgames[t][w]['rz'] for w in rec if w in mine and played(mine[w]))
    if rz_r and team_rz:
        out.append({'tag': 'Red zone', 'text': f'{rz_r} red-zone touches (rush + target) over the last {len(R)} played, {pct(rz_r / team_rz)}% of {t} red-zone touches in those games.'})
    td = sum((l.get('receiving_tds') or 0) + (l.get('rushing_tds') or 0) + (l.get('passing_tds') or 0) * (pos == 'QB') for l in R)
    if R and td:
        out.append({'tag': 'TDs', 'text': f'{int(td)} touchdowns over the last {len(R)} played.'})
    return out


def sparkdata(arr): return arr


rank_out = {'weeks': league_weeks, 'positions': {}}
for pos, d in rank.items():
    plist = []
    latest_top = set()
    for m in d['per']:
        latest_top |= {pid for pid in d['keep'] if (d['per'][m][pid][maxw - 1] or 99) <= 20}
    for pid in d['keep']:
        p = players[pid]
        lastg = sorted(games_of(p), key=lambda x: x['w'])[-1]
        item = {'id': pid, 'n': p['name'], 't': canon(lastg['t']), 'cur': canon(p.get('team', '')) if canon(p.get('team', '')) in VALID else None,
                'rk': {m: d['per'][m][pid] for m in d['per']}, 'ppg': {m: d['ppg'][m][pid] for m in d['ppg']},
                'fp': [d['cand'][pid].get(w) if w in d['cand'][pid] else None for w in league_weeks]}
        item['fp'] = [None if v is None else round(v, 1) for v in item['fp']]
        if pid in latest_top: item['why'] = why_skill(pid, pos, maxw)
        plist.append(item)
    rank_out['positions'][pos] = plist

# ---------- C. defense ----------
def def_group(p):
    pos = (p.get('pos') or '').upper(); dp = ((p.get('depth') or {}).get('pos') or '').upper()
    if pos in ('DE', 'DT', 'DL', 'NT', 'OLB'): return 'rush', ('OLB' if pos == 'OLB' else 'DL')
    if pos in ('LB', 'MLB', 'ILB') and dp in EDGE_SLOTS: return 'rush', ('DL' if dp in ('LDE', 'RDE') else 'OLB')
    if pos == 'CB' or (pos == 'DB' and dp in CB_SLOTS): return 'cov', 'CB'
    if pos in ('SAF', 'S', 'FS', 'SS') or (pos == 'DB' and dp in S_SLOTS): return 'cov', 'S'
    if pos == 'DB': return 'cov', 'DB'
    return None, None


def dgame(l):
    return {'sk': l.get('def_sacks') or 0, 'qh': l.get('def_qb_hits') or 0, 'tfl': l.get('def_tackles_for_loss') or 0,
            'int': l.get('def_interceptions') or 0, 'pd': l.get('def_pass_defended') or 0,
            'tkl': (l.get('def_tackles_solo') or 0) + (l.get('def_tackle_assists') or 0), 'snap': l.get('snap')}


KEY = {'rush': lambda a: (a['sk'], a['qh'], a['tfl']), 'cov': lambda a: (a['int'] + a['pd'], a['int'])}
dcand = {'rush': {}, 'cov': {}}
for pid, p in players.items():
    g, lab = def_group(p)
    if not g: continue
    gl = [l for l in games_of(p) if l.get('snap') is not None or any(l.get(k) for k in ('def_sacks', 'def_interceptions', 'def_pass_defended', 'def_qb_hits'))]
    if gl: dcand[g][pid] = (lab, {l['w']: dgame(l) for l in gl}, canon(sorted(gl, key=lambda x: x['w'])[-1]['t']))


def cum(ws, W):
    a = Counter()
    for w, g in ws.items():
        if w <= W:
            for k, v in g.items():
                if k != 'snap': a[k] += v
    return a


def tot(g, ws, W):
    return KEY[g](cum(ws, W))


def_out = {}
for g, cands in dcand.items():
    ranks = {pid: [None] * maxw for pid in cands}
    for W in league_weeks:
        keys = {pid: tot(g, c[1], W) for pid, c in cands.items()}
        pos_keys = [k for k in keys.values() if k[0] > 0]
        for pid, k in keys.items():
            if k[0] > 0: ranks[pid][W - 1] = 1 + sum(1 for o in pos_keys if o > k)
    keep = [pid for pid in cands if (ranks[pid][maxw - 1] or 99) <= 30 or any((r or 99) <= 12 for r in ranks[pid])]
    items = []
    for pid in keep:
        lab, ws, t = cands[pid]; p = players[pid]
        rec_w, earl_w = team_windows(t, maxw) if t in teamgames else ([], [])
        c_all = cum(ws, maxw)
        item = {'id': pid, 'n': p['name'], 't': t, 'lab': lab, 'rk': ranks[pid],
                'tot': {k: round(c_all[k], 1) if k in ('sk',) else int(c_all[k]) for k in ('sk', 'qh', 'tfl', 'int', 'pd', 'tkl')},
                'snap': r1(mean([x['snap'] for x in ws.values()])),
                'wk': [[w, round(ws[w]['sk'], 1), ws[w]['qh'], ws[w]['tfl'], ws[w]['int'], ws[w]['pd'], ws[w]['snap']] if w in ws else None for w in league_weeks]}
        if (ranks[pid][maxw - 1] or 99) <= 20:
            why = []
            R = [ws[w] for w in rec_w if w in ws]; E = [ws[w] for w in earl_w if w in ws]
            if g == 'rush':
                fmt = lambda xs, k: sum(x[k] for x in xs) / len(xs)
                if R and E:
                    why.append({'tag': 'Production', 'text': f'{fmt(R, "sk"):.2f} sacks and {fmt(R, "qh"):.2f} QB hits per game over the last {len(R)} played vs {fmt(E, "sk"):.2f} and {fmt(E, "qh"):.2f} in the {len(E)} before.'})
                elif R:
                    why.append({'tag': 'Production', 'text': f'{sum(x["sk"] for x in R):g} sacks and {sum(x["qh"] for x in R)} QB hits over {len(R)} played.'})
            else:
                fmt = lambda xs, k: sum(x[k] for x in xs) / len(xs)
                if R and E:
                    why.append({'tag': 'Production', 'text': f'{fmt(R, "int"):.2f} INT and {fmt(R, "pd"):.2f} passes defended per game over the last {len(R)} played vs {fmt(E, "int"):.2f} and {fmt(E, "pd"):.2f} in the {len(E)} before.'})
                elif R:
                    why.append({'tag': 'Production', 'text': f'{sum(x["int"] for x in R)} INT and {sum(x["pd"] for x in R)} passes defended over {len(R)} played.'})
            sr, se = mean([x['snap'] for x in R]), mean([x['snap'] for x in E])
            if sr is not None and se is not None:
                why.append({'tag': 'Snaps', 'text': f'Defensive snap share {sr:.0f}% over the last {len(R)} vs {se:.0f}% before ({sr - se:+.0f} pts).'})
            slot = (p.get('depth') or {}).get('pos')
            if slot: why.append({'tag': 'Role', 'text': f'Listed at {slot} on the current depth chart.'})
            gone = []
            for qid, (qlab, qws, qt) in cands.items():
                if qid == pid or qt != t: continue
                if canon(players[qid].get('team', '')) != t: continue
                es = mean([qws[w]['snap'] for w in earl_w if w in qws])
                last2 = rec_w[-2:]
                if es is not None and es >= 50 and len(earl_w) >= 2 and len(last2) == 2 and not any(w in qws and (qws[w]['snap'] or 0) > 0 for w in last2):
                    inj = players[qid].get('inj') or {}
                    note = f' (current report: {inj["status"]})' if inj.get('current') and inj.get('status') else ''
                    gone.append(f'{players[qid]["name"]} ({qlab}, {es:.0f}% of snaps earlier) has no recorded snaps in the last 2 team games{note}.')
            for s in gone[:2]: why.append({'tag': 'Teammate out', 'text': s})
            item['why'] = why
        items.append(item)
    def_out[g] = items

out = {'season': season, 'through_week': maxw,
       'definition': 'Counts and ratios from weekly player logs. Team target total per game = player targets / player target share. Starting QB = the team QB with the most pass attempts in that game. Snap % = offensive snap share (defensive for defenders).',
       'usage': {'teams': usage_teams},
       'rank': rank_out,
       'defense': def_out,
       'gaps': ['Pass-rush pressures are not in our data; QB hits are shown instead.', 'Snap % is missing for some player-weeks and is left blank, never zero.', 'Rank movement is descriptive (points scored), not a forecast.']}
if not usage_teams:
    raise SystemExit('Empty usage; preserving prior output')
out['derived_at'] = datetime.now(timezone.utc).isoformat()
payload = json.dumps(out, separators=(',', ':'), allow_nan=False) + '\n'
with tempfile.NamedTemporaryFile(mode='w', dir=root / 'data', prefix='.usage_board', delete=False) as f:
    f.write(payload); tmp = f.name
os.replace(tmp, root / 'data/usage_board.json')
print('usage_board.json', len(payload) // 1024, 'KB; teams', len(usage_teams), 'through week', maxw)
