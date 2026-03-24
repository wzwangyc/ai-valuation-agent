import React from 'react';

interface FinancialSpecsProps {
  data: any[];
}

const FinancialSpecs: React.FC<FinancialSpecsProps> = ({ data }) => {
  return (
    <section className="section-container">
      <div className="flex flex-col md:flex-row gap-20">
        <div className="md:w-1/3">
          <h2 className="text-4xl font-bold mb-6">Financial Specs.</h2>
          <p className="text-apple-gray text-lg">
            A precise breakdown of historical performance, mapped meticulously by our Data Agent.
          </p>
        </div>
        
        <div className="md:w-2/3 grid grid-cols-1 gap-12">
          {data.map((item, i) => (
            <div key={i} className="border-b border-apple-border pb-8 last:border-0">
              <div className="flex justify-between items-end mb-4">
                <h3 className="text-xl font-semibold">{item.label}</h3>
                <span className="text-apple-blue font-mono text-sm">{item.growth > 0 ? '+' : ''}{item.growth}% YoY</span>
              </div>
              <div className="grid grid-cols-3 gap-4">
                {item.years.map((y: any, j: number) => (
                  <div key={j} className="flex flex-col">
                    <span className="text-[11px] text-apple-gray uppercase tracking-widest mb-1">{y.year}</span>
                    <span className="text-lg font-medium">${y.value}B</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FinancialSpecs;
