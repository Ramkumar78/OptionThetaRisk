import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Screener from './Screener';
import { BrowserRouter } from 'react-router-dom';

vi.mock('axios');

// Mock api.ts imports
vi.mock('../api', () => ({
    runMarketScreener: vi.fn(),
    runTurtleScreener: vi.fn(),
    runEmaScreener: vi.fn(),
    runDarvasScreener: vi.fn(),
}));

import { runTurtleScreener } from '../api';

describe('Screener Component', () => {
  const mockData = [
    {
      Ticker: 'AAPL',
      'Price': 150.0,
      'IV Rank': 20,
      'RSI': 45,
      'Change': 1.5,
      'Vol/OI': 1.2
    },
    {
      Ticker: 'TSLA',
      'Price': 250.0,
      'IV Rank': 50,
      'RSI': 70,
      'Change': -2.0,
      'Vol/OI': 2.0
    }
  ];

  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders screener options', () => {
    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );
    // Be specific about which button or heading we expect
    expect(screen.getAllByText(/Market Screener/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Turtle Trading/i).length).toBeGreaterThan(0);
  });

  it('fetches and displays data when Run Screener is clicked', async () => {
    // Setup the mock for the default selected tab (Turtle)
    (runTurtleScreener as any).mockResolvedValue(mockData);

    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    const runBtn = screen.getByRole('button', { name: /Run Screener/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
        expect(runTurtleScreener).toHaveBeenCalled();
    });

    // Check if table renders
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('TSLA')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    (runTurtleScreener as any).mockRejectedValue(new Error('Network Error'));

    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    const runBtn = screen.getByRole('button', { name: /Run Screener/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText(/Network Error/i)).toBeInTheDocument();
    });
  });
});
