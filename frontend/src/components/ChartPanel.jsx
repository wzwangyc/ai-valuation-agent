import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';

export default function ChartPanel({ ticker }) {
  const chartContainerRef = useRef();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ticker) return;

    let isMounted = true;
    setLoading(true);

    fetch(`/api/chart/${ticker}`)
      .then(res => res.json())
      .then(chartData => {
        if (isMounted) {
          setData(chartData);
          setLoading(false);
        }
      })
      .catch(err => {
        console.error("Error fetching chart data:", err);
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
  }, [ticker]);

  useEffect(() => {
    if (loading || data.length === 0 || !chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { color: '#1A1D23' },
        textColor: '#CCCCCC',
      },
      grid: {
        vertLines: { color: '#2B2F36' },
        horzLines: { color: '#2B2F36' },
      },
      timeScale: {
        borderColor: '#2B2F36',
      },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#00FF88',
      downColor: '#FF5555',
      borderVisible: false,
      wickUpColor: '#00FF88',
      wickDownColor: '#FF5555',
    });

    candlestickSeries.setData(data);

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, loading]);

  return (
    <div className="w-full bg-bb-panel border border-bb-gray/20 flex flex-col">
      <div className="px-4 py-2 border-b border-bb-gray/20 text-xs text-bb-yellow font-bold uppercase tracking-wider">
        6-Month Daily OHLC · {ticker}
      </div>
      <div className="relative flex-1 min-h-[300px]" ref={chartContainerRef}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center text-bb-light-gray text-xs">
            LOADING CHART DATA...
          </div>
        )}
        {!loading && data.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-bb-light-gray text-xs">
            NO CHART DATA AVAILABLE
          </div>
        )}
      </div>
    </div>
  );
}
