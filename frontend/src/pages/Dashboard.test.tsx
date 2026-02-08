import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from './Dashboard';
import axios from 'axios';
import { BrowserRouter } from 'react-router-dom';

// Auto-mock axios
vi.mock('axios');

// Mock Recharts
vi.mock('recharts', () => {
  return {
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 800, height: 800 }}>{children}</div>,
    AreaChart: () => <div>AreaChart</div>,
    Area: () => <div>Area</div>,
    XAxis: () => <div>XAxis</div>,
    YAxis: () => <div>YAxis</div>,
    CartesianGrid: () => <div>CartesianGrid</div>,
    Tooltip: () => <div>Tooltip</div>,
    Brush: () => <div>Brush</div>,
  };
});

// Mock RiskMapChart
vi.mock('../components/RiskMapChart', () => ({
  default: () => <div data-testid="risk-map-chart">Risk Map Loaded</div>
}));

describe('Dashboard Component', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders loading state initially', async () => {
    // Keep promise pending to test loading state
    (axios.get as any).mockImplementation(() => new Promise(() => {}));

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    expect(screen.getByText('Loading Market Data...')).toBeInTheDocument();
  });

  it('renders portfolio results after data fetch', async () => {
    const mockData = {
        net_liquidity_now: 123456,
        buying_power_utilized_percent: 50,
        strategy_metrics: {
            total_pnl: 5000,
            win_rate: 0.65,
            max_drawdown: 1000,
            num_trades: 20
        },
        portfolio_curve: [{ x: '2023-01-01', y: 100 }],
        strategy_groups: [
            { gross_pnl: 200, pnl: 190 },
            { gross_pnl: -100, pnl: -100 }
        ],
        verdict: "Green Flag",
        verdict_color: "green",
        risk_map: []
    };

    (axios.get as any).mockResolvedValue({ data: mockData });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
        expect(screen.getByText('Market Dashboard')).toBeInTheDocument();
    });

    // Check Net Liq
    expect(screen.getByText('$123,456')).toBeInTheDocument();

    // Check PnL
    expect(screen.getByText('$5,000')).toBeInTheDocument();

    // Check Win Rate
    expect(screen.getByText('65.0%')).toBeInTheDocument();

    // Check Risk Map
    expect(screen.getByTestId('risk-map-chart')).toBeInTheDocument();
  });

  it('renders no data state correctly', async () => {
    (axios.get as any).mockResolvedValue({ data: null });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
         expect(screen.getByText('No Data Available')).toBeInTheDocument();
    });
  });
});
