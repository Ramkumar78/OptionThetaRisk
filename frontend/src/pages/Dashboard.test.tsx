import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from './Dashboard';
import axios from 'axios';
import { BrowserRouter } from 'react-router-dom';

// Auto-mock axios
vi.mock('axios');

// Mock HealthScoreGauge
vi.mock('../components/ui/HealthScoreGauge', () => ({
  default: ({ score }: any) => <div data-testid="health-score-gauge">Gauge Score: {score}</div>
}));

// Mock Tooltip
vi.mock('../components/ui/Tooltip', () => ({
  default: ({ content, children }: any) => <div data-testid="tooltip" title={content}>{children}</div>
}));

// Mock CandlestickChart
vi.mock('../components/CandlestickChart', () => ({
  default: () => <div data-testid="candlestick-chart">Chart Loaded</div>
}));

// Mock RiskMapChart
vi.mock('../components/RiskMapChart', () => ({
  default: () => <div data-testid="risk-map-chart">Risk Map Loaded</div>
}));

// Mock AreaChart
vi.mock('../components/AreaChart', () => ({
  default: () => <div data-testid="area-chart">Equity Curve Loaded</div>
}));

// Mock DrawdownChart
vi.mock('../components/DrawdownChart', () => ({
  default: () => <div data-testid="drawdown-chart">Drawdown Chart Loaded</div>
}));

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Dashboard Component', () => {
  beforeEach(() => {
    vi.resetAllMocks();

    // Default fetch mock
    mockFetch.mockResolvedValue({
      json: async () => ({ error: 'No data' })
    });
  });

  it('renders loading state initially', async () => {
    let resolvePromise: any;
    (axios.get as any).mockImplementation((url: string) => {
        if (url === '/dashboard') {
             return new Promise((resolve) => { resolvePromise = resolve; });
        }
        return Promise.resolve({ data: [] });
    });

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
        discipline_score: 95,
        portfolio_curve: [{ x: '2023-01-01', y: 100 }]
    };

    (axios.get as any).mockImplementation((url: string) => {
        if (url === '/dashboard') return Promise.resolve({ data: mockData });
        if (url === '/journal') return Promise.resolve({ data: [] }); // Mock journal for widget
        return Promise.resolve({ data: {} });
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
        expect(screen.getByText('Net Liq')).toBeInTheDocument();
    }, { timeout: 3000 });

    expect(screen.getByText((content) => content.includes('123,456'))).toBeInTheDocument();

    // Check for new charts
    expect(screen.getByText('Performance Analysis')).toBeInTheDocument();
    expect(screen.getByTestId('area-chart')).toBeInTheDocument();
    expect(screen.getByTestId('drawdown-chart')).toBeInTheDocument();
  });

  it('renders market regime after fetch', async () => {
    const closeData = Array(200).fill({ close: 400 });
    const marketData = [...closeData, { close: 410 }]; // 410 > SMA(200 of 400) -> BULL

    mockFetch.mockResolvedValue({
        ok: true,
        json: async () => marketData
    });

    (axios.get as any).mockImplementation((url: string) => {
         if (url === '/journal') return Promise.resolve({ data: [] });
         return Promise.resolve({ data: {} });
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    // Wait for chart
    await screen.findByTestId('candlestick-chart', {}, { timeout: 3000 });

    // Wait for regime update by checking for text that appears only when regime is set
    // The component renders "Market is in [REGIME] regime" when not LOADING
    await screen.findByText(/Market is in/i, {}, { timeout: 3000 });

    // Now check that BULL is present
    const bullElements = screen.getAllByText(/BULL/i);
    expect(bullElements.length).toBeGreaterThan(0);
    expect(bullElements[0]).toBeInTheDocument();
  });

  it('shows no portfolio linked if no data', async () => {
    (axios.get as any).mockImplementation((url: string) => {
         if (url === '/journal') return Promise.resolve({ data: [] });
         return Promise.resolve({ data: null });
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await screen.findByText('No Portfolio Linked', {}, { timeout: 3000 });
  });

  it('switches asset when clicked', async () => {
    mockFetch.mockResolvedValueOnce({
        json: async () => ([{ close: 400 }])
    });

    (axios.get as any).mockImplementation((url: string) => {
        if (url === '/journal') return Promise.resolve({ data: [] });
        return Promise.resolve({ data: {} });
   });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    const spyBtn = screen.getByText('S&P 500');
    expect(spyBtn.className).toContain('bg-gray-900');

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
  });

  it('handles Nifty 50 selection correctly', async () => {
    mockFetch.mockResolvedValueOnce({
        json: async () => ([{ close: 18000 }])
    });

    (axios.get as any).mockImplementation((url: string) => {
        if (url === '/journal') return Promise.resolve({ data: [] });
        return Promise.resolve({ data: {} });
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
