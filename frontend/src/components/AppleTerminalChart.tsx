import React, { useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

interface AppleTerminalChartProps {
  data: any[];
}

const AppleTerminalChart: React.FC<AppleTerminalChartProps> = ({ data }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#1D1D1F',
      },
      grid: {
        vertLines: { color: '#F5F5F7' },
        horzLines: { color: '#F5F5F7' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      timeScale: {
        borderColor: '#D2D2D7',
      },
    });

    const series = chart.addAreaSeries({
      lineColor: '#0066CC',
      topColor: 'rgba(0, 102, 204, 0.2)',
      bottomColor: 'rgba(0, 102, 204, 0.0)',
      lineWidth: 3,
    });

    series.setData(data);
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  return (
    <div className="section-container">
      <div className="apple-card p-4">
        <div className="mb-6">
          <h3 className="text-2xl font-bold">Historical Context.</h3>
          <p className="text-apple-gray text-sm">6-month performance analyzed by the Data Agent.</p>
        </div>
        <div ref={chartContainerRef} className="w-full h-[400px]" />
      </div>
    </div>
  );
};

export default AppleTerminalChart;
