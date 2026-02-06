import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import HealthScoreGauge from './HealthScoreGauge';
import React from 'react';

// Mock react-chartjs-2
vi.mock('react-chartjs-2', () => ({
  Doughnut: ({ data }: any) => {
    return <div data-testid="mock-doughnut" data-chart-data={JSON.stringify(data)}></div>;
  },
}));

// Mock chart.js registration
vi.mock('chart.js', () => ({
  Chart: { register: vi.fn() },
  ArcElement: 'ArcElement',
  Tooltip: 'Tooltip',
  Legend: 'Legend',
}));

describe('HealthScoreGauge', () => {
  it('renders correctly with high score (Green)', () => {
    render(<HealthScoreGauge score={95} />);

    // Check score text
    const scoreText = screen.getByText('95');
    expect(scoreText).toBeInTheDocument();

    // Check color (green-600 is #16a34a)
    // Note: style prop in React usually applies as inline style, so we can check it.
    // hex colors might be normalized to rgb, let's verify.
    // #16a34a is rgb(22, 163, 74)
    expect(scoreText).toHaveStyle({ color: '#16a34a' });

    // Check chart data color
    const chart = screen.getByTestId('mock-doughnut');
    const data = JSON.parse(chart.getAttribute('data-chart-data') || '{}');
    expect(data.datasets[0].backgroundColor[0]).toBe('#16a34a');
  });

  it('renders correctly with medium score (Yellow)', () => {
    render(<HealthScoreGauge score={75} />);

    const scoreText = screen.getByText('75');
    // #ca8a04 is rgb(202, 138, 4)
    expect(scoreText).toHaveStyle({ color: '#ca8a04' });

    const chart = screen.getByTestId('mock-doughnut');
    const data = JSON.parse(chart.getAttribute('data-chart-data') || '{}');
    expect(data.datasets[0].backgroundColor[0]).toBe('#ca8a04');
  });

  it('renders correctly with low score (Red)', () => {
    render(<HealthScoreGauge score={50} />);

    const scoreText = screen.getByText('50');
    // #dc2626 is rgb(220, 38, 38)
    expect(scoreText).toHaveStyle({ color: '#dc2626' });

    const chart = screen.getByTestId('mock-doughnut');
    const data = JSON.parse(chart.getAttribute('data-chart-data') || '{}');
    expect(data.datasets[0].backgroundColor[0]).toBe('#dc2626');
  });
});
