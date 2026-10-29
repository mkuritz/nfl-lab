"""Trench availability: OL/DL players listed Out/IR/Doubtful/Questionable on the current league injury
report reduce their unit using that player's real 2026 contribution, with a backup absorbing part of the role.
- OL: weight = status weight x player's recent offensive snap share / 5 (one of five line spots) x 0.5 replacement gap.
  Pass-pro rates (sacks, QB hits) and stuff rate scale up by (1+L); adjusted line yards scale down by (1-L/2);
  rush EPA/play drops by 0.10*L.
- DL: the player's own 2026 sacks, QB hits, run stuffs and the EPA of those plays are removed x status weight x 0.5
  (backup assumed to replace half of it).
Status weights: Out / Injured Reserve / Suspension / PUP = 1.0, Doubtful = 0.75, Questionable = 0.25.
No player is double-counted; failure to fetch leaves ratings unadjusted."""
import json,urllib.request,os,pandas as pd,numpy as np
OL_POS={'T','G','C','OT','OG','OL','LT','RT','LG','RG'}; DL_POS={'DE','DT','NT','DL','EDGE'}
SW={'Out':1.0,'Injured Reserve':1.0,'Suspension':1.0,'Physically Unable to Perform':1.0,'Doubtful':0.75,'Questionable':0.25}
FIX={'LAR':'LA','WSH':'WAS'}
def fetch():
  u='https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/injuries'
  return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=20))
def apply(A,sc,raw):
  if os.environ.get('SL_NO_AVAIL'): return {}
  try: d=fetch()
  except Exception as e: print('trench_avail: injury feed unavailable',e); return {}
  pl=pd.read_csv(raw+'/players.csv',low_memory=False,dtype={'espn_id':str})
  e2g=dict(zip(pl.espn_id.dropna().str.replace(r'\.0$','',regex=True),pl.gsis_id[pl.espn_id.notna()]))
  e2p=dict(zip(pl.espn_id.dropna().str.replace(r'\.0$','',regex=True),pl.pfr_id[pl.espn_id.notna()]))
  try: sn=pd.read_parquet(raw+'/snap_2026.parquet'); sn=sn[sn.game_type=='REG']
  except Exception: sn=None
  idc=[c for c in sc.columns if c.endswith('_player_id') and any(k in c for k in ('sack','qb_hit','tackle'))]
  out={}
  for t in d.get('injuries',[]):
    for i in t.get('injuries',[]):
      a=i.get('athlete') or {}; w=SW.get(i.get('status'),0)
      pos=((a.get('position') or {}).get('abbreviation') or '').upper(); tm=FIX.get((a.get('team') or {}).get('abbreviation'),(a.get('team') or {}).get('abbreviation'))
      if not w or tm not in A or (pos not in OL_POS and pos not in DL_POS): continue
      href=next((l['href'] for l in a.get('links',[]) if '/id/' in l.get('href','')),'')
      eid=href.split('/id/')[1].split('/')[0] if '/id/' in href else None
      nm=a.get('displayName'); rec=dict(n=nm,pos=pos,st=i.get('status'),w=w)
      if pos in OL_POS:
        if sn is None: continue
        pid=e2p.get(eid); g=sn[(sn.pfr_player_id==pid)] if pid else sn[(sn.player==nm)&(sn.team==tm)]
        g=g.sort_values('week').tail(4); share=float(g.offense_pct.mean()) if len(g) else 0
        if share<0.4: continue   # not a regular starter -> no unit change
        L=w*share/5*0.5; rec.update(share=round(share,2),loss=round(L,3)); out.setdefault(tm,{'ol':[],'dl':[],'L':0})
        out[tm]['ol'].append(rec); out[tm]['L']+=L
      else:
        gid=e2g.get(eid)
        if not gid: continue
        m=lambda ks:sc[[c for c in idc if any(k in c for k in ks)]].eq(gid).any(axis=1)
        skm=m(('sack',))&(sc.ispass==1); qhm=m(('qb_hit',))&(sc.ispass==1); stm=m(('tackle','sack'))&(sc.isrun==1)&(sc.yards_gained<=0)
        k=w*0.5; c=dict(dsk=k*skm.sum(),dqh=k*qhm.sum(),dstuff=k*stm.sum(),dpepa=k*float(sc[skm|qhm].epa.sum()),drepa=k*float(sc[stm].epa.sum()))
        if not (skm.sum()+qhm.sum()+stm.sum()): continue
        rec.update(sk=int(skm.sum()),qh=int(qhm.sum()),stf=int(stm.sum())); out.setdefault(tm,{'ol':[],'dl':[],'L':0})['dl'].append(rec)
        a_=A[tm]
        for x in ('dsk','dqh','dstuff'): a_[x]=max(0,a_[x]-c[x])
        a_['dpepa']-=c['dpepa']; a_['drepa']-=c['drepa']   # sacks/stuffs carry negative offensive EPA -> removing them worsens defense
  for tm,o in out.items():
    L=min(o.pop('L'),0.35); o['L']=round(L,3)
    if L:
      a_=A[tm]; a_['sk']*=1+L; a_['qh']*=1+L; a_['stuff']*=1+L; a_['aly']*=1-L/2; a_['repa']-=0.10*L*a_['rn']
  return out
