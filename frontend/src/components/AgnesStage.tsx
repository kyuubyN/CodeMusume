import React from 'react';
import { AvatarPose, MoodState } from '../types';

interface Props {
  pose: AvatarPose;
  mood: MoodState;
}

export const AgnesStage: React.FC<Props> = ({ pose, mood }) => {
  const avatarPath = `/avatars/${pose}.png`;

  // Flow aura / glows based on mood
  const getAuraEffect = () => {
    if (mood === 'great') return 'ring-4 ring-yellow-400/50 shadow-[0_0_40px_rgba(250,204,21,0.35)]';
    if (mood === 'good') return 'ring-2 ring-emerald-400/40 shadow-[0_0_25px_rgba(52,211,153,0.25)]';
    if (mood === 'terrible') return 'grayscale contrast-125 ring-2 ring-rose-500/40';
    return '';
  };

  return (
    <div className="relative w-full h-72 flex items-end justify-center overflow-hidden">
      {/* Background Lab Glow */}
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-indigo-950/20 to-transparent pointer-events-none" />
      <div className="absolute w-64 h-64 rounded-full bg-cyan-500/10 blur-3xl -top-10 pointer-events-none" />

      {/* Chemical Bubbles / Flow Particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute bottom-10 left-12 w-2 h-2 rounded-full bg-cyan-400/60 animate-ping" />
        <div className="absolute bottom-24 right-16 w-3 h-3 rounded-full bg-pink-400/50 animate-bounce" />
        <div className="absolute bottom-16 left-1/4 w-1.5 h-1.5 rounded-full bg-yellow-400/70 animate-pulse" />
      </div>

      {/* Agnes Tachyon Character Sprite */}
      <div className="relative z-10 w-64 h-72 flex items-end justify-center transition-transform duration-300 hover:scale-105">
        <img
          src={avatarPath}
          alt={`Agnes Tachyon (${pose})`}
          className={`h-full w-auto object-contain drop-shadow-[0_12px_24px_rgba(0,0,0,0.8)] rounded-2xl transition-all duration-300 ${getAuraEffect()}`}
          onError={(e) => {
            // Fallback to idle if specific pose image fails to load
            (e.target as HTMLImageElement).src = '/avatars/idle.png';
          }}
        />
      </div>

      {/* Status Badge overlay */}
      <div className="absolute top-2 right-3 z-10 bg-slate-900/80 border border-slate-700/80 px-2 py-0.5 rounded text-[10px] text-cyan-300 font-bold backdrop-blur-sm">
        Dr. Agnes Tachyon
      </div>
    </div>
  );
};
