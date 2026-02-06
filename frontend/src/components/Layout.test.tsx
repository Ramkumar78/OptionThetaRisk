import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import Layout from './Layout';

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

describe('Layout Component', () => {
  beforeEach(() => {
    // Clear localStorage and classList before each test
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  it('renders correctly', () => {
    render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    );
    expect(screen.getByText('TradeGuardian')).toBeInTheDocument();
  });

  it('toggles theme correctly', () => {
    render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    );

    const themeButton = screen.getByRole('button', { name: '' }); // The button has an SVG, but no text label. We might need to target by ID or other means.
    // However, looking at the code:
    // <button id="theme-toggle" ...>
    // We can use querySelector or getByRole if we are careful.
    // There are multiple buttons.

    // Let's use the ID which is more reliable here as the button doesn't have text.
    // But testing-library encourages roles.

    // We can select by ID in the test.
    const button = document.querySelector('#theme-toggle');
    expect(button).toBeInTheDocument();

    // Initial state: light mode (since matchMedia mocked to false and localStorage empty)
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.getItem('theme')).toBe('light');

    // Click to toggle to dark
    fireEvent.click(button!);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('theme')).toBe('dark');

    // Click to toggle back to light
    fireEvent.click(button!);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.getItem('theme')).toBe('light');
  });

  it('respects system preference if no localStorage', () => {
     // Mock matchMedia to return true for dark mode
     Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation(query => ({
          matches: query === '(prefers-color-scheme: dark)',
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });

      render(
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      );

      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(localStorage.getItem('theme')).toBe('dark');
  });
});
