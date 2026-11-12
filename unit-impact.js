/* Unit Board · Matchup Impact. Display-only.
   Turns team efficiency into points, passing yards, rushing yards and sacks versus an average opponent.
   Data: data/unit_impact.json (scripts/build_unit_impact.py). Conversions are least-squares slopes fitted on
   our own 2025 + current-season team games (see the method panel and the script header); none are hand-set.
   Unit points = fitted points-per-EPA slope x (EPA/play edge) x the offense's plays per game. */
(function(){'use strict';
const {node:n,text,card,select,json}=PV;
const root=document.getElementById('impact-app');if(!root)return;
const Q=new URLSearchParams(location.search);
let U,st={a:Q.get('a')||null,b:Q.get('b')||null};
const sg=(v,d=1)=>(v>=0?'+':'−')+Math.abs(v).toFixed(d);
const tier=r=>r<=10?'good':r>=23?'bad':'mid';
function center(v,scale,good){ // diverging bar, positive = favors offense side (right)
 const f=Math.max(-1,Math.min(1,v/scale));
 return n('svg',{viewBox:'0 0 100 12',preserveAspectRatio:'none',class:'ub-axis',role:'img','aria-label':sg(v)+' versus average'},
  n('rect',{x:0,y:3,width:100,height:6,class:'ub-bar-bg'}),
  Math.abs(f)>0.005?n('rect',{x:f>0?50:50+f*50,y:2,width:Math.max(Math.abs(f)*50,1.5),height:8,class:'ub-mv '+((f>0)===good?'up':'dn')}):null,
  n('line',{x1:50,x2:50,y1:0,y2:12,stroke:'#a4bfb6','stroke-width':0.8}));
}
function effect(A,B){
 const F=U.fit,L=U.league,a=U.teams[A],b=U.teams[B],o={};
 const ok=k=>F[k]&&!F[k].withheld;
 if(ok('pass_yds'))o.pass=F.pass_yds.k_off*(a.pass_o-L.pass_epa)+F.pass_yds.k_def*(b.pass_d-L.pass_def_epa);
 if(ok('rush_yds'))o.rush=F.rush_yds.k_off*(a.rush_o-L.rush_epa)+F.rush_yds.k_def*(b.rush_d-L.rush_def_epa);
 if(ok('sacks'))o.sacks=F.sacks.k_off*(a.sack_o-L.sack_rate)+F.sacks.k_def*(b.sack_d-L.sack_rate_def);
 if(ok('points')){
  const k=F.points;
  o.ptsPass=(k.k_off*(a.pass_o-L.pass_epa)+k.k_def*(b.pass_d-L.pass_def_epa))*a.pass_pg;
  o.ptsRush=(k.k_off*(a.rush_o-L.rush_epa)+k.k_def*(b.rush_d-L.rush_def_epa))*a.rush_pg;
  o.pts=o.ptsPass+o.ptsRush;
 }
 return o;
}
const chip=(label,r)=>n('span',{class:'ui-rk '+tier(r)},label+' #'+r);
function line(label,big,unit,bar,note,chips){
 return n('div',{class:'ui-line'},n('div',{class:'ui-lh'},n('span',{class:'ui-lab'},label),n('b',{class:'ui-val'},big,n('small',{},' '+unit))),bar,n('div',{class:'ui-note'},chips,note?n('span',{class:'mut sm'},note):null));
}
function dirCard(A,B){
 const e=effect(A,B),a=U.teams[A],b=U.teams[B];
 const ptsLine=e.pts==null?null:line('Points',sg(e.pts),'pts / game vs average',center(e.pts,4,true),'Pass '+sg(e.ptsPass)+' · Rush '+sg(e.ptsRush),null);
 const pass=e.pass==null?null:line('Passing yards',sg(e.pass,0),'yds vs average',center(e.pass,40,true),null,[chip(A+' pass O',a.rk.pass_o),chip(B+' pass D',b.rk.pass_d)]);
 const rush=e.rush==null?null:line('Rushing yards',sg(e.rush,0),'yds vs average',center(e.rush,30,true),null,[chip(A+' run O',a.rk.rush_o),chip(B+' run D',b.rk.rush_d)]);
 const sacks=e.sacks==null?null:line('Sacks taken',sg(e.sacks,2),'per game vs average',center(e.sacks,1,false),e.sacks>0?'More sacks than usual for '+A:'Fewer sacks than usual for '+A,[chip(A+' protection',a.rk.sack_o),chip(B+' pass rush',b.rk.sack_d)]);
 return n('section',{class:'pv-card ui-dir'},n('h2',{},A+' offense vs '+B+' defense'),n('p',{class:'mut sm'},'Versus what an average offense does against an average defense. #1 = best of 32.'),ptsLine,pass,rush,sacks);
}
function netFor(A,B){const x=effect(A,B),y=effect(B,A);return x.pts==null||y.pts==null?null:x.pts-y.pts}
function lineCtx(A,B){
 const g=U.slate.find(x=>(x.away===A&&x.home===B)||(x.away===B&&x.home===A));if(!g||g.spread_home==null)return null;
 // schedule feed convention: spread_home > 0 means the home team is favored
 const fav=g.spread_home>0?g.home:g.away,pts=Math.abs(g.spread_home);
 return {g,text:'Posted line: '+(pts===0?'pick’em':fav+' −'+pts)+(g.total!=null?' · total '+g.total:'')};
}
function headline(A,B){
 const net=netFor(A,B);
 if(net==null)return card('Unit matchup',text('Impact conversions are unavailable in this snapshot.'));
 const fav=net>=0?A:B,mag=Math.abs(net),even=mag<0.3,ctx=lineCtx(A,B);
 const f=Math.max(-1,Math.min(1,net/6));
 const meter=n('svg',{viewBox:'0 0 100 14',preserveAspectRatio:'none',class:'ui-tug',role:'img','aria-label':even?'Even':fav+' favored by '+mag.toFixed(1)+' points'},
  n('rect',{x:0,y:4,width:100,height:6,class:'ub-bar-bg'}),n('rect',{x:f>0?50:50+f*50,y:3,width:Math.max(Math.abs(f)*50,1),height:8,class:'ub-mv up'}),n('line',{x1:50,x2:50,y1:0,y2:14,stroke:'#a4bfb6','stroke-width':0.8}));
 return n('section',{class:'pv-card ui-head'},
  n('div',{class:'ui-hrow'},
   n('div',{class:'ui-hnum'},n('span',{class:'num'},even?'EVEN':sg(mag)),even?null:n('span',{class:'u'},'PTS')),
   n('div',{class:'ui-hcap'},n('b',{},even?'The units cancel out':'Unit matchup favors '+fav.toUpperCase()),n('span',{},even?'Neither side has a clear efficiency edge.':'Worth about '+mag.toFixed(1)+' points to '+fav+'’s side of the spread, from offense and defense efficiency alone.'),ctx?n('span',{class:'mut'},ctx.text+' (for context, not a pick).'):null)),
  n('div',{class:'ui-tugrow'},n('span',{class:'ub-stat'},B),meter,n('span',{class:'ub-stat'},A)),
  n('p',{class:'mut sm'},'Does not include QB or injury changes, special teams, home field or weather.'));
}
function slate(A,B){
 if(!U.slate.length)return null;
 const rows=U.slate.map(g=>({g,net:netFor(g.away,g.home)})).filter(x=>x.net!=null).sort((x,y)=>Math.abs(y.net)-Math.abs(x.net));
 if(!rows.length)return null;
 return n('section',{class:'pv-card ui-slate'},n('h2',{},'This week’s slate: where the units tilt'),
  n('p',{class:'mut sm'},'Points of spread value from offense/defense efficiency, away side on the right. Tap a game to open it above.'),
  rows.map(({g,net})=>{
   const f=Math.max(-1,Math.min(1,net/6)),fav=net>=0?g.away:g.home;
   const ctx=g.spread_home==null?'':(g.spread_home>0?g.home+' −'+g.spread_home:g.spread_home<0?g.away+' −'+Math.abs(g.spread_home):'pick’em');
   return n('button',{type:'button',class:'ui-srow'+((g.away===A&&g.home===B)||(g.away===B&&g.home===A)?' on':''),click:()=>{st.a=g.away;st.b=g.home;paint();root.scrollIntoView()}},
    n('span',{class:'ui-sg'},g.away+' @ '+g.home),
    n('svg',{viewBox:'0 0 100 12',preserveAspectRatio:'none',class:'ub-axis',role:'img','aria-label':fav+' favored by '+Math.abs(net).toFixed(1)},n('rect',{x:0,y:3,width:100,height:6,class:'ub-bar-bg'}),n('rect',{x:f>0?50:50+f*50,y:2,width:Math.max(Math.abs(f)*50,1),height:8,class:'ub-mv up'}),n('line',{x1:50,x2:50,y1:0,y2:12,stroke:'#a4bfb6','stroke-width':0.8})),
    n('span',{class:'ui-sv'},Math.abs(net)<0.3?'even':fav+' '+sg(Math.abs(net))),n('span',{class:'ui-sl mut'},ctx));
  }));
}
function method(){
 const F=U.fit,row=(l,k,unit)=>F[k]?n('tr',{},n('td',{},l),n('td',{},F[k].withheld?'withheld (unstable fit)':'+0.10 '+unit+' edge ≈ '+(k==='points'?'':'')+(F[k].k_off*0.10).toFixed(1)),n('td',{},F[k].n),n('td',{},(F[k].r2*100).toFixed(0)+'%')):null;
 return n('details',{class:'pv-data ui-method'},n('summary',{},'How these numbers are built'),
  text('For every team game from week 4 on in 2025 and this season, we compare what actually happened (points scored, passing yards, rushing yards, sacks taken) with the offense’s and the opponent defense’s efficiency before that game, season to date and adjusted to the league average. The slope of that relationship is the conversion shown above. Because pre-game efficiency is a noisy read, the slopes already shrink toward the average, so the numbers are conservative and describe the typical effect, not a guarantee for one game.'),
  n('div',{class:'pv-scroll'},n('table',{},n('thead',{},n('tr',{},['Measure','Offense edge worth','Team games','Share of game-to-game swing explained'].map(x=>n('th',{},x)))),n('tbody',{},
   row('Points','points','EPA/play-equivalent'),
   F.pass_yds?n('tr',{},n('td',{},'Passing yards'),n('td',{},'+0.10 pass EPA/play ≈ '+(F.pass_yds.k_off*0.1).toFixed(0)+' yds'),n('td',{},F.pass_yds.n),n('td',{},(F.pass_yds.r2*100).toFixed(0)+'%')):null,
   F.rush_yds?n('tr',{},n('td',{},'Rushing yards'),n('td',{},'+0.10 rush EPA/play ≈ '+(F.rush_yds.k_off*0.1).toFixed(0)+' yds'),n('td',{},F.rush_yds.n),n('td',{},(F.rush_yds.r2*100).toFixed(0)+'%')):null,
   F.sacks?n('tr',{},n('td',{},'Sacks taken'),n('td',{},'+1 pt sack rate ≈ '+(F.sacks.k_off*0.01).toFixed(2)+' sacks'),n('td',{},F.sacks.n),n('td',{},(F.sacks.r2*100).toFixed(0)+'%')):null,
   F.points?n('tr',{},n('td',{},'Points'),n('td',{},'+1 EPA/game edge ≈ '+F.points.k_off.toFixed(2)+' pts (defense: '+F.points.k_def.toFixed(2)+')'),n('td',{},F.points.n),n('td',{},(F.points.r2*100).toFixed(0)+'%')):null))),
  text('Single games are noisy, so the explained share is small by nature; the slopes are still statistically meaningful. Points use the Hub power rating’s own unit, EPA per game. Snapshot through week '+U.through_week+'; rebuilt in the daily Hub refresh.','mut sm'));
}
function paint(){
 const teams=Object.keys(U.teams).sort(),A=st.a,B=st.b;
 const tsel=(label,key)=>select(label,teams.map(t=>[t,t]),st[key],v=>{st[key]=v;paint()});
 const slateChips=U.slate.length?n('div',{class:'ub-chips ui-games',role:'group','aria-label':'Games this week'},U.slate.map(g=>n('button',{type:'button',class:(g.away===A&&g.home===B)?'on':'',click:()=>{st.a=g.away;st.b=g.home;paint()}},g.away+' @ '+g.home))):null;
 root.replaceChildren(
  n('section',{class:'pv-card'},n('h2',{},'Matchup Impact'),n('p',{class:'mut sm'},'Pick a game or any two teams. Efficiency numbers are converted into points, yards and sacks versus an average opponent, so you can see what the matchup is worth.'),slateChips,n('div',{class:'ub-controls'},tsel('Team A','a'),tsel('Team B','b'))),
  headline(A,B),
  n('div',{class:'pv-grid ui-grid'},dirCard(A,B),dirCard(B,A)),
  slate(A,B),method());
}
(async()=>{
 try{
  U=await json('data/unit_impact.json');
  if(!U.slate)U.slate=[];
  const teams=Object.keys(U.teams);
  if(!st.a||!U.teams[st.a]||!st.b||!U.teams[st.b]){const g=U.slate[0];st.a=g?g.away:teams[0];st.b=g?g.home:teams[1]}
  paint();
 }catch(e){console.error('unit-impact',e&&e.stack||e);root.replaceChildren(card('Matchup impact unavailable',text('The impact data could not be loaded right now. The efficiency views below are unchanged.')))}
})();
})();
