import React, { useMemo } from 'react';
import { subDays, format, eachDayOfInterval, startOfToday } from 'date-fns';
import clsx from 'clsx';

export interface HeatmapEntry {
  id: string;
  created_at: number;
  entry_date?: string;
  pnl?: number;
  [key: string]: any;
}

interface CalendarHeatmapProps {
  entries: HeatmapEntry[];
}

export const CalendarHeatmap: React.FC<CalendarHeatmapProps> = ({ entries }) => {
  const today = startOfToday();
  const startDate = subDays(today, 364); // Last 365 days roughly

  const days = useMemo(() => {
    return eachDayOfInterval({ start: startDate, end: today });
  }, [startDate, today]);

  const data = useMemo(() => {
    const map = new Map<string, number>();

    entries.forEach(entry => {
      let dateStr = '';
      if (entry.entry_date) {
        dateStr = entry.entry_date;
      } else {
        dateStr = format(new Date(entry.created_at * 1000), 'yyyy-MM-dd');
      }

      const current = map.get(dateStr) || 0;
      map.set(dateStr, current + (entry.pnl || 0));
    });

    return map;
  }, [entries]);

  // We want a grid that flows by column (weeks).
  // CSS Grid with grid-rows-7 and grid-flow-col works perfectly.

  return (
    <div className="w-full overflow-x-auto bg-white dark:bg-gray-900 p-4 rounded-lg border border-gray-200 dark:border-gray-800 mb-8">
      <div className="flex justify-between items-center mb-2">
         <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">Trading Consistency</h3>
         <div className="flex items-center space-x-2 text-xs">
            <span className="text-gray-400">Less</span>
            <div className="w-3 h-3 bg-red-500 rounded-sm"></div>
            <div className="w-3 h-3 bg-gray-200 dark:bg-gray-800 rounded-sm"></div>
            <div className="w-3 h-3 bg-green-500 rounded-sm"></div>
            <span className="text-gray-400">More</span>
         </div>
      </div>

      <div className="grid grid-rows-7 grid-flow-col gap-1 w-max">
        {days.map((day) => {
          const dateStr = format(day, 'yyyy-MM-dd');
          const pnl = data.get(dateStr);
          const hasTrade = data.has(dateStr);

          let colorClass = "bg-gray-200 dark:bg-gray-800"; // No trade

          if (hasTrade) {
            if (pnl !== undefined) {
               if (pnl > 0) colorClass = "bg-green-500";
               else if (pnl < 0) colorClass = "bg-red-500";
               else colorClass = "bg-gray-400"; // Breakeven
            }
          }

          return (
            <div
              key={dateStr}
              className={clsx("w-3 h-3 rounded-sm transition-colors", colorClass)}
              title={`${dateStr}: ${hasTrade ? `$${pnl?.toFixed(2)}` : 'No Trades'}`}
            ></div>
          );
        })}
      </div>
    </div>
  );
};
