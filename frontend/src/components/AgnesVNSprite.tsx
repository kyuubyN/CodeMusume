import React from 'react';
import { AvatarPose, MoodState } from '../types';

interface Props {
  pose: AvatarPose;
  mood: MoodState;
  onClick?: () => void;
}

export const AgnesVNSprite: React.FC<Props> = ({ pose, mood, onClick }) => {
  // If pose is normal idle but mood is great, we can choose flow sprite
  const resolvedPose = (mood === 'great' && pose === 'idle') ? 'flow' : pose;
  const avatarSrc = `/avatars/${resolvedPose}.png`;

  // Static, GPU-cheap shadow based on mood/pose — no blur animations
  const getSpriteStyle = (): React.CSSProperties => {
    if (resolvedPose === 'flow' || mood === 'great') {
      return { filter: 'drop-shadow(0 10px 20px rgba(6,182,212,0.45)) drop-shadow(0 0 8px rgba(236,72,153,0.25))' };
    }
    if (mood === 'good') {
      return { filter: 'drop-shadow(0 10px 18px rgba(52,211,153,0.35))' };
    }
    if (mood === 'terrible') {
      return { filter: 'grayscale(0.4) brightness(0.9) drop-shadow(0 8px 16px rgba(244,63,94,0.25))' };
    }
    return { filter: 'drop-shadow(0 15px 30px rgba(0,0,0,0.7))' };
  };

  return (
    <div className="absolute inset-0 pointer-events-none flex items-end justify-center z-10">
      {/* Main Character Sprite — interactive clickable sprite */}
      <div
        onClick={onClick}
        title="Interact with Dr. Agnes Tachyon"
        className={`relative h-[82%] max-h-[680px] flex items-end justify-center transition-all duration-300 pointer-events-auto ${
          onClick ? 'cursor-pointer hover:scale-[1.01] active:scale-95 group' : ''
        }`}
      >
        <img
          src={avatarSrc}
          alt={`Dr. Agnes Tachyon (${resolvedPose})`}
          decoding="async"
          loading="eager"
          className="h-full w-auto object-contain transition-all duration-300 pointer-events-auto select-none group-hover:brightness-105"
          style={getSpriteStyle()}
          onError={(e) => {
            (e.target as HTMLImageElement).src = '/avatars/idle.png';
          }}
        />

        {/* Flow Mode Japanese Badge — static, no animate-bounce */}
        {resolvedPose === 'flow' && (
          <div className="absolute top-10 right-4 px-3 py-1 rounded-full bg-gradient-to-r from-pink-500 via-rose-500 to-amber-500 text-white font-black text-xs border border-pink-200 shadow-lg">
            ⚡ ZONE: HYPER FOCUS
          </div>
        )}

        {/* Subtle click hint badge on hover */}
        {onClick && (
          <div className="absolute bottom-6 opacity-0 group-hover:opacity-100 transition-opacity bg-black/80 backdrop-blur-sm text-[#ffd000] text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full border border-[#ffd000]/50 pointer-events-none shadow-md">
            [CLICK TO INTERACT]
          </div>
        )}
      </div>
    </div>
  );
};
