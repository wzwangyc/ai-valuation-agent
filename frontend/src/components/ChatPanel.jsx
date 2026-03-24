import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2 } from 'lucide-react';

export default function ChatPanel({ ticker }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: `Agent ready. Ask me anything about the ${ticker} valuation report.` }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || !ticker || loading) return;

    const userMessage = input;
    setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`/api/chat/${ticker}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage })
      });
      const data = await res.json();
      
      setMessages(prev => [...prev, { role: 'assistant', text: data.answer }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', text: "SYSTEM ERROR: Failed to invoke RAG agent." }]);
    } finally {
      setLoading(false);
    }
  };

  if (!ticker) return null;

  return (
    <div className="flex flex-col h-full bg-bb-bg border-l border-bb-gray/20 w-80 shrink-0">
      <div className="px-4 py-3 border-b border-bb-gray/20 bg-bb-panel uppercase text-xs font-bold text-bb-yellow flex items-center gap-2">
        <Bot size={14} /> Agent Chat - {ticker}
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4" ref={scrollRef}>
        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col gap-1 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
            <span className="text-[10px] text-bb-light-gray uppercase flex items-center gap-1">
              {msg.role === 'user' ? <><User size={10}/> You</> : <><Bot size={10}/> Agent</>}
            </span>
            <div className={`text-xs p-2 rounded-none border ${msg.role === 'user' ? 'bg-bb-panel border-bb-yellow/30 text-bb-yellow' : 'bg-[#0A0C10] border-bb-gray/20 text-bb-gray'}`}>
              <span className="whitespace-pre-wrap">{msg.text}</span>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-start gap-2 text-xs text-bb-light-gray mt-2">
            <Loader2 className="animate-spin" size={14} /> Retrieving evidence...
          </div>
        )}
      </div>

      <form onSubmit={handleSend} className="p-3 border-t border-bb-gray/20 bg-bb-panel flex gap-2">
        <input 
          type="text" 
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 bg-black border border-bb-gray/30 p-2 text-xs text-white focus:outline-none focus:border-bb-yellow"
          disabled={loading}
        />
        <button 
          type="submit" 
          disabled={loading || !input.trim()}
          className="p-2 bg-bb-yellow text-black disabled:opacity-50 hover:bg-yellow-400 transition-colors"
        >
          <Send size={14} />
        </button>
      </form>
    </div>
  );
}
