import { useState } from 'react';

interface Props {
  onClose: () => void;
  onSave: (q1: string, q2: string, q3: string) => void;
}

export function DailyDebriefModal({ onClose, onSave }: Props) {
  const [q1, setQ1] = useState("");
  const [q2, setQ2] = useState("");
  const [q3, setQ3] = useState("");

  const handleSubmit = () => {
    onSave(q1, q2, q3);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div className="bg-gray-900 text-white rounded-xl max-w-2xl w-full p-6 shadow-2xl border border-gray-700">
        <h2 className="text-2xl font-bold mb-6 text-blue-400">🌙 Daily Debrief</h2>

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-bold text-gray-300 mb-1">
              1. Did the trades I took today reinforce my plan, or did I drift?
            </label>
            <textarea
              className="w-full bg-gray-800 rounded p-3 border border-gray-600 focus:border-blue-500 outline-none text-sm"
              rows={2}
              value={q1} onChange={e => setQ1(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-300 mb-1">
              2. Was the issue the setup, or was it my emotional state?
            </label>
            <textarea
              className="w-full bg-gray-800 rounded p-3 border border-gray-600 focus:border-blue-500 outline-none text-sm"
              rows={2}
              value={q2} onChange={e => setQ2(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-300 mb-1">
              3. What can I do tomorrow to become a better trader?
            </label>
            <textarea
              className="w-full bg-gray-800 rounded p-3 border border-gray-600 focus:border-blue-500 outline-none text-sm"
              rows={2}
              value={q3} onChange={e => setQ3(e.target.value)}
            />
          </div>
        </div>

        <div className="mt-8 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-white">Close</button>
          <button
            onClick={handleSubmit}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-bold"
          >
            Save to Journal
          </button>
        </div>
      </div>
    </div>
  );
}
