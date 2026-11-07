const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(require('node:path').join(__dirname,'../propintel.js'),'utf8');
const helper=source.slice(source.indexOf('var CTX=null;'),source.indexOf('var UNAVAILABLE='));
const context={D:null,Date,Intl};vm.createContext(context);vm.runInContext(helper,context);
const now=Date.parse('2026-11-06T23:00:00Z');
context.CTX={season:2026,week:9,updated:'2026-11-06T22:20Z',games:[{date:'2026-11-08T18:00Z',away:{abbr:'DET'},home:{abbr:'MIA'}}]};
context.D={week:'2026 Week 9',updated_et:'2026-11-06 05:00 PM ET'};
const p={gk:'DET@MIA'};
assert.equal(context.intelAvailable(p,now),true);
assert.equal(context.intelTime('Oct 26, 2026 9:00 PM ET'),Date.parse('2026-10-27T01:00Z'));
assert.equal(context.intelTime('2026-11-06 05:00 PM ET'),Date.parse('2026-11-06T22:00Z'));
for(const week of ['2026 Week 7','2025 Week 9','invalid']){context.D.week=week;assert.equal(context.intelAvailable(p,now),false);}
context.D.week='2026 Week 9';
for(const at of ['Oct 26, 2026 9:00 PM ET','invalid','2026-11-07T01:00:00Z']){context.D.updated_et=at;assert.equal(context.intelAvailable(p,now),false);}
context.D.updated_et='2026-11-06T22:00:00Z';assert.equal(context.intelAvailable({gk:'DAL@PHI'},now),false);
assert.equal(context.intelAvailable(p,now+73*36e5),false);
context.CTX=null;assert.equal(context.intelAvailable(p,now),false);
assert.ok(source.includes('Prop impact unavailable:'));console.log('propintel freshness checks passed');
