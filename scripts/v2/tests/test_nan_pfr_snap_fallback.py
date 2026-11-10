"""NaN pfr_id must not skip the name+team snap fallback (Alec Anderson case)."""
import math
import unittest

import pandas as pd


def id_ok(x):
    """Mirror trench_avail._id_ok — NaN must be missing, not truthy."""
    if x is None:
        return False
    try:
        if pd.isna(x):
            return False
    except Exception:
        pass
    return str(x).strip() not in ("", "nan", "None", "<NA>")


class NanPfrSnapFallback(unittest.TestCase):
    def test_nan_not_ok(self):
        self.assertFalse(id_ok(float("nan")))
        self.assertFalse(id_ok(math.nan))
        self.assertFalse(id_ok(None))
        self.assertFalse(id_ok(""))
        self.assertFalse(id_ok("nan"))
        self.assertTrue(id_ok("AndeAl01"))
        self.assertTrue(id_ok("DawkDi00"))

    def test_legacy_if_pid_would_skip_fallback(self):
        # Pre-fix gate: `g = sn[pfr==pid] if pid else name_fallback`
        # bool(nan) is True, so name fallback never ran and share stayed 0.
        pid = float("nan")
        self.assertTrue(bool(pid))  # the footgun
        self.assertFalse(id_ok(pid))

    def test_anderson_share_via_name_team(self):
        # Synthetic last-4 weeks matching Alec Anderson 2026 (~98% offense).
        sn = pd.DataFrame(
            {
                "pfr_player_id": [None, None, None, None],
                "player": ["Alec Anderson"] * 4,
                "team": ["BUF"] * 4,
                "week": [4, 5, 6, 8],
                "offense_pct": [1.0, 1.0, 1.0, 0.93],
            }
        )
        pid = float("nan")
        g = sn[sn.pfr_player_id == pid] if id_ok(pid) else sn.iloc[0:0]
        if len(g) == 0:
            g = sn[(sn.player == "Alec Anderson") & (sn.team == "BUF")]
        g = g.sort_values("week").tail(4)
        share = float(g.offense_pct.mean()) if len(g) else 0.0
        self.assertGreaterEqual(share, 0.4)
        self.assertAlmostEqual(share, 0.9825, places=4)
        # Starter loss weight at Out
        L = 1.0 * share / 5 * 0.5
        self.assertGreater(L, 0.09)


if __name__ == "__main__":
    unittest.main()
