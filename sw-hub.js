/* NFL Hub · in-hub panels (preview). Display-only.
   #strengths            Strengths & Weaknesses field map (data/strengths_weaknesses.json + data/nfl.json slate)
   #unit-board           Unit Board rendered inside the Hub (embedded page, its own chrome hidden)
   #opportunity-board    Opportunity Board rendered inside the Hub
   Other Hub hashes (#spots, #gameday, ...) are untouched. */
(function(){'use strict';
const PANELS={'strengths':{title:'Strengths & Weaknesses'},'unit-board':{title:'Unit Board',src:'unit-board.html?embed=1'},'opportunity-board':{title:'Opportunity Board',src:'injury-cascade.html?embed=1'}};
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const CSS=`<style id="swcss">
body.hp-on .w>*:not(header):not(#hp-root):not(footer):not(#sl-modal-root){display:none!important}
body.hp-on .w{max-width:1240px}
#hp-root{--sw-hot:#ff6b4a;--sw-cold:#38bdf8}
#hp-root .hp-frame{width:100%;border:1px solid var(--line);border-radius:12px;background:var(--panel);display:block;height:calc(100vh - 150px);min-height:620px}
#hp-root .hp-note{margin:0 0 10px}
#sw .sw-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin:2px 0 12px;flex-wrap:wrap}
#sw .sw-eye{font-size:10px;font-weight:800;letter-spacing:.12em;color:var(--acc)}
#sw h2{font-size:22px;margin:2px 0 4px}#sw .sw-sub{color:var(--mut);margin:0;font-size:13px}
#sw .sw-stamp{font:11px/1.4 ui-monospace,monospace;color:var(--mut);border:1px solid var(--line);border-radius:6px;padding:5px 9px;white-space:nowrap}
#sw .sw-games{display:flex;gap:8px;overflow-x:auto;padding:2px 0 10px;scrollbar-width:thin}
#sw .sw-games button{flex:0 0 auto;background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:10px;padding:8px 12px;font:700 13px/1.25 inherit;cursor:pointer;text-align:left;min-height:44px}
#sw .sw-games button small{display:block;color:var(--mut);font-weight:600;font-size:11px}
#sw .sw-games button[aria-pressed=true]{border-color:var(--acc);box-shadow:inset 0 0 0 1px var(--acc)}
#sw .sw-bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 12px}
#sw .sw-seg{display:inline-flex;background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:3px}
#sw .sw-seg button{background:transparent;border:0;color:var(--mut);font:700 12.5px/1 inherit;padding:9px 13px;border-radius:999px;cursor:pointer;min-height:36px}
#sw .sw-seg button[aria-pressed=true]{background:var(--acc);color:#04202a}
#sw .sw-swap{background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:999px;padding:8px 14px;font:700 12.5px inherit;cursor:pointer;min-height:40px}
#sw .sw-grid{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:14px;align-items:start}
#sw .sw-card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:12px}
#sw .sw-card h3{margin:0 0 8px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--mut)}
#sw .sw-field{width:100%;height:auto;display:block;border-radius:10px}
#sw .sw-field .z{cursor:pointer}#sw .sw-field .z:hover rect.zr,#sw .sw-field .z.sel rect.zr{stroke:#fff;stroke-width:2}
#sw .sw-field .z:focus{outline:none}#sw .sw-field .z:focus-visible rect.zr{stroke:#ffd166;stroke-width:2.5}
#sw .sw-leg{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--mut);margin-top:8px;flex-wrap:wrap}
#sw .sw-leg i{display:inline-block;width:150px;height:8px;border-radius:4px;background:linear-gradient(90deg,#1e6fa8,#2a3a5c 50%,#d9472b)}
#sw .sw-leg .hatch{width:16px;height:12px;border-radius:2px;background:repeating-linear-gradient(45deg,#3a4664 0 3px,#1b2540 3px 6px)}
#sw .sw-detail{min-height:120px}#sw .sw-detail table{width:100%;border-collapse:collapse;font-size:13px}#sw .sw-detail td{padding:4px 0;border-bottom:1px solid #1b2846}#sw .sw-detail td:last-child{text-align:right;font-variant-numeric:tabular-nums}
#sw .sw-k{display:grid;grid-template-columns:1fr auto;gap:2px 10px;font-size:13px}
#sw .sw-meter{position:relative;height:10px;border-radius:5px;background:#1a2747;margin:6px 0 2px;overflow:hidden}
#sw .sw-meter b{position:absolute;top:0;bottom:0;left:0;border-radius:5px}
#sw .sw-meter s{position:absolute;top:-2px;bottom:-2px;width:2px;background:#cdd6ea;text-decoration:none}
#sw .sw-tag{display:inline-block;font-size:11px;font-weight:800;border-radius:999px;padding:3px 9px;margin-top:6px}
#sw .hot{color:#ff8a6b}#sw .cold{color:#5cc8ff}#sw .tag-hot{background:#3a1a16;color:#ffb39e}#sw .tag-cold{background:#0f2a3d;color:#9fdcff}#sw .tag-mid{background:#1c2643;color:#c7d0e6}
#sw ol.sw-plan{margin:0;padding-left:20px;font-size:13px}#sw ol.sw-plan li{margin:0 0 6px}
#sw details.sw-how{font-size:12px;color:var(--mut)}#sw details.sw-how summary{cursor:pointer;font-weight:700;color:var(--txt)}
@media(max-width:900px){#sw .sw-grid{grid-template-columns:1fr}#hp-root .hp-frame{height:calc(100vh - 120px)}}
@media(max-width:600px){#sw h2{font-size:19px}#sw .sw-seg button{padding:9px 10px;font-size:12px}#sw .sw-stamp{white-space:normal}}
</style>`;
function parse(){const h=location.hash.slice(1).split('?')[0];const m=/^([\w-]+)(?:\/(.*))?$/.exec(h);return m&&PANELS[m[1]]?{key:m[1],arg:m[2]||''}:null}
let root=null,D=null,G=null,st={g:null,flip:false,mode:'plan',sel:null};
function ensure(){if(!document.getElementById('swcss'))document.head.insertAdjacentHTML('beforeend',CSS);
 if(!root){root=document.createElement('section');root.id='hp-root';root.hidden=true;const hd=document.querySelector('.w>header');hd?hd.after(root):document.body.prepend(root)}}
async function show(){const p=parse();document.body.classList.toggle('hp-on',!!p);if(!p){if(root)root.hidden=true;return}
 ensure();root.hidden=false;document.title=PANELS[p.key].title+' · NFL Hub · Sports Labs';
 if(PANELS[p.key].src){if(root.dataset.k!==p.key){root.dataset.k=p.key;root.innerHTML='<iframe class="hp-frame" title="'+esc(PANELS[p.key].title)+'" src="'+PANELS[p.key].src+'" loading="eager"></iframe>'}scrollTo(0,0);return}
 if(root.dataset.k!=='strengths'){root.dataset.k='strengths';root.innerHTML='<div id="sw"><div class="mut">Loading field map…</div></div>'}
 try{await load();const g=p.arg&&/^[A-Z]{2,3}@[A-Z]{2,3}$/.test(p.arg.split('|')[0])?p.arg.split('|')[0]:null;if(g&&G.some(x=>x.k===g))st.g=g;render()}
 catch(e){root.querySelector('#sw').innerHTML='<div class="sw-card">The field map could not load right now. Other Hub views are unchanged.</div>'}}
async function load(){if(D)return;const [a,b]=await Promise.all([fetch('data/strengths_weaknesses.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('sw');return r.json()}),fetch('data/nfl.json',{cache:'no-cache'}).then(r=>r.ok?r.json():{games:[]}).catch(()=>({games:[]}))]);
 D=a;const fx={LA:'LAR',WAS:'WSH'};G=(b.games||[]).filter(g=>g.away&&g.home).map(g=>{const aw=fx[g.away.abbr]||g.away.abbr,hm=fx[g.home.abbr]||g.home.abbr;return {k:aw+'@'+hm,aw,hm,date:g.date,post:g.state==='post',when:g.state==='post'?'Final':(g.status||'').replace(/^\d+\/\d+ - /,'')}}).filter(g=>D.teams[g.aw]&&D.teams[g.hm]);
 G.sort((x,y)=>(x.post-y.post)||String(x.date).localeCompare(String(y.date)));if(!st.g&&G.length)st.g=G[0].k}
/* ---------- math ---------- */
const L=()=>D.league;
function rankOf(side,key,val,field,hiBad){const arr=Object.values(D.teams).map(t=>{const v=t[side][key]&&t[side][key][field];return v}).filter(v=>v!=null).sort((a,b)=>hiBad?b-a:a-b);return arr.indexOf(val)+1}
function rankTeam(side,field,val,hiFirst){const arr=Object.values(D.teams).map(t=>t[side][field]).filter(v=>v!=null).sort((a,b)=>hiFirst?b-a:a-b);return val==null?null:arr.indexOf(val)+1}
function attack(off,def){const out=[];const T=D.k.thin;
 for(const [z,b] of Object.entries(L().zones)){const o=off.off.zones[z],d=def.def.zones[z];const tilt=b.share?Math.max(-1,Math.min(1.5,(o.share||0)/b.share-1)):0;
  out.push({kind:'pass',z,score:d.d+o.d+0.06*tilt,d,o,b,thin:d.n<T});}
 for(const [z,b] of Object.entries(L().lanes)){const o=off.off.lanes[z],d=def.def.lanes[z];const tilt=b.share?Math.max(-1,Math.min(1.5,(o.share||0)/b.share-1)):0;
  out.push({kind:'run',z,score:(d.d+o.d)*1.6+0.04*tilt,d,o,b,thin:d.n<T});}
 return out.sort((a,b)=>b.score-a.score)}
/* ---------- labels ---------- */
const DEPTH={short:'Short (under 10 air yds)',inter:'Intermediate (10–19)',deep:'Deep (20+)'};
const LANE={'L-end':'Left edge','L-tackle':'Left off-tackle','L-guard':'Left A/B gap','mid':'Up the middle','R-guard':'Right A/B gap','R-tackle':'Right off-tackle','R-end':'Right edge'};
const zname=(kind,z)=>kind==='run'?LANE[z]:(DEPTH[z.split(':')[0]].split(' (')[0]+' '+z.split(':')[1]);
const pct=x=>x==null?'—':Math.round(x*100)+'%';const f2=(x,d=2)=>x==null?'—':(+x).toFixed(d);const sg=(x,d=2)=>x==null?'—':(x>=0?'+':'−')+Math.abs(x).toFixed(d);
const ord=n=>n==null?'—':n+(['th','st','nd','rd'][(n%100-20)%10]||['th','st','nd','rd'][n%100]||'th');
/* ---------- colors ---------- */
function heat(v,scale){const f=Math.max(-1,Math.min(1,v/scale));const mix=(a,b,t)=>a.map((x,i)=>Math.round(x+(b[i]-x)*t));const mid=[42,58,92],hot=[217,71,43],cold=[30,111,168];const c=f>=0?mix(mid,hot,f):mix(mid,cold,-f);return 'rgb('+c.join(',')+')'}
/* ---------- field SVG ---------- */
/* Drawn in field coords: u = along the field (offense drives toward +u), v = across (v=0 is the offense's left).
   Wide screens: u runs left->right. Phones: u runs bottom->top so the field stays readable. */
const LSHORT={'L-end':'L edge','L-tackle':'L tackle','L-guard':'L A/B','mid':'Middle','R-guard':'R A/B','R-tackle':'R tackle','R-end':'R edge'};
const DSHORT={short:'SHORT',inter:'INTERMED.',deep:'DEEP'},DV={short:'SHORT',inter:'INT.',deep:'DEEP'};
function field(off,def,acts){const vert=(root.clientWidth||innerWidth)<640;const U=vert?900:1000,V=vert?600:520,VM=vert?36:26,fs=vert?1.45:1;
 const BF=vert?230:210,QBU=30,LOS=BF+20,Y2=(U-LOS-14)/34,u=y=>LOS+y*Y2;const W=vert?V:U,H=vert?U:V;
 const P=(uu,vv)=>vert?[vv,U-uu]:[uu,vv];
 const R=(u1,u2,v1,v2)=>{const [x1,y1]=P(u1,v1),[x2,y2]=P(u2,v2);return {x:Math.min(x1,x2),y:Math.min(y1,y2),w:Math.abs(x2-x1),h:Math.abs(y2-y1)}};
 const FV=V-2*VM,bands=[[VM,VM+FV*0.36],[VM+FV*0.36,VM+FV*0.64],[VM+FV*0.64,V-VM]];
 const depth={short:[0,10],inter:[10,20],deep:[20,34]};const mode=st.mode,T=D.k.thin;const F=n=>Math.round(n*fs);
 const fr=R(0,U,VM,V-VM);
 let s=`<svg class="sw-field" viewBox="0 0 ${W} ${H}" role="group" aria-label="Field map: ${esc(off.k)} offense versus ${esc(def.k)} defense"><defs>
 <pattern id="swh" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="#26314f"/><line x1="0" y1="0" x2="0" y2="8" stroke="#3b4a72" stroke-width="3"/></pattern>
 <marker id="swa" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#ffd166"/></marker></defs>
 <rect x="0" y="0" width="${W}" height="${H}" rx="12" fill="#0f2a1e"/>`;
 for(let yd=-10;yd<=30;yd+=5){const uu=u(yd);if(uu<QBU||yd===0)continue;const [x1,y1]=P(uu,VM),[x2,y2]=P(uu,V-VM);s+=`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#fff" stroke-opacity=".14" stroke-width="1.5"/>`;
  if(yd>0&&yd%10===0){const [tx,ty]=P(uu,vert?V-VM+18:VM-9);s+=`<text x="${tx}" y="${ty+(vert?4:0)}" fill="#cfe9dc" fill-opacity=".75" font-size="${F(12)}" font-weight="700" text-anchor="middle">+${yd}</text>`}}
 s+=`<rect x="${fr.x+1}" y="${fr.y}" width="${fr.w-2}" height="${fr.h}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>`;
 const topA=acts.map(a=>a.kind+':'+a.z);
 const val=(d,o)=>mode==='def'?{v:d.d,n:d.n}:mode==='off'?{v:o.d,n:o.n}:{v:d.d+o.d,n:d.n};
 ['short','inter','deep'].forEach(dp=>['left','middle','right'].forEach((dir,i)=>{const z=dp+':'+dir,d=def.def.zones[z],o=off.off.zones[z],{v,n}=val(d,o);const [a,b]=depth[dp],[v1,v2]=bands[i];
  const c=R(u(a)+3,u(b)-3,v1+3,v2-3);const fill=n===0?'#26314f':n<T?'url(#swh)':heat(v,0.22);const lab=n===0?'No data':n<T?'Thin · '+n:sg(v);
  const sub=mode==='off'?`${pct(o.share)} of tgts`:(mode==='def'||vert)?`${f2(d.ypt,1)} yds/tgt`:`${f2(d.ypt,1)} yds/tgt · ${pct(o.share)} tgts`;
  const sel=st.sel==='pass:'+z,star=mode==='plan'&&topA.includes('pass:'+z);const big=c.h>60&&c.w>110;
  s+=`<g class="z${sel?' sel':''}" tabindex="0" role="button" data-z="pass:${z}" aria-label="${esc(zname('pass',z))}: ${esc(lab)}"><rect class="zr" x="${c.x}" y="${c.y}" width="${c.w}" height="${c.h}" rx="8" fill="${fill}" fill-opacity="${n<T?1:.9}" stroke="${star?'#ffd166':'#0b1220'}" stroke-opacity="${star?1:.4}" stroke-width="${star?3:1}"/>
  <text x="${c.x+10}" y="${c.y+F(17)}" fill="#fff" fill-opacity=".8" font-size="${F(11.5)}" font-weight="800">${(vert?DV:DSHORT)[dp]} ${dir.toUpperCase()}</text>
  <text x="${c.x+10}" y="${c.y+c.h/2+F(9)}" fill="#fff" font-size="${F(n<T?16:25)}" font-weight="800">${esc(lab)}</text>
  ${big?`<text x="${c.x+10}" y="${c.y+c.h-F(9)}" fill="#e6ebf5" fill-opacity=".8" font-size="${F(11.5)}">${esc(sub)}</text>`:''}</g>`}));
 const lanes=D.lanes,lw=FV/lanes.length,L1=QBU+34,L2=LOS-4;
 if(!vert){const [tx,ty]=P((L1+L2)/2,VM-9);s+=`<text x="${tx}" y="${ty}" fill="#cfe9dc" fill-opacity=".75" font-size="12" font-weight="700" text-anchor="middle">RUN LANES</text>`}
 lanes.forEach((ln,i)=>{const d=def.def.lanes[ln],o=off.off.lanes[ln],{v,n}=val(d,o);const c=R(L1,L2,VM+i*lw+2,VM+(i+1)*lw-2);
  const fill=n===0?'#26314f':n<T?'url(#swh)':heat(v,0.12);const star=mode==='plan'&&topA.includes('run:'+ln),sel=st.sel==='run:'+ln;const txt=n===0?'—':n<T?'thin':sg(v);
  s+=`<g class="z${sel?' sel':''}" tabindex="0" role="button" data-z="run:${ln}" aria-label="${esc(LANE[ln])}: ${esc(txt)}"><rect class="zr" x="${c.x}" y="${c.y}" width="${c.w}" height="${c.h}" rx="6" fill="${fill}" stroke="${star?'#ffd166':'#0b1220'}" stroke-width="${star?3:1}" stroke-opacity="${star?1:.4}"/>`+
  (vert?`<text x="${c.x+c.w/2}" y="${c.y+F(16)}" fill="#fff" font-size="${F(10)}" font-weight="700" text-anchor="middle">${esc(LSHORT[ln])}</text><text x="${c.x+c.w/2}" y="${c.y+c.h/2+F(2)}" fill="#fff" font-size="${F(13)}" font-weight="800" text-anchor="middle">${esc(txt)}</text>`
   :`<text x="${c.x+8}" y="${c.y+c.h/2+4}" fill="#fff" font-size="12" font-weight="700">${esc(LANE[ln])}</text><text x="${c.x+c.w-(star?26:8)}" y="${c.y+c.h/2+4}" fill="#fff" font-size="13" font-weight="800" text-anchor="end">${esc(txt)}</text>`)+`</g>`});
 {const [x1,y1]=P(LOS,VM),[x2,y2]=P(LOS,V-VM),[tx,ty]=P(LOS,V-VM+15);s+=`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#60a5fa" stroke-width="3"/><text x="${tx}" y="${ty+(vert?4:2)}" fill="#93c5fd" font-size="${F(10.5)}" font-weight="800" text-anchor="middle">LOS</text>`}
 if(mode==='plan'){const qu=QBU+12,qv=V/2;const [qx,qy]=P(qu,qv);acts.forEach((a,i)=>{let tu,tv;
   if(a.kind==='pass'){const [dp,dir]=a.z.split(':');const [p1,p2]=depth[dp];const bi=['left','middle','right'].indexOf(dir);tu=u(p2)-3-F(17);tv=vert?bands[bi][1]-3-F(17):bands[bi][0]+3+F(17)}
   else{tu=vert?L1+F(14):LOS;tv=VM+lanes.indexOf(a.z)*lw+lw/2}
   const cu=(qu+tu)/2,cv=Math.min(qv,tv)-(vert?30:45);const [cx,cy]=P(cu,cv),[tx,ty]=P(tu,tv);
   s+=`<path d="M${qx} ${qy} Q${cx} ${cy} ${tx} ${ty}" fill="none" stroke="#ffd166" stroke-width="${(4-i)*fs}" stroke-dasharray="${a.kind==='run'?'0':'9 7'}" opacity=".95"/><circle cx="${tx}" cy="${ty}" r="${F(12)}" fill="#ffd166" stroke="#2a1d00" stroke-width="1.5"/><text x="${tx}" y="${ty+F(4.5)}" font-size="${F(13)}" font-weight="900" text-anchor="middle" fill="#2a1d00">${i+1}</text>`});
  s+=`<circle cx="${qx}" cy="${qy}" r="${F(11)}" fill="#e6ebf5"/><text x="${qx}" y="${qy+F(3.5)}" font-size="${F(9.5)}" font-weight="900" text-anchor="middle" fill="#0b1220">QB</text>`}
 return s+'</svg>'}
/* ---------- side cards ---------- */
function rushCard(off,def){const l=L();const dp=def.def.prs,op=off.off.prs,ttt=off.off.ttt;const idx=(dp!=null&&op!=null&&l.rush.prs)?(dp-l.rush.prs)+(op-l.rush.prs):null;
 const rd=rankTeam('def','prs',dp,true),ro=rankTeam('off','prs',op,false);
 let verdict,cls;if(idx==null){verdict='Pressure data unavailable for this matchup';cls='tag-mid'}else if(idx>0.04){verdict=`${def.k} rush should get home: expect a short clock for ${esc(off.off.qb||off.k+' QB')}`;cls='tag-hot'}else if(idx<-0.04){verdict=`${off.k} protection should hold: clean pockets likely`;cls='tag-cold'}else{verdict='Even pass-rush matchup';cls='tag-mid'}
 if(idx!=null&&ttt!=null&&l.ttt){if(idx>0.04&&ttt<l.ttt-0.15)verdict+='. Quick release softens it';if(idx>0.04&&ttt>l.ttt+0.15)verdict+='. Holds the ball long, so sack risk is real'}
 const meter=(v,lg,max,col)=>v==null?'<div class="mut sm">No charted data</div>':`<div class="sw-meter"><b style="width:${Math.min(100,v/max*100)}%;background:${col}"></b><s style="left:${Math.min(99,lg/max*100)}%"></s></div>`;
 return `<div class="sw-card"><h3>Pass rush vs protection</h3>
 <div class="sw-k"><span><b>${esc(def.k)}</b> D pressure rate</span><b>${pct(dp)} <span class="mut sm">${ord(rd)}</span></b></div>${meter(dp,l.rush.prs,0.45,'#ff6b4a')}
 <div class="sw-k" style="margin-top:8px"><span><b>${esc(off.k)}</b> O pressure allowed</span><b>${pct(op)} <span class="mut sm">${ord(ro)} best</span></b></div>${meter(op,l.rush.prs,0.45,'#38bdf8')}
 <div class="sw-k" style="margin-top:8px"><span>${esc(def.k)} D sack rate</span><b>${pct(def.def.sack)}</b><span>${esc(off.k)} O sack rate</span><b>${pct(off.off.sack)}</b>
 <span>${esc(off.off.qb||'QB')} time to throw</span><b>${ttt==null?'—':ttt.toFixed(2)+'s'} <span class="mut sm">lg ${l.ttt?l.ttt.toFixed(2):'—'}s</span></b></div>
 <span class="sw-tag ${cls}">${verdict}</span><div class="mut sm" style="margin-top:6px">White tick = league average. Pressure through Week ${esc(D.rush_through_week||'—')}.</div></div>`}
function runCard(off,def){const l=L(),dpg=def.def.runs20/(def.games||1),r=rankTeam('def','x10',def.def.x10,false);
 return `<div class="sw-card"><h3>Explosive runs</h3><div class="sw-k"><span>${esc(def.k)} D 10+ yd runs allowed</span><b>${pct(def.def.x10)} <span class="mut sm">${ord(r)} stingiest</span></b>
 <span>${esc(def.k)} D 20+ yd runs allowed</span><b>${def.def.runs20} <span class="mut sm">${dpg.toFixed(2)}/g · lg ${f2(l.runs20_pg)}</span></b>
 <span>${esc(off.k)} O 10+ yd run rate</span><b>${pct(off.off.x10)}</b><span>${esc(off.k)} O 20+ yd runs</span><b>${off.off.runs20}</b></div></div>`}
function planCard(off,def,acts,all){const li=acts.map(a=>{const v=a.kind==='pass'?`${esc(def.k)} allows ${f2(a.d.ypt,1)} yds/target here (${sg(a.d.d)} EPA vs avg); ${esc(off.k)} sends ${pct(a.o.share)} of targets here`:`${esc(def.k)} allows ${f2(a.d.ypc,1)} yds/carry here (${sg(a.d.d)} EPA vs avg); ${esc(off.k)} runs ${pct(a.o.share)} of carries here`;return `<li><b>${esc(zname(a.kind,a.z))}</b>${a.thin?' <span class="mut sm">(thin sample)</span>':''}<br><span class="mut sm">${v}</span></li>`}).join('');
 const ok=all.filter(a=>!a.thin),wp=ok.filter(a=>a.kind==='pass').pop(),wr=ok.filter(a=>a.kind==='run').pop();const avoid=[wp,wr].filter(Boolean).map(a=>esc(zname(a.kind,a.z))).join(' and ');
 return `<div class="sw-card"><h3>Where ${esc(off.k)} should attack</h3><ol class="sw-plan">${li}</ol><div class="mut sm">Toughest spots: ${avoid}.</div></div>`}
function detail(off,def){if(!st.sel)return `<div class="sw-card sw-detail"><h3>Zone detail</h3><div class="mut sm">Tap any zone or run lane on the field for the numbers behind it.</div></div>`;
 const [kind,z]=[st.sel.split(':')[0],st.sel.slice(st.sel.indexOf(':')+1)];const T=D.k.thin;
 if(kind==='pass'){const d=def.def.zones[z],o=off.off.zones[z],b=L().zones[z];const rkd=Object.values(D.teams).map(t=>t.def.zones[z].epa).sort((a,b)=>a-b).indexOf(d.epa)+1;
  return `<div class="sw-card sw-detail"><h3>${esc(zname('pass',z))}</h3><table>
  <tr><td>${esc(def.k)} D targets faced</td><td>${d.n}${d.n<T?' · thin':''}</td></tr><tr><td>Completion % allowed</td><td>${pct(d.cmp)} <span class="mut">lg ${pct(b.cmp)}</span></td></tr>
  <tr><td>Yards / target allowed</td><td>${f2(d.ypt,1)} <span class="mut">lg ${f2(b.ypt,1)}</span></td></tr><tr><td>EPA / target vs avg</td><td class="${d.d>0?'hot':'cold'}">${sg(d.d)} <span class="mut">${ord(rkd)} stingiest</span></td></tr>
  <tr><td>${esc(off.k)} O share of targets</td><td>${pct(o.share)} <span class="mut">lg ${pct(b.share)}</span></td></tr><tr><td>${esc(off.k)} O yards / target</td><td>${f2(o.ypt,1)}</td></tr><tr><td>${esc(off.k)} O EPA / target vs avg</td><td class="${o.d>0?'hot':'cold'}">${sg(o.d)}</td></tr></table></div>`}
 const d=def.def.lanes[z],o=off.off.lanes[z],b=L().lanes[z];const rkd=Object.values(D.teams).map(t=>t.def.lanes[z].epa).sort((a,b)=>a-b).indexOf(d.epa)+1;
 return `<div class="sw-card sw-detail"><h3>${esc(LANE[z])}</h3><table><tr><td>${esc(def.k)} D carries faced</td><td>${d.n}${d.n<T?' · thin':''}</td></tr>
 <tr><td>Yards / carry allowed</td><td>${f2(d.ypc,1)} <span class="mut">lg ${f2(b.ypc,1)}</span></td></tr><tr><td>10+ yd runs allowed</td><td>${pct(d.x10)} <span class="mut">lg ${pct(b.x10)}</span></td></tr>
 <tr><td>EPA / carry vs avg</td><td class="${d.d>0?'hot':'cold'}">${sg(d.d)} <span class="mut">${ord(rkd)} stingiest</span></td></tr><tr><td>${esc(off.k)} O share of carries</td><td>${pct(o.share)} <span class="mut">lg ${pct(b.share)}</span></td></tr>
 <tr><td>${esc(off.k)} O yards / carry</td><td>${f2(o.ypc,1)}</td></tr><tr><td>${esc(off.k)} O EPA / carry vs avg</td><td class="${o.d>0?'hot':'cold'}">${sg(o.d)}</td></tr></table></div>`}
/* ---------- render ---------- */
function render(){const el=root.querySelector('#sw')||root;if(!G.length){el.innerHTML='<div class="sw-card">No games on this week\'s slate yet.</div>';return}
 const g=G.find(x=>x.k===st.g)||G[0];const oK=st.flip?g.hm:g.aw,dK=st.flip?g.aw:g.hm;const off=Object.assign({k:oK},D.teams[oK]),def=Object.assign({k:dK},D.teams[dK]);const all=attack(off,def),ok=all.filter(a=>!a.thin),acts=ok.filter(a=>a.kind==='pass').slice(0,2).concat(ok.filter(a=>a.kind==='run').slice(0,1)).sort((a,b)=>b.score-a.score);
 const upd=new Date(D.updated);const ago=isNaN(upd)?'':upd.toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/New_York'})+' ET';
 const lp=st.mode==='off'?['Offense below league','Offense above league']:st.mode==='def'?['Defense stingier','Defense gives up more']:['Tougher spot','Better spot to attack'];
 el.innerHTML=`<div class="sw-head"><div><div class="sw-eye">NFL HUB · STRENGTHS &amp; WEAKNESSES</div><h2>${esc(oK)} offense vs ${esc(dK)} defense</h2><p class="sw-sub">Where the defense bends, where it holds, and where this offense likes to go. Season to date through Week ${esc(D.through_week)}.</p></div><div class="sw-stamp">UPDATED ${esc(ago)}</div></div>
 <div class="sw-games" role="group" aria-label="This week's games">${G.map(x=>`<button type="button" data-g="${esc(x.k)}" aria-pressed="${x.k===g.k}">${esc(x.aw)} @ ${esc(x.hm)}<small>${esc(x.when)}</small></button>`).join('')}</div>
 <div class="sw-bar"><div class="sw-seg" role="group" aria-label="Map layer">${[['plan','Attack plan'],['def','Defense allowed'],['off','Offense']].map(([k,t])=>`<button type="button" data-m="${k}" aria-pressed="${st.mode===k}">${t}</button>`).join('')}</div>
 <button type="button" class="sw-swap" data-flip="1">⇄ Show ${esc(dK)} offense vs ${esc(oK)} defense</button></div>
 <div class="sw-grid"><div><div class="sw-card" style="padding:10px">${field(off,def,acts)}
 <div class="sw-leg"><span>${lp[0]}</span><i></i><span>${lp[1]}</span><span class="hatch"></span><span>Thin sample (under ${D.k.thin} plays): shown, not colored</span>${st.mode==='plan'?'<span>· <b style="color:#ffd166">①②③</b> expected attack</span>':''}</div>
 <div class="mut sm" style="margin-top:6px">${(root.clientWidth||innerWidth)<640?'Offense drives up the screen; run lanes sit behind the line.':'Offense drives left to right; run lanes sit behind the line. Left/right are from the offense\'s view (left sideline at top).'} Numbers are EPA per play versus the league average for that zone${st.mode==='plan'?' (defense allowed + offense produced)':''}.</div></div>
 ${detail(off,def)}</div>
 <div>${planCard(off,def,acts,all)}${rushCard(off,def)}${runCard(off,def)}
 <details class="sw-card sw-how"><summary>How to read this</summary><p>Pass zones split targets by air yards (short under 10, intermediate 10–19, deep 20+) and by direction. Run lanes split designed runs by gap. Each cell compares EPA per play with the league average for that same zone, with small samples pulled toward average (${D.k.pass} pass / ${D.k.run} run plays of league prior) so a few plays can't dominate.</p><p>Attack plan adds the defense's weakness to the offense's strength in each zone, with a small nudge toward zones the offense already uses a lot, then marks the two best throwing zones and the best run lane. Zones under ${D.k.thin} plays are never marked. Pressure rate = charted pressures divided by dropbacks. Regular season only. Not a pick and not a price.</p><p>Updates automatically with the Hub's daily refresh.</p></details></div></div>`;
 el.querySelectorAll('[data-g]').forEach(b=>b.onclick=()=>{st.g=b.dataset.g;st.flip=false;st.sel=null;history.replaceState(null,'','#strengths/'+st.g);render()});
 el.querySelectorAll('[data-m]').forEach(b=>b.onclick=()=>{st.mode=b.dataset.m;render()});
 el.querySelector('[data-flip]').onclick=()=>{st.flip=!st.flip;st.sel=null;render()};
 el.querySelectorAll('.z').forEach(z=>{const go=()=>{st.sel=st.sel===z.dataset.z?null:z.dataset.z;render();const d=root.querySelector('.sw-detail');if(d&&innerWidth<900)d.scrollIntoView({behavior:'smooth',block:'nearest'})};z.addEventListener('click',go);z.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}})});
}
let rw=0;addEventListener('resize',()=>{if(!root||root.hidden||root.dataset.k!=='strengths'||!D)return;const v=(root.clientWidth||innerWidth)<640;if(v!==rw){rw=v;render()}});
window.NFLStrengths={open:k=>{location.hash='strengths'+(k?'/'+k:'')}};
function init(){addEventListener('hashchange',show);show()}
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();
