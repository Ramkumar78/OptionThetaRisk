import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Journal from './Journal';
import axios from 'axios';
import { BrowserRouter } from 'react-router-dom';

vi.mock('axios');

describe('Journal Component', () => {
  const mockEntries = [
    {
      id: '1',
      created_at: 1696118400, // 2023-10-01
      symbol: 'SPY',
      strategy: 'Iron Condor',
      pnl: 100,
      sentiment: 'Bullish',
      notes: 'Good trade'
    },
    {
        id: '2',
        created_at: 1696204800, // 2023-10-02
        symbol: 'IWM',
        strategy: 'Put Credit Spread',
        pnl: -50,
        sentiment: 'Bearish',
        notes: 'Bad trade'
      }
  ];

  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders journal page and fetches entries', async () => {
    // Journal.tsx expects response.data to be the array of entries
    (axios.get as any).mockResolvedValue({ data: mockEntries });

    render(
      <BrowserRouter>
        <Journal />
      </BrowserRouter>
    );

    expect(screen.getByText(/New Journal Entry/i)).toBeInTheDocument();

    await waitFor(() => {
        expect(screen.getByText('SPY')).toBeInTheDocument();
        expect(screen.getByText('IWM')).toBeInTheDocument();
    });
  });

  it('shows empty state when no entries', async () => {
    (axios.get as any).mockResolvedValue({ data: [] });

    render(
      <BrowserRouter>
        <Journal />
      </BrowserRouter>
    );

    await waitFor(() => {
        expect(screen.getByText(/No journal entries yet/i)).toBeInTheDocument();
    });
  });

  it('submits a new entry', async () => {
    (axios.get as any).mockResolvedValue({ data: [] });
    (axios.post as any).mockResolvedValue({ data: { success: true } });

    render(
        <BrowserRouter>
          <Journal />
        </BrowserRouter>
      );

    // Fill form
    fireEvent.change(screen.getByLabelText(/Symbol/i), { target: { value: 'TSLA' } });
    fireEvent.change(screen.getByLabelText(/Strategy/i), { target: { value: 'Call' } });
    fireEvent.change(screen.getByLabelText(/Notes/i), { target: { value: 'Test Note' } });

    // Submit
    fireEvent.click(screen.getByText(/Add Entry/i));

    await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith('/journal/add', expect.objectContaining({
            symbol: 'TSLA',
            strategy: 'Call',
            notes: 'Test Note'
        }));
    });
  });
});
