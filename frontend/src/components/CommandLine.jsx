import React from 'react';

const CommandLine = ({ tickerInput, setTickerInput, handleEvaluate, loading }) => {
  return (
    <div className="bg-bb-panel border-b border-bb-light-gray p-2">
      <form onSubmit={handleEvaluate} className="flex items-center space-x-2">
        <span className="text-bb-yellow font-bold text-sm w-4">&gt;</span>
        <span className="text-bb-gray font-bold text-sm uppercase">RUN_VALUATION</span>
        <input
          type="text"
          className="flex-grow bg-black border border-bb-light-gray text-bb-yellow text-sm font-mono px-2 py-1 outline-none uppercase focus:border-bb-yellow placeholder-bb-light-gray"
          value={tickerInput}
          onChange={(e) => setTickerInput(e.target.value)}
          placeholder="TICKERS (E.G. AAPL,MSFT,CVX)"
          disabled={loading}
          autoFocus
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-bb-bg border border-bb-light-gray text-bb-yellow text-sm font-bold uppercase px-6 py-1 hover:border-bb-yellow hover:text-white transition-colors disabled:opacity-50"
        >
          {loading ? 'RUNNING...' : '[RUN]'}
        </button>
      </form>
    </div>
  );
};

export default CommandLine;
