import '@testing-library/jest-dom';
import { vi } from 'vitest';
import React from 'react';

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock lightweight-charts
vi.mock('lightweight-charts', () => ({
  createChart: () => ({
    applyOptions: vi.fn(),
    timeScale: () => ({
      fitContent: vi.fn(),
    }),
    addSeries: () => ({
      setData: vi.fn(),
      applyOptions: vi.fn(),
    }),
    remove: vi.fn(),
  }),
  ColorType: { Solid: 'solid' },
  AreaSeries: 'AreaSeries',
  CandlestickSeries: 'CandlestickSeries',
}));

// Mock react-ts-tradingview-widgets
vi.mock('react-ts-tradingview-widgets', () => ({
  AdvancedRealTimeChart: () => React.createElement('div', { 'data-testid': 'tradingview-widget' }, 'TradingView Widget'),
}));
