import React, { useState } from 'react';
import axios from 'axios';

const QuickActionsSidebar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [symbol, setSymbol] = useState('');
  const [strategy, setStrategy] = useState('');
  const [sentiment, setSentiment] = useState('Neutral');
  const [pnl, setPnl] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post('/journal/add', {
        symbol: symbol.toUpperCase(),
        strategy,
        sentiment,
        pnl: pnl ? parseFloat(pnl) : 0,
        notes,
        entry_date: new Date().toISOString().split('T')[0],
        entry_time: new Date().toTimeString().split(' ')[0].slice(0, 5)
      });
      // Reset and close
      setSymbol('');
      setStrategy('');
      setNotes('');
      setPnl('');
      setIsOpen(false);
      alert('Trade logged successfully!');
    } catch (error) {
      console.error(error);
      alert('Failed to log trade.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(true)}
        className={`fixed right-0 top-1/3 z-40 bg-primary-600 text-white p-2 rounded-l-lg shadow-lg hover:bg-primary-700 transition-transform ${isOpen ? 'translate-x-full' : 'translate-x-0'}`}
        aria-label="Quick Trade"
      >
        <div className="writing-vertical-lr transform rotate-180 text-xs font-bold uppercase tracking-wider py-2" style={{ writingMode: 'vertical-lr' }}>
           ⚡ Quick Add
        </div>
      </button>

      {/* Sidebar Overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm" onClick={() => setIsOpen(false)}></div>
      )}

      {/* Sidebar */}
      <div className={`fixed right-0 top-0 h-full w-80 bg-white dark:bg-gray-800 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
         <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
             <h3 className="font-bold text-gray-900 dark:text-white">Quick Trade Entry</h3>
             <button onClick={() => setIsOpen(false)} aria-label="Close Sidebar" className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                 <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
             </button>
         </div>
         <div className="p-4">
             <form onSubmit={handleSubmit} className="space-y-4">
                 <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Symbol</label>
                    <input
                      type="text"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value)}
                      className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-900 dark:border-gray-600 dark:text-white"
                      required
                      placeholder="e.g. SPY"
                    />
                 </div>
                 <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Strategy</label>
                    <input
                      type="text"
                      value={strategy}
                      onChange={(e) => setStrategy(e.target.value)}
                      className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-900 dark:border-gray-600 dark:text-white"
                      placeholder="e.g. Vertical"
                    />
                 </div>
                 <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Sentiment</label>
                    <select
                      value={sentiment}
                      onChange={(e) => setSentiment(e.target.value)}
                      className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-900 dark:border-gray-600 dark:text-white"
                    >
                      <option>Bullish</option>
                      <option>Bearish</option>
                      <option>Neutral</option>
                    </select>
                 </div>
                 <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Realized PnL ($)</label>
                    <input
                      type="number"
                      value={pnl}
                      onChange={(e) => setPnl(e.target.value)}
                      className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-900 dark:border-gray-600 dark:text-white"
                    />
                 </div>
                 <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Notes</label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      rows={3}
                      className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:bg-gray-900 dark:border-gray-600 dark:text-white"
                    ></textarea>
                 </div>
                 <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded text-sm transition-colors disabled:opacity-50"
                 >
                    {loading ? 'Saving...' : 'Log Trade'}
                 </button>
             </form>
         </div>
      </div>
    </>
  );
};

export default QuickActionsSidebar;
