import React from 'react';
import { X, MessageSquare, Terminal } from 'lucide-react';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agnes';
  text: string;
  timestamp: string;
}

interface Props {
  messages: ChatMessage[];
  onClose: () => void;
}

export const CommsLogModal: React.FC<Props> = ({ messages, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/92 animate-fade-in font-mono select-none" style={{ contain: 'layout paint' }}>
      <div className="relative w-full max-w-2xl bg-[#0c0f16] border-2 border-white/20 rounded-2xl p-5 shadow-[0_0_60px_rgba(0,0,0,0.9)] flex flex-col gap-3 text-[#f0f3f6] max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-[#ffd000]/10 border border-[#ffd000]/40 text-[#ffd000]">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] tracking-widest text-[#7b8594] uppercase block">
                COMMS TERMINAL // DEEPSEEK-V4.1 SYNAPSE
              </span>
              <h2 className="text-sm font-black tracking-wider text-[#ffd000] uppercase">
                TRANSMISSION HISTORY // DR. AGNES TACHYON
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded bg-[#161b24] hover:bg-[#202734] text-[#7b8594] hover:text-white border border-white/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Message Log Feed */}
        <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3 min-h-[300px] max-h-[500px]">
          {messages.length === 0 ? (
            <div className="m-auto text-center text-xs text-[#7b8594] py-12 flex flex-col items-center gap-2">
              <Terminal className="w-6 h-6 opacity-40" />
              <span>NO TRANSMISSIONS LOGGED IN THIS SESSION.</span>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col gap-1 p-3 rounded-xl border ${
                  msg.sender === 'user'
                    ? 'bg-[#121824] border-[#00f0ff]/30 ml-8 text-left'
                    : 'bg-[#141720] border-[#ffd000]/30 mr-8 text-left'
                }`}
              >
                <div className="flex items-center justify-between text-[10px] tracking-widest">
                  <span
                    className={`font-black uppercase ${
                      msg.sender === 'user' ? 'text-[#00f0ff]' : 'text-[#ffd000]'
                    }`}
                  >
                    {msg.sender === 'user' ? 'OPERATOR // TRAINER' : 'DR. AGNES TACHYON'}
                  </span>
                  <span className="text-[#556070] font-sans">{msg.timestamp}</span>
                </div>
                <p className="text-xs md:text-sm text-[#e5e9f0] leading-relaxed font-sans font-medium">
                  {msg.text}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-white/10 pt-2 text-[10px] text-[#7b8594]">
          <span>TOTAL TRANSMISSIONS: {messages.length}</span>
          <button
            onClick={onClose}
            className="py-1 px-4 rounded bg-[#161a24] hover:bg-[#202634] border border-white/10 text-white font-bold"
          >
            CLOSE
          </button>
        </div>
      </div>
    </div>
  );
};
