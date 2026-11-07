const {JSDOM}=require('jsdom');const fs=require('fs');const assert=require('node:assert/strict');
(async()=>{for(const sport of ['nfl']){
 const dir=require('path').resolve(__dirname,'..');const d=JSON.parse(fs.readFileSync(dir+'/data/low_hurdles_alternates.json'));
 const dom=new JSDOM('<div id="root"></div>',{runScripts:'outside-only'});const w=dom.window;w.fetch=async()=>({ok:true,json:async()=>d});w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.dispatchEvent(new w.Event('close'));};
 w.eval(fs.readFileSync(dir+'/alternate-hurdles.js','utf8'));await w.mountAlternateHurdles(w.document.querySelector('#root'),sport);
 let root=w.document.querySelector('#root');const input=(k,v)=>{let el=root.querySelector('[data-control="'+k+'"]');el.value=v;el.dispatchEvent(new w.Event('input'));};
 const count=()=>root.querySelectorAll('article').length;assert(count()>0);const initial=count();
 input('category',d.categories[0]);assert(count()<initial);input('pos',sport==='nba'?'G':'QB');input('sort','name');
 input('floor','99999');assert.equal(count(),0);assert.match(root.querySelector('[data-rows]').textContent,/No qualifying/);
 input('floor','-1');assert.match(root.querySelector('[data-count]').textContent,/positive/);
 root.querySelector('[data-reset]').click();assert.equal(count(),initial);assert.equal(root.querySelector('[data-control="floor"]').value,'');
 root.querySelector('[data-detail]').click();assert(w.document.querySelector('dialog'));assert.match(w.document.querySelector('dialog').textContent,/Threshold retained/);assert.match(w.document.querySelector('dialog').textContent,/Season:/);w.document.querySelector('[data-close]').click();assert(!w.document.querySelector('dialog'));
 root.querySelector('[data-detail]').click();let nativeId=null;w.NFLProfile=id=>nativeId=id;w.NBAHubProfiles={openPlayer:id=>nativeId=id};w.document.querySelector('[data-native]').click();assert(nativeId);assert(!w.document.querySelector('dialog'));
 const malicious={name:'<img src=x onerror=alert(1)>',pos:'QB',category:'Passing',presets:['<img>'],games:[{value:5}]};assert.throws(()=>w.LowHurdlesMath.select([malicious],{category:'',pos:'',floor:'',min:1,sort:'name'}));
 const {evaluate,select}=w.LowHurdlesMath;assert.equal(evaluate({games:[{value:9},{value:null},{value:10}]},5).streak,1);assert.equal(evaluate({games:[{value:9},{value:0},{value:10}]},5).streak,1);assert.equal(evaluate({games:[{value:9},{dnp:true},{value:10}]},5).streak,2);
 const rows=select(d.rows,{category:'',pos:'',floor:'',min:5,sort:'streak'});console.log(sport,'PASS controls/filter/sort/reset/empty/invalid/threshold-history/missing/zero/DNP',initial,JSON.stringify(Object.fromEntries(d.categories.map(c=>[c,rows.filter(r=>r.category===c).length]))));
 for(const cat of d.categories){let r=rows.find(r=>r.category===cat);if(r)console.log(cat,r.name,r.floor,r.streak,r.games.filter(g=>!g.dnp).slice(0,r.streak).map(g=>g.value).join(','));}
 // Missing file UI.
 w.fetch=async()=>({ok:false});const extra=w.document.createElement('div');await w.mountAlternateHurdles(extra,sport);assert.match(extra.textContent,/unavailable/);
 dom.window.close();
}})().catch(e=>{console.error(e);process.exit(1)});
