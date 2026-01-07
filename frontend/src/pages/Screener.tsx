import React, { useState } from 'react';
import { formatCurrency } from '../utils/formatting';

const STRATEGIES: Record<string, {
    id: string;
    name: string;
    endpoint: string;
    description: string;
    params: string[];
    legend: { title: string; desc: string; items: { label: string; text: string }[] }[];
}> = {
    master: {
        id: 'master',
        name: 'Master Protocol',
        endpoint: '/screen/master',
        description: 'The Council Protocol. Aggregates multiple strategies (Trend, Cycle, Momentum) to find high-confluence setups.',
        params: ['region'],
        legend: [
            {
                title: 'Master Convergence',
                desc: 'Identifies setups where multiple independent strategies align.',
                items: [
                    { label: 'Strong Buy', text: 'Confluence of Trend, Cycle Bottom, and Momentum.' },
                    { label: 'Caution', text: 'Strategies are conflicting.' }
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
        params: ['region'],
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
        params: ['region'],
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
        params: ['region'],
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
        params: [],
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
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any[]>([]);
    const [regime, setRegime] = useState<string>('WAITING');
    const [error, setError] = useState<string | null>(null);
    const [region, setRegion] = useState('us_uk_mix');
    const [timeFrame, setTimeFrame] = useState('1d');
    const [selectedStrategy, setSelectedStrategy] = useState<string>('master');

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

            // Normalize results
            let finalResults = [];
            if (data.results && Array.isArray(data.results)) {
                finalResults = data.results;
            } else if (Array.isArray(data)) {
                finalResults = data;
            } else if (typeof data === 'object') {
                 // Check for sector grouping or other structures
                 // If it is grouped by sector (dict), flatten it for now
                 if (Object.values(data).every(v => Array.isArray(v))) {
                     Object.values(data).forEach((arr: any) => {
                         finalResults.push(...arr);
                     });
                 } else {
                     // Maybe it's just the object itself?
                     finalResults = [data];
                 }
            }

            if (data.regime) {
                setRegime(data.regime);
            } else if (finalResults.length > 0 && finalResults[0].regime) {
                setRegime(finalResults[0].regime);
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

    const currentStrategy = STRATEGIES[selectedStrategy];

    // Helper to extract display values safely
    const getVerdict = (r: any) => r.verdict || r.signal || r.human_verdict || 'WAIT';
    const getAction = (r: any) => r.action || (r.signal && r.signal.includes('BUY') ? 'BUY' : '-') || '-';

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
            <header className="mb-8">
                <h1 className="text-4xl font-black text-gray-900 dark:text-white tracking-tight">
                    THE COUNCIL <span className="text-primary-600">PROTOCOL</span>
                </h1>
                <p className="text-gray-500 mt-2 font-mono text-sm uppercase tracking-wider">
                    Automated Risk Management & Setup Detection
                </p>
            </header>

            {/* STRATEGY SELECTOR */}
            <div className="mb-6 overflow-x-auto pb-2">
                <div className="flex gap-2 min-w-max">
                    {Object.values(STRATEGIES).map((s) => (
                        <button
                            key={s.id}
                            onClick={() => setSelectedStrategy(s.id)}
                            className={`px-4 py-2 rounded-lg text-sm font-bold transition-all whitespace-nowrap ${
                                selectedStrategy === s.id
                                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30'
                                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                        >
                            {s.name}
                        </button>
                    ))}
                </div>
            </div>

            {/* CONTROLS CARD */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700 mb-8">
                <div className="mb-4">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1">{currentStrategy.name}</h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{currentStrategy.description}</p>
                </div>

                <div className="flex flex-col md:flex-row gap-4 items-end">
                    {currentStrategy.params.includes('region') && (
                        <div className="flex-1">
                            <label className="block text-xs font-bold uppercase text-gray-500 mb-1">Universe</label>
                            <select
                                value={region}
                                onChange={(e) => setRegion(e.target.value)}
                                className="w-full bg-gray-100 border-none rounded-lg p-3 font-bold text-gray-900 dark:bg-gray-700 dark:text-white"
                            >
                                <option value="us_uk_mix">Global Mix</option>
                                <option value="us">United States (Liquid)</option>
                                <option value="sp500">S&P 500</option>
                                <option value="uk">UK (LSE)</option>
                                <option value="india">India (NSE)</option>
                            </select>
                        </div>
                    )}

                    {currentStrategy.params.includes('time_frame') && (
                         <div className="flex-1">
                            <label className="block text-xs font-bold uppercase text-gray-500 mb-1">Time Frame</label>
                            <select
                                value={timeFrame}
                                onChange={(e) => setTimeFrame(e.target.value)}
                                className="w-full bg-gray-100 border-none rounded-lg p-3 font-bold text-gray-900 dark:bg-gray-700 dark:text-white"
                            >
                                <option value="1d">Daily (1D)</option>
                                <option value="1wk">Weekly (1W)</option>
                                <option value="1h">Hourly (1H)</option>
                                <option value="15m">15 Minutes</option>
                            </select>
                        </div>
                    )}

                    <button
                        onClick={handleRunScreener}
                        disabled={loading}
                        className="px-8 py-3 bg-black dark:bg-white dark:text-black text-white font-bold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 min-w-[150px]"
                    >
                        {loading ? 'SCANNING...' : 'RUN SCAN'}
                    </button>
                </div>

                {/* STATUS BAR */}
                <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 flex gap-6 text-xs font-mono text-gray-500">
                     <span>RESULTS: {results.length}</span>
                     {regime !== 'WAITING' && (
                        <span className={regime.includes("RED") ? "text-red-500 font-bold" : ""}>
                            REGIME: {regime}
                        </span>
                     )}
                </div>
            </div>

            {error && <div className="p-4 bg-red-100 text-red-800 rounded-lg mb-6">{error}</div>}

            {results.length > 0 && (
                <div className="overflow-x-auto rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 mb-8">
                    <table className="w-full text-sm text-left text-gray-600 dark:text-gray-300">
                        <thead className="text-xs text-gray-500 uppercase bg-gray-100 dark:bg-gray-800 border-b dark:border-gray-700">
                            <tr>
                                <th className="px-6 py-4">Ticker</th>
                                <th className="px-6 py-4">Price</th>
                                <th className="px-6 py-4">Verdict / Signal</th>
                                <th className="px-6 py-4">Stop / Risk</th>
                                <th className="px-6 py-4">Target / Info</th>
                                <th className="px-6 py-4">Breakout</th>
                                <th className="px-6 py-4 text-right">Details</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
                            {results.map((r, i) => {
                                // Common fields
                                const ticker = r?.ticker || 'UNKNOWN';
                                const company = r?.company_name || '';
                                const price = r?.price;
                                const currency = ticker.includes && (ticker.includes('.L') || ticker.endsWith('.L')) ? '£' : '$';

                                const verdict = getVerdict(r);
                                const stop = r?.stop_loss || r?.stop_price || r?.floor_level || '-';
                                const target = r?.target || r?.target_price || r?.breakout_level || '-';
                                const breakout = r?.breakout_date || '-';

                                // Dynamic details based on strategy
                                let details = '';
                                if (selectedStrategy === 'quantum') details = `H: ${r.hurst?.toFixed(2)} | E: ${r.entropy?.toFixed(2)}`;
                                else if (selectedStrategy === 'bull_put') details = `Credit: ${r.credit} | ROI: ${r.roi_pct}%`;
                                else if (selectedStrategy === 'master') details = `Score: ${r.confluence_score}/3`;
                                else if (selectedStrategy === 'hybrid') details = `Score: ${r.score} | Cycle: ${r.cycle}`;
                                else if (selectedStrategy === 'fourier') details = `Phase: ${r.cycle_phase} | Str: ${r.cycle_strength}`;
                                else if (selectedStrategy === 'fortress') details = `Strike: ${r.sell_strike} | Saf: ${r.safety_mult}`;
                                else details = `Vol: ${r.volatility_pct}% | ATR: ${r.atr_value}`;

                                // Color coding verdict
                                let badgeColor = 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
                                const vUpper = String(verdict).toUpperCase();
                                if (vUpper.includes('BUY') || vUpper.includes('LONG') || vUpper.includes('GREEN') || vUpper.includes('BREAKOUT')) badgeColor = 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
                                if (vUpper.includes('SELL') || vUpper.includes('SHORT') || vUpper.includes('RED') || vUpper.includes('EXIT')) badgeColor = 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
                                if (vUpper.includes('WAIT') || vUpper.includes('WATCH')) badgeColor = 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';

                                return (
                                    <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                                        <td className="px-6 py-4 font-bold font-mono text-gray-900 dark:text-white">
                                            {ticker}
                                            <div className="text-[10px] text-gray-400 font-normal truncate max-w-[150px]">{company}</div>
                                        </td>
                                        <td className="px-6 py-4 font-mono">{formatCurrency(price, currency)}</td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded text-xs font-bold ${badgeColor}`}>
                                                {verdict}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 font-mono text-red-500">{typeof stop === 'number' ? formatCurrency(stop, currency) : stop}</td>
                                        <td className="px-6 py-4 font-mono text-emerald-500">{typeof target === 'number' ? formatCurrency(target, currency) : target}</td>
                                        <td className="px-6 py-4 font-mono text-xs text-gray-500">{breakout}</td>
                                        <td className="px-6 py-4 text-right font-mono text-xs text-gray-400">{details}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* BACKTEST LAB SECTION */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700 mb-8">
                <h3 className="text-lg font-black text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    <span className="text-xl">🧪</span> STRATEGY LAB (BACKTEST)
                </h3>
                <div className="flex flex-col md:flex-row gap-4 items-end mb-4">
                    <div className="flex-1">
                        <label className="block text-xs font-bold uppercase text-gray-500 mb-1">Ticker</label>
                        <input
                            type="text"
                            value={backtestTicker}
                            onChange={(e) => setBacktestTicker(e.target.value.toUpperCase())}
                            placeholder="e.g. NVDA"
                            className="w-full bg-gray-100 border-none rounded-lg p-3 font-bold text-gray-900 dark:bg-gray-700 dark:text-white uppercase"
                        />
                    </div>
                    <div className="flex-1">
                        <label className="block text-xs font-bold uppercase text-gray-500 mb-1">Strategy</label>
                        <select
                            value={backtestStrategy}
                            onChange={(e) => setBacktestStrategy(e.target.value)}
                            className="w-full bg-gray-100 border-none rounded-lg p-3 font-bold text-gray-900 dark:bg-gray-700 dark:text-white"
                        >
                            <option value="grandmaster">Grandmaster (Council Protocol)</option>
                            <option value="turtle">Turtle (20-Day Breakout)</option>
                            <option value="isa">ISA Classic (Trend)</option>
                        </select>
                    </div>
                    <button
                        onClick={handleBacktest}
                        disabled={btLoading || !backtestTicker}
                        className="px-8 py-3 bg-indigo-600 text-white font-bold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
                    >
                        {btLoading ? 'RUNNING SIM...' : 'BACKTEST'}
                    </button>
                </div>

                {backtestResult && (
                    <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-center">
                            <div className="p-3 bg-white dark:bg-gray-800 rounded shadow-sm">
                                <div className="text-xs text-gray-500 uppercase">Strategy Return</div>
                                <div className={`text-xl font-black ${backtestResult.strategy_return >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                    {backtestResult.strategy_return}%
                                </div>
                            </div>
                            <div className="p-3 bg-white dark:bg-gray-800 rounded shadow-sm">
                                <div className="text-xs text-gray-500 uppercase">Buy & Hold</div>
                                <div className="text-xl font-bold text-gray-700 dark:text-gray-300">
                                    {backtestResult.buy_hold_return}%
                                </div>
                            </div>
                            <div className="p-3 bg-white dark:bg-gray-800 rounded shadow-sm">
                                <div className="text-xs text-gray-500 uppercase">Win Rate</div>
                                <div className="text-xl font-bold text-indigo-500">
                                    {backtestResult.win_rate}
                                </div>
                            </div>
                            <div className="p-3 bg-white dark:bg-gray-800 rounded shadow-sm">
                                <div className="text-xs text-gray-500 uppercase">Trades</div>
                                <div className="text-xl font-bold text-gray-700 dark:text-gray-300">
                                    {backtestResult.trades}
                                </div>
                            </div>
                        </div>

                        {backtestResult.log && backtestResult.log.length > 0 && (
                            <div className="mt-4 max-h-60 overflow-y-auto">
                                <table className="w-full text-xs text-left text-gray-500">
                                    <thead className="text-xs text-gray-400 uppercase bg-gray-100 dark:bg-gray-800 sticky top-0">
                                        <tr>
                                            <th className="px-4 py-2">Date</th>
                                            <th className="px-4 py-2">Type</th>
                                            <th className="px-4 py-2">Price</th>
                                            <th className="px-4 py-2">Reason</th>
                                            <th className="px-4 py-2 text-right">Equity</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                        {backtestResult.log.slice().reverse().map((trade: any, i: number) => (
                                            <tr key={i} className="hover:bg-white dark:hover:bg-gray-800">
                                                <td className="px-4 py-2">{trade.date}</td>
                                                <td className={`px-4 py-2 font-bold ${trade.type === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>{trade.type}</td>
                                                <td className="px-4 py-2">{trade.price}</td>
                                                <td className="px-4 py-2">{trade.reason || trade.stop || '-'}</td>
                                                <td className="px-4 py-2 text-right">{trade.equity || '-'}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* LEGEND / DOCS AT BOTTOM - DYNAMIC */}
            <div className="mt-12 border-t border-gray-200 dark:border-gray-700 pt-8 text-gray-500 text-sm">
                <h3 className="font-bold text-gray-900 dark:text-white mb-6 text-lg">PROTOCOL LEGEND & GLOSSARY</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {/* Dynamic Legend Items */}
                    {currentStrategy.legend.map((item, idx) => (
                         <div key={idx} className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg">
                            <h4 className="font-bold mb-3 text-indigo-600 dark:text-indigo-400">{item.title}</h4>
                            <p className="text-xs mb-3 text-gray-600 dark:text-gray-400">
                                {item.desc}
                            </p>
                            <ul className="list-disc pl-5 space-y-2 text-xs">
                                {item.items.map((sub, i) => (
                                    <li key={i}><strong>{sub.label}:</strong> {sub.text}</li>
                                ))}
                            </ul>
                        </div>
                    ))}

                    {/* General Glossary (Always Visible) */}
                    <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg">
                        <h4 className="font-bold mb-3 text-gray-900 dark:text-white">Universal Glossary</h4>
                        <dl className="space-y-3 text-xs">
                            <div>
                                <dt className="font-bold">SMA (Simple Moving Average):</dt>
                                <dd>The average price over X days. "Price &gt; 200 SMA" means the long-term trend is UP.</dd>
                            </div>
                            <div>
                                <dt className="font-bold">ATR (Average True Range):</dt>
                                <dd>Volatility measure. We use it to calculate safe Stop Losses.</dd>
                            </div>
                            <div>
                                <dt className="font-bold">RSI (Relative Strength):</dt>
                                <dd>Over 70 is Overbought (expensive), Under 30 is Oversold (cheap).</dd>
                            </div>
                        </dl>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Screener;
