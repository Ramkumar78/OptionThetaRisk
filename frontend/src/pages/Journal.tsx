import React, { useState, useEffect } from 'react';
import axios from 'axios';
import clsx from 'clsx';

interface JournalEntry {
  id: string;
  created_at: number;
  symbol: string;
  strategy: string;
  sentiment: string;
  notes: string;
  tags?: string;
  pnl?: number;
}

const Journal: React.FC = () => {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [analysis, setAnalysis] = useState<any>(null);

  // Form State
  const [symbol, setSymbol] = useState('');
  const [strategy, setStrategy] = useState('');
  const [sentiment, setSentiment] = useState('Neutral');
  const [notes, setNotes] = useState('');
  const [pnl, setPnl] = useState('');

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
        pnl: pnl ? parseFloat(pnl) : 0
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

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Input Form */}
      <div className="lg:col-span-1">
        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-800 p-6 sticky top-24">
           <h3 id="journal-form-title" className="text-xl font-bold text-gray-900 dark:text-white mb-4">New Journal Entry</h3>
           <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="journal-symbol" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Symbol</label>
                <input
                  type="text"
                  id="journal-symbol"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                  required
                />
              </div>

              <div>
                 <label htmlFor="journal-strategy" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Strategy</label>
                 <input
                  type="text"
                  id="journal-strategy"
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  placeholder="e.g. Iron Condor"
                  className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                />
              </div>

              <div>
                <label htmlFor="journal-sentiment" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Sentiment</label>
                <select
                  id="journal-sentiment"
                  value={sentiment}
                  onChange={(e) => setSentiment(e.target.value)}
                  className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                >
                  <option>Bullish</option>
                  <option>Bearish</option>
                  <option>Neutral</option>
                </select>
              </div>

              <div>
                <label htmlFor="journal-pnl" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Realized PnL ($)</label>
                <input
                  type="number"
                  id="journal-pnl"
                  value={pnl}
                  onChange={(e) => setPnl(e.target.value)}
                  className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                />
              </div>

              <div>
                <label htmlFor="journal-notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Notes</label>
                <textarea
                  id="journal-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                ></textarea>
              </div>

              <button
                id="journal-submit-btn"
                type="submit"
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                Add Entry
              </button>
           </form>
        </div>
      </div>

      {/* List & Analysis */}
      <div className="lg:col-span-2 space-y-6">
         <div className="flex justify-between items-center bg-white dark:bg-gray-900 p-4 rounded-xl border border-gray-200 dark:border-gray-800">
             <h2 id="journal-list-title" className="text-lg font-bold text-gray-900 dark:text-white">Your Journal</h2>
             <button
               id="journal-analyze-btn"
               onClick={handleAnalyze}
               className="text-sm px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 font-medium dark:bg-indigo-900 dark:text-indigo-300"
             >
               <i className="bi bi-magic mr-2"></i>Analyze Habits
             </button>
         </div>

         {analysis && (
            <div id="journal-analysis-result" className="bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-gray-800 dark:to-gray-800 p-6 rounded-xl border border-indigo-100 dark:border-gray-700 animate-fade-in">
                <h3 className="font-bold text-indigo-900 dark:text-indigo-300 mb-2">AI Insights</h3>
                <div className="prose dark:prose-invert text-sm">
                   {/*
                      Placeholder for analysis rendering.
                      Since the actual structure depends on backend, we just dump it for now.
                   */}
                   <pre>{JSON.stringify(analysis, null, 2)}</pre>
                </div>
            </div>
         )}

         <div className="space-y-4">
            {loading ? (
              <p className="text-center text-gray-500">Loading entries...</p>
            ) : entries.length === 0 ? (
              <div className="text-center py-10 bg-white dark:bg-gray-900 rounded-2xl border border-dashed border-gray-300 dark:border-gray-700">
                 <p className="text-gray-500">No journal entries yet.</p>
              </div>
            ) : (
              entries.map((entry) => (
                <div key={entry.id} id={`journal-entry-${entry.id}`} className="bg-white dark:bg-gray-900 p-5 rounded-xl border border-gray-100 dark:border-gray-800 shadow-sm hover:shadow-md transition-shadow relative group">
                    <button
                      onClick={() => handleDelete(entry.id)}
                      className="absolute top-4 right-4 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Delete Entry"
                    >
                      🗑️
                    </button>
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-3">
                           <span className="font-bold text-lg text-gray-900 dark:text-white">{entry.symbol}</span>
                           <span className="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">{entry.strategy || 'Trade'}</span>
                           <span className={clsx(
                             "text-xs px-2 py-1 rounded",
                             entry.sentiment === 'Bullish' ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300" :
                             entry.sentiment === 'Bearish' ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300" :
                             "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                           )}>{entry.sentiment}</span>
                        </div>
                        <span className="text-xs text-gray-400">
                          {new Date(entry.created_at * 1000).toLocaleDateString()}
                        </span>
                    </div>
                    <p className="text-gray-600 dark:text-gray-300 text-sm mb-3 whitespace-pre-wrap">{entry.notes}</p>
                    {entry.pnl !== 0 && (
                       <div className={clsx("font-mono text-sm font-bold", entry.pnl && entry.pnl > 0 ? "text-emerald-600" : "text-red-600")}>
                          {entry.pnl && entry.pnl > 0 ? '+' : ''}{entry.pnl?.toFixed(2)}
                       </div>
                    )}
                </div>
              ))
            )}
         </div>
      </div>
    </div>
  );
};

export default Journal;
