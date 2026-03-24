import React from 'react';
import { Cpu, Search, Activity, Shield, FileText } from 'lucide-react';

interface AgentOrchestratorProps {
  activeAgent: string | null;
  completedAgents: string[];
}

const AGENTS = [
  { id: 'Planner', label: 'Planner', icon: <Search size={20} /> },
  { id: 'DataCollector', label: 'Data Agent', icon: <Cpu size={20} /> },
  { id: 'Valuator', label: 'Valuator', icon: <Activity size={20} /> },
  { id: 'Critic', label: 'Critic AI', icon: <Shield size={20} /> },
  { id: 'Reporter', label: 'Reporter', icon: <FileText size={20} /> }
];

const AgentOrchestrator: React.FC<AgentOrchestratorProps> = ({ activeAgent, completedAgents }) => {
  return (
    <div className="section-container">
      <div className="flex flex-col items-center mb-16">
        <h2 className="text-5xl font-bold mb-4">Multi-Agent Intelligence</h2>
        <p className="text-apple-gray text-xl max-w-2xl text-center">
          Experience the power of five specialized AI agents working in perfect harmony to deliver institutional-grade equity valuation.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 relative">
        {/* Connection Line */}
        <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-apple-border -translate-y-1/2 z-0"></div>

        {AGENTS.map((agent, i) => {
          const isActive = activeAgent === agent.id;
          const isCompleted = completedAgents.includes(agent.id);
          
          return (
            <div key={agent.id} className="relative z-10 flex flex-col items-center">
              <div 
                className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-700 ${
                  isActive ? 'bg-apple-blue text-white shadow-lg scale-110' :
                  isCompleted ? 'bg-apple-text text-white' :
                  'bg-white text-apple-gray border border-apple-border'
                }`}
              >
                {isActive && <div className="absolute inset-0 rounded-full bg-apple-blue animate-ping opacity-20"></div>}
                {agent.icon}
              </div>
              <div className="mt-4 text-center">
                <span className={`text-[13px] font-semibold ${isActive ? 'text-apple-blue' : 'text-apple-text'}`}>
                  {agent.label}
                </span>
                <p className="text-[11px] text-apple-gray mt-1">
                  {isActive ? 'Processing...' : isCompleted ? 'Optimized' : 'Ready'}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AgentOrchestrator;
