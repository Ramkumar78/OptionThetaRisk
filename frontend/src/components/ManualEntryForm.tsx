import React, { useState } from 'react';

export interface JournalEntryData {
  symbol: string;
  strategy: string;
  sentiment: string;
  notes: string;
  pnl: number;
  emotions: string[];
  entry_date: string;
  entry_time: string;
}

interface ManualEntryFormProps {
  onSubmit: (data: JournalEntryData) => void;
  onDebrief?: () => void; // Optional for Journal page
}

export const ManualEntryForm: React.FC<ManualEntryFormProps> = ({ onSubmit, onDebrief }) => {
  const [symbol, setSymbol] = useState('');
  const [strategy, setStrategy] = useState('');
  const [sentiment, setSentiment] = useState('Neutral');
  const [notes, setNotes] = useState('');
  const [pnl, setPnl] = useState('');
  const [emotions, setEmotions] = useState<string[]>([]);
  const [entryDate, setEntryDate] = useState(new Date().toISOString().split('T')[0]);
  const [entryTime, setEntryTime] = useState(new Date().toTimeString().split(' ')[0].slice(0, 5));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      symbol: symbol.toUpperCase(),
      strategy,
      sentiment,
      notes,
      pnl: pnl ? parseFloat(pnl) : 0,
      emotions,
      entry_date: entryDate,
      entry_time: entryTime
    });
    setSymbol('');
    setStrategy('');
    setNotes('');
    setPnl('');
    setEmotions([]);
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
       <div className="flex justify-between items-center mb-4">
           <h3 className="text-lg font-bold text-gray-900 dark:text-white">New Entry</h3>
            {onDebrief && (
                <button
                    type="button"
                    onClick={onDebrief}
                    className="flex items-center text-xs font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
                    Daily Debrief
                </button>
            )}
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

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-2">Emotions</label>
            <div className="flex flex-wrap gap-2">
              {['Planned', 'Impulsive', 'Revenge', 'Disciplined'].map((emotion) => (
                <label key={emotion} className="flex items-center space-x-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer bg-gray-50 dark:bg-gray-800 px-3 py-1.5 rounded border border-gray-200 dark:border-gray-700 hover:border-gray-300">
                  <input
                    type="checkbox"
                    checked={emotions.includes(emotion)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setEmotions([...emotions, emotion]);
                      } else {
                        setEmotions(emotions.filter(em => em !== emotion));
                      }
                    }}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span>{emotion}</span>
                </label>
              ))}
            </div>
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
  );
};
