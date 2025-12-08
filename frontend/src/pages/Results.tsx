import React from 'react';
import { useLocation } from 'react-router-dom';
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
import clsx from 'clsx';
import { formatCurrency, getCurrencySymbol } from '../utils/formatting';

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

const Results: React.FC = () => {
  const location = useLocation();
  const results = location.state?.results;
  const isDark = document.documentElement.classList.contains('dark'); // Initial check, might need context for reactivity

  if (!results) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold text-gray-700 dark:text-gray-300">No results to display.</h2>
        <p className="text-gray-500">Please run an audit first.</p>
      </div>
    );
  }

  const {
    verdict,
    verdict_color,
    verdict_details,
    date_window,
    style,
    strategy_metrics,
    buying_power_utilized_percent,
    portfolio_curve,
    monthly_income,
    open_positions,
    strategy_groups,
    token
  } = results;

  // Chart Config
  const textColor = isDark ? '#94a3b8' : '#64748b';
  const gridColor = isDark ? '#334155' : '#e2e8f0';

  const portfolioChartData = {
    datasets: [{
      label: 'Cumulative Net PnL',
      data: portfolio_curve, // Assuming [{x: date, y: value}] format from backend
      borderColor: '#4f46e5',
      backgroundColor: 'rgba(79, 70, 229, 0.05)',
      borderWidth: 3,
      fill: true,
      tension: 0.2,
      pointRadius: 0,
      pointHoverRadius: 6,
      pointBackgroundColor: '#4f46e5'
    }]
  };

  const incomeChartData = {
    labels: monthly_income.map((d: any) => d.month),
    datasets: [{
      label: 'Net Income',
      data: monthly_income.map((d: any) => d.income),
      backgroundColor: monthly_income.map((d: any) => d.income >= 0 ? '#10b981' : '#f43f5e'),
      borderRadius: 4,
    }]
  };

  const chartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'nearest', axis: 'x', intersect: false },
    scales: {
      x: {
        grid: { color: gridColor, drawBorder: false },
        ticks: { color: textColor }
      },
      y: {
        grid: { color: gridColor, drawBorder: false },
        ticks: { color: textColor, callback: (val: number) => formatCurrency(val, '$') } // Default to $ for charts for now as mixed currency charts are complex
      }
    },
    plugins: {
      legend: { display: false }
    }
  };

  const portfolioOptions = {
      ...chartOptions,
      scales: {
          ...chartOptions.scales,
          x: {
              ...chartOptions.scales.x,
              type: 'time',
              time: { unit: 'day', displayFormats: { day: 'MMM d' } }
          }
      }
  };

  return (
    <div className="space-y-8 animate-fade-in">
       {/* Verdict Card */}
       <div className="relative overflow-hidden rounded-2xl shadow-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 md:p-8">
           <div className={clsx(
             "absolute top-0 right-0 -mt-20 -mr-20 w-80 h-80 rounded-full blur-3xl opacity-20",
             verdict_color === 'red' ? "bg-red-500" : verdict_color === 'yellow' ? "bg-yellow-500" : "bg-emerald-500"
           )}></div>

           <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div>
                 <p className="text-sm font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">Strategy Audit Verdict</p>
                 <h2 id="verdict-text" className={clsx(
                   "text-4xl md:text-5xl font-extrabold tracking-tight",
                   verdict_color === 'red' ? "text-red-600 dark:text-red-500" : verdict_color === 'yellow' ? "text-yellow-600 dark:text-yellow-500" : "text-emerald-600 dark:text-emerald-500"
                 )}>{verdict}</h2>
                 {verdict_details && (
                   <div className="mt-3 inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200">
                      ℹ️ {verdict_details}
                   </div>
                 )}
              </div>

              <div className="flex flex-col items-end">
                 {date_window && (
                    <div className="text-right">
                        <span className="block text-xs text-gray-400 uppercase">Analysis Period</span>
                        <span className="font-mono text-sm text-gray-700 dark:text-gray-300">{date_window.start} — {date_window.end}</span>
                    </div>
                 )}
                 <div className="mt-4">
                     <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-300 capitalize">
                        {style || 'Standard'} Profile
                     </span>
                 </div>
              </div>
           </div>
       </div>

       {/* Bento Grid Metrics */}
       <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
           <MetricCard title="Net PnL" value={strategy_metrics.total_pnl} isCurrency subValue={`Fees: $${Math.round(strategy_metrics.total_fees)}`} color={strategy_metrics.total_pnl < 0 ? 'red' : 'emerald'} icon="💰" />
           <MetricCard title="Win Rate" value={strategy_metrics.win_rate * 100} suffix="%" subValue={<ProgressBar value={strategy_metrics.win_rate * 100} />} color="blue" icon="🎯" />
           <MetricCard title="Expectancy / Trade" value={strategy_metrics.expectancy} isCurrency color={strategy_metrics.expectancy < 0 ? 'red' : 'emerald'} icon="📈" />
           <MetricCard title="BP Usage" value={buying_power_utilized_percent || 0} suffix="%" subValue="Target: < 50%" color={buying_power_utilized_percent > 75 ? 'red' : 'gray'} icon="🔋" />
       </div>

       {/* Charts */}
       <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-900 p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800">
               <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Equity Curve</h3>
               <div className="h-64 w-full">
                  <Line data={portfolioChartData} options={portfolioOptions} />
               </div>
          </div>
          <div className="bg-white dark:bg-gray-900 p-6 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800">
               <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Monthly Income</h3>
               <div className="h-64 w-full">
                  <Bar data={incomeChartData} options={chartOptions} />
               </div>
          </div>
       </div>

       {/* Open Positions */}
       <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-800/50">
              <h3 className="font-bold text-gray-900 dark:text-white">Active Positions</h3>
              <span className="bg-primary-100 text-primary-800 text-xs font-medium px-2.5 py-0.5 rounded dark:bg-primary-900 dark:text-primary-300">{open_positions.length} Open</span>
          </div>
          <div className="overflow-x-auto">
             <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                 <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                     <tr>
                         <th className="px-6 py-3">Symbol</th>
                         <th className="px-6 py-3 text-right">Price</th>
                         <th className="px-6 py-3 text-center">Expiry</th>
                         <th className="px-6 py-3 text-right">Qty</th>
                         <th className="px-6 py-3 text-right">DTE</th>
                         <th className="px-6 py-3 text-center">Status</th>
                     </tr>
                 </thead>
                 <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                     {open_positions.length === 0 ? (
                         <tr><td colSpan={6} className="px-6 py-8 text-center italic">No active positions.</td></tr>
                     ) : (
                         open_positions.map((p: any, idx: number) => {
                             const currency = getCurrencySymbol(p.symbol);
                             return (
                                 <tr key={idx} className="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                     <td className="px-6 py-4 font-bold text-gray-900 dark:text-white">{p.symbol}</td>
                                     <td className="px-6 py-4 text-right">{formatCurrency(p.current_price, currency)}</td>
                                     <td className="px-6 py-4 text-center">{p.expiry}</td>
                                     <td className={clsx("px-6 py-4 text-right font-mono", p.qty_open < 0 ? "text-red-500" : "text-emerald-500")}>{Math.round(p.qty_open)}</td>
                                     <td className="px-6 py-4 text-right">
                                        <span className={clsx(p.dte < 5 && "text-red-500 font-bold")}>{p.dte !== null ? `${p.dte}d` : '-'}</span>
                                     </td>
                                     <td className="px-6 py-4 text-center">
                                        {p.risk_alert ? (
                                            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">{p.risk_alert}</span>
                                        ) : (
                                            <span className="text-emerald-600 dark:text-emerald-400 text-xs">OK</span>
                                        )}
                                     </td>
                                 </tr>
                             );
                         })
                     )}
                 </tbody>
             </table>
          </div>
       </div>

       {/* Strategy Performance */}
       <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
               <h3 className="font-bold text-gray-900 dark:text-white">Strategy Performance</h3>
          </div>
          <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                  <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                      <tr>
                          <th className="px-6 py-3">Strategy</th>
                          <th className="px-6 py-3">Symbol</th>
                          <th className="px-6 py-3 text-right">Net PnL</th>
                          <th className="px-6 py-3 text-right">Daily PnL</th>
                      </tr>
                  </thead>
                  <tbody>
                      {strategy_groups.map((s: any, idx: number) => (
                          <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border-b dark:border-gray-700">
                              <td className="px-6 py-4">
                                  <div className="font-bold text-gray-900 dark:text-white">{s.strategy}</div>
                                  <div className="text-xs text-gray-400 mt-1">{s.legs_desc}</div>
                              </td>
                              <td className="px-6 py-4">
                                  <span className="bg-gray-100 text-gray-800 text-xs font-semibold px-2.5 py-0.5 rounded dark:bg-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600">{s.symbol}</span>
                              </td>
                              <td className={clsx("px-6 py-4 text-right font-bold", s.pnl < 0 ? "text-red-500" : "text-emerald-500")}>
                                  {formatCurrency(s.pnl, '$')}
                              </td>
                              <td className="px-6 py-4 text-right font-mono">
                                  {formatCurrency(s.average_daily_pnl, '$')}
                              </td>
                          </tr>
                      ))}
                  </tbody>
              </table>
          </div>
       </div>

       {token && (
           <div className="flex justify-center mt-8 pb-8">
            <a href={`/download/${token}/report.xlsx`} className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-xl shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all hover:-translate-y-0.5 shadow-lg shadow-primary-500/30">
                <i className="bi bi-download mr-2"></i> Download Excel Report
            </a>
          </div>
       )}

    </div>
  );
};

const MetricCard = ({ title, value, isCurrency, suffix, subValue, color, icon }: any) => (
    <div className="relative group bg-white dark:bg-gray-900 rounded-2xl p-6 border border-gray-200 dark:border-gray-800 shadow-sm hover:shadow-lg transition-all">
          <div className="flex justify-between items-start">
              <div>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
                  <h3 className={clsx("text-3xl font-bold mt-2 tracking-tight", color === 'red' ? "text-red-500" : color === 'emerald' ? "text-emerald-500" : "text-gray-900 dark:text-white")}>
                    {isCurrency ? '$' : ''}{typeof value === 'number' ? value.toFixed(isCurrency ? 2 : 1) : value}{suffix}
                  </h3>
              </div>
              <div className="p-2 bg-gray-50 dark:bg-gray-800 rounded-lg text-gray-400 group-hover:text-primary-500 transition-colors text-xl">
                  {icon}
              </div>
          </div>
          <div className="mt-4 text-xs text-gray-400">{subValue}</div>
    </div>
);

const ProgressBar = ({ value }: { value: number }) => (
    <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 mt-1">
        <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${Math.min(value, 100)}%` }}></div>
    </div>
);

export default Results;
