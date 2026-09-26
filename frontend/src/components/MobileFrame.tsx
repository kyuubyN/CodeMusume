import React from 'react';

interface Props {
  children: React.ReactNode;
}

export const MobileFrame: React.FC<Props> = ({ children }) => {
  return (
    <div className="relative w-full max-w-[430px] min-h-[820px] max-h-[920px] bg-slate-950 rounded-[44px] border-[6px] border-slate-700/80 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9),0_0_50px_rgba(59,130,246,0.15)] overflow-hidden flex flex-col justify-between my-4 ring-1 ring-slate-600/50">
      {/* Top Phone Camera / Speaker Notch */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-36 h-4 bg-slate-800 rounded-b-xl z-30 flex items-center justify-center">
        <div className="w-10 h-1 rounded-full bg-slate-700" />
      </div>

      {/* Screen Content */}
      <div className="relative w-full flex-1 flex flex-col overflow-y-auto overflow-x-hidden pt-3 scrollbar-none">
        {children}
      </div>

      {/* Bottom Phone Home Indicator Bar */}
      <div className="w-full h-3 bg-slate-950 flex items-center justify-center pb-1 z-30">
        <div className="w-24 h-1 bg-slate-600 rounded-full" />
      </div>
    </div>
  );
};
