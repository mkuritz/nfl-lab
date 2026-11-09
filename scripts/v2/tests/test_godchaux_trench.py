"""Unit tests for Nov 9, 2026 Davon Godchaux NO->JAX trench move + overlay IR wiring.
Run: python3 scripts/v2/tests/test_godchaux_trench.py
No publish; no network required for the pure-math cases.
"""
import os, sys, json, tempfile, unittest
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "v2"))


def _synth_sc():
    """Minimal play-by-play with D.Godchaux stuffs for NO and a JAX baseline."""
    rows = []
    # NO defensive run stuffs credited to Godchaux
    for i in range(2):
        rows.append(dict(
            defteam="NO", posteam="ATL", play_type="run", ispass=0, isrun=1,
            yards_gained=-1, epa=-0.9, sack=0, qb_hit=0,
            sack_player_name=None, qb_hit_1_player_name=None,
            solo_tackle_1_player_name="D.Godchaux",
            tackle_for_loss_1_player_name="D.Godchaux",
            sack_player_id=None, qb_hit_1_player_id=None,
            solo_tackle_1_player_id="00-GOD", tackle_for_loss_1_player_id="00-GOD",
        ))
    # JAX unrelated sack so team has DL volume
    rows.append(dict(
        defteam="JAX", posteam="IND", play_type="pass", ispass=1, isrun=0,
        yards_gained=-7, epa=-1.5, sack=1, qb_hit=1,
        sack_player_name="J.Hines-Allen", qb_hit_1_player_name="J.Hines-Allen",
        solo_tackle_1_player_name="J.Hines-Allen", tackle_for_loss_1_player_name=None,
        sack_player_id="00-JHA", qb_hit_1_player_id="00-JHA",
        solo_tackle_1_player_id="00-JHA", tackle_for_loss_1_player_id=None,
    ))
    # PHI J.Davis stays put (counterfactual guard)
    rows.append(dict(
        defteam="PHI", posteam="NYG", play_type="pass", ispass=1, isrun=0,
        yards_gained=-6, epa=-1.2, sack=1, qb_hit=1,
        sack_player_name="J.Davis", qb_hit_1_player_name="J.Davis",
        solo_tackle_1_player_name="J.Davis", tackle_for_loss_1_player_name=None,
        sack_player_id="00-JD", qb_hit_1_player_id="00-JD",
        solo_tackle_1_player_id="00-JD", tackle_for_loss_1_player_id=None,
    ))
    return pd.DataFrame(rows)


class GodchauxTrench(unittest.TestCase):
    def test_player_trench_move_math(self):
        """Moving Godchaux's contribution NO->JAX increases JAX dstuff and decreases NO."""
        sc = _synth_sc()
        cols = [c for c in sc.columns if c.endswith("_player_name") and any(k in c for k in ("sack", "qb_hit", "tackle"))]

        def player_trench(team, tag):
            g = sc[sc.defteam == team]
            has = lambda cs: g[cs].apply(lambda r: r.astype(str).str.fullmatch(tag).any(), axis=1)
            skm = has([c for c in cols if "sack" in c]) & (g.ispass == 1)
            qhm = has([c for c in cols if "qb_hit" in c]) & (g.ispass == 1)
            stm = has(cols) & (g.isrun == 1) & (g.yards_gained <= 0)
            return dict(dsk=int(skm.sum()), dqh=int(qhm.sum()), dstuff=int(stm.sum()),
                        dpepa=float(g[skm | qhm].epa.sum()), drepa=float(g[stm].epa.sum()))

        dg = player_trench("NO", "D.Godchaux")
        self.assertEqual(dg["dstuff"], 2)
        self.assertEqual(dg["dsk"], 0)
        A = {
            "NO": {"dsk": 5.0, "dqh": 10.0, "dstuff": 8.0, "dpepa": 1.0, "drepa": 2.0, "depa": 3.0},
            "JAX": {"dsk": 4.0, "dqh": 9.0, "dstuff": 6.0, "dpepa": 0.5, "drepa": -2.0, "depa": -1.0},
            "PHI": {"dsk": 3.0, "dqh": 5.0, "dstuff": 4.0, "dpepa": 2.0, "drepa": 1.0, "depa": 3.0},
        }
        before = {t: dict(v) for t, v in A.items()}
        for k in ("dsk", "dqh", "dstuff"):
            A["JAX"][k] += dg[k]
            A["NO"][k] = max(0, A["NO"][k] - dg[k])
        for k in ("dpepa", "drepa"):
            A["JAX"][k] += dg[k]
            A["NO"][k] -= dg[k]
            A["JAX"]["depa"] += dg[k]
            A["NO"]["depa"] -= dg[k]
        self.assertEqual(A["JAX"]["dstuff"], before["JAX"]["dstuff"] + 2)
        self.assertEqual(A["NO"]["dstuff"], before["NO"]["dstuff"] - 2)
        # PHI untouched (Jordan Davis did not trade)
        self.assertEqual(A["PHI"], before["PHI"])
        jd = player_trench("PHI", "J.Davis")
        self.assertEqual(jd["dsk"], 1)

    def test_trade_ov_ids(self):
        text = (ROOT / "scripts" / "profiles.py").read_text()
        self.assertIn('"3115383": "JAX"', text)  # Godchaux
        self.assertIn('"3919512": "JAX"', text)  # Bates
        self.assertIn('"2578570": "BAL"', text)  # Brissett
        # Davis must NOT be forced to JAX
        self.assertNotIn('"4381558": "JAX"', text)

    def test_analytics_has_godchaux_block(self):
        text = (ROOT / "scripts" / "v2" / "analytics.py").read_text()
        self.assertIn("D.Godchaux", text)
        self.assertIn("Davon Godchaux", text)
        self.assertIn("Jordan Davis remains PHI", text)
        self.assertIn("'from':'NO','to':'JAX'", text.replace(" ", ""))

    def test_hamilton_overlay(self):
        ov = json.loads((ROOT / "data" / "trench_overlay.json").read_text())
        ham = next(x for x in ov["players"] if x["name"] == "DaVon Hamilton")
        self.assertEqual(ham["team"], "JAX")
        self.assertEqual(ham["status"], "Injured Reserve")
        self.assertEqual(ham["espn_id"], "3915520")
        self.assertGreaterEqual(float(ham["cap_w"]), 1.0)

    def test_overlay_builds_espn_link(self):
        import trench_avail
        # Ensure the patched builder includes espn id href without calling network
        src = Path(trench_avail.__file__).read_text()
        self.assertIn("espn_id", src)
        self.assertIn("https://www.espn.com/nfl/player/_/id/", src)


if __name__ == "__main__":
    unittest.main()
