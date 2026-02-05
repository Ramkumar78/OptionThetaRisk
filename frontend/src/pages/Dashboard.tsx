import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import CandlestickChart from '../components/CandlestickChart';
import RiskMapChart from '../components/RiskMapChart';
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
    <div className="space-y-8 animate-fade-in pb-10">
      <header>
          <h1 className="text-3xl font-black text-gray-900 dark:text-white">TRADE<span className="text-blue-600">GUARDIAN</span></h1>
          <p className="text-gray-500 dark:text-gray-400">The AI Risk Manager that stops you from blowing up your account.</p>
      </header>

      {/* TOP ROW: MARKET STATUS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 relative overflow-hidden">
               <div className="flex flex-col space-y-4 mb-4">
                   {/* Asset Selector */}
                   <div className="flex space-x-2 overflow-x-auto pb-2 scrollbar-hide">
                       {ASSETS.map((asset) => (
                           <button
                               key={asset.symbol}
                               onClick={() => setSelectedAsset(asset)}
                               className={`px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                                   selectedAsset.symbol === asset.symbol
                                   ? 'bg-blue-600 text-white shadow-md'
                                   : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                               }`}
                           >
                               {asset.name}
                           </button>
                       ))}
                   </div>

                   <div className="flex justify-between items-start">
                       <div>
                           <h2 className="text-lg font-bold text-gray-900 dark:text-white">Market Regime ({selectedAsset.symbol})</h2>
                           <p className="text-sm text-gray-500">{regimeDetails || 'Analyzing trend...'}</p>
                       </div>
                       <div className={`px-4 py-1 rounded-full text-sm font-bold ${
                           regime === 'BULL' ? 'bg-green-100 text-green-800' :
                           regime === 'BEAR' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                       }`}>
                           {regime}
                       </div>
                   </div>
               </div>

               {/* Mini Chart */}
               <div className="h-48 w-full">
                   {marketData.length > 0 ? (
                       <CandlestickChart data={marketData} height={200} />
                   ) : (
                       <div className="h-full w-full flex items-center justify-center text-gray-400">
                           Loading Market Data...
                       </div>
                   )}
               </div>
          </div>

          <div className="bg-gradient-to-br from-blue-600 to-blue-800 text-white p-6 rounded-xl shadow-lg flex flex-col justify-between">
              <div>
                  <h2 className="text-xl font-bold mb-2">Quick Scan</h2>
                  <p className="text-blue-100 text-sm mb-4">Run the "Grandmaster" protocol to find high-probability setups right now.</p>
              </div>
              <Link to="/screener" className="w-full bg-white text-blue-700 font-bold py-3 rounded-lg text-center shadow-md hover:bg-blue-50 transition-colors">
                  Launch Screener <i className="bi bi-arrow-right ml-1"></i>
              </Link>
          </div>
      </div>

      {/* MIDDLE ROW: PORTFOLIO OR CTA */}
      <div>
          {portfolioData && (
               <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                   {/* Risk Map */}
                   <div className="lg:col-span-2 bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                       <div className="flex justify-between items-center mb-4">
                           <h3 className="text-lg font-bold text-gray-900 dark:text-white">Visual Risk Map</h3>
                           <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">X: Expiry, Y: PnL</span>
                       </div>
                       <div className="h-64 w-full">
                           <RiskMapChart data={portfolioData.risk_map || []} />
                       </div>
                   </div>

                   {/* Discipline Score */}
                   <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col justify-between">
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm text-gray-500 font-bold uppercase tracking-wider">Discipline Score</span>
                                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">BETA</span>
                            </div>
                            <div className="flex items-end space-x-2">
                                <span className={`text-5xl font-black ${
                                    (portfolioData.discipline_score || 100) >= 90 ? 'text-green-500' :
                                    (portfolioData.discipline_score || 100) >= 70 ? 'text-yellow-500' : 'text-red-500'
                                }`}>
                                    {portfolioData.discipline_score !== undefined ? portfolioData.discipline_score : 100}
                                </span>
                                <span className="text-gray-400 mb-2">/ 100</span>
                            </div>
                            <div className="mt-4 space-y-2">
                                {portfolioData.discipline_details?.map((d: string, i: number) => (
                                    <div key={i} className="text-xs text-red-500 flex items-center">
                                        <span className="mr-1">⚠️</span> {d}
                                    </div>
                                ))}
                                {(!portfolioData.discipline_details || portfolioData.discipline_details.length === 0) && (
                                    <div className="text-xs text-green-500 flex items-center">
                                        <span className="mr-1">✅</span> Perfect discipline.
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-700 grid grid-cols-2 gap-4">
                             <div>
                                <div className="text-xs text-gray-500">Net Liq</div>
                                <div className="text-lg font-bold">${portfolioData.net_liquidity_now?.toLocaleString()}</div>
                             </div>
                             <div>
                                <div className="text-xs text-gray-500">YTD</div>
                                <div className={`text-lg font-bold ${portfolioData.ytd_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {portfolioData.ytd_return_pct >= 0 ? '+' : ''}{portfolioData.ytd_return_pct?.toFixed(1)}%
                                </div>
                             </div>
                        </div>
                   </div>
               </div>
          )}

          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Portfolio Status</h3>
          {loadingPortfolio ? (
              <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"></div>
          ) : portfolioData ? (
              <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div>
                      <div className="text-sm text-gray-500">Beta Weighted Delta</div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">{portfolioData.portfolio_beta_delta?.toFixed(2) || '-'}</div>
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
                       <Link to="/audit" className="text-blue-600 font-semibold hover:underline">View Full Audit &rarr;</Link>
                  </div>
              </div>
          ) : (
              <div className="bg-gray-50 dark:bg-gray-800/50 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl p-8 text-center">
                  <div className="h-16 w-16 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">📁</div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">No Portfolio Linked</h3>
                  <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
                      Upload your trade history CSV to get deep insights into your performance, win-rate, and hidden risks.
                  </p>
                  <Link to="/audit" className="px-6 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-semibold rounded-lg hover:opacity-90 transition-opacity">
                      Upload CSV
                  </Link>
              </div>
          )}
      </div>

      {/* BOTTOM ROW: TOOLS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link to="/monte-carlo" className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow group">
              <div className="h-10 w-10 bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">🎲</div>
              <h4 className="font-bold text-gray-900 dark:text-white">Monte Carlo</h4>
              <p className="text-xs text-gray-500 mt-1">Simulate future equity curves.</p>
          </Link>
          <Link to="/portfolio-risk" className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow group">
              <div className="h-10 w-10 bg-orange-100 text-orange-600 rounded-lg flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">⚠️</div>
              <h4 className="font-bold text-gray-900 dark:text-white">Risk Map</h4>
              <p className="text-xs text-gray-500 mt-1">Analyze "What-If" scenarios.</p>
          </Link>
          <Link to="/journal" className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow group">
              <div className="h-10 w-10 bg-emerald-100 text-emerald-600 rounded-lg flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">📓</div>
              <h4 className="font-bold text-gray-900 dark:text-white">Journal</h4>
              <p className="text-xs text-gray-500 mt-1">Log trades & mindset.</p>
          </Link>
          <div className="bg-gray-100 dark:bg-gray-900 p-4 rounded-xl border border-transparent flex items-center justify-center text-center opacity-60">
              <span className="text-xs font-semibold text-gray-500">More Coming Soon...</span>
          </div>
      </div>

      {showAntiTilt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden border border-red-200 dark:border-red-900 animate-bounce-in">
                <div className="bg-red-600 p-6 text-white text-center">
                    <div className="text-5xl mb-2">⚠️</div>
                    <h2 className="text-2xl font-black uppercase">Tilt Detected</h2>
                </div>
                <div className="p-6">
                    <p className="text-gray-700 dark:text-gray-300 text-lg mb-4 text-center font-medium">
                        {revengeDetails}
                    </p>
                    <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg border border-red-100 dark:border-red-800 mb-6">
                         <p className="text-sm text-red-800 dark:text-red-200">
                             <strong>Rational AI says:</strong> "The algorithms suggest an 85% chance this next trade fails due to emotional bias."
                         </p>
                    </div>
                    <button
                        onClick={() => setShowAntiTilt(false)}
                        className="w-full py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 font-bold rounded-xl hover:opacity-90 transition-opacity"
                    >
                        I promise to take a 15 min walk
                    </button>
                </div>
            </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
