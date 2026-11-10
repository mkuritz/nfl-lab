/* NFL Hub · History · Pick Track Record. Pure render of data/nfl_card_track.json (frozen pre-kickoff picks, graded from official finals + box scores).
   Never regenerates a pick. Two groups (Games, Props), each with collapsible week buckets and counter bubbles. */
(function(root){
 var esc=function(s){return String(s==null?"":s).replace(/[<>&"]/g,function(c){return{"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[c]})};
 var am=function(p){return p==null?"":(p>0?"+":"")+p};
 var f2=function(u){return(u>=0?"+":"\u2212")+Math.abs(u).toFixed(2)+"u"};
 var MON=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
 var dl=function(k){var p=k.split("-");return MON[+p[1]-1]+" "+(+p[2])};
 var ET=function(t){return new Date(t).toLocaleString("en-US",{timeZone:"America/New_York",weekday:"short",hour:"numeric",minute:"2-digit"})+" ET"};
 var blank=function(){return{w:0,l:0,p:0,n:0,u:0,np:0}};
 function add(a,x){if(!x||!x.res)return;a.n++;if(x.res==="win")a.w++;else if(x.res==="loss")a.l++;else a.p++;if(x.u!=null&&x.res!=="void"){a.u=Math.round((a.u+x.u)*1e4)/1e4;a.np++}}
 /* rows: {cat:"games"|"props", g:game, x:pick} */
 function rowsOf(games,cat){var o=[];games.forEach(function(g){if(g.final==null)return;
  if(cat==="games"){if(g.pick&&g.pick.res)o.push({g:g,x:g.pick,t:g.pick.tier||"Pass",kind:g.pick.type})}
  else g.props.forEach(function(p){if(p.res)o.push({g:g,x:p,t:p.tier||"Pass",kind:"prop"})})});return o}
 function tally(rows){var a=blank();rows.forEach(function(r){add(a,r.x)});return a}
 function rec(a){return a.w+"-"+a.l+(a.p?"-"+a.p:"")}
 function bub(a,opt){opt=opt||{};var h='<span class="trk-bs" role="group" aria-label="'+rec(a)+' record">'+'<span class="trk-b won" title="Won">'+a.w+'</span><span class="trk-b lost" title="Lost">'+a.l+'</span>'+(a.p?'<span class="trk-b push" title="Push or void">'+a.p+'</span>':"")+'</span>';
  if(a.np)h+='<span class="trk-u '+(a.u>=0?"up":"dn")+'" title="'+a.np+' of '+a.n+' picks had a posted price">'+f2(a.u)+'</span>';
  else if(a.n)h+='<span class="trk-u na" title="No posted price, record only">record only</span>';
  return h}
 function mark(r){var m={win:["\u2713","Hit","won"],loss:["\u2717","Missed","lost"],push:["\u2013","Push","push"],void:["\u2013","Void","push"]}[r]||["\u2026","Pending","push"];return'<span class="trk-m '+m[2]+'" role="img" aria-label="'+m[1]+'" title="'+m[1]+'">'+m[0]+'</span>'}
 function tierChip(t){return t?'<span class="trk-t t'+esc(t)+'">'+esc(t)+'</span>':""}
 function star(c){return c?'<span class="trk-s" title="On the main-page confidence list as '+esc(c)+'">\u2605 Main page \u00b7 '+esc(c)+'</span>':""}
 function gameRow(r){var g=r.g,p=r.x,f=g.final;
  var line=p.type==="spread"?"Spread":"Moneyline";
  var cover=p.type==="spread"?(function(){var m=p.margin+p.line;return p.res==="push"?"Push on the number":(m>0?"Covered by ":"Missed by ")+Math.abs(m)+(Math.abs(m)===1?" pt":" pts")})():(p.margin>0?"Won outright":p.margin<0?"Lost outright":"Tied");
  return '<div class="trk-row"><div class="trk-mt"><b>'+esc(g.away)+' @ '+esc(g.home)+'</b><span class="mut"> \u00b7 Final '+f.away+'\u2013'+f.home+'</span><div class="mut sm">'+ET(g.kick)+(g.market?' \u00b7 market '+esc(g.market):'')+'</div></div>'+
   '<div class="trk-pk"><b>'+esc(p.label)+'</b>'+(p.price!=null?' <span class="mut">('+am(p.price)+')</span>':' <span class="mut">(no posted price)</span>')+'<div class="sm mut">'+line+' \u00b7 '+cover+'</div><div class="trk-tg">'+tierChip(p.tier)+star(p.conf)+'</div></div>'+
   '<div class="trk-rs">'+mark(p.res)+(p.u!=null?'<span class="trk-u '+(p.u>=0?"up":"dn")+'">'+f2(p.u)+'</span>':'')+'</div></div>'}
 function propRow(r){var g=r.g,p=r.x,f=g.final;
  var mk=p.market==="Anytime TD"?"Anytime TD":esc(p.market)+" o"+p.line;
  return '<div class="trk-row"><div class="trk-mt"><b>'+esc(p.player)+'</b> <span class="mut">'+esc(p.team)+' '+esc(p.pos)+'</span><div class="mut sm">'+esc(g.away)+' @ '+esc(g.home)+' \u00b7 Final '+f.away+'\u2013'+f.home+'</div></div>'+
   '<div class="trk-pk"><b>'+mk+'</b>'+(p.price!=null?' <span class="mut">('+am(p.price)+')</span>':'')+'<div class="sm mut">'+(p.res==="void"?"No box-score line (void)":"Actual "+(p.actual!=null?+(+p.actual).toFixed(1):"\u2014"))+'</div><div class="trk-tg">'+tierChip(p.tier)+star(p.conf)+'</div></div>'+
   '<div class="trk-rs">'+mark(p.res)+(p.u!=null?'<span class="trk-u '+(p.u>=0?"up":"dn")+'">'+f2(p.u)+'</span>':'')+'</div></div>'}
 function filt(rows,F){return rows.filter(function(r){if(F.tier!=="all"&&r.t!==F.tier)return false;if(F.main&&!r.x.conf)return false;return true})}
 function tierSplit(rows,key){var by={};rows.forEach(function(r){var k=key(r);if(!k)return;(by[k]=by[k]||[]).push(r)});
  return ["Bet","Lean","Pass"].filter(function(k){return by[k]}).map(function(k){return'<span class="trk-sp">'+tierChip(k)+bub(tally(by[k]))+'</span>'}).join("")}
 function bucket(wk,cat,F,open){var rows=filt(rowsOf(wk.games,cat),F);var h='<details class="trk-wk"'+(open?" open":"")+' data-wk="'+wk.week+'" data-cat="'+cat+'"><summary><span class="trk-wt"><b>Week '+wk.week+'</b> <span class="mut sm">'+dl(wk.from)+(wk.to!==wk.from?"\u2013"+dl(wk.to):"")+(wk.status==="live"?' <span class="trk-t">in progress</span>':'')+'</span></span><span class="trk-sb">'+(rows.length?bub(tally(rows)):'<span class="mut sm">no picks match</span>')+'</span><span class="trk-chev" aria-hidden="true">\u203a</span></summary><div class="trk-bd">';
  if(wk.note)h+='<div class="trk-note">'+esc(wk.note)+'</div>';
  if(rows.length){
   h+='<div class="trk-sps"><span class="mut sm">By card tier</span>'+tierSplit(rows,function(r){return r.t})+'</div>';
   var m=rows.filter(function(r){return r.x.conf});
   if(m.length)h+='<div class="trk-sps"><span class="mut sm">Main-page confidence</span>'+tierSplit(m,function(r){return r.x.conf})+'</div>';
   if(cat==="games"){var sp=rows.filter(function(r){return r.kind==="spread"}),ml=rows.filter(function(r){return r.kind==="ml"});
    h+='<div class="trk-sps"><span class="mut sm">By call</span>'+(sp.length?'<span class="trk-sp"><span class="trk-t">Spread</span>'+bub(tally(sp))+'</span>':'')+(ml.length?'<span class="trk-sp"><span class="trk-t">Moneyline</span>'+bub(tally(ml))+'</span>':'')+'</div>'}
   h+='<div class="trk-rows">'+rows.map(cat==="games"?gameRow:propRow).join("")+'</div>'}
  return h+'</div></details>'}
 function css(){return'<style>.trk-wrap>summary,.trk-grp>summary,.trk-wk>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:10px;flex-wrap:wrap;min-height:44px}.trk-wrap>summary::-webkit-details-marker,.trk-grp>summary::-webkit-details-marker,.trk-wk>summary::-webkit-details-marker{display:none}.trk-wrap>summary:focus-visible,.trk-grp>summary:focus-visible,.trk-wk>summary:focus-visible,.trk-pill:focus-visible{outline:2px solid var(--acc);outline-offset:2px;border-radius:10px}'+
  '.trk-wrap>summary h2{margin:0}.trk-chev{margin-left:auto;transition:transform .15s;color:var(--acc);font-size:20px}.trk-wrap[open]>summary>.trk-chev,.trk-grp[open]>summary>.trk-chev,.trk-wk[open]>summary>.trk-chev{transform:rotate(90deg)}'+
  '.trk-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:12px 0}.trk-kpi{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:10px 12px}.trk-kpi small{display:block;color:var(--mut);font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;margin-bottom:5px}.trk-kpi .mut{margin-top:4px;display:block;font-size:11px}'+
  '.trk-ctl{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0 4px}.trk-ctl .lbl{font-size:11px;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.05em;margin-right:2px}'+
  '.trk-pill{appearance:none;background:var(--panel2);border:1px solid var(--line);color:var(--mut);border-radius:999px;min-height:44px;min-width:44px;padding:8px 16px;font:inherit;font-weight:700;cursor:pointer}.trk-pill.on{border-color:var(--acc);color:var(--acc);background:#38d0f014}'+
  '.trk-grp{margin-top:12px;border:1px solid var(--line);border-radius:14px;background:#0a1224;padding:4px 12px 12px}.trk-grp>summary{font-weight:800;font-size:15px}.trk-grp>summary .sub{font-weight:500}'+
  '.trk-wk{margin-top:8px;border:1px solid var(--line);border-radius:12px;background:var(--panel2)}.trk-wk>summary{padding:6px 12px;justify-content:space-between}.trk-wt{flex:1 1 140px}.trk-sb{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.trk-bd{padding:2px 12px 12px;border-top:1px solid var(--line)}'+
  '.trk-bs{display:inline-flex;gap:4px;align-items:center}.trk-b{display:inline-grid;place-items:center;min-width:26px;height:26px;padding:0 7px;border-radius:999px;font-weight:800;font-size:12.5px;font-variant-numeric:tabular-nums}.trk-b.won{background:#16a34a33;color:#4ade80;border:1px solid #16a34a88}.trk-b.lost{background:#dc262633;color:#ff7b88;border:1px solid #dc262688}.trk-b.push{background:#64748b33;color:#aab4c8;border:1px solid #64748b88}'+
  '.trk-u{font-weight:800;font-size:12.5px;font-variant-numeric:tabular-nums;padding:3px 9px;border-radius:999px;border:1px solid var(--line)}.trk-u.up{color:#4ade80}.trk-u.dn{color:#ff7b88}.trk-u.na{color:var(--mut);font-weight:600}'+
  '.trk-sps{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:10px 0 0}.trk-sp{display:inline-flex;gap:6px;align-items:center;background:#0a1224;border:1px solid var(--line);border-radius:999px;padding:3px 10px 3px 4px}'+
  '.trk-t{font-size:10px;font-weight:900;letter-spacing:.04em;text-transform:uppercase;border-radius:999px;padding:3px 8px;background:#ffffff10;color:var(--mut)}.trk-t.tBet{background:var(--acc2);color:#06120c}.trk-t.tLean{background:#3fa9ff33;color:#8fc9ff;border:1px solid #3fa9ff66}'+
  '.trk-s{font-size:10.5px;font-weight:800;color:var(--warn);border:1px solid #f5b83d55;border-radius:999px;padding:2px 8px}.trk-note{margin:10px 0 0;padding:8px 10px;border-radius:10px;background:#f5b83d12;border:1px solid #f5b83d44;color:#e9cf8f;font-size:12px}'+
  '.trk-rows{margin-top:10px;display:grid;gap:6px}.trk-row{display:grid;grid-template-columns:1.1fr 1.2fr auto;gap:10px;align-items:center;background:#0a1224;border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:13px}.trk-tg{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}.trk-rs{display:flex;gap:8px;align-items:center;justify-content:flex-end}'+
  '.trk-m{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;font-weight:900;font-size:13px;color:#fff}.trk-m.won{background:#16a34a}.trk-m.lost{background:#dc2626}.trk-m.push{background:#64748b}'+
  '.trk-up{margin-top:8px;font-size:12px;color:var(--mut)}@media(max-width:700px){.trk-row{grid-template-columns:1fr auto}.trk-pk{grid-column:1/-1;order:3}.trk-wk>summary{padding:6px 10px}}</style>'}
 var ST={tier:"all",main:false,open:{}};
 function html(T,F,state){F=F||{tier:"all",main:false};var hasF=function(w){return w.games.some(function(g){return g.final!=null})};var W=((T&&T.weeks)||[]).filter(hasF).slice().sort(function(a,b){return b.week-a.week});
  var UP=((T&&T.weeks)||[]).filter(function(w){return !hasF(w)});
  var head=function(n){return'<summary aria-label="History: pick track record"><h2>\ud83d\udcdc History \u00b7 Track Record</h2><span class="mut sm">'+n+'</span><span class="trk-chev" aria-hidden="true">\u203a</span></summary>'};
  if(!W.length)return css()+'<details class="card trk-wrap" id="trk-history">'+head("starts once a week is graded")+'<div class="mut" style="margin-top:8px">No graded weeks yet.</div></details>';
  var all={games:[],props:[]};W.forEach(function(w){all.games=all.games.concat(rowsOf(w.games,"games"));all.props=all.props.concat(rowsOf(w.games,"props"))});
  var fg=filt(all.games,F),fp=filt(all.props,F);
  var conf=filt(all.games.concat(all.props).filter(function(r){return r.x.conf}),{tier:"all",main:false});
  var nG=W.reduce(function(n,w){return n+w.games.filter(function(g){return g.final}).length},0);
  var kp='<div class="trk-kpis"><div class="trk-kpi"><small>Games \u00b7 spread + moneyline</small>'+bub(tally(fg))+'<span class="mut">'+fg.length+' calls</span></div>'+
   '<div class="trk-kpi"><small>Props \u00b7 player picks</small>'+bub(tally(fp))+'<span class="mut">'+fp.length+' picks</span></div>'+
   '<div class="trk-kpi"><small>Main-page confidence</small>'+bub(tally(conf))+'<span class="mut">'+conf.length+' plays</span></div></div>';
  var ctl='<div class="trk-ctl" role="toolbar" aria-label="History filters"><span class="lbl">Tier</span>'+["all","Bet","Lean","Pass"].map(function(t){return'<button type="button" class="trk-pill'+(F.tier===t?" on":"")+'" data-tier="'+t+'" aria-pressed="'+(F.tier===t)+'">'+(t==="all"?"All":t)+'</button>'}).join("")+
   '<button type="button" class="trk-pill'+(F.main?" on":"")+'" data-main="1" aria-pressed="'+!!F.main+'">\u2605 Main page only</button><button type="button" class="trk-pill" data-exp="1">Expand weeks</button><button type="button" class="trk-pill" data-col="1">Collapse weeks</button></div>';
  var grp=function(cat,title,sub,rows){var o=(state&&state.grp&&state.grp[cat])!==false;return'<details class="trk-grp" data-grp="'+cat+'"'+(o?" open":"")+'><summary><span>'+title+' <span class="sub mut sm">'+sub+'</span></span><span class="trk-sb">'+bub(tally(rows))+'</span><span class="trk-chev" aria-hidden="true">\u203a</span></summary>'+W.map(function(w,i){var op=state&&state.wk&&state.wk[cat+w.week]!=null?state.wk[cat+w.week]:i===0;return bucket(w,cat,F,op)}).join("")+'</details>'};
  var body='<div class="mut sm" style="margin-top:6px">'+esc(T.method||"")+'</div>'+kp+ctl+
   grp("games","\ud83c\udfc8 Games","spread + moneyline calls",fg)+grp("props","\ud83c\udfaf Props","the three player picks under each game",fp)+
   (UP.length?'<div class="trk-up">'+UP.map(function(w){return"Week "+w.week+": "+w.games.length+" games not started \u2014 picks freeze at each kickoff and are graded after the final."}).join(" ")+'</div>':"");
  return css()+'<details class="card trk-wrap" id="trk-history"'+(state&&state.top?" open":"")+'>'+head(nG+" graded games \u00b7 "+W.length+" weeks")+body+'</details>'}
 function mount(el,T){var F={tier:"all",main:false},state={grp:{},wk:{},top:false};
  function snap(){var d=el.querySelector("#trk-history");if(!d)return;state.top=d.open;el.querySelectorAll(".trk-grp").forEach(function(x){state.grp[x.dataset.grp]=x.open});el.querySelectorAll(".trk-wk").forEach(function(x){state.wk[x.dataset.cat+x.dataset.wk]=x.open})}
  function draw(){el.innerHTML=html(T,F,state)}
  el.addEventListener("click",function(e){var b=e.target.closest("button.trk-pill");if(!b)return;e.preventDefault();snap();
   if(b.dataset.tier)F.tier=b.dataset.tier;else if(b.dataset.main)F.main=!F.main;else if(b.dataset.exp||b.dataset.col){var o=!!b.dataset.exp;el.querySelectorAll(".trk-wk").forEach(function(x){state.wk[x.dataset.cat+x.dataset.wk]=o});state.grp={games:true,props:true}}
   draw();});
  draw();return{draw:draw,F:F}}
 var api={html:html,mount:mount,rowsOf:rowsOf,tally:tally,filt:filt};
 if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.NFLTrack=api;
})(typeof window!=="undefined"?window:this);
