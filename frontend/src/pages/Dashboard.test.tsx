import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from './Dashboard';
import axios from 'axios';
import { BrowserRouter } from 'react-router-dom';

vi.mock('axios');

// Mock Results component safely
vi.mock('./Results', () => ({
    default: ({ directData }: { directData: any }) => {
        if (!directData) return <div>No Data in Results</div>;
        return <div>Results Loaded: {directData.total_pnl}</div>;
    }
}));

describe('Dashboard Component', () => {
  beforeEach(() => {
    vi.resetAllMocks();
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

    expect(screen.queryByText(/Results Loaded/i)).not.toBeInTheDocument();

    // Resolve to clean up
    if (resolvePromise) resolvePromise({ data: {} });
  });

  it('renders results after data fetch', async () => {
    (axios.get as any).mockResolvedValue({
        data: {
            total_pnl: 5000
        }
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
        expect(screen.getByText('Results Loaded: 5000')).toBeInTheDocument();
    });
  });

  it('redirects or shows error if no data', async () => {

    (axios.get as any).mockResolvedValue({
        data: {
            error: 'Some Generic Error'
        }
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
        expect(screen.getByText('Some Generic Error')).toBeInTheDocument();
    });
  });
});
