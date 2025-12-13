import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from option_auditor.screener import (
    screen_trend_followers_isa, screen_fourier_cycles,
    _calculate_dominant_cycle, fetch_data_with_retry,
    screen_mms_ote_setups
)

# --- Helper to create synthetic data ---
def create_trend_data(periods=300, start_price=100, trend='up', volatility=1.0):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='D')
    prices = [start_price]
    for i in range(1, periods):
        change = np.random.normal(0, volatility)
        if trend == 'up': change += 0.5
        elif trend == 'down': change -= 0.5
        prices.append(prices[-1] + change)

    df = pd.DataFrame({
        'Open': prices,
        'High': [p + volatility for p in prices],
        'Low': [p - volatility for p in prices],
        'Close': prices,
        'Volume': [200000] * periods # Low volume initially
    }, index=dates)
    return df

def create_sine_wave_data(periods=200, cycle_period=20):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='D')
    x = np.arange(periods)
    # y = sin(2*pi*x/T)
    y = 100 + 10 * np.sin(2 * np.pi * x / cycle_period)

    df = pd.DataFrame({
        'Open': y, 'High': y+1, 'Low': y-1, 'Close': y, 'Volume': [1000000]*periods
    }, index=dates)
    return df

class TestScreenerImprovements:

    @patch('option_auditor.screener.yf.download')
    def test_isa_screener_logic(self, mock_download):
        """Test ISA screener for Trend, Breakout Date, and Tharp Verdict."""

        # 1. AAPL: Safe Buy
        # Flat 100 for 295 days. Jump to 150 for last 5 days.
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300, freq='D')

        # Base: 100
        closes = np.full(300, 100.0)
        # Last 5 days: 150
        closes[-5:] = 150.0

        df_aapl = pd.DataFrame({
            'Open': closes, 'High': closes + 2, 'Low': closes - 2, 'Close': closes,
            'Volume': [100000] * 300 # 100k * 150 = 15M > 5M
        }, index=dates)

        # SMA 200 = (195*100 + 5*150) / 200 = (19500 + 750)/200 = 101.25
        # Current = 150. > SMA. Bullish.
        # High 50 (Shifted) = Max(last 50 shift 1).
        # Days -1 to -5 are 150.
        # But shifted, at day 0 (today), High 50 looks at -1...-50.
        # It sees the 150s. So High 50 = 152.
        # Current = 150. Wait. 150 < 152.
        # But we want Breakout.
        # Breakout condition: Close >= High_50.
        # If we just jumped TODAY.
        # Let's make it jump TODAY.
        closes[-1] = 160.0
        df_aapl['Close'] = closes
        df_aapl['High'] = closes + 2
        df_aapl['Low'] = closes - 2
        # Now High_50 (shifted) sees max of previous 50 days (which were 100 or 150).
        # Wait, if days -2 to -6 were 150.
        # High_50 is 152.
        # Current 160 > 152. Breakout!

        # 2. MSFT: Risky
        # Flat 100.
        closes_msft = np.full(300, 100.0)
        df_msft = pd.DataFrame({
            'Open': closes_msft, 'High': closes_msft + 1, 'Low': closes_msft - 1, 'Close': closes_msft,
            'Volume': [100000] * 300
        }, index=dates)
        # Huge Volatility on last day to blow up ATR?
        # ATR is rolling 20. Need sustained volatility.
        # Let's just make High/Low wide for last 20 days.
        df_msft.iloc[-25:, df_msft.columns.get_loc('High')] = 200.0
        df_msft.iloc[-25:, df_msft.columns.get_loc('Low')] = 0.0
        # SMA 200 ~ 100. Close 100.
        # We need trend to be valid. Close > SMA 200.
        # Let's bump Close to 110. SMA ~ 100.
        df_msft['Close'] = 110.0

        # Mock Batch Return (MultiIndex)
        batch_df = pd.concat({'AAPL': df_aapl, 'MSFT': df_msft}, axis=1)
        mock_download.return_value = batch_df

        # Test 1: Standard Run with Batch (>1 tickers)
        results = screen_trend_followers_isa(['AAPL', 'MSFT'], risk_per_trade_pct=0.01)
        assert len(results) == 2

        # Check AAPL
        res_aapl = next(r for r in results if r['ticker'] == 'AAPL')
        # Should be ENTER or HOLD
        assert "ENTER" in res_aapl['signal'] or "HOLD" in res_aapl['signal']
        assert res_aapl['safe_to_trade'] is True

        # Check MSFT (Should be Risky)
        res_msft = next(r for r in results if r['ticker'] == 'MSFT')
        # ATR ~ 100 (High 200 - Low 0).
        # Stop = Close 110 - 3*100 = -190.
        # Risk = 110 - (-190) = 300.
        # Risk % = 300/110 = 270%.
        # Equity Risk = 4% * 2.7 = 10%. > 1%.
        assert "RISKY" in res_msft['tharp_verdict']
        assert not res_msft['safe_to_trade']

    @patch('option_auditor.screener.yf.download')
    def test_isa_liquidity_filter(self, mock_download):
        """Test that illiquid stocks are filtered out."""
        df = create_trend_data(periods=300)
        # Low volume: 100 * 100 = 10k < 5M
        df['Volume'] = 100

        # Batch with 2 tickers to trigger batch path
        mock_download.return_value = pd.concat({'PENNY': df, 'PENNY2': df}, axis=1)

        results = screen_trend_followers_isa(['PENNY', 'PENNY2'])
        assert len(results) == 0

    @patch('option_auditor.screener.fetch_data_with_retry')
    def test_isa_single_ticker_mode(self, mock_fetch):
        """Test the single ticker path (Check Stock)."""
        df = create_trend_data(periods=300)
        df['Volume'] = 1000000

        # Single ticker path returns simple DF
        mock_fetch.return_value = df

        results = screen_trend_followers_isa(['AAPL'])
        assert len(results) == 1
        assert results[0]['ticker'] == 'AAPL'

    @patch('option_auditor.screener.yf.download')
    def test_fourier_cycles(self, mock_download):
        """Test Fourier Transform Cycle Detection."""
        # Create a perfect sine wave with 20 day period
        df = create_sine_wave_data(periods=128, cycle_period=20)

        mock_download.return_value = pd.concat({'SINE': df}, axis=1)

        results = screen_fourier_cycles(['SINE'])

        assert len(results) == 1
        r = results[0]
        # Period should be close to 20
        period_str = r['cycle_period'].split()[0]
        period = float(period_str)
        assert 18 <= period <= 22

        # Check Signal based on phase
        # The data ends at t=199. 200/20 = 10 cycles exactly.
        # Sin(2*pi*whole_number) = 0.
        # If it's 0, it's Mid-Cycle.
        # Let's shift data to be at bottom (-1).
        # Sin(3pi/2) = -1.
        # 3/4 of a cycle. 20 * 0.75 = 15.

        df_low = create_sine_wave_data(periods=135, cycle_period=20)
        # 135 / 20 = 6.75. .75 * 2pi = 1.5pi -> -1 (Low).

        mock_download.return_value = pd.concat({'LOW': df_low}, axis=1)
        results = screen_fourier_cycles(['LOW'])
        assert "CYCLICAL LOW" in results[0]['signal']

    def test_calculate_dominant_cycle_short_data(self):
        """Test helper with insufficient data."""
        prices = [100] * 50 # < 64
        res = _calculate_dominant_cycle(prices)
        assert res is None

    @patch('option_auditor.screener.yf.download')
    @patch('option_auditor.screener.yf.Ticker')
    def test_mms_bullish_setup(self, mock_ticker, mock_download):
        """Test Bullish OTE Logic (Market Maker Buy Model)."""
        # Logic:
        # 1. Low (Turtle Soup)
        # 2. Rally (Displacement) > Pre-crash High (MSS)
        # 3. Pullback to 62-79% zone

        dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='1h')
        prices = [105.0] * 10
        prices.extend([104, 103, 102]) # Drop
        prices.append(100.0) # Low (Trough) at 100

        # Rally hard to 110
        prices.extend([102, 105, 108, 110]) # Peak at 110. Range = 10.

        # Retrace 70% (Price = 110 - 7 = 103)
        prices.extend([108, 106, 104, 103]) # Current close 103

        # Pad beginning
        pad = 50 - len(prices)
        final_prices = [105.0]*pad + prices

        df = pd.DataFrame({
            'Open': final_prices, 'High': [p+0.1 for p in final_prices],
            'Low': [p-0.1 for p in final_prices], 'Close': final_prices, 'Volume': 1000
        }, index=dates)

        # Set Ticker Mock
        instance = MagicMock()
        instance.history.return_value = df
        mock_ticker.return_value = instance

        results = screen_mms_ote_setups(['AAPL'], time_frame='1h')

        # Should detect Bullish OTE
        # We need to ensure MSS condition is met:
        # Peak 110 > Last pre-crash high.
        # Pre-crash prices were ~105. 110 > 105. Yes.

        # We assume threading works or is mocked.
        # screen_mms_ote_setups uses ThreadPoolExecutor.
        # If it runs, it should return result.

        assert len(results) == 1
        assert "BULLISH OTE" in results[0]['signal']

    @patch('option_auditor.screener.time.sleep')
    @patch('option_auditor.screener.yf.download')
    def test_fetch_data_retry(self, mock_download, mock_sleep):
        """Test retry logic."""
        # Fail twice, succeed third
        df_success = pd.DataFrame({'Close': [100]}, index=[pd.Timestamp.now()])

        mock_download.side_effect = [Exception("Fail 1"), Exception("Fail 2"), df_success]

        res = fetch_data_with_retry("AAPL", retries=3)
        assert not res.empty
        assert mock_download.call_count == 3
