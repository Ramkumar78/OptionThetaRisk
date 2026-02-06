import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Docs from './Docs';
import { describe, it, expect } from 'vitest';
import '@testing-library/jest-dom'; // Ensure matchers are available

describe('Docs Component', () => {
  it('renders without crashing', () => {
    render(
      <BrowserRouter>
        <Docs />
      </BrowserRouter>
    );
    expect(screen.getByText(/Documentation &/i)).toBeInTheDocument();
  });

  it('renders Getting Started section', () => {
    render(
      <BrowserRouter>
        <Docs />
      </BrowserRouter>
    );
    expect(screen.getByText(/Getting Started/i)).toBeInTheDocument();
    expect(screen.getByText(/Get Your Data/i)).toBeInTheDocument();
  });

  it('renders Strategy Glossary section', () => {
    render(
      <BrowserRouter>
        <Docs />
      </BrowserRouter>
    );
    expect(screen.getByText(/Strategy Glossary/i)).toBeInTheDocument();
    expect(screen.getByText(/VCP \(Volatility Contraction Pattern\)/i)).toBeInTheDocument();
  });

  it('renders Jargon Buster section', () => {
    render(
      <BrowserRouter>
        <Docs />
      </BrowserRouter>
    );
    expect(screen.getByText(/Jargon Buster/i)).toBeInTheDocument();
    expect(screen.getByText(/Alpha/i)).toBeInTheDocument();
  });

  it('contains link to sample data', () => {
    render(
      <BrowserRouter>
        <Docs />
      </BrowserRouter>
    );
    const link = screen.getByText(/Download Sample Data/i);
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/sample_trades.csv');
  });

  it('handles interactive steps', () => {
     render(
      <BrowserRouter>
        <Docs />
      </BrowserRouter>
    );
    // Initial state: Step 1 active
    expect(screen.getByText(/Export CSV from your broker/i)).toBeInTheDocument();

    // Click Step 2
    fireEvent.click(screen.getByText(/Upload to Auditor/i));

    expect(screen.getByText(/Go to the/i)).toBeInTheDocument();
    expect(screen.getByText(/Audit Page/i)).toBeInTheDocument();
  });
});
