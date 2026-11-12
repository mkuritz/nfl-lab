/* Opportunity Board · usage sections (Opportunity Share, Position Rank Movement, Defense).
   Display-only. Data: data/usage_board.json, built by scripts/build_usage_board.py in the daily Hub refresh.
   Uses only the safe PV node builder (no innerHTML). Every number is a count or ratio of counts from weekly logs. */
(function(){'use strict';
const {node:n,text,card,select,json}=PV;
const root=document.getElementById('usage-app');if(!root)return;
const Q=new URLSearchParams(location.search);
const HEAD=id=>'https://a.espncdn.com/i/headshots/nfl/players/full/'+id+'.png';
const st={team:Q.get('team')||'NYG',split:'all',tab:'all',showAll:false,sel:null,
 pos:Q.get('pos')||'WR',basis:'season',cmp:1,topN:10,sort:'rank',
 dgrp:'rush',dsub:'all',dcmp:1,dtop:10};
let D,U;
const pct=x=>x==null?'—':Math.round(x*100)+'%';
const last=nm=>{const p=nm.replace(/ (Jr\.|Sr\.|II|III|IV)$/,'').split(' ');return p[p.length-1]};
const poss=nick=>nick.toUpperCase()+(/S$/i.test(nick)?"'":"'S");
function bar(frac,cls,w=100){const f=Math.max(0,Math.min(1,frac||0));return n('svg',{viewBox:'0 0 100 8',preserveAspectRatio:'none',class:'ub-bar '+(cls||''),role:'img','aria-label':Math.round(f*100)+' percent'},n('rect',{x:0,y:0,width:100,height:8,class:'ub-bar-bg'}),n('rect',{x:0,y:0,width:Math.max(f*100,f>0?2:0),height:8,class:'ub-bar-fg'}))}
function avatar(id){return n('img',{class:'ub-av',src:HEAD(id),alt:'',loading:'lazy',width:44,height:44,error:e=>e.target.classList.add('off')})}
function chips(opts,val,fn,label){return n('div',{class:'ub-chips',role:'group','aria-label':label},opts.map(([k,l])=>n('button',{type:'button',class:val===k?'on':'','aria-pressed':val===k?'true':'false',click:()=>fn(k)},l)))}
function open(id){const x=window.PVNFL;x&&x.playerOpen(id)}
const pname=(p,t)=>n('button',{class:'ub-pname pv-link',click:()=>open(p.id)},p.n);

/* ---------- 1. Opportunity Share ---------- */
function weeksFor(T,split){
 const g=T.games;if(split==='all')return g.map(x=>x[0]);
 const [k,id]=split.split(':');return g.filter(x=>k==='with'?x[2]===id:x[2]!==id).map(x=>x[0]);
}
function calc(T,weeks,tab,filterWeeks){
 const G=new Map(T.games.map(x=>[x[0],x])),W=new Set(weeks),out=[];
 for(const p of T.players){
  let tg=0,ca=0,ttd=0,rtd=0,g=0,den=0,snaps=[];
  for(const [w,snap,t,c,td1,td2] of p.g){
   if(!W.has(w)||(filterWeeks&&!filterWeeks.has(w)))continue;
   if(!(snap>0||t>0||c>0))continue;
   const gm=G.get(w);if(!gm)continue;
   const d=tab==='targets'?gm[3]:tab==='rushes'?gm[4]:(gm[3]==null?null:gm[3]+gm[4]);
   if(d==null)continue;
   g++;den+=d;tg+=t;ca+=c;ttd+=td1;rtd+=td2;if(snap!=null)snaps.push(snap);
  }
  const vol=tab==='targets'?tg:tab==='rushes'?ca:tg+ca;
  if(!g||!vol)continue;
  out.push({p,g,vol,tg,ca,share:den?vol/den:null,pg:vol/g,td:tab==='targets'?ttd:tab==='rushes'?rtd:ttd+rtd,snap:snaps.length?snaps.reduce((a,b)=>a+b,0)/snaps.length:null});
 }
 return out.sort((a,b)=>(b.share||0)-(a.share||0)||b.vol-a.vol);
}
function qbTimeline(T){
 const ids=Object.keys(T.qbs),idx=Object.fromEntries(ids.map((k,i)=>[k,i]));
 return n('div',{class:'ub-tl'},n('span',{class:'ub-tl-l'},'Starting QB'),T.games.map(x=>n('span',{class:'ub-tl-c q'+(idx[x[2]]%4)},n('b',{},'W'+x[0]),n('i',{},x[2]?last(T.qbs[x[2]]):'—'))));
}
function shareSection(){
 const T=D.usage.teams[st.team],qbIds=Object.keys(T.qbs);
 const splits=[['all','All games ('+T.games.length+')']];
 const cnt=id=>T.games.filter(x=>x[2]===id).length;
 qbIds.sort((a,b)=>cnt(b)-cnt(a));
 for(const id of qbIds){splits.push(['with:'+id,'With '+T.qbs[id]+' ('+cnt(id)+')']);}
 if(qbIds.length>=2)for(const id of qbIds)splits.push(['wo:'+id,'Without '+T.qbs[id]+' ('+(T.games.length-cnt(id))+')']);
 if(!splits.some(s=>s[0]===st.split))st.split='all';
 const wk=weeksFor(T,st.split),rows=calc(T,wk,st.tab),all=calc(T,weeksFor(T,'all'),st.tab);
 const allBy=new Map(all.map(r=>[r.p.id,r])),cur=T.games.map(x=>x[0]),recent=new Set(cur.slice(-3)),early=new Set(cur.slice(0,-3));
 const rec=new Map(calc(T,wk,st.tab,recent).map(r=>[r.p.id,r])),ear=new Map(calc(T,wk,st.tab,early).map(r=>[r.p.id,r]));
 if(!rows.some(r=>r.p.id===st.sel))st.sel=rows[0]?.p.id;
 const sel=rows.find(r=>r.p.id===st.sel),what=st.tab==='targets'?'TARGETS':st.tab==='rushes'?'CARRIES':'TARGETS + CARRIES';
 const unit=st.tab==='targets'?'Tgt':st.tab==='rushes'?'Rush':'Opp';
 const shown=st.showAll?rows:rows.slice(0,8);
 const head=n('tr',{},n('th',{},'Player'),n('th',{},'Snap%'),n('th',{},'Share%'),n('th',{},unit+'/G'),n('th',{},'TD'));
 const body=shown.map(r=>{
  const a=rec.get(r.p.id),b=ear.get(r.p.id);let tr=null;
  if(a&&b&&a.share!=null&&b.share!=null&&Math.abs(a.share-b.share)>=0.015){const d=Math.round((a.share-b.share)*100);tr=n('span',{class:'ub-tr '+(d>0?'up':'dn'),title:'Share over the last 3 team games vs earlier games'},(d>0?'▲':'▼')+Math.abs(d))}
  let vs=null;if(st.split!=='all'&&allBy.get(r.p.id)&&r.share!=null&&allBy.get(r.p.id).share!=null){const d=Math.round((r.share-allBy.get(r.p.id).share)*100);if(d)vs=n('span',{class:'ub-vs '+(d>0?'up':'dn'),title:'vs all games'},(d>0?'+':'')+d+' vs all')}
  const sub=st.tab==='all'?r.tg+' Tgt · '+r.ca+' Rush · '+r.g+' G':r.vol+' '+unit+' · '+r.g+' G';
  return n('tr',{class:'ub-row'+(r.p.id===st.sel?' sel':''),click:()=>{st.sel=r.p.id;paint()}},
   n('td',{class:'ub-pl'},n('button',{type:'button',class:'ub-selbtn','aria-label':'Show '+r.p.n,click:()=>{st.sel=r.p.id;paint()}},r.p.n),n('small',{},r.p.pos+' · '+sub)),
   n('td',{},r.snap==null?'—':Math.round(r.snap)+'%'),
   n('td',{class:'ub-sh'},n('b',{class:(r.share||0)>=0.2?'hi':''},pct(r.share)),tr,vs),
   n('td',{},r.pg.toFixed(2)),n('td',{},r.td));
 });
 const tbl=n('div',{class:'ub-tablewrap'},n('table',{class:'ub-table'},n('thead',{},head),n('tbody',{},body)));
 // callout
 let callout=text('No players with usage in this split.');
 if(sel){
  const cmp=[];
  if(qbIds.length>=2){for(const [k,l] of splits){const r=calc(T,weeksFor(T,k),st.tab).find(x=>x.p.id===sel.p.id);cmp.push([k,l,r])}}
  callout=n('div',{class:'ub-call'},
   n('div',{class:'ub-big'},n('span',{class:'num'},sel.share==null?'—':Math.round(sel.share*100)+'%'),n('div',{class:'cap'},n('b',{},'OF THE '+poss(T.nick)+' '+what),n('span',{},'ARE GOING TO '+sel.p.n.toUpperCase()))),
   bar(sel.share,'big'),
   n('p',{class:'mut sm'},sel.p.n+' · '+T.nick+' · '+(st.split==='all'?'all '+wk.length+' games':splits.find(s=>s[0]===st.split)[1])+' · shares are of the team games he played.'),
   cmp.length?n('div',{class:'ub-qbcmp'},n('h3',{},'With and without each QB'),cmp.map(([k,l,r])=>n('div',{class:'ub-qbrow'+(k===st.split?' on':'')},
     n('span',{class:'l'},l),r?n('span',{class:'v'},pct(r.share)+' · '+r.pg.toFixed(1)+'/G · '+r.g+' G'):n('span',{class:'v mut'},'did not play'),r?bar(r.share):n('span',{})))):null);
 }
 const qsel=select('QB split',splits,st.split,v=>{st.split=v;paint()});
 const tsel=select('Team',Object.keys(D.usage.teams).sort().map(t=>[t,D.usage.teams[t].name]),st.team,v=>{st.team=v;st.split='all';st.sel=null;st.showAll=false;paint()});
 return n('section',{class:'pv-card ub-card',id:'usage-share'},
  n('h2',{},'Opportunity Share'),
  n('p',{class:'mut sm'},'Builds on ',n('a',{href:'spots.html?view=roles'},'Rising Roles'),': who gets the targets and carries, and how that changes with each starting QB. ▲/▼ = change in share over the last 3 team games vs earlier games.'),
  n('div',{class:'ub-controls'},tsel,qsel),
  qbTimeline(T),
  chips([['all','All'],['targets','Targets'],['rushes','Rushes']],st.tab,k=>{st.tab=k;st.showAll=false;st.sel=null;paint()},'Opportunity type'),
  n('div',{class:'ub-two'},tbl,callout),
  rows.length>8?n('button',{type:'button',class:'ub-more',click:()=>{st.showAll=!st.showAll;paint()}},st.showAll?'Show fewer':'Show all '+rows.length):null,
  n('p',{class:'mut sm'},'Team targets per game = player targets ÷ player target share. Snap% is the average offensive snap share over the games he played. Snap counts are missing for some games and are left blank, never zero.'));
}

/* ---------- shared: rank-movement row ---------- */
function spark(ranks,upto){
 const pts=ranks.slice(0,upto).map((r,i)=>[i,r]).filter(x=>x[1]!=null);if(pts.length<2)return null;
 const mx=Math.max(10,...pts.map(p=>p[1])),W=160,H=44,X=i=>6+i/(upto-1||1)*(W-12),Y=r=>5+(r-1)/(mx-1)*(H-10);
 return n('svg',{viewBox:'0 0 '+W+' '+H,class:'ub-spark',role:'img','aria-label':'Weekly rank, week 1 to '+upto+' (top is best)'},
  n('polyline',{points:pts.map(p=>X(p[0]).toFixed(1)+','+Y(p[1]).toFixed(1)).join(' '),fill:'none',stroke:'#7de4c3','stroke-width':2}),
  pts.map(p=>n('circle',{cx:X(p[0]).toFixed(1),cy:Y(p[1]).toFixed(1),r:p===pts[pts.length-1]?3.5:2,fill:'#7de4c3'},n('title',{},'W'+(p[0]+1)+': rank '+p[1]))));
}
function moveRow(o){
 // o: {id,name,sub,from,to,fromTxt,toTxt,stat,why,rk,upto,max}
 const d=o.from==null?null:o.from-o.to,cls=d==null?'new':d>0?'up':d<0?'dn':'eq',txt=d==null?'NEW':d>0?'▲ '+d:d<0?'▼ '+Math.abs(d):'—';
 const frac=d==null?0:Math.min(1,Math.abs(d)/o.max);
 const axis=n('svg',{viewBox:'0 0 100 12',preserveAspectRatio:'none',class:'ub-axis',role:'img','aria-label':d==null?'new to the board':'moved '+d+' places'},n('rect',{x:0,y:3,width:100,height:6,class:'ub-bar-bg'}),
  d?n('rect',{x:d>0?50:50-frac*50,y:2,width:Math.max(frac*50,2),height:8,class:'ub-mv '+cls}):null,n('line',{x1:50,x2:50,y1:0,y2:12,stroke:'#a4bfb6','stroke-width':0.8}));
 const why=o.why&&o.why.length?n('details',{class:'ub-why'},n('summary',{},'Why'),n('ul',{},o.why.map(w=>n('li',{},n('span',{class:'tag'},w.tag),' ',w.text))),spark(o.rk,o.upto)):null;
 return n('div',{class:'ub-mrow'},
  n('div',{class:'ub-mtop'},avatar(o.id),n('div',{class:'ub-mname'},n('button',{class:'pv-link ub-pname',click:()=>open(o.id)},o.name),n('small',{},o.sub)),
   n('div',{class:'ub-mrk'},n('span',{class:'f'},o.fromTxt),n('span',{class:'ar'},'→'),n('span',{class:'t'},o.toTxt)),n('span',{class:'ub-badge '+cls},txt)),
  n('div',{class:'ub-mmid'},axis,n('span',{class:'ub-stat'},o.stat)),why);
}

/* ---------- 2. Position rank movement ---------- */
function rankSection(){
 const R=D.rank,W=D.through_week,list=R.positions[st.pos],ci=W-1,pi=W-1-st.cmp;
 const b=st.basis;
 const items=list.map(p=>({p,cur:p.rk[b][ci],prev:pi>=0?p.rk[b][pi]:null})).filter(x=>x.cur!=null);
 items.sort((a,b2)=>a.cur-b2.cur||(b2.p.ppg[b][ci]-a.p.ppg[b][ci]));
 let top=items.slice(0,st.topN);
 const mv=x=>x.prev==null?null:x.prev-x.cur;
 const ups=top.filter(x=>mv(x)>0).length,dns=top.filter(x=>mv(x)<0).length,nw=top.filter(x=>x.prev==null).length;
 if(st.sort==='move')top=[...top].sort((a,b2)=>(mv(b2)==null?-99:mv(b2))-(mv(a)==null?-99:mv(a)));
 const maxAbs=Math.max(3,...top.map(x=>Math.abs(mv(x)||0)));
 const lbl=b==='season'?'season PPR pts/game':'PPR pts/game, last 3 games';
 const rows=top.map(x=>moveRow({id:x.p.id,name:x.p.n,sub:(x.p.cur&&x.p.cur!==x.p.t?x.p.cur:x.p.t)+' · '+x.p.ppg[b][ci].toFixed(1)+' pts/g',
  from:x.prev,to:x.cur,fromTxt:x.prev==null?'unranked':st.pos+x.prev,toTxt:st.pos+x.cur,stat:'W'+(W-st.cmp)+' → W'+W,why:x.p.why,rk:x.p.rk[b],upto:W,max:maxAbs}));
 return n('section',{class:'pv-card ub-card',id:'usage-rank'},
  n('h2',{},'Position Rank Movement'),
  n('p',{class:'mut sm'},'How each player moves up and down his position board as the weeks go by, ranked by fantasy points scored (PPR). Open "Why" for the usage and context behind the move.'),
  n('div',{class:'ub-controls'},
   chips([['QB','QB'],['WR','WR'],['RB','RB'],['TE','TE']],st.pos,k=>{st.pos=k;paint()},'Position'),
   chips([['season','Season average'],['form','Last 3 games']],st.basis,k=>{st.basis=k;paint()},'Rank basis'),
   chips([[1,'vs last week'],[3,'vs 3 weeks ago']],st.cmp,k=>{st.cmp=k;paint()},'Compare to'),
   chips([[10,'Top 10'],[20,'Top 20']],st.topN,k=>{st.topN=k;paint()},'Board size'),
   chips([['rank','By rank'],['move','Biggest movers']],st.sort,k=>{st.sort=k;paint()},'Sort')),
  n('div',{class:'ub-sum'},n('b',{class:'up'},'▲ '+ups+' up'),n('b',{class:'dn'},'▼ '+dns+' down'),n('b',{},(top.length-ups-dns-nw)+' unchanged'),nw?n('b',{},nw+' new'):null,n('span',{class:'mut sm'},'Ranks are by '+lbl+' through week '+W+'. Players need at least half of the weeks played to rank on the season board.')),
  n('div',{class:'ub-mlist'},rows));
}

/* ---------- 3. Defense ---------- */
function defSection(){
 const W=D.through_week,ci=W-1,pi=W-1-st.dcmp,rush=st.dgrp==='rush',list=D.defense[st.dgrp];
 const subs=rush?[['all','All'],['DL','DL'],['OLB','OLB']]:[['all','All'],['CB','CB'],['S','Safeties']];
 const items=list.filter(p=>p.rk[ci]!=null&&(st.dsub==='all'||p.lab===st.dsub||(st.dsub==='CB'&&p.lab==='DB'&&false))).map(p=>({p,cur:p.rk[ci],prev:pi>=0?p.rk[pi]:null}));
 items.sort((a,b)=>a.cur-b.cur||a.p.n.localeCompare(b.p.n));
 // when a sub-filter is on, rank is still the overall defensive rank so movement is comparable; show top N of the filtered list
 const top=items.slice(0,st.dtop),maxAbs=Math.max(3,...top.map(x=>x.prev==null?0:Math.abs(x.prev-x.cur)));
 const fmt=p=>rush?p.tot.sk+' SK · '+p.tot.qh+' QB hits · '+p.tot.tfl+' TFL':p.tot.int+' INT · '+p.tot.pd+' PD · '+p.tot.tkl+' TKL';
 const rows=top.map(x=>moveRow({id:x.p.id,name:x.p.n,sub:x.p.t+' · '+x.p.lab+' · '+(x.p.snap==null?'snap —':Math.round(x.p.snap)+'% snaps'),from:x.prev,to:x.cur,fromTxt:x.prev==null?'unranked':'#'+x.prev,toTxt:'#'+x.cur,stat:fmt(x.p),why:x.p.why,rk:x.p.rk,upto:W,max:maxAbs}));
 return n('section',{class:'pv-card ub-card',id:'usage-def'},
  n('h2',{},'Defensive Playmakers'),
  n('p',{class:'mut sm'},rush?'Pass rushers (defensive line and outside linebackers) ranked by sacks, then QB hits, then tackles for loss. Pressures are not in our data, so QB hits stand in.':'Corners and safeties ranked by interceptions plus passes defended (plays on the ball), then interceptions.'),
  n('div',{class:'ub-controls'},
   chips([['rush','Pass rush · DL + OLB'],['cov','Coverage · CB + S']],st.dgrp,k=>{st.dgrp=k;st.dsub='all';paint()},'Defense group'),
   chips(subs,st.dsub,k=>{st.dsub=k;paint()},'Position filter'),
   chips([[1,'vs last week'],[3,'vs 3 weeks ago']],st.dcmp,k=>{st.dcmp=k;paint()},'Compare to'),
   chips([[10,'Top 10'],[20,'Top 20']],st.dtop,k=>{st.dtop=k;paint()},'Board size')),
  n('div',{class:'mut sm ub-sum'},'Season totals through week '+W+'. Rank movement compares the season-total board now vs '+(st.dcmp===1?'a week ago':'3 weeks ago')+'.'),
  n('div',{class:'ub-mlist'},rows.length?rows:text('No ranked players for this filter.')));
}

/* ---------- mount ---------- */
function paint(){
 root.replaceChildren(
  n('nav',{class:'ub-jump','aria-label':'Opportunity Board sections'},n('a',{href:'#usage-share'},'Opportunity share'),n('a',{href:'#usage-rank'},'Rank movement'),n('a',{href:'#usage-def'},'Defense'),n('a',{href:'#legacy-injuries'},'Injuries & baseline')),
  shareSection(),rankSection(),defSection());
}
(async()=>{
 try{
  D=await json('data/usage_board.json');
  const wait=window.PVNFL?.ready;if(wait)await wait;
  if(!D.usage.teams[st.team])st.team=Object.keys(D.usage.teams)[0];
  paint();
  if(location.hash){const el=document.getElementById(location.hash.slice(1));el&&el.scrollIntoView()}
 }catch(e){console.error('usage-board',e&&e.stack||e);root.replaceChildren(card('Usage boards unavailable',text('The usage data could not be loaded right now. The rest of this page is unchanged.')))}
})();
})();
