import React, { useState, useEffect, useRef } from 'react';

// --- Helper Components ---

// Icon for the Send button
const SendIcon = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className="text-white"
  >
    <path
      d="M2.01 21L23 12L2.01 3L2 10L17 12L2 14L2.01 21Z"
      fill="currentColor"
    />
  </svg>
);

// Icon for the User message bubble
const UserIcon = () => (
  <div className="w-8 h-8 rounded-full bg-blue-500 flex-shrink-0 flex items-center justify-center text-white font-bold">
    You
  </div>
);

// Icon for the AI message bubble
const AiIcon = () => (
  <div className="w-8 h-8 rounded-full bg-gray-700 flex-shrink-0 flex items-center justify-center">
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-white"
    >
      <path
        d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"
        fill="currentColor"
      />
      <path
        d="M12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.65 0-3 1.35-3 3s1.35 3 3 3 3-1.35 3-3-1.35-3-3-3z"
        fill="currentColor"
      />
    </svg>
  </div>
);

// Component for a single chat message
const Message = ({ message }) => {
  const isUser = message.sender === 'user';
  return (
    <div className={`flex items-start gap-3 my-4 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && <AiIcon />}
      <div
        className={`p-3 rounded-lg max-w-lg ${
          isUser
            ? 'bg-blue-500 text-white rounded-br-none'
            : 'bg-gray-200 text-gray-800 rounded-bl-none'
        }`}
      >
        {/* Handle newlines in the response text */}
        {message.text.split('\n').map((line, index) => (
          <p key={index} className={line.trim() === '' ? 'h-4' : ''}>{line}</p>
        ))}
      </div>
      {isUser && <UserIcon />}
    </div>
  );
};


// --- Main App Component ---

function App() {
  // State to hold the list of messages in the chat
  const [messages, setMessages] = useState([
    { sender: 'ai', text: 'Ask me anything about the latest Hacker News articles!' }
  ]);
  // State for the user's current input
  const [input, setInput] = useState('');
  // State to track if the AI is currently "thinking"
  const [isLoading, setIsLoading] = useState(false);

  // Ref for the end of the messages list to enable auto-scrolling
  const messagesEndRef = useRef(null);

  // The URL of your Rails API backend
  const API_URL = 'http://localhost:3000/api/v1/chat';

  // Function to automatically scroll to the latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // useEffect hook to scroll whenever new messages are added
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Function to handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: input }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const data = await response.json();
      const aiMessage = { sender: 'ai', text: data.answer || "Sorry, I couldn't get a response." };
      setMessages((prev) => [...prev, aiMessage]);

    } catch (error) {
      console.error("Failed to fetch from API:", error);
      const errorMessage = { sender: 'ai', text: `Sorry, something went wrong. ${error.message}` };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-gray-100 font-sans flex flex-col h-screen">
      {/* Header */}
      <header className="bg-orange-500 text-white p-4 text-center shadow-md">
        <h1 className="text-2xl font-bold">HN RAG Chat</h1>
        <p className="text-sm">Your AI assistant for Hacker News</p>
      </header>

      {/* Chat Window */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-4xl mx-auto">
          {messages.map((msg, index) => (
            <Message key={index} message={msg} />
          ))}
          {/* Show a "thinking" message while loading */}
          {isLoading && (
            <div className="flex items-start gap-3 my-4">
              <AiIcon />
              <div className="p-3 rounded-lg bg-gray-200 text-gray-500 rounded-bl-none animate-pulse">
                Thinking...
              </div>
            </div>
          )}
          {/* This empty div is the target for auto-scrolling */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Form */}
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
