import React, { useState } from 'react';
import { runMarketScreener, runTurtleScreener, runEmaScreener, runDarvasScreener, runMmsScreener, runBullPutScreener, runIsaTrendScreener, runFourierScreener, runHybridScreener } from '../api';
import clsx from 'clsx';
import { formatCurrency } from '../utils/formatting';

interface ScreenerProps { }

type ScreenerType = 'market' | 'turtle' | 'ema' | 'darvas' | 'mms' | 'bull_put' | 'isa' | 'fourier' | 'hybrid' | 'master' | 'fortress' | 'quantum';

const screenerInfo: Record<ScreenerType, { title: string; subtitle: string; description: string }> = {
    master: { title: "Master Protocol", subtitle: "High Probability Convergences", description: "Combines Regime Filters, Liquidity Gates, and Trend/Vol Logic." },
    turtle: { title: 'Turtle Trading', subtitle: 'Trend Breakouts', description: 'Classic Trend Following. Buy 20-Day Highs, Exit 10-Day Lows.' },
    isa: { title: 'ISA Trend', subtitle: 'Long Term Growth', description: 'Investment grade trend following (Price > 200 SMA) with volatility stops.' },
    fortress: { title: "Fortress Options", subtitle: "Income Generation", description: "VIX-Adjusted Bull Put Spreads on liquid US tickers." },
    quantum: { title: 'Quantum Screener', subtitle: 'Statistical Regimes', description: 'Hurst Exponent & Entropy analysis for regime detection.' },
    market: { title: 'Market Screener', subtitle: 'Volatility & RSI', description: 'Scans for IV Rank and RSI extremes.' },
    darvas: { title: 'Darvas Box', subtitle: 'Momentum Boxes', description: 'Consolidation breakouts near 52-week highs.' },
    mms: { title: 'MMS / OTE', subtitle: 'Smart Money', description: 'Market Maker Models & Optimal Trade Entries.' },
    ema: { title: 'EMA Crossovers', subtitle: 'Trend Following', description: '5/13 & 5/21 EMA Crossovers.' },
    bull_put: { title: 'Bull Put (Classic)', subtitle: 'Credit Spreads', description: 'Standard bullish credit spreads.' },
    fourier: { title: 'Harmonic Cycles', subtitle: 'Swing Timing', description: 'Cycle analysis to find market bottoms.' },
    hybrid: { title: 'Hybrid', subtitle: 'Trend + Cycle', description: 'Combines ISA Trend with Fourier Timing.' }
};

const StrategyTile = ({ tab, active, onClick }: { tab: { id: ScreenerType, label: string, subLabel?: string }, active: boolean, onClick: (id: ScreenerType) => void }) => (
    <button
        onClick={() => onClick(tab.id)}
        className={clsx(
            "relative flex flex-col items-start p-4 rounded-xl transition-all duration-300 border-2 w-full text-left group",
            active
                ? "bg-primary-600/10 border-primary-600 scale-[1.02] shadow-lg"
                : "bg-gray-800 border-transparent hover:bg-gray-700 hover:translate-x-2"
        )}
    >
        <span className={clsx("text-base font-bold transition-colors", active ? "text-primary-500" : "text-white group-hover:text-gray-200")}>
            {tab.label}
        </span>
        {tab.subLabel && <span className="text-[10px] text-gray-400 mt-1 uppercase tracking-widest font-medium">{tab.subLabel}</span>}
        {active && <div className="absolute right-4 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-primary-600 animate-pulse" />}
    </button>
);

const Screener: React.FC<ScreenerProps> = () => {
    const [activeTab, setActiveTab] = useState<ScreenerType>('master');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [region, setRegion] = useState('us');

    // --- BACKTEST STATE ---
    const [btTicker, setBtTicker] = useState('');
    const [btLoading, setBtLoading] = useState(false);
    const [btResult, setBtResult] = useState<any>(null);

    const runBacktest = async () => {
        if (!btTicker) return;
        setBtLoading(true);
        setBtResult(null);
        try {
            // Use the generic /backtest/run endpoint
            const res = await fetch(`/backtest/run?ticker=${btTicker}&strategy=${activeTab}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            setBtResult(data);
        } catch (err: any) {
            alert(err.message || 'Backtest failed');
        } finally {
            setBtLoading(false);
        }
    };

    const downloadCSV = () => {
        if (!results) return;
        let dataToExport: any[] = [];
        const timestamp = new Date().toISOString().replace(/[:.]/g, '').slice(0, 15);
        let filename = `${activeTab}_scan_${timestamp}.csv`;

        if (activeTab === 'market' && results.results) {
            Object.values(results.results).forEach((arr: any) => dataToExport.push(...arr));
        } else if (Array.isArray(results)) {
            dataToExport = results;
        } else if (results.results && Array.isArray(results.results)) {
            dataToExport = results.results;
        }

        if (dataToExport.length === 0) {
            alert("No data to download.");
            return;
        }

        const headers = Object.keys(dataToExport[0]);
        const csvContent = [
            headers.join(','),
            ...dataToExport.map(row =>
                headers.map(header => {
                    let val = row[header];
                    if (val === null || val === undefined) return '';
                    const valStr = String(val);
                    if (valStr.includes(',') || valStr.includes('\n')) return `"${valStr.replace(/"/g, '""')}"`;
                    return valStr;
                }).join(',')
            )
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
    };

    const handleRunScreener = async () => {
        setLoading(true);
        setError(null);
        setResults(null);
        try {
            let data;
            if (activeTab === 'master') {
                const res = await fetch(`/screen/master?region=${region}`);
                data = await res.json();
            } else if (activeTab === 'fortress') {
                const res = await fetch(`/screen/fortress`);
                data = await res.json();
            } else if (activeTab === 'quantum') {
                const res = await fetch(`/screen/quantum?region=${region}`);
                data = await res.json();
            } else if (activeTab === 'market') {
                data = await runMarketScreener(30, 50, '1d', region);
            } else if (activeTab === 'turtle') {
                data = await runTurtleScreener(region, '1d');
            } else if (activeTab === 'isa') {
                const response = await runIsaTrendScreener(region);
                data = response.results || response;
            } else if (activeTab === 'bull_put') {
                data = await runBullPutScreener(region);
            } else if (activeTab === 'fourier') {
                data = await runFourierScreener(region, '1d');
            } else if (activeTab === 'hybrid') {
                data = await runHybridScreener(region, '1d');
            } else if (activeTab === 'ema') {
                data = await runEmaScreener(region, '1d');
            } else if (activeTab === 'darvas') {
                data = await runDarvasScreener(region, '1d');
            } else if (activeTab === 'mms') {
                data = await runMmsScreener(region, '1d');
            }
            setResults(data);
        } catch (err: any) {
            setError(err.message || 'Screener failed. Ensure backend is running.');
        } finally {
            setLoading(false);
        }
    };

    const tabs: { id: ScreenerType; label: string; subLabel?: string }[] = [
        { id: 'master', label: '⚡ Master Screen', subLabel: 'Best of All' },
        { id: 'isa', label: 'ISA Trend', subLabel: 'Growth' },
        { id: 'turtle', label: 'Turtle Trading', subLabel: 'Classic' },
        { id: 'fortress', label: 'Options: Fortress', subLabel: 'Income' },
        { id: 'quantum', label: 'Quantum', subLabel: 'Stats' },
        { id: 'bull_put', label: 'Bull Put Spreads' },
        { id: 'market', label: 'Market Scanner' },
        { id: 'fourier', label: 'Fourier Cycles' },
        { id: 'hybrid', label: 'Hybrid' },
        { id: 'darvas', label: 'Darvas Box' },
        { id: 'mms', label: 'MMS / SMC' },
        { id: 'ema', label: 'EMA Cross' },
    ];

    // Check if current tab supports backtesting
    const showBacktest = ['master', 'turtle', 'isa'].includes(activeTab);

    return (
        <div className="flex flex-col md:flex-row gap-6 min-h-[calc(100vh-80px)]">
            <aside className="hidden md:flex md:flex-col w-64 flex-shrink-0 space-y-3 sticky top-6 h-fit">
                <h2 className="text-xl font-bold mb-4 px-2 text-gray-900 dark:text-white">Strategies</h2>
                <div className="grid grid-cols-1 gap-3">
                    {tabs.map(tab => (
                        <StrategyTile
                            key={tab.id}
                            tab={tab}
                            active={activeTab === tab.id}
                            onClick={(id) => { setActiveTab(id); setResults(null); setBtResult(null); }}
                        />
                    ))}
                </div>
            </aside>

            {/* Mobile Toggle */}
            <button className="md:hidden fixed bottom-6 right-6 z-50 p-4 bg-primary-600 text-white rounded-full shadow-lg" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" /></svg>
            </button>
            {isSidebarOpen && (
                <div className="fixed inset-0 z-40 bg-gray-900/90 p-6 md:hidden overflow-y-auto">
                    <h2 className="text-xl font-bold text-white mb-4">Select Strategy</h2>
                    <div className="space-y-2">
                        {tabs.map(tab => (
                            <div key={tab.id} onClick={() => { setActiveTab(tab.id); setIsSidebarOpen(false); setResults(null); }} className="p-3 bg-gray-800 text-white rounded-lg border border-gray-700">
                                {tab.label}
                            </div>
                        ))}
                    </div>
                    <button className="mt-6 w-full py-3 bg-gray-700 text-white rounded-lg" onClick={() => setIsSidebarOpen(false)}>Close</button>
                </div>
            )}

            <main className="flex-1 w-full max-w-full overflow-hidden">
                <div className="bg-gradient-to-r from-gray-800 to-gray-900 p-8 rounded-2xl mb-6 shadow-xl relative overflow-hidden">
                    <div className="relative z-10">
                        <h1 className="text-3xl font-black text-white">{screenerInfo[activeTab].title}</h1>
                        <p className="text-gray-300 mt-2">{screenerInfo[activeTab].description}</p>
                    </div>
                </div>

                <div className="bg-white dark:bg-gray-900 rounded-xl p-6 border border-gray-200 dark:border-gray-800 shadow-sm mb-6">
                    <div className="flex flex-col md:flex-row gap-4 justify-between items-end">
                        <div className="w-full md:w-1/3">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Region / Universe</label>
                            <select value={region} onChange={(e) => setRegion(e.target.value)} className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                                <option value="us">United States</option>
                                <option value="uk">UK (LSE)</option>
                                <option value="india">India (NSE)</option>
                            </select>
                        </div>
                        <button
                            onClick={handleRunScreener}
                            disabled={loading}
                            className="w-full md:w-auto px-8 py-3 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-lg shadow-md disabled:opacity-50 transition-all"
                        >
                            {loading ? 'Scanning...' : 'Run Screener'}
                        </button>
                    </div>
                </div>

                {/* --- STRATEGY LAB (BACKTESTER) --- */}
                {showBacktest && (
                    <div className="mb-6 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl p-6 border border-indigo-100 dark:border-indigo-800">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
                            <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
                            Strategy Lab: {screenerInfo[activeTab].title}
                        </h3>
                        <div className="flex gap-4 items-end">
                            <div className="flex-1 max-w-xs">
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Test Ticker</label>
                                <input
                                    type="text"
                                    value={btTicker}
                                    onChange={(e) => setBtTicker(e.target.value.toUpperCase())}
                                    placeholder="e.g. NVDA"
                                    className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg p-2.5 dark:bg-gray-800 dark:border-gray-600 dark:text-white uppercase font-mono font-bold"
                                />
                            </div>
                            <button
                                onClick={runBacktest}
                                disabled={btLoading || !btTicker}
                                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-sm disabled:opacity-50"
                            >
                                {btLoading ? 'Simulating...' : 'Run Backtest'}
                            </button>
                        </div>

                        {btResult && !btResult.error && (
                            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 animate-fadeIn">
                                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                                    <div className="text-xs text-gray-500 uppercase">Strategy Return</div>
                                    <div className={clsx("text-2xl font-bold", btResult.strategy_return > btResult.buy_hold_return ? "text-green-600" : "text-gray-900 dark:text-white")}>
                                        {btResult.strategy_return}%
                                    </div>
                                    <div className="text-xs text-gray-400 mt-1">vs Buy & Hold: {btResult.buy_hold_return}%</div>
                                </div>
                                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                                    <div className="text-xs text-gray-500 uppercase">Win Rate</div>
                                    <div className="text-2xl font-bold text-gray-900 dark:text-white">{btResult.win_rate}</div>
                                    <div className="text-xs text-gray-400 mt-1">{btResult.trades} Round Trips</div>
                                </div>
                                <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                                    <div className="text-xs text-gray-500 uppercase">Final Equity</div>
                                    <div className="text-2xl font-bold text-indigo-600">{formatCurrency(btResult.final_equity, '$')}</div>
                                    <div className="text-xs text-gray-400 mt-1">Start: $10,000</div>
                                </div>
                            </div>
                        )}
                        {btResult && btResult.log && (
                            <div className="mt-4 overflow-x-auto">
                                <table className="w-full text-xs text-left text-gray-500 dark:text-gray-400">
                                    <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                                        <tr>
                                            <th className="px-2 py-1">Date</th>
                                            <th className="px-2 py-1">Type</th>
                                            <th className="px-2 py-1 text-right">Price</th>
                                            <th className="px-2 py-1 text-right">Info</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {btResult.log.map((trade: any, idx: number) => (
                                            <tr key={idx} className="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
                                                <td className="px-2 py-1">{trade.date}</td>
                                                <td className={clsx("px-2 py-1 font-bold", trade.type === 'BUY' ? 'text-green-600' : 'text-red-600')}>{trade.type}</td>
                                                <td className="px-2 py-1 text-right">{trade.price}</td>
                                                <td className="px-2 py-1 text-right">{trade.reason || trade.stop}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {error && (
                    <div className="p-4 mb-6 text-sm text-red-800 bg-red-50 dark:bg-red-900/30 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800">
                        Error: {error}
                    </div>
                )}

                {results && (
                    <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                        <div className="p-4 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                            <span className="font-bold text-sm">Found {Array.isArray(results) ? results.length : 'Multiple'} Results</span>
                            <button
                                onClick={downloadCSV}
                                className="text-white bg-green-600 hover:bg-green-700 focus:ring-4 focus:ring-green-300 font-medium rounded-lg text-xs px-4 py-2 dark:bg-green-600 dark:hover:bg-green-700"
                            >
                                Download CSV ⬇️
                            </button>
                        </div>
                        <div className="overflow-x-auto p-4">
                            {activeTab === 'market' ? (
                                <pre className="text-xs">{JSON.stringify(results, null, 2)}</pre>
                            ) : (
                                <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                                    <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                                        <tr>
                                            {results[0] && Object.keys(results[0]).map(key => (
                                                <th key={key} className="px-4 py-3 whitespace-nowrap">{key.replace(/_/g, ' ')}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {Array.isArray(results) && results.map((row: any, i: number) => (
                                            <tr key={i} className="bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600">
                                                {Object.values(row).map((val: any, j) => (
                                                    <td key={j} className="px-4 py-3 font-medium whitespace-nowrap">
                                                        {typeof val === 'number' ? val.toFixed(2) : val}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
};

export default Screener;