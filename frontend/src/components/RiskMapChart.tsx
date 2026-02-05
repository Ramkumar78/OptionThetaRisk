import React from 'react';
import {
  Chart as ChartJS,
  LinearScale,
  PointElement,
  Tooltip,
  Legend,
  Title
} from 'chart.js';
import { Bubble } from 'react-chartjs-2';

ChartJS.register(LinearScale, PointElement, Tooltip, Legend, Title);

interface RiskMapProps {
  data: Array<{
    symbol: string;
    dte: number;
    pnl_pct: number;
    size: number;
    risk_alert?: string;
  }>;
}

const RiskMapChart: React.FC<RiskMapProps> = ({ data }) => {
  if (!data || data.length === 0) {
      return <div className="text-gray-400 text-sm text-center py-10">No Open Positions to Map</div>;
  }

  const chartData = {
    datasets: [
      {
        label: 'Open Positions',
        data: data.map(d => ({
          x: d.dte,
          y: d.pnl_pct,
          r: Math.max(5, Math.min(25, Math.sqrt(d.size) / 5)) // Scale radius based on sqrt of size for area
        })),
        backgroundColor: data.map(d => {
             // Red if losing, Green if winning.
             // Logic: PnL < 0 => Red.
             return d.pnl_pct >= 0 ? 'rgba(34, 197, 94, 0.6)' : 'rgba(239, 68, 68, 0.6)';
        }),
        borderColor: data.map(d => d.pnl_pct >= 0 ? 'rgba(34, 197, 94, 1)' : 'rgba(239, 68, 68, 1)'),
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        title: { display: true, text: 'Days to Expiration (DTE)' },
        // User wants "Red square on the left" meaning expiring soon.
        // Standard X axis 0 is left. So this works.
        min: 0,
      },
      y: {
        title: { display: true, text: 'Est. PnL %' },
        grid: {
            color: (context: any) => context.tick.value === 0 ? 'rgba(107, 114, 128, 0.5)' : 'rgba(229, 231, 235, 0.5)',
            lineWidth: (context: any) => context.tick.value === 0 ? 2 : 1,
        }
      }
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (context: any) => {
             const d = data[context.dataIndex];
             return `${d.symbol}: DTE ${d.dte}, PnL ${d.pnl_pct}% ${d.risk_alert ? '⚠️ ' + d.risk_alert : ''}`;
          }
        }
      },
      legend: { display: false }
    }
  };

  return <Bubble options={options as any} data={chartData} />;
};

export default RiskMapChart;
