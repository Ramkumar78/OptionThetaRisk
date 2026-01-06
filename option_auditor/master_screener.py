import sys
import datetime
import logging
import warnings
from typing import List, Dict, Optional

# --- 1. Numerical & Data Computing ---
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm

# --- 2. Visualization ---
import matplotlib.pyplot as plt
import seaborn as sns

# --- 3. Machine Learning ---
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
# try:
#     from pycaret.classification import load_model, predict_model
# except ImportError:
#     pass  # Handle if PyCaret is too heavy to load initially

# --- 4. Finance & Risk Ecosystem ---
try:
    from openbb import obb  # OpenBB SDK for data
except ImportError:
    print("OpenBB SDK not found. Using mock data.")
    obb = None

try:
    import riskfolio as rp  # For portfolio optimization/risk
except ImportError:
    pass

# try:
#     import alphalens
#     import pyfolio
#     import zipline
# except ImportError:
#     pass

# --- 5. Execution/Live Data ---
try:
    from ib_insync import IB, Stock, util
except ImportError:
    pass

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuantMasterScreener:
    """
    Advanced Screener integrating OpenBB, ML, and Risk Engines.
    """

    def __init__(self, use_ibkr=False):
        self.results = pd.DataFrame()
        self.use_ibkr = use_ibkr

        # Initialize IBKR if required
        if self.use_ibkr:
            try:
                self.ib = IB()
                self.ib.connect('127.0.0.1', 7497, clientId=1)
                logger.info("Connected to IBKR.")
            except Exception as e:
                logger.error(f"Could not connect to IBKR: {e}")
                self.use_ibkr = False

    def fetch_data_openbb(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
        """
        Uses OpenBB to fetch robust historical data.
        """
        if obb is None:
            logger.warning("OpenBB SDK not available. Skipping data fetch.")
            return pd.DataFrame()

        start_date = (datetime.datetime.now() - datetime.timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        try:
            # Using OpenBB v4+ syntax (check documentation for specific version changes)
            # obb.equity.price.historical returns an OBBject, we need to convert to df
            # The user code had .to_df(), which works on OBBject
            df = obb.equity.price.historical(symbol=symbol, start_date=start_date, provider="yfinance").to_df()
            # Ensure columns are lower case for consistency with analysis logic
            df.columns = [c.lower() for c in df.columns]
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def analyze_statistical_features(self, df: pd.DataFrame) -> Dict:
        """
        Uses SciPy and Statsmodels for advanced statistical metrics.
        """
        if df.empty:
            return {}

        # Ensure 'close' exists
        if 'close' not in df.columns:
            return {}

        closes = df['close'].values
        returns = df['close'].pct_change().dropna()

        if len(returns) < 2:
            return {}

        # 1. Normality Test (SciPy)
        # null hypothesis: x comes from a normal distribution
        k2, p_value = stats.normaltest(returns)
        is_normal = p_value > 0.05

        # 2. Augmented Dickey-Fuller Test for Stationarity (Statsmodels)
        try:
            adf_result = sm.tsa.stattools.adfuller(returns)
            is_stationary = adf_result[1] < 0.05
        except Exception:
            is_stationary = False

        # 3. Volatility (Numpy/Pandas)
        hist_vol = returns.std() * np.sqrt(252)

        return {
            "is_return_normal": is_normal,
            "is_stationary": is_stationary,
            "annualized_volatility": hist_vol,
            "skewness": stats.skew(returns),
            "kurtosis": stats.kurtosis(returns)
        }

    def generate_ml_signal(self, df: pd.DataFrame) -> float:
        """
        Uses Scikit-Learn to generate a simple predictive signal (prob of up move).
        Can be replaced with PyCaret model inference.
        """
        if len(df) < 50:
            return 0.5

        data = df.copy()
        data['Returns'] = data['close'].pct_change()
        data['SMA_50'] = data['close'].rolling(50).mean()
        data['Dist_SMA'] = data['close'] / data['SMA_50'] - 1
        data['Target'] = (data['Returns'].shift(-1) > 0).astype(int)

        # Features needed for prediction
        features = ['Dist_SMA', 'volume']

        # Capture the latest available data point (which has no target yet) for prediction
        # We need to handle potential NaNs in features if window is large, but Dist_SMA uses 50
        # If last row has NaN features, we can't predict well.
        if data.iloc[-1][features].isna().any():
             return 0.5

        last_row_features = data.iloc[[-1]][features]

        # Prepare Training Data: Drop rows with NaN targets (the last row and maybe others)
        # We also need to drop rows with NaN features from the start
        train_data = data.dropna(subset=['Target'] + features)

        if train_data.empty or len(train_data) < 10:
            return 0.5

        X_train = train_data[features]
        y_train = train_data['Target']

        # Simple random forest train/predict
        model = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
        model.fit(X_train, y_train)

        # Predict probability for the LATEST available data (forecasting tomorrow)
        try:
            prob_up = model.predict_proba(last_row_features)[0][1]
        except:
            prob_up = 0.5

        return prob_up

    def assess_portfolio_risk(self, symbol: str, current_portfolio: List[str]):
        """
        Uses Riskfolio-Lib to check if adding this asset reduces or increases portfolio risk.
        """
        # Placeholder: In a real scenario, you fetch returns for all tickers in current_portfolio + symbol
        # data = fetch_combined_data(current_portfolio + [symbol])

        # Example Riskfolio usage (HRP - Hierarchical Risk Parity)
        # port = rp.Portfolio(returns=data)
        # w = port.optimization(model='HRP', rm='MV', rf=0.05, linkage='single', leaf_order=True)
        # return w
        pass

    def run_screen(self, ticker_list: List[str]):
        """
        Master execution loop.
        """
        # Note: IBKR execution logic would go here if enabled (self.use_ibkr)
        # Currently defaults to data analysis via OpenBB only.

        screen_results = []

        for ticker in ticker_list:
            logger.info(f"Processing {ticker}...")

            # 1. Fetch Data (OpenBB)
            df = self.fetch_data_openbb(ticker)
            if df.empty:
                continue

            # 2. Statistical Analysis (SciPy/Statsmodels)
            stats_metrics = self.analyze_statistical_features(df)

            # 3. ML Prediction (Sklearn)
            ml_score = self.generate_ml_signal(df)

            # 4. Filter Logic
            # Example: We only want stationary returns with > 60% ML probability
            # Relaxed filter for demo purposes if nothing passes
            if ml_score > 0.60:
                result_row = {
                    "Ticker": ticker,
                    "Price": df['close'].iloc[-1],
                    "ML_Prob_Up": ml_score,
                    **stats_metrics
                }
                screen_results.append(result_row)
            else:
                 # Optional: log rejected candidates
                 pass

        self.results = pd.DataFrame(screen_results)
        return self.results

    def visualize_results(self):
        """
        Uses Seaborn/Matplotlib to visualize the screened candidates.
        """
        if self.results.empty:
            print("No results to visualize.")
            return

        plt.figure(figsize=(10, 6))
        # Ensure columns exist before plotting
        if "annualized_volatility" in self.results.columns and "ML_Prob_Up" in self.results.columns:
            sns.scatterplot(
                data=self.results,
                x="annualized_volatility",
                y="ML_Prob_Up",
                hue="Ticker",
                s=100
            )
            plt.title("Screener Candidates: Volatility vs ML Confidence")
            plt.axhline(0.5, color='red', linestyle='--')

            # Save plot to file instead of showing (headless env)
            plt.savefig("screener_results.png")
            print("Visualization saved to screener_results.png")
            plt.close() # Close to free memory

# --- Backtesting & Research Environment Hooks ---
def run_research_pipeline():
    """
    Hook to run Zipline/Alphalens analysis.
    This is usually run offline in a Jupyter environment.
    """
    # import alphalens
    # alphalens.tears.create_full_tear_sheet(factor_data)
    print("Research pipeline triggers (Alphalens/Pyfolio) would execute here.")

if __name__ == "__main__":
    # Example usage
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMD"]

    screener = QuantMasterScreener(use_ibkr=False)
    results = screener.run_screen(tickers)

    print("\n--- Screening Results ---")
    print(results)

    screener.visualize_results()
