import React from 'react';

const FooterBar = ({ reportsCount }) => {
  return (
    <div className="flex justify-between items-center bg-bb-bg border-t border-bb-light-gray px-4 py-1 text-xs text-bb-light-gray h-8">
      <div>SYSTEM: READY</div>
      <div>LAST UPDATE: {new Date().toISOString().replace('T', ' ').substring(0, 19)}</div>
      <div>EVIDENCE SOURCES: TOTAL CAPTURED</div>
      <div>EXPORT: JSON / MARKDOWN</div>
    </div>
  );
};

export default FooterBar;
