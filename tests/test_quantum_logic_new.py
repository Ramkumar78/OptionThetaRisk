import unittest
from option_auditor.screener import generate_human_verdict

class TestQuantumLogicNew(unittest.TestCase):

    def test_sniper_setup_buy(self):
        # New Strong threshold is > 0.72
        # Slope > 0.01 (1%)
        verdict, rationale = generate_human_verdict(hurst=0.75, entropy=0.5, slope=1.0, price=100)
        self.assertIn("BUY (🔥 Strong)", verdict)

    def test_sniper_setup_short(self):
        # New Strong threshold is > 0.72
        # Slope < -0.01 (-1%)
        verdict, rationale = generate_human_verdict(hurst=0.75, entropy=0.5, slope=-1.0, price=100)
        self.assertIn("SHORT (🔥 Strong)", verdict)

    def test_moderate_trend_buy(self):
        # Moderate: 0.65 < H <= 0.72
        verdict, rationale = generate_human_verdict(hurst=0.68, entropy=0.5, slope=1.0, price=100)
        self.assertIn("BUY (✅ Moderate)", verdict)

    def test_mean_reversion(self):
        # H < 0.45
        verdict, rationale = generate_human_verdict(hurst=0.35, entropy=0.5, slope=1.0, price=100)
        self.assertEqual(verdict, "REVERSAL")

    def test_casino_zone(self):
        # 0.45 <= H <= 0.65 -> Neutral/Random Walk
        # Entropy should be decent to avoid "CHOP"
        verdict, rationale = generate_human_verdict(hurst=0.50, entropy=0.5, slope=1.0, price=100)
        self.assertEqual(verdict, "NEUTRAL")

    def test_danger_zone(self):
        # S > 0.9 -> CHOP (Normalized entropy threshold is 0.9)
        verdict, rationale = generate_human_verdict(hurst=0.58, entropy=0.95, slope=1.0, price=100)
        self.assertEqual(verdict, "CHOP")

    def test_weak_trend_ignored(self):
        # H=0.62 is now considered "Weak/Ignored" (Random Walk Zone)
        # 0.60-0.65 = Weak Trend (Ignored)
        verdict, rationale = generate_human_verdict(hurst=0.62, entropy=0.5, slope=1.0, price=100)
        self.assertEqual(verdict, "NEUTRAL")

if __name__ == '__main__':
    unittest.main()
