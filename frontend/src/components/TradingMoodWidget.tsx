import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface JournalEntry {
  id: string;
  pnl?: number;
  emotions?: string[];
}

export const TradingMoodWidget: React.FC = () => {
  const [chartData, setChartData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get('/api/journal');
        const entries: JournalEntry[] = res.data;

        const emotionPnl: Record<string, number> = {};

        entries.forEach(entry => {
          if (entry.emotions && typeof entry.pnl === 'number') {
            const pnl = entry.pnl;
            entry.emotions.forEach(emotion => {
              emotionPnl[emotion] = (emotionPnl[emotion] || 0) + pnl;
            });
          }
        });

        const labels = Object.keys(emotionPnl);
        const data = Object.values(emotionPnl);

        setChartData({
          labels,
          datasets: [
            {
              label: 'PnL by Emotion',
              data,
              backgroundColor: data.map(val => val >= 0 ? '#10b981' : '#ef4444'),
            },
          ],
        });
      } catch (err) {
        console.error("Failed to fetch journal data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div className="h-48 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-lg"></div>;
  if (!chartData || chartData.labels.length === 0) return (
      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 h-full flex flex-col">
          <h3 className="text-base font-bold text-gray-900 dark:text-white mb-4">Trading Mood Analysis</h3>
          <div className="flex-grow flex items-center justify-center bg-gray-50 dark:bg-gray-800/50 rounded border border-dashed border-gray-300 dark:border-gray-700 text-gray-500 text-sm">
              No mood data available.
          </div>
      </div>
  );

  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
      <h3 className="text-base font-bold text-gray-900 dark:text-white mb-4">Trading Mood Analysis</h3>
      <div className="h-48">
        <Bar
          data={chartData}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                 callbacks: {
                     label: (context) => {
                         let label = context.dataset.label || '';
                         if (label) {
                             label += ': ';
                         }
                         if (context.parsed.y !== null) {
                             label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y);
                         }
                         return label;
                     }
                 }
              }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(100, 100, 100, 0.1)' }
                },
                x: {
                    grid: { display: false }
                }
            }
          }}
        />
      </div>
    </div>
  );
};
