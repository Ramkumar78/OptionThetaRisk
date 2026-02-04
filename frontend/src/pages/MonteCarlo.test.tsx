import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import MonteCarlo from './MonteCarlo';
import * as api from '../api';

// Mock Chart.js components to avoid canvas errors in JSDOM
vi.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="line-chart">Line Chart</div>
}));

// Mock the API
vi.mock('../api', () => ({
  runMonteCarloSimulation: vi.fn(),
}));

// Mock react-chartjs-2 to avoid canvas issues
vi.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="equity-curve-chart">Chart</div>,
}));

// Mock chart.js to avoid registration errors
vi.mock('chart.js', () => ({
  Chart: {
    register: vi.fn(),
  },
  CategoryScale: vi.fn(),
  LinearScale: vi.fn(),
  PointElement: vi.fn(),
  LineElement: vi.fn(),
  Title: vi.fn(),
  Tooltip: vi.fn(),
  Legend: vi.fn(),
}));

describe('MonteCarlo', () => {
  it('renders the form correctly', () => {
    render(<MonteCarlo />);
    expect(screen.getByText('Monte Carlo Sandbox')).toBeInTheDocument();
    expect(screen.getByLabelText('Ticker')).toBeInTheDocument();
    expect(screen.getByLabelText('Strategy')).toBeInTheDocument();
    expect(screen.getByLabelText('Simulations')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run Simulation' })).toBeInTheDocument();
  });

  it('handles API call success', async () => {
    const mockResult = {
      prob_ruin_50pct: 2.5,
      median_final_equity: 12000,
      initial_capital: 10000,
      avg_return_pct: 20,
      worst_case_return: -10,
      best_case_return: 50,
      median_drawdown: -15,
      worst_case_drawdown: -30,
      message: 'Ran 10000 simulations.',
      equity_curve_percentiles: {
        p5: [10000, 9900, 9800],
        p25: [10000, 9950, 9900],
        p50: [10000, 10000, 10100],
        p75: [10000, 10050, 10200],
        p95: [10000, 10100, 10300],
      },
      sample_equity_curves: [
        [10000, 10000, 10100],
        [10000, 9900, 9800]
      ]
      equity_curves: {
          p05: [10000, 9900, 9800],
          p25: [10000, 10000, 10000],
          p50: [10000, 10100, 10200],
          p75: [10000, 10200, 10400],
          p95: [10000, 10500, 11000]
      }
    };

    (api.runMonteCarloSimulation as any).mockResolvedValue(mockResult);

    render(<MonteCarlo />);

    const tickerInput = screen.getByLabelText('Ticker');
    fireEvent.change(tickerInput, { target: { value: 'AAPL' } });

    const runButton = screen.getByRole('button', { name: 'Run Simulation' });
    fireEvent.click(runButton);

    expect(screen.getByText('Simulating...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Risk of Ruin (>50% DD)')).toBeInTheDocument();
      expect(screen.getByText('2.5%')).toBeInTheDocument();
      expect(screen.getByText('$12,000')).toBeInTheDocument();
      expect(screen.getByText('20%')).toBeInTheDocument();

      const medianDrawdownLabels = screen.getAllByText('Median Drawdown');
      expect(medianDrawdownLabels.length).toBeGreaterThan(0);

      const medianDrawdownValues = screen.getAllByText('-15%');
      expect(medianDrawdownValues.length).toBeGreaterThan(0);

      // Verify chart is rendered
      expect(screen.getByTestId('equity-curve-chart')).toBeInTheDocument();
      // Verify Chart Section
      expect(screen.getByText('Projected Equity Curves (Cone)')).toBeInTheDocument();
      expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    });
  });

  it('handles API error', async () => {
    (api.runMonteCarloSimulation as any).mockResolvedValue({ error: 'Ticker not found' });

    render(<MonteCarlo />);

    const runButton = screen.getByRole('button', { name: 'Run Simulation' });
    fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.getByText('⚠️ Ticker not found')).toBeInTheDocument();
    });
  });
});
