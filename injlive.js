/* NFL Hub injury overlay: fresh official injury report (re-checked every 15 min, and right after injury news), applied on top of
   published picks/notes as a label only. Logged picks are never changed, re-dated or removed here. */
(function(){if(window.NFLINJ)return;const U="https://sl-scheduler.kuritzmike.workers.dev/nfl/injuries";
const BAD=/^(Out|Injured Reserve|Doubtful|Suspension|Physically Unable|Non-Football)/i,Q=/^Questionable/i;
const st=document.createElement("style");st.textContent=".injb{display:inline-block;font:800 10.5px/1.4 system-ui,sans-serif;border-radius:5px;padding:1px 6px;margin-left:6px;vertical-align:1px;white-space:nowrap;background:#dc262633;color:#fca5a5;border:1px solid #f8717166}.injb.q{background:#facc1522;color:#fde68a;border-color:#facc1555}.injn{color:#fca5a5}";document.head.appendChild(st);
const H=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const et=t=>t?new Date(t).toLocaleString("en-US",{timeZone:"America/New_York",hour:"numeric",minute:"2-digit"})+" ET":"";
const lab=s=>/Injured Reserve/i.test(s)?"IR":s;
const I=window.NFLINJ={d:null,byId:{},byName:{},
 nm:s=>String(s||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/ (jr|sr|ii|iii|iv)\.?$/,"").replace(/[^a-z]/g,""),
 get(id,name){return (id&&I.byId[id])||(name&&I.byName[I.nm(name)])||null},
 bad:x=>x&&BAD.test(x.st||""),
 badge(x){if(!x)return"";if(BAD.test(x.st))return `<span class="injb" title="${H(x.c)}">⚠ ${H(lab(x.st))} · not expected to play</span>`;if(Q.test(x.st))return `<span class="injb q" title="${H(x.c)}">${H(x.st)}</span>`;return""},
 nextUp(t,pos,id){const D=((I.d||{}).depth||{})[t];if(!D)return[];const k=String(pos||"").toLowerCase().replace("k","pk").replace("ppk","pk");return (D.pos[k]||[]).filter(a=>a.id!=id&&!a.out).slice(0,2).map(a=>a.n)},
 // team note lines for a game card
 notes(t){const L=((I.d||{}).teams||{})[t]||[],sk=/^(QB|RB|WR|TE|K|PK|FB)$/;const o=L.filter(x=>sk.test(x.pos)&&BAD.test(x.st)&&Date.now()-new Date(x.d)<10*864e5);
  return o.slice(0,4).map(x=>{const nu=I.nextUp(t,x.pos,x.id);return `${H(x.n)} (${H(x.pos)}, ${H(lab(x.st))}, ${et(x.d)} ${new Date(x.d).toLocaleDateString("en-US",{timeZone:"America/New_York",month:"short",day:"numeric"})})${nu.length?` → next up: ${nu.map(H).join(", ")}`:""}`})},
 mark(root){(root||document).querySelectorAll("[data-fl]").forEach(el=>{let q;try{q=JSON.parse(el.dataset.fl)}catch(e){return}const x=I.get(q.a,q.n||q.p);const h=I.badge(x);
  let b=el.nextElementSibling&&el.nextElementSibling.classList.contains("fls")?el.nextElementSibling:el;let m=b.nextElementSibling;if(!(m&&m.classList.contains("injb"))){m=null}
  if(!h){if(m)m.remove();return}if(m&&m.outerHTML===h)return;if(m)m.remove();b.insertAdjacentHTML("afterend",h)})},
 async pull(){try{const r=await fetch(U+"?_="+Math.floor(Date.now()/60000));if(!r.ok)return;const d=await r.json();if(!d.teams)return;I.d=d;I.byId={};I.byName={};
  for(const[t,L]of Object.entries(d.teams))for(const x of L){x.t=t;if(x.id)I.byId[x.id]=x;I.byName[I.nm(x.n)]=x}
  I.mark();(I.cbs||[]).forEach(f=>{try{f(d)}catch(e){}})}catch(e){}},cbs:[],on(f){I.cbs.push(f);if(I.d)f(I.d)}};
I.pull();setInterval(I.pull,5*60e3);
new MutationObserver(()=>{if(I.d){clearTimeout(I._t);I._t=setTimeout(()=>I.mark(),80)}}).observe(document.documentElement,{childList:true,subtree:true});
})();
