import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor.master_screener import MasterScreener

@pytest.fixture
def mock_yf_download():
    with patch('option_auditor.master_screener.yf.download') as mock:
        yield mock

@pytest.fixture
def screener():
    return MasterScreener(["AAPL"], ["BP.L"])

def create_mock_df(length=300, price=100.0, vol=2000000):
    """Helper to create a DataFrame with OHLCV data."""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='D')

    # Base price series
    prices = np.full(length, price)

    df = pd.DataFrame({
        'Open': prices,
        'High': prices * 1.01,
        'Low': prices * 0.99,
        'Close': prices,
        'Volume': np.full(length, vol)
    }, index=dates)

    return df

def test_initialization(screener):
    assert "AAPL" in screener.tickers_us
    assert "BP.L" in screener.tickers_uk
    assert screener.market_regime == "NEUTRAL"

def test_find_fresh_breakout(screener):
    # Create a scenario where price breaks out 5 days ago
    df = create_mock_df(length=100, price=100)

    # Make previous 20 days high = 105
    # So we need Close > 105 to breakout.

    # Days -25 to -6: Price = 100, High = 105
    # We need to ensure that the rolling max of High sees 105.
    df.iloc[-30:-6, df.columns.get_loc('High')] = 105.0
    df.iloc[-30:-6, df.columns.get_loc('Close')] = 100.0

    # Day -5: Price jumps to 106 (Breakout!)
    df.iloc[-5, df.columns.get_loc('Close')] = 106.0
    df.iloc[-5, df.columns.get_loc('High')] = 107.0
    # And volume must be > 1.2 * avg
    avg_vol = df.iloc[-30:-6]['Volume'].mean()
    df.iloc[-5, df.columns.get_loc('Volume')] = avg_vol * 1.5

    # Days -4 to -1: Sustains 106
    df.iloc[-4:, df.columns.get_loc('Close')] = 106.0
    df.iloc[-4:, df.columns.get_loc('Volume')] = avg_vol

    date_str, days_since, bo_price = screener._find_fresh_breakout(df)

    assert date_str is not None
    assert days_since == 4
    assert bo_price == 106.0

def test_process_stock_isa_buy(screener):
    # Requirements:
    # 1. Trend: Price > 50 > 150 > 200
    # 2. Fresh Breakout: within 12 days
    # 3. Not Extended: < 15% above 50 SMA

    df = create_mock_df(length=300, price=100, vol=2000000)

    # Construct prices to satisfy SMAs
    # SMA 200 (Last 200) < SMA 150 < SMA 50 < Price

    prices = np.zeros(300)
    prices[0:100] = 80
    prices[100:200] = 90
    prices[200:250] = 95
    prices[250:] = 100 # Avg 100
    prices[-1] = 105 # Jump at end

    df['Close'] = prices
    df['High'] = prices * 1.05
    df['Low'] = prices * 0.95
    df['Volume'] = 2000000

    with patch('option_auditor.master_screener.ta.atr') as mock_atr, \
         patch('option_auditor.master_screener.ta.rsi') as mock_rsi, \
         patch.object(screener, '_find_fresh_breakout') as mock_bo:

         # Mock Indicators
         mock_atr.return_value = pd.Series(np.full(300, 2.0), index=df.index)
         mock_rsi.return_value = pd.Series(np.full(300, 60.0), index=df.index)

         # Mock Breakout (Success)
         mock_bo.return_value = ("2023-01-01", 5, 105.0)

         result = screener._process_stock("AAPL", df)

         assert result is not None
         assert result['Type'] == "ISA_BUY"
         assert "Breakout" in result['Setup']

def test_process_stock_isa_fail_stale(screener):
    # Breakout was too long ago (though _find_fresh_breakout handles this, we can mock it returning None)
    df = create_mock_df(length=300, price=100, vol=2000000)

    prices = np.linspace(80, 110, 300)
    df['Close'] = prices
    df['High'] = prices * 1.05

    with patch('option_auditor.master_screener.ta.atr') as mock_atr, \
         patch('option_auditor.master_screener.ta.rsi') as mock_rsi, \
         patch.object(screener, '_find_fresh_breakout') as mock_bo:

         mock_atr.return_value = pd.Series(np.full(300, 2.0), index=df.index)
         mock_rsi.return_value = pd.Series(np.full(300, 50.0), index=df.index)

         # Mock Breakout (None because stale logic is inside _find_fresh_breakout)
         mock_bo.return_value = (None, None, None)

         # Ensure Options check fails too (RSI > 45)

         result = screener._process_stock("AAPL", df)
         assert result is None

def test_process_stock_options_setup(screener):
    # Requirements:
    # 1. US Stock
    # 2. Price > SMA 200
    # 3. RSI < 45
    # 4. ATR% > 2.5

    df = create_mock_df(length=300, price=100, vol=2000000)

    # Price > SMA 200
    prices = np.linspace(90, 110, 300) # SMA 200 ~ 100, Last = 110. OK.
    df['Close'] = prices

    with patch('option_auditor.master_screener.ta.atr') as mock_atr, \
         patch('option_auditor.master_screener.ta.rsi') as mock_rsi, \
         patch.object(screener, '_find_fresh_breakout') as mock_bo:

         # No breakout
         mock_bo.return_value = (None, None, None)

         # RSI < 45
         mock_rsi.return_value = pd.Series(np.full(300, 40.0), index=df.index)

         # ATR% > 2.5. Price 110. Need ATR > 2.75
         mock_atr.return_value = pd.Series(np.full(300, 3.5), index=df.index)

         result = screener._process_stock("AAPL", df)

         assert result is not None
         assert result['Type'] == "OPT_SELL"
         assert result['Setup'] == "Vol Pullback (Put Sell)"

def test_run_full_flow(screener, mock_yf_download):
    # Mock Market Regime (Bullish)
    dates = pd.date_range(periods=300, end="2023-01-01")
    regime_data = pd.DataFrame(index=dates)
    regime_data[('Close', 'SPY')] = np.linspace(300, 400, 300)
    regime_data[('Close', '^VIX')] = np.full(300, 15.0)
    regime_data.columns = pd.MultiIndex.from_tuples(regime_data.columns)

    # Mock Stock Data
    # 1. AAPL (Buy)
    # 2. BP.L (Fail)

    stock_df = create_mock_df(length=300, price=100)
    # Make AAPL a buy (reusing logic from process_stock test via patching if possible, or construct data)
    # Constructing data that passes SMA logic is annoying in integration test.
    # Let's rely on patching _process_stock to verify wiring.

    with patch.object(screener, '_process_stock') as mock_process:

        # Determine behavior based on ticker arg
        def process_side_effect(ticker, df):
            if ticker == "AAPL":
                return {"Ticker": "AAPL", "Type": "ISA_BUY", "volatility_pct": 2.0}
            return None

        mock_process.side_effect = process_side_effect

        # Mock download to return *something* that isn't empty so it iterates
        mock_yf_download.return_value = regime_data # Initially for regime

        # For the chunk loop, it calls download again.
        # We need side_effect on download.

        def download_side_effect(*args, **kwargs):
            tickers = args[0] if args else kwargs.get('tickers')
            if "SPY" in tickers:
                return regime_data

            # Stock data
            # Return MultiIndex DataFrame
            iterables = [['AAPL', 'BP.L'], ['Close', 'High', 'Low', 'Volume']]
            cols = pd.MultiIndex.from_product(iterables)
            df = pd.DataFrame(np.random.randn(300, 8), index=dates, columns=cols)
            return df

        mock_yf_download.side_effect = download_side_effect

        results = screener.run()

        assert len(results) == 1
        assert results[0]['Ticker'] == "AAPL"
