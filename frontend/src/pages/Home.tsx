import React from 'react';
import { Link } from 'react-router-dom';

const Home: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center space-y-12">
      <div className="relative w-full max-w-lg mb-4">
         <img src="/static/img/find_track_audit.jpg" className="w-full h-auto rounded-full shadow-2xl opacity-90 dark:opacity-80 border-4 border-white dark:border-gray-800" alt="Cycle of Mastery" />
      </div>

      <div className="text-center space-y-4 max-w-3xl">
        <h1 id="home-title" className="text-4xl md:text-6xl font-extrabold tracking-tight text-gray-900 dark:text-white">
          Analyze. Optimize. <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-emerald-500">Evolve.</span>
        </h1>
        <p id="home-subtitle" className="text-lg md:text-xl text-gray-600 dark:text-gray-300">
          The Automated Risk Manager for Stocks & Options.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link
            to="/screener"
            id="home-cta-screener"
            className="w-full sm:w-auto px-8 py-3.5 text-base font-semibold text-white bg-primary-600 rounded-xl hover:bg-primary-700 shadow-lg shadow-primary-500/30 transition-all hover:-translate-y-0.5 focus:ring-4 focus:ring-primary-300 dark:focus:ring-primary-900"
          >
            Market Screener
          </Link>
          <Link
            to="/audit"
            id="home-cta-audit"
            className="w-full sm:w-auto px-8 py-3.5 text-base font-semibold text-gray-900 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 hover:text-primary-600 dark:bg-gray-800 dark:text-white dark:border-gray-700 dark:hover:bg-gray-700 transition-all focus:ring-4 focus:ring-gray-100 dark:focus:ring-gray-700"
          >
            Start Audit
          </Link>
        </div>
      </div>

      <div className="w-full max-w-5xl grid md:grid-cols-3 gap-8 px-4">
        {/* Feature Cards */}
         <div id="feature-card-1" className="bg-white dark:bg-gray-900 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
            <div className="h-12 w-12 bg-primary-100 dark:bg-primary-900/50 rounded-lg flex items-center justify-center mb-4 text-primary-600 dark:text-primary-400 text-2xl">
              🔍
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Detailed Audits</h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm">Upload your trade logs to get instant feedback on risk, PnL, and strategy efficiency.</p>
         </div>

         <div id="feature-card-2" className="bg-white dark:bg-gray-900 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
            <div className="h-12 w-12 bg-emerald-100 dark:bg-emerald-900/50 rounded-lg flex items-center justify-center mb-4 text-emerald-600 dark:text-emerald-400 text-2xl">
              🚀
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Smart Screeners</h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm">Find high-probability setups with our Market, Turtle, and EMA screeners.</p>
         </div>

         <div id="feature-card-3" className="bg-white dark:bg-gray-900 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
            <div className="h-12 w-12 bg-indigo-100 dark:bg-indigo-900/50 rounded-lg flex items-center justify-center mb-4 text-indigo-600 dark:text-indigo-400 text-2xl">
              📓
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Trade Journal</h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm">Log your thoughts and executions to build a habit of continuous improvement.</p>
         </div>
      </div>
    </div>
  );
};

export default Home;
