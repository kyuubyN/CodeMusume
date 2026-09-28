import React, { useEffect, useRef, useState } from 'react';
import type { AvatarPose, MoodState } from '../types';
import type { VoiceStatus } from '../services/voiceAgent';

interface Props {
  pose: AvatarPose;
  mood: MoodState;
  status: VoiceStatus;
  /** Agnes's live voice level 0..1 (drives the talking motion). */
  getLevel: () => number;
  onPoke?: () => void;
  /** Extra HUD tag, e.g. "Eureka x1.5". */
  flag?: string | null;
}

const POSES: AvatarPose[] = ['idle', 'thinking', 'shocked', 'happy', 'serious', 'tired', 'flow', 'crazy'];

const STATUS_TAG: Record<VoiceStatus, string> = {
  idle: 'Standby',
  connecting: 'Linking',
  listening: 'Listening',
  user_speaking: 'Receiving',
  thinking: 'Analyzing',
  speaking: 'Speaking',
  error: 'Link error',
};

const POSE_TAG: Record<AvatarPose, string> = {
  idle: 'observing',
  thinking: 'hypothesizing',
  shocked: 'anomaly detected',
  happy: 'result confirmed',
  serious: 'diagnosis',
  tired: 'low energy',
  flow: 'in the zone',
  crazy: 'fascinated',
};

// Preload every pose once so crossfades never flash.
if (typeof window !== 'undefined') {
  POSES.forEach((p) => {
    const img = new Image();
    img.src = `/avatars/${p}.png`;
  });
}

export const AgnesAvatar: React.FC<Props> = ({ pose, mood, status, getLevel, onPoke, flag }) => {
  const resolved: AvatarPose = mood === 'great' && pose === 'idle' ? 'flow' : pose;
  const [layers, setLayers] = useState<{ cur: AvatarPose; prev: AvatarPose | null }>({ cur: resolved, prev: null });
  const [poked, setPoked] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef(status);
  statusRef.current = status;
  const levelRef = useRef(getLevel);
  levelRef.current = getLevel;

  useEffect(() => {
    setLayers((l) => (l.cur === resolved ? l : { cur: resolved, prev: l.cur }));
    const t = window.setTimeout(() => setLayers((l) => ({ ...l, prev: null })), 320);
    return () => window.clearTimeout(t);
  }, [resolved]);

  // Motion loop: transforms only, no React re-renders.
  useEffect(() => {
    let raf = 0;
    let smooth = 0;
    const tick = (ms: number) => {
      const t = ms / 1000;
      const s = statusRef.current;
      const raw = s === 'speaking' ? levelRef.current() : 0;
      smooth += (raw - smooth) * (raw > smooth ? 0.45 : 0.12);

      let y = Math.sin(t * 1.7) * 1.5; // breathing
      let rot = 0;
      let scale = 1 + Math.sin(t * 1.7) * 0.004;
      if (s === 'speaking') {
        y -= smooth * 12;
        scale += smooth * 0.018;
        rot = Math.sin(t * 5.5) * smooth * 1.4;
      } else if (s === 'listening') {
        rot = -1.1 + Math.sin(t * 0.9) * 0.3;
      } else if (s === 'user_speaking') {
        rot = -1.8;
        y -= 3;
      } else if (s === 'thinking') {
        rot = Math.sin(t * 1.3) * 1.2;
      }
      if (bodyRef.current) {
        bodyRef.current.style.transform = `translateY(${y.toFixed(2)}px) rotate(${rot.toFixed(3)}deg) scale(${scale.toFixed(4)})`;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const poke = () => {
    setPoked(true);
    window.setTimeout(() => setPoked(false), 260);
    onPoke?.();
  };

  const live = status !== 'idle' && status !== 'error';

  return (
    <div className="pointer-events-none relative flex h-full w-full items-end justify-center">
      {/* Floor line + shadow */}
      <div className="absolute bottom-[2%] left-1/2 h-px w-[46%] -translate-x-1/2 bg-paper/15" />
      <div className="absolute bottom-[1.5%] left-1/2 h-4 w-[22%] -translate-x-1/2 rounded-[50%] bg-black/50 blur-md" />

      <div className="relative aspect-[2/3] h-full max-h-full" style={{ transformOrigin: '50% 100%' }}>
        {/* Reticle corners */}
        <Corners />

        {/* HUD tags */}
        <div className="absolute right-[4%] top-[8%] z-10 flex flex-col items-end gap-1">
          <div className="flex items-stretch bg-ink/90 text-paper">
            <span className={`w-1.5 ${live ? 'bg-acc' : 'bg-paper/30'}`} />
            <span className="px-2.5 py-1 font-cond text-[12px] font-bold uppercase tracking-[0.24em]">
              [ {STATUS_TAG[status]}
              {status === 'thinking' || status === 'connecting' ? <span className="animate-blink">_</span> : ''} ]
            </span>
          </div>
          <div key={resolved} className="animate-slide-in bg-paper/90 px-2 py-0.5 font-mono text-[10.5px] uppercase tracking-[0.08em] text-ink">
            expr // {POSE_TAG[resolved]}
          </div>
          {flag && <div className="animate-slide-in bg-acc px-2 py-0.5 font-cond text-[12px] font-bold uppercase tracking-[0.2em] text-ink">{flag}</div>}
        </div>

        <div ref={bodyRef} className="absolute inset-0 will-change-transform" style={{ transformOrigin: '50% 100%' }}>
          <button
            type="button"
            aria-label="Poke Dr. Agnes Tachyon"
            onClick={poke}
            className={`pointer-events-auto absolute inset-x-[22%] bottom-[2%] top-[4%] cursor-pointer rounded-[40%] transition-transform duration-200 ${
              poked ? 'scale-x-[1.02] scale-y-[0.97]' : ''
            }`}
          />
          {layers.prev && (
            <img
              key={`prev-${layers.prev}`}
              src={`/avatars/${layers.prev}.png`}
              alt=""
              className="absolute inset-0 h-full w-full object-contain opacity-0 transition-opacity duration-300"
              draggable={false}
            />
          )}
          <img
            key={`cur-${layers.cur}`}
            src={`/avatars/${layers.cur}.png`}
            alt={`Dr. Agnes Tachyon, ${POSE_TAG[layers.cur]}`}
            className={`absolute inset-0 h-full w-full animate-[fade-up_0.3s_ease-out_both] select-none object-contain drop-shadow-[0_18px_24px_rgba(0,0,0,0.5)] ${
              poked ? 'scale-[0.985]' : ''
            } ${mood === 'terrible' ? 'saturate-[0.6]' : ''}`}
            draggable={false}
          />
        </div>
      </div>
    </div>
  );
};

const Corners: React.FC = () => {
  const c = 'absolute h-5 w-5 border-paper/40';
  return (
    <>
      <span className={`${c} left-[10%] top-[6%] border-l border-t`} />
      <span className={`${c} right-[10%] top-[6%] border-r border-t`} />
      <span className={`${c} bottom-[2%] left-[10%] border-b border-l`} />
      <span className={`${c} bottom-[2%] right-[10%] border-b border-r`} />
    </>
  );
};
