import React from 'react';
import { Crosshair, PenTool, Ruler, FileText, Magnet, Trash2 } from 'lucide-react';

const LeftToolbar = () => {
  const tools = [
    { icon: <Crosshair size={18} />, active: true },
    { icon: <PenTool size={18} />, active: false },
    { icon: <Ruler size={18} />, active: false },
    { icon: <FileText size={18} />, active: false },
    { icon: <Magnet size={18} />, active: false },
  ];

  return (
    <div className="w-[50px] bg-tv-panel border-r border-tv-border flex flex-col items-center py-2 gap-2 shrink-0">
      {tools.map((tool, idx) => (
        <button 
          key={idx}
          className={`p-2 rounded transition-colors ${tool.active ? 'text-tv-blue bg-tv-hover' : 'text-tv-textMuted hover:bg-tv-hover hover:text-tv-text'}`}
        >
          {tool.icon}
        </button>
      ))}
      <div className="mt-auto mb-2 text-tv-textMuted hover:bg-tv-hover hover:text-tv-red p-2 rounded transition-colors cursor-pointer">
        <Trash2 size={18} />
      </div>
    </div>
  );
};

export default LeftToolbar;
