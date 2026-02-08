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
    def __init__(self, ticker, strategy_type="grandmaster", initial_capital=BACKTEST_INITIAL_CAPITAL,
                 slippage_type="fixed_pct", slippage_value=0.0, impact_factor=0.0,
                 margin_interest_rate=0.0, leverage_limit=1.0):
        self.ticker = ticker.upper()
        self.strategy_type = strategy_type
        self.initial_capital = initial_capital

        # Components
        self.loader = BacktestDataLoader()
        self.engine = BacktestEngine(strategy_type, initial_capital,
                                     slippage_type, slippage_value, impact_factor,
                                     margin_interest_rate, leverage_limit)
        self.reporter = BacktestReporter()

        # Store last result for Monte Carlo
        self.last_trade_log = []

    def fetch_data(self):
        """Delegate data fetching to DataLoader."""
        return self.loader.fetch_data(self.ticker)

    def calculate_indicators(self, df):
        """Delegate indicator calculation to Engine."""
        return self.engine.calculate_indicators(df)

    def run(self, monte_carlo=False):
        """Orchestrate the backtest process."""
        df = self.fetch_data()
        if df is None: return {"error": "No data found"}
        if df.empty: return {"error": "Not enough history"}

        # Engine run handles indicator calculation and simulation loop
        result = self.engine.run(df)

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

        # Optional: Monte Carlo Wrapper
        if monte_carlo:
            mc_results = self.run_monte_carlo()
            report["monte_carlo"] = mc_results

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
