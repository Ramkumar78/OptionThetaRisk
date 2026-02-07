import logging

logger = logging.getLogger(__name__)

STRATEGY_DETAILS = {
    "Turtle": {
        "Philosophy": "Trend Following / Breakout",
        "Long_Term_Filter": "Uses 20/55 day highs",
        "Intermediate_Filter": "Donchian Channel (20)",
        "Core_Entry_Trigger": "Price > 20-day High",
        "Unique_Indicator": "Donchian Channels",
        "Stop_Loss_Logic": "2 ATR",
        "Profit_Target": "4 ATR",
        "Best_Used_For": "Strong Trending Markets",
        "Mathematical_Core": "Donchian High/Low",
        "Risk_Management": "ATR-based",
        "Breakout_Date": "Yes"
    },
    "5/13 EMA": {
        "Philosophy": "Momentum / Trend Following",
        "Long_Term_Filter": "52-week High (reporting only)",
        "Intermediate_Filter": "21 EMA",
        "Core_Entry_Trigger": "5 EMA cross 13 EMA",
        "Unique_Indicator": "Dual EMA Cross",
        "Stop_Loss_Logic": "Slow EMA or 1% below",
        "Profit_Target": "2R or 4 ATR",
        "Best_Used_For": "Swing Trading",
        "Mathematical_Core": "Exponential Moving Averages",
        "Risk_Management": "EMA-based trailing",
        "Breakout_Date": "Yes"
    },
    "Darvas Box": {
        "Philosophy": "Momentum / Breakout",
        "Long_Term_Filter": "Near 52-week High",
        "Intermediate_Filter": "Box Highs/Lows",
        "Core_Entry_Trigger": "Price breaks Box Ceiling",
        "Unique_Indicator": "Dynamic Box construction",
        "Stop_Loss_Logic": "Box Floor",
        "Profit_Target": "Box Height Extension",
        "Best_Used_For": "Bull Markets",
        "Mathematical_Core": "Pivot Highs/Lows",
        "Risk_Management": "Box Floor",
        "Breakout_Date": "Yes"
    },
    "ISA Strategy": {
        "Philosophy": "Long Term Trend Following",
        "Long_Term_Filter": "200 SMA",
        "Intermediate_Filter": "50-day High",
        "Core_Entry_Trigger": "Price > 50-day High (Donchian)",
        "Unique_Indicator": "Regulatory/Account specific sizing",
        "Stop_Loss_Logic": "3 ATR",
        "Profit_Target": "6 ATR",
        "Best_Used_For": "Wealth Building / ISA",
        "Mathematical_Core": "SMA + Donchian",
        "Risk_Management": "1% Risk per Trade, Max 20% Alloc",
        "Breakout_Date": "Yes"
    },
    "Fourier Strategy": {
        "Philosophy": "Cyclical / Mean Reversion",
        "Long_Term_Filter": "None",
        "Intermediate_Filter": "Hilbert Transform Phase",
        "Core_Entry_Trigger": "Phase turning from Negative to Positive",
        "Unique_Indicator": "Hilbert Transform / Signal Processing",
        "Stop_Loss_Logic": "2 ATR",
        "Profit_Target": "2 ATR",
        "Best_Used_For": "Oscillating/Sideways Markets",
        "Mathematical_Core": "DSP (Hilbert Transform)",
        "Risk_Management": "ATR-based",
        "Breakout_Date": "Yes"
    },
    "RSI Divergence": {
        "Philosophy": "Counter-Trend / Reversal",
        "Long_Term_Filter": "None",
        "Intermediate_Filter": "RSI (14)",
        "Core_Entry_Trigger": "Price Lower Low, RSI Higher Low (Bullish)",
        "Unique_Indicator": "Divergence detection",
        "Stop_Loss_Logic": "3 ATR",
        "Profit_Target": "5 ATR",
        "Best_Used_For": "Reversals",
        "Mathematical_Core": "Local Maxima/Minima comparison",
        "Risk_Management": "ATR-based",
        "Breakout_Date": "Yes"
    },
    "Medallion ISA": {
        "Philosophy": "Mean Reversion in Uptrend",
        "Long_Term_Filter": "200 SMA",
        "Intermediate_Filter": "50 SMA",
        "Core_Entry_Trigger": "RSI(3) < 15 & Volume Spike",
        "Unique_Indicator": "Short-term deep oversold in long-term uptrend",
        "Stop_Loss_Logic": "2 ATR",
        "Profit_Target": "SMA 20",
        "Best_Used_For": "Buy the Dip",
        "Mathematical_Core": "RSI(3) + Volume Stats",
        "Risk_Management": "ATR-based",
        "Breakout_Date": "Now"
    },
    "Bull Put Spread": {
        "Philosophy": "Income / Credit Strategy",
        "Long_Term_Filter": "50 SMA",
        "Intermediate_Filter": "IV Rank / IV > HV",
        "Core_Entry_Trigger": "30 Delta Short Put",
        "Unique_Indicator": "Options Mechanics",
        "Stop_Loss_Logic": "Technical Stop (2 ATR)",
        "Profit_Target": "Expiry / 50% Profit",
        "Best_Used_For": "Neutral to Bullish",
        "Mathematical_Core": "Black-Scholes Delta",
        "Risk_Management": "Defined Risk (Spread Width - Credit)",
        "Breakout_Date": "Yes"
    },
    "Bollinger Squeeze": {
        "Philosophy": "Volatility Expansion",
        "Long_Term_Filter": "None",
        "Intermediate_Filter": "Keltner Channels inside BB",
        "Core_Entry_Trigger": "BB Upper < KC Upper",
        "Unique_Indicator": "Volatility Compression",
        "Stop_Loss_Logic": "2 ATR",
        "Profit_Target": "3 ATR",
        "Best_Used_For": "Explosive Moves",
        "Mathematical_Core": "StdDev vs ATR",
        "Risk_Management": "ATR-based",
        "Breakout_Date": "Yes"
    },
    "Liquidity Grab": {
        "Philosophy": "Smart Money Concepts (SMC)",
        "Long_Term_Filter": "None",
        "Intermediate_Filter": "Swing Highs/Lows",
        "Core_Entry_Trigger": "Sweep of Swing Level + Rejection",
        "Unique_Indicator": "Fractal Swings",
        "Stop_Loss_Logic": "Swing Level +/- ATR",
        "Profit_Target": "3 ATR",
        "Best_Used_For": "Intraday/Swing Reversal",
        "Mathematical_Core": "Fractal Geometry",
        "Risk_Management": "Tight Stops",
        "Breakout_Date": "Yes"
    },
    "Fortress (Dynamic Volatility)": {
        "Philosophy": "Yield Optimization",
        "Long_Term_Filter": "200 SMA",
        "Intermediate_Filter": "VIX Regime",
        "Core_Entry_Trigger": "Price > Safe Floor (EMA20 - k*ATR)",
        "Unique_Indicator": "VIX-adjusted safety multiplier",
        "Stop_Loss_Logic": "Dynamic (k*ATR)",
        "Profit_Target": "2R",
        "Best_Used_For": "Income Generation",
        "Mathematical_Core": "VIX adjustment",
        "Risk_Management": "Volatility Adjusted",
        "Breakout_Date": "Yes"
    },
    "Quantum": {
        "Philosophy": "Physics / Chaos Theory",
        "Long_Term_Filter": "Kalman Filter Slope",
        "Intermediate_Filter": "Entropy & Hurst Exponent",
        "Core_Entry_Trigger": "AI Verdict based on Physics metrics",
        "Unique_Indicator": "Hurst, Entropy, Kalman",
        "Stop_Loss_Logic": "2.5 ATR",
        "Profit_Target": "4 ATR",
        "Best_Used_For": "Regimes detection",
        "Mathematical_Core": "Stochastic Calculus",
        "Risk_Management": "ATR-based",
        "Breakout_Date": "N/A"
    },
    "Options Only (Thalaiva)": {
        "Philosophy": "High Probability Income",
        "Long_Term_Filter": "None",
        "Intermediate_Filter": "Liquidity / Turnover",
        "Core_Entry_Trigger": "30 Delta, High ROC",
        "Unique_Indicator": "Speed Optimized",
        "Stop_Loss_Logic": "N/A (Credit Spread mechanics)",
        "Profit_Target": "Expiry",
        "Best_Used_For": "Monthly Income",
        "Mathematical_Core": "Options Greeks",
        "Risk_Management": "Defined Risk",
        "Breakout_Date": "N/A"
    },
    "MMS OTE (ICT)": {
        "Philosophy": "Market Maker Models",
        "Long_Term_Filter": "None",
        "Intermediate_Filter": "FVG (Fair Value Gaps)",
        "Core_Entry_Trigger": "Retracement to 62-79% Fib",
        "Unique_Indicator": "Fibonacci & Order Blocks",
        "Stop_Loss_Logic": "Swing High/Low",
        "Profit_Target": "-1.0 Extension",
        "Best_Used_For": "Precision Entry",
        "Mathematical_Core": "Fibonacci Ratios",
        "Risk_Management": "Tight",
        "Breakout_Date": "Yes"
    },
    "Alpha 101": {
        "Philosophy": "Quant / Delay-1 Momentum",
        "Long_Term_Filter": "None",
        "Intermediate_Filter": "Intraday strength",
        "Core_Entry_Trigger": "Alpha value > 0.5",
        "Unique_Indicator": "Formulaic Alpha",
        "Stop_Loss_Logic": "Low of Day",
        "Profit_Target": "2 ATR",
        "Best_Used_For": "Day Trading",
        "Mathematical_Core": "Price Action Formula",
        "Risk_Management": "Tight",
        "Breakout_Date": "Yes"
    },
    "Hybrid / Confluence": {
        "Philosophy": "Multi-Factor",
        "Long_Term_Filter": "200 SMA",
        "Intermediate_Filter": "Fourier Cycle",
        "Core_Entry_Trigger": "Confluence of Trend, Cycle, and Momentum",
        "Unique_Indicator": "Combining approaches",
        "Stop_Loss_Logic": "3 ATR",
        "Profit_Target": "5 ATR",
        "Best_Used_For": "High Confidence Setups",
        "Mathematical_Core": "Weighted Sum",
        "Risk_Management": "ATR-based",
        "Breakout_Date": "Yes"
    },
    "Monte Carlo": {
        "Philosophy": "Probabilistic Forecasting",
        "Long_Term_Filter": "N/A",
        "Intermediate_Filter": "N/A",
        "Core_Entry_Trigger": "N/A (Forecasting tool)",
        "Unique_Indicator": "Bootstrapping",
        "Stop_Loss_Logic": "N/A",
        "Profit_Target": "Median Forecast",
        "Best_Used_For": "Risk Assessment",
        "Mathematical_Core": "Random Sampling",
        "Risk_Management": "Probability distribution",
        "Breakout_Date": "N/A"
    }
}

def calculate_reliability_score(strategy_name: str, details: dict) -> int:
    """
    Calculates a Reliability Score (0-100) based on strategy characteristics.
    Base Score: 50
    +10: Explicit Stop Loss Logic (and not 'N/A')
    +10: Explicit Profit Target (and not 'N/A')
    +10: Uses Volatility (ATR, VIX, etc.) in logic or risk
    +10: Checks Long Term Trend (SMA 200, Highs)
    +10: Requires Confluence (Multi-factor)
    -10: Experimental / New / Single Indicator dependence
    """
    score = 50

    # Stop Loss Check
    sl = details.get("Stop_Loss_Logic", "")
    if sl and "N/A" not in sl:
        score += 10

    # Profit Target Check
    pt = details.get("Profit_Target", "")
    if pt and "N/A" not in pt:
        score += 10

    # Volatility Check
    if "ATR" in sl or "ATR" in pt or "VIX" in details.get("Unique_Indicator", "") or "Volatility" in details.get("Philosophy", ""):
        score += 10

    # Long Term Trend Check
    lt = details.get("Long_Term_Filter", "")
    if "200 SMA" in lt or "High" in lt or "Trend" in details.get("Philosophy", ""):
        score += 10

    # Confluence Check
    if "Hybrid" in strategy_name or "Confluence" in strategy_name or "Fortress" in strategy_name or "Medallion" in strategy_name:
        score += 10

    # Specific Adjustments based on analysis
    if strategy_name == "Monte Carlo":
        score = 85 # High reliability for what it is (stats)
    elif strategy_name == "Alpha 101":
        score -= 5 # Single factor (momentum), day trading is riskier
    elif strategy_name == "Fourier Strategy":
        score -= 5 # Complex math, can be laggy
    elif strategy_name == "Liquidity Grab":
        score -= 5 # Subjective patterns (SMC)

    return min(100, max(0, score))

def get_strategy_comparison_data():
    results = []
    for name, details in STRATEGY_DETAILS.items():
        score = calculate_reliability_score(name, details)
        row = details.copy()
        row["Strategy_Name"] = name
        row["Reliability_Score"] = score
        results.append(row)

    # Sort by Reliability Score Descending
    results.sort(key=lambda x: x["Reliability_Score"], reverse=True)
    return results
