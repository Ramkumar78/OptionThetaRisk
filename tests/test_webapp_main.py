import pytest
import asyncio
import nest_asyncio
from unittest.mock import patch, MagicMock

# Apply nest_asyncio to allow nested event loops (fixes "Runner.run() cannot be called from a running event loop" in CI)
# IMPORTANT: We apply it globally but also ensure it's applied to the current loop in fixtures if needed.
nest_asyncio.apply()

@pytest.fixture(autouse=True)
def apply_nest_asyncio_fixture():
    nest_asyncio.apply()

# Attempt to import. If dependencies are missing (FastAPI), this will fail,
# but we know they are present in requirements.txt
try:
    from webapp.main import app, screen_isa, global_scan_cache, perform_heavy_market_scan
except ImportError:
    pytest.skip("webapp.main dependencies not available", allow_module_level=True)

@pytest.mark.asyncio
async def test_screen_isa_live():
    # Mock the heavy scan function logic
    # We patch perform_heavy_market_scan in the module or verify logic
    # Easier: Patch screen_trend_followers_isa inside webapp.main

    with patch('webapp.main.screen_trend_followers_isa') as mock_screener:
        mock_data = [{"ticker": "AAPL", "signal": "BUY"}]
        mock_screener.return_value = mock_data

        # Call the endpoint function directly
        result = await screen_isa(region="US")

        assert result["status"] == "success"
        assert result["source"] == "live"
        assert result["data"] == mock_data

        # Verify it was cached
        assert "US" in global_scan_cache
        assert global_scan_cache["US"] == mock_data

@pytest.mark.asyncio
async def test_screen_isa_cache():
    # Setup cache
    global_scan_cache["UK"] = [{"ticker": "BP", "signal": "SELL"}]

    with patch('webapp.main.screen_trend_followers_isa') as mock_screener:
        result = await screen_isa(region="UK")

        assert result["status"] == "success"
        assert result["source"] == "cache"
        assert result["data"][0]["ticker"] == "BP"

        # Should not have called screener
        mock_screener.assert_not_called()

def test_perform_heavy_market_scan():
    with patch('webapp.main.screen_trend_followers_isa') as mock_screener:
        mock_screener.return_value = "DATA"
        res = perform_heavy_market_scan("EU")
        assert res == "DATA"
        mock_screener.assert_called_with(region="EU")
