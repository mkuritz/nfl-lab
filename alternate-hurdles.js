/* Statistical alternate thresholds only. Does not alter Highlighted/model logic. */
(function(){
'use strict';
const TAGS=new Set('p h2 h3 div label select option input button article span strong small b details summary br'.split(' '));
const ATTRS=new Set('class style value type min max step placeholder role title aria-label aria-live aria-hidden data-control data-reset data-count data-rows data-detail data-history data-chips data-page-note data-floor-note'.split(' '));
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
const time=t=>t?new Date(t).toLocaleString('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' ET':'Time unavailable';
const short={Points:'Points',Rebounds:'Rebounds',Assists:'Assists',Threes:'Threes','Receiving yards':'Rec yards','Rushing yards':'Rush yards','Passing yards':'Pass yards','Rush + Rec yards':'Rush + Rec','Kicking points':'Kick points',Receptions:'Receptions'};
const result=(g,f)=>g.dnp?'DNP':g.value==null?'Missing':g.value>=f?'Clear':'Miss';
window.mountAlternateHurdles=async function(root,sport){
 if(!root||root.dataset.loaded)return;root.dataset.loaded='1';root.classList.add('lhx');
 if(!document.getElementById('lhx-css')){const link=document.createElement('link');link.id='lhx-css';link.rel='stylesheet';link.href='alternate-hurdles.css?v=1106design';document.head.append(link);}
 root.textContent='Loading player history…';
 let d;try{const res=await fetch('data/low_hurdles_alternates.json?v=1106alt',{mode:'same-origin',credentials:'same-origin',redirect:'error'});if(!res.ok)throw Error();d=await res.json();}catch(e){root.textContent='Player logs unavailable. Please try again later. No streaks inferred.';return;}
 const state={category:'',pos:'',floor:'',min:5,sort:'streak'};let page=0;
 const chooser=(key,options,label)=>h('select',{'data-control':key,'aria-label':label},options.map(([value,label])=>h('option',{value},label)));
 root.replaceChildren(h('div',{class:'lhx-top'},h('div',{},h('div',{class:'lhx-eyebrow'},'Player streaks · '+d.season),h('h2',{},'Low Hurdles'),h('p',{},'Find easier floors. Explore the games behind every streak.')),h('div',{class:'lhx-meta'},'Completed-log snapshot',h('br',{}),time(d.updated))),h('span',{class:'lhx-label'},'Prop category'),h('div',{class:'lhx-chipbar','data-chips':'category'}),h('span',{class:'lhx-label'},'Position'),h('div',{class:'lhx-chipbar','data-chips':'pos'}),chooser('category',[['','All categories'],...d.categories.map(c=>[c,c])],'Category'),chooser('pos',[['','All positions'],...[...new Set(d.rows.map(r=>r.pos))].sort().map(c=>[c,c])],'Position'),h('div',{class:'lhx-tools'},h('label',{},h('span',{class:'lhx-label'},'Floor to clear'),h('input',{'data-control':'floor',type:'number',min:1,step:1,placeholder:'Auto · individual player floors'}),h('small',{'data-floor-note':''},'Blank = each player’s highest qualifying easy preset.')),h('label',{},h('span',{class:'lhx-label'},'Consecutive games'),h('input',{'data-control':'min',type:'number',min:1,max:30,value:5}),h('small',{},'Minimum active no-miss run.')),h('label',{},h('span',{class:'lhx-label'},'Sort by'),chooser('sort',[['streak','Longest streak'],['position','Position'],['category','Prop category'],['name','Player name']],'Sort by')),h('button',{type:'button',class:'lhx-reset','data-reset':''},'Reset filters')),h('div',{class:'lhx-results'},h('div',{'data-count':'',role:'status','aria-live':'polite'}),h('span',{class:'lhx-meta','data-page-note':''})),h('div',{'data-rows':'',class:'lhx-grid cand-grid'}),h('details',{},h('summary',{},'How floors, streaks & hit rates work'),h('p',{},'Statistical floors—not necessarily available betting markets. Auto picks each player’s highest easy preset clearing the selected minimum; changing the minimum can change that floor. A manual floor applies the same number to every filtered row, so choose one category for consistent units.'),h('p',{},'Only '+d.season+' completed logs in this snapshot are used, not live totals. Missing totals stop a run and are excluded from known-game hit rates; zeros count as misses. Explicit DNPs and byes do not count as played games. Injury designations do not confirm participation. Historical streaks do not guarantee future results. Existing Highlighted plays and estimators are unchanged.')));

 function chips(key,values){
  const box=root.querySelector('[data-chips="'+key+'"]');box.replaceChildren();
  for(const v of ['',...values]){const button=document.createElement('button');button.type='button';button.dataset.chip=v;button.setAttribute('aria-pressed',String(state[key]===v));button.textContent=v?(short[v]||v):'All';box.append(button);button.onclick=()=>{state[key]=v;root.querySelector('[data-control="'+key+'"]').value=v;page=0;render();const active=Array.from(box.querySelectorAll('button')).find(x=>x.dataset.chip===state[key]);if(active)active.focus();};}
 }

 // Read the existing shared gate state; do not create another entitlement tier.
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
 function render(){
  chips('category',d.categories);chips('pos',[...new Set(d.rows.map(r=>r.pos))].sort());
  if(!Number.isInteger(Number(state.min))||state.min<1||(state.floor!==''&&(!Number.isInteger(Number(state.floor))||Number(state.floor)<1))){root.querySelector('[data-count]').textContent='Enter positive whole numbers for floor and minimum games.';root.querySelector('[data-rows]').replaceChildren();return;}
  const rows=select(d.rows,state),shown=rows;
  const oldGrid=root.querySelector('[data-rows]');const fresh=oldGrid.cloneNode(false);fresh.className='lhx-grid cand-grid';oldGrid.replaceWith(fresh);
  root.querySelector('[data-count]').textContent=rows.length+' player/category rows · '+new Set(rows.map(r=>r.id)).size+' players';root.querySelector('[data-page-note]').textContent=state.floor===''?'Individual auto floors':state.floor+'+ manual floor';root.querySelector('[data-floor-note]').textContent=state.floor===''?'Blank = each player’s highest qualifying easy preset.':state.category?'Same '+state.floor+'+ '+state.category.toLowerCase()+' floor for all shown players.':'Same number across all categories. Select one for consistent units.';

  const cards=shown.map((r,i)=>{const recent=r.games.filter(g=>!g.dnp).slice(0,10),initials=String(r.name).split(' ').map(x=>x[0]).slice(0,2).join(''),status=r.status&&r.status!=='No designation in snapshot'&&r.status!=='Active'?r.status:'';
   return h('article',{class:'lhx-card'},h('div',{class:'lhx-identity'},h('span',{class:'lhx-avatar','aria-hidden':'true'},initials),h('div',{},h('button',{type:'button',class:'lhx-name','data-detail':i},r.name),h('div',{class:'lhx-sub'},r.team+' · '+r.pos+' · '+(r.opp||'Opponent unavailable')))),h('div',{class:'lhx-floor'},r.floor+'+ ',h('span',{},r.category)),h('div',{class:'lhx-stats'},h('div',{},h('b',{},r.streak),h('small',{},'Straight clears')),h('div',{},h('b',{},(r.n?Math.round(100*r.hits/r.n):0)+'%'),h('small',{},'Season · '+r.hits+'/'+r.n+' known games'))),h('div',{class:'lhx-run',role:'img','aria-label':'Recent games newest first: '+recent.map(g=>g.label+' '+(g.value??'missing')+' '+result(g,r.floor)).join('; ')},recent.map(g=>h('span',{class:'lhx-dot '+(g.value==null?'unknown':g.value<r.floor?'miss':''),title:g.label+': '+(g.value??'Missing')+' · '+result(g,r.floor)}))),h('div',{class:'lhx-meta'},'Recent games · newest first'+(r.missing?' · '+r.missing+' missing totals':'')),status?h('div',{class:'lhx-status'},status+' · participation not confirmed'):null,h('div',{class:'lhx-history'},h('span',{class:'lhx-meta'},(r.time&&Date.parse(r.time)<Date.now()?'Start passed · ':'')+time(r.time)),h('button',{type:'button','data-history':i,'aria-label':'View '+r.name+' '+r.floor+'+ '+r.category+' history'},'View history →')));
  });root.querySelector('[data-rows]').replaceChildren(...(cards.length?cards:[h('div',{class:'lhx-empty'},h('h3',{},'No qualifying streaks'),h('p',{},'Try a lower floor, fewer consecutive games, or reset your filters.'))]));
  root.querySelectorAll('[data-detail],[data-history]').forEach(b=>b.onclick=()=>{if(canOpen(b))detail(shown[Number(b.dataset.detail??b.dataset.history)],b);});
 }
 root.querySelectorAll('[data-control]').forEach(el=>el.addEventListener('input',()=>{state[el.dataset.control]=el.dataset.control==='min'?Number(el.value):el.value;page=0;render();}));
 root.querySelector('[data-reset]').onclick=()=>{Object.assign(state,{category:'',pos:'',floor:'',min:5,sort:'streak'});page=0;root.querySelectorAll('[data-control]').forEach(el=>el.value=state[el.dataset.control]);render();};
 render();
};
})();
