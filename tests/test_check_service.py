import pytest
from unittest.mock import patch
from webapp.services.check_service import handle_check_stock

@pytest.fixture
def mock_screener():
    with patch('webapp.services.check_service.screener') as mock:
        yield mock

def test_handle_check_stock_isa_valid(mock_screener):
    mock_screener.screen_trend_followers_isa.return_value = [{
        "price": 150.0,
        "signal": "BUY",
        "trailing_exit_20d": 140.0
    }]

    res = handle_check_stock("AAPL", "isa", "1d", 10000, entry_price=100.0)

    assert res["user_verdict"] == "✅ HOLD (Trend Valid)"
    assert res["pnl_pct"] == 50.0

def test_handle_check_stock_isa_stop(mock_screener):
    mock_screener.screen_trend_followers_isa.return_value = [{
        "price": 130.0,
        "signal": "BUY",
        "trailing_exit_20d": 140.0
    }]

    res = handle_check_stock("AAPL", "isa", "1d", 10000, entry_price=100.0)

    assert "EXIT" in res["user_verdict"]
    assert "Below 20d Low" in res["user_verdict"]

def test_handle_check_stock_turtle_stop(mock_screener):
    mock_screener.screen_turtle_setups.return_value = [{
        "price": 90.0,
        "trailing_exit_10d": 95.0,
        "stop_loss": 85.0
    }]

    res = handle_check_stock("TSLA", "turtle", "1d", 10000, entry_price=100.0)

    assert "EXIT" in res["user_verdict"]
    assert "Below 10-Day Low" in res["user_verdict"]

def test_handle_check_stock_ema_bearish(mock_screener):
    mock_screener.screen_5_13_setups.return_value = [{
        "price": 100.0,
        "signal": "SELL"
    }]

    res = handle_check_stock("MSFT", "ema", "1d", 10000, entry_price=100.0)

    assert "EXIT" in res["user_verdict"]
    assert "Bearish Cross" in res["user_verdict"]

def test_handle_check_stock_master_confluence(mock_screener):
    mock_screener.screen_master_convergence.return_value = [{
        "price": 100.0,
        "confluence_score": 3
    }]

    res = handle_check_stock("NVDA", "master", "1d", 10000, entry_price=90.0)

    assert "STAY LONG" in res["user_verdict"]

def test_handle_check_stock_unknown_strategy():
    with pytest.raises(ValueError):
        handle_check_stock("AAPL", "unknown", "1d", 10000)

def test_handle_check_stock_no_results(mock_screener):
    mock_screener.screen_trend_followers_isa.return_value = []

    res = handle_check_stock("AAPL", "isa", "1d", 10000)

    assert res is None

def test_handle_check_stock_fourier(mock_screener):
    mock_screener.screen_fourier_cycles.return_value = [{
        "price": 100.0,
        "signal": "HIGH"
    }]

    res = handle_check_stock("AMD", "fourier", "1d", 10000, entry_price=90.0)

    assert "EXIT" in res["user_verdict"]
    assert "Cycle Peak" in res["user_verdict"]

def test_handle_check_stock_default_verdict(mock_screener):
    # Test fallback logic for unknown strategies or strategies without specific verdict logic
    mock_screener.screen_bull_put_spreads.return_value = [{
        "price": 100.0,
        "signal": "BUY"
    }]

    res = handle_check_stock("SPY", "bull_put", "1d", 10000, entry_price=90.0)
    # Checks fallthrough logic
    assert "HOLD" in res["user_verdict"]
    assert "Signal Active" in res["user_verdict"]

def test_handle_check_stock_darvas(mock_screener):
    mock_screener.screen_darvas_box.return_value = [{
        "price": 100.0,
        "signal": "BUY"
    }]
    res = handle_check_stock("SPY", "darvas", "1d", 10000, entry_price=90.0)
    assert res is not None

def test_handle_check_stock_hybrid(mock_screener):
    mock_screener.screen_hybrid_strategy.return_value = [{
        "price": 100.0,
        "signal": "BUY"
    }]
    res = handle_check_stock("SPY", "hybrid", "1d", 10000, entry_price=90.0)
    assert res is not None

def test_handle_check_stock_mms(mock_screener):
    mock_screener.screen_mms_ote_setups.return_value = [{
        "price": 100.0,
        "signal": "BUY"
    }]
    res = handle_check_stock("SPY", "mms", "1d", 10000, entry_price=90.0)
    assert res is not None

def test_handle_check_stock_5_13(mock_screener):
    mock_screener.screen_5_13_setups.return_value = [{
        "price": 100.0,
        "signal": "BUY"
    }]
    res = handle_check_stock("SPY", "5/13", "1d", 10000, entry_price=90.0)
    assert res is not None
