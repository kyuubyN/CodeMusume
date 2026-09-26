import React from 'react';
import { GameState, MoodState } from '../types';
import { Sparkles, Zap } from 'lucide-react';

interface Props {
  state: GameState;
}

const MOOD_DATA: Record<MoodState, { label: string; kanji: string; color: string; border: string }> = {
  great: { label: 'Excelente', kanji: '絶好調', color: 'from-amber-400 to-yellow-500 text-amber-950', border: 'border-yellow-300' },
  good: { label: 'Bom', kanji: '好調', color: 'from-emerald-400 to-green-500 text-emerald-950', border: 'border-green-300' },
  normal: { label: 'Normal', kanji: '普通', color: 'from-blue-400 to-indigo-500 text-blue-950', border: 'border-blue-300' },
  poor: { label: 'Ruim', kanji: '不調', color: 'from-purple-400 to-purple-600 text-purple-950', border: 'border-purple-300' },
  terrible: { label: 'Péssimo', kanji: '絶不調', color: 'from-rose-500 to-red-700 text-white', border: 'border-red-400' },
};

export const TopStatusBar: React.FC<Props> = ({ state }) => {
  const mood = MOOD_DATA[state.mood] || MOOD_DATA.normal;

  // Energy color scale: green (>60), yellow (30-60), red (<30)
  const getEnergyColor = (val: number) => {
    if (val >= 60) return 'bg-gradient-to-r from-emerald-400 to-green-500';
    if (val >= 35) return 'bg-gradient-to-r from-yellow-400 to-amber-500';
    return 'bg-gradient-to-r from-rose-500 to-red-600 animate-pulse';
  };

  return (
    <div className="w-full bg-slate-900/90 backdrop-blur-md border-b border-slate-700/60 p-3 flex flex-col gap-2 z-20 shadow-lg">
      {/* Top Row: Date, Turn Counter & Mood Pill */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="bg-slate-800 text-slate-300 text-[10px] font-bold px-2 py-0.5 rounded border border-slate-700">
            Sprint 1
          </span>
          <span className="text-xs font-black text-amber-300 tracking-wider">
            TURNO {state.turn}/{state.max_turns}
          </span>
        </div>

        {/* Mood Pill */}
        <div className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-gradient-to-r ${mood.color} ${mood.border} border shadow-sm font-extrabold text-[11px]`}>
          <Sparkles className="w-3 h-3" />
          <span>{mood.kanji}</span>
          <span className="text-[10px] opacity-80">({mood.label})</span>
        </div>
      </div>

      {/* Energy Bar (HP) */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 text-[11px] font-black text-slate-300 w-12">
          <Zap className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
          <span>HP</span>
        </div>
        <div className="flex-1 bg-slate-950 h-3.5 rounded-full overflow-hidden p-0.5 border border-slate-700/80 shadow-inner">
          <div
            className={`h-full rounded-full transition-all duration-500 ${getEnergyColor(state.energy)}`}
            style={{ width: `${Math.max(0, Math.min(100, state.energy))}%` }}
          />
        </div>
        <span className="text-xs font-black text-slate-200 tabular-nums w-8 text-right">
          {state.energy}%
        </span>
      </div>
    </div>
  );
};
