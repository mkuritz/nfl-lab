"""Team/player aggregates from public nflverse play-by-play -> data/pbp_v2.json, plus power rankings, Sports Labs unit ratings and OL table."""
import os
RAW=os.environ.get('SL_RAW','/tmp/nflraw'); BL=os.environ.get('SL_BL','/tmp/bl')
import pandas as pd,numpy as np,json
out={'tw':{},'pw':{},'seasons':[]}
DIV={'AFC East':'BUF MIA NE NYJ','AFC North':'BAL CIN CLE PIT','AFC South':'HOU IND JAX TEN','AFC West':'DEN KC LV LAC','NFC East':'DAL NYG PHI WAS','NFC North':'CHI DET GB MIN','NFC South':'ATL CAR NO TB','NFC West':'ARI LA SF SEA'}
TD={t:d for d,s in DIV.items() for t in s.split()}
for y in (2025,2026):
  d=pd.read_parquet(f'{RAW}/pbp_{y}.parquet'); d=d[d.season_type=='REG'] if 'season_type' in d else d
  sc=d[(d.play_type.isin(['pass','run']))&d.epa.notna()&d.posteam.notna()].copy()
  sc['stuff']=((sc.play_type=='run')&(sc.yards_gained<=0)).astype(int)
  r=sc.yards_gained.clip(-20,100); sc['aly']=np.where(sc.play_type=='run',np.where(r<0,1.2*r,np.where(r<=4,r,np.where(r<=10,4+.5*(r-4),7))),0)
  sc['ispass']=(sc.play_type=='pass').astype(int); sc['isrun']=1-sc.ispass
  rows={}
  for (t,w),g in sc.groupby(['posteam','week']):
    p=g[g.ispass==1];u=g[g.isrun==1]
    rows[f'{t}|{w}']=dict(n=len(g),epa=g.epa.sum(),suc=g.success.sum(),pn=len(p),pepa=p.epa.sum(),psuc=p.success.sum(),rn=len(u),repa=u.epa.sum(),rsuc=u.success.sum(),
      sk=int(p.sack.sum()),qh=int(p.qb_hit.sum()),stuff=int(u.stuff.sum()),aly=u.aly.sum(),ay=p.air_yards.fillna(0).sum(),att=int(p.pass_attempt.sum()),
      qbepa=g.qb_epa.sum(),opp=g.defteam.iloc[0])
  for (t,w),g in sc.groupby(['defteam','week']):
    p=g[g.ispass==1];u=g[g.isrun==1];k=f'{t}|{w}';R=rows.setdefault(k,{})
    R.update(dn=len(g),depa=g.epa.sum(),dsuc=g.success.sum(),dpn=len(p),dpepa=p.epa.sum(),drn=len(u),drepa=u.epa.sum(),dsk=int(p.sack.sum()),dqh=int(p.qb_hit.sum()),dstuff=int(u.stuff.sum()))
  st=d[(d.special_teams_play==1)&d.epa.notna()]
  for (t,w),g in st.groupby(['posteam','week']): rows.setdefault(f'{t}|{w}',{})['stepa']=rows.get(f'{t}|{w}',{}).get('stepa',0)+g.epa.sum()
  for (t,w),g in st.groupby(['defteam','week']): rows.setdefault(f'{t}|{w}',{})['stepa']=rows.get(f'{t}|{w}',{}).get('stepa',0)-g.epa.sum()
  # gap
  rr=sc[sc.isrun==1].copy(); rr['dir']=np.where(rr.run_location=='middle','middle',rr.run_location.fillna('?')+' '+rr.run_gap.fillna('?'))
  for (t,w,dr),g in rr.groupby(['posteam','week','dir']): rows[f'{t}|{w}'].setdefault('gap',{})[dr]=[len(g),round(g.epa.sum(),2)]
  out['tw'][y]={k:{a:(round(float(b),3) if isinstance(b,(float,np.floating)) else b) for a,b in v.items()} for k,v in rows.items()}
  # players
  tt=sc[sc.ispass==1].groupby(['posteam','week']).pass_attempt.sum()
  P={}
  rec=sc[(sc.ispass==1)&sc.receiver_player_id.notna()]
  for (pid,t,w),g in rec.groupby(['receiver_player_id','posteam','week']):
    P[f'{pid}|{w}']=dict(nm=g.receiver_player_name.iloc[0],t=t,tg=len(g),ttg=int(tt.get((t,w),0)),ay=float(g.air_yards.fillna(0).sum()),repa=round(float(g.epa.sum()),2))
  for (pid,t,w),g in sc[(sc.isrun==1)&sc.rusher_player_id.notna()].groupby(['rusher_player_id','posteam','week']):
    P.setdefault(f'{pid}|{w}',dict(nm=g.rusher_player_name.iloc[0],t=t)).update(ca=len(g),ruepa=round(float(g.epa.sum()),2),rusuc=int(g.success.sum()))
  for (pid,t,w),g in sc[(sc.ispass==1)&sc.passer_player_id.notna()].groupby(['passer_player_id','posteam','week']):
    P.setdefault(f'{pid}|{w}',dict(nm=g.passer_player_name.iloc[0],t=t)).update(db=len(g),paepa=round(float(g.epa.sum()),2),pasuc=int(g.success.sum()))
  out['pw'][y]=P; out['seasons'].append(y)
  out.setdefault('maxw',{})[y]=int(sc.week.max())
out['div']=DIV
json.dump(out,open('data/pbp_v2.json','w'),separators=(',',':'))
# ---- power rankings / ratings (2026)
y=2026;T=out['tw'][y];teams=sorted({k.split('|')[0] for k in T})
def agg(t,keys):
  s={}
  for k,v in T.items():
    if k.split('|')[0]==t:
      for a in keys: s[a]=s.get(a,0)+(v.get(a) or 0)
  return s
K=['n','epa','suc','pn','pepa','psuc','rn','repa','rsuc','sk','qh','stuff','aly','dn','depa','dsuc','dpn','dpepa','drn','drepa','dsk','dqh','dstuff','stepa','qbepa']
A={t:agg(t,K) for t in teams}; G={t:len({k for k in T if k.startswith(t+'|') and T[k].get('n')}) for t in teams}
rat={t:round((A[t]['epa']-A[t]['depa']+A[t]['stepa'])/G[t],2) for t in teams}
m=np.mean(list(rat.values())); rat={t:round(v-m,2) for t,v in rat.items()}
sch=pd.read_csv(RAW+'/games.csv'); sch=sch[(sch.season==y)&(sch.game_type=='REG')]
fix=lambda x:{'LAR':'LA'}.get(x,x)
played=sch[sch.result.notna()];rem=sch[sch.result.isna()]
W={t:0.0 for t in teams}
for _,g in played.iterrows():
  if g.result>0: W[g.home_team]+=1
  elif g.result<0: W[g.away_team]+=1
  else: W[g.home_team]+=.5;W[g.away_team]+=.5
def sos(df,t): o=[g.away_team if g.home_team==t else g.home_team for _,g in df.iterrows() if t in (g.home_team,g.away_team)]; return round(float(np.mean([rat[x] for x in o])),2) if o else None
rng=np.random.default_rng(7);N=10000;tix={t:i for i,t in enumerate(teams)}
wins=np.tile(np.array([W[t] for t in teams]),(N,1))
for _,g in rem.iterrows():
  h,a=g.home_team,g.away_team; mu=rat[h]-rat[a]+1.5; hw=rng.normal(mu,13.5,N)>0
  wins[:,tix[h]]+=hw; wins[:,tix[a]]+=~hw
noise=rng.random(wins.shape)*1e-3; ww=wins+noise
mp=np.zeros(len(teams));wd=np.zeros(len(teams));wc=np.zeros(len(teams));
for conf in ('AFC','NFC'):
  ci=[tix[t] for t in teams if TD.get(t,'').startswith(conf)]
  divs=[d for d in DIV if d.startswith(conf)]
  dw=[]
  for dv in divs:
    di=[tix[t] for t in DIV[dv].split()]
    win=np.array(di)[ww[:,di].argmax(1)]; dw.append(win); np.add.at(wd,win,1)
  dw=np.stack(dw,1)
  for s in range(N):
    rest=[i for i in ci if i not in dw[s]]; wcs=sorted(rest,key=lambda i:-ww[s,i])[:3]
    for i in list(dw[s])+wcs: mp[i]+=1
    best=max(dw[s],key=lambda i:ww[s,i]); wc[best]+=.5   # top seed proxy
  # conference champ approx: weighted by rating among playoff teams -> skip heavy bracket; use top-seed*bracket proxy below
pr=[]
for t in teams:
  i=tix[t]; pr.append(dict(t=t,rat=rat[t],qb=round(A[t]['qbepa']/G[t],2),sosp=sos(played,t),sosr=sos(rem,t),w=round(float(wins[:,i].mean()),1),
    po=round(mp[i]/N,3),div=round(wd[i]/N,3),rec=f"{int(W[t])}-{G[t]-int(W[t])}"))
# conference win: simulate bracket quickly by rating-weighted single elim among playoff probabilities ~ use logistic of rating
for conf in ('AFC','NFC'):
  rows=[r for r in pr if TD[r['t']].startswith(conf)]
  sc_=np.array([r['po']*np.exp(r['rat']/4) for r in rows]); sc_=sc_**1.6; sc_/=sc_.sum()
  for r,v in zip(rows,sc_): r['conf']=round(float(v),3)
pr.sort(key=lambda r:-r['rat'])
# unit ratings percentiles
def pct(vals,hi=True):
  s=pd.Series(vals).rank(pct=True); s=s if hi else 1-s+1/len(s); return {k:int(round(v*100)) for k,v in s.items()}
U={'Pass':pct({t:A[t]['pepa']/A[t]['pn'] for t in teams}),'Rush':pct({t:A[t]['repa']/A[t]['rn'] for t in teams}),
   'Receiving':pct({t:A[t]['psuc']/A[t]['pn'] for t in teams}),'Pass block':pct({t:(A[t]['sk']+.5*A[t]['qh'])/A[t]['pn'] for t in teams},False),
   'Pass rush':pct({t:(A[t]['dsk']+.5*A[t]['dqh'])/A[t]['dpn'] for t in teams}),'Run defense':pct({t:A[t]['drepa']/A[t]['drn'] for t in teams},False),
   'Coverage':pct({t:A[t]['dpepa']/A[t]['dpn'] for t in teams},False),'Special teams':pct({t:A[t]['stepa'] for t in teams})}
# OL table
ol=[]
for t in teams:
  a=A[t]; gp={}
  for k,v in T.items():
    if k.startswith(t+'|'):
      for dr,(n,e) in (v.get('gap') or {}).items(): g=gp.setdefault(dr,[0,0]); g[0]+=n; g[1]+=e
  ol.append(dict(t=t,sk=a['sk'],skr=round(a['sk']/a['pn'],3),qh=a['qh'],qhr=round(a['qh']/a['pn'],3),aly=round(a['aly']/a['rn'],2),stuff=round(a['stuff']/a['rn'],3),
     repa=round(a['repa']/a['rn'],3),gap={k:[v[0],round(v[1]/v[0],3)] for k,v in gp.items() if v[0]>=8 and '?' not in k}))
for key,hi in (('skr',False),('qhr',False),('aly',True),('stuff',False),('repa',True)):
  P_=pct({r['t']:r[key] for r in ol},hi)
  for r in ol: r[key+'_p']=P_[r['t']]
for r in ol: r['pb']=int(round((r['skr_p']+r['qhr_p'])/2)); r['rb']=int(round((r['aly_p']+r['stuff_p']+r['repa_p'])/3))
json.dump({'season':y,'thru':out['maxw'][y],'power':pr,'units':U,'ol':ol,'div':DIV},open('data/teams_v2.json','w'))
print(pr[:3],ol[0])
