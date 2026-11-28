/* NFL First TD Scorer board (preview). One renderer shared by NFL Hub and Bet Lab. SLFirstTD.mount(el,{compact,link}) */
(function(){
var LOCAL=/^(localhost|127\.|0\.0\.0\.0)/.test(location.hostname);
var SRC=LOCAL?"./preview-data/nfl_first_td.json":"https://betlab.sportslabshq.com/data/nfl_first_td.json";
var css=`.ftd{--ftd-acc:#53e3a6;--ftd-acc2:#3fa9ff;--ftd-gold:#ffc857;--ftd-line:#ffffff14;--ftd-mut:#8b97b0;font-size:13.5px}
.ftd .ftd-card{background:#121826;border:1px solid #243049;border-radius:16px;padding:14px 14px 12px;margin:0 0 12px}
.ftd h2{margin:0 0 4px;font-size:18px}.ftd h3{margin:0 0 6px;font-size:14px}.ftd .m{color:var(--ftd-mut);font-size:12px}
.ftd .pills{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:10px 0 4px}
.ftd .pill{background:#ffffff0d;border:1px solid #ffffff22;color:inherit;border-radius:999px;padding:6px 12px;font:inherit;font-size:12.5px;cursor:pointer;white-space:nowrap}
.ftd .pill.on{background:var(--ftd-acc);border-color:var(--ftd-acc);color:#06120c;font-weight:800}
.ftd select.pill{appearance:none;-webkit-appearance:none;padding-right:26px;background-image:linear-gradient(45deg,transparent 50%,#8b97b0 50%),linear-gradient(135deg,#8b97b0 50%,transparent 50%);background-position:calc(100% - 14px) 52%,calc(100% - 9px) 52%;background-size:5px 5px;background-repeat:no-repeat}
.ftd select.pill option{background:#121826}
.ftd .games{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px;margin-top:8px}
.ftd .gm{border:1px solid var(--ftd-line);border-radius:14px;padding:9px 10px;background:#ffffff05;cursor:pointer}.ftd .gm.on{border-color:var(--ftd-acc)}
.ftd .gm b{font-size:13px}.ftd .bar{display:flex;height:8px;border-radius:99px;overflow:hidden;margin:6px 0 4px;background:#0b1326}
.ftd .bar i{display:block;height:100%}.ftd .k{display:flex;flex-wrap:wrap;gap:4px 10px;font-size:11px;color:var(--ftd-mut)}.ftd .k span:before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px;background:var(--c)}
.ftd .row{display:grid;grid-template-columns:1.6fr 1fr 1fr;gap:4px 12px;align-items:center;padding:10px 12px;border:1px solid var(--ftd-line);border-radius:14px;background:#ffffff06;margin-top:7px}
.ftd .row .why{grid-column:1/-1;color:#aab4cc;font-size:12px}
.ftd .tb{display:inline-block;font-size:10px;font-weight:900;border-radius:999px;padding:2px 8px;margin-right:6px;letter-spacing:.03em}
.ftd .tb.Value{background:var(--ftd-acc);color:#06120c}.ftd .tb.Lean{background:#3fa9ff26;color:#8fc9ff;border:1px solid #3fa9ff66}.ftd .tb.Pass{background:#ffffff10;color:#8b97b0}
.ftd .tb.Listed{color:#8b97b0;border:1px solid #ffffff22}.ftd .tb.Hold{background:#f5b94222;color:#f5c66b;border:1px solid #f5b94266}
.ftd .px{font-weight:800;font-size:15px}.ftd .viz{position:relative;height:6px;background:#0b1326;border:1px solid #243556;border-radius:99px;margin:4px 0;max-width:170px}
.ftd .viz i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#10b981,#8ee04a)}.ftd .viz u{position:absolute;top:-2px;bottom:-2px;width:2px;background:#38d0f0}
.ftd details.res{border:1px solid #243049;border-radius:16px;background:#121826;padding:0;margin-top:12px}
.ftd details.res summary{cursor:pointer;list-style:none;padding:12px 14px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-weight:800}
.ftd details.res summary::-webkit-details-marker{display:none}.ftd details.res summary:after{content:"▾";margin-left:auto;color:var(--ftd-mut)}.ftd details[open].res summary:after{content:"▴"}
.ftd .cnt{border-radius:999px;padding:3px 10px;font-size:12px;font-weight:800;background:#ffffff0d;border:1px solid #ffffff1f}.ftd .cnt.W{color:#53e3a6}.ftd .cnt.L{color:#ff7a85}.ftd .cnt.V{color:#c9d1e3}.ftd .cnt.P{color:#ffc857}
.ftd .rb{padding:0 14px 14px}.ftd table{width:100%;border-collapse:collapse;font-size:12.5px}.ftd th,.ftd td{padding:6px;border-bottom:1px solid var(--ftd-line);text-align:left}.ftd th{color:#9aa4c7;font-size:10.5px;text-transform:uppercase}
.ftd .tag{display:inline-block;font-size:10px;font-weight:900;border-radius:999px;padding:1px 7px;background:#ffffff10}.ftd .tag.W{background:#53e3a633;color:#53e3a6}.ftd .tag.L{background:#ff5d6c26;color:#ff8f98}.ftd .tag.V{color:#c9d1e3}
.ftd .prev{display:inline-block;font-size:10px;font-weight:900;border-radius:999px;padding:2px 8px;background:#a78bfa22;color:#c4b5fd;border:1px solid #a78bfa55;margin-left:6px;vertical-align:middle}
@media(max-width:640px){.ftd .games{display:grid;grid-auto-flow:column;grid-auto-columns:78%;grid-template-columns:none;overflow-x:auto;-webkit-overflow-scrolling:touch;scroll-snap-type:x mandatory;padding-bottom:4px}.ftd .gm{scroll-snap-align:start}.ftd .row{grid-template-columns:1fr 1fr}.ftd .row>span:first-child{grid-column:1/-1}.ftd .pills{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:4px}.ftd .hm{display:none}}`;
var st=document.createElement("style");st.textContent=css;document.head.appendChild(st);
var E=function(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})};
var am=function(p){return p==null?"—":(p>0?"+"+p:""+p)},pc=function(x,d){return x==null?"—":(x*100).toFixed(d==null?1:d)+"%"};
var tm=function(t){return new Date(t).toLocaleString("en-US",{timeZone:"America/New_York",weekday:"short",hour:"numeric",minute:"2-digit"})+" ET"};
var COL={team1:"#53e3a6",team2:"#3fa9ff",def:"#f59e0b",none:"#6b7280",un:"#334155"};
function gameCard(g,on){var t=Object.keys(g.team_first||{});var a=g.matchup.split(" @ ")[0],h=g.matchup.split(" @ ")[1];var A=(g.team_first||{})[a]||0,H=(g.team_first||{})[h]||0;
 return '<div class="gm'+(on?' on':'')+'" data-g="'+E(g.game)+'"><b>'+E(g.matchup)+'</b> <span class="m">'+tm(g.time)+'</span>'+
 '<div class="bar"><i style="width:'+A*100+'%;background:'+COL.team1+'"></i><i style="width:'+H*100+'%;background:'+COL.team2+'"></i><i style="width:'+g.def_st*100+'%;background:'+COL.def+'"></i><i style="width:'+g.no_td*100+'%;background:'+COL.none+'"></i></div>'+
 '<div class="k"><span style="--c:'+COL.team1+'">'+E(a)+' '+pc(A,0)+'</span><span style="--c:'+COL.team2+'">'+E(h)+' '+pc(H,0)+'</span><span style="--c:'+COL.def+'">D/ST '+pc(g.def_st,1)+'</span><span style="--c:'+COL.none+'">No TD '+pc(g.no_td,1)+'</span></div><div class="m" style="margin-top:3px">Board players '+pc(g.listed_cal!=null?g.listed_cal:g.listed,0)+' · everyone else '+pc(g.unlisted,0)+'</div></div>'}
function row(r,link){return '<div class="row"><span><span class="tb '+r.tier+'">'+(r.tier=="Hold"?"⏳ HOLD":r.tier.toUpperCase())+'</span><b>'+E(r.player)+'</b> <span class="m">'+E(r.team)+' '+E(r.pos)+' · '+E(r.matchup)+' · '+tm(r.time)+'</span></span>'+
 '<span><b>'+pc(r.pf)+'</b> <span class="m">first TD chance</span><div class="viz"><i style="width:'+Math.min(100,r.pf/0.2*100)+'%"></i>'+(r.nv==null?"":'<u style="left:'+Math.min(97,Math.max(2,r.nv/0.2*100))+'%" title="No-vig '+pc(r.nv)+'"></u>')+'</div><span class="m">fair '+am(r.fair)+(r.nv==null?"":' · no-vig '+pc(r.nv))+(r.ev==null?"":' · EV '+(r.ev>=0?"+":"")+(r.ev*100).toFixed(0)+'%')+'</span></span>'+
 '<span>'+(r.price==null?'<span class="m">No price yet</span>':'<span class="px">'+am(r.price)+'</span> <span class="m">'+E(r.book)+'</span>')+'</span><span class="why">'+E(r.why)+'</span></div>'}
function results(d){var R=d.results||{W:0,L:0,V:0,P:0,recent:[],by_tier:{}},B=d.backtest;
 var cnt=function(k,l){return '<span class="cnt '+k+'">'+l+' '+(R[k]||0)+'</span>'};
 var h='<details class="res"><summary>📊 Results & accuracy '+cnt("W","Won")+cnt("L","Lost")+cnt("V","Void")+cnt("P","Pending")+(R.units!=null?'<span class="cnt">'+(R.units>=0?"+":"")+R.units+'u</span>':'')+'</summary><div class="rb">';
 h+='<div class="m" style="margin-bottom:8px">Graded from the play-by-play: the first touchdown of the game, by its scorer. A player who never appears in the box score is a Void. Rows lock at kickoff; Value and Lean only, 1 unit each.</div>';
 var bt=R.by_tier||{};h+=Object.keys(bt).map(function(t){var x=bt[t];return '<span class="cnt">'+E(t)+': '+x.W+'-'+x.L+(x.V?' · '+x.V+' void':'')+(x.P?' · '+x.P+' pending':'')+'</span> '}).join("");
 h+=R.recent&&R.recent.length?'<div style="overflow:auto;margin-top:8px"><table><tr><th>Player</th><th class="hm">Game</th><th>Tier</th><th>Price</th><th>Result</th><th class="hm">First TD</th></tr>'+R.recent.map(function(e){return '<tr><td><b>'+E(e.player)+'</b> <span class="m">'+E(e.team)+'</span></td><td class="hm m">'+E(e.matchup)+'</td><td>'+E(e.tier)+'</td><td>'+am(e.price)+'</td><td><span class="tag '+(e.res||"")+'">'+(e.res||"Pending")+'</span></td><td class="hm m">'+E(e.first||"")+'</td></tr>'}).join("")+'</table></div>':'<div class="m" style="margin-top:8px">No graded picks yet. The first slate is graded once its games are final.</div>';
 if(B){h+='<h3 style="margin-top:14px">Backtest (chances, not profit)</h3><div class="m">'+E(B.note)+' '+B.games+' games, '+B.players+' listed players: '+B.first_td_by_listed+' first TDs vs '+B.expected+' expected.</div><div style="overflow:auto"><table><tr><th>Our chance</th><th>Players</th><th>Avg predicted</th><th>Actual</th></tr>'+(B.bins||[]).map(function(b){return '<tr><td>'+E(b.band)+'</td><td>'+b.n+'</td><td>'+pc(b.pred)+'</td><td>'+pc(b.hit)+' <span class="m">('+b.w+')</span></td></tr>'}).join("")+'</table></div>'}
 return h+'</div></details>'}
function mount(el,o){o=o||{};el.classList.add("ftd");el.innerHTML='<div class="m">Loading…</div>';
 (window.__ftdP=window.__ftdP||fetch(SRC+"?t="+Date.now()).then(function(r){return r.json()})).then(function(d){
  var S={tier:"",game:"",team:"",pos:"",sort:"pf",n:25},R=d.rows||[];
  var teams=[...new Set(R.map(function(r){return r.team}))].sort();
  function draw(){var L=R.filter(function(r){return (!S.tier||r.tier==S.tier)&&(!S.game||r.game==S.game)&&(!S.team||r.team==S.team)&&(!S.pos||r.pos==S.pos)});
   var nz=function(x,v){return x==null?v:x};L.sort(function(a,b){return S.sort=="price"?nz(a.price,1e9)-nz(b.price,1e9):nz(b[S.sort],-9)-nz(a[S.sort],-9)});
   var more=0;if(o.compact)L=L.slice(0,o.compact);else if(L.length>S.n){more=L.length-S.n;L=L.slice(0,S.n)}
   var cnt=function(t){return R.filter(function(r){return r.tier==t}).length};
   var pill=function(k,v,l){return '<button class="pill'+(S[k]==v?' on':'')+'" data-k="'+k+'" data-v="'+E(v)+'">'+l+'</button>'};
   el.innerHTML='<div class="ftd-card"><h2>🥇 First TD Scorer <span class="prev">PREVIEW</span></h2><div class="m">'+R.length+' players · '+(d.games||[]).length+' games · updated '+new Date(d.updated).toLocaleTimeString("en-US",{timeZone:"America/New_York",hour:"numeric",minute:"2-digit"})+' ET · its own model, separate from Anytime TD</div>'+
   (o.compact?'':'<div class="games">'+(d.games||[]).map(function(g){return gameCard(g,S.game==g.game)}).join("")+'</div>')+
   '<div class="pills">'+pill("tier","","All")+pill("tier","Value","Value "+cnt("Value"))+pill("tier","Lean","Lean "+cnt("Lean"))+pill("tier","Pass","Pass")+pill("tier","Hold","⏳ Holds "+cnt("Hold"))+pill("tier","Listed","No price")+
   (o.compact?'':'<select class="pill" data-sel="team"><option value="">All teams</option>'+teams.map(function(t){return '<option'+(S.team==t?' selected':'')+'>'+E(t)+'</option>'}).join("")+'</select><select class="pill" data-sel="pos"><option value="">All positions</option>'+["RB","WR","TE","QB"].map(function(t){return '<option'+(S.pos==t?' selected':'')+'>'+t+'</option>'}).join("")+'</select>')+
   '</div><div class="pills"><span class="m">Sort</span>'+pill("sort","pf","First TD chance")+pill("sort","ev","Edge")+pill("sort","price","Price")+'</div>'+
   (L.length?L.map(function(r){return row(r)}).join(""):'<div class="m" style="margin-top:8px">No players match.</div>')+
   (more?'<div style="margin-top:10px"><button class="pill" data-more="1">Show '+Math.min(25,more)+' more ('+more+' left)</button></div>':'')+
   (o.link?'<div style="margin-top:10px"><a class="pill" href="'+o.link+'" style="text-decoration:none;display:inline-block">Open the full First TD board →</a></div>':'')+
   (o.compact?'':'<div class="m" style="margin-top:10px">'+E(d.method)+'</div>')+'</div>'+(o.compact?'':results(d));
  }
  el.addEventListener("click",function(e){var b=e.target.closest("[data-k]"),g=e.target.closest(".gm");if(e.target.closest("[data-more]")){S.n+=25;draw()}else if(b){S[b.dataset.k]=b.dataset.v;S.n=25;draw()}else if(g){S.game=S.game==g.dataset.g?"":g.dataset.g;draw()}});
  el.addEventListener("change",function(e){var s=e.target.closest("[data-sel]");if(s){S[s.dataset.sel]=s.value;draw()}});
  draw()}).catch(function(){el.innerHTML='<div class="m">First TD board unavailable.</div>'})}
window.SLFirstTD={mount:mount};
})();
