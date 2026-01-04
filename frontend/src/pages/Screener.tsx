import React, { useState } from 'react';
import { formatCurrency } from '../utils/formatting';

const Screener: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any[]>([]);
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
        try {
            const res = await fetch(`/screen/master?region=${region}`);
            const data = await res.json();

            if (data.results) {
                setResults(data.results);
            } else if (Array.isArray(data)) {
                setResults(data);
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
                    <span>REGIME CHECK: {results.length > 0 ? results[0].regime : 'WAITING'}</span>
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
                                <th className="px-6 py-4 text-right">Quality</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-800">
                            {results.map((r, i) => (
                                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                                    <td className="px-6 py-4 font-bold font-mono text-gray-900 dark:text-white">
                                        {r.ticker}
                                        <div className="text-[10px] text-gray-400 font-normal">{r.company_name}</div>
                                    </td>
                                    <td className="px-6 py-4">{formatCurrency(r.price, r.ticker.includes('.L') ? '£' : '$')}</td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${
                                            r.master_verdict.includes('ISA') ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                                        }`}>
                                            {r.master_verdict}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 font-bold text-gray-900 dark:text-white">{r.action}</td>
                                    <td className="px-6 py-4 text-red-600 font-mono">{r.stop_loss}</td>
                                    <td className="px-6 py-4 text-right font-mono">{r.quality_score}</td>
                                </tr>
                            ))}
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

            {/* LEGEND / DOCS AT BOTTOM */}
            <div className="mt-12 border-t border-gray-200 dark:border-gray-700 pt-8 text-gray-500 text-sm">
                <h3 className="font-bold text-gray-900 dark:text-white mb-4">PROTOCOL LEGEND</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div>
                        <h4 className="font-bold mb-2">ISA GROWTH Criteria (UK/US Stocks)</h4>
                        <ul className="list-disc pl-5 space-y-1 text-xs">
                            <li>Market Regime: SPY &gt; 200 SMA & VIX &lt; 25.</li>
                            <li>Trend: Price &gt; 50 &gt; 200 SMA.</li>
                            <li>Momentum: Within 25% of 52-week Highs.</li>
                            <li>Trigger: Volume Breakout of 20-Day High.</li>
                            <li>Risk: 1% of £100k Account.</li>
                        </ul>
                    </div>
                    <div>
                        <h4 className="font-bold mb-2">US OPTIONS INCOME Criteria</h4>
                        <ul className="list-disc pl-5 space-y-1 text-xs">
                            <li>Strategy: Bull Put Verticals.</li>
                            <li>Trend: Price &gt; 50 SMA (Bullish).</li>
                            <li>Timing: RSI &lt; 55 (Pullback).</li>
                            <li>Implied Vol: ATR &gt; 2% of Price.</li>
                            <li>Risk: 2% of $9.5k Account.</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Screener;
