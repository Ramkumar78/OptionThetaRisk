import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, type IChartApi, type ISeriesApi, type CandlestickData } from 'lightweight-charts';

interface CandlestickChartProps {
  data: CandlestickData[];
  width?: number;
  height?: number;
}

const CandlestickChart: React.FC<CandlestickChartProps> = ({ data, width, height }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [containerDimensions, setContainerDimensions] = useState({ width: width || 600, height: height || 400 });

  // Handle auto-resizing if no width/height provided
  useEffect(() => {
    if (width && height) return;

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length === 0 || !entries[0].contentRect) return;
      const { width: newWidth, height: newHeight } = entries[0].contentRect;

      // Update dimensions state or directly update chart
      if (chartRef.current) {
        chartRef.current.applyOptions({ width: newWidth, height: height || 400 });
      }
    });

    if (chartContainerRef.current) {
      resizeObserver.observe(chartContainerRef.current);
    }

    return () => resizeObserver.disconnect();
  }, [width, height]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'rgba(156, 163, 175, 1)', // gray-400
      },
      width: width || chartContainerRef.current.clientWidth,
      height: height || 400,
      grid: {
        vertLines: { color: 'rgba(156, 163, 175, 0.1)' },
        horzLines: { color: 'rgba(156, 163, 175, 0.1)' },
      },
      timeScale: {
        borderColor: 'rgba(156, 163, 175, 0.2)',
      },
      rightPriceScale: {
        borderColor: 'rgba(156, 163, 175, 0.2)',
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981', // emerald-500
      downColor: '#ef4444', // red-500
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    candlestickSeries.setData(data);

    // Fit content
    chart.timeScale().fitContent();

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;

    return () => {
      chart.remove();
    };
  }, []); // Run once on mount

  // Update data if it changes
  useEffect(() => {
    if (seriesRef.current) {
      seriesRef.current.setData(data);
    }
  }, [data]);

  return (
    <div ref={chartContainerRef} className="w-full relative" style={{ height: height || 400 }} />
  );
};

export default CandlestickChart;
