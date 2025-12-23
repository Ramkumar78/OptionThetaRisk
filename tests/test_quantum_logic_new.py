import unittest
from option_auditor.screener import generate_human_verdict

class TestQuantumLogicNew(unittest.TestCase):

    def test_sniper_setup_buy(self):
        # H > 0.55, S < 0.85 (Normalized), Slope > 0
        verdict, rationale = generate_human_verdict(hurst=0.65, entropy=0.5, slope=1.0, price=100)
        # 0.65 > 0.62 -> "🔥 Strong"
        self.assertIn("BUY (🔥 Strong)", verdict)

    def test_sniper_setup_short(self):
        # H > 0.55, S < 0.85, Slope < 0
        verdict, rationale = generate_human_verdict(hurst=0.65, entropy=0.5, slope=-1.0, price=100)
        self.assertIn("SHORT (🔥 Strong)", verdict)

    def test_mean_reversion(self):
        # H < 0.45
        verdict, rationale = generate_human_verdict(hurst=0.35, entropy=0.5, slope=1.0, price=100)
        self.assertEqual(verdict, "REVERSAL")

    def test_casino_zone(self):
        # 0.45 <= H <= 0.55 -> Neutral
        # Entropy should be decent to avoid "CHOP"
        verdict, rationale = generate_human_verdict(hurst=0.50, entropy=0.5, slope=1.0, price=100)
        self.assertEqual(verdict, "NEUTRAL")

    def test_danger_zone(self):
        # S > 0.9 -> CHOP (Normalized entropy threshold is 0.9)
        verdict, rationale = generate_human_verdict(hurst=0.58, entropy=0.95, slope=1.0, price=100)
        self.assertEqual(verdict, "CHOP")

    def test_weak_trend(self):
        # H=0.58, S=0.9 (Normalized).
        # H > 0.55 but Entropy > 0.85 -> fails trend check.
        # Entropy >= 0.9 -> CHOP. So 0.95 is CHOP.
        # If S=0.88? H=0.58.
        # Logic:
        # if H > 0.55 and S < 0.85: ...
        # elif H < 0.45: ...
        # elif S > 0.9: CHOP
        # else: NEUTRAL

        # Case 1: S = 0.88 (between 0.85 and 0.9) -> NEUTRAL
        verdict, rationale = generate_human_verdict(hurst=0.58, entropy=0.88, slope=1.0, price=100)
        self.assertEqual(verdict, "NEUTRAL")

if __name__ == '__main__':
    unittest.main()
