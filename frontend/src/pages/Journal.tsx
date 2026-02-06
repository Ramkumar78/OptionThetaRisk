import React, { useState, useEffect } from 'react';
import axios from 'axios';
import clsx from 'clsx';
import { DailyDebriefModal } from '../components/DailyDebriefModal';
import AreaChart from '../components/AreaChart';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface JournalEntry {
  id: string;
  created_at: number;
  entry_date?: string;
  entry_time?: string;
  symbol: string;
  strategy: string;
  sentiment: string;
  notes: string;
  tags?: string;
  pnl?: number;
}

interface AnalysisResult {
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  best_pattern: string;
  worst_pattern: string;
  best_time: string;
  suggestions: string[];
  patterns: any[];
  time_analysis: any[];
  equity_curve?: { date: string; cumulative_pnl: number }[];
}

const Journal: React.FC = () => {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [showDebrief, setShowDebrief] = useState(false);

  // Form State
  const [symbol, setSymbol] = useState('');
  const [strategy, setStrategy] = useState('');
  const [sentiment, setSentiment] = useState('Neutral');
  const [notes, setNotes] = useState('');
  const [pnl, setPnl] = useState('');
  const [entryDate, setEntryDate] = useState(new Date().toISOString().split('T')[0]);
  const [entryTime, setEntryTime] = useState(new Date().toTimeString().split(' ')[0].slice(0, 5));

  const fetchEntries = async () => {
    try {
      const res = await axios.get('/journal');
      setEntries(res.data);
    } catch (error) {
      console.error("Failed to fetch journal", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post('/journal/add', {
        symbol: symbol.toUpperCase(),
        strategy,
        sentiment,
        notes,
        pnl: pnl ? parseFloat(pnl) : 0,
        entry_date: entryDate,
        entry_time: entryTime
      });
      // Reset form
      setSymbol('');
      setStrategy('');
      setNotes('');
      setPnl('');
      fetchEntries();
    } catch (error) {
      console.error("Failed to add entry", error);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure?')) return;
    try {
      await axios.delete(`/journal/delete/${id}`);
      fetchEntries();
    } catch (error) {
      console.error("Failed to delete", error);
    }
  };

  const handleAnalyze = async () => {
    try {
      const res = await axios.post('/journal/analyze');
      setAnalysis(res.data);
    } catch (error) {
      console.error("Failed to analyze", error);
    }
  };

  const handleSaveDebrief = async (q1: string, q2: string, q3: string) => {
    const combinedNotes = `DAILY DEBRIEF\n\n1. Strategy Execution:\n${q1}\n\n2. Emotional State:\n${q2}\n\n3. Improvement:\n${q3}`;

    try {
        await axios.post('/journal/add', {
            entry_date: new Date().toISOString().split('T')[0],
            entry_time: new Date().toTimeString().split(' ')[0].slice(0, 5),
            symbol: "REVIEW",
            strategy: "PSYCHOLOGY",
            sentiment: "Neutral",
            pnl: 0,
            notes: combinedNotes
        });
        fetchEntries();
    } catch (e) {
        console.error(e);
        alert("Failed to save debrief.");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Input Form */}
      <div className="lg:col-span-1">
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6 sticky top-24">
           <div className="flex justify-between items-center mb-4">
               <h3 id="journal-form-title" className="text-lg font-bold text-gray-900 dark:text-white">New Entry</h3>
                <button
                    onClick={() => setShowDebrief(true)}
                    className="flex items-center text-xs font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
                    Daily Debrief
                </button>
           </div>
           <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                   <label htmlFor="journal-date" className="block text-xs font-semibold text-gray-500 uppercase mb-1">Date</label>
                   <input
                     type="date"
                     id="journal-date"
                     value={entryDate}
                     onChange={(e) => setEntryDate(e.target.value)}
                     className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                     required
                   />
                </div>
                <div>
                   <label htmlFor="journal-time" className="block text-xs font-semibold text-gray-500 uppercase mb-1">Time</label>
                   <input
                     type="time"
                     id="journal-time"
                     value={entryTime}
                     onChange={(e) => setEntryTime(e.target.value)}
                     className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                     required
                   />
                </div>
              </div>

              <div>
                <label htmlFor="journal-symbol" className="block text-xs font-semibold text-gray-500 uppercase mb-1">Symbol</label>
                <input
                  type="text"
                  id="journal-symbol"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                  required
                />
              </div>

              <div>
                 <label htmlFor="journal-strategy" className="block text-xs font-semibold text-gray-500 uppercase mb-1">Strategy</label>
                 <input
                  type="text"
                  id="journal-strategy"
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  placeholder="e.g. Iron Condor"
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                />
              </div>

              <div>
                <label htmlFor="journal-sentiment" className="block text-xs font-semibold text-gray-500 uppercase mb-1">Sentiment</label>
                <select
                  id="journal-sentiment"
                  value={sentiment}
                  onChange={(e) => setSentiment(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                >
                  <option>Bullish</option>
                  <option>Bearish</option>
                  <option>Neutral</option>
                </select>
              </div>

              <div>
                <label htmlFor="journal-pnl" className="block text-xs font-semibold text-gray-500 uppercase mb-1">Realized PnL ($)</label>
                <input
                  type="number"
                  id="journal-pnl"
                  value={pnl}
                  onChange={(e) => setPnl(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                />
              </div>

              <div>
                <label htmlFor="journal-notes" className="block text-xs font-semibold text-gray-500 uppercase mb-1">Notes</label>
                <textarea
                  id="journal-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                ></textarea>
              </div>

              <button
                id="journal-submit-btn"
                type="submit"
                className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded text-sm transition-colors shadow-sm"
              >
                Add Entry
              </button>
           </form>
        </div>
      </div>

      {/* List & Analysis */}
      <div className="lg:col-span-2 space-y-6">
         <div className="flex justify-between items-center bg-white dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800">
             <h2 id="journal-list-title" className="text-lg font-bold text-gray-900 dark:text-white">Your Journal</h2>
             <button
               id="journal-analyze-btn"
               onClick={handleAnalyze}
               className="text-sm px-4 py-2 bg-primary-50 text-primary-700 rounded hover:bg-primary-100 font-medium dark:bg-primary-900/30 dark:text-primary-300 transition-colors flex items-center"
             >
               <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M9 3v4"/><path d="M3 5h4"/><path d="M3 9h4"/></svg>
               Analyze Habits
             </button>
         </div>

         {analysis && (
            <div id="journal-analysis-result" className="bg-white dark:bg-gray-900 rounded-lg border border-primary-100 dark:border-gray-700 animate-fade-in shadow-sm overflow-hidden">
                <div className="bg-primary-50 dark:bg-gray-800/50 px-6 py-4 border-b border-primary-100 dark:border-gray-700">
                    <h3 className="font-bold text-primary-900 dark:text-primary-100 flex items-center">
                        <span className="mr-2">✨</span> AI Insights & Habits
                    </h3>
                </div>

                <div className="p-6 space-y-6">
                    {/* Top Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded border border-gray-100 dark:border-gray-700 text-center">
                             <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-bold">Win Rate</div>
                             <div className={clsx("text-2xl font-bold mt-1", analysis.win_rate >= 50 ? "text-green-600" : "text-red-500")}>
                                 {analysis.win_rate}%
                             </div>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded border border-gray-100 dark:border-gray-700 text-center">
                             <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-bold">Total PnL</div>
                             <div className={clsx("text-2xl font-bold mt-1", analysis.total_pnl >= 0 ? "text-green-600" : "text-red-500")}>
                                 ${analysis.total_pnl.toLocaleString()}
                             </div>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded border border-gray-100 dark:border-gray-700 text-center">
                             <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-bold">Trades</div>
                             <div className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                                 {analysis.total_trades}
                             </div>
                        </div>
                    </div>

                    {/* Equity Curve */}
                    {analysis.equity_curve && analysis.equity_curve.length > 0 && (
                        <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded border border-gray-100 dark:border-gray-700">
                             <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-3">Equity Curve (Cumulative PnL)</h4>
                             <div className="h-64 w-full">
                                <AreaChart
                                    data={analysis.equity_curve.map((p: any) => ({
                                        time: p.date,
                                        value: p.cumulative_pnl
                                    }))}
                                    color="#2563EB"
                                />
                             </div>
                        </div>
                    )}

                    {/* Best/Worst */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                         <div className="p-4 rounded bg-green-50 dark:bg-green-900/10 border border-green-100 dark:border-green-800/30">
                             <div className="text-xs text-green-800 dark:text-green-300 font-bold uppercase mb-1">Best Strategy</div>
                             <div className="text-lg text-gray-900 dark:text-white font-medium">{analysis.best_pattern}</div>
                         </div>
                         <div className="p-4 rounded bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-800/30">
                             <div className="text-xs text-red-800 dark:text-red-300 font-bold uppercase mb-1">Worst Strategy</div>
                             <div className="text-lg text-gray-900 dark:text-white font-medium">{analysis.worst_pattern}</div>
                         </div>
                    </div>

                    {/* Suggestions */}
                    {analysis.suggestions.length > 0 && (
                        <div>
                            <h4 className="font-bold text-gray-900 dark:text-white mb-3 text-xs uppercase tracking-wide">Actionable Suggestions</h4>
                            <ul className="space-y-2">
                                {analysis.suggestions.map((suggestion, idx) => (
                                    <li key={idx} className="flex items-start bg-yellow-50 dark:bg-yellow-900/10 p-3 rounded border border-yellow-100 dark:border-yellow-800/30">
                                        <span className="mr-2 mt-0.5">💡</span>
                                        <span
                                          className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed"
                                          dangerouslySetInnerHTML={{ __html: suggestion }}
                                        />
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
         )}

         <div className="space-y-4">
            {loading ? (
              <p className="text-center text-gray-500 text-sm">Loading entries...</p>
            ) : entries.length === 0 ? (
              <div className="text-center py-10 bg-white dark:bg-gray-900 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
                 <p className="text-gray-500 text-sm">No journal entries yet.</p>
              </div>
            ) : (
              entries.map((entry) => (
                <div key={entry.id} id={`journal-entry-${entry.id}`} className="bg-white dark:bg-gray-900 p-5 rounded-lg border border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-600 transition-colors relative group">
                    <button
                      onClick={() => handleDelete(entry.id)}
                      className="absolute top-4 right-4 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Delete Entry"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                    </button>
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-3">
                           <span className="font-bold text-base text-gray-900 dark:text-white">{entry.symbol}</span>
                           <span className="text-xs px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-300">{entry.strategy || 'Trade'}</span>
                           <span className={clsx(
                             "text-xs px-2 py-0.5 rounded font-medium",
                             entry.sentiment === 'Bullish' ? "bg-green-50 text-green-700 border border-green-100" :
                             entry.sentiment === 'Bearish' ? "bg-red-50 text-red-700 border border-red-100" :
                             "bg-gray-50 text-gray-600 border border-gray-100"
                           )}>{entry.sentiment}</span>
                        </div>
                        <div className="text-right">
                            <div className="text-xs text-gray-400 font-mono">
                              {entry.entry_date || new Date(entry.created_at * 1000).toLocaleDateString()} {entry.entry_time}
                            </div>
                        </div>
                    </div>
                    <p className="text-gray-600 dark:text-gray-400 text-sm mb-3 whitespace-pre-wrap leading-relaxed">{entry.notes}</p>
                    {entry.pnl !== 0 && (
                       <div className={clsx("font-mono text-sm font-bold", entry.pnl && entry.pnl > 0 ? "text-green-600" : "text-red-600")}>
                          {entry.pnl && entry.pnl > 0 ? '+' : ''}{entry.pnl?.toFixed(2)}
                       </div>
                    )}
                </div>
              ))
            )}
         </div>
      </div>
      {showDebrief && <DailyDebriefModal onClose={() => setShowDebrief(false)} onSave={handleSaveDebrief} />}
    </div>
  );
};

export default Journal;
