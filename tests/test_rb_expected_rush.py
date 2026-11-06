import json, os, statistics, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

class TestRBExpected(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(DATA, "rb_expected_rush.json")) as f:
            cls.d = json.load(f)
        with open(os.path.join(DATA, "matchups.json")) as f:
            cls.m = json.load(f)

    def test_henry_whiteboard_math(self):
        h = self.d["players"]["3043078"]
        self.assertEqual(h["name"], "Derrick Henry")
        self.assertEqual(h["opp"], "JAX")
        self.assertIn("att ×", h["formula"]); self.assertTrue(abs(h["avg_att"] * h["opp_ypc"] - h["expected"]) < 0.15)
        # board Yds/car for JAX
        row = [r for r in self.m["cats"]["rush"]["best"] if r["aid"] == "3043078"][0]
        ypc = [c[1] for c in row["cols"] if c[0] == "Yds/car"][0]
        self.assertEqual(h["opp_ypc"], ypc)
        self.assertEqual(h["avg_att"], row["adv"]["car"][0])

    def test_rb_only(self):
        for p in self.d["players"].values():
            self.assertEqual(p["pos"], "RB")

    def test_coverage_present(self):
        self.assertGreater(self.d["coverage"]["shown"], 50)
        self.assertIn("hidden", self.d["coverage"])

if __name__ == "__main__":
    unittest.main()
