import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatCurrency, getCurrencySymbol } from '../utils/formatting';

// 1. STRATEGY DEFINITIONS
const STRATEGIES: Record<string, {
    id: string;
    name: string;
    endpoint: string;
    description: string;
    params: string[];
    legend: { title: string; desc: string; items: { label: string; text: string }[] }[];
}> = {
    grandmaster: {
        id: 'grandmaster',
        name: 'Grandmaster Council',
        endpoint: '/screen/master',
        description: 'The Fortress Protocol. Hardened logic for £100k ISA (VCP Trend) and $9.5k Options (Bull Puts).',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Fortress Keys',
                desc: 'Strict regime-based filtering.',
                items: [
                    { label: 'ISA VCP', text: 'Buy Signal: Trend + Volatility Squeeze.' },
                    { label: 'OPT PUT', text: 'Income Signal: Blue chip oversold put spread.' },
                    { label: 'REGIME', text: 'Green = Aggressive, Red = Cash/Hedge.' }
                ]
            }
        ]
    },
    alpha101: {
        id: 'alpha101',
        name: 'Alpha 101 (Momentum)',
        endpoint: '/screen/alpha101',
        description: 'Kakushadze Alpha #101: ((Close - Open) / (High - Low)). Captures pure intraday buying/selling pressure.',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Alpha Value',
                desc: 'Range from -1.0 to 1.0',
                items: [
                    { label: '> 0.5', text: 'Strong Bullish (Close near High).' },
                    { label: '< -0.5', text: 'Strong Bearish (Close near Low).' }
                ]
            }
        ]
    },
    hybrid: {
        id: 'hybrid',
        name: 'Hybrid (Trend + Cycle)',
        endpoint: '/screen/hybrid',
        description: 'Combines ISA Trend direction with Fourier Cycle timing to find perfect entry points.',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Hybrid Logic',
                desc: 'Uses Fourier Transform to find cycle lows within established trends.',
                items: [
                    { label: 'Perfect Buy', text: 'Cycle Bottom + Uptrend + Green Candle.' },
                    { label: 'Perfect Short', text: 'Cycle Top + Downtrend.' }
                ]
            }
        ]
    },
    turtle: {
        id: 'turtle',
        name: 'Turtle Trading',
        endpoint: '/screen/turtle',
        description: 'Classic trend following strategy based on 20-day breakouts (Donchian Channels).',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Turtle Rules',
                desc: 'Buy 20-day highs, sell 10-day lows.',
                items: [
                    { label: 'Breakout', text: 'Price > 20-Day High.' },
                    { label: 'Stop Loss', text: '2 ATR below entry.' }
                ]
            }
        ]
    },
    isa: {
        id: 'isa',
        name: 'ISA Trend Follower',
        endpoint: '/screen/isa',
        description: 'Long-term trend following for tax-free growth accounts. Buys 50-day highs in 200-day uptrends.',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'ISA Growth',
                desc: 'Long-term compounding in tax-free accounts.',
                items: [
                    { label: 'Trend Alignment', text: 'Price > 50 SMA > 200 SMA.' },
                    { label: 'Trigger', text: 'New 50-Day High.' }
                ]
            }
        ]
    },
    bull_put: {
        id: 'bull_put',
        name: 'Bull Put Spreads',
        endpoint: '/screen/bull_put',
        description: 'Income generation strategy selling credit spreads on bullish stocks.',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Options Income',
                desc: 'Selling insurance on bullish stocks.',
                items: [
                    { label: 'Setup', text: 'Uptrending stock with decent IV.' },
                    { label: 'Win Condition', text: 'Stock stays above the short strike.' }
                ]
            }
        ]
    },
    darvas: {
        id: 'darvas',
        name: 'Darvas Box',
        endpoint: '/screen/darvas',
        description: 'Momentum strategy identifying stocks breaking out of consolidated "boxes" near 52-week highs.',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Darvas Box',
                desc: 'Momentum trading breaking out of consolidation.',
                items: [
                    { label: 'Box Top', text: 'Resistance level.' },
                    { label: 'Box Bottom', text: 'Support/Stop level.' }
                ]
            }
        ]
    },
    ema: {
        id: 'ema',
        name: 'EMA Momentum',
        endpoint: '/screen/ema',
        description: 'Short-term momentum trading using 5/13 and 5/21 EMA crossovers.',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'EMA Cross',
                desc: 'Fast moving averages for quick momentum.',
                items: [
                    { label: '5/13 Cross', text: 'Short term momentum trigger.' },
                    { label: 'Blue Zone', text: 'Trending strongly.' }
                ]
            }
        ]
    },
    mms: {
        id: 'mms',
        name: 'MMS / OTE',
        endpoint: '/screen/mms',
        description: 'Smart Money Concepts: Market Maker Buy Models and Optimal Trade Entries (Fibonacci).',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Smart Money',
                desc: 'Trading with the institutions using liquidity concepts.',
                items: [
                    { label: 'OTE', text: 'Optimal Trade Entry (62-79% Retracement).' },
                    { label: 'FVG', text: 'Fair Value Gap (Imbalance).' }
                ]
            }
        ]
    },
    fourier: {
        id: 'fourier',
        name: 'Fourier Cycles',
        endpoint: '/screen/fourier',
        description: 'Uses DSP (Digital Signal Processing) to identify cyclical lows and highs.',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Harmonic Cycles',
                desc: 'Physics-based cycle analysis.',
                items: [
                    { label: 'Trough', text: 'Cycle Bottom (Buy Zone).' },
                    { label: 'Peak', text: 'Cycle Top (Sell Zone).' }
                ]
            }
        ]
    },
    quantum: {
        id: 'quantum',
        name: 'Quantum',
        endpoint: '/screen/quantum',
        description: 'Advanced physics-based analysis using Hurst Exponent, Entropy, and Kalman Filters.',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Quantum Physics',
                desc: 'Statistical mechanics applied to price.',
                items: [
                    { label: 'Hurst > 0.6', text: 'Strong Trending behavior.' },
                    { label: 'Entropy < 3.0', text: 'Organized market structure.' }
                ]
            }
        ]
    },
    fortress: {
        id: 'fortress',
        name: 'Fortress (Vol)',
        endpoint: '/screen/fortress',
        description: 'Dynamic Volatility strategy optimizing yield based on VIX regime. (US Only)',
        params: ['region', 'time_frame'],
        legend: [
            {
                title: 'Volatility Fortress',
                desc: 'Defensive income generation.',
                items: [
                    { label: 'Safety Factor', text: 'Multiplies ATR based on VIX.' },
                    { label: 'Strike', text: 'Dynamically adjusted safe strike.' }
                ]
            }
        ]
    }
};

const Screener: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any[]>([]);
    const [regime, setRegime] = useState<string>('WAITING');
    const [error, setError] = useState<string | null>(null);
    const [region, setRegion] = useState('us_uk_mix');
    const [timeFrame, setTimeFrame] = useState('1d');
    const [selectedStrategy, setSelectedStrategy] = useState<string>('grandmaster');

    // Sorting State
    const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>({ key: 'Score', direction: 'desc' });

    // Filter State
    const [filterText, setFilterText] = useState('');

    // Backtest State
    const [backtestTicker, setBacktestTicker] = useState('');
    const [backtestStrategy, setBacktestStrategy] = useState('grandmaster');
    const [backtestResult, setBacktestResult] = useState<any | null>(null);
    const [btLoading, setBtLoading] = useState(false);

    const handleRunScreener = async () => {
        setLoading(true);
        setError(null);
        setResults([]);
        setRegime('WAITING');

        const strategy = STRATEGIES[selectedStrategy];
        let url = `${strategy.endpoint}?`;

        if (strategy.params.includes('region')) {
            url += `region=${region}&`;
        }
        if (strategy.params.includes('time_frame')) {
            url += `time_frame=${timeFrame}&`;
        }

        try {
            const res = await fetch(url);
            const data = await res.json();

            if (data.error) {
                setError(data.error);
                return;
            }

            let finalResults = [];
            if (data.results && Array.isArray(data.results)) {
                finalResults = data.results;
            } else if (Array.isArray(data)) {
                finalResults = data;
            } else if (typeof data === 'object') {
                 if (Object.values(data).every(v => Array.isArray(v))) {
                     Object.values(data).forEach((arr: any) => {
                         finalResults.push(...arr);
                     });
                 } else {
                     finalResults = [data];
                 }
            }

            if (data.regime) setRegime(data.regime);
            else if (data.Regime) setRegime(data.Regime);
            else if (finalResults.length > 0) {
                if (finalResults[0].regime) setRegime(finalResults[0].regime);
                if (finalResults[0].Regime) setRegime(finalResults[0].Regime);
            }

            setResults(finalResults);

        } catch (err: any) {
            setError('System Error: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleBacktest = async () => {
        if (!backtestTicker) return;
        setBtLoading(true);
        setBacktestResult(null);
        try {
            const res = await fetch(`/backtest/run?ticker=${backtestTicker}&strategy=${backtestStrategy}`);
            const data = await res.json();
            if (data.error) {
                setError("Backtest Failed: " + data.error);
            } else {
                setBacktestResult(data);
                setError(null);
            }
        } catch (err: any) {
            setError("Backtest Error: " + err.message);
        } finally {
            setBtLoading(false);
        }
    };

    // --- SORTING LOGIC ---
    const handleSort = (key: string) => {
        let direction: 'asc' | 'desc' = 'asc';
        if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    // --- MEMOIZED RESULTS (SORTING + FILTERING) ---
    const sortedResults = useMemo(() => {
        let processed = [...results];

        // 1. Filter
        if (filterText) {
            const lowerFilter = filterText.toLowerCase();
            processed = processed.filter(row => {
                return Object.values(row).some(val =>
                    String(val).toLowerCase().includes(lowerFilter)
                );
            });
        }

        // 2. Sort
        if (sortConfig !== null) {
            processed.sort((a, b) => {
                let aVal = a[sortConfig.key] || a[sortConfig.key.toLowerCase()];
                let bVal = b[sortConfig.key] || b[sortConfig.key.toLowerCase()];

                // Special handling for Risk Plan (Target as proxy)
                if (sortConfig.key === 'RiskPlan') {
                     aVal = a.Target || a.target || 0;
                     bVal = b.Target || b.target || 0;
                }

                // Special handling for Breakout (breakout_date)
                if (sortConfig.key === 'Breakout') {
                    aVal = a.Breakout || a.breakout_date || '';
                    bVal = b.Breakout || b.breakout_date || '';
                }

                // Handle nested access or differing casing
                if (sortConfig.key === 'Setup') {
                    aVal = a.Setup || a.verdict || a.signal || a.Strategy || 'WAIT';
                    bVal = b.Setup || b.verdict || b.signal || b.Strategy || 'WAIT';
                }
                if (sortConfig.key === 'Action') {
                    aVal = a.Action || a.action || a.Score || 0;
                    bVal = b.Action || b.action || b.Score || 0;
                }

                // Numeric conversion
                // Use Number() to avoid partial parsing (e.g. "2023-10-25" -> 2023)
                const aNum = Number(aVal);
                const bNum = Number(bVal);

                if (!isNaN(aNum) && !isNaN(bNum) && aVal !== '' && bVal !== '') {
                    aVal = aNum;
                    bVal = bNum;
                } else {
                    // String fallback
                    aVal = String(aVal || '').toLowerCase();
                    bVal = String(bVal || '').toLowerCase();
                }

                if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }
        return processed;
    }, [results, sortConfig, filterText]);

    const SortIcon = ({ colKey }: { colKey: string }) => {
        if (sortConfig?.key !== colKey) return <i className="bi bi-arrow-down-up text-gray-300 ml-1 text-[10px]"></i>;
        return sortConfig.direction === 'asc' ?
            <i className="bi bi-arrow-up-short text-blue-500 ml-1"></i> :
            <i className="bi bi-arrow-down-short text-blue-500 ml-1"></i>;
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
            <header className="mb-8">
                <h1 className="text-4xl font-black text-gray-900 dark:text-white tracking-tight">
                    MARKET <span className="text-blue-600">SCREENER</span>
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2 text-lg">
                    Institutional grade scanning for high-probability setups.
                </p>

                <div className="mt-4 flex items-center gap-3">
                    <span className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Market Regime:
                    </span>
                    <span className={`px-4 py-1.5 rounded-full text-sm font-bold shadow-sm transition-all ${
                        regime.includes('BULL') || regime.includes('GREEN') ? 'bg-green-100 text-green-800 border border-green-200' :
                        regime.includes('BEAR') || regime.includes('RED') ? 'bg-red-100 text-red-800 border border-red-200' :
                        'bg-gray-200 text-gray-800 border border-gray-300'
                    }`}>
                        {regime}
                    </span>
                </div>
            </header>

            {/* CONTROLS */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mb-8 border border-gray-100 dark:border-gray-700">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div>
                        <label htmlFor="strategy-select" className="block text-xs font-semibold text-gray-500 uppercase mb-2">Strategy</label>
                        <select
                            id="strategy-select"
                            value={selectedStrategy}
                            onChange={(e) => setSelectedStrategy(e.target.value)}
                            className="w-full bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                        >
                            {Object.entries(STRATEGIES).map(([key, s]) => (
                                <option key={key} value={key}>{s.name}</option>
                            ))}
                        </select>
                    </div>

                    {STRATEGIES[selectedStrategy].params.includes('region') && (
                        <div>
                            <label htmlFor="region-select" className="block text-xs font-semibold text-gray-500 uppercase mb-2">Region</label>
                            <select
                                id="region-select"
                                value={region}
                                onChange={(e) => setRegion(e.target.value)}
                                className="w-full bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                            >
                                <option value="us">🇺🇸 United States (S&P 500)</option>
                                <option value="united_states">🇺🇸 United States (Sectors & Liquid)</option>
                                <option value="uk">🇬🇧 United Kingdom (FTSE)</option>
                                <option value="uk_euro">🇪🇺 UK & Europe</option>
                                <option value="india">🇮🇳 India (NSE)</option>
                            </select>
                        </div>
                    )}

                    {STRATEGIES[selectedStrategy].params.includes('time_frame') && (
                        <div>
                            <label htmlFor="timeframe-select" className="block text-xs font-semibold text-gray-500 uppercase mb-2">Time Frame</label>
                            <select
                                id="timeframe-select"
                                value={timeFrame}
                                onChange={(e) => setTimeFrame(e.target.value)}
                                className="w-full bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
                            >
                                <option value="1d">Daily (Swing)</option>
                                <option value="1h">1 Hour (Intraday)</option>
                                <option value="4h">4 Hour (Swing)</option>
                                <option value="1wk">Weekly (Position)</option>
                                <option value="1mo">Monthly (Macro)</option>
                            </select>
                        </div>
                    )}

                    <div className="flex items-end">
                        <button
                            onClick={handleRunScreener}
                            disabled={loading}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 px-6 rounded-lg shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
                        >
                            {loading ? 'Running...' : 'RUN SCANNER'}
                        </button>
                    </div>
                </div>

                 <div className="mt-4 text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 p-3 rounded-lg border border-gray-100 dark:border-gray-700">
                    <i className="bi bi-info-circle mr-2"></i>
                    {STRATEGIES[selectedStrategy].description}
                </div>
            </div>

            {/* ERROR MESSAGE */}
            {error && (
                <div className="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 p-4 mb-8 rounded-r-lg">
                    <div className="flex">
                        <div className="flex-shrink-0">
                            <i className="bi bi-exclamation-triangle-fill text-red-500"></i>
                        </div>
                        <div className="ml-3">
                            <p className="text-sm text-red-700 dark:text-red-200 font-medium">{error}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* SEARCH / FILTER INPUT */}
            {results.length > 0 && (
                <div className="mb-4">
                    <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i className="bi bi-search text-gray-400"></i>
                        </div>
                        <input
                            type="text"
                            className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg leading-5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                            placeholder="Filter results (e.g. 'BUY', 'AAPL', 'Technology')..."
                            value={filterText}
                            onChange={(e) => setFilterText(e.target.value)}
                        />
                    </div>
                    <p className="text-xs text-gray-500 mt-1 ml-1">
                        Showing {sortedResults.length} of {results.length} results
                    </p>
                </div>
            )}

            {/* RESULTS TABLE */}
            {results.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl overflow-hidden border border-gray-200 dark:border-gray-700">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-gray-100 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                                    <th onClick={() => handleSort('Ticker')} className="cursor-pointer px-6 py-4 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Ticker <SortIcon colKey="Ticker" /></th>
                                    <th onClick={() => handleSort('Price')} className="cursor-pointer px-6 py-4 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider text-right">Price <SortIcon colKey="Price" /></th>

                                    {/* NEW COLUMN: ATR */}
                                    <th onClick={() => handleSort('ATR')} className="cursor-pointer px-6 py-4 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider text-right">ATR <SortIcon colKey="ATR" /></th>

                                    {/* NEW COLUMN: BREAKOUT */}
                                    <th onClick={() => handleSort('Breakout')} className="cursor-pointer px-6 py-4 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Breakout <SortIcon colKey="Breakout" /></th>

                                    <th onClick={() => handleSort('Setup')} className="cursor-pointer px-6 py-4 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Strategy / Verdict <SortIcon colKey="Setup" /></th>

                                    {/* NEW COLUMN: RISK PLAN (Stop/Target) */}
                                    <th onClick={() => handleSort('RiskPlan')} className="cursor-pointer px-6 py-4 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider text-right">Risk Plan <SortIcon colKey="RiskPlan" /></th>

                                    <th onClick={() => handleSort('Action')} className="cursor-pointer px-6 py-4 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Action <SortIcon colKey="Action" /></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                                {sortedResults.map((r, i) => {
                                    const verdict = r.Setup || r.verdict || r.signal || r.Strategy || 'WAIT';
                                    const currencySymbol = getCurrencySymbol(r.Ticker || r.ticker);

                                    // Helper for Stop/Target styling
                                    const stopVal = r.Stop || r.stop || 0;
                                    const targetVal = r.Target || r.target || 0;
                                    const atrVal = r.ATR || r.atr || 0;
                                    const breakoutDate = r.Breakout || r.breakout_date || '-';
                                    const companyName = r.company_name || r.name || r.Ticker || r.ticker;

                                    return (
                                        <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                                            <td className="px-6 py-4 font-bold font-mono text-gray-900 dark:text-gray-100" title={companyName}>
                                                <div className="flex flex-col">
                                                    <span>{r.Ticker || r.ticker}</span>
                                                    {/* Optional: Show company name in small text below ticker if desired, but request asked for hover */}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-right font-mono text-gray-700 dark:text-gray-300">{formatCurrency(r.Price || r.price, currencySymbol)}</td>

                                            {/* ATR DATA */}
                                            <td className="px-6 py-4 text-right font-mono text-xs text-gray-500">
                                                {atrVal ? atrVal.toFixed(2) : '-'}
                                            </td>

                                            {/* BREAKOUT DATE */}
                                            <td className="px-6 py-4 text-xs text-gray-600 dark:text-gray-400">
                                                <span className={`px-2 py-1 rounded border ${breakoutDate === 'Consolidating' ? 'border-gray-200 bg-gray-50' : 'border-blue-200 bg-blue-50 text-blue-700'}`}>
                                                    {breakoutDate}
                                                </span>
                                            </td>

                                            <td className="px-6 py-4">
                                                <span className="px-3 py-1 rounded text-xs font-bold uppercase tracking-wide bg-gray-100 text-gray-800">
                                                    {verdict}
                                                </span>
                                            </td>

                                            {/* RISK PLAN DATA */}
                                            <td className="px-6 py-4 text-right">
                                                <div className="flex flex-col items-end gap-1">
                                                    <span className="text-xs text-green-600 bg-green-50 px-1.5 py-0.5 rounded font-mono">
                                                        T: {targetVal ? formatCurrency(targetVal, currencySymbol) : '-'}
                                                    </span>
                                                    <span className="text-xs text-red-600 bg-red-50 px-1.5 py-0.5 rounded font-mono">
                                                        S: {stopVal ? formatCurrency(stopVal, currencySymbol) : '-'}
                                                    </span>
                                                </div>
                                            </td>

                                            <td className="px-6 py-4 text-sm font-bold text-gray-900 dark:text-white">
                                                {r.Action || 'VIEW'}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* LEGEND */}
            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
                {STRATEGIES[selectedStrategy].legend.map((l, i) => (
                    <div key={i} className="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700">
                        <h3 className="font-bold text-gray-900 dark:text-white mb-2">{l.title}</h3>
                        <p className="text-sm text-gray-500 mb-4">{l.desc}</p>
                        <ul className="space-y-2">
                            {l.items.map((item, j) => (
                                <li key={j} className="flex items-start text-sm">
                                    <span className="font-bold text-gray-700 dark:text-gray-300 w-24 flex-shrink-0">{item.label}:</span>
                                    <span className="text-gray-600 dark:text-gray-400">{item.text}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>

            {/* BACKTEST SECTION - FIXED KEYS FOR GRANDMASTER */}
            <div className="mt-12 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 border border-gray-200 dark:border-gray-700">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Strategy Backtest</h2>
                <div className="flex flex-col md:flex-row gap-4 mb-6">
                    <input
                        type="text"
                        placeholder="Enter Ticker (e.g. TSLA)"
                        value={backtestTicker}
                        onChange={(e) => setBacktestTicker(e.target.value.toUpperCase())}
                        className="flex-1 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-2 text-gray-900 dark:text-white uppercase font-bold"
                    />
                    <select
                        value={backtestStrategy}
                        onChange={(e) => setBacktestStrategy(e.target.value)}
                        className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-2 text-gray-900 dark:text-white"
                    >
                        {Object.entries(STRATEGIES).map(([key, s]) => (
                            <option key={key} value={key}>{s.name}</option>
                        ))}
                    </select>
                    <button
                        onClick={handleBacktest}
                        disabled={btLoading}
                        className="bg-purple-600 hover:bg-purple-700 text-white font-bold px-8 py-2 rounded-lg transition-colors disabled:opacity-50"
                    >
                        {btLoading ? 'Testing...' : 'Run Backtest'}
                    </button>
                </div>

                {backtestResult && (
                    <div className="bg-gray-50 dark:bg-gray-700/30 p-6 rounded-lg border border-gray-100 dark:border-gray-700">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                            <div>
                                <p className="text-xs text-gray-500 uppercase">Strategy Return</p>
                                <p className={`text-xl font-bold ${(backtestResult.strategy_return || backtestResult.total_return_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {(backtestResult.strategy_return ?? backtestResult.total_return_pct ?? 0).toFixed(2)}%
                                </p>
                                <p className="text-xs text-gray-400 mt-1">
                                    {(backtestResult.total_days_held ?? 0)} days in market
                                </p>
                            </div>
                            <div>
                                <p className="text-xs text-gray-500 uppercase">Buy & Hold Return</p>
                                <p className={`text-xl font-bold ${(backtestResult.buy_hold_return_pct ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {(backtestResult.buy_hold_return_pct ?? 0).toFixed(2)}%
                                </p>
                                <p className="text-xs text-gray-400 mt-1">
                                    {(backtestResult.buy_hold_days ?? 0)} days held
                                </p>
                            </div>
                            <div>
                                <p className="text-xs text-gray-500 uppercase">Win Rate</p>
                                <p className="text-xl font-bold text-gray-900 dark:text-white">
                                    {String(backtestResult.win_rate ?? backtestResult.win_rate_pct ?? '0').replace('%', '')}%
                                </p>
                            </div>
                            <div>
                                <p className="text-xs text-gray-500 uppercase">Trades</p>
                                <p className="text-xl font-bold text-gray-900 dark:text-white">
                                    {backtestResult.trades ?? backtestResult.total_trades ?? 0}
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
                            <button
                                onClick={() => navigate('/results', { state: { results: backtestResult } })}
                                className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 font-bold bg-blue-50 dark:bg-blue-900/30 px-4 py-2 rounded-lg transition-colors"
                            >
                                <i className="bi bi-bar-chart-fill mr-2"></i>
                                View Full Analysis & Equity Curve
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Screener;
