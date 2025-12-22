import unittest
from option_auditor.screener import generate_human_verdict

class TestQuantumLogicNew(unittest.TestCase):

    def test_sniper_setup_buy(self):
        # H > 0.60, S < 1.5, Slope > 0
        verdict, rationale, score = generate_human_verdict(hurst=0.65, entropy=1.2, slope=1.0, price=100)
        self.assertEqual(verdict, "💎 STRONG BUY")
        self.assertEqual(score, 95)

    def test_sniper_setup_short(self):
        # H > 0.60, S < 1.5, Slope < 0
        verdict, rationale, score = generate_human_verdict(hurst=0.65, entropy=1.2, slope=-1.0, price=100)
        self.assertEqual(verdict, "💎 STRONG SHORT")
        self.assertEqual(score, 95)

    def test_mean_reversion(self):
        # H < 0.40
        verdict, rationale, score = generate_human_verdict(hurst=0.35, entropy=1.2, slope=1.0, price=100)
        self.assertEqual(verdict, "🔄 REVERSAL")
        self.assertEqual(score, 65)

    def test_casino_zone(self):
        # 0.45 <= H <= 0.55
        verdict, rationale, score = generate_human_verdict(hurst=0.50, entropy=1.2, slope=1.0, price=100)
        self.assertEqual(verdict, "NO TRADE") # Base verdict before refinement
        self.assertEqual(score, 10)

    def test_danger_zone(self):
        # H=0.58 (Weak Trend) and S=2.1 (Chaos) -> Danger.
        verdict, rationale, score = generate_human_verdict(hurst=0.58, entropy=2.1, slope=1.0, price=100)
        self.assertEqual(verdict, "💀 AVOID")
        self.assertEqual(score, 0)

    def test_weak_trend(self):
        # H=0.58, S=1.8 (Not Sniper, Not MR, Not Casino, Not Danger)
        verdict, rationale, score = generate_human_verdict(hurst=0.58, entropy=1.8, slope=1.0, price=100)
        self.assertEqual(verdict, "WEAK UP")
        self.assertEqual(score, 50)

if __name__ == '__main__':
    unittest.main()
