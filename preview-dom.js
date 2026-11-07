/* Safe preview primitives: never parse data as HTML. */
(function(){'use strict';
const NS='http://www.w3.org/2000/svg';
const HTML=new Set('div span p h1 h2 h3 h4 a button label input select option table thead tbody tr th td section header footer nav main dialog pre strong small details summary ul li br'.split(' '));
const SVG=new Set('svg g rect circle line path text title polyline'.split(' '));
const ATTR=new Set('id class role aria-label aria-current aria-modal tabindex type value min max step placeholder href viewBox x y x1 x2 y1 y2 cx cy r rx width height fill fill-opacity stroke stroke-width stroke-dasharray d points text-anchor preserveAspectRatio'.split(' '));
function node(tag,attrs,...children){
 if(!HTML.has(tag)&&!SVG.has(tag))throw Error('Disallowed element');
 const n=SVG.has(tag)?document.createElementNS(NS,tag):document.createElement(tag);
 for(const [key,val] of Object.entries(attrs||{})){
  if(key==='click'||key==='change'||key==='input'){if(typeof val==='function')n.addEventListener(key,val);continue}
  if(!ATTR.has(key))throw Error('Disallowed attribute '+key);
  if(val==null)continue;
  if(key==='href'){
   // Display adapters use known same-hub routes only. No data-driven protocols or hosts.
   const u=new URL(String(val),location.href);
   if(u.origin!==location.origin||!['http:','https:'].includes(u.protocol))throw Error('Unsafe link');
  }
  n.setAttribute(key,String(val));
 }
 for(const c of children.flat(Infinity))if(c!==null&&c!==undefined)n.append(c instanceof Node?c:document.createTextNode(String(c)));
 return n;
}
const text=(s,cls='mut')=>node('p',{class:cls},s);
const card=(title,...body)=>node('section',{class:'pv-card'},title?node('h2',{},title):null,...body);
const num=(v,d=2)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(d):'—';
const pc=v=>typeof v==='number'&&Number.isFinite(v)?num(v*100,1)+'%':'Unavailable';
const table=(labels,rows)=>node('details',{class:'pv-data'},node('summary',{},'View data · '+rows.length+' rows'),node('div',{class:'pv-scroll'},node('table',{},node('thead',{},node('tr',{},labels.map(l=>node('th',{},l)))),node('tbody',{},rows.map(r=>node('tr',{},r.map(c=>node('td',{},c))))))));
const select=(label,options,value,fn)=>{const s=node('select',{'aria-label':label},options.map(([id,name])=>node('option',{value:id},name)));if(value!=null)s.value=String(value);s.addEventListener('change',()=>fn(s.value));return node('label',{class:'pv-control'},node('span',{},label),s)};
function dialog(title,...body){
 const previous=document.activeElement,d=node('dialog',{'aria-label':title},node('div',{class:'pv-dialog-body'},node('button',{'aria-label':'Close profile',click:()=>d.close()},'Close ×'),node('h2',{},title),...body));
 document.body.append(d);d.addEventListener('close',()=>{d.remove();previous?.focus()},{once:true});
 d.addEventListener('click',e=>{if(e.target===d)d.close()});d.showModal();return d;
}
function chart(label,w=640,h=280){return node('svg',{viewBox:`0 0 ${w} ${h}`,role:'img','aria-label':label,class:'pv-chart'})}
function bars(labels,values,colors=['#7de4c3']){
 const vals=values.map(x=>typeof x==='number'&&Number.isFinite(x)?x:0),lo=Math.min(0,...vals),hi=Math.max(1,...vals),X=v=>165+(v-lo)/(hi-lo)*370,zero=X(0);
 const s=chart('Bar chart: '+labels.join(', '),640,Math.max(120,labels.length*34));
 labels.forEach((l,i)=>{const v=vals[i];s.append(node('text',{x:8,y:i*34+22,fill:'#b4cdc8'},l),node('rect',{x:Math.min(zero,X(v)),y:i*34+9,width:Math.abs(X(v)-zero),height:20,rx:4,fill:colors[i%colors.length]},node('title',{},String(l)+' · '+num(values[i]))),node('text',{x:555,y:i*34+23,fill:'#e7f7f2'},num(values[i])))});
 s.append(node('line',{x1:zero,x2:zero,y1:0,y2:Math.max(120,labels.length*34),stroke:'#a4bfb6'}));return s;
}
function meter(label,v,note,color='#7de4c3'){
 const s=chart(label,360,56);s.append(node('rect',{x:0,y:20,width:280,height:9,rx:4,fill:'#173d36'}));
 if(typeof v==='number'&&Number.isFinite(v))s.append(node('rect',{x:0,y:20,width:Math.max(0,Math.min(1,v))*280,height:9,rx:4,fill:color}));
 s.append(node('text',{x:0,y:13,fill:'#b4cdc8'},label),node('text',{x:288,y:29,fill:'#e7f7f2'},pc(v)));
 return node('div',{class:'pv-meter'},s,text(note,'mut sm'));
}
function pitch(){const s=chart('Soccer pitch; attacking left to right',600,400);s.classList.add('pv-pitch');
 s.append(node('rect',{x:0,y:0,width:600,height:400,fill:'#0b342b'}),node('rect',{x:5,y:5,width:590,height:390,stroke:'#7ac0ad',fill:'none','stroke-width':1}),node('line',{x1:300,x2:300,y1:5,y2:395,stroke:'#7ac0ad'}),node('circle',{cx:300,cy:200,r:46,stroke:'#7ac0ad',fill:'none'}));
 for(const x of [5,512.5])s.append(node('rect',{x,y:90,width:82.5,height:220,fill:'none',stroke:'#7ac0ad'}));
 for(const x of [5,567.5])s.append(node('rect',{x,y:150,width:27.5,height:100,fill:'none',stroke:'#7ac0ad'}));return s;
}
// Closed request capability: only these literal local files; redirects and cross-origin requests fail.
const DATA_READERS=Object.freeze({
'data/pindex.json':()=>fetch('data/pindex.json',{mode:'same-origin',credentials:'same-origin',redirect:'error'}),
'data/v2.json':()=>fetch('data/v2.json',{mode:'same-origin',credentials:'same-origin',redirect:'error'}),
'data/unit_board.json':()=>fetch('data/unit_board.json',{mode:'same-origin',credentials:'same-origin',redirect:'error'}),
'data/opportunity_history.json':()=>fetch('data/opportunity_history.json',{mode:'same-origin',credentials:'same-origin',redirect:'error'})
});
async function json(path){
 if(!Object.hasOwn(DATA_READERS,path))throw Error('Unsupported display data file');
 const r=await DATA_READERS[path]();if(!r.ok)throw Error(path+' unavailable ('+r.status+')');return r.json();
}
function metrics(items){return node('div',{class:'pv-kpis'},items.map(([label,value])=>node('div',{class:'pv-kpi'},node('small',{},label),node('strong',{},value))))}
function controls(...items){const root=document.getElementById('preview-controls'),reset=node('button',{type:'button',class:'pv-reset',click:()=>{document.dispatchEvent(new Event('pv-reset'));root.querySelector('.pv-reset')?.focus()}},'Reset filters');root.replaceChildren(...items,reset)}
function status(summary,detail){const root=document.getElementById('preview-status');root.textContent=summary;root.nextElementSibling?.classList.contains('pv-provenance')&&root.nextElementSibling.remove();root.insertAdjacentElement('afterend',node('details',{class:'pv-provenance'},node('summary',{},'Snapshot & coverage'),text(detail,'mut sm')))}
function nav(){
 const cur=location.pathname.split('/').pop().replace('.html',''),groups=window.SLTOP?.by||(window.SLNAV?.groups||[]).flatMap(x=>x[1]);
 const visible=groups.filter(x=>!/^https?:/.test(x[1])),views=new Set(['unit-board.html', 'injury-cascade.html']),primary=visible.filter(x=>views.has(x[1].replace(/^\.\//,'').split('?')[0])),other=visible.filter(x=>!views.has(x[1].replace(/^\.\//,'').split('?')[0])&&!/^\.?\/index.html$|^index.html$/.test(x[1]));
 const link=([label,href,key])=>node('a',{href,'aria-current':key===cur?'page':null},label);
 document.getElementById('preview-nav').replaceChildren(node('div',{class:'pv-nav-primary'},link(['Hub home','index.html','index']),primary.map(link)),node('details',{class:'pv-more'},node('summary',{},'More Hub tools'),node('div',{class:'pv-morelinks'},other.map(link))));
}

window.PV={node,text,card,num,pc,table,select,dialog,chart,bars,meter,pitch,json,nav,metrics,controls,status};
})();
