import React, { useState } from 'react';
import { runMarketScreener, runTurtleScreener, runEmaScreener } from '../api';
import clsx from 'clsx';
import { formatCurrency, getCurrencySymbol } from '../utils/formatting';

interface ScreenerProps {}

type ScreenerType = 'market' | 'turtle' | 'ema';

const Screener: React.FC<ScreenerProps> = () => {
  const [activeTab, setActiveTab] = useState<ScreenerType>('turtle'); // Default to Turtle or EMA first
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Market Screener State
  const [ivRank, setIvRank] = useState(30);
  const [rsiThreshold, setRsiThreshold] = useState(50);
  const [marketTimeFrame, setMarketTimeFrame] = useState('1d');

  // Turtle/EMA Screener State
  const [region, setRegion] = useState('us');
  const [strategyTimeFrame, setStrategyTimeFrame] = useState('1d');

  const handleRunScreener = async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      let data;
      if (activeTab === 'market') {
        data = await runMarketScreener(ivRank, rsiThreshold, marketTimeFrame);
      } else if (activeTab === 'turtle') {
        data = await runTurtleScreener(region, strategyTimeFrame);
      } else if (activeTab === 'ema') {
        data = await runEmaScreener(region, strategyTimeFrame);
      }
      setResults(data);
    } catch (err: any) {
      setError(err.message || 'Screener failed');
    } finally {
      setLoading(false);
    }
  };

  const tabs: { id: ScreenerType; label: string; subLabel?: string }[] = [
    { id: 'turtle', label: 'Turtle Trading' },
    { id: 'ema', label: '5/13 EMA' },
    { id: 'market', label: 'Market Screener (RSI/IV)', subLabel: 'US Options Only' },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h2 id="screener-title" className="text-2xl font-bold text-gray-900 dark:text-white">Stock & Option Screener</h2>
            <p id="screener-subtitle" className="text-sm text-gray-500 dark:text-gray-400">Find high-probability setups based on volatility and trend.</p>
          </div>

          <div className="flex space-x-2 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                onClick={() => { setActiveTab(tab.id); setResults(null); }}
                className={clsx(
                  "px-4 py-2 text-sm font-medium rounded-md transition-all flex flex-col items-center",
                  activeTab === tab.id
                    ? "bg-white dark:bg-gray-700 text-primary-600 dark:text-white shadow-sm"
                    : "text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200",
                  tab.id === 'market' && "text-gray-400 dark:text-gray-500 font-light"
                )}
              >
                <span>{tab.label}</span>
                {tab.subLabel && <span className="text-[10px] uppercase tracking-wide opacity-75">{tab.subLabel}</span>}
              </button>
            ))}
          </div>
        </div>

        {/* Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {activeTab === 'market' && (
            <>
              <div>
                <label htmlFor="iv-rank-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Min IV Rank</label>
                <input
                  type="number"
                  id="iv-rank-input"
                  value={ivRank}
                  onChange={(e) => setIvRank(Number(e.target.value))}
                  className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                />
              </div>
              <div>
                <label htmlFor="rsi-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Max RSI</label>
                <input
                  type="number"
                  id="rsi-input"
                  value={rsiThreshold}
                  onChange={(e) => setRsiThreshold(Number(e.target.value))}
                  className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                />
              </div>
              <div>
                <label htmlFor="market-timeframe" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Time Frame</label>
                <select
                  id="market-timeframe"
                  value={marketTimeFrame}
                  onChange={(e) => setMarketTimeFrame(e.target.value)}
                  className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                >
                  <option value="1d">Daily (1d)</option>
                  <option value="1wk">Weekly (1wk)</option>
                  <option value="195m">Half Day (195m)</option>
                  <option value="49m">Swing (49m)</option>
                </select>
              </div>
            </>
          )}

          {(activeTab === 'turtle' || activeTab === 'ema') && (
             <>
              <div>
                <label htmlFor="region-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Region</label>
                <select
                  id="region-select"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                >
                  <option value="us">United States</option>
                  <option value="uk_euro">UK / Europe</option>
                  <option value="india">India</option>
                </select>
              </div>
              <div>
                <label htmlFor="strategy-timeframe" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Time Frame</label>
                <select
                  id="strategy-timeframe"
                  value={strategyTimeFrame}
                  onChange={(e) => setStrategyTimeFrame(e.target.value)}
                  className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                >
                  <option value="1d">Daily (1d)</option>
                  <option value="1wk">Weekly (1wk)</option>
                  <option value="1mo">Monthly (1mo)</option>
                </select>
              </div>
             </>
          )}
        </div>

        <button
          id="run-screener-btn"
          onClick={handleRunScreener}
          disabled={loading}
          className="w-full md:w-auto px-6 py-3 text-white bg-primary-600 hover:bg-primary-700 focus:ring-4 focus:ring-primary-300 font-medium rounded-lg text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Scanning Market...
            </span>
          ) : (
            'Run Screener'
          )}
        </button>

        {error && (
          <div id="screener-error" className="mt-4 p-4 text-sm text-red-800 rounded-lg bg-red-50 dark:bg-gray-800 dark:text-red-400" role="alert">
            <span className="font-medium">Error:</span> {error}
          </div>
        )}
      </div>

      {/* Results Section */}
      {results && (
        <div id="screener-results" className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
            {activeTab === 'market' && results.sector_results && (
                <div className="p-6 border-b border-gray-200 dark:border-gray-800">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Sector Indices</h3>
                    <ScreenerTable data={results.sector_results} type="market" />
                </div>
            )}

            {activeTab === 'market' && results.results && (
                <div className="p-6">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Market Results</h3>
                    {/* Market results are grouped by sector in the backend list of dicts */}
                    <ScreenerTable data={results.results} type="market" />
                </div>
            )}

            {activeTab !== 'market' && (
                <div className="p-6">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                        {activeTab === 'turtle' ? 'Turtle Breakouts' : '5/13 EMA Setups'}
                    </h3>
                    <ScreenerTable data={results} type={activeTab} />
                </div>
            )}
        </div>
      )}
    </div>
  );
};

const ScreenerTable: React.FC<{ data: any[]; type: ScreenerType }> = ({ data, type }) => {
    if (!data || data.length === 0) {
        return <div className="text-gray-500 italic p-4 text-center">No results found matching criteria.</div>;
    }

    // Determine columns based on type
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                    <tr>
                        <th className="px-4 py-3">Symbol</th>
                        {type === 'market' && <th className="px-4 py-3">Company</th>}
                        <th className="px-4 py-3 text-right">Price</th>
                        <th className="px-4 py-3 text-right">Change</th>
                        {type === 'market' && (
                            <>
                                <th className="px-4 py-3 text-right">RSI</th>
                                <th className="px-4 py-3 text-right">IV Rank</th>
                                <th className="px-4 py-3 text-center">Signal</th>
                            </>
                        )}
                        {type !== 'market' && (
                            <>
                                <th className="px-4 py-3 text-center">Signal</th>
                                <th className="px-4 py-3 text-right">Stop Loss</th>
                            </>
                        )}
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {data.map((row, idx) => {
                        const currency = getCurrencySymbol(row.Ticker || row.symbol);
                        const price = row.Close || row.price;
                        const change = row['1D %'] || row.pct_change; // Handle different keys
                        const symbol = row.Ticker || row.symbol;

                        return (
                            <tr key={idx} className="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                <td className="px-4 py-3 font-bold text-gray-900 dark:text-white">
                                    {symbol}
                                    {/* Tooltip or small text for name if available */}
                                    {row.Company && type !== 'market' && <div className="text-xs text-gray-400 font-normal">{row.Company}</div>}
                                </td>
                                {type === 'market' && <td className="px-4 py-3 text-xs">{row.Company || '-'}</td>}

                                <td className="px-4 py-3 text-right font-mono">
                                    {formatCurrency(price, currency)}
                                </td>

                                <td className={clsx("px-4 py-3 text-right font-bold", (change || 0) >= 0 ? "text-emerald-500" : "text-red-500")}>
                                    {change ? `${change > 0 ? '+' : ''}${change.toFixed(2)}%` : '-'}
                                </td>

                                {type === 'market' && (
                                    <>
                                        <td className={clsx("px-4 py-3 text-right", (row.RSI || 0) < 30 ? "text-blue-500 font-bold" : (row.RSI || 0) > 70 ? "text-red-500 font-bold" : "")}>
                                            {row.RSI ? row.RSI.toFixed(1) : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            {row['IV Rank'] ? row['IV Rank'].toFixed(1) : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            {row.Signal && (
                                                <span className={clsx("px-2 py-1 rounded text-xs font-bold",
                                                    row.Signal === 'WAIT' ? "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300" :
                                                    row.Signal === 'OVERSOLD' ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" :
                                                    "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200"
                                                )}>
                                                    {row.Signal}
                                                </span>
                                            )}
                                        </td>
                                    </>
                                )}

                                {type !== 'market' && (
                                    <>
                                        <td className="px-4 py-3 text-center">
                                             <span className={clsx("px-2 py-1 rounded text-xs font-bold",
                                                row.signal === 'Long' || row.signal?.includes('Buy') ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200" :
                                                "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                                             )}>
                                                {row.signal}
                                             </span>
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-500">
                                            {formatCurrency(row.stop_loss, currency)}
                                        </td>
                                    </>
                                )}
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
};

export default Screener;
