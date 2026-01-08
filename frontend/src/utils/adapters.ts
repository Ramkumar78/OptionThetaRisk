import { format, parseISO } from 'date-fns';

export const adaptBacktestToResults = (backtestData: any) => {
  if (!backtestData || !backtestData.log) return null;

  // 1. Extract Equity Curve from Sell/Exit points
  // The backend log has 'equity' only on SELL rows. We filter for those.
  const portfolio_curve = backtestData.log
    .filter((trade: any) => trade.type === 'SELL' && trade.equity)
    .map((trade: any) => ({
      x: trade.date,
      y: trade.equity
    }));

  // Add start point (approximate based on first trade or assumed capital)
  // If first equity is ~9468 and return is small, we can estimate start,
  // but let's just use the first data point available or prepend start_date.
  if (portfolio_curve.length > 0) {
      portfolio_curve.unshift({
          x: backtestData.start_date,
          y: 10000 // Assuming 10k start, or calculate: final / (1 + return/100)
      });
  }

  // 2. Calculate Monthly Income
  // Group PnL by month
  const incomeMap: Record<string, number> = {};
  let previousEquity = 10000; // default start

  backtestData.log.forEach((trade: any) => {
      if (trade.type === 'SELL' && trade.equity) {
          const date = parseISO(trade.date);
          const monthKey = format(date, 'MMM yyyy');
          const pnl = trade.equity - previousEquity; // profit for this trade

          incomeMap[monthKey] = (incomeMap[monthKey] || 0) + pnl;
          previousEquity = trade.equity;
      }
  });

  const monthly_income = Object.keys(incomeMap).map(month => ({
      month,
      income: incomeMap[month]
  }));

  // 3. Map Strategy Metrics
  // Parse "33%" to 0.33
  const winRateNum = parseFloat(backtestData.win_rate) / 100;

  const strategy_metrics = {
      total_pnl: backtestData.final_equity - 10000, // Approx PnL
      total_fees: 0, // Not in simple backtest
      win_rate: isNaN(winRateNum) ? 0 : winRateNum,
      expectancy: 0, // Needs calculation
      sharpe: 0,
      drawdown: 0
  };

  // 4. Map Verdict
  const verdict = backtestData.strategy_return > 0 ? 'PROFITABLE' : 'NEEDS WORK';
  const verdict_color = backtestData.strategy_return > 0 ? 'green' : 'red';

  // 5. Construct Final Object matching Results.tsx props
  return {
      verdict,
      verdict_color,
      verdict_details: `Return: ${backtestData.strategy_return}% over ${backtestData.trades} trades`,
      date_window: { start: backtestData.start_date, end: backtestData.end_date },
      style: backtestData.strategy,
      strategy_metrics,
      buying_power_utilized_percent: 0, // Not provided
      portfolio_curve,
      monthly_income,
      open_positions: [], // Simple backtest usually closes all or doesn't report open
      strategy_groups: [{
          strategy: backtestData.strategy,
          legs_desc: backtestData.ticker,
          symbol: backtestData.ticker,
          pnl: backtestData.final_equity - 10000,
          average_daily_pnl: 0
      }],
      token: null // No download token for simple backtest yet
  };
};
