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
    <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div className="bg-gray-900 text-white rounded-xl max-w-3xl w-full p-6 shadow-2xl border border-gray-700 flex flex-col max-h-[90vh]">

        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-emerald-400 flex items-center">
            <span className="text-3xl mr-2">🧘</span> The Trader's Control Loop
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>

        <div className="overflow-y-auto pr-2">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Left: Ignore */}
            <div className="bg-red-900/10 p-5 rounded-lg border border-red-900/30">
              <h3 className="font-bold text-red-400 mb-3 text-lg flex items-center">
                <span className="mr-2">🚫</span> IGNORE (Uncontrollable)
              </h3>
              <ul className="list-disc pl-5 text-gray-400 text-sm space-y-2">
                {UNCONTROLLABLE_LIST.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
              <p className="mt-6 text-xs text-gray-500 italic border-t border-red-900/30 pt-2">
                "Worrying about these drains the energy needed for execution."
              </p>
            </div>

            {/* Right: Control */}
            <div className="bg-emerald-900/10 p-5 rounded-lg border border-emerald-900/30">
              <h3 className="font-bold text-emerald-400 mb-3 text-lg flex items-center">
                <span className="mr-2">✅</span> EXECUTE (Controllable)
              </h3>
              <div className="space-y-2">
                {CONTROL_LIST.map((item, i) => (
                  <label key={i} className="flex items-start space-x-3 cursor-pointer hover:bg-white/5 p-2 rounded transition-colors">
                    <input
                      type="checkbox"
                      checked={checkedItems.has(i)}
                      onChange={() => toggle(i)}
                      className="mt-1 w-4 h-4 text-emerald-500 rounded focus:ring-emerald-500 bg-gray-800 border-gray-600"
                    />
                    <span className={`text-sm ${checkedItems.has(i) ? "text-emerald-200" : "text-gray-400"}`}>{item}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Intention Setting */}
          <div className="mt-6">
            <label className="block text-sm font-medium text-blue-400 mb-2">
              🎯 One specific goal for today (e.g., "I will not move my stop loss")
            </label>
            <input
              type="text"
              value={intention}
              onChange={(e) => setIntention(e.target.value)}
              className="w-full bg-gray-800 text-white rounded p-3 border border-gray-600 focus:border-blue-500 outline-none"
              placeholder="Type your intention here..."
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-gray-700">
          <button onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-white transition-colors">Cancel</button>
          <button
            onClick={handleCommit}
            disabled={!isReady}
            className={`px-8 py-2 rounded font-bold transition-all shadow-lg ${
              isReady
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white transform hover:scale-105'
              : 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
            }`}
          >
            {isReady ? "I Am Ready to Trade" : `Complete Checklist (${checkedItems.size}/${CONTROL_LIST.length})`}
          </button>
        </div>
      </div>
    </div>
  );
}
