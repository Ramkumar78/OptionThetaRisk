import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from option_auditor.common.data_utils import get_cached_market_data
from option_auditor.common.constants import SECTOR_COMPONENTS, SECTOR_NAMES
from option_auditor.strategies.math_utils import calculate_greeks, calculate_option_price
import logging

logger = logging.getLogger(__name__)

def _get_sector_map():
    """Reverse maps your constants to find sectors fast without API calls."""
    sector_map = {}
    for sector_code, tickers in SECTOR_COMPONENTS.items():
        # Map code (XLK) to Name (Technology) if possible
        sector_name = SECTOR_NAMES.get(sector_code, sector_code)
        if isinstance(tickers, list):
            for t in tickers:
                sector_map[t] = sector_name
    return sector_map

def analyze_portfolio_risk(positions: list) -> dict:
    """
    Input: [{'ticker': 'NVDA', 'value': 10000}, {'ticker': 'GOOG', 'value': 5000}]
    Output: Risk Report with Correlation Matrix and Sector Warnings.
    """
    if not positions:
        return {}

    # 1. Convert Input to DataFrame
    pos_df = pd.DataFrame(positions)
    # Ensure columns exist
    if 'ticker' not in pos_df.columns or 'value' not in pos_df.columns:
        return {"error": "Invalid input format. Must contain 'ticker' and 'value'."}

    pos_df['ticker'] = pos_df['ticker'].astype(str).str.upper().str.strip()
    pos_df['value'] = pd.to_numeric(pos_df['value'], errors='coerce').fillna(0)

    total_value = pos_df['value'].sum()

    if total_value == 0:
         # To avoid JSON serialization errors with numpy types, return Python primitive
         return {"error": "Total portfolio value is zero."}

    # Ensure total_value is a float
    total_value = float(total_value)

    ticker_list = pos_df['ticker'].unique().tolist()

    # 2. Get Historical Data (1 Year) for Correlation
    # We use your existing Cached Loader to be fast and safe
    price_data = get_cached_market_data(ticker_list, period="1y", cache_name="portfolio_risk")

    # Handle MultiIndex if necessary
    closes = pd.DataFrame()
    if not price_data.empty:
        if isinstance(price_data.columns, pd.MultiIndex):
            # If MultiIndex (Ticker, Price), get Close
            try:
                # yfinance group_by='ticker' -> (Ticker, OHLC)
                # We need to extract Close for each Ticker.
                # xs with level=1 assumes level 1 is 'Close'.
                if 'Close' in price_data.columns.get_level_values(1):
                     closes = price_data.xs('Close', level=1, axis=1)
                else:
                    # Fallback if structure is different
                    closes = price_data.xs('Close', level=1, axis=1)
            except Exception as e:
                # Fallback
                logger.debug(f"Failed to slice multi-index price data: {e}")
        else:
            # Fallback for single ticker or simple df
            if 'Close' in price_data.columns:
                # Likely single ticker OHLC
                # If we have only one ticker, we can map it
                if len(ticker_list) == 1:
                   closes = price_data[['Close']].rename(columns={'Close': ticker_list[0]})
                else:
                   # Fallback, but keep as DF to avoid crash, though column name might be 'Close'
                   closes = price_data[['Close']]
            else:
                 closes = price_data

    # Ensure closes is DataFrame
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()

    # Filter to only the tickers we asked for
    # If columns don't match tickers (e.g. 'Close'), try to be smart or just use what we have if 1:1
    if len(ticker_list) == 1 and len(closes.columns) == 1:
        # Assume it's the one
        if closes.columns[0] != ticker_list[0]:
             closes.columns = [ticker_list[0]]

    valid_tickers = [t for t in ticker_list if t in closes.columns]
    closes = closes[valid_tickers]

    # --- A. CONCENTRATION RISK (Single Stock) ---
    concentration_warnings = []
    # Calculate weight per ticker (handle duplicates in input by grouping)
    ticker_weights = pos_df.groupby('ticker')['value'].sum() / total_value

    for ticker, weight in ticker_weights.items():
        pct = weight * 100
        if pct > 15.0: # Threshold: >15% in one stock
            concentration_warnings.append(
                f"⚠️ HIGH CONCENTRATION: {ticker} is {pct:.1f}% of portfolio. (Rec: <10%)"
            )

    # --- B. SECTOR RISK ---
    sector_map = _get_sector_map()

    # Apply map to the grouped ticker df (conceptually)
    # We need to map each ticker in ticker_weights to a sector
    ticker_sectors = {}

    # Identify Unknowns
    unknowns = [t for t in ticker_list if t not in sector_map]

    # If Unknown, try a quick fetch (slow path) - limit to 5
    if unknowns:
        for t in unknowns[:5]: # Limit to 5 to avoid timeouts
            try:
                info = yf.Ticker(t).info
                real_sector = info.get('sector', 'Other')
                # Add to map
                sector_map[t] = real_sector
            except Exception as e:
                logger.debug(f"Failed to fetch sector for {t}: {e}")
                sector_map[t] = 'Unknown'

    # Calculate Sector Weights
    sector_values = {}
    for ticker, weight in ticker_weights.items():
        sec = sector_map.get(ticker, 'Unknown')
        val = weight * total_value
        sector_values[sec] = sector_values.get(sec, 0) + val

    sector_risk = {k: v / total_value for k, v in sector_values.items()}

    sector_warnings = []
    sector_breakdown = []

    for sector, weight in sector_risk.items():
        pct = weight * 100
        sector_breakdown.append({"name": sector, "value": round(pct, 1)})

        if pct > 30.0 and sector != "Unknown":
            sector_warnings.append(
                f"🛑 SECTOR OVERLOAD: {pct:.1f}% in {sector}. If this sector rotates, you crash."
            )

    # Sort breakdown by value desc
    sector_breakdown.sort(key=lambda x: x['value'], reverse=True)

    # --- C. CORRELATION RISK (The Math) ---
    high_corr_pairs = []
    corr_matrix_dict = {}
    div_score = 0

    if not closes.empty and len(closes.columns) > 1:
        # Calculate daily returns
        returns = closes.pct_change().dropna()

        if not returns.empty:
            # Correlation Matrix (-1.0 to 1.0)
            corr_matrix = returns.corr()
            corr_matrix_dict = corr_matrix.to_dict()

            tickers_in_matrix = corr_matrix.columns

            # Iterate upper triangle to avoid duplicates
            for i in range(len(tickers_in_matrix)):
                for j in range(i+1, len(tickers_in_matrix)):
                    t1, t2 = tickers_in_matrix[i], tickers_in_matrix[j]
                    score = corr_matrix.iloc[i, j]

                    if score > 0.8:
                        high_corr_pairs.append({
                            "pair": f"{t1} + {t2}",
                            "score": round(score, 2),
                            "verdict": "🔥 DUPLICATE RISK"
                        })
                    elif score < 0.0:
                        high_corr_pairs.append({
                            "pair": f"{t1} + {t2}",
                            "score": round(score, 2),
                            "verdict": "✅ GOOD HEDGE"
                        })

            # Portfolio Diversification Score (1 - Average Correlation)
            # We want average of off-diagonal elements
            # Sum of matrix - Sum of diagonal (which is len(tickers))
            # Count of off-diagonal elements = N^2 - N
            n = len(tickers_in_matrix)
            if n > 1:
                sum_corr = corr_matrix.sum().sum()
                avg_corr = (sum_corr - n) / (n**2 - n)
                div_score = (1 - avg_corr) * 100
            else:
                div_score = 0 # Single asset = No diversification benefit? Or 0 correlation?
                # If single asset, risk is high. Diversification is 0.
    else:
        # Not enough data for correlation
        div_score = 0

    return {
        "total_value": total_value,
        "diversification_score": round(div_score, 1),
        "concentration_warnings": concentration_warnings,
        "sector_warnings": sector_warnings,
        "sector_breakdown": sector_breakdown, # For Pie Chart
        "high_correlation_pairs": high_corr_pairs, # For Table
        "correlation_matrix": corr_matrix_dict # For Heatmap (advanced)
    }

def analyze_portfolio_greeks(positions: list) -> dict:
    """
    Calculates aggregated Greeks for an options portfolio.

    Input: List of dicts with:
      - ticker: str
      - type: "call" or "put"
      - strike: float
      - expiry: str ("YYYY-MM-DD")
      - qty: float

    Output:
      - portfolio_totals: {delta, gamma, theta, vega}
      - positions: List of details per position
    """
    if not positions:
        return {}

    # 1. Gather Tickers and fetch Prices
    tickers = list(set([p['ticker'].upper().strip() for p in positions]))

    # Fetch Data (Price + History for Vol)
    # Using 6mo to get enough history for 30d rolling vol
    market_data = get_cached_market_data(tickers, period="6mo", cache_name="portfolio_greeks")

    current_prices = {}
    historical_vols = {}

    # Extract Current Price and Calculate Vol
    for t in tickers:
        try:
            # Handle MultiIndex or Single
            series = pd.Series()

            if isinstance(market_data.columns, pd.MultiIndex):
                # Try to find the Close column for this ticker
                # yfinance often returns (PriceType, Ticker) or (Ticker, PriceType)
                if t in market_data.columns.get_level_values(0):
                     # Likely (Ticker, OHLC)
                     if 'Close' in market_data[t].columns:
                         series = market_data[t]['Close']
                elif t in market_data.columns.get_level_values(1):
                     # Likely (OHLC, Ticker)
                     # Find column where level 1 is t and level 0 is Close
                     cols = [c for c in market_data.columns if c[1] == t and c[0] == 'Close']
                     if cols:
                         series = market_data[cols[0]]
            else:
                 # Single ticker case or flat columns
                 # If flat columns, check if 'Close' exists or if column name is the ticker (Close only df)
                 if 'Close' in market_data.columns:
                     series = market_data['Close']
                 elif t in market_data.columns:
                     series = market_data[t]

            if not series.empty:
                # Ensure sorted by date
                series = series.sort_index()

                # Get Last Price (Handle NaN at end if any)
                last_valid = series.dropna().iloc[-1] if not series.dropna().empty else 0
                current_prices[t] = float(last_valid)

                # Calculate Hist Vol (30d annualized)
                # Log returns
                returns = np.log(series / series.shift(1))
                # 30-day std dev annualized
                if len(returns) > 30:
                    vol = returns.rolling(window=30).std().iloc[-1] * np.sqrt(252)
                else:
                    vol = returns.std() * np.sqrt(252)

                if pd.isna(vol) or vol < 1e-4:
                    vol = 0.4 # Default
                historical_vols[t] = vol
            else:
                 # Fallback if fetch failed (use last known or manual entry?)
                 # For now, 0 price effectively disables greeks
                 current_prices[t] = 0.0
                 historical_vols[t] = 0.4

        except Exception as e:
            logger.error(f"Error processing data for {t}: {e}")
            current_prices[t] = 0.0
            historical_vols[t] = 0.4

    # 2. Iterate Positions
    portfolio_totals = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    position_details = []

    now = datetime.now()

    for pos in positions:
        try:
            ticker = pos.get('ticker', '').upper().strip()
            otype = pos.get('type', 'call').lower().strip()
            strike = float(pos.get('strike', 0))
            expiry_str = pos.get('expiry', '').strip()
            qty = float(pos.get('qty', 0))

            if not ticker or not expiry_str:
                continue

            S = current_prices.get(ticker, 0.0)
            sigma = historical_vols.get(ticker, 0.4)
            r = 0.045 # 4.5% Risk Free Rate

            if S <= 0:
                # Can't calc greeks
                position_details.append({
                    "ticker": ticker,
                    "error": "Price unavailable"
                })
                continue

            # TTE
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            except ValueError:
                 # Try other formats if needed, or skip
                 continue

            # Set to end of day (16:00)
            expiry_date = expiry_date.replace(hour=16, minute=0, second=0)

            diff = expiry_date - now
            days_to_expiry = diff.total_seconds() / 86400.0
            T = days_to_expiry / 365.0

            # If expired or today
            if T < 0: T = 0

            greeks = calculate_greeks(S, strike, T, r, sigma, otype)

            # Scale by Qty and Contract Size (100)
            multiplier = 100 * qty

            pos_delta = greeks['delta'] * multiplier
            pos_gamma = greeks['gamma'] * multiplier
            pos_theta = greeks['theta'] * multiplier
            pos_vega = greeks['vega'] * multiplier

            # Aggregate
            portfolio_totals['delta'] += pos_delta
            portfolio_totals['gamma'] += pos_gamma
            portfolio_totals['theta'] += pos_theta
            portfolio_totals['vega'] += pos_vega

            position_details.append({
                "ticker": ticker,
                "type": otype,
                "strike": strike,
                "expiry": expiry_str,
                "qty": qty,
                "S": round(S, 2),
                "IV": round(sigma * 100, 1),
                "delta": round(pos_delta, 2),
                "gamma": round(pos_gamma, 2),
                "theta": round(pos_theta, 2),
                "vega": round(pos_vega, 2)
            })

        except Exception as e:
            logger.error(f"Error calculating greeks for position {pos}: {e}")
            continue

    return {
        "portfolio_totals": {k: round(v, 2) for k, v in portfolio_totals.items()},
        "positions": position_details
    }


def analyze_scenario(positions: list, scenario: dict) -> dict:
    """
    Project PnL based on a market shock scenario.
    scenario: { "price_change_pct": float, "vol_change_pct": float }
    """
    if not positions:
        return {}

    # Extract scenario params
    price_change_pct = float(scenario.get("price_change_pct", 0.0))
    vol_change_pct = float(scenario.get("vol_change_pct", 0.0))

    # 1. Gather Tickers and fetch Prices
    tickers = list(set([p['ticker'].upper().strip() for p in positions]))
    market_data = get_cached_market_data(tickers, period="6mo", cache_name="portfolio_scenario")

    current_prices = {}
    historical_vols = {}

    # Fetch Data Logic (Duplicated from Greeks analysis for safety/isolation)
    for t in tickers:
        try:
            series = pd.Series()
            if isinstance(market_data.columns, pd.MultiIndex):
                if t in market_data.columns.get_level_values(0):
                     if 'Close' in market_data[t].columns:
                         series = market_data[t]['Close']
                elif t in market_data.columns.get_level_values(1):
                     cols = [c for c in market_data.columns if c[1] == t and c[0] == 'Close']
                     if cols:
                         series = market_data[cols[0]]
            else:
                 if 'Close' in market_data.columns:
                     series = market_data['Close']
                 elif t in market_data.columns:
                     series = market_data[t]

            if not series.empty:
                series = series.sort_index()
                last_valid = series.dropna().iloc[-1] if not series.dropna().empty else 0
                current_prices[t] = float(last_valid)

                returns = np.log(series / series.shift(1))
                if len(returns) > 30:
                    vol = returns.rolling(window=30).std().iloc[-1] * np.sqrt(252)
                else:
                    vol = returns.std() * np.sqrt(252)

                if pd.isna(vol) or vol < 1e-4:
                    vol = 0.4
                historical_vols[t] = vol
            else:
                 current_prices[t] = 0.0
                 historical_vols[t] = 0.4
        except Exception as e:
            logger.error(f"Error processing data for {t}: {e}")
            current_prices[t] = 0.0
            historical_vols[t] = 0.4

    # 2. Calculate PnL Impact
    total_current_value = 0.0
    total_new_value = 0.0
    now = datetime.now()
    details = []

    for pos in positions:
        try:
            ticker = pos.get('ticker', '').upper().strip()
            otype = pos.get('type', 'call').lower().strip()
            strike = float(pos.get('strike', 0))
            expiry_str = pos.get('expiry', '').strip()
            qty = float(pos.get('qty', 0))

            if not ticker or not expiry_str:
                continue

            S = current_prices.get(ticker, 0.0)
            sigma = historical_vols.get(ticker, 0.4)
            r = 0.045

            if S <= 0: continue

            # Apply Shock
            S_new = S * (1 + price_change_pct / 100.0)
            sigma_new = sigma * (1 + vol_change_pct / 100.0)
            if sigma_new < 0.01: sigma_new = 0.01

            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            except ValueError:
                 continue

            expiry_date = expiry_date.replace(hour=16, minute=0, second=0)
            diff = expiry_date - now
            days_to_expiry = diff.total_seconds() / 86400.0
            T = days_to_expiry / 365.0
            if T < 0: T = 0

            # Calculate Prices
            price_curr = calculate_option_price(S, strike, T, r, sigma, otype)
            price_new = calculate_option_price(S_new, strike, T, r, sigma_new, otype)

            val_curr = price_curr * 100 * qty
            val_new = price_new * 100 * qty

            pnl = val_new - val_curr

            total_current_value += val_curr
            total_new_value += val_new

            details.append({
                "ticker": ticker,
                "type": otype,
                "strike": strike,
                "qty": qty,
                "S_old": round(S, 2),
                "S_new": round(S_new, 2),
                "IV_old": round(sigma*100, 1),
                "IV_new": round(sigma_new*100, 1),
                "val_old": round(val_curr, 2),
                "val_new": round(val_new, 2),
                "pnl": round(pnl, 2)
            })

        except Exception as e:
            logger.error(f"Error calculating scenario for {pos}: {e}")
            continue

    total_pnl = total_new_value - total_current_value
    pnl_pct = (total_pnl / abs(total_current_value) * 100) if total_current_value != 0 else 0.0

    return {
        "current_value": round(total_current_value, 2),
        "new_value": round(total_new_value, 2),
        "pnl": round(total_pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "details": details
    }
