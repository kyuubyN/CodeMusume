import React from 'react';
import { AttributeType } from '../types';
import { Coffee, Flag, Zap, Heart, Flame, Shield, BookOpen } from 'lucide-react';

interface Props {
  energy: number;
  loading: boolean;
  onTrain: (attr: AttributeType) => void;
  onRest: () => void;
  onRace: () => void;
}

export const CommandDeck: React.FC<Props> = ({ energy, loading, onTrain, onRest, onRace }) => {
  // Calculate failure rate based on energy
  const getFailureRate = (attr: AttributeType): number => {
    if (attr === 'wisdom') return 0; // Wisdom study never fails
    if (energy >= 80) return 0;
    if (energy >= 60) return 5;
    if (energy >= 40) return 18;
    if (energy >= 20) return 45;
    return 75;
  };

  const trainOptions: Array<{ type: AttributeType; label: string; icon: React.ReactNode; color: string }> = [
    { type: 'speed', label: 'Speed', icon: <Zap className="w-4 h-4 text-cyan-400" />, color: 'hover:border-cyan-500/80 active:bg-cyan-950/40' },
    { type: 'stamina', label: 'Stamina', icon: <Heart className="w-4 h-4 text-pink-400" />, color: 'hover:border-pink-500/80 active:bg-pink-950/40' },
    { type: 'power', label: 'Power', icon: <Flame className="w-4 h-4 text-amber-400" />, color: 'hover:border-amber-500/80 active:bg-amber-950/40' },
    { type: 'guts', label: 'Guts', icon: <Shield className="w-4 h-4 text-rose-400" />, color: 'hover:border-rose-500/80 active:bg-rose-950/40' },
    { type: 'wisdom', label: 'Wisdom', icon: <BookOpen className="w-4 h-4 text-emerald-400" />, color: 'hover:border-emerald-500/80 active:bg-emerald-950/40' },
  ];

  return (
    <div className="w-full p-2.5 bg-slate-950/90 border-t border-slate-800/80 flex flex-col gap-2">
      {/* Upper Row: 5 Training Buttons */}
      <div className="grid grid-cols-5 gap-1.5">
        {trainOptions.map((opt) => {
          const failRate = getFailureRate(opt.type);
          return (
            <button
              key={opt.type}
              disabled={loading}
              onClick={() => onTrain(opt.type)}
              className={`relative flex flex-col items-center justify-center p-2 rounded-xl bg-slate-900 border border-slate-700/80 shadow-md transition-all duration-150 ${opt.color} disabled:opacity-50 active:scale-95 group`}
            >
              {/* Failure Risk Badge */}
              <span
                className={`absolute -top-1.5 right-1 px-1.5 py-0.2 rounded-full text-[9px] font-black tracking-tight ${
                  failRate === 0
                    ? 'bg-emerald-500 text-emerald-950'
                    : failRate > 30
                    ? 'bg-rose-500 text-white animate-pulse'
                    : 'bg-amber-400 text-amber-950'
                }`}
              >
                {failRate}%
              </span>

              {/* Icon */}
              <div className="mb-0.5 transform transition-transform group-hover:scale-110">
                {opt.icon}
              </div>

              {/* Label */}
              <span className="text-[10px] font-extrabold text-slate-200">
                {opt.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Lower Row: Rest Button & URA Derby Button */}
      <div className="grid grid-cols-2 gap-2">
        {/* Rest Button */}
        <button
          disabled={loading}
          onClick={onRest}
          className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 border border-blue-400/40 shadow-md text-white font-extrabold text-xs transition-all active:scale-95 disabled:opacity-50"
        >
          <Coffee className="w-4 h-4 text-blue-200" />
          <span>DESCANSAR (+HP)</span>
        </button>

        {/* URA Derby Race Button */}
        <button
          disabled={loading}
          onClick={onRace}
          className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-gradient-to-r from-amber-500 via-yellow-400 to-orange-500 hover:from-amber-400 hover:to-orange-400 border border-yellow-200 text-amber-950 font-black text-xs shadow-[0_0_20px_rgba(245,158,11,0.4)] transition-all active:scale-95 animate-pulse"
        >
          <Flag className="w-4 h-4 text-amber-950 fill-amber-950" />
          <span>URA DERBY (2000m)</span>
        </button>
      </div>
    </div>
  );
};
