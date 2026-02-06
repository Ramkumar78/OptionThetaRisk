import React from 'react';
import { Chart as ChartJS, ArcElement, Tooltip as ChartTooltip, Legend } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(ArcElement, ChartTooltip, Legend);

interface HealthScoreGaugeProps {
  score: number;
}

const HealthScoreGauge: React.FC<HealthScoreGaugeProps> = ({ score }) => {
  const getColor = (s: number) => {
    if (s >= 90) return '#16a34a'; // green-600
    if (s >= 70) return '#ca8a04'; // yellow-600
    return '#dc2626'; // red-600
  };

  const color = getColor(score);

  const data = {
    datasets: [
      {
        data: [score, 100 - score],
        backgroundColor: [color, '#e5e7eb'], // gray-200
        borderWidth: 0,
        circumference: 180,
        rotation: -90,
      },
    ],
  };

  const options = {
    cutout: '75%',
    plugins: {
      tooltip: { enabled: false },
      legend: { display: false },
    },
    maintainAspectRatio: false,
    responsive: true,
  };

  return (
    <div className="relative w-full h-32 flex justify-center items-end" data-testid="health-score-gauge">
        <div className="w-48 h-full">
            <Doughnut data={data} options={options} />
        </div>
        <div className="absolute bottom-0 flex flex-col items-center mb-4">
             <span className="text-4xl font-bold" style={{ color }}>{score}</span>
             <span className="text-xs text-gray-400">/ 100</span>
        </div>
    </div>
  );
};

export default HealthScoreGauge;
