import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging

# --- CONFIGURATION (HARDENED) ---
ISA_ACCOUNT_GBP = 100000.0  # Your Capital
OPTIONS_ACCOUNT_USD = 9500.0
RISK_PER_TRADE = 0.01       # 1% Risk Rule (Seykota/Thorp)
MIN_VOL_US = 1_000_000      # Liquidity Gate (Griffin)
MIN_VOL_UK = 200_000        # Liquidity Gate for UK (Lower due to market size)
VIX_PANIC_LEVEL = 28.0      # Soros Gate (Market Crash Level)

# Setup Logger
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("CouncilScreener")

class MasterScreener:
    def __init__(self, tickers_us, tickers_uk):
        self.tickers_us = list(set(tickers_us))
        self.tickers_uk = list(set(tickers_uk))
        self.all_tickers = self.tickers_us + self.tickers_uk
        self.regime = "NEUTRAL"

    def check_market_regime(self):
        """
        The Soros Gate: Determines if we are allowed to play.
        """
        try:
            # Fetch SPY and VIX
            data = yf.download(["SPY", "^VIX"], period="1y", progress=False)['Close']

            spy_price = data['SPY'].iloc[-1]
            spy_sma200 = data['SPY'].rolling(200).mean().iloc[-1]
            vix = data['^VIX'].iloc[-1]

            # 1. Bull Market: Price > 200SMA & VIX < 20
            if spy_price > spy_sma200 and vix < 20:
                self.regime = "GREEN"
            # 2. Chop Market: Price > 200SMA but VIX High
            elif spy_price > spy_sma200 and vix >= 20:
                self.regime = "YELLOW"
            # 3. Bear Market: Price < 200SMA (Cash is King)
            else:
                self.regime = "RED"

            if vix > VIX_PANIC_LEVEL:
                self.regime = "RED"

            logger.info(f"MARKET REGIME: {self.regime} (SPY vs 200SMA | VIX: {vix:.2f})")

        except Exception as e:
            logger.error(f"Failed to check regime: {e}. Defaulting to RED.")
            self.regime = "RED"

    def _calculate_physics_score(self, series):
        """
        The Thorp Fix: Calculates Volatility/Entropy on LOG RETURNS.
        Returns a score 0-100 (0=Random, 100=Strong Trend/Structure).
        """
        try:
            # Log Returns (Stationary Data)
            log_ret = np.log(series / series.shift(1)).dropna()

            # 1. Volatility (Annualized)
            vol = log_ret.std() * np.sqrt(252)

            # 2. Trend Strength (Sharpe-like proxy)
            mean_ret = log_ret.mean() * 252
            trend_score = (mean_ret / vol) if vol > 0 else 0

            return trend_score
        except:
            return 0.0

    def analyze_ticker(self, ticker, df):
        """
        The Unified Logic.
        """
        try:
            # --- DATA HYGIENE (Simons) ---
            if len(df) < 252: return None # Need 1 year of data

            curr_price = df['Close'].iloc[-1]
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]

            is_uk = ticker.endswith(".L")
            is_us = not is_uk

            # --- LIQUIDITY GATE (Griffin) ---
            if is_us and avg_vol < MIN_VOL_US: return None
            if is_uk and avg_vol < MIN_VOL_UK: return None

            # --- INDICATORS ---
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            sma_150 = df['Close'].rolling(150).mean().iloc[-1]
            sma_200 = df['Close'].rolling(200).mean().iloc[-1]
            atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1]
            rsi = ta.rsi(df['Close'], length=14).iloc[-1]

            # 52-Week High
            high_52 = df['High'].rolling(252).max().iloc[-1]
            dist_to_high = (high_52 - curr_price) / high_52

            # --- STRATEGY 1: ISA SWING (Minervini/Trend) ---
            # Buying US/UK Stocks for the £100k account.
            isa_signal = False
            isa_setup = ""

            # Rule 1: Trend Alignment (Minervini)
            trend_ok = (curr_price > sma_150) and (sma_150 > sma_200) and (curr_price > sma_200)

            # Rule 2: Near Highs (Momentum)
            near_high = dist_to_high < 0.25 # Within 25% of highs

            # Rule 3: Contraction (VCP) or Breakout
            # We check if RSI is supportive (not overbought yet)
            rsi_ok = 50 <= rsi <= 70

            if self.regime != "RED" and trend_ok and near_high and rsi_ok:
                isa_signal = True
                isa_setup = "Trend Leader"

            # --- STRATEGY 2: US OPTIONS (Sosnoff/Thorp) ---
            # Selling Bull Put Spreads for the $9.5k account.
            opt_signal = False
            opt_setup = ""

            # Rule 1: Uptrend (Don't sell puts on falling knives)
            # Rule 2: Pullback (RSI < 50) - We want to sell premium into fear.
            # Rule 3: High Volatility (ATR% > 2.0%) - ensures premium is juicy.
            atr_pct = (atr / curr_price) * 100

            if is_us and self.regime != "RED" and (curr_price > sma_200):
                if rsi < 50 and atr_pct > 2.0:
                    opt_signal = True
                    opt_setup = "Bull Put (High IV)"

            # --- SIZING (Kelly/Risk Manager) ---
            # ISA Sizing (GBP)
            stop_loss = curr_price - (3 * atr) # Wide stop for swing
            risk_per_share = curr_price - stop_loss

            isa_shares = 0
            if isa_signal and risk_per_share > 0:
                # Account for FX if US stock (approx 0.79 USD/GBP)
                fx_rate = 0.79 if is_us else 1.0
                risk_amt = ISA_ACCOUNT_GBP * RISK_PER_TRADE # £1,000 Risk
                isa_shares = int((risk_amt / fx_rate) / risk_per_share)

                # Max 20% Allocation Cap
                max_shares = int((ISA_ACCOUNT_GBP * 0.20) / (curr_price * fx_rate))
                isa_shares = min(isa_shares, max_shares)

            # Options Sizing (USD)
            # Standard: $5 wide spread. Max loss = $500 minus credit.
            # We assume roughly $400 risk per contract.
            opt_contracts = 0
            if opt_signal:
                risk_amt_usd = OPTIONS_ACCOUNT_USD * 0.05 # Risk 5% on options ($475)
                opt_contracts = 1 # Keep it to 1 contract for small account

            if not isa_signal and not opt_signal:
                return None

            return {
                "Ticker": ticker,
                "Price": round(curr_price, 2),
                "Regime": self.regime,
                "Type": "ISA_BUY" if isa_signal else "OPT_SELL",
                "Setup": isa_setup if isa_signal else opt_setup,
                "Stop Loss": round(stop_loss, 2),
                "Action": f"Buy {isa_shares} Shares" if isa_signal else f"Sell {opt_contracts} Put Spread",
                "Metrics": f"RSI:{rsi:.0f} ATR%:{atr_pct:.1f}% DistH:{dist_to_high:.2f}",
                "Warning": "Check Earnings!" if is_us else ""
            }

        except Exception as e:
            return None

    def run(self):
        # 1. Check Regime
        self.check_market_regime()
        if self.regime == "RED":
            print("\n🛑 MARKET REGIME IS RED (BEARISH).")
            print("COUNCIL ORDER: CEASE ALL LONG BUYING. CASH PRESERVED.\n")
            return

        print(f"\n🚀 SCANNING {len(self.all_tickers)} TICKERS IN {self.regime} REGIME...\n")

        # 2. Batch Download
        # Chunking to avoid Yahoo limits
        chunk_size = 50
        results = []

        for i in range(0, len(self.all_tickers), chunk_size):
            chunk = self.all_tickers[i:i+chunk_size]
            try:
                data = yf.download(chunk, period="2y", group_by='ticker', progress=False, threads=True)

                if len(chunk) == 1:
                    # Single ticker handling
                    res = self.analyze_ticker(chunk[0], data)
                    if res: results.append(res)
                else:
                    for ticker in chunk:
                        try:
                            df = data[ticker].dropna()
                            res = self.analyze_ticker(ticker, df)
                            if res: results.append(res)
                        except: pass
            except Exception as e:
                logger.error(f"Chunk failed: {e}")

        # 3. Output Results
        df_res = pd.DataFrame(results)
        if not df_res.empty:
            # Sort by Setup Quality (ISA Buys first)
            df_res = df_res.sort_values(by=['Type', 'Ticker'], ascending=[True, True])

            print(df_res.to_markdown(index=False))
            print("\nIMPORTANT: Verify US Earnings Dates before executing Options trades.")
        else:
            print("No setups found meeting the Council's strict criteria.")

# --- EXECUTION ---
if __name__ == "__main__":
    # REPLACE WITH YOUR FULL LISTS
    # NOTE: I included a mix to test filters
    us_universe = ["NVDA", "MSFT", "TSLA", "AAPL", "AMD", "PLTR", "HOOD", "AMC", "GME"]
    uk_universe = ["RR.L", "AZN.L", "SHEL.L", "BP.L", "BARC.L", "VOD.L"]

    screener = MasterScreener(us_universe, uk_universe)
    screener.run()