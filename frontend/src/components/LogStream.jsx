import React, { useEffect, useRef } from 'react';

const LogStream = ({ logs, loading }) => {
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="bg-bb-panel border-b border-bb-light-gray h-48 overflow-y-auto p-2 font-mono text-xs leading-relaxed" ref={terminalRef}>
      {logs.map((log, i) => (
        <div key={i} className="flex space-x-2 mb-1">
          <span className="text-bb-light-gray shrink-0">[{log.time}]</span>
          <span className="text-bb-yellow font-bold shrink-0">[{log.ticker}] [{log.agent}]</span>
          <span className="text-white break-words">{log.message}</span>
        </div>
      ))}
      {loading && (
        <div className="text-bb-light-gray animate-pulse mt-2">
          _System is processing data...
        </div>
      )}
    </div>
  );
};

export default LogStream;
