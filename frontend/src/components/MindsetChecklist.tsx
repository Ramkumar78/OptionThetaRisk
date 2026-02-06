import { useState } from 'react';

const CONTROL_LIST = [
  "My Trading Plan (Entry/Exit Rules)",
  "My Risk Per Trade (Defined Loss)",
  "My Position Sizing (Contracts/Shares)",
  "Entry Criteria (Valid Setup)",
  "Stop Loss Placement (Invalidation Point)",
  "Profit Taking Method (Targets)",
  "Daily Max Loss Limit",
  "My Mental State (Calm/Focused)"
];

const UNCONTROLLABLE_LIST = [
  "Unexpected News / Fed Speakers",
  "Algo Spikes / Flash Crashes",
  "The Outcome of THIS Single Trade",
  "What Other Traders Are Doing"
];

interface Props {
  onClose: () => void;
  onSaveToJournal: (notes: string) => void;
}

export function MindsetChecklist({ onClose, onSaveToJournal }: Props) {
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());
  const [intention, setIntention] = useState("");

  const toggle = (idx: number) => {
    const next = new Set(checkedItems);
    if (next.has(idx)) next.delete(idx);
    else next.add(idx);
    setCheckedItems(next);
  };

  const isReady = checkedItems.size === CONTROL_LIST.length;

  const handleCommit = () => {
    // Save a "Trade" entry that represents this mental check-in
    const note = `[PRE-FLIGHT CHECKLIST COMPLETED]\n\nIntention for today: ${intention || "Disciplined Execution"}`;
    onSaveToJournal(note);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-lg max-w-3xl w-full p-6 border border-gray-200 dark:border-gray-800 flex flex-col max-h-[90vh] shadow-xl">

        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
            The Trader's Control Loop
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-900 dark:hover:text-white text-xl">&times;</button>
        </div>

        <div className="overflow-y-auto pr-2">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Left: Ignore */}
            <div className="p-5 rounded border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
              <h3 className="font-bold text-gray-500 uppercase text-xs tracking-wider mb-4 flex items-center">
                Ignore (Uncontrollable)
              </h3>
              <ul className="list-disc pl-4 text-gray-600 dark:text-gray-400 text-sm space-y-2 marker:text-gray-400">
                {UNCONTROLLABLE_LIST.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
              <p className="mt-6 text-xs text-gray-400 italic border-t border-gray-200 dark:border-gray-700 pt-2">
                "Worrying about these drains the energy needed for execution."
              </p>
            </div>

            {/* Right: Control */}
            <div className="p-5 rounded border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
              <h3 className="font-bold text-primary-600 dark:text-primary-400 uppercase text-xs tracking-wider mb-4 flex items-center">
                Execute (Controllable)
              </h3>
              <div className="space-y-2">
                {CONTROL_LIST.map((item, i) => (
                  <label key={i} className="flex items-start space-x-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 p-2 rounded transition-colors -ml-2">
                    <input
                      type="checkbox"
                      checked={checkedItems.has(i)}
                      onChange={() => toggle(i)}
                      className="mt-0.5 w-4 h-4 text-primary-600 rounded focus:ring-primary-500 border-gray-300 dark:border-gray-600 dark:bg-gray-800"
                    />
                    <span className={`text-sm ${checkedItems.has(i) ? "text-gray-900 dark:text-gray-100 font-medium" : "text-gray-500 dark:text-gray-400"}`}>{item}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Intention Setting */}
          <div className="mt-6">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Daily Intention
            </label>
            <input
              type="text"
              value={intention}
              onChange={(e) => setIntention(e.target.value)}
              className="w-full bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white rounded p-3 border border-gray-200 dark:border-gray-700 focus:border-primary-500 outline-none transition-colors"
              placeholder="One specific goal for today (e.g. 'I will not move my stop loss')..."
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={onClose} className="px-4 py-2 text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors text-sm font-medium">Cancel</button>
          <button
            onClick={handleCommit}
            disabled={!isReady}
            className={`px-6 py-2 rounded text-sm font-bold transition-all ${
              isReady
              ? 'bg-primary-600 hover:bg-primary-700 text-white shadow-sm'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed border border-gray-200 dark:border-gray-700'
            }`}
          >
            {isReady ? "Ready to Trade" : `Checklist (${checkedItems.size}/${CONTROL_LIST.length})`}
          </button>
        </div>
      </div>
    </div>
  );
}
