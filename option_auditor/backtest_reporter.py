from typing import Dict, Any, List
import pandas as pd
import logging

logger = logging.getLogger("BacktestReporter")

class BacktestReporter:
    def generate_report(self, engine_result: Dict[str, Any], ticker: str, strategy_type: str, initial_capital: float) -> Dict[str, Any]:
        """
        Generates the final backtest report based on engine results.
        """
        # Unpack engine result
        sim_data = engine_result['sim_data']
        trade_log = engine_result['trade_log']
        equity_curve = engine_result['equity_curve']
        final_equity = engine_result['final_equity']
        bnh_final_value = engine_result['bnh_final_value']
        initial_price = engine_result['initial_price']
        final_price = engine_result['final_price']
        buy_hold_days = engine_result['buy_hold_days']

        actual_start_str = sim_data.index[0].strftime('%Y-%m-%d')
        actual_end_str = sim_data.index[-1].strftime('%Y-%m-%d')

        # Calculate Returns
        strat_return = ((final_equity - initial_capital) / initial_capital) * 100

        # Simple B&H Return (Price only)
        simple_bnh_return = ((final_price - initial_price) / initial_price) * 100

        # B&H Equity Return
        bnh_return_equity = ((bnh_final_value - initial_capital) / initial_capital) * 100

        # Trade Stats
        sell_trades = [t['days'] for t in trade_log if t['type'] == 'SELL' and isinstance(t['days'], int)]
        avg_days_held = round(sum(sell_trades) / len(sell_trades)) if sell_trades else 0
        total_days_held = sum(sell_trades)

        structured_trades = []
        current_trade = {}

        for event in trade_log:
            if event['type'] == 'BUY':
                current_trade = {
                    "buy_date": event['date'],
                    "buy_price": event['price'],
                    "stop_loss": event.get('stop'),
                    "target": event.get('target', 'Trailing')
                }
            elif event['type'] == 'SELL':
                if current_trade:
                    current_trade["sell_date"] = event['date']
                    current_trade["sell_price"] = event['price']
                    current_trade["reason"] = event['reason']
                    current_trade["days_held"] = event['days']

                    if current_trade.get('buy_price', 0) > 0:
                        pnl = ((current_trade['sell_price'] - current_trade['buy_price']) / current_trade['buy_price']) * 100
                        current_trade["return_pct"] = round(pnl, 2)

                    structured_trades.append(current_trade)
                    current_trade = {}

        return {
            "ticker": ticker,
            "strategy": strategy_type.upper(),
            "start_date": actual_start_str,
            "end_date": actual_end_str,
            "strategy_return": round(strat_return, 2),
            "buy_hold_return": round(bnh_return_equity, 2),
            "buy_hold_return_pct": round(simple_bnh_return, 2),
            "buy_hold_days": buy_hold_days,
            "avg_days_held": avg_days_held,
            "total_days_held": total_days_held,
            "trades": len(trade_log) // 2,
            "win_rate": self._calculate_win_rate(trade_log),
            "final_equity": round(final_equity, 2),
            "log": trade_log,
            "trade_list": structured_trades,
            "equity_curve": equity_curve
        }

    def _calculate_win_rate(self, trade_log: List[Dict[str, Any]]) -> str:
        wins = 0; losses = 0; entry = 0
        for t in trade_log:
            if t['type'] == 'BUY': entry = t['price']
            if t['type'] == 'SELL':
                if t['price'] > entry: wins += 1
                else: losses += 1
        total = wins + losses
        if total == 0: return "0%"
        return f"{round((wins/total)*100)}%"
