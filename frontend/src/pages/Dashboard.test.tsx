import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from './Dashboard';
import axios from 'axios';
import { BrowserRouter } from 'react-router-dom';

// Mock axios
vi.mock('axios');

// Mock CandlestickChart
vi.mock('../components/CandlestickChart', () => ({
  default: () => <div data-testid="candlestick-chart">Chart Loaded</div>
}));

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Dashboard Component', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Default fetch mock (empty market data)
    mockFetch.mockResolvedValue({
      json: async () => ({ error: 'No data' })
    });
  });

  it('renders loading state initially', async () => {
    // Hang the axios request to check loading state
    let resolvePromise: any;
    (axios.get as any).mockImplementation(() => new Promise((resolve) => {
        resolvePromise = resolve;
    }));

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    // Check for Dashboard Title
    expect(screen.getByText(/COMMAND/i)).toBeInTheDocument();

    // Check for "Loading Market Data..." or similar if initial state
    expect(screen.getByText('Loading Market Data...')).toBeInTheDocument();

    // Check for Portfolio Loading Skeleton (pulse div exists, but checking absence of data is easier)
    expect(screen.queryByText('Net Liquidity')).not.toBeInTheDocument();

    // Cleanup to avoid open handles
    if (resolvePromise) resolvePromise({ data: {} });
  });

  it('renders portfolio results after data fetch', async () => {
    // Mock Portfolio Data
    (axios.get as any).mockResolvedValue({
        data: {
            net_liquidity_now: 123456,
            ytd_return_pct: 15.5,
            portfolio_beta_delta: 50.2
        }
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
        expect(screen.getByText('Net Liquidity')).toBeInTheDocument();
    });

    // Check formatted values (using regex to be locale-safe or partial match)
    expect(screen.getByText((content) => content.includes('123,456'))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes('+15.50%'))).toBeInTheDocument();
    expect(screen.getByText('50.20')).toBeInTheDocument();
  });

  it('renders market regime after fetch', async () => {
    // Mock Market Data
    // We need enough data points. 200 items.
    const closeData = Array(200).fill({ close: 400 });
    // Add one more that is higher (410)
    // Code calculates SMA200 of last 200 items?
    // "const closes = data.map((d: any) => d.close);"
    // "const sum = closes.slice(-period).reduce((a: number, b: number) => a + b, 0);"
    // period = 200.
    // If I return 201 items: 200 items of 400, then 410.
    // slice(-200) will take one 400 out and include 410?
    // No, slice(-200) takes the last 200.
    // So if list is [x1...x200, 410]. slice(-200) is [x2...x200, 410].
    // SMA will be slightly higher than 400.
    // Last close is 410.
    // 410 > 400.something -> BULL.

    const marketData = [...closeData, { close: 410 }];

    mockFetch.mockResolvedValue({
      json: async () => marketData
    });

    (axios.get as any).mockResolvedValue({ data: {} });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    // Wait for chart
    await waitFor(() => {
        expect(screen.getByTestId('candlestick-chart')).toBeInTheDocument();
    });

    // Check for BULL regime
    await waitFor(() => {
         expect(screen.getByText('BULL')).toBeInTheDocument();
    });
  });

  it('shows no portfolio linked if no data', async () => {
    // Mock error/empty
    (axios.get as any).mockResolvedValue({
        data: null
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
        expect(screen.getByText('No Portfolio Linked')).toBeInTheDocument();
    });
  });
});
