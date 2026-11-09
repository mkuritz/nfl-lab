/* Statistical alternate thresholds only. Does not alter Highlighted/model logic. */
(function(){
'use strict';
const TAGS=new Set('p h2 h3 div label select option input button article span strong small b details summary br'.split(' '));
const ATTRS=new Set('class style value type min max step placeholder role title aria-label aria-live aria-hidden aria-pressed hidden data-control data-reset data-count data-rows data-detail data-history data-chips data-page-note data-floor-note data-rung data-rung-bar data-results data-card-rung'.split(' '));
function h(tag,attrs,...children){if(!TAGS.has(tag))throw Error('Unsupported element');const e=document.createElement(tag);for(const [key,value] of Object.entries(attrs||{})){if(!ATTRS.has(key))throw Error('Unsupported attribute');e.setAttribute(key,String(value))}for(const child of children.flat(Infinity))if(child!=null)e.append(child instanceof Node?child:document.createTextNode(String(child)));return e}

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
 // Passing TDs: prefer calibrated recommend rung when it still clears the streak minimum.
 if(row.category==='Passing TDs'&&row.recommend!=null){
  const rec=Number(row.recommend);
  if(Number.isFinite(rec)&&rec>=1&&evaluate(row,rec).streak>=min)return rec;
 }
 const valid=row.presets.map(Number).filter(f=>Number.isFinite(f)&&f>=1&&evaluate(row,f).streak>=min);
 return valid.length?valid[valid.length-1]:Number(row.presets[0]);
}
function select(rows,state){
 return rows.filter(r=>(!state.category||r.category===state.category)&&(!state.pos||r.pos===state.pos)).map(r=>{
 const floor=state.floor===''?defaultFloor(r,state.min):Number(state.floor);
 return {...r,...evaluate(r,floor)};
 }).filter(r=>r.streak>=state.min).sort((a,b)=>state.sort==='name'?a.name.localeCompare(b.name):state.sort==='position'?a.pos.localeCompare(b.pos)||b.streak-a.streak:state.sort==='category'?a.category.localeCompare(b.category)||b.streak-a.streak:b.streak-a.streak||b.floor-a.floor||a.name.localeCompare(b.name));
}

/* ---- Passing TD Poisson ladder (same mean blend as pro_analytics) ---- */
const PASS_TD_MIN_MODEL=0.60, PASS_TD_MIN_EMP=0.60, PASS_TD_MIN_EDGE=0.02;
function poissonTail(lam,kMin){
 if(kMin<=0)return 1; if(!(lam>0))return 0;
 let cdf=0, term=Math.exp(-lam);
 for(let k=0;k<kMin;k++){ if(k>0) term*=lam/k; cdf+=term; }
 return Math.max(1e-4, Math.min(1-1e-4, 1-cdf));
}
function projectedMean(values){
 const vals=values.filter(v=>v!=null&&Number.isFinite(Number(v))).map(Number);
 if(!vals.length)return null;
 const recent=vals.slice(0,10);
 return 0.65*(recent.reduce((a,b)=>a+b,0)/recent.length)+0.35*(vals.reduce((a,b)=>a+b,0)/vals.length);
}
function recommendPassTdRung(row,thresholds){
 const thr=Object.assign({min_model:PASS_TD_MIN_MODEL,min_emp:PASS_TD_MIN_EMP,min_edge:PASS_TD_MIN_EDGE},thresholds||{});
 if(row.recommend!=null&&Array.isArray(row.rungs)&&row.rungs.length)return {recommend:Number(row.recommend),rungs:row.rungs,mu:row.mu};
 const vals=(row.games||[]).filter(g=>!g.dnp).map(g=>g.value);
 const mu=projectedMean(vals); if(mu==null)return {recommend:1,rungs:[],mu:null};
 const played=vals.filter(v=>v!=null).map(Number);
 const rungs=[1,2,3].map(k=>{
  const model_p=poissonTail(mu,k);
  const emp_n=Math.min(played.length,10);
  const emp_h=played.slice(0,10).filter(v=>v>=k).length;
  const emp_p=emp_n?emp_h/emp_n:null;
  const p_emp=emp_n?(emp_h+1.5*model_p)/(emp_n+1.5):model_p;
  const p=emp_n?0.6*model_p+0.4*p_emp:model_p;
  const pre=(row.rungs||[]).find(r=>r.k===k)||{};
  const edge=pre.edge!=null?pre.edge:null;
  let clears=p>=thr.min_model&&(emp_p==null||emp_p>=thr.min_emp||emp_n<4);
  if(edge!=null&&pre.price!=null) clears=clears&&edge>=thr.min_edge;
  return {k,line:k-0.5,mu:Math.round(mu*1000)/1000,model_p:+model_p.toFixed(4),emp_p:emp_p==null?null:+emp_p.toFixed(4),p:+p.toFixed(4),price:pre.price??null,book:pre.book??null,nv:pre.nv??null,edge,clears,price_missing:pre.price==null};
 });
 let recommend=1; for(let i=rungs.length-1;i>=0;i--) if(rungs[i].clears){recommend=rungs[i].k;break;}
 return {recommend,rungs,mu};
}

window.LowHurdlesMath={evaluate,defaultFloor,select,poissonTail,projectedMean,recommendPassTdRung,PASS_TD_MIN_MODEL,PASS_TD_MIN_EMP,PASS_TD_MIN_EDGE};
const time=t=>t?new Date(t).toLocaleString('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' ET':'Time unavailable';
const short={Points:'Points',Rebounds:'Rebounds',Assists:'Assists',Threes:'Threes','Receiving yards':'Rec yards','Rushing yards':'Rush yards','Passing yards':'Pass yards','Passing TDs':'Pass TDs','Rush + Rec yards':'Rush + Rec','Kicking points':'Kick points',Receptions:'Receptions'};
const result=(g,f)=>g.dnp?'DNP':g.value==null?'Missing':g.value>=f?'Clear':'Miss';
const pct=p=>p==null?'—':Math.round(p*100)+'%';
const am=px=>{if(px==null)return '—';const n=Number(px);return n>0?'+'+Math.round(n):String(Math.round(n));};

window.mountAlternateHurdles=async function(root,sport){
 if(!root||root.dataset.loaded)return;root.dataset.loaded='1';root.classList.add('lhx');if(sport==='nfl')document.documentElement.classList.add('lhx-active');
 if(!document.getElementById('lhx-css')){const link=document.createElement('link');link.id='lhx-css';link.rel='stylesheet';link.href='alternate-hurdles.css?v=1109passtd';document.head.append(link);}
 root.textContent='Loading player history…';
 let d;try{const res=await fetch('data/low_hurdles_alternates.json?v=1109passtd',{mode:'same-origin',credentials:'same-origin',redirect:'error'});if(!res.ok)throw Error();d=await res.json();}catch(e){root.textContent='Player logs unavailable. Please try again later. No streaks inferred.';return;}
 const state={category:'',pos:'',floor:'',min:5,sort:'streak'};let page=0;
 const thr=d.thresholds||{};
 const chooser=(key,options,label)=>h('select',{'data-control':key,'aria-label':label},options.map(([value,label])=>h('option',{value},label)));
 root.replaceChildren(
  h('div',{class:'lhx-top'},h('div',{},h('div',{class:'lhx-eyebrow'},'Player streaks · '+d.season),h('h2',{},'Low Hurdles'),h('p',{},'Find easier floors. Explore the games behind every streak. Passing TDs use a 1+/2+/3+ ladder with a calibrated recommendation.')),h('div',{class:'lhx-meta'},'Completed-log snapshot',h('br',{}),time(d.updated))),
  h('span',{class:'lhx-label'},'Prop category'),h('div',{class:'lhx-chipbar','data-chips':'category'}),
  h('span',{class:'lhx-label'},'Position'),h('div',{class:'lhx-chipbar','data-chips':'pos'}),
  chooser('category',[['','All categories'],...d.categories.map(c=>[c,c])],'Category'),
  chooser('pos',[['','All positions'],...[...new Set(d.rows.map(r=>r.pos))].sort().map(c=>[c,c])],'Position'),
  h('div',{class:'lhx-tools'},
   h('label',{},h('span',{class:'lhx-label'},'Floor to clear'),h('input',{'data-control':'floor',type:'number',min:1,step:1,placeholder:'Auto · individual player floors'}),h('div',{class:'lhx-rungbar','data-rung-bar':'','hidden':''}),h('small',{'data-floor-note':''},'Blank = each player’s highest qualifying easy preset.')),
   h('label',{},h('span',{class:'lhx-label'},'Consecutive games'),h('input',{'data-control':'min',type:'number',min:1,max:30,value:5}),h('small',{},'Minimum active no-miss run. Passing TDs often clear at 2–3.')),
   h('label',{},h('span',{class:'lhx-label'},'Sort by'),chooser('sort',[['streak','Longest streak'],['position','Position'],['category','Prop category'],['name','Player name']],'Sort by')),
   h('button',{type:'button',class:'lhx-reset','data-reset':''},'Reset filters')
  ),
  h('div',{class:'lhx-results'},h('div',{'data-count':'',role:'status','aria-live':'polite'}),h('span',{class:'lhx-meta','data-page-note':''})),
  h('div',{'data-rows':'',class:'lhx-grid cand-grid'}),
  h('details',{class:'lhx-grade','data-results':''},
   h('summary',{},'Passing TD ladder results · consolidated'),
   h('div',{class:'lhx-grade-body'},'Select Passing TDs to see Week 9 (Nov 8 finals) ladder backtest for recommended rungs.')
  ),
  h('details',{},h('summary',{},'How floors, streaks & hit rates work'),h('p',{},'Statistical floors—not necessarily available betting markets. Auto picks each player’s highest easy preset clearing the selected minimum; changing the minimum can change that floor. A manual floor applies the same number to every filtered row, so choose one category for consistent units.'),h('p',{},'Passing TDs: Poisson from the projected per-game mean (0.65×L10 + 0.35×season). Recommend the highest of 1+/2+/3+ that clears model ≥60%, L10 ≥60%, and +2% edge when a live alt price exists. Switch rungs with the dark pills. Missing alt prices are disclosed; existing Highlighted plays and estimators are unchanged.'),h('p',{},'Only '+d.season+' completed logs in this snapshot are used, not live totals. Missing totals stop a run and are excluded from known-game hit rates; zeros count as misses. Explicit DNPs and byes do not count as played games. Injury designations do not confirm participation. Historical streaks do not guarantee future results.'))
 );

 function chips(key,values){
  const box=root.querySelector('[data-chips="'+key+'"]');box.replaceChildren();
  for(const v of ['',...values]){const button=document.createElement('button');button.type='button';button.dataset.chip=v;button.setAttribute('aria-pressed',String(state[key]===v));button.textContent=v?(short[v]||v):'All';box.append(button);button.onclick=()=>{state[key]=v;root.querySelector('[data-control="'+key+'"]').value=v;page=0;if(key==='category') syncRungBar();render();const active=Array.from(box.querySelectorAll('button')).find(x=>x.dataset.chip===state[key]);if(active)active.focus();};}
 }

 function syncRungBar(){
  const bar=root.querySelector('[data-rung-bar]');
  const floorInput=root.querySelector('[data-control="floor"]');
  const passTd=state.category==='Passing TDs';
  if(!passTd){bar.hidden=true;bar.replaceChildren();floorInput.hidden=false;return;}
  floorInput.hidden=true;bar.hidden=false;
  const pills=['','1','2','3'].map(k=>{
   const btn=document.createElement('button');btn.type='button';btn.className='lhx-rung';btn.dataset.rung=k;
   const pressed=k===''?state.floor==='':String(state.floor)===k;
   btn.setAttribute('aria-pressed',String(pressed));
   btn.textContent=k===''?'Auto · recommended':k+'+ Pass TDs';
   btn.onclick=()=>{state.floor=k;floorInput.value=k;page=0;render();syncRungBar();};
   return btn;
  });
  bar.replaceChildren(...pills);
 }

 function canOpen(trigger){
  if(!trigger?.isConnected||trigger.closest('[inert],.sl-locked'))return false;
  if(typeof window.SLGateState!=='function')return false;
  const access=window.SLGateState(),row=trigger.closest('.lhx-card'),grid=row?.parentElement;if(!row||!grid)return false;
  if(access.paid)return true;
  const index=Array.from(grid.children).filter(e=>e.classList.contains('lhx-card')).indexOf(row);
  return index>=0&&index<(access.session?2:1);
 }
 function detail(r,trigger){
  const dialog=document.createElement('dialog');dialog.className='lhx-dialog';dialog.setAttribute('aria-labelledby','lhx-title');
  const add=(tag,text,parent=dialog)=>{const el=document.createElement(tag);el.textContent=text;parent.append(el);return el;};
  const close=add('button','Close ✕');close.type='button';close.dataset.close='';close.className='lhx-close';
  add('div',r.team+' · '+r.pos+' · '+d.season).className='lhx-eyebrow';const title=add('h2',r.name);title.id='lhx-title';
  add('p',r.floor+'+ '+r.category+' · '+r.streak+' straight clears · Season: '+r.hits+'/'+r.n+' ('+(r.n?Math.round(100*r.hits/r.n):0)+'%)');
  if(r.category==='Passing TDs'){
   const ladder=recommendPassTdRung(r,thr);
   add('p','Projected mean '+((ladder.mu!=null)?ladder.mu.toFixed(2):'—')+' pass TD/g · Recommended '+ladder.recommend+'+ (model ≥60% · L10 ≥60% · +2% edge when priced).');
   const lad=add('div','');lad.className='lhx-ladder';
   for(const rg of ladder.rungs){
    const pill=document.createElement('div');pill.className='lhx-ladder-row'+(rg.k===r.floor?' on':'')+(rg.clears?' clears':'');
    pill.textContent=rg.k+'+ · model '+pct(rg.p)+(rg.price!=null?' · '+am(rg.price):' · price n/a')+(rg.edge!=null?' · edge '+(rg.edge*100).toFixed(1)+'%':'')+(rg.k===ladder.recommend?' · recommended':'');
    lad.append(pill);
   }
   dialog.append(lad);
  }
  add('p','Threshold retained: '+r.floor+'+. '+r.status+'. Missing totals: '+r.missing+' · DNPs: '+r.dnp+'.');
  const heading=add('h3','Recent game totals');heading.style.marginBottom='0';
  const plotted=r.games.slice(0,12).reverse();const max=Math.max(r.floor,...plotted.filter(g=>!g.dnp&&g.value!=null).map(g=>Math.max(0,Number(g.value))))||1;
  const chart=add('div','');chart.className='lhx-chart';chart.setAttribute('role','img');chart.setAttribute('aria-label','Oldest to newest game totals. Selected floor '+r.floor+'. '+plotted.map(g=>g.label+': '+(g.value??'missing')+' '+result(g,r.floor)).join('; '));
  for(const g of plotted){const col=add('div','',chart);col.className='lhx-barcol';const label=g.dnp?'DNP':g.value==null?'?':String(g.value);add('span',label,col).className='lhx-value';const bar=add('div','',col);bar.className='lhx-bar '+(g.dnp||g.value==null?'unknown':g.value<r.floor?'miss':'');bar.style.height=(g.dnp||g.value==null?3:Math.max(3,100*Math.max(0,Number(g.value))/max))+'%';col.title=g.label+' · '+label+' · '+result(g,r.floor);}
  add('p','Oldest → newest · Teal clears '+r.floor+'+ · Rose misses · Gray unavailable. Bar height = actual total; negative totals are labeled at the baseline.').style.fontSize='12px';
  const history=add('details','');const summary=add('summary','All games · '+r.games.length+' log entries',history);history.open=true;
  for(const g of r.games){const row=add('div','',history);row.className='lhx-log';add('span',g.label,row);const txt=add('span',(g.dnp?'DNP':g.value==null?'Missing':String(g.value))+' · '+result(g,r.floor),row);txt.className=g.dnp||g.value==null?'':g.value>=r.floor?'lhx-pass':'lhx-fail';}
  const native=add('button','Open full player profile →');native.type='button';native.dataset.native='';native.className='lhx-native';add('p','Full profile uses standard Hub metrics. This history uses your selected floor.').style.fontSize='12px';
  document.body.append(dialog);close.onclick=()=>dialog.close();dialog.addEventListener('close',()=>{dialog.remove();if(trigger&&trigger.isConnected)trigger.focus();});native.onclick=()=>{if(!canOpen(trigger)){dialog.close();return;}dialog.close();if(sport==='nfl'&&window.NFLProfile)window.NFLProfile(r.id);else if(window.NBAHubProfiles)window.NBAHubProfiles.openPlayer(r.id,r.category);};dialog.showModal();close.focus();
 }

 function gradePanel(passRows){
  const box=root.querySelector('[data-results] .lhx-grade-body');
  if(!box)return;
  // Week 9 = Nov 8, 2026 Sunday slate in this snapshot
  const week=9;
  const lines=[];
  let n1=0,h2=0,h3=0,nRec=0,hRec=0;
  for(const r of passRows){
   const g=r.games.find(x=>!x.dnp&&x.week===week&&x.value!=null);
   if(!g)continue;
   const ladder=recommendPassTdRung(r,thr);
   const hit1=g.value>=1, hit2=g.value>=2, hit3=g.value>=3;
   if(hit1){n1++; if(hit2)h2++; if(hit3)h3++;}
   const rec=ladder.recommend||1; nRec++; if(g.value>=rec)hRec++;
   lines.push({name:r.name,team:r.team,td:g.value,rec,hit1,hit2,hit3,mu:ladder.mu});
  }
  const summary=document.createElement('p');
  const recPct=nRec?Math.round(100*hRec/nRec):0;
  if(n1){summary.textContent='Week '+week+' finals (Nov 8): of '+n1+' QBs who hit 1+ Pass TDs, '+h2+' ('+Math.round(100*h2/n1)+'%) also hit 2+ and '+h3+' ('+Math.round(100*h3/n1)+'%) hit 3+. Recommended-rung record '+hRec+'-'+(nRec-hRec)+' ('+recPct+'%).';}
  else{summary.textContent='Week 9 Passing TD finals not found in this snapshot.';}
  const list=document.createElement('div');list.className='lhx-grade-list';
  for(const L of lines.sort((a,b)=>b.td-a.td||a.name.localeCompare(b.name))){
   const row=document.createElement('div');row.className='lhx-grade-row';
   row.textContent=`${L.name} (${L.team}) · ${L.td} Pass TD · rec ${L.rec}+ · ${L.hit1?'1✓':'1✗'} ${L.hit2?'2✓':'2✗'} ${L.hit3?'3✓':'3✗'}`;
   list.append(row);
  }
  box.replaceChildren(summary,list);
 }

 function render(){
  chips('category',d.categories);chips('pos',[...new Set(d.rows.map(r=>r.pos))].sort());syncRungBar();
  if(!Number.isInteger(Number(state.min))||state.min<1||(state.floor!==''&&(!Number.isInteger(Number(state.floor))||Number(state.floor)<1))){root.querySelector('[data-count]').textContent='Enter positive whole numbers for floor and minimum games.';root.querySelector('[data-rows]').replaceChildren();return;}
  const rows=select(d.rows,state),shown=rows;
  const oldGrid=root.querySelector('[data-rows]');const fresh=oldGrid.cloneNode(false);fresh.className='lhx-grid cand-grid';oldGrid.replaceWith(fresh);
  const passNote=state.category==='Passing TDs'?(state.floor===''?'Auto = calibrated recommend rung':'Manual '+state.floor+'+ Pass TDs'):(state.floor===''?'Individual auto floors':state.floor+'+ manual floor');
  root.querySelector('[data-count]').textContent=rows.length+' player/category rows · '+new Set(rows.map(r=>r.id)).size+' players';
  root.querySelector('[data-page-note]').textContent=passNote;
  root.querySelector('[data-floor-note]').textContent=state.category==='Passing TDs'?(state.floor===''?'Auto uses the highest 1+/2+/3+ rung that clears model ≥60%, L10 ≥60%, and +2% edge when priced.':'Showing every QB at '+state.floor+'+ Passing TDs.'):(state.floor===''?'Blank = each player’s highest qualifying easy preset.':state.category?'Same '+state.floor+'+ '+state.category.toLowerCase()+' floor for all shown players.':'Same number across all categories. Select one for consistent units.');

  const cards=shown.map((r,i)=>{
   const recent=r.games.filter(g=>!g.dnp).slice(0,10),initials=String(r.name).split(' ').map(x=>x[0]).slice(0,2).join(''),status=r.status&&r.status!=='No designation in snapshot'&&r.status!=='Active'?r.status:'';
   const ladder=r.category==='Passing TDs'?recommendPassTdRung(r,thr):null;
   const rungPills=ladder?h('div',{class:'lhx-card-rungs'},[1,2,3].map(k=>{
    const rg=ladder.rungs.find(x=>x.k===k)||{p:null,clears:false};
    const on=r.floor===k;
    return h('button',{type:'button',class:'lhx-rung'+(on?' on':'')+(k===ladder.recommend?' rec':''),'data-card-rung':String(k),'aria-pressed':String(on),title:pct(rg.p)+(rg.clears?' clears':'')},k+'+');
   })) : null;
   const recBadge=ladder?h('div',{class:'lhx-rec'},'Recommended '+ladder.recommend+'+ · μ '+(ladder.mu!=null?ladder.mu.toFixed(2):'—')+' · model '+pct((ladder.rungs.find(x=>x.k===r.floor)||{}).p)):null;
   const priceNote=ladder?(function(){
    const rg=ladder.rungs.find(x=>x.k===r.floor);
    if(!rg)return null;
    return h('div',{class:'lhx-meta'},rg.price!=null?('Live alt '+am(rg.price)+(rg.edge!=null?' · edge '+(rg.edge*100).toFixed(1)+'%':'')):'Alt price unavailable for this rung');
   })():null;
   return h('article',{class:'lhx-card'},
    h('div',{class:'lhx-identity'},h('span',{class:'lhx-avatar','aria-hidden':'true'},initials),h('div',{},h('button',{type:'button',class:'lhx-name','data-detail':i},r.name),h('div',{class:'lhx-sub'},r.team+' · '+r.pos+' · '+(r.opp||'Opponent unavailable')))),
    h('div',{class:'lhx-floor'},r.floor+'+ ',h('span',{},r.category)),
    rungPills,recBadge,priceNote,
    h('div',{class:'lhx-stats'},h('div',{},h('b',{},r.streak),h('small',{},'Straight clears')),h('div',{},h('b',{},(r.n?Math.round(100*r.hits/r.n):0)+'%'),h('small',{},'Season · '+r.hits+'/'+r.n+' known games'))),
    h('div',{class:'lhx-run',role:'img','aria-label':'Recent games newest first: '+recent.map(g=>g.label+' '+(g.value??'missing')+' '+result(g,r.floor)).join('; ')},recent.map(g=>h('span',{class:'lhx-dot '+(g.value==null?'unknown':g.value<r.floor?'miss':''),title:g.label+': '+(g.value??'Missing')+' · '+result(g,r.floor)}))),
    h('div',{class:'lhx-meta'},'Recent games · newest first'+(r.missing?' · '+r.missing+' missing totals':'')),
    status?h('div',{class:'lhx-status'},status+' · participation not confirmed'):null,
    h('div',{class:'lhx-history'},h('span',{class:'lhx-meta'},(r.time&&Date.parse(r.time)<Date.now()?'Start passed · ':'')+time(r.time)),h('button',{type:'button','data-history':i,'aria-label':'View '+r.name+' '+r.floor+'+ '+r.category+' history'},'View history →'))
   );
  });
  root.querySelector('[data-rows]').replaceChildren(...(cards.length?cards:[h('div',{class:'lhx-empty'},h('h3',{},'No qualifying streaks'),h('p',{},'Try a lower floor, fewer consecutive games, or reset your filters.'))]));
  root.querySelectorAll('[data-detail],[data-history]').forEach(b=>b.onclick=()=>{if(canOpen(b))detail(shown[Number(b.dataset.detail??b.dataset.history)],b);});
  root.querySelectorAll('[data-card-rung]').forEach(b=>b.onclick=()=>{state.category='Passing TDs';state.floor=b.dataset.cardRung;root.querySelector('[data-control="category"]').value='Passing TDs';root.querySelector('[data-control="floor"]').value=state.floor;page=0;render();});
  gradePanel(d.rows.filter(r=>r.category==='Passing TDs'));
 }
 root.querySelectorAll('[data-control]').forEach(el=>el.addEventListener('input',()=>{state[el.dataset.control]=el.dataset.control==='min'?Number(el.value):el.value;page=0;if(el.dataset.control==='category')syncRungBar();render();}));
 root.querySelector('[data-reset]').onclick=()=>{Object.assign(state,{category:'',pos:'',floor:'',min:5,sort:'streak'});page=0;root.querySelectorAll('[data-control]').forEach(el=>el.value=state[el.dataset.control]);syncRungBar();render();};
 render();
};
})();
