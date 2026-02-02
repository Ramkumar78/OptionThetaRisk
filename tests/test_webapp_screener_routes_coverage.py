import pytest
from unittest.mock import patch, MagicMock

# --- Route Tests ---

def test_screener_status(client):
    """Test /api/screener/status"""
    with patch("webapp.blueprints.screener_routes.data_api_breaker") as mock_breaker:
        mock_breaker.current_state = "closed"
        resp = client.get("/api/screener/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["api_health"] == "closed"
        assert data["is_fallback"] is False

def test_run_backtest(client):
    """Test /backtest/run"""
    with patch("webapp.blueprints.screener_routes.UnifiedBacktester") as MockBT:
        instance = MockBT.return_value
        instance.run.return_value = {"trades": 5, "win_rate": 0.8}

        # Missing ticker
        resp = client.get("/backtest/run")
        assert resp.status_code == 400

        # Success
        resp = client.get("/backtest/run?ticker=AAPL&strategy=master")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["trades"] == 5

def test_screen_market(client):
    """Test POST /screen"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None):

        mock_screener.screen_market.return_value = [{"ticker": "AAPL", "score": 99}]
        mock_screener.screen_sectors.return_value = {"Tech": "Bullish"}

        resp = client.post("/screen", data={
            "iv_rank": "30",
            "rsi_threshold": "60",
            "time_frame": "1d",
            "region": "us"
        })

        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["results"]) == 1
        assert data["sector_results"]["Tech"] == "Bullish"

def test_screen_turtle(client):
    """Test /screen/turtle"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener:
        mock_screener.screen_turtle_setups.return_value = [{"ticker": "TURTLE", "verdict": "BUY"}]

        resp = client.get("/screen/turtle?region=us")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "TURTLE"

def test_check_isa_stock(client):
    """Test /screen/isa/check"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener:
        # Mock resolve_ticker
        mock_screener.resolve_ticker.side_effect = lambda x: x.upper()
        # Mock screen_trend_followers_isa
        mock_screener.screen_trend_followers_isa.return_value = [{
            "ticker": "AAPL",
            "price": 150.0,
            "signal": "ENTER",
            "trailing_exit_20d": 140.0
        }]

        # Missing ticker
        resp = client.get("/screen/isa/check")
        assert resp.status_code == 400

        # Valid ticker
        resp = client.get("/screen/isa/check?ticker=aapl&account_size=50000&entry_price=145")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ticker"] == "AAPL"
        assert "pnl_pct" in data
        assert "✅ HOLD" in data["signal"]

        # Not found
        mock_screener.screen_trend_followers_isa.return_value = []
        resp = client.get("/screen/isa/check?ticker=unknown")
        assert resp.status_code == 404

def test_screen_alpha101(client):
    """Test /screen/alpha101"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None):

        mock_screener.screen_alpha_101.return_value = [{"ticker": "ALPHA"}]

        resp = client.get("/screen/alpha101")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "ALPHA"

def test_screen_mystrategy(client):
    """Test /screen/mystrategy"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None):

        mock_screener.screen_my_strategy.return_value = [{"ticker": "MYSTRAT"}]

        resp = client.get("/screen/mystrategy")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "MYSTRAT"

def test_screen_fortress(client):
    """Test /screen/fortress"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None):

        mock_screener.screen_dynamic_volatility_fortress.return_value = [{"ticker": "FORT"}]

        resp = client.get("/screen/fortress")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "FORT"

def test_screen_options_only(client):
    """Test /screen/options_only"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None):

        mock_screener.screen_options_only_strategy.return_value = [{"ticker": "OPT"}]

        resp = client.get("/screen/options_only")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "OPT"

def test_screen_isa(client):
    """Test /screen/isa"""
    with patch("webapp.blueprints.screener_routes.resolve_region_tickers") as mock_resolve, \
         patch("webapp.blueprints.screener_routes.get_cached_market_data") as mock_data, \
         patch("webapp.blueprints.screener_routes.IsaStrategy") as MockStrategy, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None):

        mock_resolve.return_value = ["AAPL"]

        # Mock Data
        import pandas as pd
        mock_data.return_value = pd.DataFrame({"Close": [100, 101]}, index=[0, 1]) # Simple mock

        # Mock Strategy
        instance = MockStrategy.return_value
        instance.analyze.return_value = {"Signal": "ENTER", "ticker": "AAPL"}

        resp = client.get("/screen/isa?region=us")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["ticker"] == "AAPL"

def test_screen_bull_put(client):
    """Test /screen/bull_put"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.screen_bull_put_spreads.return_value = [{"ticker": "BULL"}]

        resp = client.get("/screen/bull_put")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "BULL"

def test_screen_vertical_put(client):
    """Test /screen/vertical_put"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None):

        mock_screener.screen_vertical_put_spreads.return_value = [{"ticker": "VERT"}]

        resp = client.get("/screen/vertical_put")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "VERT"

def test_screen_darvas(client):
    """Test /screen/darvas"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.screen_darvas_box.return_value = [{"ticker": "DARVAS"}]

        resp = client.get("/screen/darvas")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "DARVAS"

def test_screen_ema(client):
    """Test /screen/ema"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.screen_5_13_setups.return_value = [{"ticker": "EMA"}]

        resp = client.get("/screen/ema")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "EMA"

def test_screen_mms(client):
    """Test /screen/mms"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.screen_mms_ote_setups.return_value = [{"ticker": "MMS"}]

        resp = client.get("/screen/mms")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "MMS"

def test_screen_liquidity_grabs(client):
    """Test /screen/liquidity_grabs"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.screen_liquidity_grabs.return_value = [{"ticker": "LIQ"}]

        resp = client.get("/screen/liquidity_grabs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "LIQ"

def test_screen_squeeze(client):
    """Test /screen/squeeze"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.screen_bollinger_squeeze.return_value = [{"ticker": "SQ"}]

        resp = client.get("/screen/squeeze")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "SQ"

def test_screen_hybrid(client):
    """Test /screen/hybrid"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.screen_hybrid_strategy.return_value = [{"ticker": "HYB"}]

        resp = client.get("/screen/hybrid")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "HYB"

def test_screen_master(client):
    """Test /screen/master and /screen/quant"""
    with patch("webapp.blueprints.screener_routes.screen_master_convergence") as mock_screen, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None):

        mock_screen.return_value = [{"ticker": "MASTER"}]

        resp = client.get("/screen/master")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "MASTER"

        # Check Quant redirect
        resp = client.get("/screen/quant")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "MASTER"

def test_screen_fourier(client):
    """Test /screen/fourier"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.resolve_ticker.side_effect = lambda x: x.upper()
        mock_screener.screen_fourier_cycles.return_value = [{"ticker": "FOURIER"}]

        # General screen
        resp = client.get("/screen/fourier")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "FOURIER"

        # Single ticker
        resp = client.get("/screen/fourier?ticker=AAPL")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ticker"] == "FOURIER"

        # Not found single
        mock_screener.screen_fourier_cycles.return_value = []
        resp = client.get("/screen/fourier?ticker=UNKNOWN")
        assert resp.status_code == 404

def test_screen_rsi_divergence(client):
    """Test /screen/rsi_divergence"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.screen_rsi_divergence.return_value = [{"ticker": "RSI"}]

        resp = client.get("/screen/rsi_divergence")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "RSI"

def test_screen_universal(client):
    """Test /screen/universal"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None), \
         patch("webapp.blueprints.screener_routes.resolve_region_tickers", return_value=["AAPL"]):

        mock_screener.screen_universal_dashboard.return_value = {"results": [{"ticker": "UNI"}]}

        resp = client.get("/screen/universal")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["results"][0]["ticker"] == "UNI"

def test_screen_quantum(client):
    """Test /screen/quantum"""
    with patch("webapp.blueprints.screener_routes.screener") as mock_screener, \
         patch("webapp.blueprints.screener_routes.get_cached_screener_result", return_value=None):

        mock_screener.screen_quantum_setups.return_value = [{
            "ticker": "Q", "price": 100, "hurst": 0.6, "entropy": 0.1,
            "signal": "BUY", "score": 90, "company_name": "Q Corp",
            "kalman_diff": 0.5
        }]

        resp = client.get("/screen/quantum")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["ticker"] == "Q"
        assert data[0]["hurst"] == 0.6

def test_check_unified_stock(client):
    """Test /screen/check"""
    with patch("webapp.blueprints.screener_routes.handle_check_stock") as mock_handle, \
         patch("webapp.blueprints.screener_routes.resolve_ticker", side_effect=lambda x: x.upper()):

        mock_handle.return_value = {"ticker": "CHECK", "verdict": "BUY"}

        # Missing ticker
        resp = client.get("/screen/check")
        assert resp.status_code == 400

        # Valid
        resp = client.get("/screen/check?ticker=AAPL&strategy=isa")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ticker"] == "CHECK"

        # Not found
        mock_handle.return_value = None
        resp = client.get("/screen/check?ticker=UNKNOWN")
        assert resp.status_code == 404
