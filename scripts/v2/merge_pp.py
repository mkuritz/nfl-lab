"""Attach market prices to data/v2.json rows from the Bet Lab prop price board (already-lettered books, no new odds credits)."""
import json,os,re,unicodedata,statistics as S
BL=os.environ.get('SL_BL','/tmp/bl')
nm=lambda s:re.sub(r"[^a-z]","",unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower())
P=json.load(open(BL+'/prop_prices.json')); R=P['rows']
Q={}
for k,v in R.items():
  sp,mk,pk,ln=(k.split('|')+['',''])[:4]
  if sp!='nfl': continue
  Q[(pk,mk,ln)]=v
def fl(x):
  try: return str(float(x))
  except Exception: return ''
Q2={(a,b,fl(c) if c else ''):v for (a,b,c),v in Q.items()}
d=json.load(open('data/v2.json')); n=nb=0
for r in d['rows']:
  atd=r['market']=='Anytime TD'
  q=Q2.get((nm(r['name']),r['market'],'' if atd else fl(r['line']))) or (Q2.get((nm(r['name']),r['market'],fl(0.5))) if atd else None)
  if not atd: r.update(fair=None,nb=None,best=None,bbook=None,edge=None,fsrc=None)
  if not q or (q.get('start') or '')[:10]!=(r.get('time') or '')[:10]: 
    if not atd: r['hl']=bool(r['prob'] and r['prob']>=.6 and r['hit'][1]>=5 and r['hit'][0]/r['hit'][1]>=.6)
    continue
  n+=1
  if q.get('best') is not None: r['best']=q['best']; r['bbook']=q.get('book')
  if q.get('nv') is not None and (q.get('nv_books') or 0)>=2: r['fair']=round(q['nv'],4); r['nb']=q['nv_books']; r['fsrc']='consensus'
  elif q.get('fair') is not None: r['fair']=round(q['fair'],4); r['nb']=q.get('fair_books'); r['fsrc']='sharp'
  if r['fair'] is not None and not atd and r['hit'][1]>=5:
    r['prob']=round((r['hit'][0]+20*r['fair'])/(r['hit'][1]+20),4); r['src']='hit rate shrunk to market (K=20)'
  if r['fair'] is not None and r['prob'] is not None: r['edge']=round(r['prob']-r['fair'],3); nb+=1
  if not atd: r['hl']=bool(r['edge'] is not None and r['edge']>=.03) or bool(r['prob'] and r['prob']>=.6 and r['hit'][1]>=5 and r['hit'][0]/r['hit'][1]>=.6)
d['odds_t']=P.get('as_of'); json.dump(d,open('data/v2.json','w'))
print('rows',len(d['rows']),'priced',n,'with edge',nb)
