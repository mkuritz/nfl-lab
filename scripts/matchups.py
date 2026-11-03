import json,glob,os,statistics as st,collections
import urllib.request,concurrent.futures as cf,datetime,sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); NL=ROOT+'/data'
BL=os.environ.get('BETLAB_DATA','https://betlab.sportslabshq.com/data')
def jload(name):
    if BL.startswith('http'):
        with urllib.request.urlopen(f'{BL}/{name}?t={int(datetime.datetime.now().timestamp())}',timeout=60) as r: return json.load(r)
    return json.load(open(f'{BL}/{name}'))
nfl=json.load(open(f'{NL}/nfl.json')); games=nfl['games']
opp={};site={};gtime={}
for g in games:
    a,h=g['away']['abbr'],g['home']['abbr']; opp[a]=h;opp[h]=a;site[a]='@';site[h]='vs';gtime[a]=gtime[h]=g['date']
plogs=jload('plogs_nfl.json')
props=jload('props_nfl.json')
# players: team,pos,depth,inj
P={}
for f in glob.glob(f'{NL}/players/*.json'):
    d=json.load(open(f)); P[d['id']]=d
# newest injury status wins: player file vs v2 inj list
v2=json.load(open(f'{NL}/v2.json'))['inj']
inj={}
for aid,d in P.items():
    i=d.get('inj') or {}
    if i.get('status'): inj[aid]=(i.get('date') or '',i['status'])
for t,L in v2.items():
    for r in L:
        if r['id'] not in inj or (r.get('dt') or '')>inj[r['id']][0]: inj[r['id']]=(r.get('dt') or '',r['st'])
try:
    for t,L in jload('injuries_nfl.json').items():
        for r in L: inj.setdefault(r['aid'],('',r['status']))
except Exception as e: print('betlab injuries unavailable',e)
try:   # live injury feed, newest timestamp wins (smart refresh, Nov 3)
    with urllib.request.urlopen('https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries',timeout=30) as r: _lf=json.load(r)
    for tm in _lf.get('injuries',[]):
        for i in tm.get('injuries',[]):
            h=((i.get('athlete') or {}).get('links') or [{}])[0].get('href','')
            if '/id/' not in h: continue
            aid=h.split('/id/')[1].split('/')[0]; d=(i.get('date') or '')
            if aid not in inj or d[:16]>inj[aid][0][:16]: inj[aid]=(d,i.get('status') or '')
except Exception as e: print('live injury feed unavailable',e)
def athlete(aid):
    try:
        with urllib.request.urlopen(f'https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{aid}',timeout=20) as r: a=json.load(r)['athlete']
        L=sorted(a.get('injuries') or [],key=lambda x:x.get('date',''))
        return aid,((L[-1]['date'][:16]+'Z',L[-1]['status']) if L else None)
    except Exception: return aid,'ERR'
cand=[a for a,d in P.items() if d.get('team') in opp and d.get('pos') in('QB','RB','WR','TE') and (d.get('depth') or {}).get('rank') and d['depth']['rank']<=3]
CHG=[]
with cf.ThreadPoolExecutor(16) as ex:
    for aid,r in ex.map(athlete,cand):
        if r=='ERR' or r is None: continue
        old=inj.get(aid)
        if not old or r[0]>=(old[0] or ''):
            if not old or old[1]!=r[1]: CHG.append((P[aid]['name'],P[aid]['team'],old[1] if old else 'none',r[1],r[0]))
            inj[aid]=r
for c in CHG: print('injury newer:',c)
# display-only QB-out note for pass catchers (Nov 3): newest status of each team's depth-chart QB1/QB2; grade unchanged
QBN={}
_tq=collections.defaultdict(list)
for _a,_d in P.items():
    if _d.get('pos')=='QB' and (_d.get('depth') or {}).get('rank'): _tq[_d['team']].append((_d['depth']['rank'],_d['name'],inj.get(_a,('',''))[1] or 'Active'))
for _t,L in _tq.items():
    L.sort(); _o=[x for x in L if x[2] in ('Out','Doubtful','Suspended') or x[2].startswith('Injured Reserve')]
    _nx=next((x for x in L if x not in _o),None)
    # only when a team's top QB(s) by recent starts are out: a QB who started 1+ 2026 game and is now unavailable
    _o=[x for x in _o if any(g['d']>='2026-09-01' and g['s'].get('passingAttempts',0)>=10 for g in plogs.get(next(a_ for a_,d_ in P.items() if d_['name']==x[1] and d_.get('team')==_t),[]))]
    if _o: QBN[_t]='QB-out: '+' · '.join(f'{n} {s_}' for _,n,s_ in _o)+(f'; next up {_nx[1]}'+(f' ({_nx[2]})' if _nx[2]!='Active' else '') if _nx and len(_o)>=2 else '')
print('QB-out notes',QBN)
OUT={'Out','Injured Reserve','Doubtful','Suspended','Physically Unable to Perform','Reserve'}
def season(aid,team):
    return [g for g in plogs.get(aid,[]) if g['d']>='2026-09-01' and g['t']==team]
# ---- defense allowed (2026, from every player game) ----
def blank(): return collections.defaultdict(float)
D=collections.defaultdict(blank); gms=collections.defaultdict(set); longr=collections.defaultdict(list)
for aid,L in plogs.items():
    pos=(P.get(aid) or {}).get('pos')
    for g in L:
        if g['d']<'2026-09-01': continue
        o=g['o']; s=g['s']; gms[o].add(g['e']); d=D[o]
        d['ry']+=s.get('rushingYards',0); d['ra']+=s.get('rushingAttempts',0)
        d['py']+=s.get('passingYards',0); d['pa']+=s.get('passingAttempts',0)
        td=s.get('rushingTouchdowns',0)+s.get('receivingTouchdowns',0); d['td']+=td
        if pos in('WR','TE','RB'): d['rec_'+pos]+=s.get('receivingYards',0); d['td_'+pos]+=td
        if s.get('longRushing',0)>=20: d['r20']+=1
pb=json.load(open(f'{NL}/pbp_v2.json'))['tw']['2026']
air=collections.defaultdict(lambda:[0,0]); pr=collections.defaultdict(lambda:[0,0])
for k,r in pb.items():
    t=k.split('|')[0]; o=r.get('opp')
    if o: air[o][0]+=r.get('ay',0); air[o][1]+=r.get('att',0)
    pr[t][0]+=r.get('dpn',0); pr[t][1]+=r.get('dn',0)
teams=[t for t in D if len(gms[t])>=4]
def per(t,k): return D[t][k]/len(gms[t])
M={}
for t in teams:
    M[t]=dict(rush_g=per(t,'ry'),ypc=D[t]['ry']/max(D[t]['ra'],1),r20=per(t,'r20'),
      pass_g=per(t,'py'),ypa=D[t]['py']/max(D[t]['pa'],1),td_g=per(t,'td'),
      adot=air[t][0]/max(air[t][1],1),passrate=pr[t][0]/max(pr[t][1],1)*100,
      **{f'rec_{p}':per(t,'rec_'+p) for p in('WR','TE','RB')},**{f'td_{p}':per(t,'td_'+p) for p in('WR','TE','RB')})
def rank(key,hi_bad=True):  # rank 32 = most allowed (best for offense), like screenshots
    s=sorted(teams,key=lambda t:M[t][key]); return {t:i+1 for i,t in enumerate(s)}
RK={k:rank(k) for k in M[teams[0]]}
lg={k:st.mean(M[t][k] for t in teams) for k in M[teams[0]]}
# ---- lines ----
mk={'td':'Anytime TD','rush':'Rushing Yards','rec':'Receiving Yards','pass':'Passing Yards'}
LN={}
for p in props:
    for c,m in mk.items():
        if p['market']==m and p['team'] in opp: LN[(c,p['aid'])]=p
CAT={'td':dict(stat=lambda s:1 if s.get('rushingTouchdowns',0)+s.get('receivingTouchdowns',0)>0 else 0,pos=('RB','WR','TE'),depth=(1,2,3)),
     'rush':dict(stat=lambda s:s.get('rushingYards',0),pos=('RB','QB'),depth=(1,2)),
     'rec':dict(stat=lambda s:s.get('receivingYards',0),pos=('WR','TE','RB'),depth=(1,2,3)),
     'pass':dict(stat=lambda s:s.get('passingYards',0),pos=('QB',),depth=(1,))}
def mfac(c,pos,o):
    m=M[o]
    if c=='rush': return 0.5*m['rush_g']/lg['rush_g']+0.5*m['ypc']/lg['ypc']
    if c=='pass': return 0.5*m['pass_g']/lg['pass_g']+0.5*m['ypa']/lg['ypa']
    if c=='rec': return m['rec_'+pos]/lg['rec_'+pos]
    return 0.5*m['td_'+pos]/lg['td_'+pos]+0.5*m['td_g']/lg['td_g']
def cols(c,pos,o):
    m=M[o];R=lambda k:RK[k][o]
    if c=='td': return [('Opp TDs/g',m['td_g'],R('td_g')),(f'TDs to {pos}/g',m['td_'+pos],R('td_'+pos)),(f'Rec yds to {pos}/g',m['rec_'+pos],R('rec_'+pos))]
    if c=='rush': return [('Rush yds/g',m['rush_g'],R('rush_g')),('Yds/car',m['ypc'],R('ypc')),('20+ yd runs/g',m['r20'],R('r20'))]
    if c=='rec': return [(f'Rec yds to {pos}/g',m['rec_'+pos],R('rec_'+pos)),('Pass yds/g',m['pass_g'],R('pass_g')),('Air yds/att',m['adot'],R('adot'))]
    return [('Pass yds/g',m['pass_g'],R('pass_g')),('Yds/att',m['ypa'],R('ypa')),('Pass rate faced %',m['passrate'],R('passrate'))]
# league TD-game rate by position (2026, depth-chart regulars with 4+ games) - shrink target for TD chance (4 extra average games)
_lt=collections.defaultdict(list)
for _a,_d in P.items():
    if _d.get('pos') in ('RB','WR','TE') and (_d.get('depth') or {}).get('rank') in (1,2):
        _g=[g for g in plogs.get(_a,[]) if g['d']>='2026-09-01']
        if len(_g)>=4: _lt[_d['pos']]+= [1 if g['s'].get('rushingTouchdowns',0)+g['s'].get('receivingTouchdowns',0)>0 else 0 for g in _g]
LGTD={k:st.mean(v) for k,v in _lt.items()}; print('league TD-game rate',{k:round(v,3) for k,v in LGTD.items()})
GR=['A+','A','A-','B+','B','B-','C+','C','C-','D+','D','F']
out={}
for c,cfg in CAT.items():
    rows=[]
    for aid,d in P.items():
        t=d.get('team'); pos=d.get('pos'); dep=(d.get('depth') or {}).get('rank')
        if t not in opp or opp[t] not in M or pos not in cfg['pos'] or not dep or dep>max(cfg['depth']): continue
        if c=='rush' and pos=='QB' and dep!=1: continue
        st_=inj.get(aid,('',''))[1]
        if st_ in OUT or st_.startswith('Injured Reserve') or 'Out' in st_.split(): continue
        G=sorted(season(aid,t),key=lambda g:g['d'])
        if len(G)<4: continue
        vals=[cfg['stat'](g['s']) for g in G]; l5=vals[-5:]
        if c!='td' and st.mean(vals)<{'rush':30,'rec':30,'pass':150}[c]: continue
        if c=='td' and (dep>(2 if pos=='WR' else 1)): continue
        lp=LN.get((c,aid)); line=lp['line'] if lp else (0.5 if c=='td' else max(0.5,round(st.median(vals))-0.5))
        src='posted' if lp else ('model' if c!='td' else 'model')
        base=0.6*st.mean(l5)+0.4*st.mean(vals); f=mfac(c,pos,opp[t]); proj=base*f
        sd=max(st.pstdev(vals),1 if c!='td' else .1)
        score=(proj-line)/sd if c!='td' else proj
        rows.append(dict(aid=aid,name=d['name'],team=t,opp=opp[t],site=site[t],pos=pos,inj=st_ if st_ not in('','Active') else '',**({'qb':QBN[t]} if t in QBN and pos in('WR','TE','RB') and c in('rec','td') else {}),
            line=line,src=src,book=((lp or {}).get('book') or ('Book A' if (lp or {}).get('ov') else None)),price=(lp or {}).get('ov'),l5=l5,hits=sum(v>line for v in l5),l5avg=round(st.mean(l5),2 if c=='td' else 1),
            proj=round(proj*100 if c=='td' else proj,1),td_chance=(round(100*(1-(1-min((len(vals)*(0.4*st.mean(l5)+0.6*st.mean(vals))+4*LGTD.get(pos,0.3))/(len(vals)+4),0.95))**f)) if c=='td' else None),szn_hits=sum(v>line for v in vals),szn_n=len(vals),szn_avg=round(st.mean(vals),2 if c=='td' else 1),
            **({} if c!='td' else (lambda T:dict(td2_szn=round(100*sum(x>=2 for x in T)/len(T)),td3_szn=round(100*sum(x>=3 for x in T)/len(T)),td2_l5=sum(x>=2 for x in T[-5:]),td3_l5=sum(x>=3 for x in T[-5:])))([g['s'].get('rushingTouchdowns',0)+g['s'].get('receivingTouchdowns',0) for g in G])),mf=round(f,2),score=score,time=gtime[t],
            cols=[(a,(round(b,1 if b>3 else 2) if b else None),(r if b else None)) for a,b,r in cols(c,pos,opp[t])]))
    rows.sort(key=lambda r:-r['score']); n=len(rows)
    def pct(key):  # 0-10 within this category's slate (10 = best in category)
        v=sorted(key(r) for r in rows); m=len(v)-1 or 1
        return lambda r: round(10*sum(x<key(r) for x in v)/m,1)
    comp=[('Defense matchup',pct(lambda r:r['mf'])),('Last 5 form',pct(lambda r:(r['hits']/max(1,len(r['l5'])),r['l5avg']-r['line'] if c!='td' else r['l5avg']))),
          ('Season hit rate',pct(lambda r:r['szn_hits']/max(1,r['szn_n']))),('Projection vs line',pct(lambda r:r['score']))]
    for r in rows: r['parts']=[[k,f(r)] for k,f in comp]
    for i,r in enumerate(rows): r['grade']=GR[min(11,int(i/n*12))]; r['g10']=round(10*(n-1-i)/max(1,n-1),1); r.pop('score')
    out[c]=dict(best=rows,worst=rows[::-1],n=n)
json.dump(dict(week=nfl['week'],updated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),cats={c:dict(best=v['best'],n=v['n']) for c,v in out.items()}),open(NL+'/matchups.json','w'),separators=(',',':'))
for c in out:
    print(c,out[c]['n']);
    for r in out[c]['best'][:3]+out[c]['worst'][:3]: print(' ',r['grade'],r['name'],r['pos'],r['team'],r['site'],r['opp'],r['line'],r['src'],r['hits'],r['l5avg'],r['mf'],r['cols'])
