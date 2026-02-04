import React, { useState } from 'react';
import { runBacktest } from '../api';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface Trade {
  buy_date: string;
  buy_price: number;
  sell_date?: string;
  sell_price?: number;
  return_pct?: number;
  reason?: string;
  days_held?: number;
}

interface BacktestResult {
  ticker: string;
  strategy: string;
  start_date: string;
  end_date: string;
  strategy_return: number;
  buy_hold_return: number;
  buy_hold_return_pct: number;
  trades: number;
  win_rate: string;
  final_equity: number;
  trade_list: Trade[];
  equity_curve: { date: string; strategy_equity: number; buy_hold_equity: number }[];
  equity_curves?: { date: string; strategy_equity: number; buy_hold_equity: number }[];
  total_days_held: number;
}

const Backtester: React.FC = () => {
  const [ticker, setTicker] = useState('SPY');
  const [strategy, setStrategy] = useState('master');
  const [initialCapital, setInitialCapital] = useState(10000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const strategies = [
    { value: 'master', label: 'Master Convergence (Trend)' },
    { value: 'turtle', label: 'Turtle (Trend)' },
    { value: 'isa', label: 'ISA Trend' },
    { value: 'market', label: 'Market (RSI Dip)' },
    { value: 'ema', label: 'EMA Cross (5/13)' },
    { value: 'darvas', label: 'Darvas Box' },
    { value: 'mms', label: 'MMS / OTE' },
    { value: 'bull_put', label: 'Bull Put (Credit)' },
    { value: 'hybrid', label: 'Hybrid (Fourier+RSI)' },
    { value: 'fortress', label: 'Fortress (Safe)' },
    { value: 'quantum', label: 'Quantum (Volatility)' },
    { value: 'alpha101', label: 'Alpha101 (Mean Rev)' },
    { value: 'liquidity_grab', label: 'Liquidity Grab (SMC)' },
    { value: 'rsi_divergence', label: 'RSI Divergence' },
  ];

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await runBacktest(ticker, strategy, initialCapital);
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.error || err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Visual Strategy Backtester</h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          Validate your edge before risking capital. Run historical simulations to visualize performance vs Buy & Hold.
        </p>

        <form onSubmit={handleRun} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label htmlFor="ticker-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ticker</label>
            <input
              id="ticker-input"
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              placeholder="e.g. SPY"
              required
            />
          </div>

          <div>
            <label htmlFor="strategy-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Strategy</label>
            <select
              id="strategy-select"
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              {strategies.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="capital-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Initial Capital ($)</label>
            <input
              id="capital-input"
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Number(e.target.value) || 10000)}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              min="1000"
              step="1000"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg shadow-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Running...
              </>
            ) : (
              'Run Backtest'
            )}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg">
            ⚠️ {error}
          </div>
        )}
      </div>

      {result && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card
              label="Total Return"
              value={`${result.strategy_return}%`}
              color={result.strategy_return > 0 ? "green" : "red"}
              desc={`vs Buy & Hold: ${result.buy_hold_return}%`}
            />
             <Card
              label="Final Equity"
              value={`$${result.final_equity.toLocaleString()}`}
              color="blue"
              desc={`Started: $${initialCapital.toLocaleString()}`}
            />
            <Card
              label="Win Rate"
              value={result.win_rate}
              color="orange"
              desc={`${result.trades} Trades`}
            />
             <Card
              label="Avg Days Held"
              value={`${result.trades > 0 ? Math.round(result.total_days_held / result.trades) : 0}`}
              color="gray"
              desc="Time in Market"
            />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Equity Curve</h3>
            <div className="h-96 w-full">
               <Line
                  data={{
                      labels: result.equity_curves ? result.equity_curves.map(x => x.date) : result.equity_curve.map(x => x.date), // Fallback if API structure differs
                      datasets: [
                          {
                              label: `Strategy (${result.strategy})`,
                              data: result.equity_curves ? result.equity_curves.map(x => x.strategy_equity) : result.equity_curve.map(x => x.strategy_equity),
                              borderColor: 'rgba(34, 197, 94, 1)', // green-500
                              backgroundColor: 'rgba(34, 197, 94, 0.1)',
                              borderWidth: 2,
                              pointRadius: 0,
                              fill: true,
                          },
                          {
                              label: 'Buy & Hold',
                              data: result.equity_curves ? result.equity_curves.map(x => x.buy_hold_equity) : result.equity_curve.map(x => x.buy_hold_equity),
                              borderColor: 'rgba(156, 163, 175, 0.8)', // gray-400
                              borderWidth: 2,
                              borderDash: [5, 5],
                              pointRadius: 0,
                              fill: false,
                          }
                      ]
                  }}
                  options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      interaction: { mode: 'index', intersect: false },
                      scales: {
                          x: { grid: { display: false } },
                          y: { grid: { color: 'rgba(0, 0, 0, 0.05)' } }
                      },
                      plugins: {
                          tooltip: {
                              callbacks: {
                                  label: (ctx) => `${ctx.dataset.label}: $${Number(ctx.raw).toLocaleString()}`
                              }
                          }
                      }
                  }}
               />
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700 overflow-hidden">
             <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Trade Log</h3>
             <div className="overflow-x-auto">
               <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                 <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                   <tr>
                     <th className="px-6 py-3">Entry Date</th>
                     <th className="px-6 py-3">Entry Price</th>
                     <th className="px-6 py-3">Exit Date</th>
                     <th className="px-6 py-3">Exit Price</th>
                     <th className="px-6 py-3">Result</th>
                     <th className="px-6 py-3">Reason</th>
                   </tr>
                 </thead>
                 <tbody>
                   {result.trade_list.map((trade, idx) => (
                     <tr key={idx} className="bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600">
                       <td className="px-6 py-4">{trade.buy_date}</td>
                       <td className="px-6 py-4">${trade.buy_price.toFixed(2)}</td>
                       <td className="px-6 py-4">{trade.sell_date || '-'}</td>
                       <td className="px-6 py-4">{trade.sell_price ? `$${trade.sell_price.toFixed(2)}` : '-'}</td>
                       <td className={`px-6 py-4 font-bold ${(trade.return_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                         {trade.return_pct ? `${trade.return_pct}%` : '-'}
                       </td>
                       <td className="px-6 py-4">{trade.reason || 'Holding'}</td>
                     </tr>
                   ))}
                   {result.trade_list.length === 0 && (
                      <tr>
                          <td colSpan={6} className="px-6 py-4 text-center">No trades generated.</td>
                      </tr>
                   )}
                 </tbody>
               </table>
             </div>
          </div>
        </div>
      )}
    </div>
  );
};

const Card = ({ label, value, color, desc }: { label: string, value: string, color: string, desc: string }) => {
    const colorClasses: Record<string, string> = {
        red: "text-red-600 dark:text-red-400",
        green: "text-emerald-600 dark:text-emerald-400",
        blue: "text-blue-600 dark:text-blue-400",
        orange: "text-orange-600 dark:text-orange-400",
        gray: "text-gray-900 dark:text-white"
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</h3>
            <div className={`text-2xl font-bold mt-2 ${colorClasses[color] || colorClasses.gray}`}>
                {value}
            </div>
            <p className="text-xs text-gray-400 mt-2">{desc}</p>
        </div>
    );
};

export default Backtester;
