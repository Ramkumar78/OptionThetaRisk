import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import TradingMoodWidget from './TradingMoodWidget';
import axios from 'axios';

// Mock axios
vi.mock('axios');

// Mock Chart.js
vi.mock('react-chartjs-2', () => ({
  Bar: ({ data }: any) => (
    <div data-testid="bar-chart">
      {JSON.stringify(data)}
    </div>
  ),
}));

describe('TradingMoodWidget', () => {
  it('renders loading state initially', () => {
    (axios.get as any).mockImplementation(() => new Promise(() => {})); // Never resolves
    render(<TradingMoodWidget />);
    expect(screen.getByText('Loading Mood Data...')).toBeInTheDocument();
  });

  it('renders chart with data', async () => {
    const mockData = [
      { id: '1', pnl: 100, emotions: ['Disciplined'] },
      { id: '2', pnl: -50, emotions: ['Impulsive'] },
      { id: '3', pnl: 200, emotions: ['Disciplined'] },
    ];
    (axios.get as any).mockResolvedValue({ data: mockData });

    render(<TradingMoodWidget />);

    await waitFor(() => {
        expect(screen.getByText('Trading Mood')).toBeInTheDocument();
    });

    const chart = screen.getByTestId('bar-chart');
    expect(chart).toBeInTheDocument();
    // Disciplined avg: (100 + 200) / 2 = 150
    // Impulsive avg: -50
    expect(chart.textContent).toContain('Disciplined');
    expect(chart.textContent).toContain('Impulsive');
  });

  it('renders empty state if no data', async () => {
    (axios.get as any).mockResolvedValue({ data: [] });
    render(<TradingMoodWidget />);
    await waitFor(() => {
        expect(screen.getByText('No emotional data logged yet.')).toBeInTheDocument();
    });
  });
});
