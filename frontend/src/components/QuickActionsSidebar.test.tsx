import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import QuickActionsSidebar from './QuickActionsSidebar';
import axios from 'axios';

// Mock axios
vi.mock('axios');

// Mock window.alert
window.alert = vi.fn();

describe('QuickActionsSidebar', () => {
  it('is initially closed', () => {
    render(<QuickActionsSidebar />);
    expect(screen.getByLabelText('Quick Trade')).toBeInTheDocument();
  });

  it('opens when toggle button is clicked', async () => {
    render(<QuickActionsSidebar />);
    const toggle = screen.getByLabelText('Quick Trade');
    fireEvent.click(toggle);

    expect(screen.getByText('Quick Trade Entry')).toBeInTheDocument();
  });

  it('submits form correctly', async () => {
    (axios.post as any).mockResolvedValue({ data: { success: true } });
    render(<QuickActionsSidebar />);

    // Open it
    fireEvent.click(screen.getByLabelText('Quick Trade'));

    // Fill form
    const symbolInput = screen.getByPlaceholderText('e.g. SPY');
    fireEvent.change(symbolInput, { target: { value: 'AAPL' } });

    const submitBtn = screen.getByText('Log Trade');
    fireEvent.click(submitBtn);

    await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith('/journal/add', expect.objectContaining({
            symbol: 'AAPL',
            sentiment: 'Neutral'
        }));
    });
  });
});
