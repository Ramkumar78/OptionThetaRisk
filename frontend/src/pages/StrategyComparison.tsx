import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Tooltip from '../components/ui/Tooltip';

interface StrategyDetail {
  Strategy_Name: string;
  Reliability_Score: number;
  Philosophy: string;
  Long_Term_Filter: string;
  Intermediate_Filter: string;
  Core_Entry_Trigger: string;
  Unique_Indicator: string;
  Stop_Loss_Logic: string;
  Profit_Target: string;
  Best_Used_For: string;
  Mathematical_Core: string;
  Risk_Management: string;
  Breakout_Date: string;
}

const StrategyComparison: React.FC = () => {
  const [strategies, setStrategies] = useState<StrategyDetail[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('/api/strategies/comparison');
        setStrategies(response.data);
      } catch (error) {
        console.error("Failed to fetch strategy data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400';
    if (score >= 75) return 'text-blue-600 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400';
    return 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-400';
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500 animate-pulse">Loading Strategy Guide...</div>;
  }

  return (
    <div className="space-y-6 pb-10">
      <header>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">Strategy Guide & Reliability Ratings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Comparative analysis of all algorithmic strategies available in TradeGuardian.
        </p>
      </header>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400 border-b dark:border-gray-700">
              <tr>
                <th className="px-6 py-4 font-bold">Strategy Name</th>
                <th className="px-6 py-4 text-center font-bold">Reliability</th>
                <th className="px-6 py-4 font-bold">Philosophy</th>
                <th className="px-6 py-4 font-bold">Core Trigger</th>
                <th className="px-6 py-4 font-bold">Stop Loss</th>
                <th className="px-6 py-4 font-bold">Profit Target</th>
                <th className="px-6 py-4 font-bold">Best Used For</th>
                <th className="px-6 py-4 font-bold">Math Core</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {strategies.map((strategy, index) => (
                <tr key={index} className="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                  <td className="px-6 py-4 font-medium text-gray-900 dark:text-white whitespace-nowrap">
                    <div className="text-base">{strategy.Strategy_Name}</div>
                    <div className="text-xs text-gray-500 font-normal mt-0.5 truncate max-w-[200px]" title={strategy.Unique_Indicator}>{strategy.Unique_Indicator}</div>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${getScoreColor(strategy.Reliability_Score)}`}>
                      {strategy.Reliability_Score}/100
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-600 dark:text-gray-300">
                    <div className="font-medium">{strategy.Philosophy}</div>
                    <div className="text-xs text-gray-500 mt-1 truncate max-w-[150px]" title={strategy.Long_Term_Filter}>Filter: {strategy.Long_Term_Filter}</div>
                  </td>
                  <td className="px-6 py-4 text-xs font-mono text-gray-600 dark:text-gray-300 whitespace-pre-wrap max-w-[200px]">
                    {strategy.Core_Entry_Trigger}
                  </td>
                  <td className="px-6 py-4 text-gray-600 dark:text-gray-300 text-xs">
                    {strategy.Stop_Loss_Logic}
                  </td>
                  <td className="px-6 py-4 text-gray-600 dark:text-gray-300 text-xs">
                    {strategy.Profit_Target}
                  </td>
                  <td className="px-6 py-4 text-gray-600 dark:text-gray-300 text-xs">
                    {strategy.Best_Used_For}
                  </td>
                  <td className="px-6 py-4 text-gray-500 text-center">
                    <Tooltip content={strategy.Mathematical_Core}>
                        <span className="text-primary-600 hover:text-primary-700 dark:text-primary-400 cursor-help border-b border-dotted border-primary-500">Info</span>
                    </Tooltip>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="text-xs text-gray-500 dark:text-gray-400 mt-4 px-2 italic bg-gray-50 dark:bg-gray-800/50 p-3 rounded border border-gray-100 dark:border-gray-700">
          * Reliability Score is calculated based on: Defined Risk Rules (Stop/Target), Volatility Integration, Trend Alignment, and Multi-Factor Confluence.
          It does not guarantee future performance.
      </div>
    </div>
  );
};

export default StrategyComparison;
