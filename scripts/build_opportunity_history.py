#!/usr/bin/env python3
"""Descriptive attributed opportunities from stored EPA-filtered regular-season player weeks."""
from pathlib import Path
from collections import defaultdict
import json
from datetime import datetime, timezone
import hashlib, math, os, tempfile
ATTRIBUTION={'creator':'nflverse contributors','source':'https://github.com/nflverse/nflverse-data','license':'CC-BY-4.0','license_url':'https://creativecommons.org/licenses/by/4.0/','changes':'Filtered and aggregated existing stored 2026 team/player-week observations; no raw plays in this output.'}
VALID=set('ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LV LAC LAR MIA MIN NE NO NYG NYJ PHI PIT SF SEA TB TEN WSH'.split())
def canon(t):return {'LA':'LAR','WAS':'WSH'}.get(t,t)
def write_atomic(root,name,out,source,season,week):
    if not 2020<=int(season)<=datetime.now(timezone.utc).year:raise ValueError('Future or malformed season')
    out.update(attribution=ATTRIBUTION,derived_at=datetime.now(timezone.utc).isoformat(),source_data_as_of=None,source_snapshot_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),through_week=week)
    payload=json.dumps(out,separators=(',',':'),allow_nan=False)+'\n'
    with tempfile.NamedTemporaryFile(mode='w',dir=root/'data',prefix='.'+name,delete=False) as f:
        f.write(payload);tmp=f.name
    os.replace(tmp,root/'data'/name)
r=Path(__file__).resolve().parents[1];d=json.loads((r/'data/pbp_v2.json').read_text());season=str(max(d['seasons']));teams=defaultdict(dict)
if not 2020<=int(season)<=datetime.now(timezone.utc).year:raise ValueError('Future/malformed season')
if not d['pw'].get(season):raise ValueError('Empty source; preserve prior output')
maxweek=0
for key,row in d['pw'][season].items():
    pid,w=key.rsplit('|',1);t=canon(row['t']);week=int(w)
    if t not in VALID or not 1<=week<=18 or not pid:raise ValueError('Invalid source identity/week')
    maxweek=max(maxweek,week)
    item=teams[t].setdefault(week,{'week':week,'players':[],'carries':0,'targets':0})
    ca=row.get('ca',0);tg=row.get('tg',0)
    if any(type(v) is not int or v<0 for v in [ca,tg]):raise ValueError('Invalid attributed counts')
    item['carries']+=ca;item['targets']+=tg
    item['players'].append({'source_id':pid,'name':row['nm'],'carries':ca,'targets':tg})
out={'season':int(season),'definition':'Observed attributed player opportunities only. Source regular-season pass/run plays with nonmissing EPA; targets require receiver ID, carries require rusher ID. Shares divide by sum of attributed counts in selected team weeks, not every team snap. Missing player-week rows are not proven inactive/zero opportunity. Not an injury effect, future forecast or redistributive allocation.','teams':{t:[weeks[w] for w in sorted(weeks)] for t,weeks in sorted(teams.items())}}
write_atomic(r,'opportunity_history.json',out,r/'data/pbp_v2.json',season,maxweek)
print('Teams',len(out['teams']),'player-week rows',sum(len(w['players']) for v in out['teams'].values() for w in v))
