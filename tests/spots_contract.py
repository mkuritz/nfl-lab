import importlib.util, unittest, json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build_spots_preview.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
class Contracts(unittest.TestCase):
 def setUp(self):
  self.v=json.loads((ROOT/'data/v2.json').read_text());self.n=json.loads((ROOT/'data/nfl.json').read_text());self.dv=json.loads((ROOT/'data/nfl_dvp.json').read_text());self.now=b.stamp(self.v['updated'])+600;self.profiles={p.stem:json.loads(p.read_text()) for p in (ROOT/'data/players').glob('*.json') if p.stem.isdigit()}
 def build(self):return b.normalize(self.v,self.n,self.profiles,self.dv,self.now)
 def test_real_coverage_determinism(self):
  d=self.build();self.assertEqual(d,self.build());self.assertEqual(len(d['games']),14);self.assertGreater(len(d['rows']),450);self.assertGreater(len(d['roles']),150);self.assertEqual(len({r['key'] for r in d['rows']}),len(d['rows']));self.assertTrue(all(r['native'] for r in d['rows']));self.assertTrue(all(x['week']<d['week'] for r in d['rows'] for x in r['history']));self.assertTrue(all(g['time']>'2026-11-07' for g in d['games']));self.assertFalse(any('rz' in r for r in d['roles']))
 def test_future_stale_mixed_season(self):
  for offset in [-1,5401]:
   self.now=b.stamp(self.v['updated'])+offset
   with self.assertRaises(ValueError):self.build()
  self.now=b.stamp(self.v['updated'])+600;self.n['season']=2025
  with self.assertRaises(ValueError):self.build()
 def test_wrong_opponent_time_duplicate(self):
  r=next(x for x in self.v['rows'] if x['time']>'2026-11-07');r['oa']='ZZZ';d=self.build();self.assertFalse(any(x['id']==r['aid'] and x['market']==r['market'] for x in d['rows']))
  r['oa']=next(g for g in d['games'] if g['id']==r['game'])['away'];r['time']='bad';self.assertTrue(self.build())
  good=next(x for x in self.v['rows'] if x['time'].startswith('2026-11-08'));self.v['rows'].append(good.copy())
  with self.assertRaises(ValueError):self.build()
 def test_missing_not_zero_and_old_year_excluded(self):
  r=next(x for x in self.v['rows'] if x['time']>'2026-11-07');fields=b.FIELDS[r['market']]
  self.profiles[str(r['aid'])]['log']=[{'s':2026,'w':2,'t':r['team'],**{f:0 for f in fields}},{'s':2026,'w':3,'t':r['team']},{'s':2025,'w':18,'t':r['team'],**{f:500 for f in fields}}]
  d=self.build();h=next(x['history'] for x in d['rows'] if x['id']==r['aid'] and x['market']==r['market']);self.assertEqual(h,[{'week':2,'value':0,'opponent':''}])

 def test_model_flags_unchanged(self):
  for r in self.build()['rows']:
   source=next(x for x in self.v['rows'] if str(x['aid'])==r['id'] and str(x['game'])==r['game'] and x['market']==r['market']);self.assertEqual(r['highlighted'],source.get('hl') is True);self.assertEqual(r['estimate'],source['prob'])
if __name__=='__main__':unittest.main()
