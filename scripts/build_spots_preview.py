"""Offline, manual display adapter. Reads existing repo snapshots only; no fetching or jobs."""
import argparse, hashlib, json, math, re
from datetime import datetime, timezone
from pathlib import Path

MARKETS = {'TE':['Receiving Yards','Receptions'], 'WR':['Receiving Yards','Receptions'], 'RB':['Rushing Yards','Carries','Receiving Yards','Receptions','Rushing Plus Receiving Yards'], 'QB':['Passing Yards','Pass Completions','Passing Attempts','Rushing Yards']}
FIELDS={'Receiving Yards':['receiving_yards'],'Receptions':['receptions'],'Rushing Yards':['rushing_yards'],'Carries':['carries'],'Passing Yards':['passing_yards'],'Pass Completions':['completions'],'Passing Attempts':['attempts'],'Rushing Plus Receiving Yards':['rushing_yards','receiving_yards'],'Anytime TD':['rushing_tds','receiving_tds']}
DEFAULT_AGE_MIN = 90
OUT_STATUSES=frozenset({'Out','Injured Reserve','Doubtful','Out for season','Reserve/PUP','Reserve/NFI','Reserve/COVID-19','Suspended'})

def number(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def stamp(x):
    if not isinstance(x,str): raise ValueError('Missing timestamp')
    d=datetime.fromisoformat(x.replace('Z','+00:00'))
    if d.tzinfo is None: raise ValueError('Timestamp requires timezone')
    return d.timestamp()
def normalize(v,n,profiles,dvp,now,max_age_minutes=DEFAULT_AGE_MIN):
    season = datetime.fromtimestamp(now,timezone.utc).year - (datetime.fromtimestamp(now,timezone.utc).month < 3)
    if n.get('season')!=season or not isinstance(n.get('week'),int) or n['week']!=v.get('week'):raise ValueError('Season/week mismatch')
    for src in [v,n]:
        age=now-stamp(src.get('updated'))
        if age < 0 or age > max_age_minutes * 60: raise ValueError('Source snapshot future/stale')
    games=[];seen=set()
    for g in n.get('games',[]):
        if g.get('state')!='pre':continue
        try:t=stamp(g.get('date'))
        except ValueError:continue
        if not now<t<now+7*86400 or str(g.get('id')) in seen:continue
        a=g.get('away',{}).get('abbr');h=g.get('home',{}).get('abbr')
        if a not in v.get('logos',{}) or h not in v.get('logos',{}) or a==h or not str(g.get('id','')).isascii() or not str(g.get('id','')).isdigit():continue
        seen.add(str(g['id']));games.append({'id':str(g['id']),'away':a,'home':h,'time':g['date'],'venue':g.get('venue') or 'Venue unavailable','line':g.get('line') if number(g.get('line')) else None,'total':g.get('total') if number(g.get('total')) else None})
    games.sort(key=lambda x:(stamp(x['time']),x['id']));index={g['id']:g for g in games}
    rows=[];identities=set();rejected=0
    for r in v.get('rows',[]):
        game=index.get(str(r.get('game')));aid=str(r.get('aid',''));pos=r.get('pos');market=r.get('market')
        if not game or not (aid.isascii() and aid.isdigit()) or pos not in MARKETS or market not in MARKETS[pos]+['Anytime TD']:rejected+=1;continue
        opponent=game['home'] if r.get('team')==game['away'] else game['away'] if r.get('team')==game['home'] else None
        if not opponent or r.get('oa')!=opponent or r.get('time')!=game['time'] or not number(r.get('line')):rejected+=1;continue
        key='|'.join([aid,game['id'],market]);
        if key in identities:raise ValueError('Conflicting duplicate player/game/market')
        identities.add(key);history=[];weeks=set()
        profile=profiles.get(aid,{})
        for x in sorted(profile.get('log',[]),key=lambda x:x.get('w',0),reverse=True):
            w=x.get('w');fields=FIELDS[market]
            if x.get('dnp') is True or x.get('s')!=season or x.get('t')!=r['team'] or not isinstance(w,int) or not 1<=w<n['week'] or w in weeks or not all(number(x.get(f)) for f in fields):continue
            weeks.add(w);history.append({'week':w,'value':sum(x[f] for f in fields),'opponent':x.get('o','')})
        prob=r.get('prob') if number(r.get('prob')) and 0<=r['prob']<=1 else None
        price=r.get('best') if number(r.get('best')) and abs(r['best'])>=100 else None
        profile=profiles.get(aid,{});native=profile.get('id')==aid and profile.get('team')==r['team'] and profile.get('pos')==pos
        inj=profile.get('inj') if isinstance(profile.get('inj'),dict) else {}
        st=inj.get('status')
        if not st and isinstance(r.get('inj'),dict):
            st=r['inj'].get('status') or r['inj'].get('st')
        if st in OUT_STATUSES:rejected+=1;continue
        inj_label=st if st else None
        rows.append({'key':key,'id':aid,'native':native,'name':str(r.get('name') or 'Player unavailable'),'team':r['team'],'opponent':opponent,'position':pos,'game':game['id'],'time':game['time'],'market':market,'line':r['line'],'estimate':prob,'market_blended':'market blend' in str(r.get('src','')).lower(),'price':price,'book':r.get('bbook') if isinstance(r.get('bbook'),str) and (re.fullmatch(r'Book [A-Z]+|Exchange',r['bbook']) is not None) else None,'highlighted':r.get('hl') is True,'injury':inj_label,'history':history})
    roles=[]
    for aid in sorted(set(r['id'] for r in rows)):
        p=profiles.get(aid,{});base=next(r for r in rows if r['id']==aid);logs=[];weeks=set()
        for x in sorted(p.get('log',[]),key=lambda x:x.get('w',0),reverse=True):
            w=x.get('w')
            if x.get('dnp') is True or x.get('s')!=season or x.get('t')!=base['team'] or not isinstance(w,int) or not 1<=w<n['week'] or w in weeks:continue
            weeks.add(w);item={'week':w}
            for metric in ['targets','carries','attempts','snap','target_share']:
                value=x.get(metric)
                if number(value) and value>=0 and (metric!='snap' or value<=100) and (metric!='target_share' or value<=1):item[metric]=value
            logs.append(item)
        roles.append({**{k:base[k] for k in ['id','native','name','team','opponent','position','game','time','injury']},'key':'role|'+aid+'|'+base['game'],'logs':logs})
    allowances=[]
    if dvp.get('season')==season:
        for t,entry in dvp.get('teams',{}).items():
            for pos in MARKETS:
                x=entry.get(pos,{})
                if not isinstance(x,dict):continue
                metrics={k:x[k] for k in ['yds','rec','td'] if number(x.get(k)) and x[k]>=0}
                if metrics:allowances.append({'team':t,'position':pos,'games':entry.get('g'),'metrics':metrics})
    return {'schema':1,'season':season,'week':n['week'],'source_updated':{'players':v['updated'],'games':n['updated']},'max_age_minutes':max_age_minutes,'dvp_updated':dvp.get('updated'),'games':games,'rows':rows,'roles':roles,'allowances':allowances,'coverage':{'rows':len(rows),'players':len(roles),'upcoming_games':len(games),'rejected_noncurrent_or_invalid_rows':rejected,'red_zone':'Not supplied: unverified partial rz fields are not published','line_history':'Opening/current timestamps not verified: no movement claims','line_provenance':'Native reference lines; no supplied bookmaker provenance for non-TD lines'},'rights':'Existing native snapshots only. No new external imports; retain existing data-credits.html attribution.'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));parser.add_argument('--max-age-minutes',type=int,default=DEFAULT_AGE_MIN);a=parser.parse_args();root=Path(a.root);read=lambda f:json.loads((root/f).read_text());v=read('data/v2.json');n=read('data/nfl.json')
    ids={str(r.get('aid','')) for r in v.get('rows',[]) if str(r.get('aid','')).isascii() and str(r.get('aid','')).isdigit()};profiles={i:read('data/players/'+i+'.json') for i in ids if (root/'data/players'/ (i+'.json')).is_file()}
    data=normalize(v,n,profiles,read('data/nfl_dvp.json'),datetime.now(timezone.utc).timestamp(),max_age_minutes=a.max_age_minutes);data['input_sha256']={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in ['data/v2.json','data/nfl.json','data/nfl_dvp.json']}
    out=root/'data/spots_preview.json'
    if out.exists():
        old=json.loads(out.read_text())
        if stamp(old['source_updated']['players'])>stamp(v['updated']):raise ValueError('Preserving newer output')
    out.write_text(json.dumps(data,separators=(',',':'),allow_nan=False)+'\n');print(data['coverage'])
if __name__=='__main__':main()
