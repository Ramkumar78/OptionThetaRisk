import React, { useState, useMemo, useEffect } from 'react';
import { runMarketScreener, runTurtleScreener, runEmaScreener, runDarvasScreener, runMmsScreener, runBullPutScreener, runIsaTrendScreener, checkUnifiedStock, runFourierScreener, runHybridScreener } from '../api';
import clsx from 'clsx';
import { formatCurrency, getCurrencySymbol } from '../utils/formatting';

interface ScreenerProps { }

type ScreenerType = 'market' | 'turtle' | 'ema' | 'darvas' | 'mms' | 'bull_put' | 'isa' | 'fourier' | 'hybrid' | 'master' | 'fortress';

const screenerInfo: Record<ScreenerType, { title: string; subtitle: string; description: string }> = {
    master: {
        title: 'Master Convergence',
        subtitle: 'Multi-Strategy Collation',
        description: 'Runs ISA Trend, Fourier Cycles, and Momentum checks simultaneously. Finds the highest probability setups where multiple strategies agree (Confluence).'
    },
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
    },
    hybrid: {
        title: 'Hybrid (Trend + Cycle)',
        subtitle: 'High Probability Setup',
        description: 'Combines ISA Trend (Direction) with Fourier Cycles (Timing). Finds "Buy the Dip" setups where a strong uptrend meets a cyclical bottom. High probability, high reward.'
    },
    fortress: {
        title: "Options: Bull Put Spread - Dynamic ATR VIX Screener",
        subtitle: "VIX-Adjusted ATR Spreads",
        description: "Mathematically derived Bull Put Spreads using a dynamic safety multiplier based on the VIX. Targets liquid US options."
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
        {active && <div className="absolute right-4 top-1/2 -translate-y-1/2 w-2 h-2 bg-primary-600 rounded-full animate-pulse" />}
    </button>
);

// Summary Card Component
const StatCard = ({ title, value, color, subValue }: { title: string, value: string | number, color?: string, subValue?: string }) => (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-100 dark:border-gray-700 shadow-sm flex flex-col items-center justify-center text-center">
        <span className="text-xs text-gray-500 uppercase tracking-wide font-medium">{title}</span>
        <span className={clsx("text-2xl font-bold mt-1", color ? color : "text-gray-900 dark:text-white")}>
            {value}
        </span>
        {subValue && <span className="text-xs text-gray-400 mt-1">{subValue}</span>}
    </div>
);

// Progress Bar Component
const ProgressBar = ({ message, progress }: { message: string, progress: number }) => (
    <div className="w-full max-w-md mx-auto py-8 text-center space-y-4">
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span>Initiating</span>
            <span>Fetching</span>
            <span>Analyzing</span>
            <span>Optimizing</span>
            <span>Done</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 overflow-hidden relative">
            <div
                className="bg-primary-600 h-2.5 rounded-full transition-all duration-500 ease-out relative"
                style={{ width: `${progress}%` }}
            >
                {/* Shimmer effect */}
                <div className="absolute top-0 left-0 bottom-0 right-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer w-full h-full" style={{ backgroundSize: '200% 100%' }}></div>
            </div>
        </div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 animate-pulse">{message}</p>
    </div>
);


const Screener: React.FC<ScreenerProps> = () => {
    const [activeTab, setActiveTab] = useState<ScreenerType>('turtle');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [loadingStage, setLoadingStage] = useState(0); // 0-100
    const [loadingMessage, setLoadingMessage] = useState("");

    const [results, setResults] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [regimeSuggestion, setRegimeSuggestion] = useState<any>(null);

    // Market Screener State
    const [ivRank, setIvRank] = useState(30);
    const [rsiThreshold, setRsiThreshold] = useState(50);
    const [marketTimeFrame, setMarketTimeFrame] = useState('1d');

    // Strategy Screener State
    const [region, setRegion] = useState('us');
    const [strategyTimeFrame, setStrategyTimeFrame] = useState('1d');

    // ISA Specific State
    const [checkTicker, setCheckTicker] = useState('');
    const [checkEntryPrice, setCheckEntryPrice] = useState('');
    const [checkResult, setCheckResult] = useState<any>(null);
    const [checkLoading, setCheckLoading] = useState(false);
    const [checkEntryDate, setCheckEntryDate] = useState('');
    const [tableFilter, setTableFilter] = useState('');
    const [checkError, setCheckError] = useState<string | null>(null);

    // Fake Loading Progress Logic
    useEffect(() => {
        let interval: any;
        if (loading) {
            setLoadingStage(0);
            const stages = [
                { pct: 10, msg: "Connecting to Exchange..." },
                { pct: 30, msg: "Fetching Batch Data..." },
                { pct: 50, msg: "Processing Price Action..." },
                { pct: 70, msg: "Running Algorithms..." },
                { pct: 90, msg: "Finalizing Report..." }
            ];

            let step = 0;
            setLoadingMessage(stages[0].msg);

            interval = setInterval(() => {
                step++;
                if (step < stages.length) {
                    setLoadingStage(stages[step].pct);
                    setLoadingMessage(stages[step].msg);
                }
            }, 800); // Update every 800ms
        } else {
            setLoadingStage(100);
        }
        return () => clearInterval(interval);
    }, [loading]);

    const handleRunScreener = async () => {
        setLoading(true);
        setError(null);
        setResults(null);
        setRegimeSuggestion(null);
        setTableFilter('');
        try {
            let data;
            if (activeTab === 'market') {
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
                data = await runBullPutScreener(region);
            } else if (activeTab === 'isa') {
                const response = await runIsaTrendScreener(region);
                if (response.results) {
                    data = response.results;
                    setRegimeSuggestion(response.regime_suggestion);
                } else {
                    data = response;
                }
            } else if (activeTab === 'fourier') {
                data = await runFourierScreener(region, strategyTimeFrame);
            } else if (activeTab === 'hybrid') {
                data = await runHybridScreener(region, strategyTimeFrame);
            } else if (activeTab === 'master') {
                const res = await fetch(`/screen/master?region=${region}`);
                data = await res.json();
            } else if (activeTab === 'fortress') {
                const res = await fetch(`/screen/fortress`);
                data = await res.json();
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
            const strategy = activeTab;
            const data = await checkUnifiedStock(checkTicker, strategy, strategyTimeFrame, checkEntryPrice, checkEntryDate);
            setCheckResult(data);
        } catch (err: any) {
            setCheckError(err.message || 'Check failed');
        } finally {
            setCheckLoading(false);
        }
    };

    const stats = useMemo(() => {
        if (!results) return null;

        let items: any[] = [];
        if (activeTab === 'market' && results.results) {
            Object.values(results.results).forEach((arr: any) => items.push(...arr));
        } else if (Array.isArray(results)) {
            items = results;
        }

        if (items.length === 0) return null;

        const total = items.length;
        let bullish = 0;
        let bearish = 0;
        let neutral = 0;
        let bestPerformer = { ticker: '-', change: -999 };
        let bullishTickers: string[] = [];

        items.forEach(i => {
            const sig = (i.Signal || i.signal || "").toLowerCase();
            const change = i['1D %'] !== undefined ? i['1D %'] : (i.pct_change_1d || 0);

            const isBullish = sig.includes('buy') || sig.includes('long') || sig.includes('breakout') || sig.includes('enter') || sig.includes('green') || sig.includes('strong');

            if (isBullish) {
                bullish++;
                bullishTickers.push(i.Ticker || i.ticker || i.symbol);
            }
            else if (sig.includes('sell') || sig.includes('short') || sig.includes('dump') || sig.includes('exit') || sig.includes('red')) bearish++;
            else neutral++;

            if (change > bestPerformer.change) {
                bestPerformer = { ticker: i.Ticker || i.ticker || i.symbol, change };
            }
        });

        return {
            total,
            bullish,
            bearish,
            neutral,
            bestPerformer,
            bullishTickers
        };
    }, [results, activeTab]);

    const tabs: { id: ScreenerType; label: string; subLabel?: string }[] = [
        { id: 'fortress', label: 'Options: Bull Put', subLabel: 'Dynamic ATR VIX' },
        { id: 'master', label: '⚡ Master Convergence', subLabel: 'Best of All' },
        { id: 'hybrid', label: 'Hybrid (Trend+Cycle)', subLabel: 'High Prob' },
        { id: 'turtle', label: 'Turtle Trading' },
        { id: 'darvas', label: 'Darvas Box' },
        { id: 'fourier', label: 'Harmonic Cycles' },
        { id: 'mms', label: 'MMS / OTE', subLabel: 'SMC' },
        { id: 'ema', label: '5/13 & 5/21 EMA' },
        { id: 'isa', label: 'ISA Trend Follower', subLabel: 'Long Only' },
        { id: 'bull_put', label: 'Bull Put Spreads', subLabel: 'Yield' },
        { id: 'market', label: 'Market Screener (RSI/IV)', subLabel: 'US Options Only' },
    ];

    return (
        <div className="flex flex-col md:flex-row gap-6 min-h-[calc(100vh-80px)]">
            {/* Desktop Sidebar */}
            <aside className="hidden md:flex md:flex-col w-64 flex-shrink-0 space-y-3 sticky top-6 h-fit">
                <h2 className="text-xl font-bold mb-4 px-2 text-gray-900 dark:text-white">Strategies</h2>
                <div className="grid grid-cols-1 gap-3">
                    {tabs.map(tab => (
                        <StrategyTile
                            key={tab.id}
                            tab={tab}
                            active={activeTab === tab.id}
                            onClick={(id) => { setActiveTab(id); setResults(null); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                        />
                    ))}
                </div>
            </aside>

            {/* Mobile FAB */}
            <button
                className="md:hidden fixed bottom-24 right-6 z-40 p-4 bg-gray-800 text-white rounded-full shadow-xl hover:bg-gray-700 transition-all border border-gray-600"
                onClick={() => setIsSidebarOpen(true)}
            >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                </svg>
            </button>

            {/* Mobile Menu Overlay */}
            {isSidebarOpen && (
                <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm md:hidden" onClick={() => setIsSidebarOpen(false)}>
                    <div className="absolute bottom-0 w-full bg-gray-900 rounded-t-2xl p-6 max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-bold text-white">Select Strategy</h2>
                            <button onClick={() => setIsSidebarOpen(false)} className="text-gray-400 hover:text-white">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        <div className="grid grid-cols-1 gap-3 pb-8">
                            {tabs.map(tab => (
                                <StrategyTile
                                    key={tab.id}
                                    tab={tab}
                                    active={activeTab === tab.id}
                                    onClick={(id) => { setActiveTab(id); setResults(null); setIsSidebarOpen(false); }}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Content Area */}
            <main className="flex-1 w-full max-w-full overflow-hidden pb-20 md:pb-0">
                {/* Netflix-style Header */}
                <div className="relative p-8 rounded-2xl bg-gradient-to-br from-gray-800 to-black overflow-hidden mb-6 shadow-xl">
                    <div className="relative z-10">
                        <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">{screenerInfo[activeTab].title}</h1>
                        <p className="text-gray-300 mt-2 max-w-xl text-lg font-light leading-relaxed">{screenerInfo[activeTab].description}</p>
                    </div>
                    <div className="absolute top-0 right-0 opacity-5 text-8xl md:text-9xl font-black select-none pointer-events-none text-white truncate max-w-full -translate-y-4 translate-x-12">
                        {activeTab.toUpperCase()}
                    </div>
                </div>

                {/* Controls Area */}
                <div className="bg-white dark:bg-gray-900 rounded-xl p-6 border border-gray-200 dark:border-gray-800 shadow-sm mb-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {activeTab === 'market' && (
                            <>
                                <div>
                                    <label htmlFor="region-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Region</label>
                                    <select
                                        id="region-select"
                                        value={region}
                                        onChange={(e) => setRegion(e.target.value)}
                                        className="bg-gray-50 border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
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
                                        className="bg-gray-50 border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="rsi-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Max RSI</label>
                                    <input
                                        type="number"
                                        id="rsi-input"
                                        value={rsiThreshold}
                                        onChange={(e) => setRsiThreshold(Number(e.target.value))}
                                        className="bg-gray-50 border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="market-timeframe" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Time Frame</label>
                                    <select
                                        id="market-timeframe"
                                        value={marketTimeFrame}
                                        onChange={(e) => setMarketTimeFrame(e.target.value)}
                                        className="bg-gray-50 border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                                    >
                                        <option value="1d">Daily (1d)</option>
                                        <option value="1wk">Weekly (1wk)</option>
                                        <option value="195m">Half Day (195m)</option>
                                        <option value="49m">Swing (49m)</option>
                                    </select>
                                </div>
                            </>
                        )}

                        {(activeTab === 'turtle' || activeTab === 'ema' || activeTab === 'darvas' || activeTab === 'mms' || activeTab === 'isa' || activeTab === 'fourier' || activeTab === 'hybrid' || activeTab === 'master') && (
                            <>
                                <div>
                                    <label htmlFor="region-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Region</label>
                                    <select
                                        id="region-select"
                                        value={region}
                                        onChange={(e) => setRegion(e.target.value)}
                                        className="bg-gray-50 border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                                    >
                                        <option value="us">United States</option>
                                        <option value="uk">UK 350 (LSE)</option>
                                        <option value="uk_euro">UK / Europe (Diversified)</option>
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
                                        className="bg-gray-50 border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
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
                                        className="bg-gray-50 border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block w-full p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
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

                        {activeTab === 'fortress' && (
                            <div className="col-span-3 flex items-center justify-center p-4 bg-blue-50 dark:bg-blue-900/10 rounded-lg text-blue-800 dark:text-blue-200">
                                <p className="text-center italic">Scanning High-Liquidity US Options Universe automatically. No region selection required.</p>
                            </div>
                        )}
                    </div>

                    <div className="mt-6 flex justify-end">
                        {/* Desktop Button - Hidden on Mobile */}
                        <button
                            id="run-screener-btn-desktop"
                            onClick={handleRunScreener}
                            disabled={loading}
                            className="hidden md:block w-full md:w-auto px-8 py-3 text-white bg-primary-600 hover:bg-primary-700 focus:ring-4 focus:ring-primary-300 font-bold rounded-lg text-base shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105"
                        >
                            {loading ? 'Running...' : 'Run Screener'}
                        </button>
                    </div>
                </div>

                {/* Mobile Thumb-Zone Button */}
                <div className="fixed bottom-0 left-0 right-0 p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 md:hidden z-30 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
                    <button
                        onClick={handleRunScreener}
                        disabled={loading}
                        className="w-full py-4 text-white bg-primary-600 hover:bg-primary-700 font-bold rounded-xl text-lg shadow-lg active:scale-95 transition-all disabled:opacity-50"
                    >
                        {loading ? 'Running Analysis...' : 'Run Screener'}
                    </button>
                </div>

                {/* Loading State */}
                {loading && (
                    <div className="mb-6">
                        <ProgressBar message={loadingMessage} progress={loadingStage} />
                    </div>
                )}

                {error && (
                    <div id="screener-error" className="mb-6 p-4 text-sm text-red-800 rounded-lg bg-red-50 dark:bg-gray-800 dark:text-red-400 border border-red-200 dark:border-red-900" role="alert">
                        <span className="font-bold block mb-1">Analysis Failed</span> {error}
                    </div>
                )}

                {/* Regime Suggestion */}
                {activeTab === 'isa' && regimeSuggestion && (
                    <div className="mb-6 bg-orange-50 dark:bg-orange-900/20 border-l-4 border-orange-500 p-4 rounded-r-lg shadow-sm">
                        <div className="flex">
                            <div className="flex-shrink-0">
                                <svg className="h-5 w-5 text-orange-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <div className="ml-3">
                                <p className="text-sm text-orange-700 dark:text-orange-200">
                                    {regimeSuggestion.message}
                                    <button
                                        onClick={() => { setActiveTab('fourier'); setResults(null); setRegimeSuggestion(null); }}
                                        className="ml-2 font-bold underline hover:text-orange-800 dark:hover:text-orange-100"
                                    >
                                        Switch to Fourier
                                    </button>
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Results Container */}
                <div className="space-y-6 animate-fadeIn">
                    {/* Summary Stats */}
                    {results && stats && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <StatCard title="Total Scanned" value={stats.total} />
                            <StatCard title="Bullish Signals" value={stats.bullish} color="text-emerald-600 dark:text-emerald-400" />
                            <StatCard title="Bearish Signals" value={stats.bearish} color="text-red-600 dark:text-red-400" />
                            <StatCard title="Top Mover" value={stats.bestPerformer.change > -999 ? `${stats.bestPerformer.change > 0 ? '+' : ''}${stats.bestPerformer.change.toFixed(2)}%` : '-'} subValue={stats.bestPerformer.ticker} color={stats.bestPerformer.change >= 0 ? "text-emerald-600" : "text-red-600"} />
                        </div>
                    )}

                    {/* Bullish List */}
                    {results && stats && stats.bullishTickers.length > 0 && (
                        <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4">
                            <span className="font-bold text-emerald-800 dark:text-emerald-200 text-sm">Bullish Candidates: </span>
                            <span className="text-emerald-700 dark:text-emerald-300 text-sm break-words leading-relaxed">
                                {stats.bullishTickers.join(', ')}
                            </span>
                        </div>
                    )}

                    {/* Tables */}
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
                                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
                                        <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                                            Results
                                        </h3>
                                        <input
                                            type="text"
                                            placeholder="Filter Results..."
                                            value={tableFilter}
                                            onChange={(e) => setTableFilter(e.target.value)}
                                            className="bg-white border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-500 focus:border-primary-500 block p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white w-full sm:w-64"
                                        />
                                    </div>
                                    <ScreenerTable data={results} type={activeTab} filter={tableFilter} />
                                </div>
                            )}
                        </div>
                    )}
                </div>


                {/* Individual Stock Check - Relocated */}
                {['isa', 'turtle', 'darvas', 'ema', 'bull_put', 'hybrid', 'mms', 'fourier', 'master'].includes(activeTab) && (
                    <div className="mt-12 border-t border-gray-100 dark:border-gray-800 pt-8">
                        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Check Individual Stock</h3>
                            <form onSubmit={handleCheckStock} className="flex flex-col sm:flex-row gap-4">
                                <div className="flex-1">
                                    <label htmlFor="check-stock" className="sr-only">Ticker</label>
                                    <input
                                        type="text"
                                        id="check-stock"
                                        value={checkTicker}
                                        onChange={(e) => setCheckTicker(e.target.value)}
                                        placeholder="Ticker (e.g. AAPL)"
                                        className="w-full bg-white border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                                    />
                                </div>
                                <div className="flex-1">
                                    <label htmlFor="check-entry-price" className="sr-only">Entry Price</label>
                                    <input
                                        type="number"
                                        id="check-entry-price"
                                        step="0.01"
                                        value={checkEntryPrice}
                                        onChange={(e) => setCheckEntryPrice(e.target.value)}
                                        placeholder="Entry Price ($)"
                                        className="w-full bg-white border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                                    />
                                </div>
                                <div className="flex-1">
                                    <label htmlFor="check-entry-date" className="sr-only">Date Bought</label>
                                    <div className="relative">
                                        <input
                                            type="date"
                                            id="check-entry-date"
                                            value={checkEntryDate}
                                            onChange={(e) => setCheckEntryDate(e.target.value)}
                                            placeholder="Date Bought"
                                            className="w-full bg-white border border-gray-300 text-gray-900 text-base rounded-lg focus:ring-primary-500 focus:border-primary-500 block p-3 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
                                        />
                                    </div>
                                </div>
                                <button
                                    type="submit"
                                    disabled={checkLoading || !checkTicker.trim()}
                                    className="px-6 py-3 text-white bg-indigo-600 hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-300 font-medium rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                                >
                                    {checkLoading ? 'Checking...' : 'Check Strategy'}
                                </button>
                            </form>
                            {checkError && <div className="mt-4 p-3 bg-red-100 text-red-800 rounded-lg text-sm">{checkError}</div>}

                            {/* Result Card */}
                            {checkResult && (
                                <div className="mt-6 bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-600 shadow-lg animate-fadeIn">
                                    <h4 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex justify-between items-center border-b border-gray-100 dark:border-gray-700 pb-2">
                                        <span>{checkResult.company_name} ({checkResult.ticker})</span>
                                        <span className={clsx("text-sm px-3 py-1 rounded-full font-bold",
                                            (checkResult.signal || "").toString().toUpperCase().includes('ENTER') || (checkResult.signal || "").toString().toUpperCase().includes('BUY') ? "bg-emerald-100 text-emerald-800" :
                                                (checkResult.signal || "").toString().toUpperCase().includes('SELL') || (checkResult.signal || "").toString().toUpperCase().includes('EXIT') ? "bg-red-100 text-red-800" :
                                                    "bg-gray-200 text-gray-800")}>
                                            {checkResult.signal || "N/A"}
                                        </span>
                                    </h4>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
                                        <div>
                                            <span className="text-gray-500 dark:text-gray-400 block text-xs uppercase tracking-wider mb-1">Price</span>
                                            <span className="font-mono text-2xl text-gray-900 dark:text-white font-bold">{formatCurrency(checkResult.price || checkResult.Close, getCurrencySymbol(checkResult.ticker))}</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-500 dark:text-gray-400 block text-xs uppercase tracking-wider mb-1">Signal</span>
                                            <span className={clsx("text-lg font-bold",
                                                checkResult.signal?.includes('BUY') ? "text-emerald-600" :
                                                    checkResult.signal?.includes('SELL') ? "text-red-600" : "text-gray-900 dark:text-white"
                                            )}>
                                                {checkResult.signal || "WAIT"}
                                            </span>
                                        </div>
                                        {checkResult.pnl_value !== undefined && (
                                            <div className="col-span-2 bg-gray-50 dark:bg-gray-700/50 p-3 rounded-lg border border-gray-100 dark:border-gray-700">
                                                <span className="text-gray-500 dark:text-gray-400 block text-xs uppercase tracking-wider mb-1">Performance</span>
                                                <div className="flex items-baseline gap-2">
                                                    <span className={clsx("text-2xl font-mono font-bold", checkResult.pnl_value >= 0 ? "text-emerald-600" : "text-red-600")}>
                                                        {checkResult.pnl_value >= 0 ? "+" : ""}{parseFloat(checkResult.pnl_pct).toFixed(2)}%
                                                    </span>
                                                    <span className="text-base text-gray-600 dark:text-gray-300">
                                                        ({checkResult.pnl_value >= 0 ? "+" : ""}{formatCurrency(checkResult.pnl_value, getCurrencySymbol(checkResult.ticker))})
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                        {checkResult.pct_change_1d !== undefined && (
                                            <div>
                                                <span className="text-gray-500 dark:text-gray-400 block text-xs uppercase tracking-wider mb-1">Change (1D)</span>
                                                <span className={clsx("font-mono font-bold text-lg", checkResult.pct_change_1d >= 0 ? "text-emerald-600" : "text-red-600")}>
                                                    {checkResult.pct_change_1d >= 0 ? "+" : ""}{checkResult.pct_change_1d.toFixed(2)}%
                                                </span>
                                            </div>
                                        )}
                                        {checkResult.atr !== undefined && (
                                            <div>
                                                <span className="text-gray-500 dark:text-gray-400 block text-xs uppercase tracking-wider mb-1">ATR</span>
                                                <span className="font-mono text-gray-900 dark:text-white font-medium">{checkResult.atr}</span>
                                            </div>
                                        )}
                                        {(checkResult['52_week_high'] || checkResult['52_week_low']) && (
                                            <div>
                                                <span className="text-gray-500 dark:text-gray-400 block text-xs uppercase tracking-wider mb-1">52 Wk High/Low</span>
                                                <span className="font-mono text-gray-900 dark:text-white text-xs">
                                                    H: {checkResult['52_week_high'] || "-"}<br />
                                                    L: {checkResult['52_week_low'] || "-"}
                                                </span>
                                            </div>
                                        )}
                                        {checkResult.user_verdict && (
                                            <div className="col-span-2">
                                                <span className="text-gray-500 dark:text-gray-400 block text-xs uppercase tracking-wider mb-1">Verdict</span>
                                                <span className="font-bold text-gray-900 dark:text-white text-lg">{checkResult.user_verdict}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </main>
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
                return Object.values(item).some(val =>
                    val && typeof val === 'string' && val.toLowerCase().includes(lowerFilter) ||
                    typeof val === 'number' && val.toString().includes(lowerFilter)
                );
            });
        }
        if (sortConfig !== null) {
            sortableItems.sort((a, b) => {
                let aValue = a[sortConfig.key];
                let bValue = b[sortConfig.key];

                if (sortConfig.key === 'symbol') {
                    aValue = a.Ticker || a.ticker || a.symbol;
                    bValue = b.Ticker || b.ticker || b.symbol;
                } else if (sortConfig.key === 'hurst') {
                    aValue = a.hurst;
                    bValue = b.hurst;
                } else if (sortConfig.key === 'entropy') {
                    aValue = a.entropy;
                    bValue = b.entropy;
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
                    if (aValue === 'N/A*') aValue = -1;
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
                    aValue = a.target || a.target_price;
                    bValue = b.target || b.target_price;
                } else if (sortConfig.key === 'rr_ratio') {
                    aValue = parseFloat((a.rr_ratio || "0").split(' ')[0]);
                    bValue = parseFloat((b.rr_ratio || "0").split(' ')[0]);
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
                    aValue = parseFloat((a.max_position_size || "0").replace('%', ''));
                    bValue = parseFloat((b.max_position_size || "0").replace('%', ''));
                } else if (sortConfig.key === 'cycle_period') {
                    aValue = parseFloat((a.cycle_period || "0").split(' ')[0]);
                    bValue = parseFloat((b.cycle_period || "0").split(' ')[0]);
                } else if (sortConfig.key === 'cycle_pos') {
                    aValue = parseFloat((a.cycle_position || "0").split(' ')[0]);
                    bValue = parseFloat((b.cycle_position || "0").split(' ')[0]);
                } else if (sortConfig.key === 'score') {
                    aValue = a.score;
                    bValue = b.score;
                } else if (sortConfig.key === 'trend') {
                    aValue = a.trend;
                    bValue = b.trend;
                } else if (sortConfig.key === 'cycle') {
                    aValue = a.cycle;
                    bValue = b.cycle;
                } else if (sortConfig.key === 'atr') {
                    aValue = a.atr_value;
                    bValue = b.atr_value;
                } else if (sortConfig.key === 'breakout_date') {
                    aValue = a.breakout_date;
                    bValue = b.breakout_date;
                } else if (sortConfig.key === 'cushion') {
                    aValue = parseFloat((a.cushion || "0").replace('%', ''));
                    bValue = parseFloat((b.cushion || "0").replace('%', ''));
                }

                const isInvalid = (v: any) => v === undefined || v === null || v === 'N/A' || v === 'N/A*' || v === '';
                if (isInvalid(aValue) && isInvalid(bValue)) return 0;
                if (isInvalid(aValue)) return 1;
                if (isInvalid(bValue)) return -1;

                if (typeof aValue === 'string') {
                    aValue = aValue.toLowerCase();
                    bValue = bValue.toLowerCase();
                }

                if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
                if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
                return 0;
            });
        }
        return sortableItems;
    }, [data, filter, sortConfig]);

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
            className={clsx(
                "px-4 py-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 select-none whitespace-nowrap",
                align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left',
                sortKey === 'symbol' ? "sticky left-0 z-20 bg-gray-50 dark:bg-gray-700 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]" : ""
            )}
            onClick={() => requestSort(sortKey)}
        >
            <div className={clsx("flex items-center", align === 'right' ? 'justify-end' : align === 'center' ? 'justify-center' : 'justify-start')}>
                {label} {getSortIndicator(sortKey)}
            </div>
        </th>
    );

    return (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
            <table className="w-full text-sm text-left text-gray-500 dark:text-gray-400">
                <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400">
                    <tr>
                        <HeaderCell label="Symbol" sortKey="symbol" />
                        {type === 'market' && <HeaderCell label="Company" sortKey="company" />}
                        <HeaderCell label="Price" sortKey="price" align="right" />
                        {type !== 'bull_put' && type !== 'hybrid' && type !== 'fortress' && <HeaderCell label="Change" sortKey="change" align="right" />}

                        {type === 'fortress' && (
                            <>
                                <HeaderCell label="Safety K" sortKey="k_factor" align="center" />
                                <HeaderCell label="Sell Put" sortKey="sell_strike" align="right" />
                                <HeaderCell label="Buy Put" sortKey="buy_strike" align="right" />
                                <HeaderCell label="Safety %" sortKey="cushion" align="right" />
                                <HeaderCell label="Close Date" sortKey="manage_by" align="right" />
                            </>
                        )}

                        {type !== 'fortress' && <HeaderCell label="ATR" sortKey="atr" align="right" />}
                        {type !== 'fortress' && <HeaderCell label="Breakout Date" sortKey="breakout_date" align="right" />}

                        {type === 'market' && (
                            <>
                                <HeaderCell label="RSI" sortKey="rsi" align="right" />
                                <HeaderCell label="IV Rank" sortKey="iv_rank" align="right" />
                                <HeaderCell label="Signal" sortKey="signal" align="center" />
                            </>
                        )}
                        {type === 'master' && (
                            <>
                                <HeaderCell label="Verdict" sortKey="verdict" align="center" />
                                <HeaderCell label="Score" sortKey="confluence_score" align="center" />
                                <HeaderCell label="ISA Trend" sortKey="isa_trend" align="center" />
                                <HeaderCell label="Fourier" sortKey="fourier" align="right" />
                                <HeaderCell label="Momentum" sortKey="momentum" align="right" />
                                <HeaderCell label="Hurst (H)" sortKey="hurst" align="right" />
                                <HeaderCell label="Entropy (S)" sortKey="entropy" align="right" />
                            </>
                        )}
                        {type !== 'market' && type !== 'bull_put' && type !== 'master' && type !== 'fortress' && (
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
                                {type === 'hybrid' && (
                                    <>
                                        <HeaderCell label="Trend" sortKey="trend" align="center" />
                                        <HeaderCell label="Cycle" sortKey="cycle" align="center" />
                                        <HeaderCell label="Period" sortKey="cycle_period" align="right" />
                                        <HeaderCell label="Score" sortKey="score" align="right" />
                                        <HeaderCell label="Stop" sortKey="stop_loss" align="right" />
                                        <HeaderCell label="Target" sortKey="target" align="right" />
                                        <HeaderCell label="R/R" sortKey="rr_ratio" align="right" />
                                    </>
                                )}
                                {type !== 'isa' && type !== 'fourier' && type !== 'hybrid' && <HeaderCell label="Stop Loss" sortKey="stop_loss" align="right" />}
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
                        const change = row['1D %'] !== undefined ? row['1D %'] : (row.pct_change_1d !== undefined ? row.pct_change_1d : row.pct_change);
                        const symbol = row.Ticker || row.ticker || row.symbol;
                        const company = row.Company || row.company_name;
                        const rsi = row.RSI || row.rsi;
                        const ivRank = row['IV Rank'] || row.iv_rank;
                        const signal = row.Signal || row.signal;

                        return (
                            <tr key={idx} className="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                <td className="px-4 py-3 font-bold text-gray-900 dark:text-white sticky left-0 z-10 bg-white dark:bg-gray-800 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                                    {symbol}
                                    {company && type !== 'market' && <div className="text-[10px] text-gray-400 font-normal truncate max-w-[100px]">{company}</div>}
                                </td>
                                {type === 'market' && <td className="px-4 py-3 text-xs">{company || '-'}</td>}

                                <td className="px-4 py-3 text-right font-mono whitespace-nowrap">
                                    {formatCurrency(price, currency)}
                                </td>

                                {type !== 'bull_put' && type !== 'hybrid' && type !== 'fortress' && (
                                    <td className={clsx("px-4 py-3 text-right font-bold whitespace-nowrap", (change || 0) >= 0 ? "text-emerald-500" : "text-red-500")}>
                                        {change !== undefined && change !== null ? `${change > 0 ? '+' : ''}${typeof change === 'number' ? change.toFixed(2) : change}%` : '-'}
                                    </td>
                                )}

                                {type === 'fortress' ? (
                                    <>
                                        <td className="px-4 py-3 text-center whitespace-nowrap">
                                            <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded dark:bg-blue-900 dark:text-blue-200">
                                                {row.k_factor}x ATR
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400 whitespace-nowrap">${row.sell_strike}</td>
                                        <td className="px-4 py-3 text-right font-mono text-gray-500 whitespace-nowrap">${row.buy_strike}</td>
                                        <td className="px-4 py-3 text-right font-bold text-gray-900 dark:text-gray-300 whitespace-nowrap">{row.cushion}</td>
                                        <td className="px-4 py-3 text-right text-xs text-gray-500 whitespace-nowrap">{row.manage_by}</td>
                                    </>
                                ) : (
                                    <>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 whitespace-nowrap">
                                            {row.atr_value ? formatCurrency(row.atr_value, currency) : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 whitespace-nowrap">
                                            {row.breakout_date || '-'}
                                        </td>
                                    </>
                                )}

                                {type === 'market' && (
                                    <>
                                        <td className={clsx("px-4 py-3 text-right whitespace-nowrap", (rsi || 0) < 30 ? "text-blue-500 font-bold" : (rsi || 0) > 70 ? "text-red-500 font-bold" : "")}>
                                            {rsi !== undefined && rsi !== null ? (typeof rsi === 'number' ? rsi.toFixed(1) : rsi) : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-right whitespace-nowrap">
                                            {ivRank !== undefined && ivRank !== null ? (typeof ivRank === 'number' ? ivRank.toFixed(1) : ivRank) : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-center whitespace-nowrap">
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

                                {type !== 'market' && type !== 'bull_put' && type !== 'fortress' && (
                                    <>
                                        {type === 'master' ? (
                                            <>
                                                <td className="px-4 py-3 text-center font-bold whitespace-nowrap">
                                                    <span className={clsx("px-2 py-1 rounded text-xs",
                                                        (row.verdict || "").includes('STRONG') ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" :
                                                            (row.verdict || "").includes('SELL') ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300")}>
                                                        {row.verdict}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-center font-mono font-bold text-indigo-600 dark:text-indigo-400 whitespace-nowrap">
                                                    {row.confluence_score}/3
                                                </td>
                                                <td className="px-4 py-3 text-center text-xs text-gray-900 dark:text-gray-300 whitespace-nowrap">
                                                    {row.isa_trend === 'BULLISH' ? '🟢 UP' : '🔴 DOWN'}
                                                </td>
                                                <td className="px-4 py-3 text-right text-xs text-gray-500 whitespace-nowrap">
                                                    {row.fourier}
                                                </td>
                                                <td className="px-4 py-3 text-right text-xs text-gray-500 whitespace-nowrap">
                                                    {row.momentum}
                                                </td>
                                                <td className="px-4 py-3 text-right text-xs text-gray-500 whitespace-nowrap font-mono">
                                                    {row.hurst ? row.hurst.toFixed(2) : '-'}
                                                </td>
                                                <td className="px-4 py-3 text-right text-xs text-gray-500 whitespace-nowrap font-mono">
                                                    {row.entropy ? row.entropy.toFixed(2) : '-'}
                                                </td>
                                            </>
                                        ) : (
                                            <td className="px-4 py-3 text-center whitespace-nowrap">
                                                <span className={clsx("px-2 py-1 rounded text-xs font-bold",
                                                    signal && (signal.includes('Long') || signal.includes('Buy') || signal.includes('BUY') || signal.includes('BREAKOUT') || signal.includes('PERFECT BUY')) ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200" :
                                                        signal && (signal.includes('Short') || signal.includes('SHORT') || signal.includes('Sell') || signal.includes('DUMP')) ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" :
                                                            signal && (signal.includes('WAIT')) ? "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300" :
                                                                "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                                                )}>
                                                    {signal}
                                                </span>
                                            </td>
                                        )}
                                        {type === 'darvas' && (
                                            <>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300 whitespace-nowrap">
                                                    {formatCurrency(row.breakout_level, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400 font-bold whitespace-nowrap">
                                                    {formatCurrency(row.target_price, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 whitespace-nowrap">
                                                    {formatCurrency(row.high_52w, currency)}
                                                </td>
                                            </>
                                        )}
                                        {type === 'mms' && (
                                            <>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-indigo-600 dark:text-indigo-400 whitespace-nowrap">
                                                    {row.ote_zone}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400 font-bold whitespace-nowrap">
                                                    {formatCurrency(row.target, currency)}
                                                </td>
                                            </>
                                        )}
                                        {type === 'isa' && (
                                            <>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300 whitespace-nowrap">
                                                    {formatCurrency(row.breakout_level, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-red-600 dark:text-red-400 font-bold whitespace-nowrap">
                                                    {formatCurrency(row.stop_loss_3atr, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-orange-600 dark:text-orange-400 whitespace-nowrap">
                                                    {formatCurrency(row.trailing_exit_20d, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 whitespace-nowrap">
                                                    {row.volatility_pct}%
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 whitespace-nowrap">
                                                    {formatCurrency(row.risk_per_share, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300 whitespace-nowrap">
                                                    {row.tharp_verdict}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400 font-bold whitespace-nowrap">
                                                    {row.max_position_size}
                                                </td>
                                            </>
                                        )}
                                        {type === 'fourier' && (
                                            <>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300 whitespace-nowrap">
                                                    {row.cycle_period}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-indigo-600 dark:text-indigo-400 font-bold whitespace-nowrap">
                                                    {row.cycle_position}
                                                </td>
                                            </>
                                        )}
                                        {type === 'hybrid' && (
                                            <>
                                                <td className="px-4 py-3 text-center whitespace-nowrap">
                                                    <span className={clsx("font-bold text-xs", row.trend === 'BULLISH' ? "text-emerald-600 dark:text-emerald-400" : row.trend === 'BEARISH' ? "text-red-600 dark:text-red-400" : "text-gray-500")}>
                                                        {row.trend}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-center font-mono text-xs text-gray-900 dark:text-gray-300 whitespace-nowrap">
                                                    {row.cycle}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 whitespace-nowrap">
                                                    {row.period_days}d
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400 whitespace-nowrap">
                                                    {row.score}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-red-600 dark:text-red-400 font-bold whitespace-nowrap">
                                                    {formatCurrency(row.stop_loss, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400 font-bold whitespace-nowrap">
                                                    {formatCurrency(row.target, currency)}
                                                </td>
                                                <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300 whitespace-nowrap">
                                                    {row.rr_ratio}
                                                </td>
                                            </>
                                        )}
                                        {type !== 'isa' && type !== 'fourier' && type !== 'hybrid' && (
                                            <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 whitespace-nowrap">
                                                {formatCurrency(row.stop_loss, currency)}
                                            </td>
                                        )}
                                    </>
                                )}

                                {type === 'bull_put' && (
                                    <>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400 font-bold whitespace-nowrap">
                                            ${row.credit.toFixed(2)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 whitespace-nowrap">
                                            ${row.max_risk.toFixed(2)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-indigo-600 dark:text-indigo-400 font-bold whitespace-nowrap">
                                            {row.roi_pct}%
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-900 dark:text-gray-300 whitespace-nowrap">
                                            {row.short_strike}/{row.long_strike} <span className="text-gray-400 text-[10px]">({row.short_delta})</span>
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-xs text-gray-500 whitespace-nowrap">
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
