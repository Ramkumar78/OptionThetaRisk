import pandas as pd
import numpy as np
import yfinance as yf
from option_auditor.common.data_utils import get_cached_market_data
from option_auditor.common.constants import SECTOR_COMPONENTS, SECTOR_NAMES

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
            except Exception:
                # Fallback
                pass
        else:
            # Fallback for single ticker or simple df
            closes = price_data['Close'] if 'Close' in price_data.columns else price_data

    # Filter to only the tickers we asked for
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
            except:
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
