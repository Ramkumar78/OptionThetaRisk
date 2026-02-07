import React, { useState } from 'react';
import axios from 'axios';
import { ManualEntryForm, type JournalEntryData } from './ManualEntryForm';
import { MindsetChecklist } from './MindsetChecklist';
import clsx from 'clsx';

interface QuickActionsSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const QuickActionsSidebar: React.FC<QuickActionsSidebarProps> = ({ isOpen, onClose }) => {
  const [showChecklist, setShowChecklist] = useState(false);
  const [pendingEntry, setPendingEntry] = useState<JournalEntryData | null>(null);

  const handleSubmit = (data: JournalEntryData) => {
    setPendingEntry(data);
    setShowChecklist(true);
  };

  const handleConfirmedSubmit = async () => {
    setShowChecklist(false);
    if (!pendingEntry) return;

    try {
      await axios.post('/api/journal/add', pendingEntry);
      setPendingEntry(null);
      alert("Trade Logged Successfully! 🚀");
      onClose(); // Close sidebar on success
    } catch (error) {
      console.error("Failed to add entry", error);
      alert("Failed to log trade.");
    }
  };

  return (
    <>
        <div
            className={clsx(
                "fixed inset-y-0 right-0 z-40 w-full sm:w-96 bg-white dark:bg-gray-900 shadow-2xl transform transition-transform duration-300 ease-in-out border-l border-gray-200 dark:border-gray-800",
                isOpen ? "translate-x-0" : "translate-x-full"
            )}
        >
            <div className="h-full flex flex-col p-6 overflow-y-auto">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white">Quick Trade</h2>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>

                <ManualEntryForm onSubmit={handleSubmit} />

            </div>
        </div>

        {/* Overlay */}
        {isOpen && (
            <div
                className="fixed inset-0 bg-black/50 z-30 backdrop-blur-sm"
                onClick={onClose}
            ></div>
        )}

        <MindsetChecklist
            isOpen={showChecklist}
            onClose={() => setShowChecklist(false)}
            onConfirm={handleConfirmedSubmit}
            actionName="Log Trade"
        />
    </>
  );
};
