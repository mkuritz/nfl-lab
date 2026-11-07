#!/usr/bin/env python3
"""Manual display-only team aggregate builder. No models or schedules modified."""
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
root=Path(__file__).resolve().parents[1]
pbp=json.loads((root/'data/pbp_v2.json').read_text())
season=str(max(int(x) for x in pbp['tw']));maxweek=0
if not 2020<=int(season)<=datetime.now(timezone.utc).year:raise ValueError('Future/malformed season')
if not pbp['tw'][season]:raise ValueError('Empty source; preserve prior output')
a=defaultdict(lambda:defaultdict(float))
for key,row in pbp['tw'][season].items():
    raw_team,week=key.split('|');team=canon(raw_team);week=int(week)
    if team not in VALID or not 1<=week<=18:raise ValueError('Invalid team/week')
    maxweek=max(maxweek,week)
    required='pepa pn repa rn epa n dpepa dpn drepa drn depa dn sk dsk'.split()
    if any(type(row.get(k)) not in (int,float) or not math.isfinite(row[k]) for k in required):raise ValueError('Missing/nonfinite metric; never substitute zero')
    if any(row[k]<0 for k in 'pn rn n dpn drn dn sk dsk'.split()):raise ValueError('Negative source count')
    for field,value in row.items():
        if type(value) in (int,float):
            if not math.isfinite(value):raise ValueError('Nonfinite source value')
            a[team][field]+=value
    a[team]['g']+=1
metrics={'pass_epa':('pepa','pn'),'rush_epa':('repa','rn'),'off_epa':('epa','n'),'pass_def_epa':('dpepa','dpn'),'rush_def_epa':('drepa','drn'),'def_epa':('depa','dn'),'sack_rate_off':('sk','pn'),'sack_rate_def':('dsk','dpn')}
rows=[]
for team,values in a.items():
    r={'team':team,'g':int(values['g'])}
    r.update({key:round(values[num]/values[den],4) if values[den] else None for key,(num,den) in metrics.items()})
    rows.append(r)
write_atomic(root,'unit_board.json',{'season':int(season),'source':'pbp_v2.json stored team-week aggregates','note':'Explosive-play and red-zone event metrics unavailable. No proxy relabeled as either.','teams':sorted(rows,key=lambda x:x['team'])},root/'data/pbp_v2.json',season,maxweek)
print('Built',len(rows),'teams for',season)
