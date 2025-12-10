import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Audit from './Audit';
import axios from 'axios';
import { BrowserRouter } from 'react-router-dom';

vi.mock('axios');

describe('Audit Component', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    (axios.post as any).mockResolvedValue({ data: { status: 'success' } });
  });

  it('renders without crashing', () => {
    render(
      <BrowserRouter>
        <Audit />
      </BrowserRouter>
    );
    expect(screen.getByText(/Audit Your Portfolio/i)).toBeInTheDocument();
  });

  it('switches to Manual Entry mode', () => {
    render(
      <BrowserRouter>
        <Audit />
      </BrowserRouter>
    );
    const manualTab = screen.getByText(/Manual Entry/i);
    fireEvent.click(manualTab);

    expect(screen.getByText(/\+ Add Row/i)).toBeInTheDocument();
  });

  it('adds a row in Manual Entry mode', () => {
    render(
      <BrowserRouter>
        <Audit />
      </BrowserRouter>
    );
    fireEvent.click(screen.getByText(/Manual Entry/i));
    fireEvent.click(screen.getByText(/\+ Add Row/i));

    const selects = screen.getAllByRole('combobox');
    expect(selects.length).toBeGreaterThan(0);
  });
});
