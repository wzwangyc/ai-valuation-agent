import React, { useState } from 'react';
import AppleHeader from './components/AppleHeader';
import AgentOrchestrator from './components/AgentOrchestrator';
import IntrinsicFairValueCard from './components/IntrinsicFairValueCard';
import FinancialSpecs from './components/FinancialSpecs';
import ValidationAuditView from './components/ValidationAuditView';
import AppleTerminalChart from './components/AppleTerminalChart';
import RAGBubble from './components/RAGBubble';

import { mockMetrics, mockDCF, mockValidationIssues, mockEvidenceAudits } from './mockData';

const financialData = [
  { label: 'Revenue', growth: 12.5, years: [{ year: '2023', value: 6.8 }, { year: '2024', value: 7.2 }, { year: '2025 (E)', value: 8.1 }] },
  { label: 'EBITDA', growth: 8.2, years: [{ year: '2023', value: 1.4 }, { year: '2024', value: 1.5 }, { year: '2025 (E)', value: 1.7 }] },
  { label: 'Free Cash Flow', growth: 15.1, years: [{ year: '2023', value: 0.9 }, { year: '2024', value: 1.1 }, { year: '2025 (E)', value: 1.3 }] },
];

const chartData = [
  { time: '2023-10-01', value: 170.5 },
  { time: '2023-11-15', value: 182.3 },
  { time: '2023-12-20', value: 189.4 },
  { time: '2024-01-25', value: 184.2 },
  { time: '2024-02-15', value: 191.8 },
  { time: '2024-03-22', value: 189.45 },
];

function App() {
  const [ticker, setTicker] = useState('AAPL');
  const [loading, setLoading] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [completedAgents, setCompletedAgents] = useState<string[]>([]);
  const [showResult, setShowResult] = useState(false);

  const handleRunAnalysis = async () => {
    setLoading(true);
    setCompletedAgents([]);
    setShowResult(false);
    
    const agents = ['Planner', 'DataCollector', 'Valuator', 'Critic', 'Reporter'];
    
    for (const agent of agents) {
      setActiveAgent(agent);
      await new Promise(resolve => setTimeout(resolve, 1200));
      setCompletedAgents(prev => [...prev, agent]);
    }
    
    setActiveAgent(null);
    setLoading(false);
    setShowResult(true);
  };

  return (
    <div className="min-h-screen bg-apple-bg text-apple-text selection:bg-apple-blue selection:text-white pb-20">
      <AppleHeader 
        ticker={ticker} 
        onTickerChange={setTicker} 
        onRun={handleRunAnalysis} 
        loading={loading} 
      />

      <main>
        {/* Welcome Section */}
        <section className="section-container text-center pt-32 pb-24">
          <div className="inline-block px-4 py-1.5 bg-apple-blue bg-opacity-10 text-apple-blue rounded-full text-xs font-bold uppercase tracking-widest mb-8 animate-in fade-in zoom-in duration-700">
            Institutional Multi-Agent Intelligence
          </div>
          <h1 className="text-[90px] font-bold tracking-tight leading-[0.9] mb-8 animate-in slide-in-from-top-10 duration-1000">
            Precision.<br/>
            <span className="text-apple-gray">Beyond Intuition.</span>
          </h1>
          <p className="text-2xl text-apple-gray max-w-2xl mx-auto leading-tight mb-12 opacity-80 animate-in fade-in duration-1000 delay-300">
            Our agent orchestrator leverages audited financial data to determine the true intrinsic value of your assets.
          </p>
          <div className="animate-in fade-in duration-1000 delay-500">
            <button 
              onClick={handleRunAnalysis}
              className="apple-button-primary text-xl px-12 py-4 shadow-2xl hover:scale-105"
            >
              Analyze {ticker}
            </button>
          </div>
        </section>

        {/* Dynamic Orchesration */}
        <div id="orchestrator" className="bg-white border-y border-apple-border">
          <AgentOrchestrator activeAgent={activeAgent} completedAgents={completedAgents} />
        </div>

        {/* Dynamic Results Content */}
        {showResult && (
          <div className="space-y-0 animate-in fade-in duration-1000">
            <div className="bg-apple-bg py-20">
              <IntrinsicFairValueCard 
                ticker={ticker} 
                fairValue={mockDCF.fair_price_per_share} 
                currentPrice={189.45} 
                upside={((mockDCF.fair_price_per_share / 189.45) - 1) * 100} 
              />
            </div>

            <AppleTerminalChart data={chartData} />
            
            <FinancialSpecs data={financialData} />
            
            <div className="bg-white py-20">
              <ValidationAuditView audits={mockEvidenceAudits} issues={mockValidationIssues} />
            </div>

            {/* CTA section */}
            <section className="section-container pt-32 text-center">
              <div className="apple-card bg-apple-text text-white p-20 rounded-[4rem]">
                <h2 className="text-6xl font-bold mb-8">Ready for Audit.</h2>
                <p className="text-apple-gray text-xl mb-12 max-w-xl mx-auto">
                  The Analyst Reporter has finalized the formal Investment Memorandum for {ticker}.
                </p>
                <div className="flex justify-center gap-6">
                  <button className="bg-white text-black px-10 py-4 rounded-full font-bold text-lg hover:bg-opacity-90 transition-all">Download Report</button>
                  <button className="border border-white border-opacity-30 px-10 py-4 rounded-full font-bold text-lg hover:bg-white hover:text-black transition-all">View Evidence</button>
                </div>
              </div>
            </section>
          </div>
        )}

        <footer className="section-container border-t border-apple-border mt-32 text-center py-20">
          <p className="text-[12px] text-apple-gray uppercase tracking-widest mb-6 font-bold">Institutional Guardrails</p>
          <p className="text-sm text-apple-gray max-w-3xl mx-auto italic leading-relaxed">
            Data provided for demonstration purposes. All valuations are purely algorithmic and derived from multi-agent consensus. Always consult with a certified financial analyst before making investment decisions.
          </p>
        </footer>
      </main>

      <RAGBubble ticker={ticker} />
    </div>
  );
}

export default App;
