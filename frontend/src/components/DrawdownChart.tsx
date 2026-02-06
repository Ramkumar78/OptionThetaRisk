import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TimeScale
} from 'chart.js';
import type { ScriptableContext } from 'chart.js';
import { Line } from 'react-chartjs-2';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  TimeScale
);

interface DrawdownChartProps {
  data: { x: string; y: number }[];
  initialCapital?: number;
}

const DrawdownChart: React.FC<DrawdownChartProps> = ({ data, initialCapital = 10000 }) => {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return { datasets: [] };

    // Sort by date just in case
    const sorted = [...data].sort((a, b) => new Date(a.x).getTime() - new Date(b.x).getTime());

    // Calculate Drawdown
    let maxEquity = -Infinity;
    const drawdownPoints = sorted.map(d => {
        const equity = initialCapital + d.y;
        if (equity > maxEquity) maxEquity = equity;

        // Avoid division by zero
        const dd = maxEquity > 0 ? (equity - maxEquity) / maxEquity * 100 : 0;
        return { x: d.x, y: dd };
    });

    return {
      datasets: [
        {
          label: 'Drawdown %',
          data: drawdownPoints,
          borderColor: '#ef4444', // red-500
          backgroundColor: (context: ScriptableContext<"line">) => {
             const ctx = context.chart.ctx;
             const gradient = ctx.createLinearGradient(0, 0, 0, 200);
             gradient.addColorStop(0, 'rgba(239, 68, 68, 0.5)');
             gradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');
             return gradient;
          },
          fill: true,
          tension: 0.1,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
      ],
    };
  }, [data, initialCapital]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
            label: (context: any) => `Drawdown: ${context.parsed.y.toFixed(2)}%`
        }
      },
    },
    scales: {
      x: {
        type: 'time' as const,
        time: {
          tooltipFormat: 'MMM d, yyyy',
        },
        grid: {
          display: false,
        },
        ticks: {
            maxTicksLimit: 6
        }
      },
      y: {
        // Allow dynamic scaling but ensure 0 is max
        max: 0,
        ticks: {
          callback: (value: any) => `${value}%`,
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        }
      },
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false
    }
  };

  return (
    <div className="w-full h-full">
        <Line data={chartData} options={options} />
    </div>
  );
};

export default DrawdownChart;
