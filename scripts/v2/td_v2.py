"""Prototype-only TD chance v2: deployed ATD prob + red-zone/goal-line shares (walk-forward-tested logistic), then 75/25 logit pool with market fair. TD props never Highlighted until audit passes."""
import os
RAW=os.environ.get('SL_RAW','/tmp/nflraw'); BL=os.environ.get('SL_BL','/tmp/bl')
import json,numpy as np,pandas as pd
R=json.load(open('scripts/v2/rz_results.json'));c=dict(zip(R['cols'],R['coef_full']));b0=R['int']
pl=pd.read_csv(RAW+'/players.csv',usecols=['gsis_id','espn_id'],dtype=str).dropna();E2G=dict(zip(pl.espn_id.str.replace(r'\.0$','',regex=True),pl.gsis_id))
P=pd.read_parquet(RAW+'/pbp_2026.parquet');P=P[(P.season_type=='REG')&(P.yardline_100<=20)&P.play_type.isin(['run','pass'])]
tr=P.groupby('posteam').size();g5=P[P.yardline_100<=5].groupby('posteam').size()
ru=P[P.play_type=='run'].groupby(['rusher_player_id','posteam']).size();r5=P[(P.play_type=='run')&(P.yardline_100<=5)].groupby(['rusher_player_id','posteam']).size();tg=P[P.play_type=='pass'].groupby(['receiver_player_id','posteam']).size()
A={r['aid']:r for r in json.load(open(BL+'/analyst_nfl.json'))['td_all']}
lg=lambda p:np.log(min(max(p,1e-4),1-1e-4)/(1-min(max(p,1e-4),1-1e-4)));ex=lambda z:1/(1+np.exp(-z))
d=json.load(open('data/v2.json'));W=0.75;n=0
for r in d['rows']:
  if r['market']!='Anytime TD': continue
  a=A.get(r['aid']);r['hl']=False
  if not a: continue
  t={'LAR':'LA','WSH':'WAS'}.get(r['team'],r['team']);g=E2G.get(r['aid']);T=tr.get(t,1);T5=g5.get(t,1)
  f={'lp':lg(a['prob']),'rzru':ru.get((g,t),0)/T,'gl':r5.get((g,t),0)/T5,'rztg':tg.get((g,t),0)/T,'litt':np.log((a.get('itt') or 22)/22)}
  v2=float(ex(b0+sum(c[k]*f[k] for k in c)));r['p_model_v1']=a['prob'];r['p_model_v2']=round(v2,4);r['rzsh']=[round(f['rzru'],3),round(f['gl'],3),round(f['rztg'],3)]
  r['prob']=round(float(ex(W*lg(r['fair'])+(1-W)*lg(v2))),4) if r['fair'] is not None else round(v2,4)
  r['src']='TD model v2 (red-zone) + 75% market blend' if r['fair'] is not None else 'TD model v2 (red-zone); no market fair'
  r['edge']=round(r['prob']-r['fair'],3) if r['fair'] is not None else None; n+=1
json.dump(d,open('data/v2.json','w'))
T=sorted([r for r in d['rows'] if r['market']=='Anytime TD' and r['edge'] is not None],key=lambda r:-r['edge'])
print('updated',n)
for r in T[:10]: print(f"{r['name']:22} v1 {r['p_model_v1']*100:5.1f} v2 {r['p_model_v2']*100:5.1f} fair {r['fair']*100:5.1f} ({r['fsrc']},{r['nb']}) final {r['prob']*100:5.1f} edge {r['edge']*100:+5.1f} best {r['bbook']} {r['best']}")
