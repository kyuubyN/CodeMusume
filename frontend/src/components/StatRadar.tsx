import React from 'react';
import { AttributeScores, StatRank } from '../types';

interface Props {
  attributes: AttributeScores;
}

const getRank = (score: number): StatRank => {
  if (score >= 1150) return 'SS';
  if (score >= 1000) return 'S';
  if (score >= 800) return 'A';
  if (score >= 700) return 'B';
  if (score >= 600) return 'C';
  if (score >= 500) return 'D';
  if (score >= 400) return 'E';
  if (score >= 200) return 'F';
  return 'G';
};

const RANK_BADGES: Record<StatRank, { bg: string; text: string; ring: string }> = {
  SS: { bg: 'bg-gradient-to-r from-amber-400 via-pink-500 to-cyan-400', text: 'text-white', ring: 'ring-pink-300' },
  S: { bg: 'bg-gradient-to-r from-amber-300 to-yellow-500', text: 'text-amber-950', ring: 'ring-amber-300' },
  A: { bg: 'bg-gradient-to-r from-pink-400 to-rose-500', text: 'text-white', ring: 'ring-rose-300' },
  B: { bg: 'bg-gradient-to-r from-orange-400 to-amber-500', text: 'text-orange-950', ring: 'ring-orange-300' },
  C: { bg: 'bg-gradient-to-r from-yellow-300 to-yellow-500', text: 'text-yellow-950', ring: 'ring-yellow-200' },
  D: { bg: 'bg-gradient-to-r from-emerald-400 to-green-500', text: 'text-emerald-950', ring: 'ring-emerald-300' },
  E: { bg: 'bg-gradient-to-r from-sky-400 to-blue-500', text: 'text-blue-950', ring: 'ring-blue-300' },
  F: { bg: 'bg-gradient-to-r from-violet-400 to-purple-500', text: 'text-white', ring: 'ring-purple-300' },
  G: { bg: 'bg-slate-600', text: 'text-slate-200', ring: 'ring-slate-500' },
};

export const StatRadar: React.FC<Props> = ({ attributes }) => {
  const stats = [
    { key: 'speed', label: 'VEL', icon: '⚡', score: attributes.speed },
    { key: 'stamina', label: 'STA', icon: '❤️', score: attributes.stamina },
    { key: 'power', label: 'POW', icon: '💥', score: attributes.power },
    { key: 'guts', label: 'GUT', icon: '🛡️', score: attributes.guts },
    { key: 'wisdom', label: 'WIS', icon: '📖', score: attributes.wisdom },
  ];

  return (
    <div className="w-full px-3 py-2 bg-slate-900/95 border-y border-slate-800/80 backdrop-blur-md">
      <div className="grid grid-cols-5 gap-1.5">
        {stats.map((item) => {
          const rank = getRank(item.score);
          const badge = RANK_BADGES[rank];
          return (
            <div
              key={item.key}
              className="flex flex-col items-center bg-slate-950/70 border border-slate-800 rounded-lg p-1.5 transition-transform hover:scale-105 shadow-sm"
            >
              {/* Header: Icon + Label */}
              <div className="flex items-center gap-0.5 text-[10px] font-black text-slate-400">
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </div>

              {/* Rank Pill */}
              <div className={`mt-0.5 px-2 py-0.5 rounded-full text-[10px] font-black tracking-tighter ${badge.bg} ${badge.text} shadow-sm ring-1 ${badge.ring}`}>
                {rank}
              </div>

              {/* Score Value */}
              <div className="mt-1 text-xs font-black text-slate-100 tabular-nums">
                {item.score}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
