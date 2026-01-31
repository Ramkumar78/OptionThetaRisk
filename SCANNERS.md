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

---

## 5. Turtle Trading Screener

**Strategy ID:** `turtle`
**Endpoint:** `/screen/turtle`

Classic Trend Following strategy based on Richard Dennis's Turtles.

### Logic
*   **Long Entry:** Price breaks above the 20-day High (Donchian Channel).
*   **Short Entry:** Price breaks below the 20-day Low.
*   **Exit:** 10-day Low (for Longs) or 10-day High (for Shorts).

---

## 6. 5/13 EMA Screener

**Strategy ID:** `ema_crossover`
**Endpoint:** `/screen/ema`

Momentum breakout strategy using fast Exponential Moving Averages.

### Logic
*   **Buy Signal:** 5 EMA crosses above 13 EMA (or is above 13 EMA for trending).
*   **Sell Signal:** 5 EMA crosses below 13 EMA.

---

## 7. Darvas Box Screener

**Strategy ID:** `darvas`
**Endpoint:** `/screen/darvas`

Identifies stocks breaking out of "boxes" (consolidations) on high volume, used by Nicolas Darvas to make $2M.

### Logic
*   **Box Construction:** Identifies a Ceiling (High that isn't exceeded for 3 days) and Floor.
*   **Breakout:** Price closes above the Box Ceiling.
*   **Volume:** Requires volume spike (e.g., > 2x average) to confirm validity.

---

## 8. ISA Trend Screener

**Strategy ID:** `isa`
**Endpoint:** `/screen/isa`

A robust Trend Following system designed for tax-free accounts (ISA).

### Logic
*   **Trend Filter:** Price must be above 200 SMA.
*   **Breakout:** Price breaks above 50-day High.
*   **Risk Management:** Dynamic position sizing based on account size and 3x ATR trailing stop.
*   **Verdict:** Returns "SAFE" or "RISKY" based on volatility and position size limits.

---

## 9. MMS OTE (Market Maker Sell/Buy Model)

**Strategy ID:** `mms_ote`
**Endpoint:** `/screen/mms_ote`

Based on ICT concepts, identifies Optimal Trade Entries (OTE) using Fibonacci retracements.

### Logic
*   **Structure Shift:** Identifies Market Structure Shift (MSS) after a liquidity sweep.
*   **Retracement:** Waits for price to return to the 62-79% Fibonacci zone.
*   **Direction:** Bullish OTE (Buy in discount) or Bearish OTE (Sell in premium).

---

## 10. Alpha 101 Screener

**Strategy ID:** `alpha101`
**Endpoint:** `/screen/alpha101`

Implements select alphas from the paper "101 Formulaic Alphas".

### Logic
*   **Alpha #1:** Mean reversion based on returns and volume.
*   **Logic:** `rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5`
*   **Output:** Quantile ranking of stocks.

---

## 11. Hybrid Strategy

**Strategy ID:** `hybrid`
**Endpoint:** `/screen/hybrid`

Combines multiple signals (Trend, Cycle, Volume) for a high-conviction verdict.

### Logic
*   **Trend:** 200 SMA.
*   **Cycle:** Fourier Transform / Hilbert Phase.
*   **Momentum:** RSI & MACD.
*   **Verdict:** "PERFECT BUY" when all align.

---

## 12. Fortress Strategy

**Strategy ID:** `fortress`
**Endpoint:** `/screen/fortress`

A defensive strategy adapting to Market Regimes (Green/Yellow/Red).

### Logic
*   **Regime:** Uses VIX and SPY Trend to determine regime.
*   **Action:**
    *   Green: Aggressive Longs.
    *   Yellow: Hedged / Quality.
    *   Red: Cash / Shorts / Put Spreads.

---

## 13. Bull Put Spread Screener

**Strategy ID:** `bull_put`
**Endpoint:** `/screen/bull_put`

Finds high-probability credit spreads for income.

### Logic
*   **Trend:** Stock in uptrend (> 50 SMA).
*   **Oversold:** Short-term pullback (RSI < 50 but > 40).
*   **Strike Selection:** Sell Puts at delta ~0.20 or support levels.

---

## 14. Fourier Cycles

**Strategy ID:** `fourier`
**Endpoint:** `/screen/fourier`

Uses Digital Signal Processing (DSP) to find cyclical turning points.

### Logic
*   **Dominant Cycle:** Extracts the dominant cycle period.
*   **Phase:** Calculates phase (0-360) to identify Tops (Peak) and Bottoms (Valley).

---

## 15. Quantum Setups

**Strategy ID:** `quantum`
**Endpoint:** `/screen/quantum`

Experimental physics-based screener (likely using momentum/energy analogues).

### Logic
*   **Energy:** Measures "kinetic energy" of price moves.
*   **Entanglement:** Correlation with sector/index.
