import pytest
from option_auditor.screener import screen_market
from unittest.mock import patch, MagicMock
import pandas as pd
import sys

def test_screen_market_no_data():
    """Test screen_market when no data is returned."""
    with patch('yfinance.download') as mock_download:
        mock_download.return_value = pd.DataFrame()
        # We need pandas_ta installed or mocked for this to run past import
        with patch.dict(sys.modules, {'pandas_ta': MagicMock()}):
            results = screen_market()
            assert results == []

def test_screen_market_logic():
    """Test the screening logic with mocked data."""
    with patch('yfinance.download') as mock_download:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100)
        data = {
            'Close': [100.0] * 99 + [110.0]  # Price goes up
        }
        df = pd.DataFrame(data, index=dates)

        # Setup mocking correctly.
        # Since screen_market does 'import pandas_ta as ta', we must mock it in sys.modules.
        mock_ta = MagicMock()
        mock_ta.rsi.return_value = pd.Series([40.0] * 100, index=dates)
        mock_ta.sma.return_value = pd.Series([100.0] * 100, index=dates)

        with patch.dict(sys.modules, {'pandas_ta': mock_ta}):
            def side_effect(symbol, **kwargs):
                if symbol == "SPY":
                    return df.copy() # Return copy to avoid mutation issues if any
                return pd.DataFrame()

            mock_download.side_effect = side_effect

            results = screen_market(rsi_threshold=50)

            spy_result = next((r for r in results if r['ticker'] == 'SPY'), None)
            assert spy_result is not None
            assert spy_result['trend'] == 'BULLISH'
            assert spy_result['is_green'] is True
            assert "GREEN LIGHT" in spy_result['signal']

def test_screen_market_bearish():
    """Test that bearish trend yields WAIT signal."""
    with patch('yfinance.download') as mock_download:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100)
        data = {'Close': [100.0] * 100}
        df = pd.DataFrame(data, index=dates)

        mock_ta = MagicMock()
        mock_ta.rsi.return_value = pd.Series([40.0] * 100, index=dates)
        mock_ta.sma.return_value = pd.Series([110.0] * 100, index=dates)

        with patch.dict(sys.modules, {'pandas_ta': mock_ta}):
            def side_effect(symbol, **kwargs):
                if symbol == "SPY":
                    return df.copy()
                return pd.DataFrame()
            mock_download.side_effect = side_effect

            results = screen_market()
            spy_result = next((r for r in results if r['ticker'] == 'SPY'), None)

            assert spy_result is not None
            assert spy_result['trend'] == 'BEARISH'
            assert spy_result['is_green'] is False
            assert spy_result['signal'] == "WAIT"

def test_missing_pandas_ta():
    """Test that missing pandas_ta raises ImportError."""
    # To simulate missing package, we remove it from sys.modules and make import fail
    with patch.dict(sys.modules):
        if 'pandas_ta' in sys.modules:
            del sys.modules['pandas_ta']

        # We need to ensure __import__ fails for pandas_ta
        real_import = __import__
        def mock_import(name, *args, **kwargs):
            if name == 'pandas_ta':
                raise ImportError("No module named 'pandas_ta'")
            return real_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            with pytest.raises(ImportError, match="required for the screener"):
                screen_market()
