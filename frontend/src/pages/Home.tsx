import React from 'react';
import { Link } from 'react-router-dom';

const Home: React.FC = () => {
  return (
    <div className="space-y-20 pb-20">

      {/* HERO SECTION */}
      <section className="relative text-center space-y-8 pt-10 px-4">
        <div className="max-w-4xl mx-auto space-y-6">
            <h1 id="home-title" className="text-5xl md:text-7xl font-black tracking-tighter text-gray-900 dark:text-white leading-[1.1]">
              Institutional-Grade <br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-500">Risk Analytics</span> <br/>
              for Retail Traders.
            </h1>
            <p id="home-subtitle" className="text-xl md:text-2xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto leading-relaxed">
              Stop trading blind. Audit your past, screen for the future, and simulate your edge with the same tools the pros use.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-6">
              <Link
                to="/dashboard"
                className="w-full sm:w-auto px-8 py-4 text-lg font-bold text-white bg-blue-600 rounded-xl hover:bg-blue-700 shadow-xl shadow-blue-500/20 transition-all hover:-translate-y-1 focus:ring-4 focus:ring-blue-300 dark:focus:ring-blue-900"
              >
                Launch Dashboard
              </Link>
              <Link
                to="/docs"
                className="w-full sm:w-auto px-8 py-4 text-lg font-bold text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition-all focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700"
              >
                Read the Docs
              </Link>
            </div>
        </div>

        {/* Hero Image / Graphic Placeholder */}
        <div className="relative max-w-5xl mx-auto mt-12 rounded-2xl overflow-hidden shadow-2xl border border-gray-200 dark:border-gray-800 bg-gray-900 aspect-[16/9] flex items-center justify-center group">
             {/* We can use the existing image, or a placeholder for a 'Dashboard Screenshot' */}
             <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent opacity-60 z-10"></div>
             <img
                src="/static/img/find_track_audit.jpg"
                alt="Platform Interface"
                className="w-full h-full object-cover opacity-80 group-hover:scale-105 transition-transform duration-700"
             />
             <div className="absolute bottom-0 left-0 right-0 p-8 z-20 text-left">
                 <div className="inline-block px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-bold mb-2 border border-green-500/30">
                    LIVE SYSTEM
                 </div>
                 <h3 className="text-white text-2xl font-bold">Comprehensive Dashboard</h3>
                 <p className="text-gray-300">Track Market Regime, Portfolio Greeks, and Net Liquidity in real-time.</p>
             </div>
        </div>
      </section>

      {/* TRUST / STATS STRIP */}
      <section className="border-y border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
          <div className="max-w-7xl mx-auto px-4 py-12 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              <div>
                  <div className="text-3xl font-black text-gray-900 dark:text-white mb-1">100%</div>
                  <div className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Open Source</div>
              </div>
              <div>
                  <div className="text-3xl font-black text-gray-900 dark:text-white mb-1">Local</div>
                  <div className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Data Processing</div>
              </div>
              <div>
                  <div className="text-3xl font-black text-gray-900 dark:text-white mb-1">Black-Scholes</div>
                  <div className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Pricing Model</div>
              </div>
              <div>
                  <div className="text-3xl font-black text-gray-900 dark:text-white mb-1">Monte Carlo</div>
                  <div className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Simulations</div>
              </div>
          </div>
      </section>

      {/* WORKFLOW SECTION */}
      <section className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">How It Works</h2>
              <p className="text-xl text-gray-600 dark:text-gray-400">The "Cycle of Mastery" simplified.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-12 relative">
              {/* Connector Line (Desktop) */}
              <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-1 bg-gradient-to-r from-blue-200 via-indigo-200 to-purple-200 dark:from-blue-900 dark:to-purple-900 -z-10 rounded-full"></div>

              {/* Step 1 */}
              <div className="relative flex flex-col items-center text-center space-y-4">
                  <div className="w-24 h-24 bg-white dark:bg-gray-800 rounded-full border-4 border-blue-100 dark:border-blue-900/50 flex items-center justify-center text-4xl shadow-lg">
                      📥
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 dark:text-white">1. Import</h3>
                  <p className="text-gray-600 dark:text-gray-400">
                      Upload your trade history CSV from any major broker. We parse, normalize, and store it locally.
                  </p>
              </div>

              {/* Step 2 */}
              <div className="relative flex flex-col items-center text-center space-y-4">
                  <div className="w-24 h-24 bg-white dark:bg-gray-800 rounded-full border-4 border-indigo-100 dark:border-indigo-900/50 flex items-center justify-center text-4xl shadow-lg">
                      ⚙️
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 dark:text-white">2. Analyze</h3>
                  <p className="text-gray-600 dark:text-gray-400">
                      Our engine calculates Portfolio Greeks, PnL attribution, and Win/Loss metrics instantly.
                  </p>
              </div>

              {/* Step 3 */}
              <div className="relative flex flex-col items-center text-center space-y-4">
                  <div className="w-24 h-24 bg-white dark:bg-gray-800 rounded-full border-4 border-purple-100 dark:border-purple-900/50 flex items-center justify-center text-4xl shadow-lg">
                      📈
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 dark:text-white">3. Optimize</h3>
                  <p className="text-gray-600 dark:text-gray-400">
                      Use the "What-If" Sandbox and Monte Carlo sims to refine your strategy and execute better.
                  </p>
              </div>
          </div>
      </section>

      {/* FEATURES GRID */}
      <section className="bg-gray-50 dark:bg-gray-900/30 py-20 rounded-3xl mx-4">
        <div className="max-w-7xl mx-auto px-4">
            <h2 className="text-3xl md:text-4xl font-bold text-center text-gray-900 dark:text-white mb-16">
                Everything You Need to <span className="text-blue-600">Scale</span>
            </h2>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                {/* Feature 1 */}
                <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:-translate-y-1 transition-transform">
                    <div className="w-14 h-14 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center text-2xl mb-6">🔍</div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">Deep Audits</h3>
                    <p className="text-gray-600 dark:text-gray-400">Uncover hidden leaks in your trading. Track expectancy, profit factor, and max drawdown automatically.</p>
                </div>

                {/* Feature 2 */}
                <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:-translate-y-1 transition-transform">
                    <div className="w-14 h-14 bg-purple-100 text-purple-600 rounded-xl flex items-center justify-center text-2xl mb-6">📊</div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">Portfolio Greeks</h3>
                    <p className="text-gray-600 dark:text-gray-400">Don't just watch price. Watch your risk. Monitor Beta-Weighted Delta, Gamma, and Theta across your entire book.</p>
                </div>

                {/* Feature 3 */}
                <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:-translate-y-1 transition-transform">
                    <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center text-2xl mb-6">🚀</div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">Smart Screeners</h3>
                    <p className="text-gray-600 dark:text-gray-400">Algorithmic scanners for Turtle Traders, Mean Reversion, and Trend Following. Find the setup before the crowd.</p>
                </div>

                {/* Feature 4 */}
                <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:-translate-y-1 transition-transform">
                    <div className="w-14 h-14 bg-orange-100 text-orange-600 rounded-xl flex items-center justify-center text-2xl mb-6">🎲</div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">Monte Carlo Lab</h3>
                    <p className="text-gray-600 dark:text-gray-400">Project your future equity curve. Stress-test your strategy against 10,000 random market scenarios.</p>
                </div>

                {/* Feature 5 */}
                <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:-translate-y-1 transition-transform">
                    <div className="w-14 h-14 bg-pink-100 text-pink-600 rounded-xl flex items-center justify-center text-2xl mb-6">📓</div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">Trader's Journal</h3>
                    <p className="text-gray-600 dark:text-gray-400">Log your psychological state alongside your PnL. Identify patterns in your behavior, not just the charts.</p>
                </div>

                {/* Feature 6 */}
                <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 hover:-translate-y-1 transition-transform">
                    <div className="w-14 h-14 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center text-2xl mb-6">⚠️</div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">Scenario Analysis</h3>
                    <p className="text-gray-600 dark:text-gray-400">"What if SPY drops 5%?" Visualize exactly how your PnL reacts to market shocks instantly.</p>
                </div>
            </div>
        </div>
      </section>

      {/* CTA */}
      <section className="text-center px-4">
          <div className="max-w-4xl mx-auto bg-gradient-to-br from-gray-900 to-gray-800 rounded-3xl p-12 text-white shadow-2xl">
              <h2 className="text-3xl md:text-4xl font-bold mb-6">Ready to upgrade your trading?</h2>
              <p className="text-gray-300 text-lg mb-8 max-w-2xl mx-auto">
                  Join the traders who are moving from "guessing" to "engineering" their returns.
              </p>
              <Link
                to="/audit"
                className="inline-block px-10 py-4 text-lg font-bold text-blue-900 bg-white rounded-xl hover:bg-gray-100 transition-colors"
              >
                Start Your First Audit
              </Link>
          </div>
      </section>
    </div>
  );
};

export default Home;
