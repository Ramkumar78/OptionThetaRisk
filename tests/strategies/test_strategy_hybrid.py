import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np
from option_auditor.screener import screen_hybrid_strategy

@patch('option_auditor.strategies.hybrid.get_cached_market_data')
@patch('option_auditor.strategies.hybrid.fetch_batch_data_safe')
def test_screen_hybrid_perfect_buy(mock_fetch, mock_cache, mock_market_data):
    # Hybrid needs:
    # 1. ISA Trend (Close > SMA200) -> BULLISH
    # 2. Fourier Cycle (Bottom) -> BOTTOM
    # 3. Green Candle (Close > Open)
    # 4. No Panic Selling (Range < 2*ATR)
    # 5. Not Making Lower Lows (Close > Prev Low)

    df = mock_market_data(days=250, price=100.0, trend="up")

    # 1. Trend: Ensure > SMA200
    sma_200 = df['Close'].rolling(200).mean().iloc[-1]
    df.iloc[-1, df.columns.get_loc('Close')] = sma_200 + 10.0

    # 3. Green Candle
    df.iloc[-1, df.columns.get_loc('Open')] = sma_200 + 5.0

    # 4. Low Volatility (ATR)
    # Mock ATR to be 2.0
    # Range (High - Low) should be < 4.0
    df.iloc[-1, df.columns.get_loc('High')] = sma_200 + 11.0
    df.iloc[-1, df.columns.get_loc('Low')] = sma_200 + 9.0 # Range 2.0

    # 5. Higher Low
    prev_low = df['Low'].iloc[-2]
    df.iloc[-1, df.columns.get_loc('Close')] = max(df['Close'].iloc[-1], prev_low + 1.0)

    mock_fetch.return_value = df

    # Mock Cycle to Bottom (-0.8)
    with patch('option_auditor.strategies.hybrid.calculate_dominant_cycle', return_value=(20, -0.8)):
        results = screen_hybrid_strategy(ticker_list=["HYBRID"], check_mode=True)

        assert len(results) == 1
        assert "PERFECT BUY" in results[0]['verdict']
        assert results[0]['score'] >= 90

@patch('option_auditor.strategies.hybrid.fetch_batch_data_safe')
def test_screen_hybrid_perfect_short(mock_fetch, mock_market_data):
    # Bearish Trend + Cycle Top
    df = mock_market_data(days=250, price=100.0, trend="down")

    # Ensure < SMA200
    sma_200 = df['Close'].rolling(200).mean().iloc[-1]
    df.iloc[-1, df.columns.get_loc('Close')] = sma_200 - 10.0

    mock_fetch.return_value = df

    # Mock Cycle to Top (0.8)
    with patch('option_auditor.strategies.hybrid.calculate_dominant_cycle', return_value=(20, 0.8)):
        results = screen_hybrid_strategy(ticker_list=["SHORT"], check_mode=True)

        assert len(results) == 1
        assert "PERFECT SHORT" in results[0]['verdict']

@patch('option_auditor.strategies.hybrid.fetch_batch_data_safe')
def test_screen_hybrid_falling_knife(mock_fetch, mock_market_data):
    # Bullish Trend + Bottom + Lower Lows (Falling Knife)
    df = mock_market_data(days=250, price=100.0, trend="up")

    # Trend Bullish
    sma_200 = df['Close'].rolling(200).mean().iloc[-1]
    df.iloc[-1, df.columns.get_loc('Close')] = sma_200 + 10.0

    # Lower Low (Close < Prev Low)
    prev_low = df['Low'].iloc[-2]
    df.iloc[-1, df.columns.get_loc('Close')] = prev_low - 1.0

    mock_fetch.return_value = df

    with patch('option_auditor.strategies.hybrid.calculate_dominant_cycle', return_value=(20, -0.8)):
        results = screen_hybrid_strategy(ticker_list=["KNIFE"], check_mode=True)

        assert len(results) == 1
        assert "Falling Knife" in results[0]['verdict']
