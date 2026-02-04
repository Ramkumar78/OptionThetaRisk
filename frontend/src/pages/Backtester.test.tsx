import React from 'react';
import { render, screen } from '@testing-library/react';
import Backtester from './Backtester';
import { vi } from 'vitest';

// Mock Chart.js to avoid canvas errors in JSDOM
vi.mock('react-chartjs-2', () => ({
  Line: () => null
}));

describe('Backtester Component', () => {
  it('renders the backtester form', () => {
    render(<Backtester />);

    expect(screen.getByText('Visual Strategy Backtester')).toBeInTheDocument();
    expect(screen.getByLabelText(/Ticker/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Strategy/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Initial Capital/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Backtest/i })).toBeInTheDocument();
  });
});
