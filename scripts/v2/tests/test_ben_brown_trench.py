"""Ben Brown NE OL overlay upgrade tests (Nov 9 preview)."""
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "v2"))


class BenBrownTrench(unittest.TestCase):
    def test_overlay_has_brown_out(self):
        ov = json.loads((ROOT / "data" / "trench_overlay.json").read_text())
        brown = next(x for x in ov["players"] if x["name"] == "Ben Brown")
        self.assertEqual(brown["team"], "NE")
        self.assertEqual(brown["status"], "Out")
        self.assertEqual(brown["espn_id"], "4362890")
        self.assertGreaterEqual(float(brown["cap_w"]), 1.0)
        self.assertFalse(brown.get("unconfirmed", True))

    def test_avail_allows_upgrade(self):
        src = (ROOT / "scripts" / "v2" / "trench_avail.py").read_text()
        self.assertIn("upgrade_names", src)
        self.assertIn("allow overlay to UPGRADE", src)
        self.assertIn("ow > fw", src)

    def test_upgrade_math_doubtful_to_out(self):
        SW = {"Out": 1.0, "Injured Reserve": 1.0, "Doubtful": 0.75, "Questionable": 0.25}
        feed_w = SW["Doubtful"]
        overlay_w = min(SW["Out"], 1.0)
        self.assertGreater(overlay_w, feed_w)
        # OL loss scales with weight; Out vs Doubtful is 1.0/0.75 = +33% more OL hit
        share = 0.90
        L_d = feed_w * share / 5 * 0.5
        L_o = overlay_w * share / 5 * 0.5
        self.assertAlmostEqual(L_d, 0.0675, places=4)
        self.assertAlmostEqual(L_o, 0.09, places=4)
        self.assertGreater(L_o, L_d)


if __name__ == "__main__":
    unittest.main()
