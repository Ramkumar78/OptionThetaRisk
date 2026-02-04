import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import CandlestickChart from '../components/CandlestickChart';
import { type CandlestickData } from 'lightweight-charts';

const Dashboard: React.FC = () => {
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [loadingPortfolio, setLoadingPortfolio] = useState(true);

  // Market State
  const [spyData, setSpyData] = useState<CandlestickData[]>([]);
  const [regime, setRegime] = useState<'BULL' | 'BEAR' | 'LOADING'>('LOADING');
  const [regimeDetails, setRegimeDetails] = useState<string>('');

  useEffect(() => {
    // 1. Fetch Portfolio Data
    const fetchPortfolio = async () => {
      try {
        const response = await axios.get('/dashboard');
        if (response.data && !response.data.error) {
          setPortfolioData(response.data);
        }
      } catch (err) {
        // Ignore error (user might not have portfolio)
      } finally {
        setLoadingPortfolio(false);
      }
    };

    // 2. Fetch Market Data (SPY) for Regime
    const fetchMarket = async () => {
      try {
        const res = await fetch('/analyze/market-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker: 'SPY', period: '2y' })
        });
        const data = await res.json();
        if (!data.error && Array.isArray(data) && data.length > 200) {
             setSpyData(data);

             // Calculate SMA 200
             const closes = data.map((d: any) => d.close);
             const lastClose = closes[closes.length - 1];

             // Simple SMA 200 calc
             const period = 200;
             const sum = closes.slice(-period).reduce((a: number, b: number) => a + b, 0);
             const sma200 = sum / period;

             if (lastClose > sma200) {
                 setRegime('BULL');
                 setRegimeDetails(`SPY ($${lastClose.toFixed(2)}) > SMA200 ($${sma200.toFixed(2)})`);
             } else {
                 setRegime('BEAR');
                 setRegimeDetails(`SPY ($${lastClose.toFixed(2)}) < SMA200 ($${sma200.toFixed(2)})`);
             }
        } else {
            setRegime('LOADING'); // Or error
        }
      } catch (e) {
          console.error("Failed to fetch market data", e);
      }
    };

    fetchPortfolio();
    fetchMarket();
  }, []);

  return (
    <div className="space-y-8 animate-fade-in pb-10">
      <header>
          <h1 className="text-3xl font-black text-gray-900 dark:text-white">COMMAND <span className="text-blue-600">CENTER</span></h1>
          <p className="text-gray-500 dark:text-gray-400">Welcome back, Trader. Here is your daily briefing.</p>
      </header>

      {/* TOP ROW: MARKET STATUS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 relative overflow-hidden">
               <div className="flex justify-between items-start mb-4">
                   <div>
                       <h2 className="text-lg font-bold text-gray-900 dark:text-white">Market Regime (SPY)</h2>
                       <p className="text-sm text-gray-500">{regimeDetails || 'Analyzing trend...'}</p>
                   </div>
                   <div className={`px-4 py-1 rounded-full text-sm font-bold ${
                       regime === 'BULL' ? 'bg-green-100 text-green-800' :
                       regime === 'BEAR' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                   }`}>
                       {regime}
                   </div>
               </div>

               {/* Mini Chart */}
               <div className="h-48 w-full">
                   {spyData.length > 0 ? (
                       <CandlestickChart data={spyData} height={200} />
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
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Portfolio Status</h3>
          {loadingPortfolio ? (
              <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"></div>
          ) : portfolioData ? (
              <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div>
                      <div className="text-sm text-gray-500">Net Liquidity</div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">${portfolioData.net_liquidity_now?.toLocaleString()}</div>
                  </div>
                  <div>
                      <div className="text-sm text-gray-500">YTD Return</div>
                      <div className={`text-2xl font-bold ${portfolioData.ytd_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {portfolioData.ytd_return_pct >= 0 ? '+' : ''}{portfolioData.ytd_return_pct?.toFixed(2)}%
                      </div>
                  </div>
                  <div>
                      <div className="text-sm text-gray-500">Beta Weighted Delta</div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">{portfolioData.portfolio_beta_delta?.toFixed(2) || '-'}</div>
                  </div>
                  <div className="flex items-center">
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
    </div>
  );
};

export default Dashboard;
