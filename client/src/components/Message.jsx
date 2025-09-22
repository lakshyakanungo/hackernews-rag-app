import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { UserIcon, AiIcon } from '../icons';

export const  Message = ({ message }) => {
  const isUser = message.sender === 'user';

  return (
    <div className={`flex items-start gap-3 my-4 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && <AiIcon />}
      <div className={`p-3 rounded-lg max-w-lg ${isUser ? 'bg-blue-500 text-white rounded-br-none' : 'bg-gray-200 text-gray-800 rounded-bl-none'}`}>
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkBreaks]}
          >
            {message.text}
          </ReactMarkdown>
        </div>
      </div>
      {isUser && <UserIcon />}
    </div>
  );
};
