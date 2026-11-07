#!/usr/bin/env python3
"""Display-only alternate floor dataset; no model/pick inputs modified."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'data'
def load(n):
 if n=='v2.json':return json.loads((D/'v2.json').read_text())
 if n=='nba_hub.json':return json.loads((D/'nba_hub.json').read_text())
 if n=='plogs_nba.json':return json.loads((D/'plogs_nba.json').read_text())
 raise ValueError('Unsupported data filename')
def build():
 SPORT='nfl'
 rows=[]
 if SPORT=='nfl':
  v=load('v2.json'); week=int(v['week']); updated=v['updated']
  cats={'Receiving yards':('receiving_yards',[10,15,20,25,30,40,50,60,70]),'Receptions':('receptions',[1,2,3,4,5,6,7]),'Rushing yards':('rushing_yards',[5,10,15,20,25,40,50,60,70]),'Passing yards':('passing_yards',[150,170,175,180,200,210,225,250,260]),'Rush + Rec yards':('combo',[20,40,60,80,100]),'Kicking points':('kick',[3,4,5,6,7,8])}
  for f in sorted((D/'players').glob('*.json')):
   p=json.load(open(f)); nxt=p.get('next') or {}
   if not nxt or p.get('team')=='FA': continue
   logs=sorted([g for g in p.get('log',[]) if g.get('s')==2026 and g.get('w',99)<=week],key=lambda g:g['w'],reverse=True)
   for cat,(stat,presets) in cats.items():
    if cat=='Passing yards' and p.get('pos')!='QB': continue
    if cat=='Kicking points' and p.get('pos')!='K': continue
    if cat!='Kicking points' and p.get('pos') not in ['QB','RB','WR','TE','FB']: continue
    games=[]
    for g in logs:
     value=g.get(stat)
     if stat=='combo': value=(g.get('rushing_yards') or 0)+(g.get('receiving_yards') or 0) if g.get('rushing_yards') is not None and g.get('receiving_yards') is not None else None
     if stat=='kick': value=3*g['fg_made']+g['pat_made'] if g.get('fg_made') is not None and g.get('pat_made') is not None else None
     games.append({'label':'W'+str(g['w'])+' '+str(g.get('o','')),'value':value,'dnp':g.get('snap')==0})
    if not any(g['value'] is not None for g in games): continue
    rows.append(dict(id=p['id'],name=p['name'],team=p['team'],pos=p['pos'],category=cat,presets=presets,games=games,opp=nxt.get('opp'),time=nxt.get('date'),status=(p.get('inj') or {}).get('status') or 'No designation in snapshot'))
 else:
  h=load('nba_hub.json'); logs=load('plogs_nba.json'); updated=h['updated']; week=None
  cats={'Points':('points',[5,10,15,20,25,30]),'Rebounds':('totalRebounds',[2,3,4,5,6,8,10]),'Assists':('assists',[1,2,3,4,5,6,8]),'Threes':('threePointFieldGoalsMade-threePointFieldGoalsAttempted',[1,2,3,4])}
  people={}
  injuries={str(x['id']):x.get('status') for x in h.get('injuries',[])}
  for unit in h.get('units',[]):
   for side in ['first','second']:
    for p in unit.get(side,{}).get('players',[]): people[str(p['id'])]=p
  for p in h.get('props',[]): people.setdefault(str(p['aid']),dict(id=p['aid'],name=p['player'],team=p['team'],pos=p.get('pos','Unknown')))
  for aid,p in people.items():
   slate=next((g for g in h['slate'] if p['team'] in [g.get('home'),g.get('away')]),{})
   gl=sorted([g for g in logs.get(aid,[]) if '2026-10-20'<=g.get('d','')<'2027-07-01'],key=lambda g:g['d'],reverse=True)
   for cat,(stat,presets) in cats.items():
    games=[dict(label=g['d']+' '+str(g.get('o','')),value=(g.get('s') or {}).get(stat),dnp=(g.get('s') or {}).get('minutes')==0) for g in gl]
    if not any(g['value'] is not None for g in games): continue
    rows.append(dict(id=aid,name=p['name'],team=p['team'],pos=p.get('pos','Unknown'),category=cat,presets=presets,games=games,opp=slate.get('away') if p['team']==slate.get('home') else slate.get('home'),time=slate.get('time'),status=injuries.get(aid) or p.get('status') or 'No designation in snapshot'))
 out=dict(window='2026 NFL through completed slate-week logs' if SPORT=='nfl' else '2026-10-20 through 2027-06-30',sport=SPORT,season='2026 NFL' if SPORT=='nfl' else '2026–27 NBA',updated=updated,categories=list(cats),rows=rows)
 (D/'low_hurdles_alternates.json').write_text(json.dumps(out,separators=(',',':'))+'\n')
 print(SPORT,len(rows),{c:sum(r['category']==c for r in rows) for c in cats})
if __name__=='__main__': build()
