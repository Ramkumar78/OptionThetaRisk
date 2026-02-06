import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { TradingMoodWidget } from './TradingMoodWidget';
import axios from 'axios';
import React from 'react';

// Mock axios
vi.mock('axios');

// Mock react-chartjs-2
vi.mock('react-chartjs-2', () => ({
  Bar: () => React.createElement('div', { 'data-testid': 'bar-chart' }, 'Bar Chart'),
}));

describe('TradingMoodWidget', () => {
  it('renders loading state initially', () => {
    // Mock axios to return a promise that never resolves (or resolves later)
    (axios.get as any).mockImplementation(() => new Promise(() => {}));
    render(<TradingMoodWidget />);
    // Check for loading skeleton (animate-pulse) or container
    const container = document.querySelector('.animate-pulse');
    expect(container).toBeInTheDocument();
  });

  it('renders "No mood data" when entries are empty', async () => {
    (axios.get as any).mockResolvedValue({ data: [] });
    render(<TradingMoodWidget />);

    await waitFor(() => {
        expect(screen.getByText('No mood data available.')).toBeInTheDocument();
    });
  });

  it('renders chart when data is present', async () => {
    const mockData = [
      { id: '1', emotions: ['Disciplined'], pnl: 100 },
      { id: '2', emotions: ['Impulsive'], pnl: -50 },
      { id: '3', emotions: ['Disciplined'], pnl: 50 }, // Total Disciplined: 150
    ];
    (axios.get as any).mockResolvedValue({ data: mockData });

    render(<TradingMoodWidget />);

    await waitFor(() => {
        expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
        expect(screen.getByText('Trading Mood Analysis')).toBeInTheDocument();
    });
  });
});
