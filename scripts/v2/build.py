"""Build data/v2.json for the NFL Hub v2 prototype from our own feeds only."""
import os
RAW=os.environ.get('SL_RAW','/tmp/nflraw'); BL=os.environ.get('SL_BL','/tmp/bl')
import json,os,collections,statistics as S
NL='data'; BL=os.environ.get('SL_BL','/tmp/bl')
L=lambda p:json.load(open(p))
props=L(BL+'/props_nfl.json'); games={g['id']:g for g in L(BL+'/games_nfl.json')}
dvp=L(BL+'/nfl_dvp.json')['teams']; an=L(BL+'/analyst_nfl.json'); nfl=L(NL+'/nfl.json')
atd={r['aid']:r for r in an['td_all']}
LOGO={}
for g in nfl['games']:
  for s in ('home','away'): LOGO[g[s]['abbr']]=g[s]['logo']
for s in nfl['standings']: LOGO.setdefault(s['team'],s['logo'])
MK={'Receiving Yards':['receiving_yards'],'Receptions':['receptions'],'Rushing Yards':['rushing_yards'],'Carries':['carries'],
    'Passing Yards':['passing_yards'],'Rushing Plus Receiving Yards':['rushing_yards','receiving_yards'],'Anytime TD':['rushing_tds','receiving_tds'],'Pass Completions':['completions'],'Passing Attempts':['attempts']}
DVK={'Receiving Yards':'yds','Receptions':'rec','Rushing Yards':'yds','Rushing Plus Receiving Yards':'yds','Passing Yards':'yds','Anytime TD':'td','Carries':'yds','Pass Completions':'yds','Passing Attempts':'yds'}
lg={}
for pos in ('QB','RB','WR','TE'):
  for k in ('yds','rec','td','tgt'):
    v=[t[pos][k] for t in dvp.values() if pos in t and k in t[pos]]
    if v: lg[(pos,k)]=S.mean(v)
def grade(r):
  if r is None: return None
  return 'GREAT' if r>=1.12 else 'GOOD' if r>=1.04 else 'NEUTRAL' if r>=.96 else 'TOUGH' if r>=.88 else 'BAD'
pc={}
def player(aid):
  if aid not in pc:
    try: pc[aid]=L(f'{NL}/players/{aid}.json')
    except Exception: pc[aid]=None
  return pc[aid]
out=[]; teams_inj=collections.defaultdict(list)
for f in os.listdir(NL+'/players'):
  p=L(f'{NL}/players/{f}')
  if p.get('inj') and p['grp']!='DEF' or (p.get('inj') and p['pos'] in('QB','RB','WR','TE','K')):
    pass
  if p.get('inj'): teams_inj[p['team']].append({'n':p['name'],'pos':p['pos'],'st':p['inj']['status'],'d':p['inj'].get('detail'),'dt':p['inj'].get('date'),'id':p['id']})
for r in props:
  if r['market'] not in MK or r['pos'] not in ('QB','RB','WR','TE'): continue
  p=player(r['aid'])
  if not p: continue
  g=games.get(r['game'],{}); keys=MK[r['market']]
  logs=[x for x in p['log'] if x['s']==2026]+[x for x in p['log'] if x['s']!=2026]
  vals=[{'w':x['w'],'s':x['s'],'o':x['o'],'v':round(sum(x.get(k,0) or 0 for k in keys),1)} for x in logs][:10]
  line=r['line']; hit=sum(1 for v in vals if v['v']>line); n=len(vals)
  x=r.get('x') or {}; h10,n10=(x.get('l10') or [0,0])[:2]; hs,ns=(x.get('szn') or [0,0])[:2]
  avg=round(S.mean([v['v'] for v in vals]),1) if vals else None
  if r['market']=='Anytime TD':
    a=atd.get(r['aid']); prob=a['prob'] if a else None; src='ATD model'
    fair=a.get('mkt_nv') if a else None; nb=a.get('n_books') if a else None; best=a.get('best') if a else None; bbook=a.get('best_book') if a else None
  else:
    prob=round((h10+hs)/(n10+ns),3) if n10+ns>=5 else None; src='hit-rate blend'; fair=nb=best=bbook=None
  edge=round(prob-fair,3) if (prob is not None and fair is not None and (nb or 0)>=2) else None
  pos=r['pos']; dk=DVK[r['market']]; opp=r['oa']; dv=dvp.get(opp,{}).get(pos)
  srk=(sorted(t[pos][dk] for t in dvp.values() if pos in t and dk in t[pos]).index(dv[dk])+1) if dv and dk in dv else None
  ratio=(dv[dk]/lg[(pos,dk)]) if dv and dk in dv and lg.get((pos,dk)) else None
  s26=[x for x in p['log'] if x['s']==2026]
  ts=[x.get('target_share') for x in s26 if x.get('target_share') is not None]
  sn=[x.get('snap') for x in s26 if x.get('snap') is not None]
  rz=sum(x.get('rz',0) or 0 for x in s26)
  def m(a): return round(S.mean(a),3) if a else None
  avgs={k:m([x.get(k,0) or 0 for x in s26[:10]]) for k in ('receiving_yards','receptions','targets','rushing_yards','carries','passing_yards','completions','attempts')}
  avgs['td']=m([(x.get('rushing_tds',0) or 0)+(x.get('receiving_tds',0) or 0) for x in s26])
  ins=[]
  if len(ts)>=4:
    a3,ss=S.mean(ts[:3]),S.mean(ts)
    ins.append({'h':'Target share '+('rising' if a3>ss+.02 else 'falling' if a3<ss-.02 else 'steady'),'t':f"{p['name']} has a {a3*100:.1f}% target share over his last 3 games, vs {ss*100:.1f}% across {len(ts)} games this season.",'tone':'up' if a3>ss+.02 else 'down' if a3<ss-.02 else 'flat'})
  if dv and dk in dv:
    rk=srk; unit={'yds':'yards','rec':'receptions','td':'TDs','tgt':'targets'}[dk]
    ins.append({'h':f"{opp} ranks {rk} of 32 vs {pos}s",'t':f"{opp} allows {dv[dk]:.1f} {unit} per game to {pos}s, vs a league average of {lg[(pos,dk)]:.1f} ({(ratio-1)*100:+.0f}%).",'tone':'up' if ratio>1.04 else 'down' if ratio<.96 else 'flat'})
  if len(sn)>=4:
    a3,ss=S.mean(sn[:3]),S.mean(sn)
    if abs(a3-ss)>=5: ins.append({'h':'Snap share '+('up' if a3>ss else 'down'),'t':f"He has played {a3:.0f}% of snaps over his last 3 games, vs {ss:.0f}% on the season.",'tone':'up' if a3>ss else 'down'})
  if n: ins.append({'h':f"Over {line} in {hit} of last {n}",'t':f"He has gone over {line} {r['market'].lower()} in {hit} of his last {n} games, averaging {avg}.",'tone':'up' if hit/n>=.6 else 'down' if hit/n<=.4 else 'flat'})
  if r.get('open') is not None and r['open']!=line:
    ins.append({'h':'Line moved '+('up' if line>r['open'] else 'down'),'t':f"The line opened at {r['open']} and now sits at {line}.",'tone':'up' if line>r['open'] else 'down'})
  for i in (r.get('inj') or [])[:2]:
    if i['status'] in ('Out','Injured Reserve','Doubtful'): ins.append({'h':f"{i['name']} {i['status'].lower()}",'t':f"Teammate {i['name']} ({i['pos']}) is listed {i['status']}, which frees up {i['pos']} usage on {r['team']}.",'tone':'up'})
  if rz>=3 and r['market']=='Anytime TD': ins.append({'h':f"{rz} red-zone opportunities",'t':f"He has {rz} red-zone opportunities across {len(s26)} games this season.",'tone':'up'})
  if a and r['market']=='Anytime TD' and a.get('itt'): ins.append({'h':f"Team total {a['itt']}",'t':f"{r['team']} is implied for {a['itt']} points, vs a slate average of {an['slate_avg_itt']:.1f}.",'tone':'up' if a['itt']>an['slate_avg_itt'] else 'down'}) if (a:=atd.get(r['aid'])) else None
  wx=g.get('wx') or {}
  out.append({'aid':r['aid'],'name':r['player'],'team':r['team'],'pos':pos,'opp':r['opp'],'oa':opp,'home':r['home'],'time':r['time'],'game':r['game'],
   'head':p.get('head'),'num':p.get('num'),'inj':p.get('inj') and {'st':p['inj']['status'],'d':p['inj'].get('detail')},
   'market':r['market'],'line':line,'open':r.get('open'),'prob':prob,'src':src,'fair':fair,'nb':nb,'best':best,'bbook':bbook,'edge':edge,
   'grade':grade(ratio),'ratio':ratio and round(ratio,3),'dvr':srk,'hit':[hit,n],'avg':avg,'vals':vals,'avgs':avgs,
   'ts':[round(t,3) for t in ts[:8]],'snap':sn[:8],'ins':ins[:6],'hl':bool(edge is not None and edge>=.03) or bool(prob and prob>=.6 and n>=5 and hit/n>=.6),
   'wx':{'dome':wx.get('dome'),'temp':wx.get('temp'),'wind':wx.get('wind'),'pop':wx.get('pop')},'gs':r.get('gs')})
json.dump({'updated':max(L(NL+'/meta.json').get('updated',''),''),'week':nfl.get('week'),'logos':LOGO,'inj':teams_inj,'rows':out,
  'lg':{f'{a}|{b}':round(v,2) for (a,b),v in lg.items()}},open('data/v2.json','w'))
print(len(out),collections.Counter(r['market'] for r in out),sum(r['hl'] for r in out),sum(r['edge'] is not None for r in out))
# season totals + positional ranks (2026, from our player logs)
ST={'QB':['passing_yards','passing_tds','rushing_yards','fantasy_points_ppr'],'RB':['rushing_yards','rushing_tds','receptions','fantasy_points_ppr'],
    'WR':['receiving_yards','receptions','targets','fantasy_points_ppr'],'TE':['receiving_yards','receptions','targets','fantasy_points_ppr']}
tot=collections.defaultdict(dict)
for f in os.listdir(NL+'/players'):
  p=L(f'{NL}/players/{f}')
  if p['pos'] not in ST: continue
  s=[x for x in p['log'] if x['s']==2026]
  if not s: continue
  tot[p['pos']][p['id']]={k:round(sum(x.get(k,0) or 0 for x in s),1) for k in ST[p['pos']]}
hero={}
for r in out:
  pos=r['pos'];me=tot[pos].get(r['aid'])
  if not me or r['aid'] in hero: continue
  tiles=[]
  for k in ST[pos]:
    vs=sorted((v[k] for v in tot[pos].values()),reverse=True); tiles.append({'k':k,'v':me[k],'rk':vs.index(me[k])+1,'of':len(vs)})
  p=player(r['aid']); hero[r['aid']]={'tiles':tiles,'age':p.get('age'),'exp':p.get('exp'),'college':p.get('college'),'draft':p.get('draft'),'depth':p.get('depth'),'news':p.get('news',[])[:3]}
# Compute PFF-style Defensive Funnel Tags & Trench Advantage Badges from nfl_dvp.json + teams_v2.json
try:
  _dvp_full = L(BL+'/nfl_dvp.json')
  _tv2 = L('data/teams_v2.json')
  _u = _tv2.get('units', {}); _ol_map = {x['t']: x for x in _tv2.get('ol', [])}
  _nt = lambda t: {'LAR': 'LA', 'WSH': 'WAS'}.get(t, t)
  _tf = {}
  for _tm, _d in _dvp_full.get('teams', {}).items():
    _ut = _nt(_tm); _cov = _u.get('Coverage', {}).get(_ut, 50); _rund = _u.get('Run defense', {}).get(_ut, 50); _pr = _u.get('Pass rush', {}).get(_ut, 50)
    _qb, _rb, _wr, _te = _d.get('QB', {}), _d.get('RB', {}), _d.get('WR', {}), _d.get('TE', {})
    _tgs = []
    if (_cov <= 42 or _qb.get('r', 16) >= 22 or _wr.get('r', 16) >= 22) and (_rund - _cov >= 14 or _qb.get('r', 16) - _rb.get('r', 16) >= 6):
      _tgs.append({'tag': 'Pass Funnel', 'kind': 'pass', 'detail': f"Pass D #{_qb.get('r',24)} vs Run D #{_rb.get('r',10)}"})
    elif (_rund <= 42 or _rb.get('r', 16) >= 22) and (_cov - _rund >= 14 or _rb.get('r', 16) - _qb.get('r', 16) >= 6):
      _tgs.append({'tag': 'Run Funnel', 'kind': 'run', 'detail': f"Run D #{_rb.get('r',24)} ({_rb.get('yds',125):.0f} yds/g) vs Pass D #{_qb.get('r',12)}"})
    if _te.get('r', 16) >= 23 or _te.get('yds', 0) >= 60 or _te.get('rec', 0) >= 6.0:
      _tgs.append({'tag': 'TE Funnel', 'kind': 'te', 'detail': f"#{_te.get('r',25)} vs TE ({_te.get('yds',0):.0f} yds, {_te.get('rec',0):.1f} rec/g)"})
    _wrec, _wyds = _wr.get('rec', 0) or 0, _wr.get('yds', 0) or 0
    _ypr = _wyds / max(1.0, _wrec)
    if _wrec >= 8.6 and (_wr.get('r', 16) >= 19 or _ypr <= 15.2):
      _tgs.append({'tag': 'Slot WR Vulnerable', 'kind': 'slot', 'detail': f"{_wrec:.1f} WR catches/g allowed (#{_wr.get('r',22)})"})
    if (_ypr >= 15.3 and _wyds >= 142) or (_qb.get('yds', 0) >= 252 and _wr.get('r', 16) >= 21):
      _tgs.append({'tag': 'Deep Ball Vulnerable', 'kind': 'deep', 'detail': f"{_ypr:.1f} yds/rec to WRs · {_qb.get('yds',0):.0f} pass yds/g"})
    _ttd = (_qb.get('td', 0) or 0) + (_rb.get('td', 0) or 0)
    if _ttd >= 2.55 or _qb.get('td', 0) >= 2.0 or _rb.get('td', 0) >= 1.15:
      _tgs.append({'tag': 'Red-Zone TD Sieve', 'kind': 'rz', 'detail': f"{_ttd:.1f} off TDs/g allowed"})
    if _pr <= 32: _tgs.append({'tag': 'Clean Pocket Def', 'kind': 'trench', 'detail': f"Pass rush {_pr}th pct"})
    _d['funnels'] = _tgs
    _tf[_tm] = {'tags': _tgs, 'cov_pct': _cov, 'rund_pct': _rund, 'pr_pct': _pr}
  for _k in list(_tf.keys()):
    if _k == 'LAR': _tf['LA'] = _tf[_k]
    if _k == 'LA': _tf['LAR'] = _tf[_k]
    if _k == 'WSH': _tf['WAS'] = _tf[_k]
    if _k == 'WAS': _tf['WSH'] = _tf[_k]
  json.dump(_dvp_full, open('data/nfl_dvp.json', 'w'), separators=(',', ':'))
except Exception as _e:
  print('funnel build warn:', _e); _tf = {}; _ol_map = {}
d=json.load(open('data/v2.json')); d['hero']=hero; json.dump(d,open('data/v2.json','w')); print('hero',len(hero))
try:
  d=json.load(open('data/v2.json'))
  _nt = lambda t: {'LAR': 'LA', 'WSH': 'WAS'}.get(t, t)
  for _r in d.get('rows', []):
    _pos, _tm, _opp = _r.get('pos'), _nt(_r.get('team')), _r.get('oa')
    _fobj = _tf.get(_opp) or _tf.get(_nt(_opp)) or {'tags': [], 'cov_pct': 50, 'rund_pct': 50, 'pr_pct': 50}
    _ol = _ol_map.get(_tm) or {}; _pb, _rb, _aly = _ol.get('pb', 50), _ol.get('rb', 50), _ol.get('aly', 4.0)
    _pr, _rund = _fobj['pr_pct'], _fobj['rund_pct']
    _b = [t for t in _fobj['tags'] if (_pos=='QB' and t['tag'] in ('Pass Funnel','Deep Ball Vulnerable','Slot WR Vulnerable','Red-Zone TD Sieve','TE Funnel')) or (_pos=='WR' and t['tag'] in ('Pass Funnel','Slot WR Vulnerable','Deep Ball Vulnerable','Red-Zone TD Sieve')) or (_pos=='TE' and t['tag'] in ('TE Funnel','Pass Funnel','Slot WR Vulnerable','Red-Zone TD Sieve')) or (_pos=='RB' and t['tag'] in ('Run Funnel','Red-Zone TD Sieve','Pass Funnel'))]
    if _pos in ('QB','WR','TE') and (_pb - _pr >= 12 or _pr <= 30):
      _b.append({'tag': f"Trench: Clean Pocket (+{max(8,_pb-_pr)} PB vs PR)", 'kind': 'trench_up', 'detail': f"{_r.get('team')} OL Pass Block {_pb}th pct vs {_opp} Pass Rush {_pr}th pct"})
    elif _pos == 'RB' and (_rb - _rund >= 10 or _rund <= 32):
      _b.append({'tag': f"Trench: OL Run Push ({_aly:.1f} ALY)", 'kind': 'trench_up', 'detail': f"{_r.get('team')} OL Run Block {_rb}th pct ({_aly:.2f} ALY) vs {_opp} Run D {_rund}th pct"})
    _r['funnels'] = _b[:3]
  d['team_funnels'] = _tf
  json.dump(d, open('data/v2.json', 'w'), separators=(',', ':'))
except Exception as _e: print('v2 funnel attach warn:', _e)
