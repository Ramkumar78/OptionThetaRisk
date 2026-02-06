import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Journal from './Journal';
import axios from 'axios';
import { BrowserRouter } from 'react-router-dom';
import React from 'react';

vi.mock('axios');

// Mock AreaChart
vi.mock('../components/AreaChart', () => ({
  default: (props: any) => <div data-testid="area-chart" data-props={JSON.stringify(props)}>Area Chart</div>
}));

// Mock Chart.js components (still needed if referenced, but AreaChart is main one)
vi.mock('react-chartjs-2', () => ({
  Line: (props: any) => <div data-testid="line-chart" data-props={JSON.stringify(props)}>Line Chart</div>
}));


describe('Journal Component', () => {
  const mockEntries = [
    {
      id: '1',
      created_at: 1696118400, // 2023-10-01
      symbol: 'SPY',
      strategy: 'Iron Condor',
      pnl: 100,
      sentiment: 'Bullish',
      notes: 'Good trade'
    },
    {
        id: '2',
        created_at: 1696204800, // 2023-10-02
        symbol: 'IWM',
        strategy: 'Put Credit Spread',
        pnl: -50,
        sentiment: 'Bearish',
        notes: 'Bad trade'
      }
  ];

  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders journal page and fetches entries', async () => {
    // Journal.tsx expects response.data to be the array of entries
    (axios.get as any).mockResolvedValue({ data: mockEntries });

    render(
      <BrowserRouter>
        <Journal />
      </BrowserRouter>
    );

    expect(screen.getByText(/New Journal Entry/i)).toBeInTheDocument();

    await waitFor(() => {
        expect(screen.getByText('SPY')).toBeInTheDocument();
        expect(screen.getByText('IWM')).toBeInTheDocument();
    });
  });

  it('shows empty state when no entries', async () => {
    (axios.get as any).mockResolvedValue({ data: [] });

    render(
      <BrowserRouter>
        <Journal />
      </BrowserRouter>
    );

    await waitFor(() => {
        expect(screen.getByText(/No journal entries yet/i)).toBeInTheDocument();
    });
  });

  it('submits a new entry', async () => {
    (axios.get as any).mockResolvedValue({ data: [] });
    (axios.post as any).mockResolvedValue({ data: { success: true } });

    render(
        <BrowserRouter>
          <Journal />
        </BrowserRouter>
      );

    // Fill form
    fireEvent.change(screen.getByLabelText(/Symbol/i), { target: { value: 'TSLA' } });
    fireEvent.change(screen.getByLabelText(/Strategy/i), { target: { value: 'Call' } });
    fireEvent.change(screen.getByLabelText(/Notes/i), { target: { value: 'Test Note' } });

    // Submit
    fireEvent.click(screen.getByText(/Add Entry/i));

    await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith('/journal/add', expect.objectContaining({
            symbol: 'TSLA',
            strategy: 'Call',
            notes: 'Test Note'
        }));
    });
  });

  it('analyzes journal and shows charts', async () => {
    (axios.get as any).mockResolvedValue({ data: mockEntries });

    const mockAnalysis = {
        total_trades: 2,
        win_rate: 50,
        total_pnl: 50,
        best_pattern: "Iron Condor",
        worst_pattern: "Put Credit Spread",
        best_time: "Morning",
        suggestions: ["Good job"],
        patterns: [],
        time_analysis: [],
        equity_curve: [
            { date: "2023-10-01", cumulative_pnl: 100 },
            { date: "2023-10-02", cumulative_pnl: 50 }
        ]
    };

    (axios.post as any).mockResolvedValue({ data: mockAnalysis });

    render(
        <BrowserRouter>
          <Journal />
        </BrowserRouter>
    );

    // Click Analyze
    fireEvent.click(screen.getByRole('button', { name: /Analyze Habits/i }));

    await waitFor(() => {
        // Check for stats
        expect(screen.getByText('50%')).toBeInTheDocument(); // Win rate

        // Check for chart
        expect(screen.getByText('Equity Curve (Cumulative PnL)')).toBeInTheDocument();
        const chart = screen.getByTestId('area-chart');
        expect(chart).toBeInTheDocument();

        // Check props passed to chart
        const props = JSON.parse(chart.getAttribute('data-props') || '{}');
        // AreaChart expects data in format { time: string, value: number }[]
        expect(props.data).toEqual([
            { time: "2023-10-01", value: 100 },
            { time: "2023-10-02", value: 50 }
        ]);
    });
  });

  it('does not render chart when equity curve is empty', async () => {
      (axios.get as any).mockResolvedValue({ data: mockEntries });

      const mockAnalysis = {
          total_trades: 2,
          win_rate: 50,
          total_pnl: 50,
          best_pattern: "Iron Condor",
          worst_pattern: "Put Credit Spread",
          best_time: "Morning",
          suggestions: ["Good job"],
          patterns: [],
          time_analysis: [],
          equity_curve: [] // Empty
      };

      (axios.post as any).mockResolvedValue({ data: mockAnalysis });

      render(
          <BrowserRouter>
            <Journal />
          </BrowserRouter>
      );

      // Click Analyze
      fireEvent.click(screen.getByRole('button', { name: /Analyze Habits/i }));

      await waitFor(() => {
          // Check for stats to ensure analysis loaded
          expect(screen.getByText('50%')).toBeInTheDocument();

          // Chart header and component should NOT be present
          expect(screen.queryByText('Equity Curve (Cumulative PnL)')).not.toBeInTheDocument();
          expect(screen.queryByTestId('area-chart')).not.toBeInTheDocument();
      });
  });
});
