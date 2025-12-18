import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Screener from './Screener';
import { BrowserRouter } from 'react-router-dom';

vi.mock('axios');

// Mock api.ts imports
vi.mock('../api');

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
    // Mock window.scrollTo
    window.scrollTo = vi.fn();
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

  it.skip('fetches and displays data when Run Screener is clicked', async () => {
    // Setup the mock for the default selected tab (Turtle)
    (runTurtleScreener as any).mockResolvedValue(mockData);
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    // There are now two "Run Screener" buttons (Desktop and Mobile)
    const runBtns = screen.getAllByRole('button', { name: /Run Screener/i });
    await user.click(runBtns[0]); // Click the first available one

    try {
      await waitFor(() => {
        expect(runTurtleScreener).toHaveBeenCalled();
        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.getByText('TSLA')).toBeInTheDocument();
      }, { timeout: 3000 });
    } catch (e) {
      console.error('DOM State on Failure:', screen.debug());
      throw e;
    }
  });

  it('handles API errors gracefully', async () => {
    (runTurtleScreener as any).mockRejectedValue(new Error('Network Error'));

    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    const runBtns = screen.getAllByRole('button', { name: /Run Screener/i });
    fireEvent.click(runBtns[0]);

    await waitFor(() => {
      expect(screen.getByText(/Network Error/i)).toBeInTheDocument();
    });
  });

  it('sorts Safety % column numerically', async () => {
    // Mock fetch for fortress screener
    const fortressData = [
      {
        ticker: 'A', // 10%
        k_factor: 2.4,
        sell_strike: 100,
        buy_strike: 90,
        cushion: '10.0%',
        manage_by: '2025-01-01'
      },
      {
        ticker: 'B', // 2%
        k_factor: 2.4,
        sell_strike: 50,
        buy_strike: 45,
        cushion: '2.0%',
        manage_by: '2025-01-01'
      },
      {
        ticker: 'C', // 1.7%
        k_factor: 2.4,
        sell_strike: 200,
        buy_strike: 190,
        cushion: '1.7%',
        manage_by: '2025-01-01'
      }
    ];

    // Use vi.stubGlobal instead of assigning to global.fetch directly
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      json: () => Promise.resolve(fortressData)
    }));

    try {
      render(
        <BrowserRouter>
          <Screener />
        </BrowserRouter>
      );

      // Switch to Fortress tab
      const fortressTab = screen.getByText('Options: Bull Put');
      fireEvent.click(fortressTab);

      // Run Screener - handle multiple buttons
      const runBtns = screen.getAllByRole('button', { name: /Run Screener/i });
      fireEvent.click(runBtns[0]);

      await waitFor(() => {
        expect(screen.getByText('10.0%')).toBeInTheDocument();
      });

      // Click sorting header for Safety % (cushion)
      const sortHeader = screen.getByText('Safety %');
      fireEvent.click(sortHeader); // Ascending

      const cells = document.querySelectorAll('tbody tr td:nth-child(6)');
      expect(cells.length).toBe(3);

      expect(cells[0].textContent).toBe('1.7%');
      expect(cells[1].textContent).toBe('2.0%');
      expect(cells[2].textContent).toBe('10.0%');

    } finally {
      vi.unstubAllGlobals();
    }
  });
});
