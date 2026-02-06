import React, { useState, useEffect } from 'react';

interface MindsetChecklistProps {
  isOpen: boolean;
  onConfirm: () => void;
  onClose: () => void;
  actionName?: string;
}

export const MindsetChecklist: React.FC<MindsetChecklistProps> = ({ isOpen, onConfirm, onClose, actionName = "Proceed" }) => {
  const [q1, setQ1] = useState<string | null>(null); // Chasing loss? (No)
  const [q2, setQ2] = useState<string | null>(null); // Within risk plan? (Yes)
  const [q3, setQ3] = useState<string | null>(null); // Calm? (Yes)

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setQ1(null);
      setQ2(null);
      setQ3(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const isValid = q1 === 'no' && q2 === 'yes' && q3 === 'yes';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-md w-full border border-blue-100 dark:border-blue-900 overflow-hidden transform transition-all">
        {/* Header */}
        <div className="bg-blue-50 dark:bg-blue-900/30 p-6 border-b border-blue-100 dark:border-blue-800">
          <h2 className="text-xl font-bold text-blue-900 dark:text-blue-100 flex items-center">
            <span className="text-2xl mr-2">🧠</span> Mindset Check
          </h2>
          <p className="text-blue-600 dark:text-blue-300 text-sm mt-1">
            Pause and reflect before you {actionName.toLowerCase()}.
          </p>
        </div>

        {/* content */}
        <div className="p-6 space-y-6">
          {/* Q1 */}
          <div className="space-y-2">
            <p className="font-medium text-gray-800 dark:text-gray-200">1. Am I chasing a loss?</p>
            <div className="flex space-x-4">
              <label className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg border cursor-pointer transition-colors ${q1 === 'yes' ? 'bg-red-100 border-red-300 text-red-800 dark:bg-red-900/30 dark:border-red-800 dark:text-red-200' : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-gray-300'}`}>
                <input type="radio" name="q1" className="hidden" onChange={() => setQ1('yes')} checked={q1 === 'yes'} />
                <span>Yes</span>
              </label>
              <label className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg border cursor-pointer transition-colors ${q1 === 'no' ? 'bg-green-100 border-green-300 text-green-800 dark:bg-green-900/30 dark:border-green-800 dark:text-green-200' : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-gray-300'}`}>
                <input type="radio" name="q1" className="hidden" onChange={() => setQ1('no')} checked={q1 === 'no'} />
                <span>No</span>
              </label>
            </div>
          </div>

           {/* Q2 */}
           <div className="space-y-2">
            <p className="font-medium text-gray-800 dark:text-gray-200">2. Is this within my risk plan?</p>
            <div className="flex space-x-4">
              <label className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg border cursor-pointer transition-colors ${q2 === 'yes' ? 'bg-green-100 border-green-300 text-green-800 dark:bg-green-900/30 dark:border-green-800 dark:text-green-200' : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-gray-300'}`}>
                <input type="radio" name="q2" className="hidden" onChange={() => setQ2('yes')} checked={q2 === 'yes'} />
                <span>Yes</span>
              </label>
              <label className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg border cursor-pointer transition-colors ${q2 === 'no' ? 'bg-red-100 border-red-300 text-red-800 dark:bg-red-900/30 dark:border-red-800 dark:text-red-200' : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-gray-300'}`}>
                <input type="radio" name="q2" className="hidden" onChange={() => setQ2('no')} checked={q2 === 'no'} />
                <span>No</span>
              </label>
            </div>
          </div>

           {/* Q3 */}
           <div className="space-y-2">
            <p className="font-medium text-gray-800 dark:text-gray-200">3. Am I calm?</p>
            <div className="flex space-x-4">
              <label className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg border cursor-pointer transition-colors ${q3 === 'yes' ? 'bg-green-100 border-green-300 text-green-800 dark:bg-green-900/30 dark:border-green-800 dark:text-green-200' : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-gray-300'}`}>
                <input type="radio" name="q3" className="hidden" onChange={() => setQ3('yes')} checked={q3 === 'yes'} />
                <span>Yes</span>
              </label>
              <label className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg border cursor-pointer transition-colors ${q3 === 'no' ? 'bg-red-100 border-red-300 text-red-800 dark:bg-red-900/30 dark:border-red-800 dark:text-red-200' : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-gray-300'}`}>
                <input type="radio" name="q3" className="hidden" onChange={() => setQ3('no')} checked={q3 === 'no'} />
                <span>No</span>
              </label>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 dark:bg-gray-900/50 p-6 flex justify-between items-center border-t border-gray-100 dark:border-gray-800">
             <button
                onClick={onClose}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 font-medium hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
             >
                Cancel
             </button>
             <button
                id="mindset-confirm-btn"
                onClick={onConfirm}
                disabled={!isValid}
                className={`px-6 py-2 rounded-lg font-bold shadow-sm transition-all ${isValid ? 'bg-blue-600 hover:bg-blue-700 text-white transform hover:scale-105' : 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'}`}
             >
                {actionName}
             </button>
        </div>
      </div>
    </div>
  );
};
