import React, { useState, useMemo, useEffect } from 'react';
import { runMarketScreener, runTurtleScreener, runEmaScreener, runDarvasScreener, runMmsScreener, runBullPutScreener, runIsaTrendScreener, runFourierScreener, runHybridScreener } from '../api';
import clsx from 'clsx';

interface ScreenerProps { }

type ScreenerType = 'market' | 'turtle' | 'ema' | 'darvas' | 'mms' | 'bull_put' | 'isa' | 'fourier' | 'hybrid' | 'master' | 'fortress' | 'quantum';

const screenerInfo: Record<ScreenerType, { title: string; subtitle: string; description: string }> = {
    master: {
        title: "The Council's Master Screen",
        subtitle: "High Probability Convergences",
        description: "The ultimate filter. Combines 'Soros Regime' detection, 'Griffin Liquidity' gates, and separate logic for Trend (ISA) vs. Volatility Selling (Options)."
    },
    fortress: {
        title: "Fortress Options",
        subtitle: "VIX-Adjusted Spreads",
        description: "Mathematically derived Bull Put Spreads using dynamic safety multipliers based on the VIX. Targets high-liquidity US options."
    },
    quantum: {
        title: 'Quantum Screener',
        subtitle: 'Statistical Regimes',
        description: 'Utilizes Hurst Exponent and Entropy to identify market regimes (Trending vs Mean Reverting) and potential turning points.'
    },
    market: {
        title: 'Market Screener',
        subtitle: 'Volatility & RSI',
        description: 'Scans for liquid US options with specific IV Rank and RSI thresholds. Good for general idea generation.'
    },
    turtle: {
        title: 'Turtle Trading',
        subtitle: 'Trend Breakouts',
        description: 'Classic 20-Day Donchian Channel breakouts. Best for catching major trends in moving markets.'
    },
    darvas: {
        title: 'Darvas Box',
        subtitle: 'Momentum Boxes',
        description: 'Identifies consolidation "boxes" near 52-week highs. Buys when price breaks the ceiling on volume.'
    },
    mms: {
        title: 'MMS / OTE',
        subtitle: 'Smart Money Concepts',
        description: 'Identifies structural shifts and retracements into premium/discount zones (62-79%).'
    },
    ema: {
        title: 'EMA Crossovers',
        subtitle: 'Moving Average Trend',
        description: '5/13 and 5/21 Exponential Moving Average crossovers for trend catching.'
    },
    bull_put: {
        title: 'Bull Put Spreads',
        subtitle: 'Income Generation',
        description: 'Finds bullish setups suitable for selling credit spreads. Targets ~45 DTE, 30 Delta puts.'
    },
    isa: {
        title: 'ISA Trend Follower',
        subtitle: 'Long-Term Growth',
        description: 'Robust long-only strategy. Requires Price > 200 SMA and a breakout above the 50-day High.'
    },
    fourier: {
        title: 'Harmonic Cycles',
        subtitle: 'Cycle Analysis',
        description: 'Deconstructs price into sine waves to find cyclical bottoms.'
    },
    hybrid: {
        title: 'Hybrid (Trend + Cycle)',
        subtitle: 'High Probability',
        description: 'Combines ISA Trend direction with Fourier Cycle timing. "Buy the dip" in an uptrend.'
    }
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

    // Results Data
    const [results, setResults] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    // Inputs
    const [region, setRegion] = useState('us');

    // --- CSV DOWNLOADER ---
    const downloadCSV = () => {
        if (!results) return;

        let dataToExport: any[] = [];
        const timestamp = new Date().toISOString().replace(/[:.]/g, '').slice(0, 15);
        let filename = `${activeTab}_scan_${timestamp}.csv`;

        // 1. Flatten Data Structure based on Screener Type
        if (activeTab === 'market' && results.results) {
            // Market screener returns grouped results
            Object.values(results.results).forEach((arr: any) => dataToExport.push(...arr));
        } else if (Array.isArray(results)) {
            // Standard list results (Master, Turtle, etc.)
            dataToExport = results;
        } else if (results.results && Array.isArray(results.results)) {
            // ISA / Hybrid wrapper
            dataToExport = results.results;
        }

        if (dataToExport.length === 0) {
            alert("No data to download.");
            return;
        }

        // 2. Extract Headers dynamically
        const headers = Object.keys(dataToExport[0]);

        // 3. Convert to CSV String
        const csvContent = [
            headers.join(','), // Header Row
            ...dataToExport.map(row =>
                headers.map(header => {
                    let val = row[header];
                    // Handle nulls/undefined
                    if (val === null || val === undefined) return '';
                    // Handle strings with commas
                    const valStr = String(val);
                    if (valStr.includes(',') || valStr.includes('\n')) {
                        return `"${valStr.replace(/"/g, '""')}"`;
                    }
                    return valStr;
                }).join(',')
            )
        ].join('\n');

        // 4. Trigger Download
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    const handleRunScreener = async () => {
        setLoading(true);
        setError(null);
        setResults(null);
        try {
            let data;
            // Map strategy to API call
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
            setError(err.message || 'Screener failed');
        } finally {
            setLoading(false);
        }
    };

    const tabs: { id: ScreenerType; label: string; subLabel?: string }[] = [
        { id: 'master', label: '⚡ Master Screen', subLabel: 'Best of All' },
        { id: 'fortress', label: 'Options: Fortress', subLabel: 'Income' },
        { id: 'quantum', label: 'Quantum', subLabel: 'Stats' },
        { id: 'isa', label: 'ISA Trend', subLabel: 'Growth' },
        { id: 'turtle', label: 'Turtle Trading' },
        { id: 'bull_put', label: 'Bull Put Spreads' },
        { id: 'market', label: 'Market Scanner' },
        { id: 'fourier', label: 'Fourier Cycles' },
        { id: 'hybrid', label: 'Hybrid' },
        { id: 'darvas', label: 'Darvas Box' },
        { id: 'mms', label: 'MMS / SMC' },
        { id: 'ema', label: 'EMA Cross' },
    ];

    return (
        <div className="flex flex-col md:flex-row gap-6 min-h-[calc(100vh-80px)]">
            {/* Sidebar */}
            <aside className="hidden md:flex md:flex-col w-64 flex-shrink-0 space-y-3 sticky top-6 h-fit">
                <h2 className="text-xl font-bold mb-4 px-2 text-gray-900 dark:text-white">Strategies</h2>
                <div className="grid grid-cols-1 gap-3">
                    {tabs.map(tab => (
                        <StrategyTile
                            key={tab.id}
                            tab={tab}
                            active={activeTab === tab.id}
                            onClick={(id) => { setActiveTab(id); setResults(null); }}
                        />
                    ))}
                </div>
            </aside>

            {/* Mobile Sidebar Toggle */}
            <button className="md:hidden fixed bottom-6 right-6 z-50 p-4 bg-primary-600 text-white rounded-full shadow-lg" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" /></svg>
            </button>
            {isSidebarOpen && (
                <div className="fixed inset-0 z-40 bg-gray-900/90 p-6 md:hidden overflow-y-auto">
                    <h2 className="text-xl font-bold text-white mb-4">Select Strategy</h2>
                    <div className="space-y-2">
                        {tabs.map(tab => (
                            <div key={tab.id} onClick={() => { setActiveTab(tab.id); setIsSidebarOpen(false); }} className="p-3 bg-gray-800 text-white rounded-lg border border-gray-700">
                                {tab.label}
                            </div>
                        ))}
                    </div>
                    <button className="mt-6 w-full py-3 bg-gray-700 text-white rounded-lg" onClick={() => setIsSidebarOpen(false)}>Close</button>
                </div>
            )}

            {/* Main Content */}
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
                            {loading ? 'Scanning Markets...' : 'Run Screener'}
                        </button>
                    </div>
                </div>

                {error && (
                    <div className="p-4 mb-6 text-sm text-red-800 bg-red-50 dark:bg-red-900/30 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800">
                        Error: {error}
                    </div>
                )}

                {results && (
                    <div className="space-y-6 animate-fadeIn">
                        {/* Download Button Area */}
                        <div className="flex justify-end">
                            <button
                                onClick={downloadCSV}
                                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg shadow-sm transition-colors"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M12 12.75l-3-3m0 0l3-3m-3 3h12" />
                                </svg>
                                Download Results CSV
                            </button>
                        </div>

                        {/* Table Display */}
                        <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 overflow-x-auto">
                            {/* Render different tables based on format */}
                            {activeTab === 'market' ? (
                                <div className="p-4">
                                    <h3 className="font-bold mb-2 text-gray-900 dark:text-white">Sector Analysis</h3>
                                    {/* Market Screener Table Component would go here */}
                                    <p className="text-gray-500 italic">Market results loaded. Use 'Download CSV' to view full data or check console.</p>
                                </div>
                            ) : (
                                <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                                    <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                                        <tr>
                                            {/* Dynamic Headers */}
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