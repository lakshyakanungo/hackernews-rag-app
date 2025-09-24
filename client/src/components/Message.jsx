import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { UserIcon, AiIcon } from '../icons';

export const Message = ({ message }) => {
  const isUser = message.sender === 'user';

  return (
    <div className={`flex items-start gap-3 my-4 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && <AiIcon />}
      <div className={`p-3 rounded-xl max-w-2xl shadow-sm ${isUser ? 'bg-blue-500 text-white rounded-br-none' : 'bg-slate-100 text-gray-800 rounded-bl-none'}`}>
        <div className={`prose prose-sm max-w-none ${isUser ? 'prose-invert prose-p:text-white prose-headings:text-white prose-strong:text-white prose-ul:text-white prose-ol:text-white' : ''}`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.text}</p>
          ) : (
            // For AI messages, use ReactMarkdown to process potential formatting.
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                {message.text}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
      {isUser && <UserIcon />}
    </div>
  );
};
