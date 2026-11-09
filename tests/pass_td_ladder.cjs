const {JSDOM}=require('jsdom');const fs=require('fs');const assert=require('node:assert/strict');
const path=require('path');
(async()=>{
 const dir=path.resolve(__dirname,'..');
 const d=JSON.parse(fs.readFileSync(dir+'/data/low_hurdles_alternates.json'));
 const dom=new JSDOM('<div id="root"></div>',{runScripts:'outside-only'});
 const w=dom.window;
 w.fetch=async()=>({ok:true,json:async()=>d});
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true};
 w.HTMLDialogElement.prototype.close=function(){this.dispatchEvent(new w.Event('close'))};
 w.SLGateState=()=>({paid:true,session:true});
 w.eval(fs.readFileSync(dir+'/alternate-hurdles.js','utf8'));
 const M=w.LowHurdlesMath;
 assert.equal(M.poissonTail(0,1),0);
 assert.ok(M.poissonTail(2.2,1)>0.85);
 assert.ok(M.poissonTail(2.2,2)>0.55);
 assert.ok(M.poissonTail(2.2,3)<0.55);
 // High-mean QB recommends 2+; streak of 5 at 2+ with all clears
 const highGames=[2,3,2,2,3,2,2,2,2,3].map(v=>({value:v}));
 const high={category:'Passing TDs',presets:[1,2,3],games:highGames,recommend:2,rungs:[{k:1,p:0.9,clears:true},{k:2,p:0.65,clears:true},{k:3,p:0.35,clears:false}]};
 assert.equal(M.recommendPassTdRung(high).recommend,2);
 assert.equal(M.defaultFloor(high,5),2);
 // Low-mean stays at 1+
 const low={category:'Passing TDs',presets:[1,2,3],games:[1,0,1,1,0,1,2,1,0,1].map(v=>({value:v}))};
 assert.equal(M.recommendPassTdRung(low).recommend,1);
 // Streak math unchanged for yards
 assert.equal(M.evaluate({games:[{value:10},{value:null},{value:10}]},5).streak,1);
 // Dataset contains Passing TDs + recommend field
 const ptd=d.rows.filter(r=>r.category==='Passing TDs');
 assert.ok(ptd.length>=20);
 assert.ok(ptd.some(r=>r.recommend===2));
 assert.ok(d.categories.includes('Passing TDs'));

 const root=w.document.querySelector('#root');
 await w.mountAlternateHurdles(root,'nfl');
 assert(root.querySelector('[data-results]'),'collapsible results present');
 const chips=[...root.querySelectorAll('[data-chips="category"] button')];
 const chip=chips.find(b=>/Pass TDs|Passing TDs/.test(b.textContent));
 assert(chip,'Passing TDs chip exists');
 chip.click();
 const chipAfter=[...root.querySelectorAll('[data-chips="category"] button')].find(b=>/Pass TDs|Passing TDs/.test(b.textContent));
 assert.equal(chipAfter.getAttribute('aria-pressed'),'true');
 const bar=root.querySelector('[data-rung-bar]');
 assert(bar && !bar.hidden,'rung bar visible for Passing TDs');
 assert.equal(bar.querySelectorAll('.lhx-rung').length,4,'Auto+1+2+3 pills');
 assert.ok(root.querySelectorAll('[data-card-rung]').length>=3,'per-card rung pills');
 const grade=root.querySelector('[data-results] .lhx-grade-body');
 assert(grade && /Week 9|Passing TD/.test(grade.textContent));
 console.log('PASS pass_td_ladder poisson/recommend/defaultFloor/rung-pills/results', 'ptd_rows',ptd.length);
 dom.window.close();
})().catch(e=>{console.error(e);process.exit(1)});
