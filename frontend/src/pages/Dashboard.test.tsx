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

// Mock RiskMapChart
vi.mock('../components/RiskMapChart', () => ({
  default: () => <div data-testid="risk-map-chart">Risk Map Loaded</div>
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
    let resolvePromise: any;
    (axios.get as any).mockImplementation(() => new Promise((resolve) => {
        resolvePromise = resolve;
    }));

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    expect(screen.getByText(/Command Center/i)).toBeInTheDocument();
    expect(screen.getByText('Loading Market Data...')).toBeInTheDocument();

    // Cleanup
    if (resolvePromise) resolvePromise({ data: {} });
  });

  it('renders portfolio results after data fetch', async () => {
    const mockData = {
        net_liquidity_now: 123456,
        ytd_return_pct: 15.5,
        portfolio_beta_delta: 50.2,
        discipline_score: 95
    };

    (axios.get as any).mockResolvedValue({ data: mockData });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    // Wait for loading to finish and data to appear
    await waitFor(() => {
        expect(screen.getByText('Net Liq')).toBeInTheDocument();
    }, { timeout: 2000 });

    expect(screen.getByText((content) => content.includes('123,456'))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes('15.50%'))).toBeInTheDocument();
    expect(screen.getByText('50.20')).toBeInTheDocument();
    expect(screen.getByText('95')).toBeInTheDocument();
  });

  it('renders market regime after fetch', async () => {
    const closeData = Array(200).fill({ close: 400 });
    const marketData = [...closeData, { close: 410 }]; // 410 > SMA(200 of 400) -> BULL

    mockFetch.mockResolvedValue({
      json: async () => marketData
    });

    (axios.get as any).mockResolvedValue({ data: {} }); // Resolve portfolio to avoid "No Portfolio Linked" distraction

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
        expect(screen.getByTestId('candlestick-chart')).toBeInTheDocument();
    }, { timeout: 2000 });

    // Debug help: print text content if fails
    await waitFor(() => {
         expect(screen.getByText('BULL')).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('shows no portfolio linked if no data', async () => {
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

  it('switches asset when clicked', async () => {
    mockFetch.mockResolvedValueOnce({
        json: async () => ([{ close: 400 }])
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    const spyBtn = screen.getByText('S&P 500');
    expect(spyBtn.className).toContain('bg-gray-900'); // Selected style

    const goldBtn = screen.getByText('Gold');

    mockFetch.mockResolvedValueOnce({
        json: async () => ([{ close: 2000 }])
    });

    act(() => {
        goldBtn.click();
    });

    await waitFor(() => {
        expect(goldBtn.className).toContain('bg-gray-900');
    });

    expect(spyBtn.className).not.toContain('bg-gray-900');

    await waitFor(() => {
        expect(mockFetch).toHaveBeenLastCalledWith('/analyze/market-data', expect.objectContaining({
            body: expect.stringContaining('GC=F')
        }));
    });
  });

  it('handles Nifty 50 selection correctly', async () => {
    mockFetch.mockResolvedValueOnce({
        json: async () => ([{ close: 18000 }])
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    const niftyBtn = screen.getByText('Nifty 50');

    mockFetch.mockResolvedValueOnce({
        json: async () => ([{ close: 18500 }])
    });

    act(() => {
        niftyBtn.click();
    });

    await waitFor(() => {
        expect(mockFetch).toHaveBeenLastCalledWith('/analyze/market-data', expect.objectContaining({
            body: expect.stringContaining('^NSEI')
        }));
    });
  });
});
