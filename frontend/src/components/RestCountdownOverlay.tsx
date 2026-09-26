import React, { useState, useEffect } from 'react';
import { Coffee, BatteryCharging } from 'lucide-react';
import { sounds } from '../services/audio';

interface Props {
  initialEnergy: number;
  onComplete: () => void;
  onInstantSkip?: () => void;
}

export const RestCountdownOverlay: React.FC<Props> = ({
  initialEnergy,
  onComplete,
  onInstantSkip,
}) => {
  const TOTAL_SECONDS = 60;
  const [secondsRemaining, setSecondsRemaining] = useState(TOTAL_SECONDS);
  const [simulatedEnergy, setSimulatedEnergy] = useState(initialEnergy);

  useEffect(() => {
    sounds.playClick();
    const interval = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          sounds.playSuccess();
          onComplete();
          return 0;
        }

        const nextSec = prev - 1;
        // Progressively restore energy over 60 seconds up to 100%
        const elapsed = TOTAL_SECONDS - nextSec;
        const restored = Math.min(100, Math.round(initialEnergy + ((100 - initialEnergy) * (elapsed / TOTAL_SECONDS))));
        setSimulatedEnergy(restored);

        return nextSec;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [initialEnergy, onComplete]);

  const progressPercent = Math.round(((TOTAL_SECONDS - secondsRemaining) / TOTAL_SECONDS) * 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/95 animate-fade-in font-mono select-none" style={{ contain: 'layout paint' }}>
      <div className="relative w-full max-w-lg bg-[#0d1017] border-2 border-[#00f0ff] rounded-2xl p-6 shadow-[0_0_80px_rgba(0,240,255,0.3)] flex flex-col items-center text-center gap-5 text-[#f0f3f6]">
        {/* Steaming Coffee / Battery Icon */}
        <div className="relative flex items-center justify-center w-24 h-24 rounded-full bg-[#121824] border-2 border-[#00f0ff] shadow-[0_0_30px_rgba(0,240,255,0.4)]">
          <Coffee className="w-10 h-10 text-[#00f0ff] animate-bounce" />
          <div className="absolute -top-2 text-xs animate-ping">☕</div>
        </div>

        {/* Title */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] tracking-widest text-[#00f0ff] uppercase font-black">
            PROTOCOLO DE RECARGA SINÁPTICA // DESCANSO (60s)
          </span>
          <h2 className="text-xl font-black tracking-wide text-white">
            AGNES EM PAUSA PARA CAFÉ & RECARGA
          </h2>
          <p className="text-xs text-[#7b8594] font-sans">
            A energia está sendo restaurada progressivamente para calibrar os circuitos neurais.
          </p>
        </div>

        {/* Large Countdown Clock */}
        <div className="flex items-center justify-center px-6 py-3 rounded-xl bg-[#141a26] border border-[#00f0ff]/40 shadow-inner">
          <span className="text-3xl md:text-4xl font-black font-mono tracking-widest text-[#ffd000] tabular-nums">
            00:{String(secondsRemaining).padStart(2, '0')}
          </span>
        </div>

        {/* Restoring Energy Bar */}
        <div className="w-full flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs text-[#a0aec0]">
            <span className="flex items-center gap-1 font-bold text-[#00f0ff]">
              <BatteryCharging className="w-4 h-4" />
              ENERGIA RESTAURANDO:
            </span>
            <span className="font-mono font-bold text-white tabular-nums">
              {simulatedEnergy}% / 100%
            </span>
          </div>

          <div className="w-full h-3 rounded-full bg-[#161c28] border border-white/10 p-0.5 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#00f0ff] via-cyan-400 to-emerald-400 transition-all duration-1000 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Instant Skip Button for testing / dev convenience */}
        {onInstantSkip && (
          <button
            onClick={() => {
              sounds.playClick();
              onInstantSkip();
            }}
            className="text-[10px] text-[#7b8594] hover:text-[#ffd000] tracking-wider uppercase underline transition-colors pt-2"
          >
            [PULAR ESPERA DE 60s // RESTAURAR INSTANTANEAMENTE]
          </button>
        )}
      </div>
    </div>
  );
};
