import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Screener from './Screener';
import { BrowserRouter } from 'react-router-dom';

vi.mock('axios');

// Mock api.ts imports
vi.mock('../api');

import { runTurtleScreener } from '../api';

describe('Screener Component', () => {
  const mockData = [
    {
      Ticker: 'AAPL',
      'Price': 150.0,
      'IV Rank': 20,
      'RSI': 45,
      'Change': 1.5,
      'Vol/OI': 1.2
    },
    {
      Ticker: 'TSLA',
      'Price': 250.0,
      'IV Rank': 50,
      'RSI': 70,
      'Change': -2.0,
      'Vol/OI': 2.0
    }
  ];

  beforeEach(() => {
    vi.resetAllMocks();
    // Mock window.scrollTo
    window.scrollTo = vi.fn();
    // Mock createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:url');
    // Mock revokeObjectURL
    global.URL.revokeObjectURL = vi.fn();
  });

  it('renders screener options', () => {
    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );
    // Be specific about which button or heading we expect
    expect(screen.getAllByText(/Market Scanner/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Turtle Trading/i).length).toBeGreaterThan(0);
  });

  it('fetches and displays data when Run Screener is clicked', async () => {
    // Setup the mock for the default selected tab (Master) but let's switch to Turtle to use existing mockData easily or mock master
    // The component defaults to 'master', which uses fetch() instead of api function.
    // Let's mock fetch for master
    global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve(mockData)
    });

    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    // There are now two "Run Screener" buttons (Desktop and Mobile)
    const runBtns = screen.getAllByRole('button', { name: /Run Screener/i });
    await user.click(runBtns[0]); // Click the first available one

    try {
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith('/screen/master?region=us');
        expect(screen.getByText('AAPL')).toBeInTheDocument();
        expect(screen.getByText('TSLA')).toBeInTheDocument();
      }, { timeout: 3000 });
    } catch (e) {
      console.error('DOM State on Failure:', screen.debug());
      throw e;
    }
  });

  it('handles API errors gracefully', async () => {
     global.fetch = vi.fn().mockRejectedValue(new Error('Network Error'));

    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    const runBtns = screen.getAllByRole('button', { name: /Run Screener/i });
    fireEvent.click(runBtns[0]);

    await waitFor(() => {
      expect(screen.getByText(/Network Error/i)).toBeInTheDocument();
    });
  });

  it('generates and downloads CSV when Download button is clicked', async () => {
     global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve(mockData)
    });

    render(
      <BrowserRouter>
        <Screener />
      </BrowserRouter>
    );

    // Run Screener first to get results
    const runBtns = screen.getAllByRole('button', { name: /Run Screener/i });
    fireEvent.click(runBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });

    // Mock link click
    const linkClickSpy = vi.fn();
    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
        const el = document.createElementNS('http://www.w3.org/1999/xhtml', tagName) as HTMLElement;
        if (tagName === 'a') {
            el.click = linkClickSpy;
        }
        return el;
    });

    const downloadBtn = screen.getByText('Download Results CSV');
    fireEvent.click(downloadBtn);

    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(linkClickSpy).toHaveBeenCalled();

    // Check if the link was created with correct attributes
    expect(createElementSpy).toHaveBeenCalledWith('a');
  });

  it('displays dynamic headers based on result keys', async () => {
    const dynamicData = [
        { 'Column A': 'Value 1', 'Column B': 'Value 2' }
    ];
    global.fetch = vi.fn().mockResolvedValue({
        json: () => Promise.resolve(dynamicData)
    });

    render(
        <BrowserRouter>
          <Screener />
        </BrowserRouter>
      );

      const runBtns = screen.getAllByRole('button', { name: /Run Screener/i });
      fireEvent.click(runBtns[0]);

      await waitFor(() => {
        expect(screen.getByText('Column A')).toBeInTheDocument();
        expect(screen.getByText('Column B')).toBeInTheDocument();
        expect(screen.getByText('Value 1')).toBeInTheDocument();
      });
  });
});
