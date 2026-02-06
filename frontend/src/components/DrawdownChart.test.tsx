import { render, screen } from '@testing-library/react';
import { describe, it, vi, expect } from 'vitest';
import DrawdownChart from './DrawdownChart';

// Mock chart.js to avoid canvas errors
vi.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="line-chart">Line Chart</div>
}));

describe('DrawdownChart', () => {
  it('renders without crashing', () => {
    const data = [{ x: '2023-01-01', y: 100 }];
    render(<DrawdownChart data={data} />);
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('handles empty data gracefully', () => {
      render(<DrawdownChart data={[]} />);
      // Should still render (maybe empty chart or just the mock)
      // The component returns a Line chart even with empty data (datasets: [])
      expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });
});
