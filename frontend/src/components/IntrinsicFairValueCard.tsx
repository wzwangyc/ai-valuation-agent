import React from 'react';
import { TrendingUp, ArrowRight } from 'lucide-react';

interface IntrinsicFairValueCardProps {
  ticker: string;
  fairValue: number;
  currentPrice: number;
  upside: number;
}

const IntrinsicFairValueCard: React.FC<IntrinsicFairValueCardProps> = ({ ticker, fairValue, currentPrice, upside }) => {
  return (
    <section className="section-container">
      <div className="apple-card overflow-hidden relative group">
        <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
          <TrendingUp size={120} className="text-apple-blue" />
        </div>
        
        <div className="relative z-10">
          <span className="text-apple-blue font-semibold text-lg mb-2 block">Intrinsic Fair Value</span>
          <h2 className="text-7xl font-bold mb-8 tracking-tighter">${fairValue.toFixed(2)}</h2>
          
          <div className="flex flex-wrap gap-12 border-t border-apple-border pt-8">
            <div>
              <p className="text-apple-gray text-sm font-medium uppercase tracking-widest mb-1">Current Price</p>
              <p className="text-2xl font-semibold">${currentPrice.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-apple-gray text-sm font-medium uppercase tracking-widest mb-1">Potential Upside</p>
              <p className="text-2xl font-semibold text-apple-blue">+{upside.toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-apple-gray text-sm font-medium uppercase tracking-widest mb-1">Recommendation</p>
              <p className="text-2xl font-semibold">Accumulate</p>
            </div>
          </div>

          <div className="mt-12 flex items-center gap-2 text-apple-blue font-semibold cursor-pointer group/link">
            <span>Explore the methodology</span>
            <ArrowRight size={18} className="group-hover/link:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>
    </section>
  );
};

export default IntrinsicFairValueCard;
