import os
RAW=os.environ.get('SL_RAW','/tmp/nflraw'); BL=os.environ.get('SL_BL','/tmp/bl')
import json,urllib.request,concurrent.futures as C
d=json.load(open('data/v2.json'))
def f(a):
  try:
    x=json.load(urllib.request.urlopen(f"https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{a}",timeout=15))['athlete']
    return a,{'ht':x.get('displayHeight'),'wt':x.get('displayWeight'),'tc':x.get('team',{}).get('color'),'tc2':x.get('team',{}).get('alternateColor'),'st':(x.get('status') or {}).get('name')}
  except Exception as e: return a,{}
with C.ThreadPoolExecutor(16) as ex:
  for a,b in ex.map(f,list(d['hero'])): d['hero'][a].update(b)
json.dump(d,open('data/v2.json','w'));print(sum(1 for h in d['hero'].values() if h.get('ht')))
