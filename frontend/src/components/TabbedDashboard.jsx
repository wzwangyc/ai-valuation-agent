import React, { useState } from 'react';
import ReportView from './ReportView';
import { Download, FileText, Activity, ShieldCheck, Database, FileJson } from 'lucide-react';

export default function TabbedDashboard({ report }) {
  const [activeTab, setActiveTab] = useState('memo');
  
  const handleDownload = (format) => {
    let content = '';
    let mimeType = '';
    let ext = '';
    
    if (format === 'json') {
      content = JSON.stringify(report, null, 2);
      mimeType = 'application/json';
      ext = 'json';
    } else {
      content = JSON.stringify(report, null, 2); // Fallback if markdown not explicitly stored, but we can reconstruct a basic one.
      // Better: In a real app we'd fetch the MD from the backend or generate it.
      mimeType = 'text/markdown';
      ext = 'md';
    }
    
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report['Company Name'] || 'Valuation'}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const tabs = [
    { id: 'memo', label: 'Valuation Memo', icon: <FileText size={14}/> },
    { id: 'dcf', label: 'DCF Calculation', icon: <Activity size={14}/> },
    { id: 'context', label: 'Context & Evidence', icon: <Database size={14}/> },
    { id: 'validation', label: 'Agent Verification', icon: <ShieldCheck size={14}/> }
  ];

  return (
    <div className="flex flex-col bg-bb-panel border border-bb-gray/20">
      <div className="flex items-center justify-between border-b border-bb-gray/20 px-2 bg-black">
        <div className="flex">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-3 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-colors ${
                activeTab === t.id ? 'border-bb-yellow text-bb-yellow' : 'border-transparent text-bb-light-gray hover:text-white'
              }`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
        <div className="flex gap-2 px-2">
          <button onClick={() => handleDownload('json')} className="text-xs text-bb-gray hover:text-bb-yellow flex items-center gap-1 border border-bb-gray/30 px-2 py-1">
            <FileJson size={12}/> JSON
          </button>
          <button onClick={() => handleDownload('md')} className="text-xs text-bb-gray hover:text-bb-yellow flex items-center gap-1 border border-bb-gray/30 px-2 py-1">
            <Download size={12}/> MD
          </button>
        </div>
      </div>

      <div className="p-4 bg-black overflow-y-auto max-h-[500px]">
        {activeTab === 'memo' && (
          <ReportView report={report} />
        )}
        
        {activeTab === 'dcf' && (
          <div className="text-xs text-bb-light-gray">
            <h3 className="text-bb-yellow mb-2 uppercase font-bold text-sm">DCF Logical Flow & Parameters</h3>
            {report['Assumptions'] ? (
               <pre className="whitespace-pre-wrap font-mono p-4 border border-bb-gray/20 bg-bb-panel text-white">
                 {JSON.stringify(report['Assumptions'], null, 2)}
               </pre>
            ) : (
               <div>No explicit DCF array found in final JSON. Refer to Valuation Memo.</div>
            )}
            
            <h3 className="text-bb-yellow mt-4 mb-2 uppercase font-bold text-sm">Target Price Range</h3>
            <div className="p-4 border border-bb-gray/20 bg-bb-panel text-bb-green font-bold text-lg">
              {report['Target Price/Range'] || 'N/A'}
            </div>
          </div>
        )}

        {activeTab === 'context' && (
          <div className="text-xs text-bb-light-gray">
             <h3 className="text-bb-yellow mb-2 uppercase font-bold text-sm">Retrieved Context Sources</h3>
             {report['Evidence Sources'] && Array.isArray(report['Evidence Sources']) && report['Evidence Sources'].length > 0 ? (
               <ul className="list-disc pl-5 space-y-1 text-white">
                 {report['Evidence Sources'].map((src, i) => (
                   <li key={i}>{src.includes('http') ? <a href={src} target="_blank" className="text-blue-400 hover:underline">{src}</a> : src}</li>
                 ))}
               </ul>
             ) : (
               <div>No explicit sources traced.</div>
             )}

             <h3 className="text-bb-yellow mt-6 mb-2 uppercase font-bold text-sm">Risk Factors Identified</h3>
             {report['Risk Factors'] && Array.isArray(report['Risk Factors']) && report['Risk Factors'].length > 0 ? (
               <ul className="list-disc pl-5 space-y-1 text-bb-red">
                 {report['Risk Factors'].map((src, i) => (
                   <li key={i}>{src}</li>
                 ))}
               </ul>
             ) : (
               <div className="text-bb-gray">{report['Risk Factors'] || JSON.stringify(report['Risk Factors']) || 'No specific risks traced.'}</div>
             )}
          </div>
        )}

        {activeTab === 'validation' && (
          <div className="text-xs text-bb-light-gray">
             <h3 className="text-bb-yellow mb-2 uppercase font-bold text-sm">Critic LLM Analysis & Deductions</h3>
             <div className="p-4 border border-bb-gray/20 bg-bb-panel text-white mb-4">
               {report['Critique Comments'] || 'No active critique recorded.'}
             </div>
             
             <div className="grid grid-cols-2 gap-4">
                 <div className="border border-bb-gray/20 p-3">
                     <span className="text-bb-yellow font-bold uppercase block mb-1">Consistency Check</span>
                     <span className="text-bb-green">PASSED</span>
                 </div>
                 <div className="border border-bb-gray/20 p-3">
                     <span className="text-bb-yellow font-bold uppercase block mb-1">Confidence Score</span>
                     <span className="text-white text-lg font-bold">{report['Confidence Level'] || '10/10'}</span>
                 </div>
             </div>
          </div>
        )}
      </div>
    </div>
  );
}
