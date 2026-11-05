/* Home Game Day card: rewrite the QB-out line with NFL Hub's own corrected status (season starter out, who starts, season-ending
   backups, reported trades). Text only; no play, price or grade is changed. Source: data/matchups.json "qb" notes. */
(function(){var Q={};fetch("data/matchups.json?v="+Math.floor(Date.now()/3e5)).then(function(r){return r.ok?r.json():null}).then(function(d){if(!d)return;
 (Object.values(d.cats||{})).forEach(function(c){Object.values(c||{}).forEach(function(L){(Array.isArray(L)?L:[]).forEach(function(r){if(r&&r.qb&&r.team&&!Q[r.team])Q[r.team]=r.qb})})});
 Object.keys(Q).forEach(function(t){Q[t]=Q[t].split(/(?<=\.)\s+(?=[A-Z])/).filter(function(s){return !/ is \d+-\d+| hasn't played/.test(s)}).join(" ")});fix()}).catch(function(){});
 var RE=/QB-out:\s*[^·\n]*?·\s*likely starter\s+[A-Z][\w'-]+(?:\s(?:[A-Z][\w'-]+|I{1,3}|IV|Jr\.|Sr\.)){1,2}/;
 function fix(){var nc=document.getElementById("nc");if(!nc||!Object.keys(Q).length)return;var w=document.createTreeWalker(nc,NodeFilter.SHOW_TEXT),n,hit=[];while(n=w.nextNode())if(RE.test(n.nodeValue))hit.push(n);
  hit.forEach(function(n){var m=/QB-out:\s*([A-Z][\w.'-]+(?:\s(?!Out\b|Doubtful\b|Questionable\b|Suspended\b|Injured\b)[A-Z][\w.'-]+)+)/.exec(n.nodeValue),nm=m&&m[1],t=null;   // team = the one whose note names the same QB
   Object.keys(Q).forEach(function(k){if(!t&&nm&&Q[k].indexOf(nm)>-1)t=k});if(t)n.nodeValue=n.nodeValue.replace(RE,Q[t].replace(/\.$/,""))})}
 new MutationObserver(function(){clearTimeout(fix._t);fix._t=setTimeout(fix,120)}).observe(document.documentElement,{childList:true,subtree:true});})();
