"""Corrected power ratings + season sim. Ratings: EPA net/game regressed to mean (g/(g+6)), then ridge-fit to this week's market spreads. Sim: 20k seasons, per-sim rating uncertainty, real seeding + playoff bracket."""
import os
RAW=os.environ.get('SL_RAW','/tmp/nflraw'); BL=os.environ.get('SL_BL','/tmp/bl')
import json,numpy as np,pandas as pd,collections
T=json.load(open('data/teams_v2.json'));DIV=T['div'];TD={t:d for d,s in DIV.items() for t in s.split()}
P={r['t']:r for r in T['power']};teams=sorted(P);ix={t:i for i,t in enumerate(teams)}
ab=lambda x:{'LAR':'LA','WSH':'WAS'}.get(x,x)
sch=pd.read_csv(RAW+'/games.csv');sch=sch[(sch.season==2026)&(sch.game_type=='REG')]
played=sch[sch.result.notna()];rem=sch[sch.result.isna()]
G=collections.Counter(list(played.home_team)+list(played.away_team))
W=collections.Counter();Lc=collections.Counter();Tc=collections.Counter()
for _,g in played.iterrows():
  if g.result>0: W[g.home_team]+=1;Lc[g.away_team]+=1
  elif g.result<0: W[g.away_team]+=1;Lc[g.home_team]+=1
  else: Tc[g.home_team]+=1;Tc[g.away_team]+=1
raw={t:P[t]['rat'] for t in teams}; prior=np.array([raw[t]*G[t]/(G[t]+6) for t in teams])
HFA=1.5; mk=json.load(open(BL+'/games_nfl.json'))
A=[];b=[]
for m in mk:
  h,a=ab(m['home']),ab(m['away']); row=np.zeros(32); row[ix[h]]=1; row[ix[a]]=-1; A.append(row); b.append(-m['spread']-HFA)  # home margin implied
A=np.array(A);b=np.array(b);lam=0.6
r=np.linalg.solve(A.T@A+lam*np.eye(32),A.T@b+lam*prior)
# Apply mid-season trade/IR rating delta so SF (on Week 8 bye), SEA, and IND reflect Oct 27 trades immediately
TRADE_RAT_DELTA={'SF':0.65,'SEA':0.56,'IND':-1.12}
for _tm,_d in TRADE_RAT_DELTA.items():
  if _tm in ix: r[ix[_tm]]+=_d
r-=r.mean()
fit=A@r; pre=A@prior
rng=np.random.default_rng(11);N=20000
base=np.array([W[t]+.5*Tc[t] for t in teams],float);wins=np.tile(base,(N,1))
R=r+rng.normal(0,2.0,(N,32))
H=np.array([ix[h] for h in rem.home_team]);Aw=np.array([ix[a] for a in rem.away_team])
res=np.zeros((N,32))
for k in range(len(H)):
  m=R[:,H[k]]-R[:,Aw[k]]+HFA+rng.normal(0,13.5,N); hw=m>0; wins[:,H[k]]+=hw; wins[:,Aw[k]]+=~hw
ww=wins+rng.random(wins.shape)*1e-3
po=np.zeros(32);dv=np.zeros(32);cf=np.zeros(32);sb=np.zeros(32)
def game(s,a,b,home):  # returns winner index
  m=R[s,a]-R[s,b]+(HFA if home else 0)+rng.normal(0,13.5); return a if m>0 else b
for s in range(N):
  champs={}
  for conf in ('AFC','NFC'):
    dw=[max((ix[t] for t in DIV[d].split()),key=lambda i:ww[s,i]) for d in DIV if d.startswith(conf)]
    rest=sorted([ix[t] for t in teams if TD[t].startswith(conf) and ix[t] not in dw],key=lambda i:-ww[s,i])[:3]
    seeds=sorted(dw,key=lambda i:-ww[s,i])+rest
    for i in seeds: po[i]+=1
    for i in dw: dv[i]+=1
    w1=[game(s,seeds[1],seeds[6],1),game(s,seeds[2],seeds[5],1),game(s,seeds[3],seeds[4],1)]
    alive=sorted([seeds[0]]+w1,key=lambda i:seeds.index(i))
    f1=game(s,alive[0],alive[3],1);f2=game(s,alive[1],alive[2],1)
    a,b_=sorted([f1,f2],key=lambda i:seeds.index(i));c=game(s,a,b_,1);cf[c]+=1;champs[conf]=c
  sb[game(s,champs['AFC'],champs['NFC'],0)]+=1
def sos(df,t):
  o=[g.away_team if g.home_team==t else g.home_team for _,g in df.iterrows() if t in (g.home_team,g.away_team)];return round(float(np.mean([r[ix[x]] for x in o])),2) if o else None
out=[]
for t in teams:
  i=ix[t];out.append(dict(t=t,rat=round(float(r[i]),2),raw=raw[t],qb=P[t]['qb'],sosp=sos(played,t),sosr=sos(rem,t),w=round(float(wins[:,i].mean()),1),
    po=round(po[i]/N,3),div=round(dv[i]/N,3),conf=round(cf[i]/N,3),sb=round(sb[i]/N,3),rec=f"{W[t]}-{Lc[t]}"+(f"-{Tc[t]}" if Tc[t] else ""),left=int(17-G[t])))
out.sort(key=lambda x:-x['rat']);T['power']=out
T['sim']={'n':N,'hfa':HFA,'sd':13.5,'rating_sd':2.0,'ridge':lam,'reg_games':6,
  'check':{'sd_raw':round(float(np.std(list(raw.values()))),2),'sd_final':round(float(r.std()),2),'mae_prior_vs_market':round(float(np.abs(pre-b).mean()),2),'mae_final_vs_market':round(float(np.abs(fit-b).mean()),2),
  'sum_div':round(float(dv.sum()/N),2),'sum_po':round(float(po.sum()/N),2),'sum_conf':round(float(cf.sum()/N),2),'sum_sb':round(float(sb.sum()/N),2),'avg_w':round(float(wins.mean()),2),'games_left':int(len(rem))}}
json.dump(T,open('data/teams_v2.json','w'))
print(T['sim']['check'])
for d,s in DIV.items(): print(d,[(x['t'],x['rec'],x['rat'],x['div']) for x in out if x['t'] in s.split()])
print([(x['t'],x['po'],x['conf'],x['sb']) for x in out[:6]])
