import React from 'react';
import { Search, Shield, Cpu, Activity, Layout, Menu } from 'lucide-react';

interface AppleHeaderProps {
  ticker: string;
  onTickerChange: (ticker: string) => void;
  onRun: () => void;
  loading: boolean;
}

const AppleHeader: React.FC<AppleHeaderProps> = ({ ticker, onTickerChange, onRun, loading }) => {
  return (
    <header className="glass h-12 flex items-center justify-between px-6 border-b border-apple-border backdrop-blur-md">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-1.5 cursor-pointer">
          <div className="w-5 h-5 bg-apple-text rounded-sm flex items-center justify-center">
            <Shield size={12} className="text-white" />
          </div>
          <span className="text-[14px] font-semibold tracking-tight">AI Valuation Pro</span>
        </div>
        
        <nav className="hidden md:flex items-center gap-5 text-[12px] text-apple-gray font-medium">
          <a href="#" className="hover:text-apple-text transition-colors">Overview</a>
          <a href="#" className="hover:text-apple-text transition-colors">Analysis</a>
          <a href="#" className="hover:text-apple-text transition-colors">Components</a>
          <a href="#" className="hover:text-apple-text transition-colors">Compare</a>
        </nav>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative group">
          <input 
            type="text" 
            value={ticker}
            onChange={(e) => onTickerChange(e.target.value.toUpperCase())}
            placeholder="Search Apple..."
            className="bg-[#E8E8ED] bg-opacity-50 border-none rounded-full h-7 pl-8 pr-4 text-[12px] w-40 focus:w-48 focus:bg-white transition-all focus:ring-2 focus:ring-apple-blue outline-none"
          />
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-apple-gray" />
        </div>

        <button 
          onClick={onRun}
          disabled={loading}
          className={`apple-button-primary h-7 px-4 py-0 flex items-center justify-center text-[12px] ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {loading ? 'Processing...' : 'Run Analysis'}
        </button>
      </div>
    </header>
  );
};

export default AppleHeader;
