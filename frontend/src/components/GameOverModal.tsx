import React from 'react';
import { GameState } from '../types';
import { Trophy, RotateCcw } from 'lucide-react';

interface Props {
  state: GameState;
  onRestart: () => void;
}

export const GameOverModal: React.FC<Props> = ({ state, onRestart }) => {
  const totalScore =
    state.attributes.speed +
    state.attributes.stamina +
    state.attributes.power +
    state.attributes.guts +
    state.attributes.wisdom;

  const getOverallRank = (score: number) => {
    if (score >= 4500) return 'SS (Legendary Enterprise)';
    if (score >= 3800) return 'S (Enterprise Master)';
    if (score >= 3000) return 'A (Production Grade)';
    if (score >= 2200) return 'B (Staging Ready)';
    if (score >= 1500) return 'C (Moderate Technical Debt)';
    return 'D (Spaghetti Architecture - Surgery Needed)';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 animate-fade-in select-none" style={{ contain: 'layout paint' }}>
      <div className="w-full max-w-md bg-gradient-to-b from-slate-900 to-indigo-950 border-2 border-amber-400/80 rounded-3xl p-6 shadow-[0_0_60px_rgba(245,158,11,0.35)] flex flex-col gap-3.5 text-slate-100 text-center">
        {/* Trophy Header */}
        <div className="flex items-center flex-col justify-center">
          <div className="p-3 rounded-full bg-amber-400/20 border border-amber-300/40 text-amber-300 mb-1">
            <Trophy className="w-8 h-8 fill-amber-300" />
          </div>
          <span className="text-[10px] uppercase font-black text-amber-400 tracking-widest">
            Repository Graduation
          </span>
          <h2 className="text-lg font-black text-white">
            {state.repo_name}
          </h2>
        </div>

        {/* Overall Rank Box */}
        <div className="bg-slate-950/80 rounded-2xl border border-slate-700/80 p-3 shadow-inner">
          <span className="text-[10px] font-bold text-slate-400 block mb-0.5">
            Final Architectural Classification:
          </span>
          <div className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-pink-400 to-cyan-300">
            {getOverallRank(totalScore)}
          </div>
          <span className="text-xs text-slate-300 font-bold tabular-nums">
            Total Score: {totalScore} pts
          </span>
        </div>

        {/* Final Stat Highlights */}
        <div className="grid grid-cols-5 gap-1 text-[11px] font-black bg-slate-900/80 p-2 rounded-xl border border-slate-800">
          <div>⚡ {state.attributes.speed}</div>
          <div>❤️ {state.attributes.stamina}</div>
          <div>💥 {state.attributes.power}</div>
          <div>🛡️ {state.attributes.guts}</div>
          <div>📖 {state.attributes.wisdom}</div>
        </div>

        {/* Agnes Final Verdict */}
        <p className="text-xs text-cyan-200 italic px-2">
          "Kukuku... The grand computational experiment is a triumph, Morumotto-kun! Our architectural remedies have stabilized the specimen's genome."
        </p>

        {/* Restart Button */}
        <button
          onClick={onRestart}
          className="w-full mt-2 py-3 rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-300 hover:to-orange-400 text-slate-950 font-black text-xs shadow-lg transition-all active:scale-95 flex items-center justify-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          <span>START NEW TRAINING CYCLE</span>
        </button>
      </div>
    </div>
  );
};
