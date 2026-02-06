import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PositionSizer from './PositionSizer';
import { describe, it, expect } from 'vitest';

describe('PositionSizer', () => {
  it('renders correctly with default values', () => {
    render(<PositionSizer />);

    expect(screen.getByLabelText(/Account Size/i)).toHaveValue(10000);
    expect(screen.getByLabelText(/Risk Per Trade/i)).toHaveValue(1);
    expect(screen.getByText(/Max Shares to Buy/i)).toBeInTheDocument();
  });

  it('calculates max shares correctly', () => {
    render(<PositionSizer />);

    const stopLossInput = screen.getByLabelText(/Stop Loss Amount/i);
    fireEvent.change(stopLossInput, { target: { value: '2' } });

    // Formula: (10000 * 0.01) / 2 = 100 / 2 = 50
    expect(screen.getByText('50')).toBeInTheDocument();
  });

  it('updates calculation when inputs change', () => {
    render(<PositionSizer />);

    const accountInput = screen.getByLabelText(/Account Size/i);
    const riskInput = screen.getByLabelText(/Risk Per Trade/i);
    const stopLossInput = screen.getByLabelText(/Stop Loss Amount/i);

    fireEvent.change(accountInput, { target: { value: '20000' } });
    fireEvent.change(riskInput, { target: { value: '2' } });
    fireEvent.change(stopLossInput, { target: { value: '4' } });

    // Formula: (20000 * 0.02) / 4 = 400 / 4 = 100
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('shows concentration risk warning when position size exceeds 20%', () => {
    render(<PositionSizer />);

    // Setup: 50 shares calculated
    const stopLossInput = screen.getByLabelText(/Stop Loss Amount/i);
    fireEvent.change(stopLossInput, { target: { value: '2' } });

    // Add Entry Price to trigger warning check
    // Shares = 50.
    // To exceed 20% of 10000 (which is 2000), Position Value must be > 2000.
    // 50 * Entry Price > 2000 => Entry Price > 40.

    const entryPriceInput = screen.getByLabelText(/Entry Price/i);
    fireEvent.change(entryPriceInput, { target: { value: '100' } });

    // Position Value = 50 * 100 = 5000. 5000 > 2000. Warning should show.
    expect(screen.getByText(/Concentration Risk/i)).toBeInTheDocument();
  });

  it('does not show warning when position size is safe', () => {
    render(<PositionSizer />);

    // Setup: 50 shares calculated
    const stopLossInput = screen.getByLabelText(/Stop Loss Amount/i);
    fireEvent.change(stopLossInput, { target: { value: '2' } });

    // Add Entry Price
    // Shares = 50.
    // Position Value < 2000. 50 * Entry Price < 2000 => Entry Price < 40.

    const entryPriceInput = screen.getByLabelText(/Entry Price/i);
    fireEvent.change(entryPriceInput, { target: { value: '10' } });

    // Position Value = 50 * 10 = 500. 500 < 2000. No warning.
    expect(screen.queryByText(/Concentration Risk/i)).not.toBeInTheDocument();
  });
});
