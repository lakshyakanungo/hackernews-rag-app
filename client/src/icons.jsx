import { Send, CircleUserRound, Bot } from 'lucide-react';

export const SendIcon = () => (
  <Send size={20} />
);

export const UserIcon = () => (
  <div className="w-8 h-8 rounded-full bg-blue-400 flex-shrink-0 flex items-center justify-center">
    <CircleUserRound size={20} className="text-white" />
  </div>
);

export const AiIcon = () => (
  <div className="w-8 h-8 rounded-full bg-slate-700 flex-shrink-0 flex items-center justify-center">
    <Bot size={20} className="text-white" />
  </div>
);
