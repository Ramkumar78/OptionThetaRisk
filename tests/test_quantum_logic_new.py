import unittest
from option_auditor.screener import generate_human_verdict

class TestQuantumLogicNew(unittest.TestCase):

    def test_sniper_setup_buy(self):
        # H > 0.55 (New threshold), S < 1.6, Slope > 0
        verdict, rationale = generate_human_verdict(hurst=0.65, entropy=1.2, slope=1.0, price=100)
        self.assertEqual(verdict, "💎 STRONG BUY")

    def test_sniper_setup_short(self):
        # H > 0.55, S < 1.6, Slope < 0
        verdict, rationale = generate_human_verdict(hurst=0.65, entropy=1.2, slope=-1.0, price=100)
        self.assertEqual(verdict, "💎 STRONG SHORT")

    def test_mean_reversion(self):
        # H < 0.40
        verdict, rationale = generate_human_verdict(hurst=0.35, entropy=1.2, slope=1.0, price=100)
        self.assertEqual(verdict, "🔄 REVERSAL WATCH")

    def test_casino_zone(self):
        # 0.40 <= H <= 0.55 -> Neutral
        verdict, rationale = generate_human_verdict(hurst=0.50, entropy=1.2, slope=1.0, price=100)
        self.assertEqual(verdict, "NEUTRAL / HOLD")

    def test_danger_zone(self):
        # S > 2.0 -> AVOID
        verdict, rationale = generate_human_verdict(hurst=0.58, entropy=2.1, slope=1.0, price=100)
        self.assertEqual(verdict, "💀 AVOID")

    def test_weak_trend(self):
        # H=0.58, S=1.8.
        # Old logic: WEAK UP.
        # New logic: H > 0.55 but S >= 1.6 -> condition fails -> Neutral.
        verdict, rationale = generate_human_verdict(hurst=0.58, entropy=1.8, slope=1.0, price=100)
        self.assertEqual(verdict, "NEUTRAL / HOLD")

if __name__ == '__main__':
    unittest.main()
