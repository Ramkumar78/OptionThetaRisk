import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

# Import the strategy (will be created later, but we mock it or import it if available)
# Since we are creating the test file first, we assume the import will work when we run it.
try:
    from option_auditor.strategies.quality_200w import Quality200wStrategy
except ImportError:
    pass

@pytest.fixture
def mock_yf_ticker():
    with patch('option_auditor.strategies.quality_200w.yf.Ticker') as mock:
        yield mock

def create_mock_df(days=2000, start_price=100, trend=1):
    dates = pd.date_range('2018-01-01', periods=days)
    prices = [start_price + (i * trend * 0.1) + (np.random.randn() * 2) for i in range(days)]
    df = pd.DataFrame({
        'Open': prices,
        'High': [p + 2 for p in prices],
        'Low': [p - 2 for p in prices],
        'Close': prices,
        'Volume': [1000000] * days
    }, index=dates)
    return df

class TestQuality200wStrategy:

    def test_analyze_insufficient_data(self):
        # Create small DF
        df = create_mock_df(days=100)
        strategy = Quality200wStrategy("AAPL", df)
        result = strategy.analyze()
        assert result is None

    def test_analyze_price_below_50sma(self):
        # Create DF where price < 50 SMA
        # We can force this by having a sharp drop at the end
        df = create_mock_df(days=2000, start_price=100, trend=0.05)
        # Drop last 10 days significantly
        last_price = df['Close'].iloc[-11]
        for i in range(10):
            df.iloc[-10+i, df.columns.get_loc('Close')] = last_price * 0.5 # Huge drop

        strategy = Quality200wStrategy("AAPL", df)
        result = strategy.analyze()
        assert result is None

    def test_analyze_price_above_200w_sma_limit(self):
        # Create DF where price is way above 200W SMA
        # Steady uptrend
        df = create_mock_df(days=2000, start_price=100, trend=0.1)
        # Ensure 200W SMA is well below price
        # At day 2000, price ~ 100 + 200 = 300.
        # SMA 200W (approx 1000 days avg) ~ 100 + 100 = 200.
        # Price 300 > 200 * 1.01. Should return None.

        strategy = Quality200wStrategy("AAPL", df)
        result = strategy.analyze()
        assert result is None

    def test_analyze_valid_buy_signal(self, mock_yf_ticker):
        # We need Price > 50 SMA AND Price <= 200W SMA * 1.01
        # This usually happens in a dip within a long-term downtrend or flat market?
        # Or uptrend where price dips to 200W SMA but stays above 50D SMA?
        # If Price > 50D SMA, then 50D SMA < Price.
        # If Price <= 200W SMA, then Price <= 200W SMA.
        # So 50D SMA < Price <= 200W SMA.
        # This implies 50D SMA < 200W SMA (Death Cross territory).
        # So we are looking for a recovery (Price > 50D) while still below 200W Long Term Resistance?
        # Or "Price trading below the 200-week SMA ... OR within 1% above".
        # Yes, it's a "Quality 200-Week MA" strategy, often meaning buying NEAR the 200W SMA.

        # Let's construct a scenario:
        # Long term flat/up.
        # Recent price is near 200W SMA.
        # And recent price popped above 50D SMA.

        df = create_mock_df(days=2000, start_price=100, trend=0.01) # Slow trend

        # Calculate expected SMA 200W roughly.
        # We can manually set the last prices to satisfy conditions.

        # 1. 200W SMA (approx 1000 days). Let's say it's 120.
        # 2. We set Close to 120 (at SMA).
        # 3. We need 50D SMA < 120. Let's say 115.
        # 4. We set last 50 days to avg 115, but last day is 120.

        # To make it easier, we mock the indicators or force values if possible?
        # No, strategy calculates them.
        # We can rely on the fact that if we have a flat line at 100, SMA 200W is 100. SMA 50D is 100.
        # Price is 100.
        # Price > 50D SMA (100 > 100 is False). We need Price > 50D SMA.
        # So Price 101, 50D SMA 100.
        # SMA 200W 100.
        # Price 101 <= 100 * 1.01 (101 <= 101). True.

        # Scenario:
        # History: 100 for 1950 days.
        # Last 50 days: Gradual rise to 101.

        dates = pd.date_range('2018-01-01', periods=2000)
        prices = [100.0] * 1950 + [100.0 + (i * 0.04) for i in range(50)] # Ends at 102.0 roughly? 50*0.04 = 2.0. 102.
        # Avg of last 50: (100+102)/2 = 101.
        # Price 102. 102 > 101. (Price > 50 SMA).
        # SMA 200W: Mostly 100.
        # 102 > 100 * 1.01 (101). 102 > 101. Fail.

        # Let's try simpler:
        # Price 100.5. SMA 50 ~ 100. SMA 200 ~ 100.
        # 100.5 > 100 (True).
        # 100.5 <= 101 (True).

        prices = [100.0] * 1950 + [100.0 + (i * 0.02) for i in range(50)] # Ends at 101.0
        # SMA 50 ~ 100.5. Price 101. Price > SMA 50.
        # SMA 200W ~ 100.
        # Price 101 <= 100 * 1.01 (101). True.

        df = pd.DataFrame({
            'Open': prices, 'High': prices, 'Low': prices, 'Close': prices, 'Volume': [1000000]*2000
        }, index=dates)

        # Mock Fundamentals
        mock_instance = mock_yf_ticker.return_value
        mock_instance.info = {'revenueGrowth': 0.10} # Positive growth
        mock_instance.financials = pd.DataFrame() # Empty to trigger fallback or skip

        strategy = Quality200wStrategy("AAPL", df)
        result = strategy.analyze()

        assert result is not None
        assert result['ticker'] == "AAPL"
        assert result['verdict'] == "BUY (Quality Dip)"

    def test_analyze_negative_revenue_growth(self, mock_yf_ticker):
        # Same setup as valid buy
        dates = pd.date_range('2018-01-01', periods=2000)
        prices = [100.0] * 1950 + [100.0 + (i * 0.02) for i in range(50)]
        df = pd.DataFrame({
            'Open': prices, 'High': prices, 'Low': prices, 'Close': prices, 'Volume': [1000000]*2000
        }, index=dates)

        # Mock Negative Fundamentals
        mock_instance = mock_yf_ticker.return_value
        mock_instance.info = {'revenueGrowth': -0.05}

        strategy = Quality200wStrategy("AAPL", df)
        result = strategy.analyze()
        assert result is None
