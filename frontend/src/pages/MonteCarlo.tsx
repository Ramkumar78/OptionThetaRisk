import React, { useState } from 'react';
import { runMonteCarloSimulation } from '../api';

interface SimulationResult {
  prob_ruin_50pct: number;
  median_final_equity: number;
  initial_capital: number;
  avg_return_pct: number;
  worst_case_return: number;
  best_case_return: number;
  median_drawdown: number;
  worst_case_drawdown: number;
  message: string;
}

const MonteCarlo: React.FC = () => {
  const [ticker, setTicker] = useState('SPY');
  const [strategy, setStrategy] = useState('turtle');
  const [simulations, setSimulations] = useState<number>(10000);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await runMonteCarloSimulation(ticker, strategy, simulations);
      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.error || err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Monte Carlo Sandbox</h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          Simulate thousands of portfolio lifetimes based on historical strategy performance to assess tail risk and expected returns.
        </p>

        <form onSubmit={handleRun} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label htmlFor="ticker-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ticker</label>
            <input
              id="ticker-input"
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              placeholder="e.g. SPY"
              required
            />
          </div>

          <div>
            <label htmlFor="strategy-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Strategy</label>
            <select
              id="strategy-select"
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              <option value="turtle">Turtle (Trend)</option>
              <option value="alpha101">Alpha101 (Mean Rev)</option>
              <option value="grandmaster">Grandmaster</option>
              <option value="isa">ISA Trend</option>
              <option value="master_convergence">Master Convergence</option>
            </select>
          </div>

          <div>
            <label htmlFor="simulations-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Simulations</label>
            <input
              id="simulations-input"
              type="number"
              value={simulations}
              onChange={(e) => setSimulations(Number(e.target.value) || 10000)}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              min="100"
              max="100000"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg shadow-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Simulating...
              </>
            ) : (
              'Run Simulation'
            )}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg">
            ⚠️ {error}
          </div>
        )}
      </div>

      {result && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card
            label="Risk of Ruin (>50% DD)"
            value={`${result.prob_ruin_50pct}%`}
            color={result.prob_ruin_50pct > 5 ? "red" : "green"}
            desc="Probability of experiencing a 50% drawdown."
          />
          <Card
             label="Median Final Equity"
             value={`$${result.median_final_equity.toLocaleString()}`}
             color="blue"
             desc={`Starting from $${result.initial_capital.toLocaleString()}`}
          />
          <Card
             label="Average Return"
             value={`${result.avg_return_pct}%`}
             color={result.avg_return_pct > 0 ? "green" : "red"}
             desc="Mean total return across all simulations."
          />
           <Card
             label="Median Drawdown"
             value={`${result.median_drawdown}%`}
             color="orange"
             desc="Median depth of drawdown encountered."
          />

          <div className="md:col-span-2 lg:col-span-4 bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
             <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Detailed Statistics</h3>
             <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                 <div>
                     <h4 className="text-sm font-medium text-gray-500 uppercase mb-3">Equity Range (90% CI)</h4>
                     <div className="space-y-3">
                         <div className="flex justify-between items-center p-3 bg-red-50 dark:bg-red-900/10 rounded-lg">
                             <span className="text-gray-600 dark:text-gray-400">Worst Case (5th Percentile)</span>
                             <span className="font-mono font-bold text-red-600 dark:text-red-400">{result.worst_case_return}%</span>
                         </div>
                         <div className="flex justify-between items-center p-3 bg-green-50 dark:bg-green-900/10 rounded-lg">
                             <span className="text-gray-600 dark:text-gray-400">Best Case (95th Percentile)</span>
                             <span className="font-mono font-bold text-green-600 dark:text-green-400">+{result.best_case_return}%</span>
                         </div>
                     </div>
                 </div>

                 <div>
                     <h4 className="text-sm font-medium text-gray-500 uppercase mb-3">Drawdown Analysis</h4>
                     <div className="space-y-3">
                         <div className="flex justify-between items-center p-3 bg-orange-50 dark:bg-orange-900/10 rounded-lg">
                             <span className="text-gray-600 dark:text-gray-400">Median Drawdown</span>
                             <span className="font-mono font-bold text-orange-600 dark:text-orange-400">{result.median_drawdown}%</span>
                         </div>
                         <div className="flex justify-between items-center p-3 bg-red-50 dark:bg-red-900/10 rounded-lg">
                             <span className="text-gray-600 dark:text-gray-400">Worst Case Drawdown (95% CI)</span>
                             <span className="font-mono font-bold text-red-600 dark:text-red-400">{result.worst_case_drawdown}%</span>
                         </div>
                     </div>
                 </div>
             </div>

             <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-700 text-center text-sm text-gray-500">
                 {result.message}
             </div>
          </div>
        </div>
      )}
    </div>
  );
};

const Card = ({ label, value, color, desc }: { label: string, value: string, color: string, desc: string }) => {
    const colorClasses: Record<string, string> = {
        red: "text-red-600 dark:text-red-400",
        green: "text-emerald-600 dark:text-emerald-400",
        blue: "text-blue-600 dark:text-blue-400",
        orange: "text-orange-600 dark:text-orange-400",
        gray: "text-gray-900 dark:text-white"
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</h3>
            <div className={`text-2xl font-bold mt-2 ${colorClasses[color] || colorClasses.gray}`}>
                {value}
            </div>
            <p className="text-xs text-gray-400 mt-2">{desc}</p>
        </div>
    );
};

export default MonteCarlo;
