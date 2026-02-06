import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

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

const TradingMoodWidget: React.FC = () => {
  const [chartData, setChartData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('/journal');
        const entries: JournalEntry[] = response.data;

        const emotionStats: Record<string, { totalPnl: number; count: number }> = {};

        entries.forEach(entry => {
          if (entry.emotions && entry.emotions.length > 0 && entry.pnl !== undefined) {
            entry.emotions.forEach(emotion => {
              if (!emotionStats[emotion]) {
                emotionStats[emotion] = { totalPnl: 0, count: 0 };
              }
              emotionStats[emotion].totalPnl += entry.pnl!;
              emotionStats[emotion].count += 1;
            });
          }
        });

        const labels = Object.keys(emotionStats);
        const data = labels.map(label => {
            const stats = emotionStats[label];
            return stats.count > 0 ? stats.totalPnl / stats.count : 0;
        });

        const colors = data.map(val => val >= 0 ? '#10b981' : '#ef4444');

        setChartData({
          labels,
          datasets: [
            {
              label: 'Avg PnL per Mood ($)',
              data,
              backgroundColor: colors,
              borderRadius: 4,
            },
          ],
        });
      } catch (error) {
        console.error('Failed to fetch journal data for mood widget', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div className="h-48 flex items-center justify-center text-sm text-gray-500">Loading Mood Data...</div>;

  if (!chartData || chartData.labels.length === 0) {
      return (
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 h-full flex flex-col">
          <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">Trading Mood</h3>
          <div className="flex-grow min-h-[150px] flex items-center justify-center text-sm text-gray-500 bg-gray-50 dark:bg-gray-800 rounded border border-dashed border-gray-300 dark:border-gray-700">
              No emotional data logged yet.
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">Correlation between your emotions and PnL.</p>
        </div>
      );
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: { display: false },
    },
    scales: {
        y: {
            grid: { color: '#e5e7eb' }, // gray-200
            ticks: { color: '#6b7280' } // gray-500
        },
        x: {
            grid: { display: false },
            ticks: { color: '#6b7280' }
        }
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 h-full flex flex-col">
      <h3 className="text-base font-bold text-gray-900 dark:text-white mb-2">Trading Mood</h3>
      <div className="flex-grow min-h-[150px]">
        <Bar data={chartData} options={options} />
      </div>
      <p className="text-xs text-gray-500 mt-2 text-center">Correlation between your emotions and PnL.</p>
    </div>
  );
};

export default TradingMoodWidget;
