import React, { useState } from 'react';
import { MessageCircle, Send, X, Shield } from 'lucide-react';

interface RAGBubbleProps {
  ticker: string;
}

const RAGBubble: React.FC<RAGBubbleProps> = ({ ticker }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: `Hello! I'm your Intelligence Agent. Ask me anything about ${ticker}'s valuation.` }
  ]);
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim()) return;
    setMessages([...messages, { role: 'user', content: input }]);
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Based on the latest 10-K filing, ${ticker} shows strong free cash flow conversion. My analysis is anchored to audited evidence.` 
      }]);
    }, 1000);
    setInput('');
  };

  return (
    <div className="fixed bottom-8 right-8 z-[100]">
      {isOpen ? (
        <div className="w-[380px] h-[500px] bg-white rounded-3xl shadow-2xl border border-apple-border flex flex-col overflow-hidden animate-in slide-in-from-bottom-5 duration-300">
          <div className="p-4 border-b border-apple-border flex justify-between items-center bg-apple-bg">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-apple-blue" />
              <span className="font-semibold text-sm">Intelligence Agent</span>
            </div>
            <button onClick={() => setIsOpen(false)}><X size={18} className="text-apple-gray" /></button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] p-3 rounded-2xl text-[13px] ${
                  m.role === 'user' ? 'bg-apple-blue text-white' : 'bg-apple-bg text-apple-text'
                }`}>
                  {m.content}
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 border-t border-apple-border">
            <div className="flex gap-2">
              <input 
                type="text" 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask a question..."
                className="flex-1 bg-apple-bg rounded-full px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-apple-blue"
              />
              <button onClick={handleSend} className="w-9 h-9 bg-apple-blue text-white rounded-full flex items-center justify-center hover:opacity-90 transition-opacity">
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <button 
          onClick={() => setIsOpen(true)}
          className="w-16 h-16 bg-apple-blue text-white rounded-full shadow-2xl flex items-center justify-center hover:scale-105 transition-transform group"
        >
          <MessageCircle size={28} />
          <div className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full border-2 border-white flex items-center justify-center text-[10px] font-bold">1</div>
        </button>
      )}
    </div>
  );
};

export default RAGBubble;
