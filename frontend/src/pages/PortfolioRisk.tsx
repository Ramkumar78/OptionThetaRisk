import React, { useState } from 'react';
import axios from 'axios';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, type ChartData } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import clsx from 'clsx';

ChartJS.register(ArcElement, Tooltip, Legend);

interface PortfolioRiskReport {
  total_value: number;
  diversification_score: number;
  concentration_warnings: string[];
  sector_warnings: string[];
  sector_breakdown: { name: string; value: number }[];
  high_correlation_pairs: { pair: string; score: number; verdict: string }[];
  correlation_matrix: Record<string, Record<string, number>>;
}

const PortfolioRisk: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [report, setReport] = useState<PortfolioRiskReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setReport(null);

    try {
      // Parse input
      const lines = inputText.trim().split('\n');
      const positions = [];

      for (const line of lines) {
        if (!line.trim()) continue;
        const parts = line.split(/[,\t]+/); // Split by comma or tab
        if (parts.length >= 2) {
          const ticker = parts[0].trim();
          let valStr = parts[1].trim();
          valStr = valStr.replace(/[^0-9.-]/g, ''); // Remove currency symbols
          const value = parseFloat(valStr);
          if (ticker && !isNaN(value)) {
            positions.push({ ticker, value });
          }
        }
      }

      if (positions.length === 0) {
        setError('No valid positions found. Use format: Ticker, Value (e.g. NVDA, 5000)');
        setLoading(false);
        return;
      }

      const response = await axios.post('/analyze/portfolio', { positions });
      if (response.data.error) {
          setError(response.data.error);
      } else {
          setReport(response.data);
      }
    } catch (e: any) {
      setError(e.response?.data?.error || e.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getGaugeColor = (score: number) => {
    if (score >= 60) return '#10b981'; // Emerald-500
    if (score >= 30) return '#f59e0b'; // Amber-500
    return '#ef4444'; // Red-500
  };

  const gaugeData: ChartData<'doughnut'> = {
    labels: ['Diversification', 'Risk'],
    datasets: [
      {
        data: report ? [report.diversification_score, 100 - report.diversification_score] : [0, 100],
        backgroundColor: [
            report ? getGaugeColor(report.diversification_score) : '#e5e7eb',
            '#e5e7eb'
        ],
        borderWidth: 0,
        circumference: 180,
        rotation: 270,
      },
    ],
  };

  const sectorData: ChartData<'doughnut'> = {
      labels: report?.sector_breakdown.map(s => s.name) || [],
      datasets: [
          {
              data: report?.sector_breakdown.map(s => s.value) || [],
              backgroundColor: [
                '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316',
                '#eab308', '#84cc16', '#10b981', '#06b6d4', '#3b82f6'
              ],
              borderWidth: 1,
          }
      ]
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Portfolio Risk Heatmap</h1>
        <p className="text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
          Analyze your portfolio for hidden correlation risks, sector concentration, and "Diworsification".
        </p>
      </div>

      {/* Input Section */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 max-w-3xl mx-auto">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Paste Positions (Format: Ticker, Value)
        </label>
        <textarea
          className="w-full h-32 p-3 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
          placeholder="NVDA, 5000&#10;AMD, 3000&#10;GOOG, 4000"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        />
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Analyzing...
              </>
            ) : (
              'Analyze Risk'
            )}
          </button>
        </div>
        {error && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
                {error}
            </div>
        )}
      </div>

      {report && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Hedgeometer */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col items-center">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Hedgeometer</h3>
            <div className="w-64 relative">
                <Doughnut data={gaugeData} options={{ cutout: '70%', plugins: { tooltip: { enabled: false }, legend: { display: false } } }} />
                <div className="absolute inset-0 flex items-center justify-center pt-10 flex-col">
                    <span className="text-4xl font-bold text-gray-900 dark:text-white">{report.diversification_score}</span>
                    <span className="text-xs text-gray-500 uppercase tracking-wider mt-1">Score</span>
                </div>
            </div>
            <div className="mt-4 text-center">
                 {report.diversification_score >= 60 ? (
                     <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                         ✅ Well Diversified
                     </span>
                 ) : report.diversification_score >= 30 ? (
                     <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                         ⚠️ Moderate
                     </span>
                 ) : (
                     <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                         🔥 Dangerously Correlated
                     </span>
                 )}
            </div>
          </div>

          {/* Red Flags */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white flex items-center">
                <span className="mr-2">🚩</span> Red Flags
            </h3>
            <div className="space-y-3">
                {report.concentration_warnings.length === 0 && report.sector_warnings.length === 0 ? (
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg text-sm text-center">
                        No critical warnings found. Good job!
                    </div>
                ) : (
                    <>
                        {report.concentration_warnings.map((w, i) => (
                            <div key={`conc-${i}`} className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
                                {w}
                            </div>
                        ))}
                        {report.sector_warnings.map((w, i) => (
                            <div key={`sec-${i}`} className="p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg text-sm text-orange-700 dark:text-orange-300">
                                {w}
                            </div>
                        ))}
                    </>
                )}
            </div>
          </div>

          {/* Sector Breakdown */}
           <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Sector Breakdown</h3>
            <div className="h-64 flex justify-center">
                 <Doughnut data={sectorData} options={{ maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }} />
            </div>
          </div>

          {/* Clone Wars (Correlations) */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">The "Clone Wars" (High Correlation)</h3>
             {report.high_correlation_pairs.length === 0 ? (
                  <div className="text-center text-gray-500 py-10">No highly correlated pairs found.</div>
             ) : (
                 <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                        <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                            <tr>
                                <th className="px-4 py-3">Pair</th>
                                <th className="px-4 py-3">Correlation</th>
                                <th className="px-4 py-3">Verdict</th>
                            </tr>
                        </thead>
                        <tbody>
                            {report.high_correlation_pairs.map((item, i) => (
                                <tr key={i} className="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
                                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{item.pair}</td>
                                    <td className={clsx("px-4 py-3 font-bold", item.score > 0.8 ? "text-red-600" : "text-green-600")}>
                                        {item.score}
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={clsx("px-2 py-1 rounded text-xs font-medium",
                                            item.score > 0.8 ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" :
                                            "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                                        )}>
                                            {item.verdict}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                 </div>
             )}
          </div>

          {/* Correlation Heatmap */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 lg:col-span-2">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Correlation Matrix</h3>
             {Object.keys(report.correlation_matrix).length === 0 ? (
                  <div className="text-center text-gray-500 py-10">No correlation data available.</div>
             ) : (
                 <div className="overflow-x-auto">
                    <div className="inline-block min-w-full">
                        <div className="grid gap-1" style={{ gridTemplateColumns: `auto repeat(${Object.keys(report.correlation_matrix).length}, minmax(40px, 1fr))` }}>
                            {/* Header Row */}
                            <div className="h-10"></div> {/* Empty corner */}
                            {Object.keys(report.correlation_matrix).sort().map(ticker => (
                                <div key={`col-${ticker}`} className="flex items-center justify-center font-bold text-xs text-gray-600 dark:text-gray-400 h-10 w-10">
                                    {ticker}
                                </div>
                            ))}

                            {/* Matrix Rows */}
                            {Object.keys(report.correlation_matrix).sort().map(rowTicker => (
                                <React.Fragment key={`row-${rowTicker}`}>
                                    {/* Row Label */}
                                    <div className="flex items-center justify-end pr-2 font-bold text-xs text-gray-600 dark:text-gray-400 h-10">
                                        {rowTicker}
                                    </div>
                                    {/* Cells */}
                                    {Object.keys(report.correlation_matrix).sort().map(colTicker => {
                                        const value = report.correlation_matrix[rowTicker][colTicker];
                                        let bgClass = "bg-gray-100 dark:bg-gray-700";
                                        let textClass = "text-gray-800 dark:text-gray-200";

                                        if (value === 1.0) {
                                            bgClass = "bg-gray-200 dark:bg-gray-600"; // Diagonal
                                            textClass = "text-gray-400 dark:text-gray-500";
                                        } else if (value > 0.8) {
                                            bgClass = "bg-red-500 text-white";
                                        } else if (value > 0.6) {
                                            bgClass = "bg-red-300 text-red-900";
                                        } else if (value > 0.3) {
                                            bgClass = "bg-orange-200 text-orange-900";
                                        } else if (value < 0.0) {
                                            bgClass = "bg-green-400 text-green-900"; // Hedge
                                        } else if (value < 0.3) {
                                            bgClass = "bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300"; // Low corr
                                        }

                                        return (
                                            <div
                                                key={`${rowTicker}-${colTicker}`}
                                                className={`h-10 w-10 flex items-center justify-center text-xs rounded-sm ${bgClass} ${textClass} cursor-default`}
                                                title={`${rowTicker} vs ${colTicker}: ${value.toFixed(2)}`}
                                            >
                                                {value.toFixed(1)}
                                            </div>
                                        );
                                    })}
                                </React.Fragment>
                            ))}
                        </div>
                    </div>
                 </div>
             )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PortfolioRisk;
