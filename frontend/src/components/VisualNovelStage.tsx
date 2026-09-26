import React from 'react';

interface Props {
  children: React.ReactNode;
  backgroundImage: string;
  isRace?: boolean;
}

export const VisualNovelStage: React.FC<Props> = ({
  children,
  backgroundImage,
  isRace = false,
}) => {
  return (
    <div className="relative w-screen h-screen overflow-hidden bg-[#07090c] flex flex-col justify-between select-none">
      {/* Background Image Layer (100% Fullscreen Viewport) */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none select-none z-0">
        <img
          src={backgroundImage}
          alt="Visual Novel Background"
          className={`w-full h-full object-cover ${
            isRace ? 'brightness-105' : 'brightness-90'
          }`}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />

        {/* Tactical Dark Gradients & Vignette */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#080a0e]/85 via-transparent to-[#080a0e]/70 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#080a0e]/40 via-transparent to-[#080a0e]/40 pointer-events-none" />

        {/* Arknights Endfield Style Technical Grid Overlay — static, will-change: auto */}
        <div
          className="absolute inset-0 pointer-events-none opacity-20"
          style={{
            backgroundImage:
              'linear-gradient(to right, rgba(255, 255, 255, 0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.08) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
            willChange: 'auto',
          }}
        />

        {/* Technical Corner Telemetry Markers */}
        <div className="absolute top-2 left-3 font-mono text-[9px] tracking-widest text-[#7b8594] pointer-events-none flex items-center gap-2">
          <span className="text-[#f5a623] font-bold">+</span>
          <span>SYS.TELEMETRY // ENDFIELD-SYS</span>
          <span className="opacity-40">|</span>
          <span>SEC.04 // LAB-ROOM</span>
        </div>
        <div className="absolute top-2 right-3 font-mono text-[9px] tracking-widest text-[#7b8594] pointer-events-none flex items-center gap-2">
          <span>OPERATIONAL MATRIX: OPTIMAL</span>
          <span className="text-[#f5a623] font-bold">+</span>
        </div>
        <div className="absolute bottom-1 left-3 font-mono text-[8px] tracking-widest text-[#4b5563] pointer-events-none">
          +---+ ENGINELINK // PROTOCOL 2.0 // DEEPSEEK-V4.1-FLASH
        </div>
      </div>

      {/* Main Viewport Content Layers */}
      <div className="relative z-10 w-full h-full flex flex-col justify-between overflow-hidden select-none">
        {children}
      </div>
    </div>
  );
};
