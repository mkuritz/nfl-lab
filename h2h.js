/* Head-to-Head Prop Advantage: shared renderer (h2h.html + Lines toggle). Display only. */
(function(){
var E=function(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})};
var OPEN={};
function n1(x){return x==null?"—":(Math.round(x*10)/10)}
function stTag(s){if(!s||!s.st)return "";var c=/Out|Reserve|Inactive|Suspended|PUP|Injury/.test(s.st)?"var(--bad)":/Doubtful/.test(s.st)?"#fb923c":/Questionable/.test(s.st)?"#facc15":"var(--acc2)";
 return ' <span class="h2-st" style="color:'+c+';border-color:'+c+'">'+E(s.st)+(s.d?' · '+E(s.d):'')+'</span>'}
function pname(p){return p.pid?'<a href="#" data-pid="'+E(p.pid)+'">'+E(p.name)+'</a>':E(p.name)}
function card(p,t,T){var s=p.summary,G=p.games||[],stat="";
 if(s){if(p.def){stat=s.g+' G · '+s.tk+' tkl · '+s.sk+' sk · '+s.int+' INT'}
 else{var b=[];if(p.pos=="QB")b.push(s.py_g+' pass yds/g · '+s.td+' pass TD · '+s.int+' INT · 300+: '+s.p300+'/'+s.g);
  if(s.ry_g>=5||p.pos=="RB")b.push(s.car_g+' car · '+s.ry_g+' rush yds/g');if(p.pos!="QB")b.push(s.tgt_g+' tgt · '+s.rec_g+' rec · '+s.recy_g+' rec yds/g');
  if(p.pos!="QB")b.push('80+: <b>'+s.scr80+'/'+s.g+'</b> · 100+: <b class="up">'+s.scr100+'/'+s.g+'</b>');b.push(s.skill_td+' rush/rec TD');stat=b.join(' · ')}}
 else stat='<span class="mut">No games vs '+E(T.opp)+' yet.</span>';
 var k=t+p.name,op=OPEN[k];
 var gl=G.map(function(g){var c=g.season+' '+(g.stage?g.stage:'Wk '+g.week);
  var l=p.def?(g.tk+' tkl'+(g.sk?' · '+g.sk+' sk':'')+(g.int?' · '+g.int+' INT':'')+(g.pd?' · '+g.pd+' PD':'')):
   [g.att?g.cmp+'/'+g.att+', '+g.py+' yds, '+g.ptd+' TD, '+g.pint+' INT':'',g.car?g.car+'-'+g.ry+(g.rtd?'-'+g.rtd+' TD':'')+' rush':'',(g.tgt||g.rec)?g.rec+'-'+g.recy+(g.rectd?'-'+g.rectd+' TD':'')+' rec ('+g.tgt+' tgt)':''].filter(Boolean).join(' · ')||'—';
  var big=!p.def&&p.pos!="QB"&&(g.ry+g.recy)>=100;
  return '<tr><td>'+E(g.date)+'</td><td>'+E(c)+'</td><td>'+E(g.team)+'</td><td'+(big?' class="up"':'')+'>'+l+'</td></tr>'}).join("");
 var rows=gl.split('</tr>').filter(Boolean);
 var pr=(p.props||[]).map(function(q){
  var why=[];if(q.inj_add)why.push('+'+n1(q.inj_add)+' vacated');if(q.def_pct)why.push('+'+q.def_pct+'% opp. defenders out');
  return '<tr'+(q.adv?' class="h2-adv"':'')+'><td>'+E(q.market)+'</td><td><b>'+n1(q.h2h)+'</b>'+(q.h2h_g?' <span class="mut">('+q.h2h_g+' G)</span>':'')+'</td><td>'+n1(q.line)+'</td><td>'+n1(q.base)+'</td><td><b>'+n1(q.proj)+'</b>'+(why.length?'<div class="mut" style="font-size:10.5px">'+why.join(' · ')+'</div>':'')+'</td><td>'+(q.adv?'<span class="tag" style="background:#22c55e22;color:var(--acc2)">▲ Prop advantage</span>':'<span class="mut">—</span>')+'</td></tr>'}).join("");
 var adv=(p.props||[]).some(function(q){return q.adv});
 return '<div class="card h2-card" style="margin:0;background:var(--panel2)'+(adv?';border-color:#22c55e88':'')+'"><div style="display:flex;justify-content:space-between;gap:6px;align-items:baseline;flex-wrap:wrap"><b>'+pname(p)+' <span class="mut">'+E(t)+' '+E(p.pos)+' · vs '+E(T.opp)+'</span>'+stTag(p.status)+'</b><span class="tag">'+(s?s.g:0)+' G vs '+E(T.opp)+'</span></div>'+
  '<div class="sm" style="margin-top:4px">'+stat+'</div>'+
  (p.adj&&p.adj.from&&p.adj.from.length?'<div class="sm mut" style="margin-top:3px">Vacated volume: +'+p.adj.tg+' tgt/g'+(p.adj.ca?', +'+p.adj.ca+' car/g':'')+' (from '+E(p.adj.from.join(", "))+' out)</div>':'')+
  (pr?'<div class="wrap" style="margin-top:6px"><table class="h2-pt"><tr><th>Market</th><th>H2H avg</th><th>Line</th><th>Season avg</th><th>Injury-adj. proj.</th><th></th></tr>'+pr+'</table></div>':'')+
  (rows.length?'<div class="wrap" style="margin-top:6px"><table><tr><th>Date</th><th>Game</th><th>Team</th><th>Line</th></tr>'+(op?rows:rows.slice(0,3)).join('</tr>')+'</tr></table></div>':'')+
  (rows.length>3?'<button class="chip" style="margin-top:6px" data-ho="'+E(k)+'">'+(op?'Show fewer':'Show all '+rows.length+' games')+'</button>':'')+'</div>'}
function missing(t,T){var M=T.missing||{},P=M.players||[],D=(T.opp_def_out||{}).out||[];
 var h='<div class="card" style="margin:0;grid-column:1/-1;background:var(--panel2);border-color:#f8717166"><b>🩹 Missing production · '+E(t)+' vs '+E(T.opp)+'</b>';
 if(!P.length)h+='<p class="sm mut" style="margin:4px 0 0">No '+E(t)+' skill players are listed out.</p>';
 else{h+='<div class="wrap" style="margin-top:6px"><table><tr><th>Out tonight</th><th>Status</th><th>G vs '+E(T.opp)+'</th><th>Tgt/g</th><th>Rec yds/g</th><th>Rush yds/g</th><th>TD</th><th>100+</th><th>2026 tgt/car per g</th></tr>'+
  P.map(function(m){var s=m.h2h;return '<tr><td>'+pname(m)+' <span class="mut">'+E(m.pos)+'</span>'+(m.fresh?'':' <span class="mut sm">(already missing recent games)</span>')+'</td><td>'+E(m.status)+'</td><td>'+(s?s.g:0)+'</td><td>'+(s?s.tgt_g:'—')+'</td><td>'+(s?s.recy_g:'—')+'</td><td>'+(s?s.ry_g:'—')+'</td><td>'+(s?s.skill_td+(m.pos=="QB"?' + '+s.td+' pass':''):'—')+'</td><td>'+(s?s.scr100+'/'+s.g:'—')+'</td><td>'+n1(m.tg_g26)+' / '+n1(m.ca_g26)+'</td></tr>'}).join("")+'</table></div>';
  if(M.h2h_g)h+='<p class="sm" style="margin:6px 0 0">Historically vs '+E(T.opp)+', these players combined for <b>'+M.h2h_tgt_g+' targets</b>, <b>'+M.h2h_recy_g+' receiving yds</b> and <b>'+M.h2h_ry_g+' rushing yds</b> per game they played, and <b>'+M.h2h_td+' rush/rec TDs</b>.</p>';
  h+='<p class="sm" style="margin:4px 0 0">Vacated 2026 volume from fresh absences: <b>'+M.tg_g+' targets/g</b> and <b>'+M.ca_g+' RB carries/g</b>.</p>';
  if((M.beneficiaries||[]).length)h+='<p class="sm" style="margin:4px 0 0">Likely to absorb it: '+M.beneficiaries.map(function(b){return '<b>'+E(b.name)+'</b> <span class="mut">('+[b.tg?'+'+b.tg+' tgt':'',b.ca?'+'+b.ca+' car':''].filter(Boolean).join(', ')+', ≈+'+b.yds+' yds)</span>'}).join(' · ')+'</p>'}
 h+='<p class="sm" style="margin:6px 0 0">'+(D.length?'🛡️ '+E(T.opp)+' defenders out: '+D.map(function(d){return '<b>'+E(d.name)+'</b> <span class="mut">'+E(d.pos)+' · '+E(d.status)+'</span>'}).join(' · '):'<span class="mut">No regular '+E(T.opp)+' defenders listed out.</span>')+'</p></div>';return h}
function render(box,G,t,opts){opts=opts||{};var T=G.teams[t],P=T.players,o=P.filter(function(p){return!p.def}),d=P.filter(function(p){return p.def});
 var h='<div class="chips" style="grid-column:1/-1;margin:0">'+Object.keys(G.teams).map(function(x){return '<button class="chip '+(x==t?"on":"")+'" data-ht="'+E(x)+'">'+E(x)+' vs '+E(G.teams[x].opp)+' ('+G.teams[x].players.filter(function(p){return p.summary}).length+' with history)</button>'}).join("")+'</div>'+
  missing(t,T)+o.map(function(p){return card(p,t,T)}).join("")+(d.length?'<h3 style="grid-column:1/-1;margin:6px 0 0">DEFENDERS WITH SACKS OR INTs VS '+E(T.opp)+'</h3>'+d.map(function(p){return card(p,t,T)}).join(""):'');
 box.innerHTML=h;
 box.querySelectorAll("[data-ht]").forEach(function(b){b.onclick=function(){opts.onTeam&&opts.onTeam(b.dataset.ht)}});
 box.querySelectorAll("[data-ho]").forEach(function(b){b.onclick=function(){OPEN[b.dataset.ho]=!OPEN[b.dataset.ho];render(box,G,t,opts)}});
 box.querySelectorAll("a[data-pid]").forEach(function(a){a.onclick=function(e){e.preventDefault();e.stopPropagation();window.NFLProfile&&NFLProfile(a.dataset.pid)}})}
function pickGame(D){var now=Date.now(),up=D.games.filter(function(g){return Date.parse(g.time)+4*36e5>now});return (up[0]||D.games[D.games.length-1])}
var css=document.createElement("style");css.textContent='.h2-st{display:inline-block;margin-left:6px;padding:0 6px;border:1px solid;border-radius:999px;font-size:10px;font-weight:800}.h2-pt td,.h2-pt th{white-space:nowrap}.h2-adv td{background:#22c55e12}';document.head.appendChild(css);
window.H2H={render:render,pickGame:pickGame,E:E};
})();
