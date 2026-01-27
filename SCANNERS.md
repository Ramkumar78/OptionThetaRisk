# Option Auditor Scanners & Backtesters

This document details the specialized screening and backtesting capabilities of the Option Auditor platform.

## 1. Liquidity Grab (SMC) Screener

**Strategy ID:** `liquidityGrab`
**Endpoint:** `/screen/liquidity_grabs`

The **Liquidity Grab Screener** is based on Smart Money Concepts (SMC) and ICT (Inner Circle Trader) methodologies. It identifies high-probability reversal setups where price "sweeps" liquidity from recent swing points but fails to sustain the breakout (Rejection).

### Logic

The screener identifies:
1.  **Swing Highs/Lows:** Uses a fractal detection algorithm (default 3-bar lookback) to find recent pivotal highs and lows.
2.  **Sweeps:**
    *   **Bullish Sweep:** Price dips *below* a recent Swing Low (grabbing stop losses) but the candle *closes* back above that Swing Low. This indicates a "Bear Trap" or absorption of selling pressure.
    *   **Bearish Sweep:** Price spikes *above* a recent Swing High (grabbing buy stops) but the candle *closes* back below that Swing High. This indicates a "Bull Trap" or distribution.

### Risk Management (Default)
*   **Stop Loss:**
    *   Bullish: 0.5 ATR below the Low of the sweep candle.
    *   Bearish: 0.5 ATR above the High of the sweep candle.
*   **Target:** 3:1 Reward-to-Risk Ratio.

### How to Use
1.  Select **"Liquidity Grab (SMC)"** in the Screener dropdown.
2.  Choose a Timeframe (e.g., 1H for intraday, 1D for swing).
3.  Look for **"BULLISH SWEEP"** or **"BEARISH SWEEP"** verdicts.
4.  **Strength Score:** Higher % indicates a deeper sweep (displacement), often signaling a stronger reaction.

---

## 2. RSI Divergence Screener

**Strategy ID:** `rsiDivergence`
**Endpoint:** `/screen/rsi_divergence`

This screener detects **Regular Divergences**, which are powerful trend reversal signals.

### Logic
*   **Bullish Divergence:** Price makes a **Lower Low**, but RSI makes a **Higher Low**. This suggests momentum is shifting bullish despite the price drop.
*   **Bearish Divergence:** Price makes a **Higher High**, but RSI makes a **Lower High**. This suggests momentum is exhausted despite the price rise.

---

## 3. Backtesting

The platform includes a **Unified Backtester** capable of simulating these strategies over 5 years of historical data.

### Supported Strategies
*   `master` (Grandmaster/Fortress)
*   `isa` (Trend Following)
*   `turtle` (Donchian Breakouts)
*   `liquidity_grab` (SMC Sweeps)
*   `rsi` (RSI Divergence)

### How to Run (API)
Call the backtest endpoint with the ticker and strategy:

`GET /backtest/run?ticker=TSLA&strategy=liquidity_grab`

The result includes:
*   **Total Return vs Buy & Hold**
*   **Win Rate**
*   **Trade Log** (Entries, Exits, Reasons)
*   **Equity Curve Data**

### How to Run (Code)
You can run the backtester programmatically:

```python
from option_auditor.unified_backtester import UnifiedBacktester

# Run Liquidity Grab Backtest
bt = UnifiedBacktester("AAPL", strategy_type="liquidity_grab")
results = bt.run()

print(f"Strategy Return: {results['strategy_return']}%")
print(f"Win Rate: {results['win_rate']}")
```

---

## 4. Bollinger Squeeze Screener

**Strategy ID:** `squeeze`
**Endpoint:** `/screen/squeeze`

The **Bollinger Squeeze Screener** identifies stocks in a period of low volatility (consolidation) that often precedes a violent breakout. It uses the relationship between Bollinger Bands and Keltner Channels (TTM Squeeze concept).

### Logic
*   **Squeeze ON:** The Bollinger Bands (Length 20, Std 2.0) are completely *inside* the Keltner Channels (Length 20, ATR Mult 1.5). This indicates volatility is compressed relative to the average range.
*   **Momentum:** Uses the relationship between Price and the 20 SMA to determine potential breakout direction (Bullish or Bearish).

### Output
*   **Verdict:** "BULLISH SQUEEZE" or "BEARISH SQUEEZE".
*   **Momentum:** Directional bias.
*   **Target/Stop:** Based on ATR expansion.
