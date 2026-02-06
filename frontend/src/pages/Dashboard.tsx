import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import CandlestickChart from '../components/CandlestickChart';
import RiskMapChart from '../components/RiskMapChart';
import AreaChart from '../components/AreaChart';
import DrawdownChart from '../components/DrawdownChart';
import { type CandlestickData } from 'lightweight-charts';

const ASSETS = [
  { symbol: 'SPY', name: 'S&P 500' },
  { symbol: '^FTSE', name: 'FTSE 100' },
  { symbol: '^NSEI', name: 'Nifty 50' },
  { symbol: 'XLK', name: 'Technology' },
  { symbol: 'XLF', name: 'Financials' },
  { symbol: 'XLV', name: 'Health Care' },
  { symbol: 'XLY', name: 'Discretionary' },
  { symbol: 'XLP', name: 'Staples' },
  { symbol: 'XLE', name: 'Energy' },
  { symbol: 'XLI', name: 'Industrials' },
  { symbol: 'XLB', name: 'Materials' },
  { symbol: 'XLU', name: 'Utilities' },
  { symbol: 'XLRE', name: 'Real Estate' },
  { symbol: 'XLC', name: 'Comms' },
  { symbol: 'GC=F', name: 'Gold' },
  { symbol: 'SI=F', name: 'Silver' },
  { symbol: 'TLT', name: 'Bonds (20Y)' },
  { symbol: 'GOOG', name: 'Alphabet' },
  { symbol: 'AAPL', name: 'Apple' },
  { symbol: 'BRK-B', name: 'Berkshire' },
];

const Dashboard: React.FC = () => {
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [loadingPortfolio, setLoadingPortfolio] = useState(true);
  const [showAntiTilt, setShowAntiTilt] = useState(false);
  const [revengeDetails, setRevengeDetails] = useState("");

  // Market State
  const [selectedAsset, setSelectedAsset] = useState(ASSETS[0]);
  const [marketData, setMarketData] = useState<CandlestickData[]>([]);
  const [regime, setRegime] = useState<'BULL' | 'BEAR' | 'LOADING'>('LOADING');
  const [regimeDetails, setRegimeDetails] = useState<string>('');

  useEffect(() => {
    // 1. Fetch Portfolio Data
    const fetchPortfolio = async () => {
      try {
        const response = await axios.get('/dashboard');
        if (response.data && !response.data.error) {
          setPortfolioData(response.data);

          // Anti-Tilt Check
          const strats = response.data.strategy_groups;
          if (strats && strats.length > 0) {
              const last = strats[strats.length - 1];
              if (last.is_revenge) {
                   setRevengeDetails(`Revenge Trade Detected on ${last.symbol}. You just had a loss.`);
                   setShowAntiTilt(true);
              }
          }
        }
      } catch (err) {
        // Ignore error (user might not have portfolio)
      } finally {
        setLoadingPortfolio(false);
      }
    };
    fetchPortfolio();
  }, []);

  // 2. Fetch Market Data for Regime
  useEffect(() => {
    const fetchMarket = async () => {
      setRegime('LOADING');
      setMarketData([]);
      try {
        const res = await fetch('/analyze/market-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker: selectedAsset.symbol, period: '2y' })
        });
        const data = await res.json();
        if (!data.error && Array.isArray(data) && data.length > 200) {
             setMarketData(data);

             // Calculate SMA 200
             const closes = data.map((d: any) => d.close);
             const lastClose = closes[closes.length - 1];

             // Simple SMA 200 calc
             const period = 200;
             const sum = closes.slice(-period).reduce((a: number, b: number) => a + b, 0);
             const sma200 = sum / period;

             if (lastClose > sma200) {
                 setRegime('BULL');
                 setRegimeDetails(`${selectedAsset.symbol} ($${lastClose.toFixed(2)}) > SMA200 ($${sma200.toFixed(2)})`);
             } else {
                 setRegime('BEAR');
                 setRegimeDetails(`${selectedAsset.symbol} ($${lastClose.toFixed(2)}) < SMA200 ($${sma200.toFixed(2)})`);
             }
        } else {
            setRegime('LOADING'); // Or error
        }
      } catch (e) {
          console.error("Failed to fetch market data", e);
          setRegime('LOADING');
      }
    };

    fetchMarket();
  }, [selectedAsset]);

  return (
    <div className="space-y-6 pb-10">
      <header className="flex justify-between items-end">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">Command Center</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Market Overview & Risk Management</p>
          </div>
      </header>

      {/* TOP ROW: MARKET STATUS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
               <div className="flex flex-col space-y-4 mb-4">
                   {/* Asset Selector */}
                   <div className="flex space-x-2 overflow-x-auto pb-2 scrollbar-hide">
                       {ASSETS.map((asset) => (
                           <button
                               key={asset.symbol}
                               onClick={() => setSelectedAsset(asset)}
                               className={`px-3 py-1.5 rounded text-sm font-medium whitespace-nowrap transition-colors ${
                                   selectedAsset.symbol === asset.symbol
                                   ? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
                                   : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                               }`}
                           >
                               {asset.name}
                           </button>
                       ))}
                   </div>

                   <div className="flex justify-between items-center">
                       <div>
                           <div className="flex items-center gap-2">
                               <h2 className="text-base font-bold text-gray-900 dark:text-white">{selectedAsset.symbol} Regime</h2>
                               <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                                   regime === 'BULL' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                                   regime === 'BEAR' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' : 'bg-gray-100 text-gray-600'
                               }`}>
                                   {regime}
                               </span>
                           </div>
                           <p className="text-xs text-gray-500 font-mono mt-1">{regimeDetails || 'Analyzing trend...'}</p>
                       </div>
                   </div>
               </div>

               {/* Mini Chart */}
               <div className="h-48 w-full border-t border-gray-100 dark:border-gray-700 pt-4">
                   {marketData.length > 0 ? (
                       <CandlestickChart data={marketData} height={200} />
                   ) : (
                       <div className="h-full w-full flex items-center justify-center text-gray-400 text-sm">
                           Loading Market Data...
                       </div>
                   )}
               </div>
          </div>

          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
              <div>
                  <div className="w-10 h-10 bg-primary-50 dark:bg-primary-900/20 text-primary-600 rounded flex items-center justify-center mb-4">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="22" y1="12" x2="18" y2="12"/><line x1="6" y1="12" x2="2" y2="12"/><line x1="12" y1="6" x2="12" y2="2"/><line x1="12" y1="22" x2="12" y2="18"/></svg>
                  </div>
                  <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Market Scanner</h2>
                  <p className="text-gray-500 text-sm mb-6">Run the "Grandmaster" protocol to identify high-probability setups in the current regime.</p>
              </div>
              <Link to="/screener" className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2.5 rounded text-center transition-colors text-sm">
                  Launch Screener
              </Link>
          </div>
      </div>

      {/* MIDDLE ROW: PORTFOLIO OR CTA */}
      <div>
          {portfolioData && (
               <>
               <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                   {/* Risk Map */}
                   <div className="lg:col-span-2 bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                       <div className="flex justify-between items-center mb-4">
                           <h3 className="text-base font-bold text-gray-900 dark:text-white">Visual Risk Map</h3>
                           <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">X: Expiry, Y: PnL</span>
                       </div>
                       <div className="h-64 w-full">
                           <RiskMapChart data={portfolioData.risk_map || []} />
                       </div>
                   </div>

                   {/* Discipline Score */}
                   <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 flex flex-col justify-between">
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-xs text-gray-500 font-bold uppercase tracking-wider">Discipline Score</span>
                                <span className="px-2 py-0.5 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 text-[10px] font-bold rounded uppercase">Beta</span>
                            </div>
                            <div className="flex items-end space-x-2">
                                <span className={`text-4xl font-bold ${
                                    (portfolioData.discipline_score || 100) >= 90 ? 'text-green-600' :
                                    (portfolioData.discipline_score || 100) >= 70 ? 'text-yellow-600' : 'text-red-600'
                                }`}>
                                    {portfolioData.discipline_score !== undefined ? portfolioData.discipline_score : 100}
                                </span>
                                <span className="text-gray-400 mb-1.5 text-sm">/ 100</span>
                            </div>
                            <div className="mt-4 space-y-2">
                                {portfolioData.discipline_details?.map((d: string, i: number) => (
                                    <div key={i} className="text-xs text-red-600 flex items-start">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5 mt-0.5 flex-shrink-0"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                                        {d}
                                    </div>
                                ))}
                                {(!portfolioData.discipline_details || portfolioData.discipline_details.length === 0) && (
                                    <div className="text-xs text-green-600 flex items-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5"><polyline points="20 6 9 17 4 12"/></svg>
                                        Perfect discipline.
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-700 grid grid-cols-2 gap-4">
                             <div>
                                <div className="text-xs text-gray-500 mb-1">Net Liq</div>
                                <div className="text-base font-bold font-mono">${portfolioData.net_liquidity_now?.toLocaleString()}</div>
                             </div>
                             <div>
                                <div className="text-xs text-gray-500 mb-1">YTD</div>
                                <div className={`text-base font-bold font-mono ${portfolioData.ytd_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {portfolioData.ytd_return_pct >= 0 ? '+' : ''}{portfolioData.ytd_return_pct?.toFixed(1)}%
                                </div>
                             </div>
                        </div>
                   </div>
               </div>

               {/* Performance Analysis */}
               <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 mb-8">
                    <h3 className="text-base font-bold text-gray-900 dark:text-white mb-4">Performance Analysis</h3>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <h4 className="text-xs text-gray-500 uppercase font-bold">Equity Curve</h4>
                            </div>
                            <div className="h-64">
                                 {portfolioData.portfolio_curve && (
                                     <AreaChart
                                         data={portfolioData.portfolio_curve.map((p: any) => ({
                                             time: p.x,
                                             value: (portfolioData.account_size_start || 0) + p.y
                                         }))}
                                         color="#2563eb"
                                     />
                                 )}
                            </div>
                        </div>
                        <div>
                             <div className="flex justify-between items-center mb-2">
                                <h4 className="text-xs text-gray-500 uppercase font-bold">Drawdown</h4>
                             </div>
                             <div className="h-64">
                                  <DrawdownChart
                                      data={portfolioData.portfolio_curve || []}
                                      initialCapital={portfolioData.account_size_start || 0}
                                  />
                             </div>
                        </div>
                    </div>
               </div>
               </>
          )}

          <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Portfolio Status</h3>
          {loadingPortfolio ? (
              <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse"></div>
          ) : portfolioData ? (
              <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700 grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div>
                      <div className="text-xs text-gray-500 uppercase font-bold mb-1">Beta Weighted Delta</div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white font-mono">{portfolioData.portfolio_beta_delta?.toFixed(2) || '-'}</div>
                  </div>
                  <div className="md:col-span-2 space-y-2">
                       <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide">Morning Briefing</h4>
                       {portfolioData.verdict_details ? (
                           <div className="text-sm text-red-600 font-medium bg-red-50 dark:bg-red-900/20 p-2 rounded border border-red-100 dark:border-red-900/50">
                               {portfolioData.verdict_details}
                           </div>
                       ) : (
                           <div className="text-sm text-green-600 font-medium bg-green-50 dark:bg-green-900/20 p-2 rounded border border-green-100 dark:border-green-900/50">
                               All clear. No critical risks detected.
                           </div>
                       )}
                       {regime !== 'LOADING' && (
                           <div className="text-xs text-gray-600 dark:text-gray-400">
                               Market is in <strong>{regime}</strong> regime. {regime === 'BULL' ? 'Buy dips.' : 'Sell rips.'}
                           </div>
                       )}
                  </div>
                  <div className="flex items-center justify-end">
                       <Link to="/audit" className="text-primary-600 font-medium hover:text-primary-700 text-sm">View Full Audit &rarr;</Link>
                  </div>
              </div>
          ) : (
              <div className="bg-gray-50 dark:bg-gray-800/50 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-8 text-center">
                  <div className="h-12 w-12 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-500">
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                  </div>
                  <h3 className="text-base font-bold text-gray-900 dark:text-white mb-1">No Portfolio Linked</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-sm mx-auto">
                      Upload your trade history CSV to get deep insights into your performance.
                  </p>
                  <Link to="/audit" className="px-5 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm font-medium rounded hover:opacity-90 transition-opacity">
                      Upload CSV
                  </Link>
              </div>
          )}
      </div>

      {/* BOTTOM ROW: TOOLS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link to="/monte-carlo" className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 transition-colors group">
              <div className="text-primary-600 dark:text-primary-400 mb-3 group-hover:scale-110 transition-transform origin-left">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><circle cx="15.5" cy="8.5" r="1.5"/><circle cx="8.5" cy="15.5" r="1.5"/><circle cx="15.5" cy="15.5" r="1.5"/></svg>
              </div>
              <h4 className="font-bold text-gray-900 dark:text-white text-sm">Monte Carlo</h4>
              <p className="text-xs text-gray-500 mt-1">Simulate future equity curves.</p>
          </Link>
          <Link to="/portfolio-risk" className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 transition-colors group">
              <div className="text-orange-600 dark:text-orange-400 mb-3 group-hover:scale-110 transition-transform origin-left">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              </div>
              <h4 className="font-bold text-gray-900 dark:text-white text-sm">Risk Map</h4>
              <p className="text-xs text-gray-500 mt-1">Analyze "What-If" scenarios.</p>
          </Link>
          <Link to="/journal" className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 transition-colors group">
              <div className="text-emerald-600 dark:text-emerald-400 mb-3 group-hover:scale-110 transition-transform origin-left">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
              </div>
              <h4 className="font-bold text-gray-900 dark:text-white text-sm">Journal</h4>
              <p className="text-xs text-gray-500 mt-1">Log trades & mindset.</p>
          </Link>
          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg border border-dashed border-gray-200 dark:border-gray-800 flex items-center justify-center text-center">
              <span className="text-xs font-semibold text-gray-400">More Coming Soon...</span>
          </div>
      </div>

      {showAntiTilt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl max-w-md w-full overflow-hidden border border-red-200 dark:border-red-900">
                <div className="bg-red-600 p-4 text-white flex items-center gap-3">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    <h2 className="text-lg font-bold">Tilt Risk Detected</h2>
                </div>
                <div className="p-6">
                    <p className="text-gray-700 dark:text-gray-300 mb-4 font-medium">
                        {revengeDetails}
                    </p>
                    <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded border border-red-100 dark:border-red-800 mb-6">
                         <p className="text-xs text-red-800 dark:text-red-200 leading-relaxed">
                             <strong>System Warning:</strong> Historical analysis indicates a significantly higher probability of subsequent losses when trading immediately after a drawdown of this magnitude.
                         </p>
                    </div>
                    <button
                        onClick={() => setShowAntiTilt(false)}
                        className="w-full py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-bold rounded hover:opacity-90 transition-opacity text-sm"
                    >
                        Acknowledge Risk
                    </button>
                </div>
            </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
