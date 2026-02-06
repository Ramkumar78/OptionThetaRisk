import React, { useState, useEffect } from 'react';

const PositionSizer: React.FC = () => {
  const [accountSize, setAccountSize] = useState<number>(10000);
  const [riskPercentage, setRiskPercentage] = useState<number>(1);
  const [stopLossAmount, setStopLossAmount] = useState<number | ''>('');
  const [entryPrice, setEntryPrice] = useState<number | ''>('');
  const [maxShares, setMaxShares] = useState<number>(0);
  const [showWarning, setShowWarning] = useState<boolean>(false);

  useEffect(() => {
    if (stopLossAmount && typeof stopLossAmount === 'number' && stopLossAmount > 0) {
        const riskAmount = accountSize * (riskPercentage / 100);
        // Using Math.floor to be conservative with share count
        const shares = Math.floor(riskAmount / stopLossAmount);
        setMaxShares(shares);

        if (entryPrice && typeof entryPrice === 'number') {
            const positionValue = shares * entryPrice;
            const concentrationThreshold = accountSize * 0.20;
            setShowWarning(positionValue > concentrationThreshold);
        } else {
            setShowWarning(false);
        }
    } else {
        setMaxShares(0);
        setShowWarning(false);
    }
  }, [accountSize, riskPercentage, stopLossAmount, entryPrice]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 border border-gray-100 dark:border-gray-700 max-w-md w-full">
      <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Position Sizer</h3>

      <div className="space-y-4">
        <div>
          <label htmlFor="account-size" className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
            Account Size ($)
          </label>
          <input
            type="number"
            id="account-size"
            value={accountSize}
            onChange={(e) => setAccountSize(Number(e.target.value))}
            className="w-full p-2.5 text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
          />
        </div>

        <div>
          <label htmlFor="risk-percentage" className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
            Risk Per Trade %
          </label>
          <input
            type="number"
            id="risk-percentage"
            value={riskPercentage}
            onChange={(e) => setRiskPercentage(Number(e.target.value))}
            className="w-full p-2.5 text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
          />
        </div>

        <div>
          <label htmlFor="stop-loss-amount" className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
            Stop Loss Amount ($ distance)
          </label>
          <input
            type="number"
            id="stop-loss-amount"
            value={stopLossAmount}
            onChange={(e) => setStopLossAmount(e.target.value === '' ? '' : Number(e.target.value))}
            className="w-full p-2.5 text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
            placeholder="e.g. 2.50"
          />
        </div>

        <div>
          <label htmlFor="entry-price" className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
            Entry Price ($) <span className="text-gray-400 font-normal">(Optional, for warning)</span>
          </label>
          <input
            type="number"
            id="entry-price"
            value={entryPrice}
            onChange={(e) => setEntryPrice(e.target.value === '' ? '' : Number(e.target.value))}
            className="w-full p-2.5 text-sm text-gray-900 bg-gray-50 rounded-lg border border-gray-300 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white"
            placeholder="e.g. 150.00"
          />
        </div>

        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
                Max Shares to Buy: <span className="text-primary-600 dark:text-primary-400">{maxShares}</span>
            </div>
            {showWarning && (
                <div className="mt-2 text-sm text-red-600 dark:text-red-400 font-medium animate-pulse">
                    ⚠️ Concentration Risk: Position size exceeds 20% of account!
                </div>
            )}
        </div>
      </div>
    </div>
  );
};

export default PositionSizer;
