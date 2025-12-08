import React, { useState } from 'react';
import { runMarketScreener, runTurtleScreener, runEmaScreener } from '../api';
import clsx from 'clsx';

interface ScreenerProps {}

type ScreenerType = 'market' | 'turtle' | 'ema';

const Screener: React.FC<ScreenerProps> = () => {
  const [activeTab, setActiveTab] = useState<ScreenerType>('market');
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

  const tabs: { id: ScreenerType; label: string }[] = [
    { id: 'market', label: 'Market Screener' },
    { id: 'turtle', label: 'Turtle Trading' },
    { id: 'ema', label: '5/13 EMA' },
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
                  "px-4 py-2 text-sm font-medium rounded-md transition-all",
                  activeTab === tab.id
                    ? "bg-white dark:bg-gray-700 text-primary-600 dark:text-white shadow-sm"
                    : "text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                )}
              >
                {tab.label}
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
        <div id="screener-results" className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 overflow-x-auto">
            {/*
                NOTE: This is a placeholder for the actual results table.
                Since the backend logic for returning JSON is not yet implemented,
                we will just dump the JSON for now or show a message.

                Once the backend is updated to return structured JSON (lists of dicts),
                we can render a proper table here.
            */}
             <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-auto max-h-96">
                {JSON.stringify(results, null, 2)}
             </pre>

             {/* Note for later: We need to implement specific table components for each screener type */}
        </div>
      )}
    </div>
  );
};

export default Screener;
