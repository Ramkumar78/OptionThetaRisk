import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const Docs: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      title: "Get Your Data",
      content: (
        <div className="space-y-2">
          <p>You need transaction history to use the Auditor.</p>
          <ul className="list-disc list-inside text-sm pl-2">
            <li>Export CSV from your broker (Tastytrade, IBKR).</li>
            <li>
              <strong>New user?</strong>{" "}
              <a href="/sample_trades.csv" download className="text-primary-600 hover:underline font-medium">
                Download Sample Data
              </a>{" "}
              to see how it works instantly.
            </li>
          </ul>
        </div>
      )
    },
    {
      title: "Upload to Auditor",
      content: (
        <p>
          Go to the <Link to="/audit" className="text-primary-600 hover:underline">Audit Page</Link> and drop your CSV file.
          The system will parse your trades, group them into strategies, and calculate risk metrics.
        </p>
      )
    },
    {
      title: "Analyze Results",
      content: (
        <p>
          Review the "Verdict". Are you taking too much risk? Is your "Fee Drag" killing your profits?
          Check the <strong>Visual Risk Map</strong> to see concentrated exposures.
        </p>
      )
    }
  ];

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
        {/* Interactive Getting Started */}
        <section id="getting-started" className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
            <span className="bg-blue-100 text-blue-600 p-2 rounded-lg mr-3 text-xl">🚀</span>
            Getting Started
          </h2>

          <div className="grid md:grid-cols-3 gap-4">
            {steps.map((step, idx) => (
              <div
                key={idx}
                onClick={() => setActiveStep(idx)}
                className={`cursor-pointer p-4 rounded-xl border transition-all duration-200 ${
                  activeStep === idx
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-primary-300'
                }`}
              >
                <div className="flex items-center space-x-3 mb-2">
                  <span className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                    activeStep === idx ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                  }`}>
                    {idx + 1}
                  </span>
                  <h3 className={`font-semibold ${activeStep === idx ? 'text-primary-700 dark:text-primary-400' : 'text-gray-700 dark:text-gray-300'}`}>
                    {step.title}
                  </h3>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 p-6 bg-gray-50 dark:bg-gray-700/30 rounded-xl border border-gray-200 dark:border-gray-700">
             <div className="text-gray-600 dark:text-gray-300">
               {steps[activeStep].content}
             </div>
          </div>
        </section>

        {/* Strategy Glossary (UK/Context) */}
        <section id="glossary" className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 flex items-center">
             <span className="bg-indigo-100 text-indigo-600 p-2 rounded-lg mr-3 text-xl">🇬🇧</span>
             Strategy Glossary
          </h2>
          <div className="space-y-6 text-gray-600 dark:text-gray-300">
            <div>
              <h3 className="font-bold text-gray-900 dark:text-white text-lg">VCP (Volatility Contraction Pattern)</h3>
              <p className="mt-1">
                A chart pattern popularized by Mark Minervini. It represents a stock consolidating after an advance.
                Price volatility decreases (contracts) from left to right (e.g., 20% correction, then 10%, then 5%).
                This drying up of supply signals a potential explosive breakout.
              </p>
            </div>
            <div>
              <h3 className="font-bold text-gray-900 dark:text-white text-lg">ISA Trend Following</h3>
              <p className="mt-1">
                Optimized for UK Individual Savings Accounts (ISAs). Since shorting is not allowed in standard ISAs,
                this strategy focuses exclusively on <strong>Long Only</strong> momentum. It filters for stocks in
                "Stage 2" uptrends where the 50-day MA is above the 150-day and 200-day MAs.
              </p>
            </div>
             <div>
              <h3 className="font-bold text-gray-900 dark:text-white text-lg">Liquidity Grab (SMC)</h3>
              <p className="mt-1">
                Smart Money Concepts (SMC) setup. Identifies when price briefly pierces a key support/resistance level
                to "sweep" stop-loss orders (liquidity) before reversing rapidly. A "Bear Trap" or "Bull Trap."
              </p>
            </div>
          </div>
        </section>

        {/* Jargon Buster */}
        <section id="jargon" className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
           <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 flex items-center">
            <span className="bg-teal-100 text-teal-600 p-2 rounded-lg mr-3 text-xl">🧠</span>
            Jargon Buster
          </h2>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
             <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <span className="font-bold text-gray-900 dark:text-white block">Alpha</span>
                <span className="text-gray-600 dark:text-gray-300">Returns generated in excess of the market benchmark (S&P 500). The "Edge."</span>
             </div>
             <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <span className="font-bold text-gray-900 dark:text-white block">Beta</span>
                <span className="text-gray-600 dark:text-gray-300">Measure of volatility relative to the market. Beta of 1.5 means the stock moves 1.5x as much as the market.</span>
             </div>
             <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <span className="font-bold text-gray-900 dark:text-white block">Drawdown</span>
                <span className="text-gray-600 dark:text-gray-300">The peak-to-trough decline in account value. A 50% drawdown requires a 100% gain to recover.</span>
             </div>
             <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <span className="font-bold text-gray-900 dark:text-white block">R-Multiple</span>
                <span className="text-gray-600 dark:text-gray-300">Profit expressed in units of Risk. If you risk $100 and make $300, that is a 3R trade.</span>
             </div>
             <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <span className="font-bold text-gray-900 dark:text-white block">Theta</span>
                <span className="text-gray-600 dark:text-gray-300">Time decay. The amount an option loses value each day as expiration approaches.</span>
             </div>
             <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <span className="font-bold text-gray-900 dark:text-white block">Expectancy</span>
                <span className="text-gray-600 dark:text-gray-300">Average amount you can expect to win (or lose) per trade over the long run.</span>
             </div>
          </div>
        </section>

        {/* Greeks (Existing) */}
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

        {/* Monte Carlo (Existing) */}
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

        {/* FAQ (Existing) */}
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
