import React from 'react';
import { Link } from 'react-router-dom';

const Docs: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto space-y-12 pb-12">
      <header className="space-y-4 text-center py-10">
        <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 dark:text-white">
          Documentation & <span className="text-primary-600">Guides</span>
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-300">
          Master the platform. Master the markets.
        </p>
      </header>

      <div className="space-y-12">
        {/* Getting Started */}
        <section id="getting-started" className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 flex items-center">
            <span className="bg-blue-100 text-blue-600 p-2 rounded-lg mr-3 text-xl">🚀</span>
            Getting Started
          </h2>
          <div className="space-y-4 text-gray-600 dark:text-gray-300">
            <p>
              Trade Auditor is designed to ingest your trading history and provide institutional-grade analytics.
              Here is how to begin:
            </p>
            <ol className="list-decimal list-inside space-y-2 ml-2">
              <li><strong>Export your Data:</strong> Download your trade history as a CSV file from your broker (e.g., ThinkOrSwim, Interactive Brokers).</li>
              <li><strong>Upload to Audit:</strong> Navigate to the <Link to="/audit" className="text-blue-600 hover:underline">Audit page</Link> and upload your CSV.</li>
              <li><strong>Verify:</strong> The system will parse your trades. Check the "Dashboard" for your updated portfolio summary.</li>
            </ol>
          </div>
        </section>

        {/* Understanding Greeks */}
        <section id="greeks" className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 flex items-center">
            <span className="bg-purple-100 text-purple-600 p-2 rounded-lg mr-3 text-xl">📊</span>
            Understanding Portfolio Greeks
          </h2>
          <div className="grid md:grid-cols-2 gap-6 text-gray-600 dark:text-gray-300">
            <div>
              <h3 className="font-bold text-gray-900 dark:text-white mb-2">Beta Weighted Delta</h3>
              <p className="text-sm">
                This normalizes your portfolio's directional risk against the S&P 500 (SPY).
                A value of <strong>+50</strong> means your portfolio moves roughly like 50 shares of SPY.
              </p>
            </div>
            <div>
              <h3 className="font-bold text-gray-900 dark:text-white mb-2">Theta (Time Decay)</h3>
              <p className="text-sm">
                The theoretical dollar amount your portfolio gains (or loses) per day due to time passing, assuming no price movement.
                Positive Theta is generally desired for premium sellers.
              </p>
            </div>
            <div>
              <h3 className="font-bold text-gray-900 dark:text-white mb-2">Vega (Volatility)</h3>
              <p className="text-sm">
                Sensitivity to changes in Implied Volatility (IV). A highly negative Vega means you profit when market fear (IV) drops.
              </p>
            </div>
            <div>
              <h3 className="font-bold text-gray-900 dark:text-white mb-2">Gamma (Acceleration)</h3>
              <p className="text-sm">
                The rate of change of Delta. High Gamma means your directional risk changes rapidly as the market moves.
              </p>
            </div>
          </div>
        </section>

        {/* Monte Carlo */}
        <section id="monte-carlo" className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 flex items-center">
            <span className="bg-orange-100 text-orange-600 p-2 rounded-lg mr-3 text-xl">🎲</span>
            Monte Carlo Simulations
          </h2>
          <div className="space-y-4 text-gray-600 dark:text-gray-300">
            <p>
              We don't just look at the past; we simulate the future. The Monte Carlo engine runs thousands of
              simulations based on your strategy's statistical profile (win rate, avg win/loss, std dev).
            </p>
            <ul className="list-disc list-inside space-y-2 ml-2">
              <li><strong>P50 (Median):</strong> The most likely outcome path.</li>
              <li><strong>P5 (Worst Case):</strong> The bottom 5% of outcomes. Use this to stress-test your risk of ruin.</li>
              <li><strong>P95 (Best Case):</strong> The top 5% of outcomes. The "Blue Sky" scenario.</li>
            </ul>
            <p className="text-sm italic mt-2">
              Tip: Use the "Sandbox" mode to tweak your win rate and see how it impacts your long-term equity curve stability.
            </p>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 flex items-center">
            <span className="bg-green-100 text-green-600 p-2 rounded-lg mr-3 text-xl">❔</span>
            FAQ
          </h2>
          <div className="space-y-6">
             <div>
                 <h3 className="font-bold text-gray-900 dark:text-white">Is my data safe?</h3>
                 <p className="text-gray-600 dark:text-gray-300 text-sm">Yes. This application runs locally or on your private server. Your trade data is processed within your own environment and is not sent to any third-party aggregator.</p>
             </div>
             <div>
                 <h3 className="font-bold text-gray-900 dark:text-white">What brokers are supported?</h3>
                 <p className="text-gray-600 dark:text-gray-300 text-sm">Currently, we support CSV exports from major US brokers (TDA/Schwab, E*Trade, IBKR). Custom formats can be mapped in the backend.</p>
             </div>
             <div>
                 <h3 className="font-bold text-gray-900 dark:text-white">How is "Market Regime" calculated?</h3>
                 <p className="text-gray-600 dark:text-gray-300 text-sm">We analyze the S&P 500 (SPY) price relative to its 200-day Simple Moving Average (SMA). Price {'>'} SMA200 is considered a Bull Market, while Price {'<'} SMA200 indicates a Bear Market context.</p>
             </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Docs;
