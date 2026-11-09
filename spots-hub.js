/* NFL Hub · Spots in-page view (index.html#spots[/view]). Preview integration; display-only. */
(function(){'use strict';
const VIEWS=['td-wrte','td-rb','line-te','line-wr','line-rb','line-qb','roles','matchups','soft'];
const CSS=`<style id="sphcss">body.spots-on .w>*:not(header):not(#spots-root):not(footer):not(#sl-modal-root){display:none!important}
body.spots-on{background:#080f11;color:#dce9e8}body.spots-on .w{max-width:1440px;padding:18px 24px}body.spots-on .w>header{padding-bottom:14px;border-bottom:1px solid #213236;margin-bottom:18px}
body.spots-on .sl-side{background:#0d191c;border-color:#223438;width:206px;font-size:14px}body.spots-on .sl-side h4{color:#899c9f;font-size:11px}body.spots-on .sl-side a{border-radius:3px;padding:8px 10px;color:#aebfc0;font-weight:500}body.spots-on .sl-side a.cur{background:#162d2d;box-shadow:inset 2px 0 #32c9b5;color:#e7f6f1}body.spots-on .sl-tog{background:#122528;border-color:#294044;color:#b8d2d0}
#spots-root{--vb:#111f22;--vp:#14272a;--vl:#263a3d;--vm:#32c9b5;--vt:#dfebea;--vs:#9db1b3;color:var(--vt);font:14px/1.5 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:1280px;margin:0 auto}
#spots-root .spot-head{display:none}#spots-root .vz-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin:4px 0 16px}#spots-root .vz-heading h2{font-size:24px;line-height:1.2;font-weight:750;letter-spacing:-.6px;margin:3px 0 6px}#spots-root .vz-heading p{margin:0;color:var(--vs);font-size:14px}
#spots-root .vz-eyebrow{font-size:10px;font-weight:750;color:#68adab;letter-spacing:1.3px}#spots-root .vz-status{display:flex;align-items:center;gap:7px;font:11px/1.4 ui-monospace,monospace;color:#a6bfbc;border:1px solid #2a4444;border-radius:4px;padding:5px 9px;white-space:nowrap}#spots-root .vz-status i{height:5px;width:5px;background:var(--vm);border-radius:50%}
#spots-root #spot-status{margin:0 0 14px;color:var(--vs);font-size:13px}#spots-root #spot-views{display:flex;gap:0;flex-wrap:wrap;border-bottom:1px solid var(--vl);padding-bottom:12px;margin:0 0 14px;overflow:auto}
#spots-root #spot-views button{border:1px solid var(--vl);border-right:0;background:#0d1b1e;color:#a8bcbc;padding:9px 14px;min-height:40px;font:650 13px/1.2 inherit;cursor:pointer;white-space:nowrap}#spots-root #spot-views button:first-child{border-radius:5px 0 0 5px}#spots-root #spot-views button:last-child{border-radius:0 5px 5px 0;border-right:1px solid var(--vl)}#spots-root #spot-views button[aria-pressed=true]{background:#176269;color:#e6fffa;border-color:#378e8b}
#spots-root .section-label{font-size:11px;letter-spacing:.4px;color:#9db5b6;text-transform:uppercase;margin:0 0 8px}#spots-root .section-label span{text-transform:none;letter-spacing:0;color:var(--vs);margin-left:8px;font-weight:500}
#spots-root #spot-games{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px}#spots-root #spot-controls{display:flex;gap:12px;flex-wrap:wrap;align-items:end;margin:0 0 16px}#spots-root .spot-controls{display:flex;gap:12px;flex-wrap:wrap;align-items:end;width:100%}
#spots-root label{display:flex;flex-direction:column;gap:5px;font-size:11px;color:var(--vs)}#spots-root select,#spots-root input[type=search]{min-height:40px;padding:8px 10px;border-radius:4px;border:1px solid var(--vl);background:#0e1c1f;color:var(--vt);font:inherit}
#spots-root .spot-heading{display:flex;justify-content:space-between;align-items:end;gap:12px;margin:0 0 12px}#spots-root .spot-heading h2{margin:0;font-size:18px;font-weight:700}#spots-root .spot-heading p{margin:4px 0 0;color:var(--vs);font-size:13px}#spots-root #spot-count{color:var(--vs);font-size:12px;white-space:nowrap}
#spots-root .spot-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}#spots-root .spot-card{background:var(--vb);border:1px solid var(--vl);border-radius:6px;padding:16px;box-shadow:0 2px 8px #00000012}#spots-root .spot-empty{border:1px dashed var(--vl);border-radius:6px;padding:28px;color:var(--vs);text-align:center}
#spots-root .spot-method{margin-top:18px;color:var(--vs);font-size:12px}#spots-root footer{display:none}
@media(min-width:768px){body.spots-on.sl-open{padding-left:206px}}
@media(max-width:600px){body.spots-on .w{padding:12px}#spots-root .vz-heading{flex-direction:column;gap:8px}#spots-root .vz-heading h2{font-size:21px}#spots-root #spot-views button{flex:1 1 auto;padding:9px 11px;font-size:12px}#spots-root .spot-heading{flex-direction:column;align-items:start}}</style>`;

function parse(){const h=location.hash.slice(1);if(h==='spots')return {on:true,view:null};const m=/^spots\/([\w-]+)$/.exec(h);if(m&&VIEWS.includes(m[1]))return {on:true,view:m[1]};return {on:false,view:null}}
let root=null,booted=false;
function ensureShell(){
 if(!root){const hd=document.querySelector('.w>header');root=document.createElement('section');root.id='spots-root';root.hidden=true;root.setAttribute('aria-live','polite');(hd?hd.after(root):document.querySelector('.w')?.prepend(root)||document.body.prepend(root))}
 if(!document.getElementById('sphcss'))document.head.insertAdjacentHTML('beforeend',CSS);
 root.innerHTML=`<div class="vz-heading"><div><div class="vz-eyebrow">NFL HUB · SPOTS</div><h2>Your NFL spot check</h2><p>Nine views. One place. Pick a game, check the numbers, open the player.</p></div><div class="vz-status" title="Recorded snapshot"><i></i><span>RECORDED · NOT LIVE</span></div></div>
 <div id="spot-status" role="status">Checking the recorded snapshot…</div>
 <nav id="spot-views" aria-label="Spots views"></nav>
 <section aria-label="Game filter"><div class="section-label">Upcoming games <span>Choose a tile or use All games</span></div><div id="spot-games"></div></section>
 <div id="spot-controls"></div>
 <header class="spot-heading"><div><h2 id="spot-title"></h2><p id="spot-caption"></p></div><span id="spot-count" role="status"></span></header>
 <div id="spot-board" aria-live="polite"></div>
 <details class="spot-method"><summary>Coverage & how to read these views</summary><p>Built from existing Hub snapshots. Current-game offers fail closed after source expiry or kickoff. These are not live prices or new picks.</p><p id="spot-provenance"></p></details>`;
}
function loadSpots(){return new Promise((resolve,reject)=>{
 if(window.SpotCore&&window.SpotsApp)return resolve();
 const need=[];
 if(!window.SpotCore)need.push('spots-core.js?v=1109hub1');
 if(!document.querySelector('link[href*="spots.css"]')){const l=document.createElement('link');l.rel='stylesheet';l.href='spots.css?v=1109hub1';document.head.appendChild(l)}
 if(!window.SpotsApp)need.push('spots.js?v=1109hub1');
 let left=need.length;if(!left)return resolve();
 need.forEach(src=>{const s=document.createElement('script');s.src=src;s.onload=()=>{if(--left===0)resolve()};s.onerror=()=>reject(Error('Spots assets unavailable'));document.head.appendChild(s)});
})}
async function show(){
 const {on,view}=parse();document.body.classList.toggle('spots-on',on);if(!root&&!on)return;ensureShell();root.hidden=!on;if(!on)return;
 try{await loadSpots();window.SpotsHub={active:true,view};if(window.SpotsApp){if(!booted){booted=true;await window.SpotsApp.boot()}else window.SpotsApp.render()}
 }catch(e){root.querySelector('#spot-board').textContent='Spots could not load. Existing Hub pages are unchanged.'}}
function init(){addEventListener('hashchange',show);show()}
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();
