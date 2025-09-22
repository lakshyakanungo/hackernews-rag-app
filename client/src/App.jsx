import React, { useState, useEffect, useRef } from 'react';
import { Message } from './components/Message';
import { SendIcon, AiIcon } from './icons.jsx';

// --- Main App Component ---
function App() {
  const [messages, setMessages] = useState([
    { sender: 'ai', text: 'Ask me anything about the latest Hacker News articles!' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);

  const messagesEndRef = useRef(null);
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000/api/v1/chat/stream";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const url = `${API_URL}?query=${encodeURIComponent(input)}${conversationId ? `&conversation_id=${conversationId}` : ''}`;
    const eventSource = new EventSource(url);

    let aiMessage = null;
    let firstChunk = true;

    eventSource.onmessage = (event) => {
      console.log(event, "event");
      try {
        const data = JSON.parse(event.data);
        if (data.done) {
          if (data.conversation_id) setConversationId(data.conversation_id);
          setIsLoading(false);
          eventSource.close();
        }
      } catch {
        // Partial text chunk
        if (firstChunk) {
          // Hide loader immediately
          setIsLoading(false);
          firstChunk = false;

          // First chunk → create AI message
          aiMessage = { sender: 'ai', text: event.data.replace(/\[NL]/g, '\n') };
          setMessages((prev) => [...prev, aiMessage]);
        } else {
          // Subsequent chunks → update AI message
          aiMessage = { ...aiMessage, text: aiMessage.text + event.data.replace(/\[NL]/g, '\n') };
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = aiMessage;
            return updated;
          });
        }
      }
    };

    eventSource.onerror = () => {
      console.error("Stream error");
      eventSource.close();
      let aiMessage = { sender: 'ai', text: "There was an error getting the response." };
      setMessages((prev) => [...prev, aiMessage]);
      setIsLoading(false);
    };
  };

  return (
    <div className="bg-gray-100 font-sans flex flex-col h-screen">
      <header className="bg-orange-500 text-white p-4 text-center shadow-md">
        <h1 className="text-2xl font-bold">HN RAG Chat</h1>
        <p className="text-sm">Your AI assistant for Hacker News</p>
      </header>

      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-4xl mx-auto">
          {messages.map((msg, index) => (
            <Message key={index} message={msg} />
          ))}
          {isLoading && (
            <div className="flex items-start gap-3 my-4">
              <AiIcon />
              <div className="p-3 rounded-lg bg-gray-200 text-gray-500 rounded-bl-none animate-pulse">
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <footer className="bg-white border-t border-gray-200 p-4">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              className="flex-1 p-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-orange-400 transition"
              disabled={isLoading}
            />
            <button
              type="submit"
              className="bg-orange-500 p-3 rounded-full hover:bg-orange-600 disabled:bg-gray-400 transition-colors duration-200 flex items-center justify-center"
              disabled={isLoading}
            >
              <SendIcon />
            </button>
          </form>
        </div>
      </footer>
    </div>
  );
}

export default App;
