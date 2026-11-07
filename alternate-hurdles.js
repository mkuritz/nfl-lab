/* Statistical alternate thresholds only. Does not alter Highlighted/model logic. */
(function(){
'use strict';
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function evaluate(row,floor){
 floor=Number(floor); if(!Number.isFinite(floor)||floor<1)throw new Error("Invalid floor");
 let streak=0,blocked=false,hits=0,n=0,missing=0,dnp=0;
 for(const g of row.games){
  if(g.dnp){dnp++;continue;}
  if(g.value==null||!Number.isFinite(Number(g.value))){missing++;blocked=true;continue;}
  n++;if(g.value>=floor)hits++;
  if(!blocked&&g.value>=floor)streak++;else blocked=true;
 }
 return {floor,streak,hits,n,missing,dnp};
}
function defaultFloor(row,min){
 const valid=row.presets.map(Number).filter(f=>Number.isFinite(f)&&f>=1&&evaluate(row,f).streak>=min);
 return valid.length?valid[valid.length-1]:Number(row.presets[0]);
}
function select(rows,state){
 return rows.filter(r=>(!state.category||r.category===state.category)&&(!state.pos||r.pos===state.pos)).map(r=>{
 const floor=state.floor===''?defaultFloor(r,state.min):Number(state.floor);
 return {...r,...evaluate(r,floor)};
 }).filter(r=>r.streak>=state.min).sort((a,b)=>state.sort==='name'?a.name.localeCompare(b.name):state.sort==='position'?a.pos.localeCompare(b.pos)||b.streak-a.streak:state.sort==='category'?a.category.localeCompare(b.category)||b.streak-a.streak:b.streak-a.streak||b.floor-a.floor||a.name.localeCompare(b.name));
}
window.LowHurdlesMath={evaluate,defaultFloor,select};
window.mountAlternateHurdles=async function(root,sport){
 if(!root||root.dataset.loaded)return;root.dataset.loaded='1';
 root.innerHTML='<p>Loading alternate floors…</p>';
 let d;try{const res=await fetch('data/low_hurdles_alternates.json?v=1106alt');if(!res.ok)throw Error();d=await res.json();}catch(e){root.innerHTML='<p>Alternate-floor logs unavailable. No streaks inferred.</p>';return;}
 const state={category:'',pos:'',floor:'',min:5,sort:'streak'};
 if(!document.getElementById('lh-responsive')){const style=document.createElement('style');style.id='lh-responsive';style.textContent='.lh-controls label{display:flex;flex-direction:column;gap:4px;max-width:100%}.lh-controls input,.lh-controls select,.lh-controls button{min-height:44px;max-width:100%;box-sizing:border-box}[data-rows] article{overflow-wrap:anywhere}[data-rows] button{min-height:44px}dialog table{border-collapse:collapse;table-layout:fixed}dialog th,dialog td{padding:6px;overflow-wrap:anywhere}@media(max-width:600px){.lh-controls{flex-direction:column}.lh-controls input,.lh-controls select{width:100%!important}[data-rows] strong{float:none!important;display:block}dialog{max-width:calc(100vw - 32px)!important;max-height:85vh;overflow:auto;box-sizing:border-box}}';document.head.appendChild(style);}

 root.innerHTML=`<h2>Low Hurdles · Statistical alternate floors</h2><p>${E(d.season)} only. Snapshot updated ${E(new Date(d.updated).toLocaleString('en-US',{timeZone:'America/New_York'}))} ET. The scheduled start may have passed; streaks use the completed logs available in this snapshot, not live totals. Historical streaks do not confirm participation; injury designations are shown. These thresholds are statistical floors, not necessarily offered betting markets; no odds are implied. Missing totals stop a streak. Explicit zero-minute/zero-snap DNPs and byes do not count as played games; a recorded zero counts as a miss.</p><p>Default: highest easy preset each player has cleared in the selected minimum run. A threshold override applies the same number across filtered categories (choose a category first for meaningful units). Season hit rate uses all known played totals; missing totals are excluded from that denominator and disclosed. Nothing changes Highlighted plays or estimators.</p>
 <div class="lh-controls" style="display:flex;flex-wrap:wrap;gap:12px;margin:15px 0">
 <label>Category <select data-control="category"><option value="">All categories</option>${d.categories.map(c=>`<option>${E(c)}</option>`).join('')}</select></label>
 <label>Position <select data-control="pos"><option value="">All positions</option>${[...new Set(d.rows.map(r=>r.pos))].sort().map(p=>`<option>${E(p)}</option>`).join('')}</select></label>
 <label>Threshold override <input data-control="floor" type="number" min="1" step="1" placeholder="Per-player preset" style="width:130px"></label>
 <label>Minimum streak <input data-control="min" type="number" min="1" max="30" value="5" style="width:60px"></label>
 <label>Sort <select data-control="sort"><option value="streak">Longest streak</option><option value="position">Position</option><option value="category">Prop category</option><option value="name">Player</option></select></label>
 <button type="button" data-reset>Reset</button></div><div data-count role="status"></div><div data-rows></div>`;
 function detail(r){
  const dialog=document.createElement('dialog');dialog.style.cssText='max-width:700px;width:90%;background:#121a2a;color:#e6e9ef;border:1px solid #65748b;border-radius:12px;padding:20px';
  const add=(tag,text,parent=dialog)=>{const el=document.createElement(tag);el.textContent=text;parent.append(el);return el;};
  const close=add('button','Close');close.type='button';close.dataset.close='';close.style.float='right';
  add('h2',r.name+' · '+r.floor+'+ '+r.category);
  add('p',d.season+' · '+r.streak+'/'+r.streak+' active run · '+r.status+' · Season: '+r.hits+'/'+r.n+' ('+(r.n?Math.round(100*r.hits/r.n):0)+'%) at this threshold. Missing totals: '+r.missing+'; explicit DNPs: '+r.dnp+'.');
  add('p','Threshold retained: '+r.floor+'+. Display-only statistical history.');
  const native=add('button','Open full in-hub profile');native.type='button';native.dataset.native='';
  add('p','Full profile uses standard Hub metrics; this selected-threshold history remains separate.');
  const table=add('table','');table.style.width='100%';const head=add('thead','',table);const hr=add('tr','',head);['Game','Total','At '+r.floor+'+'].forEach(x=>add('th',x,hr));const body=add('tbody','',table);
  for(const g of r.games){const tr=add('tr','',body);add('td',g.label,tr);add('td',g.dnp?'DNP':g.value==null?'Missing':String(g.value),tr);add('td',g.dnp?'Not played':g.value==null?'Unknown / stops run':g.value>=r.floor?'Clear':'Miss',tr);}
  document.body.append(dialog);dialog.querySelector('[data-close]').onclick=()=>dialog.close();dialog.addEventListener('close',()=>dialog.remove());
  dialog.querySelector('[data-native]').onclick=()=>{dialog.close();if(sport==='nfl'&&window.NFLProfile)window.NFLProfile(r.id);else if(window.NBAHubProfiles)window.NBAHubProfiles.openPlayer(r.id,r.category);};dialog.showModal();
 }
 function render(){
  if(!Number.isInteger(Number(state.min))||Number(state.min)<1||(state.floor!==''&&(!Number.isInteger(Number(state.floor))||Number(state.floor)<1))){root.querySelector('[data-count]').textContent='Enter positive whole numbers for threshold and minimum streak.';root.querySelector('[data-rows]').innerHTML='';return;}
  const rows=select(d.rows,state);
  root.querySelector('[data-count]').textContent=rows.length+' qualifying player/category rows · '+new Set(rows.map(r=>r.id)).size+' unique players · min '+state.min+' · '+(state.floor===''?'per-player easy preset':'global '+state.floor+'+ override');
  root.querySelector('[data-rows]').innerHTML=rows.length?rows.map((r,i)=>`<article style="border:1px solid #314158;border-radius:10px;padding:12px;margin:8px 0"><button type="button" data-detail="${i}" style="font-weight:bold">${E(r.name)}</button> <span>${E(r.team)} · ${E(r.pos)} · ${E(r.status)} · ${E(r.opp||'No upcoming opponent')}</span><strong style="float:right">${r.streak}/${r.streak} games</strong><div>${r.floor}+ ${E(r.category)} · season ${r.hits}/${r.n} (${r.n?Math.round(r.hits/r.n*100):0}%) · missing ${r.missing}</div><small>${r.time&&Date.parse(r.time)<Date.now()?'Scheduled start has passed · ':''}${r.time?E(new Date(r.time).toLocaleString('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}))+' ET':'Kickoff/tip time unavailable'} · Recent: ${r.games.filter(g=>!g.dnp).slice(0,r.streak).map(g=>E(g.value)).join(', ')}</small></article>`).join(''):'<p>No qualifying streaks at these controls. Lower the floor or minimum, or reset. Missing totals are never skipped to create a streak.</p>';
  root.querySelectorAll('[data-detail]').forEach(b=>b.onclick=()=>detail(rows[Number(b.dataset.detail)]));
 }
 root.querySelectorAll('[data-control]').forEach(el=>el.addEventListener('input',()=>{state[el.dataset.control]=el.dataset.control==='min'?Number(el.value):el.value;render();}));
 root.querySelector('[data-reset]').onclick=()=>{Object.assign(state,{category:'',pos:'',floor:'',min:5,sort:'streak'});root.querySelectorAll('[data-control]').forEach(el=>el.value=state[el.dataset.control]);render();};render();
};
})();
