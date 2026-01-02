import React, { useState } from 'react';
import { runMarketScreener, runTurtleScreener, runEmaScreener, runDarvasScreener, runMmsScreener, runBullPutScreener, runIsaTrendScreener, runFourierScreener, runHybridScreener } from '../api';


interface ScreenerProps { }

type ScreenerType = 'market' | 'turtle' | 'ema' | 'darvas' | 'mms' | 'bull_put' | 'isa' | 'fourier' | 'hybrid' | 'master' | 'fortress' | 'quantum';

const screenerInfo: Record<ScreenerType, { title: string; subtitle: string; description: string }> = {
    master: { title: "Master Protocol", subtitle: "High Probability Convergences", description: "Combines Regime Filters, Liquidity Gates, and Trend/Vol Logic." },
    fortress: { title: "Fortress Options", subtitle: "Income Generation", description: "VIX-Adjusted Bull Put Spreads on liquid US tickers." },
    quantum: { title: 'Quantum Screener', subtitle: 'Statistical Regimes', description: 'Hurst Exponent & Entropy analysis for regime detection.' },
    market: { title: 'Market Screener', subtitle: 'Volatility & RSI', description: 'Scans for IV Rank and RSI extremes.' },
    turtle: { title: 'Turtle Trading', subtitle: 'Trend Breakouts', description: '20-Day Donchian Channel Breakouts.' },
    darvas: { title: 'Darvas Box', subtitle: 'Momentum Boxes', description: 'Consolidation breakouts near 52-week highs.' },
    mms: { title: 'MMS / OTE', subtitle: 'Smart Money', description: 'Market Maker Models & Optimal Trade Entries.' },
    ema: { title: 'EMA Crossovers', subtitle: 'Trend Following', description: '5/13 & 5/21 EMA Crossovers.' },
    bull_put: { title: 'Bull Put (Classic)', subtitle: 'Credit Spreads', description: 'Standard bullish credit spreads.' },
    isa: { title: 'ISA Trend', subtitle: 'Long Term Growth', description: 'Investment grade trend following (Price > 200 SMA).' },
    fourier: { title: 'Harmonic Cycles', subtitle: 'Swing Timing', description: 'Cycle analysis to find market bottoms.' },
    hybrid: { title: 'Hybrid', subtitle: 'Trend + Cycle', description: 'Combines ISA Trend with Fourier Timing.' }
};

const Screener: React.FC<ScreenerProps> = () => {
    const [activeTab, setActiveTab] = useState<ScreenerType>('master');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [region, setRegion] = useState('us');

    // --- CSV DOWNLOAD LOGIC ---
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

    return (
        <div className="flex flex-col min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 p-4">

            {/* HEADER */}
            <div className="mb-6 bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                    <div>
                        <h1 className="text-2xl font-bold">{screenerInfo[activeTab].title}</h1>
                        <p className="text-sm text-gray-500">{screenerInfo[activeTab].description}</p>
                    </div>
                    <div className="flex gap-2">
                        <select
                            className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                            value={activeTab}
                            onChange={(e) => { setActiveTab(e.target.value as ScreenerType); setResults(null); }}
                        >
                            {Object.entries(screenerInfo).map(([key, val]) => (
                                <option key={key} value={key}>{val.title}</option>
                            ))}
                        </select>
                        <select
                            className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                            value={region}
                            onChange={(e) => setRegion(e.target.value)}
                        >
                            <option value="us">US Market</option>
                            <option value="uk">UK Market (LSE)</option>
                            <option value="india">India (NSE)</option>
                        </select>
                        <button
                            onClick={handleRunScreener}
                            disabled={loading}
                            className="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 dark:bg-blue-600 dark:hover:bg-blue-700 focus:outline-none dark:focus:ring-blue-800 disabled:opacity-50"
                        >
                            {loading ? 'Scanning...' : 'Run Scan'}
                        </button>
                    </div>
                </div>
            </div>

            {/* ERROR */}
            {error && (
                <div className="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-50 dark:bg-gray-800 dark:text-red-400 border border-red-300">
                    {error}
                </div>
            )}

            {/* RESULTS AREA */}
            {results && (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    {/* DOWNLOAD BAR */}
                    <div className="p-4 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                        <span className="font-bold text-sm">Found {Array.isArray(results) ? results.length : 'Multiple'} Results</span>
                        <button
                            onClick={downloadCSV}
                            className="text-white bg-green-600 hover:bg-green-700 focus:ring-4 focus:ring-green-300 font-medium rounded-lg text-xs px-4 py-2 dark:bg-green-600 dark:hover:bg-green-700"
                        >
                            Download CSV ⬇️
                        </button>
                    </div>

                    {/* TABLE */}
                    <div className="overflow-x-auto p-4">
                        {activeTab === 'market' ? (
                            <pre className="text-xs">{JSON.stringify(results, null, 2)}</pre>
                        ) : (
                            <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                                <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                                    <tr>
                                        {results[0] && Object.keys(results[0]).map(key => (
                                            <th key={key} className="px-4 py-3">{key}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {Array.isArray(results) && results.map((row: any, i: number) => (
                                        <tr key={i} className="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
                                            {Object.values(row).map((val: any, j) => (
                                                <td key={j} className="px-4 py-3">{val}</td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Screener;