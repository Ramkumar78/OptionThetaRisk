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

interface PortfolioGreeksReport {
  portfolio_totals: {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
  };
  positions: Array<{
    ticker: string;
    type: string;
    strike: number;
    expiry: string;
    qty: number;
    S: number;
    IV: number;
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    error?: string;
  }>;
}

const PortfolioRisk: React.FC = () => {
  const [mode, setMode] = useState<'stocks' | 'options'>('stocks');
  const [inputText, setInputText] = useState('');

  const [riskReport, setRiskReport] = useState<PortfolioRiskReport | null>(null);
  const [greeksReport, setGreeksReport] = useState<PortfolioGreeksReport | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setRiskReport(null);
    setGreeksReport(null);

    try {
      const lines = inputText.trim().split('\n');
      const positions = [];

      for (const line of lines) {
        if (!line.trim()) continue;
        const parts = line.split(/[,\t]+/);

        if (mode === 'stocks') {
             // Ticker, Value
             if (parts.length >= 2) {
                const ticker = parts[0].trim();
                let valStr = parts[1].trim();
                valStr = valStr.replace(/[^0-9.-]/g, '');
                const value = parseFloat(valStr);
                if (ticker && !isNaN(value)) {
                    positions.push({ ticker, value });
                }
             }
        } else {
             // Ticker, Type, Strike, Expiry, Qty
             // Example: NVDA, Call, 900, 2024-12-20, 10
             if (parts.length >= 5) {
                 const ticker = parts[0].trim();
                 const type = parts[1].trim();
                 const strike = parseFloat(parts[2].replace(/[^0-9.-]/g, ''));
                 const expiry = parts[3].trim();
                 const qty = parseFloat(parts[4].replace(/[^0-9.-]/g, ''));

                 if (ticker && type && !isNaN(strike) && expiry && !isNaN(qty)) {
                     positions.push({ ticker, type, strike, expiry, qty });
                 }
             }
        }
      }

      if (positions.length === 0) {
        setError(mode === 'stocks'
            ? 'No valid positions. Format: Ticker, Value'
            : 'No valid positions. Format: Ticker, Type, Strike, Expiry, Qty');
        setLoading(false);
        return;
      }

      if (mode === 'stocks') {
          const response = await axios.post('/analyze/portfolio', { positions });
          if (response.data.error) setError(response.data.error);
          else setRiskReport(response.data);
      } else {
          const response = await axios.post('/analyze/portfolio/greeks', { positions });
          if (response.data.error) setError(response.data.error);
          else setGreeksReport(response.data);
      }

    } catch (e: any) {
      setError(e.response?.data?.error || e.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getGaugeColor = (score: number) => {
    if (score >= 60) return '#10b981';
    if (score >= 30) return '#f59e0b';
    return '#ef4444';
  };

  const gaugeData: ChartData<'doughnut'> = {
    labels: ['Diversification', 'Risk'],
    datasets: [
      {
        data: riskReport ? [riskReport.diversification_score, 100 - riskReport.diversification_score] : [0, 100],
        backgroundColor: [
            riskReport ? getGaugeColor(riskReport.diversification_score) : '#e5e7eb',
            '#e5e7eb'
        ],
        borderWidth: 0,
        circumference: 180,
        rotation: 270,
      },
    ],
  };

  const sectorData: ChartData<'doughnut'> = {
      labels: riskReport?.sector_breakdown.map(s => s.name) || [],
      datasets: [
          {
              data: riskReport?.sector_breakdown.map(s => s.value) || [],
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
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            {mode === 'stocks' ? 'Portfolio Risk Heatmap' : 'Live Greeks Dashboard'}
        </h1>
        <p className="text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
          {mode === 'stocks'
            ? 'Analyze your portfolio for hidden correlation risks, sector concentration, and "Diworsification".'
            : 'Real-time aggregated Delta, Gamma, Theta, and Vega exposure management.'}
        </p>
      </div>

      {/* Toggle */}
      <div className="flex justify-center">
          <div className="bg-gray-100 dark:bg-gray-700 p-1 rounded-lg inline-flex">
              <button
                className={clsx("px-4 py-2 rounded-md text-sm font-medium transition-all", mode === 'stocks' ? "bg-white dark:bg-gray-600 shadow-sm text-gray-900 dark:text-white" : "text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white")}
                onClick={() => setMode('stocks')}
              >
                  Stocks / Risk
              </button>
              <button
                className={clsx("px-4 py-2 rounded-md text-sm font-medium transition-all", mode === 'options' ? "bg-white dark:bg-gray-600 shadow-sm text-gray-900 dark:text-white" : "text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white")}
                onClick={() => setMode('options')}
              >
                  Options / Greeks
              </button>
          </div>
      </div>

      {/* Input Section */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 max-w-3xl mx-auto">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {mode === 'stocks' ? 'Paste Positions (Format: Ticker, Value)' : 'Paste Options (Format: Ticker, Type, Strike, Expiry, Qty)'}
        </label>
        <textarea
          className="w-full h-32 p-3 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
          placeholder={mode === 'stocks' ? "NVDA, 5000\nAMD, 3000" : "NVDA, Call, 900, 2024-12-20, 10\nTSLA, Put, 150, 2024-11-15, -5"}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        />
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center"
          >
            {loading ? 'Analyzing...' : (mode === 'stocks' ? 'Analyze Risk' : 'Calculate Greeks')}
          </button>
        </div>
        {error && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
                {error}
            </div>
        )}
      </div>

      {/* STOCKS REPORT */}
      {mode === 'stocks' && riskReport && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Hedgeometer */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col items-center">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Hedgeometer</h3>
            <div className="w-64 relative">
                <Doughnut data={gaugeData} options={{ cutout: '70%', plugins: { tooltip: { enabled: false }, legend: { display: false } } }} />
                <div className="absolute inset-0 flex items-center justify-center pt-10 flex-col">
                    <span className="text-4xl font-bold text-gray-900 dark:text-white">{riskReport.diversification_score}</span>
                    <span className="text-xs text-gray-500 uppercase tracking-wider mt-1">Score</span>
                </div>
            </div>
             <div className="mt-4 text-center">
                 {riskReport.diversification_score >= 60 ? (
                     <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">✅ Well Diversified</span>
                 ) : riskReport.diversification_score >= 30 ? (
                     <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">⚠️ Moderate</span>
                 ) : (
                     <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">🔥 Dangerously Correlated</span>
                 )}
            </div>
          </div>

          {/* Red Flags */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">🚩 Red Flags</h3>
            <div className="space-y-3">
                {riskReport.concentration_warnings.length === 0 && riskReport.sector_warnings.length === 0 ? (
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg text-sm text-center">No critical warnings found.</div>
                ) : (
                    <>
                        {riskReport.concentration_warnings.map((w, i) => <div key={`conc-${i}`} className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">{w}</div>)}
                        {riskReport.sector_warnings.map((w, i) => <div key={`sec-${i}`} className="p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg text-sm text-orange-700 dark:text-orange-300">{w}</div>)}
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

          {/* Correlations Table */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">High Correlation Pairs</h3>
             {riskReport.high_correlation_pairs.length === 0 ? (
                  <div className="text-center text-gray-500 py-10">None found.</div>
             ) : (
                 <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                        <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                            <tr>
                                <th className="px-4 py-3">Pair</th>
                                <th className="px-4 py-3">Corr</th>
                                <th className="px-4 py-3">Verdict</th>
                            </tr>
                        </thead>
                        <tbody>
                            {riskReport.high_correlation_pairs.map((item, i) => (
                                <tr key={i} className="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
                                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">{item.pair}</td>
                                    <td className={clsx("px-4 py-3 font-bold", item.score > 0.8 ? "text-red-600" : "text-green-600")}>{item.score}</td>
                                    <td className="px-4 py-3">{item.verdict}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                 </div>
             )}
          </div>

           {/* Heatmap */}
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 lg:col-span-2">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Correlation Matrix</h3>
             {Object.keys(riskReport.correlation_matrix).length === 0 ? (
                  <div className="text-center text-gray-500 py-10">No data.</div>
             ) : (
                 <div className="overflow-x-auto">
                    <div className="inline-block min-w-full">
                        <div className="grid gap-1" style={{ gridTemplateColumns: `auto repeat(${Object.keys(riskReport.correlation_matrix).length}, minmax(40px, 1fr))` }}>
                            <div className="h-10"></div>
                            {Object.keys(riskReport.correlation_matrix).sort().map(ticker => (
                                <div key={`col-${ticker}`} className="flex items-center justify-center font-bold text-xs text-gray-600 dark:text-gray-400 h-10 w-10">{ticker}</div>
                            ))}
                            {Object.keys(riskReport.correlation_matrix).sort().map(rowTicker => (
                                <React.Fragment key={`row-${rowTicker}`}>
                                    <div className="flex items-center justify-end pr-2 font-bold text-xs text-gray-600 dark:text-gray-400 h-10">{rowTicker}</div>
                                    {Object.keys(riskReport.correlation_matrix).sort().map(colTicker => {
                                        const value = riskReport.correlation_matrix[rowTicker][colTicker];
                                        let bgClass = "bg-gray-100 dark:bg-gray-700";
                                        let textClass = "text-gray-800 dark:text-gray-200";
                                        if (value === 1.0) { bgClass = "bg-gray-200 dark:bg-gray-600"; textClass = "text-gray-400"; }
                                        else if (value > 0.8) { bgClass = "bg-red-500 text-white"; }
                                        else if (value > 0.6) { bgClass = "bg-red-300 text-red-900"; }
                                        else if (value < 0.0) { bgClass = "bg-green-400 text-green-900"; }
                                        return (
                                            <div key={`${rowTicker}-${colTicker}`} className={`h-10 w-10 flex items-center justify-center text-xs rounded-sm ${bgClass} ${textClass}`} title={`${value.toFixed(2)}`}>
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

      {/* GREEKS REPORT */}
      {mode === 'options' && greeksReport && (
          <div className="space-y-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                      { label: 'Portfolio Delta', val: greeksReport.portfolio_totals.delta, desc: 'Directional Risk (SPY Equiv approx)' },
                      { label: 'Portfolio Gamma', val: greeksReport.portfolio_totals.gamma, desc: 'Acceleration of Delta' },
                      { label: 'Portfolio Theta', val: greeksReport.portfolio_totals.theta, desc: 'Daily Time Decay ($)', color: 'text-red-600' },
                      { label: 'Portfolio Vega', val: greeksReport.portfolio_totals.vega, desc: 'Exposure to 1% Vol Increase' }
                  ].map((card, i) => (
                      <div key={i} className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                          <div className="text-sm text-gray-500 dark:text-gray-400">{card.label}</div>
                          <div className={clsx("text-2xl font-bold my-1", card.color || "text-gray-900 dark:text-white")}>
                              {card.val.toFixed(2)}
                          </div>
                          <div className="text-xs text-gray-400">{card.desc}</div>
                      </div>
                  ))}
              </div>

              {/* Positions Table */}
              <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Positions Analysis</h3>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                        <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                            <tr>
                                <th className="px-4 py-3">Ticker</th>
                                <th className="px-4 py-3">Type</th>
                                <th className="px-4 py-3">Strike</th>
                                <th className="px-4 py-3">Expiry</th>
                                <th className="px-4 py-3">Price (S)</th>
                                <th className="px-4 py-3">IV %</th>
                                <th className="px-4 py-3">Delta</th>
                                <th className="px-4 py-3">Gamma</th>
                                <th className="px-4 py-3">Theta</th>
                                <th className="px-4 py-3">Vega</th>
                            </tr>
                        </thead>
                        <tbody>
                            {greeksReport.positions.map((pos, i) => (
                                <tr key={i} className="bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700">
                                    <td className="px-4 py-3 font-bold text-gray-900 dark:text-white">{pos.ticker}</td>
                                    <td className="px-4 py-3 uppercase">{pos.type}</td>
                                    <td className="px-4 py-3">{pos.strike}</td>
                                    <td className="px-4 py-3">{pos.expiry}</td>
                                    <td className="px-4 py-3">{pos.error ? <span className="text-red-500">Err</span> : pos.S}</td>
                                    <td className="px-4 py-3">{pos.IV}</td>
                                    <td className={clsx("px-4 py-3", pos.delta > 0 ? "text-green-600" : "text-red-600")}>{pos.delta}</td>
                                    <td className="px-4 py-3">{pos.gamma}</td>
                                    <td className="px-4 py-3 text-red-600">{pos.theta}</td>
                                    <td className="px-4 py-3">{pos.vega}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
              </div>
          </div>
      )}
    </div>
  );
};

export default PortfolioRisk;
