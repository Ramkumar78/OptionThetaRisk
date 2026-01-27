import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from option_auditor.unified_backtester import UnifiedBacktester

def test_backtester_liquidity_grab_bullish():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    df = pd.DataFrame(index=dates)

    df['Close'] = 100.0
    df['High'] = 105.0
    df['Low'] = 95.0
    df['Open'] = 100.0
    df['Volume'] = 1000000.0
    df['Spy'] = 100.0
    df['Vix'] = 15.0

    # Indicators
    df['sma50'] = 100.0
    df['sma200'] = 90.0
    df['sma150'] = 95.0
    df['sma20'] = 100.0
    df['atr'] = 2.0
    df['high_20'] = 110.0
    df['high_10'] = 105.0
    df['low_20'] = 90.0
    df['low_10'] = 95.0
    df['high_50'] = 115.0
    df['spy_sma200'] = 90.0
    df['ema5'] = 100.0
    df['ema13'] = 100.0
    df['ema21'] = 100.0
    df['rsi'] = 50.0
    df['alpha101'] = 0.0

    # Swing Low at 50 (Price 90)
    df.iloc[48, df.columns.get_loc('Low')] = 95.0
    df.iloc[49, df.columns.get_loc('Low')] = 90.0
    df.iloc[50, df.columns.get_loc('Low')] = 95.0

    # Trigger Bullish Sweep at 60
    # Entry ~92. Stop ~88 (92 - 0.5*ATR(2) -> wait, Logic: Low(89)-0.5*2 = 88).
    # Risk 4. Target 92 + 12 = 104.
    df.iloc[60, df.columns.get_loc('Low')] = 89.0
    df.iloc[60, df.columns.get_loc('Close')] = 92.0

    # Exit at 70 (Target Hit)
    df.iloc[70, df.columns.get_loc('High')] = 105.0
    df.iloc[70, df.columns.get_loc('Close')] = 105.0

    with patch.object(UnifiedBacktester, 'fetch_data', return_value=df):
        with patch.object(UnifiedBacktester, 'calculate_indicators', return_value=df):
            bt = UnifiedBacktester("TEST", strategy_type="liquidity_grab")
            result = bt.run()

            # Now we should have 1 closed trade
            assert result['trades'] == 1
            assert result['win_rate'] == "100%"

def test_backtester_rsi_bullish_div():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    df = pd.DataFrame(index=dates)

    df['Close'] = 100.0
    df['High'] = 105.0
    df['Low'] = 100.0
    df['Open'] = 100.0
    df['Volume'] = 1000.0
    df['Spy'] = 100.0
    df['Vix'] = 15.0

    df['sma50'] = 100.0
    df['sma200'] = 90.0
    df['spy_sma200'] = 90.0
    df['atr'] = 2.0
    df['rsi'] = 50.0
    df['high_50'] = 110.0 # dummy
    df['high_20'] = 110.0
    df['low_20'] = 90.0
    df['high_10'] = 110.0
    df['low_10'] = 90.0
    df['ema5'] = 100.0
    df['ema13'] = 100.0
    df['ema21'] = 100.0
    df['alpha101'] = 0.0

    # Shift swings to avoid warmup cut (first 27 + 20 = 47 indices skipped effectively?)
    # Index 50 is safe.

    # Swing Low 1 at 50: Low=95, RSI=30
    df.iloc[49, df.columns.get_loc('Low')] = 98.0
    df.iloc[50, df.columns.get_loc('Low')] = 95.0
    df.iloc[51, df.columns.get_loc('Low')] = 98.0
    df.iloc[50, df.columns.get_loc('rsi')] = 30.0

    # Swing Low 2 at 70: Low=94 (Lower), RSI=35 (Higher) -> Divergence
    df.iloc[69, df.columns.get_loc('Low')] = 96.0
    df.iloc[70, df.columns.get_loc('Low')] = 94.0
    df.iloc[71, df.columns.get_loc('Low')] = 96.0
    df.iloc[70, df.columns.get_loc('rsi')] = 35.0

    # Logic triggers at i=71 (Confirmation of Swing at 70)
    # Entry at 71. Close=100. Low=96.
    # Stop = Low - 1*ATR = 94? No, Logic uses `Low[i]` at entry?
    # Logic: `stop_loss = row['Low'] - (1.0 * atr)`.
    # At i=71, Low=96. Stop=94. Target=106.

    # Exit at 90
    df.iloc[90, df.columns.get_loc('High')] = 110.0
    df.iloc[90, df.columns.get_loc('Close')] = 110.0

    with patch.object(UnifiedBacktester, 'fetch_data', return_value=df):
        with patch.object(UnifiedBacktester, 'calculate_indicators', return_value=df):
            bt = UnifiedBacktester("TEST", strategy_type="rsi")
            result = bt.run()

            assert result['trades'] == 1
