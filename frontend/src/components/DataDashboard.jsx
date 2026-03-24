import React from 'react';

const DataCard = ({ title, value, colorClass = "text-white" }) => (
  <div className="border border-white bg-bb-bg p-3 flex flex-col justify-between h-20 shadow-none">
    <div className="text-bb-light-gray text-xs uppercase font-bold tracking-wider">{title}</div>
    <div className={`text-lg font-bold ${colorClass}`}>{value}</div>
  </div>
);

const DataDashboard = ({ report }) => {
  if (!report) return null;

  const upsetDownside = parseFloat(report['Target Price/Range']['Upside/Downside']) || 0;
  const upsetColorItem = upsetDownside > 0 ? 'text-bb-green' : 'text-bb-red';
  
  const currentPrice = `$${report['Key Inputs']['Current Price']}`;
  const dcfPrice = report['Target Price/Range']['DCF Fair Price'];
  const upsideLabel = `${report['Target Price/Range']['Upside/Downside']}`;

  const wacc = report['Assumptions']['WACC'];
  const termG = report['Assumptions']['Terminal Growth Rate Cap'] || report['Assumptions']['Applied Terminal Growth Rate'] || '3.5%';
  const conf = report['Confidence Level'] ? report['Confidence Level'].split('—')[0].trim() : 'N/A';
  
  return (
    <div className="p-4 bg-bb-panel border-b border-bb-light-gray">
      <div className="text-bb-yellow text-md font-bold uppercase mb-4 border-b border-bb-yellow pb-1 inline-block">
        {report['Company Name']} - VALUATION SUMMARY
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <DataCard title="CURRENT PRICE" value={currentPrice} />
        <DataCard title="DCF FAIR VALUE" value={dcfPrice} colorClass="text-bb-yellow" />
        <DataCard title="UPSIDE/DOWNSIDE" value={upsideLabel} colorClass={upsetColorItem} />
        
        <DataCard title="WACC" value={wacc} />
        <DataCard title="TERMINAL G" value={termG} />
        <DataCard title="CONFIDENCE" value={conf} colorClass="text-white" />
      </div>
    </div>
  );
};

export default DataDashboard;
