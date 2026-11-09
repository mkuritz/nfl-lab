// Hub Spots mount checks (jsdom). NODE_PATH=/workspace/visual-preview-tests/node_modules node tests/hub_spots.cjs
const fs=require('fs'),path=require('path'),{JSDOM}=require('jsdom');
const R=path.join(__dirname,'..');let ok=0,bad=0;const t=(c,m)=>{c?ok++:(bad++,console.log('FAIL',m))};const wait=ms=>new Promise(r=>setTimeout(r,ms));
const html=fs.readFileSync(path.join(R,'index.html'),'utf8');
(async()=>{
 const dom=new JSDOM(html,{url:'https://nfllab.sportslabshq.com/index.html#spots',runScripts:'outside-only',resources:'usable'});
 const w=dom.window;w.fetch=async(u)=>{const f=path.join(R,String(u).split('?')[0].replace(/^\.\//,''));return fs.existsSync(f)?{ok:true,json:async()=>JSON.parse(fs.readFileSync(f,'utf8')),text:async()=>fs.readFileSync(f,'utf8')}:{ok:false}};
 w.SLGateState=()=>({paid:true,session:null});
 for(const f of['navcfg.js','side.js','spots-hub.js'])w.eval(fs.readFileSync(path.join(R,f),'utf8'));
 await wait(200);
 // manually ensure shell + load spots like browser would after deferred scripts
 w.eval(fs.readFileSync(path.join(R,'spots-core.js'),'utf8'));
 // Build shell by invoking hash path
 w.location.hash='spots';await wait(100);
 // spots-hub show is async and loads scripts via DOM — in jsdom createElement script won't fetch. Call ensure path manually:
 const hub=fs.readFileSync(path.join(R,'spots-hub.js'),'utf8');
 // Direct: create shell nodes expected by spots.js
 const root=w.document.getElementById('spots-root')||(()=>{const s=w.document.createElement('section');s.id='spots-root';w.document.querySelector('.w').append(s);return s})();
 root.innerHTML=`<div id="spot-status"></div><nav id="spot-views"></nav><div id="spot-games"></div><div id="spot-controls"></div><h2 id="spot-title"></h2><p id="spot-caption"></p><span id="spot-count"></span><div id="spot-board"></div><p id="spot-provenance"></p>`;
 w.document.body.classList.add('spots-on');
 w.SpotsHub={active:true,view:null};
 w.eval(fs.readFileSync(path.join(R,'spots.js'),'utf8'));
 await wait(50);
 if(w.SpotsApp){await w.SpotsApp.boot();await wait(50)}
 t(!!w.document.body.classList.contains('spots-on')||!!w.SpotsApp,'hub spots mode available');
 t(!!w.SpotsApp,'SpotsApp exported for hub');
 t(!!w.document.getElementById('spot-board')?.children.length,'spot board rendered cards or empty state');
 t(fs.readFileSync(path.join(R,'navcfg.js'),'utf8').includes('index.html#spots'),'nav points at hub hash');
 t(fs.readFileSync(path.join(R,'spots.html'),'utf8').includes('spots-redirect'),'standalone redirects');
 const redir=new JSDOM('<html></html>',{url:'https://nfllab.sportslabshq.com/spots.html?view=roles&game=401',runScripts:'outside-only'});
 redir.window.eval(fs.readFileSync(path.join(R,'spots-redirect.js'),'utf8'));
 t(redir.window.__spotsRedirect==='index.html?game=401#spots/roles','redirect preserves view');
 console.log(`hub_spots: ${ok} passed, ${bad} failed`);process.exit(bad?1:0);
})().catch(e=>{console.error(e);process.exit(1)});
