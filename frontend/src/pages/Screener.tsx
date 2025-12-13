import React, { useState, useMemo } from 'react';
import { runMarketScreener, runTurtleScreener, runEmaScreener, runDarvasScreener, runMmsScreener, runBullPutScreener, runIsaTrendScreener, checkIsaStock, runFourierScreener } from '../api';
import clsx from 'clsx';
import { formatCurrency, getCurrencySymbol } from '../utils/formatting';

interface ScreenerProps {}

type ScreenerType = 'market' | 'turtle' | 'ema' | 'darvas' | 'mms' | 'bull_put' | 'isa' | 'fourier';

const screenerInfo: Record<ScreenerType, { title: string; subtitle: string; description: string }> = {
  market: {
    title: 'Market Screener',
    subtitle: 'Volatility & RSI Scanner',
    description: 'Scans for liquid US options with specific IV Rank and RSI thresholds. Ideal for finding mean-reversion setups (High IV/RSI) or value entries (Low RSI). Supports sector-based grouping.'
  },
  turtle: {
    title: 'Turtle Trading',
    subtitle: 'Trend Following Breakouts',
    description: 'Based on the classic Turtle Trading experiment. Identifies 20-Day Breakouts (Donchian Channel) to catch major trends. Best used in trending markets.'
  },
  darvas: {
    title: 'Darvas Box',
    subtitle: 'Momentum Breakouts',
    description: 'Identifies stocks consolidating near 52-week highs in a "box" pattern. Signals a buy when price breaks the "Ceiling" on high volume. A powerful momentum strategy.'
  },
  mms: {
    title: 'MMS / OTE',
    subtitle: 'Smart Money Concepts',
    description: 'Market Maker Models & Optimal Trade Entry. Identifies structural shifts and retracements into premium/discount zones (62-79%). High precision entries.'
  },
  ema: {
    title: 'EMA Crossovers',
    subtitle: 'Moving Average Trend',
    description: 'Scans for 5/13 and 5/21 Exponential Moving Average crossovers. "Fresh Breakouts" indicate new trends, while "Trending" signals ongoing momentum. Uses dynamic stops.'
  },
  bull_put: {
    title: 'Bull Put Spreads',
    subtitle: 'Income Generation',
    description: 'Finds bullish setups (Price > SMA 50) suitable for selling credit spreads. Targets ~45 DTE, 30 Delta puts to generate theta income with defined risk.'
  },
  isa: {
    title: 'ISA Trend Follower',
    subtitle: 'Long-Term Growth',
    description: 'A robust long-only strategy. Requires Price > 200 SMA and a breakout above the 50-day High. Exits when price closes below the 20-day Low. Ideal for portfolio growth.'
  },
  fourier: {
    title: 'Harmonic Cycles',
    subtitle: 'Fourier Analysis',
    description: 'Deconstructs price action into waves to identify dominant time cycles. Signals entries at cyclical bottoms (troughs). Best for swing trading in chopping or sideways markets.'
  }
};

const Screener: React.FC<ScreenerProps> = () => {
  const [activeTab, setActiveTab] = useState<ScreenerType>('turtle'); // Default to Turtle or EMA first
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Market Screener State
  const [ivRank, setIvRank] = useState(30);
  const [rsiThreshold, setRsiThreshold] = useState(50);
  const [marketTimeFrame, setMarketTimeFrame] = useState('1d');

  // Turtle/EMA/Strategy Screener State
  const [region, setRegion] = useState('us');
  const [strategyTimeFrame, setStrategyTimeFrame] = useState('1d');

  // ISA Specific State
  const [checkTicker, setCheckTicker] = useState('');
  const [checkEntryPrice, setCheckEntryPrice] = useState('');
  const [checkResult, setCheckResult] = useState<any>(null);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [checkLoading, setCheckLoading] = useState(false);
  const [tableFilter, setTableFilter] = useState('');

  const handleRunScreener = async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    setTableFilter('');
    try {
      let data;
      if (activeTab === 'market') {
        // We now pass 'region' to market screener too
        data = await runMarketScreener(ivRank, rsiThreshold, marketTimeFrame, region);
      } else if (activeTab === 'turtle') {
        data = await runTurtleScreener(region, strategyTimeFrame);
      } else if (activeTab === 'ema') {
        data = await runEmaScreener(region, strategyTimeFrame);
      } else if (activeTab === 'darvas') {
        data = await runDarvasScreener(region, strategyTimeFrame);
      } else if (activeTab === 'mms') {
        data = await runMmsScreener(region, strategyTimeFrame);
      } else if (activeTab === 'bull_put') {
        // Bull Put usually implies US liquid, but we can pass region if we want to expand later
        data = await runBullPutScreener(region);
      } else if (activeTab === 'isa') {
        data = await runIsaTrendScreener(region);
      } else if (activeTab === 'fourier') {
        data = await runFourierScreener(region, strategyTimeFrame);
      }
      setResults(data);
    } catch (err: any) {
      setError(err.message || 'Screener failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckStock = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!checkTicker.trim()) return;
      setCheckLoading(true);
      setCheckResult(null);
      setCheckError(null);
      try {
          const data = await checkIsaStock(checkTicker, checkEntryPrice);
          setCheckResult(data);
      } catch (err: any) {
          setCheckError(err.message || 'Check failed');
      } finally {
          setCheckLoading(false);
      }
  };

  const tabs: { id: ScreenerType; label: string; subLabel?: string }[] = [
    { id: 'turtle', label: 'Turtle Trading' },
    { id: 'darvas', label: 'Darvas Box' },
    { id: 'fourier', label: 'Harmonic Cycles', subLabel: 'New' },
    { id: 'mms', label: 'MMS / OTE', subLabel: 'SMC' },
    { id: 'ema', label: '5/13 & 5/21 EMA' },
    { id: 'isa', label: 'ISA Trend Follower', subLabel: 'Long Only' },
    { id: 'bull_put', label: 'Bull Put Spreads', subLabel: 'Yield' },
    { id: 'market', label: 'Market Screener (RSI/IV)', subLabel: 'US Options Only' },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6">

        {/* Header & Tabs */}
        <div className="flex flex-col gap-6 mb-6">
            <div>
                <h2 id="screener-title" className="text-2xl font-bold text-gray-900 dark:text-white">Stock & Option Screener</h2>
                <p id="screener-subtitle" className="text-sm text-gray-500 dark:text-gray-400">Find high-probability setups based on volatility and trend.</p>
            </div>

            <div className="w-full">
                <div className="flex space-x-2 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg overflow-x-auto whitespace-nowrap no-scrollbar">
                    {tabs.map((tab) => (
                        <button
                        key={tab.id}
                        id={`tab-${tab.id}`}
                        onClick={() => { setActiveTab(tab.id); setResults(null); }}
                        className={clsx(
                            "px-4 py-2 text-sm font-medium rounded-md transition-all flex flex-col items-center justify-center flex-shrink-0 min-w-[120px]",
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

            {/* Dynamic Description Box */}
            <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg border border-gray-100 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1 flex items-center">
                    {screenerInfo[activeTab].title}
                    <span className="hidden sm:inline-block mx-2 text-gray-300 dark:text-gray-600">|</span>
                    <span className="text-sm font-normal text-gray-500 dark:text-gray-400 block sm:inline">{screenerInfo[activeTab].subtitle}</span>
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">
                    {screenerInfo[activeTab].description}
                </p>
            </div>
        </div>

        {/* Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {activeTab === 'market' && (
            <>
              <div>
                <label htmlFor="region-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Region</label>
                <select
                  id="region-select"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                >
                  <option value="us">United States (Sectors)</option>
                  <option value="sp500">S&P 500</option>
                </select>
              </div>
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

          {activeTab === 'isa' && (
             <div className="col-span-1 md:col-span-3 space-y-4">
                 <div className="flex items-end gap-4">
                     <div className="flex-1">
                        <label htmlFor="check-stock" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Check a Stock</label>
                        <form onSubmit={handleCheckStock} className="flex gap-2">
                            <input
                                type="text"
                                id="check-stock"
                                value={checkTicker}
                                onChange={(e) => setCheckTicker(e.target.value)}
                                placeholder="Enter Ticker (e.g. AAPL, TSLA) or Name"
                                className="flex-1 bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                            />
                            <input
                                type="number"
                                step="0.01"
                                value={checkEntryPrice}
                                onChange={(e) => setCheckEntryPrice(e.target.value)}
                                placeholder="Entry Price (Opt.)"
                                className="w-32 bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                            />
                            <button
                                type="submit"
                                disabled={checkLoading || !checkTicker.trim()}
                                className="px-4 py-2 text-white bg-indigo-600 hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-300 font-medium rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                            >
                                {checkLoading ? 'Checking...' : 'Check'}
                            </button>
                        </form>
                     </div>
                 </div>
                 {checkError && <div className="text-red-600 text-sm">{checkError}</div>}
                 {checkResult && (
                     <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                         <h4 className="text-md font-bold text-gray-900 dark:text-white mb-2">{checkResult.company_name} ({checkResult.ticker})</h4>
                         <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                             <div>
                                 <span className="text-gray-500 dark:text-gray-400 block">Signal</span>
                                 <span className={clsx("font-bold", checkResult.signal.includes('ENTER') ? "text-emerald-600" : checkResult.signal.includes('EXIT') ? "text-orange-600" : checkResult.signal.includes('SELL') ? "text-red-600" : "text-blue-600")}>
                                     {checkResult.signal}
                                 </span>
                             </div>
                             <div>
                                 <span className="text-gray-500 dark:text-gray-400 block">Price</span>
                                 <span className="font-mono text-gray-900 dark:text-white">{formatCurrency(checkResult.price, getCurrencySymbol(checkResult.ticker))}</span>
                             </div>
                             <div>
                                 <span className="text-gray-500 dark:text-gray-400 block">Stop Loss (3ATR)</span>
                                 <span className="font-mono text-red-600 dark:text-red-400 font-bold">{formatCurrency(checkResult.stop_loss_3atr, getCurrencySymbol(checkResult.ticker))}</span>
                             </div>
                             <div>
                                 <span className="text-gray-500 dark:text-gray-400 block">Risk/Share</span>
                                 <span className="font-mono text-gray-900 dark:text-white">{formatCurrency(checkResult.risk_per_share, getCurrencySymbol(checkResult.ticker))}</span>
                             </div>
                         </div>
                     </div>
                 )}
                 <div className="flex items-center text-sm text-gray-500 italic">
                      Strategy: Long Only Trend Following. Risk: 1% per trade. Position: 4% of Account.
                  </div>
             </div>
          )}

          {(activeTab === 'turtle' || activeTab === 'ema' || activeTab === 'darvas' || activeTab === 'mms' || activeTab === 'isa' || activeTab === 'fourier') && (
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
                  <option value="sp500">S&P 500</option>
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
                  {activeTab === 'mms' ? (
                      <>
                        <option value="1h">Hourly (1h)</option>
                        <option value="15m">Intraday (15m)</option>
                        <option value="1d">Daily (1d)</option>
                      </>
                  ) : (
                      <>
                        <option value="1d">Daily (1d)</option>
                        <option value="1wk">Weekly (1wk)</option>
                        <option value="1mo">Monthly (1mo)</option>
                      </>
                  )}
                </select>
              </div>
             </>
          )}

          {activeTab === 'bull_put' && (
              <>
                 <div>
                    <label htmlFor="region-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Region</label>
                    <select
                      id="region-select"
                      value={region}
                      onChange={(e) => setRegion(e.target.value)}
                      className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                    >
                      <option value="us">United States (High Liquid)</option>
                      <option value="sp500">S&P 500 (Filtered &gt; SMA200)</option>
                    </select>
                  </div>
                  <div className="flex items-center text-sm text-gray-500 italic mt-6">
                      Targeting 45 DTE, ~30 Delta Puts.
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
                <div className="p-6 space-y-8">
                    {/* Iterate over sector keys */}
                    {Object.keys(results.results).map((sectorName) => {
                        const sectorData = results.results[sectorName];
                        if (!sectorData || sectorData.length === 0) return null;
                        return (
                            <div key={sectorName}>
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{sectorName}</h3>
                                <ScreenerTable data={sectorData} type="market" />
                            </div>
                        );
                    })}
                </div>
            )}

            {activeTab !== 'market' && (
                <div className="p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                            {activeTab === 'turtle' ? 'Turtle Breakouts' :
                            activeTab === 'darvas' ? 'Darvas Box Setups' :
                            activeTab === 'mms' ? 'Market Maker Models (OTE)' :
                            activeTab === 'bull_put' ? 'Bull Put Spreads' :
                            activeTab === 'isa' ? 'Trend Follower (ISA)' :
                            activeTab === 'fourier' ? 'Harmonic Cycle (Fourier)' :
                            '5/13 EMA Setups'}
                        </h3>
                        {activeTab === 'isa' && (
                            <input
                                type="text"
                                placeholder="Filter Results..."
                                value={tableFilter}
                                onChange={(e) => setTableFilter(e.target.value)}
                                className="bg-white border border-gray-300 text-gray-900 text-xs rounded-lg focus:ring-primary-500 focus:border-primary-500 block p-2 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white w-48"
                            />
                        )}
                    </div>
                    <ScreenerTable data={results} type={activeTab} filter={tableFilter} />
                </div>
            )}
        </div>
      )}
    </div>
  );
};

interface SortConfig {
  key: string;
  direction: 'asc' | 'desc';
}

const ScreenerTable: React.FC<{ data: any[]; type: ScreenerType; filter?: string }> = ({ data, type, filter }) => {
    const [sortConfig, setSortConfig] = useState<SortConfig | null>(null);

    const sortedData = useMemo(() => {
        let sortableItems = [...data];
        if (filter) {
            const lowerFilter = filter.toLowerCase();
            sortableItems = sortableItems.filter(item => {
                const ticker = (item.Ticker || item.ticker || item.symbol || "").toLowerCase();
                const name = (item.Company || item.company_name || "").toLowerCase();
                return ticker.includes(lowerFilter) || name.includes(lowerFilter);
            });
        }
        if (sortConfig !== null) {
            sortableItems.sort((a, b) => {
                // Map frontend sort keys to data keys
                let aValue = a[sortConfig.key];
                let bValue = b[sortConfig.key];

                // Handle specific mappings if key doesn't match directly
                if (sortConfig.key === 'symbol') {
                     aValue = a.Ticker || a.ticker || a.symbol;
                     bValue = b.Ticker || b.ticker || b.symbol;
                } else if (sortConfig.key === 'company') {
                    aValue = a.Company || a.company_name;
                    bValue = b.Company || b.company_name;
                } else if (sortConfig.key === 'price') {
                    aValue = a.Close || a.price;
                    bValue = b.Close || b.price;
                } else if (sortConfig.key === 'change') {
                    aValue = a['1D %'] || a.pct_change_1d || a.pct_change;
                    bValue = b['1D %'] || b.pct_change_1d || b.pct_change;
                } else if (sortConfig.key === 'rsi') {
                    aValue = a.RSI || a.rsi;
                    bValue = b.RSI || b.rsi;
                } else if (sortConfig.key === 'iv_rank') {
                     aValue = a['IV Rank'] || a.iv_rank;
                     if (aValue === 'N/A*') aValue = -1; // Treat N/A as low
                     bValue = b['IV Rank'] || b.iv_rank;
                     if (bValue === 'N/A*') bValue = -1;
                } else if (sortConfig.key === 'signal') {
                    aValue = a.Signal || a.signal;
                    bValue = b.Signal || b.signal;
                } else if (sortConfig.key === 'stop_loss') {
                    aValue = a.stop_loss;
                    bValue = b.stop_loss;
                } else if (sortConfig.key === 'breakout') {
                    aValue = a.breakout_level;
                    bValue = b.breakout_level;
                } else if (sortConfig.key === 'target') {
                    aValue = a.target_price;
                    bValue = b.target_price;
                } else if (sortConfig.key === 'high_52w') {
                    aValue = a.high_52w;
                    bValue = b.high_52w;
                } else if (sortConfig.key === 'ote_zone') {
                    aValue = a.ote_zone;
                    bValue = b.ote_zone;
                } else if (sortConfig.key === 'credit') {
                    aValue = a.credit;
                    bValue = b.credit;
                } else if (sortConfig.key === 'roi') {
                    aValue = a.roi_pct;
                    bValue = b.roi_pct;
                } else if (sortConfig.key === 'dte') {
                    aValue = a.dte;
                    bValue = b.dte;
                } else if (sortConfig.key === 'volatility') {
                    aValue = a.volatility_pct;
                    bValue = b.volatility_pct;
                } else if (sortConfig.key === 'risk_share') {
                    aValue = a.risk_per_share;
                    bValue = b.risk_per_share;
                } else if (sortConfig.key === 'tharp') {
                    aValue = a.tharp_verdict;
                    bValue = b.tharp_verdict;
                } else if (sortConfig.key === 'max_size') {
                    // Sort numerically if possible (remove %)
                    aValue = parseFloat((a.max_position_size || "0").replace('%',''));
                    bValue = parseFloat((b.max_position_size || "0").replace('%',''));
                } else if (sortConfig.key === 'cycle_period') {
                    aValue = parseFloat((a.cycle_period || "0").split(' ')[0]);
                    bValue = parseFloat((b.cycle_period || "0").split(' ')[0]);
                } else if (sortConfig.key === 'cycle_pos') {
                    aValue = parseFloat((a.cycle_position || "0").split(' ')[0]);
                    bValue = parseFloat((b.cycle_position || "0").split(' ')[0]);
                }

                if (aValue === undefined || aValue === null) return 1;
                if (bValue === undefined || bValue === null) return -1;

                if (typeof aValue === 'string') {
                     aValue = aValue.toLowerCase();
                     bValue = bValue.toLowerCase();
                }

                if (aValue < bValue) {
                    return sortConfig.direction === 'asc' ? -1 : 1;
                }
                if (aValue > bValue) {
                    return sortConfig.direction === 'asc' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableItems;
    }, [data, sortConfig]);

    const requestSort = (key: string) => {
        let direction: 'asc' | 'desc' = 'asc';
        if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const getSortIndicator = (key: string) => {
        if (!sortConfig || sortConfig.key !== key) return <span className="text-gray-300 ml-1">⇅</span>;
        return sortConfig.direction === 'asc' ? <span className="text-primary-600 ml-1">↑</span> : <span className="text-primary-600 ml-1">↓</span>;
    };

    if (!data || data.length === 0) {
        return <div className="text-gray-500 italic p-4 text-center">No results found matching criteria.</div>;
    }

    const HeaderCell = ({ label, sortKey, align = 'left' }: { label: string, sortKey: string, align?: string }) => (
        <th
            className={clsx("px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none", align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left')}
            onClick={() => requestSort(sortKey)}
        >
            <div className={clsx("flex items-center", align === 'right' ? 'justify-end' : align === 'center' ? 'justify-center' : 'justify-start')}>
                {label} {getSortIndicator(sortKey)}
            </div>
        </th>
    );

    // Determine columns based on type
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                    <tr>
                        <HeaderCell label="Symbol" sortKey="symbol" />
                        {type === 'market' && <HeaderCell label="Company" sortKey="company" />}
                        <HeaderCell label="Price" sortKey="price" align="right" />
                        {type !== 'bull_put' && <HeaderCell label="Change" sortKey="change" align="right" />}
                        {type === 'market' && (
                            <>
                                <HeaderCell label="RSI" sortKey="rsi" align="right" />
                                <HeaderCell label="IV Rank" sortKey="iv_rank" align="right" />
                                <HeaderCell label="Signal" sortKey="signal" align="center" />
                            </>
                        )}
                        {type !== 'market' && type !== 'bull_put' && (
                            <>
                                <HeaderCell label="Signal" sortKey="signal" align="center" />
                                {type === 'darvas' && (
                                    <>
                                        <HeaderCell label="Breakout" sortKey="breakout" align="right" />
                                        <HeaderCell label="Target" sortKey="target" align="right" />
                                        <HeaderCell label="52W High" sortKey="high_52w" align="right" />
                                    </>
                                )}
                                {type === 'mms' && (
                                    <>
                                        <HeaderCell label="OTE Zone" sortKey="ote_zone" align="right" />
                                        <HeaderCell label="Target" sortKey="target" align="right" />
                                    </>
                                )}
                                {type === 'isa' && (
                                    <>
                                        <HeaderCell label="Breakout Date" sortKey="breakout_date" align="right" />
                                        <HeaderCell label="Breakout Level" sortKey="breakout" align="right" />
                                        <HeaderCell label="Stop (3ATR)" sortKey="stop_loss" align="right" />
                                        <HeaderCell label="Exit (20L)" sortKey="trailing_exit" align="right" />
                                        <HeaderCell label="Vol %" sortKey="volatility" align="right" />
                                        <HeaderCell label="Risk/Share" sortKey="risk_share" align="right" />
                                        <HeaderCell label="Tharp Verdict" sortKey="tharp" align="right" />
                                        <HeaderCell label="Max Size" sortKey="max_size" align="right" />
                                    </>
                                )}
                                {type === 'fourier' && (
                                    <>
                                        <HeaderCell label="Cycle Period" sortKey="cycle_period" align="right" />
                                        <HeaderCell label="Cycle Position" sortKey="cycle_pos" align="right" />
                                    </>
                                )}
                                {type !== 'isa' && type !== 'fourier' && <HeaderCell label="Stop Loss" sortKey="stop_loss" align="right" />}
                            </>
                        )}
                        {type === 'bull_put' && (
                            <>
                                <HeaderCell label="Credit" sortKey="credit" align="right" />
                                <HeaderCell label="Max Risk" sortKey="risk" align="right" />
                                <HeaderCell label="ROI" sortKey="roi" align="right" />
                                <HeaderCell label="Short Strike" sortKey="strike" align="right" />
                                <HeaderCell label="DTE" sortKey="dte" align="right" />
                            </>
                        )}
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {sortedData.map((row, idx) => {
                        const currency = getCurrencySymbol(row.Ticker || row.ticker || row.symbol);
                        const price = row.Close || row.price;
                        // Handle multiple possible keys for change
                        const change = row['1D %'] !== undefined ? row['1D %'] : (row.pct_change_1d !== undefined ? row.pct_change_1d : row.pct_change);
                        const symbol = row.Ticker || row.ticker || row.symbol;
                        const company = row.Company || row.company_name;
                        const rsi = row.RSI || row.rsi;
                        const ivRank = row['IV Rank'] || row.iv_rank;
                        const signal = row.Signal || row.signal;

                        return (
                            <tr key={idx} className="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                <td className="px-4 py-3 font-bold text-gray-900 dark:text-white">
                                    {symbol}
                                    {/* Tooltip or small text for name if available */}
                                    {company && type !== 'market' && <div className="text-xs text-gray-400 font-normal">{company}</div>}
                                </td>
                                {type === 'market' && <td className="px-4 py-3 text-xs">{company || '-'}</td>}

                                <td className="px-4 py-3 text-right font-mono">
                                    {formatCurrency(price, currency)}
                                </td>

                                {type !== 'bull_put' && (
                                  <td className={clsx("px-4 py-3 text-right font-bold", (change || 0) >= 0 ? "text-emerald-500" : "text-red-500")}>
                                      {change !== undefined && change !== null ? `${change > 0 ? '+' : ''}${typeof change === 'number' ? change.toFixed(2) : change}%` : '-'}
                                  </td>
                                )}

                                {type === 'market' && (
                                    <>
                                        <td className={clsx("px-4 py-3 text-right", (rsi || 0) < 30 ? "text-blue-500 font-bold" : (rsi || 0) > 70 ? "text-red-500 font-bold" : "")}>
                                            {rsi !== undefined && rsi !== null ? (typeof rsi === 'number' ? rsi.toFixed(1) : rsi) : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            {ivRank !== undefined && ivRank !== null ? (typeof ivRank === 'number' ? ivRank.toFixed(1) : ivRank) : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            {signal && (
                                                <span className={clsx("px-2 py-1 rounded text-xs font-bold",
                                                    signal === 'WAIT' ? "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300" :
                                                    signal.includes('OVERSOLD') || signal.includes('Buy') ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" :
                                                    signal.includes('OVERBOUGHT') || signal.includes('Sell') ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" :
                                                    "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200"
                                                )}>
                                                    {signal}
                                                </span>
                                            )}
                                        </td>
                                    </>
                                )}

                                {type !== 'market' && type !== 'bull_put' && (
                                    <>
                                        <td className="px-4 py-3 text-center">
                                             <span className={clsx("px-2 py-1 rounded text-xs font-bold",
                                                signal && (signal.includes('Long') || signal.includes('Buy') || signal.includes('BREAKOUT')) ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200" :
                                                signal && (signal.includes('Short') || signal.includes('Sell') || signal.includes('DUMP')) ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" :
                                                "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                                             )}>
                                                {signal}
                                             </span>
                                        </td>
                                        {type === 'darvas' && (
                                            <>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300">
                                                    {formatCurrency(row.breakout_level, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400 font-bold">
                                                    {formatCurrency(row.target_price, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-500">
                                                    {formatCurrency(row.high_52w, currency)}
                                                </td>
                                            </>
                                        )}
                                        {type === 'mms' && (
                                            <>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-indigo-600 dark:text-indigo-400">
                                                    {row.ote_zone}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400 font-bold">
                                                    {formatCurrency(row.target, currency)}
                                                </td>
                                            </>
                                        )}
                                        {type === 'isa' ? (
                                            <>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300">
                                                    {row.breakout_date || "N/A"}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300">
                                                    {formatCurrency(row.breakout_level, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-red-600 dark:text-red-400 font-bold">
                                                    {formatCurrency(row.stop_loss_3atr, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-orange-600 dark:text-orange-400">
                                                    {formatCurrency(row.trailing_exit_20d, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-500">
                                                    {row.volatility_pct}%
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-500">
                                                    {formatCurrency(row.risk_per_share, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300">
                                                    {row.tharp_verdict}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400 font-bold">
                                                    {row.max_position_size}
                                                </td>
                                            </>
                                        ) : type === 'fourier' ? (
                                            <>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300">
                                                    {row.cycle_period}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-indigo-600 dark:text-indigo-400 font-bold">
                                                    {row.cycle_position}
                                                </td>
                                            </>
                                        ) : (
                                            <td className="px-4 py-3 text-right font-mono text-xs text-gray-500">
                                                {formatCurrency(row.stop_loss, currency)}
                                            </td>
                                        )}
                                    </>
                                )}

                                {type === 'bull_put' && (
                                    <>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400 font-bold">
                                            ${row.credit.toFixed(2)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-500">
                                            ${row.max_risk.toFixed(2)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-indigo-600 dark:text-indigo-400 font-bold">
                                            {row.roi_pct}%
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300">
                                            {row.short_strike}/{row.long_strike} <span className="text-gray-400 text-[10px]">({row.short_delta})</span>
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-500">
                                            {row.dte}d
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
