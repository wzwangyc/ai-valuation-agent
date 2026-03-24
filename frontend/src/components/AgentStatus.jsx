import React from 'react';

const AGENTS = [
  { id: 'Planner', label: 'Planner' },
  { id: 'DataCollector', label: 'Data Agent' },
  { id: 'Valuator', label: 'Valuator' },
  { id: 'Critic', label: 'Critic AI' },
  { id: 'Reporter', label: 'Reporter' }
];

const AgentStatus = ({ activeAgent, completedAgents }) => {
  return (
    <div className="flex bg-bb-bg border-b border-bb-light-gray p-2 text-sm uppercase tracking-wider overflow-x-auto space-x-6">
      {AGENTS.map((agent) => {
        const isActive = activeAgent === agent.id;
        const isCompleted = completedAgents.includes(agent.id);
        
        // Status indicator
        let statusIcon = '⏳';
        let textColor = 'text-bb-light-gray';
        
        if (isCompleted) {
          statusIcon = '✅';
          textColor = 'text-bb-green';
        } else if (isActive) {
          statusIcon = '🔄';
          textColor = 'text-bb-yellow';
        }

        return (
          <div key={agent.id} className={`flex items-center space-x-2 ${textColor} font-bold whitespace-nowrap`}>
            <span>{agent.label}</span>
            <span>{statusIcon}</span>
          </div>
        );
      })}
    </div>
  );
};

export default AgentStatus;
