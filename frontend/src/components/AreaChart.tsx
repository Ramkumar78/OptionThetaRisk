import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, AreaSeries, type IChartApi, type ISeriesApi, type AreaData } from 'lightweight-charts';

interface AreaChartProps {
  data: AreaData[];
  width?: number;
  height?: number;
  color?: string;
}

const AreaChart: React.FC<AreaChartProps> = ({ data, width, height, color = '#2563eb' }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  // Handle auto-resizing if no width/height provided
  useEffect(() => {
    if (width && height) return;

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length === 0 || !entries[0].contentRect) return;
      const { width: newWidth } = entries[0].contentRect;

      if (chartRef.current && newWidth > 0) {
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

    // Default width to 600 if clientWidth is 0 (e.g. headless/test)
    const initialWidth = width || chartContainerRef.current.clientWidth || 600;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'rgba(156, 163, 175, 1)', // gray-400
      },
      width: initialWidth,
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

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: color,
      topColor: color,
      bottomColor: 'rgba(37, 99, 235, 0.05)', // transparent version
    });

    try {
        // Ensure data is sorted by time and valid
        if (data && data.length > 0) {
            const sortedData = [...data].sort((a, b) => (a.time > b.time ? 1 : -1));
            // Check for duplicates
            const uniqueData = sortedData.filter((item, index, self) =>
                index === 0 || item.time !== self[index - 1].time
            );
            areaSeries.setData(uniqueData);
        }
    } catch (e) {
        console.error("AreaChart Data Error:", e);
    }

    chart.timeScale().fitContent();

    chartRef.current = chart;
    seriesRef.current = areaSeries;

    return () => {
      chart.remove();
    };
  }, []); // Run once on mount

  // Update data
  useEffect(() => {
    if (seriesRef.current && data && data.length > 0) {
      try {
          const sortedData = [...data].sort((a, b) => (a.time > b.time ? 1 : -1));
          const uniqueData = sortedData.filter((item, index, self) =>
              index === 0 || item.time !== self[index - 1].time
          );
          seriesRef.current.setData(uniqueData);
      } catch (e) {
          console.error("AreaChart Update Error:", e);
      }
    }
  }, [data]);

  // Update options
  useEffect(() => {
      if (seriesRef.current && color) {
          seriesRef.current.applyOptions({
              lineColor: color,
              topColor: color,
          });
      }
  }, [color]);

  return (
    <div ref={chartContainerRef} className="w-full relative" style={{ height: height || 400 }} />
  );
};

export default AreaChart;
