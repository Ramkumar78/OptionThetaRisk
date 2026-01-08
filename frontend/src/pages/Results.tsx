import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';
import { formatCurrency, getCurrencySymbol } from '../utils/formatting';

// REGISTER CHARTS (Critical to prevent blank screen)
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler
);

interface ResultsProps {
  directData?: any;
}

const Results: React.FC<ResultsProps> = ({ directData }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    let rawData = directData || location.state?.results;

    if (!rawData) {
      return; // Data not ready yet
    }

    // --- AUTO-ADAPTER: Fix Simple JSON to Complex Format ---
    // If we have 'log' but NO 'strategy_metrics', it's the Simple Backtest format.
    if (rawData.log && !rawData.strategy_metrics) {
      console.log("Adapting Simple Backtest Data...");

      // 1. Calculate Equity Curve
      const curve = [];
      // Add start point
      curve.push({ x: rawData.start_date, y: 10000 }); // Assume 10k start

      rawData.log.forEach((trade: any) => {
        if (trade.type === 'SELL' && trade.equity) {
          curve.push({ x: trade.date, y: trade.equity });
        }
      });

      // 2. Calculate Monthly Income (Simple approximation)
      const incomeMap: Record<string, number> = {};
      let prevEquity = 10000;
      rawData.log.forEach((trade: any) => {
        if (trade.type === 'SELL' && trade.equity) {
           const dateObj = new Date(trade.date);
           const monthKey = dateObj.toLocaleString('default', { month: 'short', year: 'numeric' });
           const pnl = trade.equity - prevEquity;
           incomeMap[monthKey] = (incomeMap[monthKey] || 0) + pnl;
           prevEquity = trade.equity;
        }
      });
      const monthlyIncome = Object.keys(incomeMap).map(m => ({ month: m, income: incomeMap[m] }));

      // 3. Construct Metrics
      const winRateStr = String(rawData.win_rate || "0").replace('%', '');

      rawData = {
        ...rawData,
        verdict: rawData.strategy_return > 0 ? "PROFITABLE" : "NEEDS WORK",
        verdict_color: rawData.strategy_return > 0 ? "green" : "red",
        verdict_details: `Return: ${rawData.strategy_return}% | Trades: ${rawData.trades}`,
        date_window: { start: rawData.start_date, end: rawData.end_date },
        style: rawData.strategy,

        strategy_metrics: {
          total_pnl: rawData.final_equity - 10000,
          win_rate: parseFloat(winRateStr) / 100,
          profit_factor: rawData.profit_factor || 0,
          drawdown: 0, // Not calculated in simple mode
          sharpe: 0    // Not calculated in simple mode
        },
        portfolio_curve: curve,
        monthly_income: monthlyIncome,
        strategy_groups: [{
          strategy: rawData.strategy,
          legs_desc: rawData.ticker,
          symbol: rawData.ticker,
          pnl: rawData.final_equity - 10000
        }]
      };
    }
    // -------------------------------------------------------

    setData(rawData);
  }, [directData, location.state]);

  if (!data) {
    return (
      <div className="p-8 text-center text-gray-500">
        <p>No results found. Run a backtest first.</p>
        <button onClick={() => navigate('/screener')} className="mt-4 text-blue-600 font-bold hover:underline">
          Go to Screener
        </button>
      </div>
    );
  }

  // --- HELPER ---
  const currencySymbol = getCurrencySymbol(data.ticker || (data.strategy_groups && data.strategy_groups[0]?.symbol) || '');

  // --- CHART CONFIGURATION ---
  const curveChartData = {
    datasets: [{
      label: 'Portfolio Equity',
      data: data.portfolio_curve || [],
      borderColor: '#2563eb',
      backgroundColor: 'rgba(37, 99, 235, 0.1)',
      fill: true,
      tension: 0.2,
      pointRadius: 2,
    }]
  };

  const incomeChartData = {
    labels: data.monthly_income?.map((m: any) => m.month) || [],
    datasets: [{
      label: 'Monthly PnL',
      data: data.monthly_income?.map((m: any) => m.income) || [],
      backgroundColor: (context: any) => {
        const val = context.raw;
        return val >= 0 ? '#16a34a' : '#dc2626';
      },
      borderRadius: 4,
    }]
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700 mb-2 flex items-center gap-2">
            <i className="bi bi-arrow-left"></i> Back
          </button>
          <h1 className="text-3xl font-black text-gray-900 dark:text-white">
            AUDIT <span className="text-blue-600">RESULTS</span>
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {data.date_window?.start} to {data.date_window?.end} • {data.style}
          </p>
        </div>

        <div className={`px-6 py-3 rounded-xl shadow-sm border-l-4 ${data.verdict_color === 'green' ? 'bg-green-50 border-green-500' : 'bg-red-50 border-red-500'}`}>
          <p className="text-xs font-bold uppercase tracking-wider text-gray-500">Verdict</p>
          <p className={`text-2xl font-black ${data.verdict_color === 'green' ? 'text-green-700' : 'text-red-700'}`}>
            {data.verdict}
          </p>
          <p className="text-sm text-gray-600 mt-1">{data.verdict_details}</p>
        </div>
      </div>

      {/* METRICS GRID */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white dark:bg-gray-800 p-5 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
          <p className="text-xs font-bold text-gray-500 uppercase">Total PnL</p>
          <p className={`text-2xl font-mono font-bold ${data.strategy_metrics?.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(data.strategy_metrics?.total_pnl || 0, currencySymbol)}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-5 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
          <p className="text-xs font-bold text-gray-500 uppercase">Win Rate</p>
          <p className="text-2xl font-mono font-bold text-gray-900 dark:text-white">
            {((data.strategy_metrics?.win_rate || 0) * 100).toFixed(1)}%
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-5 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
          <p className="text-xs font-bold text-gray-500 uppercase">Trades</p>
          <p className="text-2xl font-mono font-bold text-gray-900 dark:text-white">
            {data.trades || data.total_trades || 0}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 p-5 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
          <p className="text-xs font-bold text-gray-500 uppercase">Profit Factor</p>
          <p className="text-2xl font-mono font-bold text-gray-900 dark:text-white">
            {data.strategy_metrics?.profit_factor?.toFixed(2) || 'N/A'}
          </p>
        </div>
      </div>

      {/* CHARTS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 h-[400px]">
          <h3 className="font-bold text-gray-800 dark:text-white mb-4">Equity Curve</h3>
          <div className="h-[320px] w-full">
             <Line data={curveChartData} options={{ maintainAspectRatio: false, responsive: true, scales: { x: { type: 'time', time: { unit: 'month' } } } }} />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 h-[400px]">
          <h3 className="font-bold text-gray-800 dark:text-white mb-4">Monthly Income</h3>
          <div className="h-[320px] w-full">
            <Bar data={incomeChartData} options={{ maintainAspectRatio: false, responsive: true }} />
          </div>
        </div>
      </div>

      {/* TRADE LOG */}
      {data.log && data.log.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700">
            <h3 className="font-bold text-gray-800 dark:text-white">Trade Log</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 uppercase text-xs">
                <tr>
                  <th className="px-6 py-3">Date</th>
                  <th className="px-6 py-3">Type</th>
                  <th className="px-6 py-3 text-right">Price</th>
                  <th className="px-6 py-3">Reason / Details</th>
                  <th className="px-6 py-3 text-right">Equity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {data.log.map((trade: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-6 py-3 font-mono">{trade.date}</td>
                    <td className="px-6 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${
                        trade.type === 'BUY' ? 'bg-blue-100 text-blue-800' :
                        trade.type === 'SELL' ? 'bg-gray-100 text-gray-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {trade.type}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-right font-mono">{formatCurrency(trade.price, currencySymbol)}</td>
                    <td className="px-6 py-3 text-gray-600">{trade.reason || trade.stop ? `Stop: ${trade.stop}` : '-'}</td>
                    <td className="px-6 py-3 text-right font-mono font-bold">
                      {trade.equity ? formatCurrency(trade.equity, currencySymbol) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Results;