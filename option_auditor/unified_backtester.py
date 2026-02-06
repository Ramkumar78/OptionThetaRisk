import pandas as pd
import logging
from option_auditor.monte_carlo_simulator import MonteCarloSimulator
from option_auditor.backtest_data_loader import BacktestDataLoader
from option_auditor.backtest_engine import BacktestEngine
from option_auditor.backtest_reporter import BacktestReporter
from option_auditor.config import BACKTEST_INITIAL_CAPITAL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UnifiedBacktester")

class UnifiedBacktester:
    def __init__(self, ticker, strategy_type="grandmaster", initial_capital=BACKTEST_INITIAL_CAPITAL, start_date=None, end_date=None):
        self.ticker = ticker.upper()
        self.strategy_type = strategy_type
        self.initial_capital = initial_capital
        self.start_date = start_date
        self.end_date = end_date

        # Components
        self.loader = BacktestDataLoader()
        self.engine = BacktestEngine(strategy_type, initial_capital)
        self.reporter = BacktestReporter()

        # Store last result for Monte Carlo
        self.last_trade_log = []

    def fetch_data(self):
        """Delegate data fetching to DataLoader."""
        # Calculate period based on start_date
        period = "10y"
        if self.start_date:
            try:
                s_dt = pd.Timestamp(self.start_date)
                limit_10y = pd.Timestamp.now() - pd.Timedelta(days=365*10)
                if s_dt < limit_10y:
                    period = "max"
            except:
                pass

        return self.loader.fetch_data(self.ticker, period=period)

    def calculate_indicators(self, df):
        """Delegate indicator calculation to Engine."""
        return self.engine.calculate_indicators(df)

    def run(self):
        """Orchestrate the backtest process."""
        df = self.fetch_data()
        if df is None: return {"error": "No data found"}
        if df.empty: return {"error": "Not enough history"}

        # Engine run handles indicator calculation and simulation loop
        # Pass date range to engine
        result = self.engine.run(df, start_date=self.start_date, end_date=self.end_date)

        if "error" in result:
            return result

        # Store trade log for Monte Carlo
        self.last_trade_log = result['trade_log']

        # Generate Report
        report = self.reporter.generate_report(
            result,
            self.ticker,
            self.strategy_type,
            self.initial_capital
        )

        return report

    def run_monte_carlo(self, simulations=10000):
        # Run backtest if not already run
        if not self.last_trade_log:
             result = self.run()
             if "error" in result:
                 return result

        if not self.last_trade_log:
             return {"error": "No trades generated in backtest."}

        # Reconstruct structured trades for MonteCarloSimulator
        structured_trades = []
        current_trade = {}
        for event in self.last_trade_log:
            if event['type'] == 'BUY':
                current_trade = {"buy_price": event['price']}
            elif event['type'] == 'SELL':
                if current_trade:
                    current_trade["sell_price"] = event['price']
                    if current_trade.get('buy_price', 0) > 0:
                        pnl = ((current_trade['sell_price'] - current_trade['buy_price']) / current_trade['buy_price']) * 100
                        current_trade["return_pct"] = round(pnl, 2)
                    structured_trades.append(current_trade)
                    current_trade = {}

        if not structured_trades:
             return {"error": "No completed trades to simulate."}

        mc = MonteCarloSimulator(structured_trades, self.initial_capital)
        return mc.run(simulations=simulations)
