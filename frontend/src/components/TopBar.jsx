import React from 'react';
import { Search, RotateCcw, LayoutTemplate, Activity, ShieldCheck, Crosshair, PenTool, Ruler, FileText } from 'lucide-react';

const TopBar = ({ tickerInput, setTickerInput, handleEvaluate, loading }) => {
  return (
    <div className="flex justify-between items-center bg-tv-panel px-4 py-2 border-b border-tv-border text-xs font-sans">
      
      {/* Left: Logo & Search */}
      <div className="flex items-center gap-4">
        {/* Fake TV Logo */}
        <div className="flex items-center gap-2">
          <Activity size={24} className="text-tv-blue" />
          <span className="text-white font-bold text-lg tracking-tight">ValuationView</span>
        </div>
        
        {/* Ticker Search (Replaces CommandLine) */}
        <div className="relative flex items-center">
          <form onSubmit={handleEvaluate} className="flex">
            <div className="absolute left-2 top-1/2 -translate-y-1/2 text-tv-textMuted">
              <Search size={14} />
            </div>
            <input
              type="text"
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value)}
              placeholder="Symbol Search (e.g. AAPL)"
              className="pl-8 pr-4 py-1.5 bg-tv-bg border border-tv-border rounded text-white text-sm focus:outline-none focus:border-tv-blue transition-colors font-sans uppercase w-[200px]"
              disabled={loading}
              autoFocus
            />
          </form>
        </div>

        {/* Fake Timeframes */}
        <div className="hidden md:flex items-center gap-1 border-l border-tv-border pl-4 ml-2">
          <button className="px-2 py-1 hover:bg-tv-hover rounded text-tv-textMuted hover:text-white">1D</button>
          <button className="px-2 py-1 hover:bg-tv-hover rounded text-tv-textMuted hover:text-white">5D</button>
          <button className="px-2 py-1 hover:bg-tv-hover rounded text-tv-textMuted hover:text-white">1M</button>
          <button className="px-2 py-1 bg-tv-hover rounded text-tv-blue font-bold">6M</button>
          <button className="px-2 py-1 hover:bg-tv-hover rounded text-tv-textMuted hover:text-white">YTD</button>
        </div>
      </div>

      {/* Right: Layout & Status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-tv-textMuted hidden sm:flex">
          <span className="flex items-center gap-1"><ShieldCheck size={14} className="text-tv-green"/> SECURE</span>
        </div>
        <button 
           onClick={handleEvaluate}
           disabled={loading}
           className="px-4 py-1.5 bg-tv-blue text-white rounded font-bold hover:bg-blue-600 transition-colors flex items-center gap-2 text-sm disabled:opacity-50"
        >
          {loading ? <RotateCcw className="animate-spin" size={14} /> : null}
          {loading ? 'ANALYZING...' : 'RUN AGENT'}
        </button>
      </div>

    </div>
  );
};

export default TopBar;
