import React, { useState } from 'react';
import axios from 'axios';

export default function App() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('Idle');

  const onUpload = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setLoading(true);
    setStatus('Indexing Modalities...');
    try {
      await axios.post('http://localhost:8000/upload', formData);
      setStatus('Success: Vector & Graph Synced');
    } catch (e) {
      setStatus('Error Uploading');
    }
    setLoading(false);
  };

  const onChat = async () => {
    if (!query) return;
    setLoading(true);
    const userMsg = { role: 'user', text: query };
    setMessages(prev => [...prev, userMsg]);
    
    try {
      const res = await axios.post('http://localhost:8000/chat', { query });
      setMessages(prev => [...prev, { role: 'ai', text: res.data.answer }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'ai', text: 'Error reaching backend.' }]);
    }
    setQuery('');
    setLoading(false);
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-black text-white">

      {/* Sidebar */}
      <div className="w-72 p-6 flex flex-col backdrop-blur-xl bg-white/5 border-r border-white/10 shadow-xl">
        
        <h1 className="text-2xl font-bold mb-8 bg-gradient-to-r from-orange-400 to-orange-500 bg-clip-text text-transparent">
          GraphRAG v3
        </h1>

        <div className="flex-1 space-y-6">
          
          <div>
            <label className="block text-sm mb-2 text-gray-300">Upload Data</label>

            <input 
              type="file" 
              onChange={(e) => setFile(e.target.files[0])}
              className="block w-full text-sm text-gray-300 
              file:mr-4 file:py-2 file:px-4 
              file:rounded-lg file:border-0 
              file:bg-orange-600 file:text-white 
              hover:file:bg-orange-500 cursor-pointer"
            />

            <button 
              onClick={onUpload}
              disabled={loading}
              className="mt-4 w-full py-2 rounded-lg font-medium 
              bg-gradient-to-r from-orange-600 to-orange-600 
              hover:opacity-90 transition shadow-lg disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Upload'}
            </button>
          </div>

        </div>

        <div className="text-xs mt-6 text-gray-400">
          Status:{" "}
          <span className={`font-medium ${
            status.includes('Error') ? 'text-red-400' : 'text-green-400'
          }`}>
            {status}
          </span>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-20">
              <p className="text-lg">Start chatting </p>
              <p className="text-sm">Ask anything from uploaded documents</p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              
              <div className={`max-w-2xl px-5 py-3 rounded-2xl text-sm shadow-md
                ${m.role === 'user'
                  ? 'bg-gradient-to-r from-orange-600 to-red-600 text-white'
                  : 'bg-white/5 backdrop-blur-md border border-white/10 text-gray-200'
                }`}
              >
                {m.text}
              </div>

            </div>
          ))}
        </div>

        {/* Input */}
        <div className="p-5 border-t border-white/10 backdrop-blur-xl bg-white/5">
          <div className="max-w-4xl mx-auto flex items-center gap-3">

            <input 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onChat()}
              placeholder="Ask a multi-modal query..."
              className="flex-1 px-5 py-3 rounded-xl 
              bg-white/5 border border-white/10 
              focus:outline-none focus:ring-2 focus:ring-red-500 
              placeholder-gray-400"
            />

            <button 
              onClick={onChat}
              disabled={loading}
              className="px-6 py-3 rounded-xl font-semibold 
              bg-gradient-to-r from-orange-600 to-orange-600 
              hover:scale-105 transition-transform shadow-lg disabled:opacity-50"
            >
              Send
            </button>

          </div>
        </div>

      </div>
    </div>
  );
}