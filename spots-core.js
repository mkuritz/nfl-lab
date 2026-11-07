/* Display-only contracts. No pick, estimator, pricer or Highlighted mutation. */
(function(root){'use strict';
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const seasonAt=now=>{const d=new Date(now);return d.getUTCFullYear()-(d.getUTCMonth()<2?1:0)};
function current(D,N,V,now=Date.now()){
 if(D?.schema!==1||D.max_age_minutes!==90||D.season!==seasonAt(now)||N?.season!==D.season||N.week!==D.week||V?.week!==D.week)return false;
 return [['games',N],['players',V]].every(([key,src])=>{const ts=Date.parse(src.updated);return Number.isFinite(ts)&&src.updated===D.source_updated[key]&&now-ts>=0&&now-ts<=D.max_age_minutes*60000});
}
function gameCurrent(g,N,now=Date.now()){const n=N.games?.find(x=>String(x.id)===g.id);return !!n&&n.state==='pre'&&n.date===g.time&&n.away?.abbr===g.away&&n.home?.abbr===g.home&&Date.parse(g.time)>now&&Date.parse(g.time)<now+7*86400000}
function lineStats(history,line){const a=history.filter(x=>finite(x.value));if(!finite(line))return {n:0,wins:0,pushes:0,losses:0,rate:null,mean:null};const wins=a.filter(x=>x.value>line).length,pushes=a.filter(x=>x.value===line).length,losses=a.length-wins-pushes;return {n:a.length,wins,pushes,losses,rate:wins+losses?wins/(wins+losses):null,mean:a.length?a.reduce((s,x)=>s+x.value,0)/a.length:null}}
function role(logs,metric){const valid=logs.filter(x=>finite(x[metric])).slice().sort((a,b)=>b.week-a.week);if(valid.length<6)return null;const last=valid.slice(0,3),prior=valid.slice(3,6),mean=a=>a.reduce((s,x)=>s+x[metric],0)/a.length;return {last:mean(last),prior:mean(prior),delta:mean(last)-mean(prior),latest_weeks:last.map(x=>x.week),prior_weeks:prior.map(x=>x.week),observations:valid.length}}
const implied=p=>finite(p)&&Math.abs(p)>=100?(p>0?100/(p+100):-p/(-p+100)):null;
root.SpotCore={finite,seasonAt,current,gameCurrent,lineStats,role,implied};
})(typeof window==='undefined'?globalThis:window);
