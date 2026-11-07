/* Player prop intel on NFL Hub player profiles. Data: data/prop_intel.json (built by props/tools/prop_intel.py). Fits both the v2 sheet (#v2s) and the classic profile (#nfpd). */
(function(){if(window.__pi)return;window.__pi=1;
var D=null,AID=null,E=function(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})};

// Display-only fail-closed gate: current official Hub season/week and a recent dated import.
var CTX=null;
function intelTime(raw){
 if(typeof raw!=="string")return NaN;
 if(/^\d{4}-\d\d-\d\dT.*(?:Z|[+-]\d\d:\d\d)$/.test(raw))return Date.parse(raw);
 var m=/^(?:([A-Z][a-z]{2}) (\d{1,2}), (\d{4})|(\d{4})-(\d\d)-(\d\d)) (\d{1,2}):(\d\d) (AM|PM) ET$/.exec(raw);
 if(!m)return NaN;
 var y=+(m[3]||m[4]),mo=m[1]?"JanFebMarAprMayJunJulAugSepOctNovDec".indexOf(m[1])/3:+m[5]-1,day=+(m[2]||m[6]);
 var wall=Date.UTC(y,mo,day,+m[7]%12+(m[9]==="PM"?12:0),+m[8]),t=wall;
 for(var i=0;i<3;i++){var a=Object.fromEntries(new Intl.DateTimeFormat("en-US",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(new Date(t)).map(function(p){return[p.type,p.value]}));t+=wall-Date.UTC(+a.year,+a.month-1,+a.day,+a.hour,+a.minute);}
 return t;
}
function intelAvailable(p,now){
 now=now||Date.now();
 var m=/^(\d{4}) Week (\d{1,2})$/.exec(D&&D.week||""),at=intelTime(D&&(D.updated_at||D.updated_et)),ct=Date.parse(CTX&&CTX.updated);
 if(!p||!m||!CTX||+m[1]!==+CTX.season||+m[2]!==+CTX.week||!isFinite(at)||at>now||now-at>72*36e5||!isFinite(ct)||ct>now||now-ct>48*36e5)return false;
 return (CTX.games||[]).some(function(g){var kick=Date.parse(g.date);return g&&g.away&&g.home&&p.gk===g.away.abbr+"@"+g.home.abbr&&isFinite(kick)&&kick>=now-6*36e5&&kick<=now+7*864e5;});
}
var UNAVAILABLE="<div class='mut pi-unavailable' role='status'>Prop impact unavailable: current-week, fresh verified context is not available.</div>";
fetch("data/nfl.json?v="+Math.floor(Date.now()/3e5)).then(function(r){return r.ok?r.json():null}).then(function(j){CTX=j;tick();}).catch(function(){});
fetch("data/prop_intel.json?v="+Math.floor(Date.now()/3e5)).then(function(r){return r.ok?r.json():null}).then(function(j){D=j;tick()}).catch(function(){});
var DIR={up:["▲ Up","up"],down:["▼ Down","down"],uncertain:["◆ Uncertain",""]};
function card(p){var d=DIR[p.dir]||DIR.uncertain;
 return '<div class="in '+d[1]+'" style="margin:0"><b>Prop impact · '+E(d[0])+(p.unconfirmed?' <span class="pi-u">Unconfirmed</span>':'')+'</b>'+
 '<p>'+E(p.note)+'</p><div class="chips" style="margin-top:6px">'+p.markets.map(function(m){return '<span class="chip" style="cursor:default;padding:3px 9px;font-size:11px">'+E(m)+'</span>'}).join("")+'</div>'+
 '<div class="ctx">CONFIDENCE: '+E(p.conf.toUpperCase())+(p.conf_note?' ('+E(p.conf_note)+')':'')+' · '+E(p.game)+'</div><div class="ctx" style="margin-top:2px">'+E(p.src)+' · '+E(p.time)+' · '+E(D.week)+'</div></div>'}
function css(){if(document.getElementById("pi-css"))return;var s=document.createElement("style");s.id="pi-css";s.textContent='.pi-box{padding:12px 16px;border-bottom:1px solid var(--line,#232b3b)}.pi-box .in{background:var(--panel2,#121a2a);border:1px solid var(--line,#232b3b);border-left:3px solid var(--mut,#8b97b0);border-radius:12px;padding:10px 12px}.pi-box .in.up{border-left-color:var(--acc2,#53e3a6)}.pi-box .in.down{border-left-color:var(--bad,#ff5d6c)}.pi-box .in p{margin:6px 0 0;font-size:13px}.pi-box .ctx{font-size:10.5px;color:var(--mut,#8b97b0);font-weight:700;margin-top:7px;letter-spacing:.03em}.pi-box .chips{display:flex;gap:6px;flex-wrap:wrap}.pi-box .chip{background:transparent;border:1px solid var(--line,#232b3b);color:var(--mut,#8b97b0);border-radius:999px;font-weight:800}.pi-u{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:999px;font-size:10px;font-weight:800;letter-spacing:.04em;background:#facc1522;color:#facc15;border:1px solid #facc1555;vertical-align:1px}';document.head.appendChild(s)}
// Recheck existing cards too, so a long-open profile cannot retain expired context.
function tick(){var p,box;
 function place(host,id,anchor){if(!host||!id)return;css();p=D&&D.players&&D.players[id];var html=intelAvailable(p)?card(p):UNAVAILABLE;
 box=host.querySelector(".pi-box");if(!box){box=document.createElement("div");box.className="pi-box";anchor?host.insertBefore(box,anchor):host.appendChild(box)}
 if(box.__piHtml!==html){box.__piHtml=html;box.innerHTML=html;}}
 var sh=document.querySelector("#v2s .sh");if(sh&&AID)place(sh,AID,sh.querySelector(".tabs"));
 var nf=document.getElementById("nfpd"),m=/#player=(\d+)/.exec(location.hash),id=m?m[1]:AID;
 if(nf&&nf.querySelector(".hd"))place(nf,id,nf.querySelector(".hd").nextSibling);
}
setInterval(tick,60000);
function wrap(){if(window.NFLV2&&!NFLV2.__pi){var o=NFLV2.open;NFLV2.open=function(a){AID=String(a);return o.apply(this,arguments)};NFLV2.__pi=1}
 if(window.NFLProfile&&!window.NFLProfile.__pi){var o2=window.NFLProfile;window.NFLProfile=function(a){AID=String(a);return o2.apply(this,arguments)};window.NFLProfile.__pi=1}}
wrap();document.addEventListener("click",function(e){var el=e.target.closest&&e.target.closest("[data-nfp],[data-aid]");if(el)AID=el.getAttribute("data-nfp")||el.getAttribute("data-aid")},true);
var T=null;new MutationObserver(function(){wrap();if(!T)T=setTimeout(function(){T=null;tick()},60)}).observe(document.documentElement,{childList:true,subtree:true});
})();
