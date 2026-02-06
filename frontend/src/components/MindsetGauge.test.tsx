import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MindsetGauge from './MindsetGauge';
import React from 'react';

// Mock chart.js registration
vi.mock('chart.js', () => ({
  Chart: {
    register: vi.fn(),
  },
  ArcElement: {},
  Tooltip: {},
  Legend: {},
}));

// Mock react-chartjs-2
vi.mock('react-chartjs-2', () => ({
  Doughnut: ({ data, options }: any) => {
    return (
      <div data-testid="doughnut-chart" data-props={JSON.stringify({ data, options })}>
        Doughnut Chart
      </div>
    );
  },
}));

describe('MindsetGauge', () => {
  it('renders the score correctly', () => {
    render(<MindsetGauge score={85} />);
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('/ 100')).toBeInTheDocument();
  });

  it('passes correct data to Doughnut chart', () => {
    render(<MindsetGauge score={75} />);
    const chart = screen.getByTestId('doughnut-chart');
    const props = JSON.parse(chart.getAttribute('data-props') || '{}');

    expect(props.data.datasets[0].data).toEqual([75, 25]);
  });

  it('uses green color for score >= 90', () => {
    render(<MindsetGauge score={95} />);
    const chart = screen.getByTestId('doughnut-chart');
    const props = JSON.parse(chart.getAttribute('data-props') || '{}');

    // Green: #16a34a
    expect(props.data.datasets[0].backgroundColor[0]).toBe('#16a34a');

    // Text color check
    const scoreText = screen.getByText('95');
    // HEX to RGB conversion might happen in computed style, but let's check exact HEX first or rely on implementation detail
    // If JSDOM handles color styles, it might convert to rgb()
    // #16a34a is rgb(22, 163, 74)
    expect(scoreText).toHaveStyle({ color: '#16a34a' });
  });

  it('uses yellow color for score >= 70 and < 90', () => {
    render(<MindsetGauge score={80} />);
    const chart = screen.getByTestId('doughnut-chart');
    const props = JSON.parse(chart.getAttribute('data-props') || '{}');

    // Yellow: #ca8a04
    expect(props.data.datasets[0].backgroundColor[0]).toBe('#ca8a04');

    const scoreText = screen.getByText('80');
    expect(scoreText).toHaveStyle({ color: '#ca8a04' });
  });

  it('uses red color for score < 70', () => {
    render(<MindsetGauge score={50} />);
    const chart = screen.getByTestId('doughnut-chart');
    const props = JSON.parse(chart.getAttribute('data-props') || '{}');

    // Red: #dc2626
    expect(props.data.datasets[0].backgroundColor[0]).toBe('#dc2626');

    const scoreText = screen.getByText('50');
    expect(scoreText).toHaveStyle({ color: '#dc2626' });
  });
});
