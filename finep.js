/* Fine print: long notes sit behind a collapsed "Learn more" toggle. Content is unchanged. */
(function(){
var CSS='.flm-a{position:relative;display:inline-block}.flm{background:none;border:0;padding:4px 0;cursor:pointer;color:inherit;text-decoration:none;font:inherit;font-size:14px;opacity:.7;min-width:28px;min-height:28px;line-height:1}.flm-w{position:absolute;left:0;top:100%;z-index:60;width:min(360px,calc(100vw - 24px));max-height:60vh;overflow:auto;background:var(--card,var(--bg,#111));color:inherit;border:1px solid var(--line,rgba(127,127,127,.35));border-radius:10px;padding:10px;box-shadow:0 8px 24px rgba(0,0,0,.35);text-align:left}';
var st=document.createElement('style');st.textContent=CSS;document.head.appendChild(st);
var openA=null;function shut(){if(openA){openA.w.hidden=true;openA.b.setAttribute('aria-expanded','false');openA=null}}
document.addEventListener('click',function(e){if(openA&&!openA.a.contains(e.target))shut()});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&openA){var b=openA.b;shut();b.focus()}});
var n=0;function tog(nodes){nodes=nodes.filter(function(x){return x&&!x.dataset.flm});if(!nodes.length)return;
 var a=document.createElement('span');a.className='flm-a';nodes[0].parentNode.insertBefore(a,nodes[0]);
 var b=document.createElement('button');b.type='button';b.className='mut sm flm';b.textContent='ⓘ';b.setAttribute('aria-label','More info');b.title='More info';
 var w=document.createElement('div');w.className='flm-w';w.hidden=true;w.id='flm'+(++n);w.setAttribute('role','tooltip');
 b.setAttribute('aria-expanded','false');b.setAttribute('aria-controls',w.id);
 nodes.forEach(function(x){x.dataset.flm=1;w.appendChild(x)});a.appendChild(b);a.appendChild(w);
 var o={a:a,b:b,w:w};function show(){if(openA&&openA!==o)shut();w.hidden=false;b.setAttribute('aria-expanded','true');openA=o;
  var r=a.getBoundingClientRect();w.style.left=Math.min(0,innerWidth-12-r.left-Math.min(360,innerWidth-24))+'px'}
 var hov=matchMedia('(hover:hover)').matches;
 if(hov){a.addEventListener('mouseenter',show);a.addEventListener('mouseleave',function(){if(openA===o&&!a.contains(document.activeElement))shut()})}
 b.addEventListener('click',function(e){e.stopPropagation();if(openA===o&&!hov)shut();else show()});
 a.addEventListener('focusout',function(e){if(!a.contains(e.relatedTarget)&&openA===o)shut()});
}
function run(){
 document.querySelectorAll('.eia-card').forEach(function(c){if(c.dataset.flmc)return;c.dataset.flmc=1;tog([].slice.call(c.children,4))});
 document.querySelectorAll('.ncm').forEach(function(n){if((n.innerText||'').length>140&&!n.closest('.eia-card'))tog([n])});
 document.querySelectorAll('.ncp').forEach(function(p){if(p.dataset.flmc)return;p.dataset.flmc=1;var k=[].slice.call(p.children).filter(function(x){return (x.innerText||'').length>90});if(k.length>1)tog(k.slice(1))});
 document.querySelectorAll('ul.sl').forEach(function(u){if(u.dataset.flmc)return;var li=[].slice.call(u.children);if(li.length<=3)return;u.dataset.flmc=1;
  var u2=document.createElement('ul');u2.className=u.className;li.slice(3).forEach(function(x){u2.appendChild(x)});u.parentNode.insertBefore(u2,u.nextSibling);tog([u2])});
}
var t;new MutationObserver(function(){clearTimeout(t);t=setTimeout(run,150)}).observe(document.documentElement,{childList:true,subtree:true});
document.addEventListener('DOMContentLoaded',run);run();
})();
