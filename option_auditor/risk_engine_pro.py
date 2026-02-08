import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Union, Optional
from datetime import datetime
from option_auditor import portfolio_risk
from option_auditor.models import StressTestResult, TradeGroup
from option_auditor.strategies.math_utils import calculate_option_price, calculate_greeks
from option_auditor.common.data_utils import get_cached_market_data

logger = logging.getLogger(__name__)

class RiskEngine:
    """
    Advanced Risk Engine for portfolio stress testing, Greeks analysis, and correlation heatmaps.
    """
    def __init__(self, positions: List[Union[Dict[str, Any], TradeGroup]]):
        """
        Initialize with a list of positions.
        Positions can be TradeGroup objects or dictionaries.
        """
        self.raw_positions = positions
        self.positions = []
        self.tickers = set()
        self.market_data = {}

        # Normalize positions immediately
        self._normalize_positions()

    def _normalize_positions(self):
        """
        Convert mixed input types (TradeGroup, dict) into a standard internal dictionary format.
        Standard format:
        {
            'symbol': str,
            'qty': float,
            'strike': Optional[float],
            'right': Optional[str] ('C'/'P'),
            'expiry': Optional[str] (YYYY-MM-DD),
            'multiplier': float (100 for options, 1 for stock)
        }
        """
        for p in self.raw_positions:
            norm = {}
            if isinstance(p, TradeGroup):
                norm['symbol'] = p.symbol
                norm['qty'] = p.qty_net
                norm['strike'] = p.strike
                norm['right'] = p.right # 'C' or 'P'
                if p.expiry:
                    norm['expiry'] = pd.to_datetime(p.expiry).strftime('%Y-%m-%d')
                else:
                    norm['expiry'] = None
                norm['multiplier'] = 100.0 if (p.strike and p.right) else 1.0
            elif isinstance(p, dict):
                norm['symbol'] = p.get('symbol') or p.get('ticker')
                norm['qty'] = float(p.get('qty', p.get('qty_net', 0)))
                norm['strike'] = float(p.get('strike')) if p.get('strike') else None
                norm['right'] = p.get('right') or p.get('type') # 'C'/'P' or 'call'/'put'

                # Normalize right to 'C'/'P'
                if norm['right']:
                    r = norm['right'].upper()
                    if r.startswith('C'): norm['right'] = 'C'
                    elif r.startswith('P'): norm['right'] = 'P'

                norm['expiry'] = p.get('expiry')
                if norm['expiry']:
                     try:
                         norm['expiry'] = pd.to_datetime(norm['expiry']).strftime('%Y-%m-%d')
                     except:
                         norm['expiry'] = None

                norm['multiplier'] = 100.0 if (norm['strike'] and norm['right']) else 1.0

            if norm['symbol']:
                norm['symbol'] = norm['symbol'].upper()
                self.positions.append(norm)
                self.tickers.add(norm['symbol'])

    def _fetch_market_data(self):
        """
        Fetches current price and historical volatility for all unique tickers.
        Stores in self.market_data: { 'SYMBOL': {'price': float, 'vol': float} }
        """
        if not self.tickers:
            return

        ticker_list = list(self.tickers)
        # Fetch 6 months of data for volatility calculation
        data = get_cached_market_data(ticker_list, period="6mo", cache_name="risk_engine_pro")

        for t in ticker_list:
            price = 0.0
            vol = 0.40 # Default IV

            try:
                # Extract Series for this ticker
                series = pd.Series()

                # Handle MultiIndex (Ticker, OHLC) or (OHLC, Ticker) or Single Level
                if isinstance(data.columns, pd.MultiIndex):
                    if t in data.columns.get_level_values(0):
                        if 'Close' in data[t].columns:
                            series = data[t]['Close']
                    elif t in data.columns.get_level_values(1):
                        # Find col where level 1 is t and level 0 is Close
                        cols = [c for c in data.columns if c[1] == t and c[0] == 'Close']
                        if cols:
                            series = data[cols[0]]
                else:
                    # Single level
                    if 'Close' in data.columns:
                        series = data['Close']
                    elif t in data.columns:
                        series = data[t]

                if not series.empty:
                    series = series.sort_index()
                    last_val = series.dropna().iloc[-1] if not series.dropna().empty else 0
                    price = float(last_val)

                    # Calculate Historic Volatility (30-day annualized)
                    returns = np.log(series / series.shift(1))
                    if len(returns) > 30:
                        vol = returns.rolling(window=30).std().iloc[-1] * np.sqrt(252)
                    else:
                        vol = returns.std() * np.sqrt(252)

                    if pd.isna(vol) or vol < 1e-4:
                        vol = 0.40
            except Exception as e:
                logger.error(f"Error fetching data for {t}: {e}")

            self.market_data[t] = {'price': price, 'vol': vol}

    def _calculate_time_to_expiry(self, expiry_str: Optional[str]) -> float:
        if not expiry_str:
            return 0.0
        try:
            expiry = datetime.strptime(expiry_str, '%Y-%m-%d')
            # Set to end of day
            expiry = expiry.replace(hour=16, minute=0, second=0)
            now = datetime.now()
            diff = (expiry - now).total_seconds()
            if diff <= 0:
                return 0.0
            return diff / (365.0 * 24 * 3600)
        except Exception:
            return 0.0

    def run_what_if_analysis(self) -> List[StressTestResult]:
        """
        Simulate -10% to +10% market moves in 1% increments.
        """
        if not self.market_data:
            self._fetch_market_data()

        results = []
        r = 0.045 # Risk Free Rate assumption

        # Calculate current portfolio value for baseline
        total_current_value = 0.0
        # Pre-calculate base parameters for all positions to speed up loop
        calc_positions = []

        for p in self.positions:
            sym = p['symbol']
            md = self.market_data.get(sym, {'price': 0.0, 'vol': 0.4})
            S = md['price']
            sigma = md['vol']

            if S <= 0: continue

            T = 0.0
            is_option = False
            if p['strike'] and p['right']:
                is_option = True
                T = self._calculate_time_to_expiry(p['expiry'])

            # Calculate current value
            val_curr = 0.0
            if is_option:
                otype = 'call' if p['right'] == 'C' else 'put'
                price = calculate_option_price(S, p['strike'], T, r, sigma, otype)
                val_curr = price * p['multiplier'] * p['qty']
            else:
                val_curr = S * p['qty']

            total_current_value += val_curr

            calc_positions.append({
                'p': p, 'S': S, 'sigma': sigma, 'T': T, 'is_option': is_option, 'val_curr': val_curr
            })

        # Loop -10 to +10
        for i in range(-10, 11):
            pct = i # Integer percent
            factor = 1 + (pct / 100.0)

            total_new_value = 0.0

            for item in calc_positions:
                S_new = item['S'] * factor
                sigma = item['sigma']

                val_new = 0.0
                if item['is_option']:
                    p = item['p']
                    otype = 'call' if p['right'] == 'C' else 'put'
                    price_new = calculate_option_price(S_new, p['strike'], item['T'], r, sigma, otype)
                    val_new = price_new * p['multiplier'] * p['qty']
                else:
                    val_new = S_new * item['p']['qty']

                total_new_value += val_new

            pnl = total_new_value - total_current_value
            pnl_pct = (pnl / abs(total_current_value) * 100) if total_current_value != 0 else 0.0

            results.append(StressTestResult(
                scenario_name=f"Market {'+' if pct > 0 else ''}{pct}%",
                market_move_pct=float(pct),
                portfolio_value_change=round(pnl, 2),
                portfolio_value_change_pct=round(pnl_pct, 2),
                details=[]
            ))

        return results

    def calculate_portfolio_greeks(self) -> Dict[str, float]:
        """
        Calculate total Delta, Gamma, Vega, Theta for the portfolio.
        """
        if not self.market_data:
            self._fetch_market_data()

        totals = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
        r = 0.045

        for p in self.positions:
            sym = p['symbol']
            md = self.market_data.get(sym, {'price': 0.0, 'vol': 0.4})
            S = md['price']
            sigma = md['vol']

            if S <= 0: continue

            # If stock, Delta = 1 (or -1? No, stock delta is 1 per share).
            # If Short Stock, qty is negative, so Delta contribution is naturally negative.
            if not (p['strike'] and p['right']):
                # Stock
                totals['delta'] += 1.0 * p['qty']
                continue

            T = self._calculate_time_to_expiry(p['expiry'])

            otype = 'call' if p['right'] == 'C' else 'put'
            greeks = calculate_greeks(S, p['strike'], T, r, sigma, otype)

            # Scale by quantity and multiplier (100)
            factor = p['qty'] * p['multiplier']

            totals['delta'] += greeks['delta'] * factor
            totals['gamma'] += greeks['gamma'] * factor
            totals['theta'] += greeks['theta'] * factor
            totals['vega'] += greeks['vega'] * factor

        return {k: round(v, 2) for k, v in totals.items()}

    def generate_correlation_heatmap(self) -> Dict[str, Any]:
        """
        Generate correlation matrix for the portfolio.
        Delegates to portfolio_risk analysis but returns just the matrix structure.
        """
        try:
            # Re-use existing logic which is robust
            report = portfolio_risk.analyze_portfolio_risk(self.raw_positions)
            return report.get('correlation_matrix', {})
        except Exception as e:
            logger.error(f"Error generating correlation heatmap: {e}")
            return {}

def check_allocation_concentration(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Checks if any single ticker exceeds 5% of the total portfolio value.
    Input: List of dicts with 'ticker' and 'value'.
    Output: List of violations, e.g., [{'ticker': 'AAPL', 'percentage': 12.5}]
    """
    if not positions:
        return []

    total_value = sum(float(p.get('value', 0)) for p in positions)
    if total_value == 0:
        return []

    violations = []

    # Aggregate value by ticker first to handle multiple entries for same ticker
    ticker_values = {}
    for p in positions:
        t = p.get('ticker', 'UNKNOWN').upper()
        v = float(p.get('value', 0))
        ticker_values[t] = ticker_values.get(t, 0) + v

    for ticker, value in ticker_values.items():
        pct = (value / total_value) * 100
        if pct > 5.0:
            violations.append({
                "ticker": ticker,
                "percentage": round(pct, 2),
                "message": f"Allocation {pct:.1f}% exceeds 5% limit."
            })

    return violations

def calculate_retail_safety_score(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates a 'Retail Safety Score' (0-100).
    Penalties:
    - Concentration: -5 points for each ticker > 5%.
    - Sector Risk: -10 points for each sector warning (from portfolio_risk).
    - Correlation: -10 points for high correlation warnings (from portfolio_risk).
    """
    score = 100
    breakdown = []

    # 1. Concentration Check
    concentration_violations = check_allocation_concentration(positions)
    for violation in concentration_violations:
        penalty = 5
        score -= penalty
        breakdown.append(f"Concentration penalty: -{penalty} for {violation['ticker']} ({violation['percentage']}%)")

    # 2. Use existing portfolio risk analysis for Sector and Correlation
    # portfolio_risk.analyze_portfolio_risk handles sector and correlation logic
    try:
        risk_report = portfolio_risk.analyze_portfolio_risk(positions)
    except Exception as e:
        logger.error(f"Error calling analyze_portfolio_risk: {e}")
        risk_report = {}

    # Sector Warnings
    sector_warnings = risk_report.get("sector_warnings", [])
    for warning in sector_warnings:
        penalty = 10
        score -= penalty
        breakdown.append(f"Sector penalty: -{penalty} ({warning})")

    # Correlation / Diversification
    # analyze_portfolio_risk returns 'high_correlation_pairs'
    high_corr = risk_report.get("high_correlation_pairs", [])
    duplicate_risks = [p for p in high_corr if p.get('verdict') == "🔥 DUPLICATE RISK"]

    if duplicate_risks:
        penalty = 10 * len(duplicate_risks)
        score -= penalty
        breakdown.append(f"Correlation penalty: -{penalty} ({len(duplicate_risks)} high correlation pairs)")

    # Ensure score is 0-100
    score = max(0, min(100, score))

    return {
        "score": score,
        "breakdown": breakdown,
        "details": risk_report
    }

def calculate_what_if_scenario(positions: List[Dict[str, Any]], scenario_type: str = "market_drop_10") -> Dict[str, Any]:
    """
    Calculates impact of a market scenario.
    Default: FTSE 100 or S&P 500 drops 10% overnight.
    We simulate this by dropping all asset prices by 10%.
    """
    if scenario_type == "market_drop_10":
        scenario = {"price_change_pct": -10.0, "vol_change_pct": 0.0}
    else:
        # Default or handle other scenarios
        scenario = {"price_change_pct": -10.0, "vol_change_pct": 0.0}

    # Check if the input has option details (strike, type, expiry)
    # analyze_scenario requires these to price options.
    has_option_details = any('strike' in p and 'expiry' in p for p in positions)

    if has_option_details:
        return portfolio_risk.analyze_scenario(positions, scenario)
    else:
        # Simple equity simulation using 'value'
        total_val = sum(float(p.get('value', 0)) for p in positions)
        if total_val == 0:
            return {"current_value": 0, "new_value": 0, "pnl": 0, "pnl_pct": 0, "details": []}

        drop_pct = scenario["price_change_pct"] / 100.0
        new_val = total_val * (1 + drop_pct)
        pnl = new_val - total_val

        return {
            "current_value": total_val,
            "new_value": new_val,
            "pnl": pnl,
            "pnl_pct": scenario["price_change_pct"],
            "details": [{"ticker": "ALL", "pnl": pnl, "note": "Simplified equity shock applied to total value"}]
        }
