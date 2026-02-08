import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pandas as pd
from option_auditor.models import calculate_regulatory_fees, calculate_commission
from option_auditor.currency_converter import CurrencyConverter

class TestRegulatoryFees:
    def test_us_stock_sell(self):
        # Sell 100 shares at $100. Value $10,000.
        # SEC: 10000 * 0.0000278 = 0.278
        # TAF: 100 * 0.000166 = 0.0166 (Cap 8.30)
        # Total: 0.2946
        fee = calculate_regulatory_fees("AAPL", 100.0, 100, action="SELL", asset_class="stock", multiplier=1.0)
        assert fee == pytest.approx(0.278 + 0.0166, abs=0.0001)

    def test_us_option_sell(self):
        # Sell 10 contracts at $5.00. Multiplier 100.
        # Value = 10 * 100 * 5 = 5000.
        # SEC: 5000 * 0.0000278 = 0.139
        # TAF: 10 (contracts) * 0.00244 = 0.0244
        # Total: 0.1634
        fee = calculate_regulatory_fees("AAPL", 5.0, 10, action="SELL", asset_class="option", multiplier=100.0)
        assert fee == pytest.approx(0.139 + 0.0244, abs=0.0001)

    def test_us_buy(self):
        fee = calculate_regulatory_fees("AAPL", 100.0, 100, action="BUY", asset_class="stock")
        assert fee == 0.0

    def test_taf_cap(self):
        # TAF Cap test
        # 1,000,000 shares. TAF = 166.0. Cap 8.30.
        # SEC on 1M * $10 = $10M * rate = 278.0
        fee = calculate_regulatory_fees("AAPL", 10.0, 1000000, action="SELL", asset_class="stock")
        sec_fee = 1000000 * 10 * 0.0000278 # 278.0
        taf_fee = 8.30
        assert fee == pytest.approx(sec_fee + taf_fee, abs=0.001)

    def test_india_regression(self):
        # 10 shares @ 1000. Value 10000. STT 0.1% = 10.
        fee = calculate_regulatory_fees("RELIANCE.NS", 1000.0, 10, action="BUY", asset_class="stock")
        assert fee == pytest.approx(10.0)

    def test_uk_regression(self):
        # 100 shares @ 100 (pence? or pounds?).
        # Usually UK quotes are in pence, but calculate_regulatory_fees assumes price is in base currency units for fee calc?
        # UK Stamp Duty is 0.5% of consideration.
        # If Price 100, Qty 100. Val 10000. Fee 50.
        fee = calculate_regulatory_fees("LLOY.L", 100.0, 100, action="BUY", asset_class="stock")
        assert fee == pytest.approx(50.0)

class TestCommissions:
    def test_fixed_stock(self):
        # Fixed US Stock: max(1.0, 100 * 0.005) = max(1.0, 0.5) = 1.0
        comm = calculate_commission(100, 150.0, "stock", "AAPL", "fixed")
        assert comm == 1.0

        # 1000 shares: 1000 * 0.005 = 5.0
        comm = calculate_commission(1000, 150.0, "stock", "AAPL", "fixed")
        assert comm == 5.0

    def test_tiered_stock(self):
        # Tiered US Stock:
        # 100 shares.
        # Base: 100 * 0.0035 = 0.35. Min 0.35. Correct.
        # Max: 100 * 150 * 0.01 = 150.
        # Result 0.35.
        comm = calculate_commission(100, 150.0, "stock", "AAPL", "tiered")
        assert comm == pytest.approx(0.35)

    def test_tiered_option(self):
        # Tiered US Option:
        # 10 contracts.
        # Rate 0.65.
        # Base: 10 * 0.65 = 6.50.
        # Min: 1.00.
        comm = calculate_commission(10, 5.0, "option", "AAPL", "tiered", multiplier=100.0)
        assert comm == 6.50

class TestCurrencyConverter:
    @patch('yfinance.Ticker')
    def test_convert(self, mock_ticker):
        # Setup mock
        mock_hist = MagicMock()
        # Create a DataFrame with a 'Close' column
        dates = pd.date_range(start='2023-01-01', periods=5, freq='D')
        data = {'Close': [1.2, 1.21, 1.22, 1.23, 1.24]}
        df = pd.DataFrame(data, index=dates)
        mock_hist.history.return_value = df
        mock_ticker.return_value = mock_hist

        converter = CurrencyConverter(base_currency='USD')

        # Test get_rate
        # Date match
        rate = converter.get_rate('GBP', 'USD', datetime(2023, 1, 2))
        assert rate == 1.21

        # Test convert
        amount = 100
        converted = converter.convert(amount, 'GBP', datetime(2023, 1, 2))
        assert converted == 121.0
