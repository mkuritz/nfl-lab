"""Hard guard: Anytime TD stays off Highlighted until td-v3 passes the 150-prop market test."""
import json
d=json.load(open('data/v2.json')); k=0
for r in d['rows']:
  if r['market'] in ('Anytime TD','2+ TDs') and r.get('hl'): r['hl']=False; k+=1
d['td_hl']=False; json.dump(d,open('data/v2.json','w')); print('td hl forced off',k)
