import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from option_auditor.main_analyzer import _calculate_drawdown, _calculate_portfolio_curve, _detect_broker, _normalize_ticker, _fetch_live_prices, _check_itm_risk, refresh_dashboard_data, analyze_csv
from option_auditor.models import TradeGroup, Leg, StrategyGroup

# --- Fixtures ---

@pytest.fixture
def sample_strategies():
    s1 = MagicMock(spec=StrategyGroup)
    s1.exit_ts = pd.Timestamp("2023-01-01")
    s1.net_pnl = 100.0
    s1.symbol = "AAPL"
    s1.strategy_name = "Long Call"

    s2 = MagicMock(spec=StrategyGroup)
    s2.exit_ts = pd.Timestamp("2023-01-02")
    s2.net_pnl = -50.0 # Drawdown starts
    s2.symbol = "MSFT"
    s2.strategy_name = "Short Put"

    s3 = MagicMock(spec=StrategyGroup)
    s3.exit_ts = pd.Timestamp("2023-01-03")
    s3.net_pnl = -20.0 # Deepens drawdown
    s3.symbol = "TSLA"
    s3.strategy_name = "Iron Condor"

    return [s1, s2, s3]

# --- Calculation Tests ---

def test_calculate_drawdown(sample_strategies):
    # PnL: +100 (Peak 100), -50 (Cum 50, DD 50), -20 (Cum 30, DD 70)
    dd = _calculate_drawdown(sample_strategies)
    assert dd == 70.0

def test_calculate_drawdown_empty():
    assert _calculate_drawdown([]) == 0.0

def test_calculate_portfolio_curve(sample_strategies):
    curve = _calculate_portfolio_curve(sample_strategies)
    assert len(curve) == 4 # Initial point + 3 trades
    assert curve[-1]['y'] == 30.0

def test_calculate_portfolio_curve_empty():
    assert _calculate_portfolio_curve([]) == []

# --- Helper Tests ---

def test_detect_broker():
    df = pd.DataFrame(columns=["Underlying Symbol"])
    assert _detect_broker(df) == "tasty"

    df = pd.DataFrame(columns=["Description", "Symbol"])
    assert _detect_broker(df) == "tasty"

    df = pd.DataFrame(columns=["ClientAccountID"])
    assert _detect_broker(df) == "ibkr"

    df = pd.DataFrame(columns=["Comm/Fee", "T. Price"])
    assert _detect_broker(df) == "ibkr"

    df = pd.DataFrame(columns=["Random"])
    assert _detect_broker(df) is None

def test_normalize_ticker():
    assert _normalize_ticker("SPX") == "^SPX"
    assert _normalize_ticker("/ES") == "ES=F"
    assert _normalize_ticker("BRK/B") == "BRK-B"
    assert _normalize_ticker("AAPL") == "AAPL"
    assert _normalize_ticker(123) == "123"

def test_fetch_live_prices_batch():
    with patch("yfinance.download") as mock_dl:
        # Mock batch return
        # Correct format: (Ticker, "Close") or (Level0=Ticker, Level1=PriceType)
        # The code expects: if sym in df.columns.levels[0] -> Ticker is Level 0
        mock_dl.return_value = pd.DataFrame(
            {("AAPL", "Close"): [150.0], ("MSFT", "Close"): [300.0]},
            index=[pd.Timestamp.now()]
        )
        mock_dl.return_value.columns = pd.MultiIndex.from_tuples([("AAPL", "Close"), ("MSFT", "Close")])

        # Patch Fallback Ticker as well to prevent real network call if logic fails
        with patch("yfinance.Ticker"):
            prices = _fetch_live_prices(["AAPL", "MSFT"])
            assert prices.get("AAPL") == 150.0
            assert prices.get("MSFT") == 300.0

def test_fetch_live_prices_single():
    with patch("yfinance.download") as mock_dl:
        # Case 2: Single ticker (Single Index)
        mock_dl.return_value = pd.DataFrame({"Close": [150.0]})
        prices = _fetch_live_prices(["AAPL"])
        assert prices.get("AAPL") == 150.0

def test_fetch_live_prices_fallback():
    with patch("yfinance.download") as mock_dl:
        # Batch fails or empty
        mock_dl.side_effect = Exception("Batch failed")

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.fast_info = {"last_price": 150.0}
            prices = _fetch_live_prices(["AAPL"])
            assert prices.get("AAPL") == 150.0

# --- Risk Logic Tests ---

def test_check_itm_risk():
    # Setup risky position: Short Put ITM
    g = TradeGroup(contract_id="P1", symbol="AAPL", expiry=pd.Timestamp.now(), strike=150, right="P")
    g.add_leg(Leg(ts=pd.Timestamp.now(), qty=-10, price=0, fees=0, proceeds=0)) # -10 Short Puts

    prices = {"AAPL": 100.0} # Put Strike 150, Price 100 -> Deep ITM (50 pts)
    # Intrinsic = 50 * 10 * 100 = 50,000 Risk

    risky, amt, details = _check_itm_risk([g], prices)
    assert risky
    assert amt == 50000.0
    assert "AAPL" in details[0]

def test_refresh_dashboard_data():
    saved_data = {
        "open_positions": [
            {"symbol": "AAPL", "qty_open": -1, "contract": "P 150.0", "strike": 150.0, "expiry": "2023-01-01"}
        ]
    }

    # Patch where it is imported in main_analyzer
    with patch("option_auditor.main_analyzer._fetch_live_prices") as mock_fetch:
        mock_fetch.return_value = {"AAPL": 100.0} # ITM

        res = refresh_dashboard_data(saved_data)

        p = res["open_positions"][0]
        assert p["current_price"] == 100.0
        # ITM Risk check: Strike 150 Put, Price 100 -> ITM
        # Should have risk alert
        assert "risk_alert" in p
        assert "ITM Risk" in p["risk_alert"]

# --- Main Analyzer Integration ---

def test_analyze_csv_empty_file(tmp_path):
    f = tmp_path / "empty.csv"
    f.touch()
    res = analyze_csv(csv_path=str(f))
    assert "error" in res
    assert "empty" in res["error"]

def test_analyze_csv_manual_data():
    # Fix: use 'qty' instead of 'quantity'
    manual_data = [
        {"date": "2023-01-01", "symbol": "AAPL", "action": "BUY", "qty": 100, "price": 100}
    ]
    # Patch yfinance to avoid network calls during open position check
    with patch("option_auditor.main_analyzer._fetch_live_prices", return_value={"AAPL": 110.0}):
        res = analyze_csv(manual_data=manual_data)
        assert "metrics" in res
        # Check open positions
        assert len(res["open_positions"]) == 1
        assert res["open_positions"][0]["symbol"] == "AAPL"

def test_analyze_csv_global_fees():
    # Fix: use 'qty' instead of 'quantity'
    manual_data = [
        {"date": "2023-01-01", "symbol": "AAPL", "action": "BUY", "qty": 100, "price": 100}
    ]
    with patch("option_auditor.main_analyzer._fetch_live_prices", return_value={"AAPL": 110.0}):
        res = analyze_csv(manual_data=manual_data, global_fees=1.0)
        # Check strategy groups fees
        # Open positions might form a strategy group if not closed?
        # Yes, build_strategies processes everything.
        strategies = res["strategy_groups"]
        assert len(strategies) > 0
        assert strategies[0]["fees"] == 1.0

def test_analyze_csv_no_data():
    res = analyze_csv()
    assert "error" in res
    assert "No input data" in res["error"]

def test_analyze_csv_unsupported_broker(tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("random,column")
    res = analyze_csv(csv_path=str(f), broker="bad_broker")
    assert "error" in res
