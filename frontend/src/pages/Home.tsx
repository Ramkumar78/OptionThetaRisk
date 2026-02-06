import React from 'react';
import { Link } from 'react-router-dom';

const Home: React.FC = () => {
  return (
    <div className="space-y-24 pb-20">

      {/* HERO SECTION */}
      <section className="relative text-center space-y-8 pt-12 px-4">
        <div className="max-w-4xl mx-auto space-y-6">
            <h1 id="home-title" className="text-4xl md:text-6xl font-extrabold tracking-tight text-gray-900 dark:text-white">
              Institutional-Grade <br/>
              <span className="text-primary-600 dark:text-primary-500">Risk Analytics</span> <br/>
              for Retail Traders.
            </h1>
            <p id="home-subtitle" className="text-lg md:text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto leading-relaxed">
              Stop trading blind. Audit your past, screen for the future, and simulate your edge with the same tools the pros use.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-6">
              <Link
                to="/dashboard"
                className="w-full sm:w-auto px-8 py-3 text-base font-semibold text-white bg-primary-600 rounded hover:bg-primary-700 shadow-sm transition-all focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                Launch Dashboard
              </Link>
              <Link
                to="/docs"
                className="w-full sm:w-auto px-8 py-3 text-base font-semibold text-gray-700 bg-gray-100 rounded hover:bg-gray-200 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition-all focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
              >
                Read the Docs
              </Link>
            </div>
        </div>

        {/* Hero Image Placeholder */}
        <div className="relative max-w-5xl mx-auto mt-12 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-800 bg-gray-900 aspect-[16/9] flex items-center justify-center">
             <img
                src="/static/img/find_track_audit.jpg"
                alt="Platform Interface"
                className="w-full h-full object-cover opacity-90"
             />
             <div className="absolute bottom-0 left-0 right-0 p-8 z-20 text-left bg-gradient-to-t from-black/80 to-transparent">
                 <div className="inline-block px-2 py-1 bg-green-900/50 text-green-400 rounded text-xs font-bold mb-2 border border-green-700/50">
                    LIVE SYSTEM
                 </div>
                 <h3 className="text-white text-xl font-bold">Comprehensive Dashboard</h3>
                 <p className="text-gray-300 text-sm">Track Market Regime, Portfolio Greeks, and Net Liquidity in real-time.</p>
             </div>
        </div>
      </section>

      {/* TRUST / STATS STRIP */}
      <section className="border-y border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
          <div className="max-w-7xl mx-auto px-4 py-12 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              <div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">100%</div>
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Open Source</div>
              </div>
              <div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">Local</div>
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Data Processing</div>
              </div>
              <div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">Black-Scholes</div>
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Pricing Model</div>
              </div>
              <div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">Monte Carlo</div>
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Simulations</div>
              </div>
          </div>
      </section>

      {/* WORKFLOW SECTION */}
      <section className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">How It Works</h2>
              <p className="text-lg text-gray-600 dark:text-gray-400">The cycle of mastery.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
              {/* Step 1 */}
              <div className="flex flex-col items-center text-center p-6 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900">
                  <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center text-2xl mb-4 text-gray-700 dark:text-gray-300">
                      1
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Import</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                      Upload your trade history CSV from any major broker. We parse, normalize, and store it locally.
                  </p>
              </div>

              {/* Step 2 */}
              <div className="flex flex-col items-center text-center p-6 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900">
                  <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center text-2xl mb-4 text-gray-700 dark:text-gray-300">
                      2
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Analyze</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                      Our engine calculates Portfolio Greeks, PnL attribution, and Win/Loss metrics instantly.
                  </p>
              </div>

              {/* Step 3 */}
              <div className="flex flex-col items-center text-center p-6 border border-gray-200 dark:border-gray-800 rounded-lg bg-white dark:bg-gray-900">
                  <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center text-2xl mb-4 text-gray-700 dark:text-gray-300">
                      3
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Optimize</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                      Use the "What-If" Sandbox and Monte Carlo sims to refine your strategy and execute better.
                  </p>
              </div>
          </div>
      </section>

      {/* FEATURES GRID */}
      <section className="bg-gray-50 dark:bg-gray-900/30 py-20 border-y border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4">
            <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-12">
                Everything You Need to Scale
            </h2>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Feature 1 */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded border border-gray-200 dark:border-gray-700">
                    <div className="mb-4 text-primary-600 dark:text-primary-400">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Deep Audits</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Uncover hidden leaks in your trading. Track expectancy, profit factor, and max drawdown automatically.</p>
                </div>

                {/* Feature 2 */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded border border-gray-200 dark:border-gray-700">
                    <div className="mb-4 text-primary-600 dark:text-primary-400">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Portfolio Greeks</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Don't just watch price. Watch your risk. Monitor Beta-Weighted Delta, Gamma, and Theta across your entire book.</p>
                </div>

                {/* Feature 3 */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded border border-gray-200 dark:border-gray-700">
                    <div className="mb-4 text-primary-600 dark:text-primary-400">
                         <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Smart Screeners</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Algorithmic scanners for Turtle Traders, Mean Reversion, and Trend Following. Find the setup before the crowd.</p>
                </div>

                {/* Feature 4 */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded border border-gray-200 dark:border-gray-700">
                    <div className="mb-4 text-primary-600 dark:text-primary-400">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><circle cx="15.5" cy="8.5" r="1.5"/><circle cx="8.5" cy="15.5" r="1.5"/><circle cx="15.5" cy="15.5" r="1.5"/></svg>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Monte Carlo Lab</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Project your future equity curve. Stress-test your strategy against 10,000 random market scenarios.</p>
                </div>

                {/* Feature 5 */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded border border-gray-200 dark:border-gray-700">
                    <div className="mb-4 text-primary-600 dark:text-primary-400">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Trader's Journal</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Log your psychological state alongside your PnL. Identify patterns in your behavior, not just the charts.</p>
                </div>

                {/* Feature 6 */}
                <div className="bg-white dark:bg-gray-800 p-6 rounded border border-gray-200 dark:border-gray-700">
                    <div className="mb-4 text-primary-600 dark:text-primary-400">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">Scenario Analysis</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">"What if SPY drops 5%?" Visualize exactly how your PnL reacts to market shocks instantly.</p>
                </div>
            </div>
        </div>
      </section>

      {/* CTA */}
      <section className="text-center px-4">
          <div className="max-w-4xl mx-auto bg-gray-900 dark:bg-gray-800 rounded-lg p-10 text-white shadow-sm border border-gray-800">
              <h2 className="text-3xl font-bold mb-4">Ready to upgrade your trading?</h2>
              <p className="text-gray-300 text-lg mb-8 max-w-2xl mx-auto">
                  Join the traders who are moving from "guessing" to "engineering" their returns.
              </p>
              <Link
                to="/audit"
                className="inline-block px-8 py-3 text-base font-bold text-gray-900 bg-white rounded hover:bg-gray-100 transition-colors"
              >
                Start Your First Audit
              </Link>
          </div>
      </section>
    </div>
  );
};

export default Home;
