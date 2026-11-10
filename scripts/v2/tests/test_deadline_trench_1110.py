"""Nov 10, 2026 trade-deadline trench moves: DT Jordan Davis PHI->JAX (Nov 9), C Ryan Neuzil ATL->BAL for G Andrew Vorhees (Nov 10).
Run: python3 scripts/v2/tests/test_deadline_trench_1110.py   (no network)"""
import re, sys, unittest
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]
SRC = (ROOT / "scripts" / "v2" / "analytics.py").read_text()

def _load(name):
    """Pull a top-level helper out of analytics.py without running the build."""
    m = re.search(rf"^def {name}\(.*?(?=^\S)", SRC, re.S | re.M)
    ns = {"pd": pd}; exec(m.group(0), ns); return ns[name]

class DeadlineTrench(unittest.TestCase):
    def test_davis_matched_by_id_not_name(self):
        f = _load("_player_trench_id")
        sc = pd.DataFrame([
            dict(defteam="PHI", ispass=1, isrun=0, yards_gained=-6, epa=-1.2, sack_player_id="00-0037073", qb_hit_1_player_id="00-0037073", solo_tackle_1_player_id=None),
            dict(defteam="PHI", ispass=0, isrun=1, yards_gained=0, epa=-0.7, sack_player_id=None, qb_hit_1_player_id=None, solo_tackle_1_player_id="00-0037073"),
            # a different "J.Davis" on PHI must not count
            dict(defteam="PHI", ispass=1, isrun=0, yards_gained=-5, epa=-1.0, sack_player_id="00-OTHER", qb_hit_1_player_id="00-OTHER", solo_tackle_1_player_id=None),
        ])
        r = f(sc, "PHI", "00-0037073")
        self.assertEqual((r["dsk"], r["dqh"], r["dstuff"]), (1, 1, 1))
        self.assertAlmostEqual(r["dpepa"], -1.2); self.assertAlmostEqual(r["drepa"], -0.7)

    def test_ol_shift_is_symmetric_and_starter_gated(self):
        shift = _load("_ol_shift")
        a = dict(sk=20.0, qh=40.0, stuff=30.0, aly=500.0, repa=-10.0, rn=200)
        b = dict(a); shift(a, 0.10); shift(b, -0.10)
        self.assertGreater(a["sk"], 20.0); self.assertLess(b["sk"], 20.0)
        self.assertLess(a["aly"], 500.0); self.assertGreater(b["aly"], 500.0)
        self.assertAlmostEqual(a["repa"] + b["repa"], -20.0)
        self.assertIn("if sh>=0.4 else 0.0", SRC)

    def test_trades_and_notes_listed(self):
        t = SRC.replace(" ", "")
        self.assertIn("'player':'JordanDavis','pos':'DT','from':'PHI','to':'JAX'", t)
        self.assertIn("'player':'RyanNeuzil','pos':'C','from':'ATL','to':'BAL'", t)
        self.assertIn("('RyanNeuzil','ATL','BAL'),('AndrewVorhees','BAL','ATL')", t)
        self.assertNotIn("Jordan Davis remains PHI", SRC)

    def test_trade_ov(self):
        p = (ROOT / "scripts" / "profiles.py").read_text()
        for k, v in (("4381558", "JAX"), ("4036444", "BAL"), ("4243220", "ATL")): self.assertIn(f'"{k}": "{v}"', p)

if __name__ == "__main__":
    unittest.main()
