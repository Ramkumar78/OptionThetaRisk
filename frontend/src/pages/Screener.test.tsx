import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Screener from './Screener';
import { BrowserRouter } from 'react-router-dom';

// Mock dependencies
vi.mock('axios');
vi.mock('../api');

describe('Screener Component', () => {
  const mockData = {
    results: [
      {
        Ticker: 'AAPL',
        Price: 150.0,
        Change: 1.5,
        Setup: 'PERFECT BUY',
        Action: 'BUY',
        Score: 3,
        RS_Rating: 85
      },
      {
        Ticker: 'TSLA',
        Price: 250.0,
        Change: -2.0,
        Setup: 'WAIT',
        Action: '-',
        Score: 1,
        RS_Rating: 40
      }
    ],
    regime: 'BULLISH'
  };

  beforeEach(() => {
    vi.resetAllMocks();
    global.fetch = vi.fn();
  });

  it('renders screener options', () => {
    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    expect(screen.getAllByText(/MARKET/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/SCREENER/i)[0]).toBeInTheDocument();

    // Check if strategy selector is present
    const strategySelect = screen.getByRole('combobox', { name: /strategy/i });
    expect(strategySelect).toBeInTheDocument();
    expect(strategySelect).toHaveValue('grandmaster');
  });

  it('fetches and displays data when Run Scanner is clicked', async () => {
    global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve(mockData)
    });

    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    const runBtn = screen.getByRole('button', { name: /RUN SCANNER/i });
    await user.click(runBtn);

    await waitFor(() => {
      // Check for API call
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/screen/master'));

      // Check for results
      expect(screen.getByText('AAPL')).toBeInTheDocument();
      expect(screen.getByText('TSLA')).toBeInTheDocument();

      // Check for price formatting (with $ default)
      expect(screen.getByText('$150.00')).toBeInTheDocument();

      // Check for Regime
      expect(screen.getByText('BULLISH')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
     global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve({ error: 'Backend Error' })
     });

    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    const runBtn = screen.getByRole('button', { name: /RUN SCANNER/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText(/Backend Error/i)).toBeInTheDocument();
    });
  });

  it('updates strategy description when changed', async () => {
    const user = userEvent.setup();
    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    const strategySelect = screen.getByRole('combobox', { name: /strategy/i });

    // Change to Turtle
    await user.selectOptions(strategySelect, 'turtle');

    expect(screen.getByText(/Classic trend following strategy/i)).toBeInTheDocument();

    // Change back to Grandmaster
    await user.selectOptions(strategySelect, 'grandmaster');
    expect(screen.getByText(/The Fortress Protocol/i)).toBeInTheDocument();
  });
});
