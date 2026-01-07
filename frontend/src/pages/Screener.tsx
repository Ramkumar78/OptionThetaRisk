import React, { useState } from 'react';
import { formatCurrency, getCurrencySymbol } from '../utils/formatting';

const Screener: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any[]>([]);
    const [regime, setRegime] = useState<string>('WAITING');
    const [error, setError] = useState<string | null>(null);
    const [region, setRegion] = useState('us_uk_mix');

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
        try {
            const res = await fetch(`/screen/master?region=${region}`);
            const data = await res.json();

            if (data.regime) {
                setRegime(data.regime);
            }

            if (data.results) {
                setResults(data.results);
            } else if (Array.isArray(data)) {
                setResults(data);
                if (data.length > 0 && data[0].regime) {
                     setRegime(data[0].regime);
                }
            } else {
                setResults([]);
            }
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

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
            <header className="mb-8">
                <h1 className="text-4xl font-black text-gray-900 dark:text-white tracking-tight">
                    THE COUNCIL <span className="text-primary-600">PROTOCOL</span>
                </h1>
                <p className="text-gray-500 mt-2 font-mono text-sm">
                    ISA GROWTH (£100k)  |  US OPTIONS INCOME ($9.5k)
                </p>
            </header>

            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg border border-gray-200 dark:border-gray-700 mb-8">
                <div className="flex flex-col md:flex-row gap-4 items-end">
                    <div className="flex-1">
                        <label className="block text-xs font-bold uppercase text-gray-500 mb-1">Universe</label>
                        <select
                            value={region}
                            onChange={(e) => setRegion(e.target.value)}
                            className="w-full bg-gray-100 border-none rounded-lg p-3 font-bold text-gray-900 dark:bg-gray-700 dark:text-white"
                        >
                            <option value="us_uk_mix">Global Mix (US Leaders + UK 350)</option>
                            <option value="us">United States Only</option>
                            <option value="uk">UK Only (LSE)</option>
                        </select>
                    </div>
                    <button
                        onClick={handleRunScreener}
                        disabled={loading}
                        className="px-8 py-3 bg-black dark:bg-white dark:text-black text-white font-bold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
                    >
                        {loading ? 'AUDITING MARKET...' : 'RUN PROTOCOL'}
                    </button>
                </div>

                {/* STATUS BAR */}
                <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 flex gap-6 text-xs font-mono text-gray-500">
                    <span className={regime.includes("RED") ? "text-red-500 font-bold" : ""}>
                        REGIME CHECK: {regime}
                    </span>
                    <span>ISA RISK: 1.0%</span>
                    <span>OPT RISK: 2.0%</span>
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
                                <th className="px-6 py-4">Verdict</th>
                                <th className="px-6 py-4">Action</th>
                                <th className="px-6 py-4">Stop Loss</th>
                                <th className="px-6 py-4">Breakout Date</th>
                                <th className="px-6 py-4 text-right">Quality</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
                            {results.map((r, i) => {
                                // Defensive programming to prevent crashes
                                const ticker = r?.ticker || 'UNKNOWN';
                                const company = r?.company_name || '';
                                const verdict = r?.master_verdict || '';
                                const action = r?.action || '-';
                                const stop = r?.stop_loss || '-';
                                const score = r?.quality_score || 0;
                                const breakoutDate = r?.breakout_date || '-';
                                const currency = ticker.includes && ticker.includes('.L') ? '£' : '$';

                                return (
                                    <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                                        <td className="px-6 py-4 font-bold font-mono text-gray-900 dark:text-white">
                                            {ticker}
                                            <div className="text-[10px] text-gray-400 font-normal">{company}</div>
                                        </td>
                                        <td className="px-6 py-4">{formatCurrency(r?.price, currency)}</td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded text-xs font-bold ${
                                                verdict.includes && verdict.includes('ISA') ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                                            }`}>
                                                {verdict}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 font-bold text-gray-900 dark:text-white">{action}</td>
                                        <td className="px-6 py-4 text-red-600 font-mono">{stop}</td>
                                        <td className="px-6 py-4 text-gray-500 font-mono text-xs">{breakoutDate}</td>
                                        <td className="px-6 py-4 text-right font-mono">{score}</td>
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

            {/* LEGEND / DOCS AT BOTTOM - ENHANCED FOR LAYMEN */}
            <div className="mt-12 border-t border-gray-200 dark:border-gray-700 pt-8 text-gray-500 text-sm">
                <h3 className="font-bold text-gray-900 dark:text-white mb-6 text-lg">PROTOCOL LEGEND & GLOSSARY</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {/* Strategy 1: ISA Growth */}
                    <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg">
                        <h4 className="font-bold mb-3 text-indigo-600 dark:text-indigo-400">ISA GROWTH (Long-Term Trend)</h4>
                        <p className="text-xs mb-3 text-gray-600 dark:text-gray-400">
                            Designed for long-term compounding in tax-free accounts (ISA/Roth). We only buy when the overall market is safe and the stock is establishing a new uptrend.
                        </p>
                        <ul className="list-disc pl-5 space-y-2 text-xs">
                            <li><strong>Market Regime:</strong> Is the S&P 500 rising? Are fears (VIX) low? If yes, we can buy.</li>
                            <li><strong>Trend Alignment:</strong> Price must be above both the 50-day and 200-day average prices.</li>
                            <li><strong>Trigger:</strong> We buy when price breaks above the highest point of the last 20 days (Breakout).</li>
                            <li><strong>Exit:</strong> We sell if it drops below the lowest point of the last 20 days.</li>
                        </ul>
                    </div>

                    {/* Strategy 2: Income */}
                    <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg">
                        <h4 className="font-bold mb-3 text-emerald-600 dark:text-emerald-400">US OPTIONS INCOME (Cash Flow)</h4>
                        <p className="text-xs mb-3 text-gray-600 dark:text-gray-400">
                            Designed to generate monthly income by selling "insurance" (Bull Put Spreads) on strong stocks that are temporarily pulling back.
                        </p>
                        <ul className="list-disc pl-5 space-y-2 text-xs">
                            <li><strong>Setup:</strong> Stock is in an uptrend but has dipped slightly (RSI &lt; 55).</li>
                            <li><strong>Implied Volatility (IV):</strong> Insurance premiums are expensive (good for sellers).</li>
                            <li><strong>Safety:</strong> We bet the stock won't fall below a safety floor (Support) within 45 days.</li>
                            <li><strong>Win Condition:</strong> Stock stays flat or goes up. We keep the premium.</li>
                        </ul>
                    </div>

                    {/* Glossary */}
                    <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg">
                        <h4 className="font-bold mb-3 text-gray-900 dark:text-white">Beginner's Glossary</h4>
                        <dl className="space-y-3 text-xs">
                            <div>
                                <dt className="font-bold">SMA (Simple Moving Average):</dt>
                                <dd>The average price over X days. "Price &gt; 200 SMA" means the long-term trend is UP.</dd>
                            </div>
                            <div>
                                <dt className="font-bold">RSI (Relative Strength Index):</dt>
                                <dd>Speedometer for price. Over 70 is "Speeding" (Overbought). Under 30 is "Stalled" (Oversold). We buy dips around 40-50.</dd>
                            </div>
                            <div>
                                <dt className="font-bold">ATR (Average True Range):</dt>
                                <dd>How much the stock moves on average per day. We use this to set safe Stop Losses so normal wiggles don't kick us out.</dd>
                            </div>
                            <div>
                                <dt className="font-bold">VIX (Volatility Index):</dt>
                                <dd>The "Fear Gauge". High VIX (&gt;25) means panic. We stay cash. Low VIX (&lt;20) means calm seas. We trade.</dd>
                            </div>
                        </dl>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Screener;
