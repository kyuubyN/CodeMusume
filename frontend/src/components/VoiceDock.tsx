import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { VoiceController } from '../hooks/useVoiceAgent';
import type { VoiceStatus } from '../services/voiceAgent';

interface Props {
  voice: VoiceController;
  /** Used when no voice session is live (typed chat through the backend). */
  onTextFallback: (text: string) => void;
  textBusy: boolean;
}

const STATUS: Record<VoiceStatus, string> = {
  idle: 'Offline',
  connecting: 'Linking',
  listening: 'Listening',
  user_speaking: 'Receiving',
  thinking: 'Processing',
  speaking: 'Transmitting',
  error: 'Link error',
};

const BARS = 28;

export const VoiceDock: React.FC<Props> = ({ voice, onTextFallback, textBusy }) => {
  const { status, live, partial, log, error, muted } = voice;
  const [typing, setTyping] = useState(false);
  const [text, setText] = useState('');
  const [showLog, setShowLog] = useState(false);
  const meterRef = useRef<HTMLDivElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef(status);
  statusRef.current = status;

  const lastAgnes = useMemo(() => [...log].reverse().find((l) => l.role === 'agnes'), [log]);
  const lastUser = useMemo(() => [...log].reverse().find((l) => l.role === 'user'), [log]);

  // Segmented level meter follows whoever is talking.
  useEffect(() => {
    let raf = 0;
    let smooth = 0;
    const hist = new Array(BARS).fill(0);
    let frame = 0;
    const tick = () => {
      const agent = voice.agentRef.current;
      const s = statusRef.current;
      const lvl = !agent ? 0 : s === 'speaking' ? agent.getOutputLevel() : agent.getInputLevel();
      smooth += (lvl - smooth) * 0.35;
      if (++frame % 3 === 0) {
        hist.shift();
        hist.push(smooth);
      }
      const el = meterRef.current;
      if (el) {
        for (let i = 0; i < BARS; i++) {
          const bar = el.children[i] as HTMLElement | undefined;
          if (bar) bar.style.transform = `scaleY(${Math.max(0.08, Math.min(1, hist[i] * 1.4)).toFixed(3)})`;
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [voice.agentRef]);

  useEffect(() => {
    if (showLog && logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [showLog, log.length]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    setText('');
    if (live) voice.sendText(t);
    else onTextFallback(t);
  };

  const receiving = status === 'user_speaking' || status === 'thinking';
  const cell = 'flex items-center justify-center border-r border-hair px-4 font-cond text-[12px] font-bold uppercase tracking-[0.18em] transition-colors';

  return (
    <div className="pointer-events-auto mx-auto flex w-full max-w-[720px] flex-col gap-2">
      {showLog && (
        <div className="ef-panel animate-fade-up">
          <div className="flex items-center justify-between border-b border-hair px-4 py-2">
            <span className="ef-label">Comms log</span>
            <button onClick={() => setShowLog(false)} className="ef-label hover:text-ink">
              Close
            </button>
          </div>
          <div ref={logRef} className="scroll-thin max-h-[32vh] overflow-y-auto px-4 py-2">
            {log.length === 0 && <p className="py-2 text-sm text-sub">No transmissions yet.</p>}
            {log.map((l) => (
              <div key={l.id} className="flex gap-3 border-b border-hair py-2 last:border-b-0">
                <span className={`w-14 shrink-0 pt-0.5 font-cond text-[11px] font-bold uppercase tracking-[0.16em] ${l.role === 'agnes' ? 'text-ink' : 'text-faint'}`}>
                  {l.role === 'agnes' ? 'Agnes' : l.role === 'user' ? 'You' : 'Event'}
                </span>
                <p className={`text-[13.5px] leading-relaxed ${l.role === 'event' ? 'text-sub' : 'text-ink'}`}>
                  {l.text}
                  {l.interrupted && <span className="text-faint"> [interrupted]</span>}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="ef-panel">
        {/* Speaker bar */}
        <div className="flex items-stretch border-b border-hair">
          <span className="bg-ink px-3 py-1.5 font-cond text-[13px] font-bold uppercase tracking-[0.2em] text-paper">Agnes Tachyon</span>
          <span className="ef-label flex items-center px-3">Chief architect · lab 04</span>
          <span className="ml-auto flex items-center gap-2 px-4">
            <span className={`h-2 w-2 ${live ? 'bg-acc' : 'bg-faint'} ${status === 'listening' ? 'animate-blink' : ''}`} />
            <span className="font-cond text-[12px] font-bold uppercase tracking-[0.2em] text-ink">
              {muted && live ? 'Mic muted' : STATUS[status]}
            </span>
          </span>
        </div>

        {/* Caption */}
        <div className="min-h-[4.75rem] px-5 py-4" aria-live="polite">
          {lastAgnes ? (
            <p key={lastAgnes.id} className={`animate-fade-up text-[17px] font-medium leading-relaxed ${status === 'speaking' ? 'text-sub' : 'text-ink'}`}>
              {lastAgnes.text}
            </p>
          ) : (
            <p className="text-[16px] leading-relaxed text-sub">
              Open the voice link and ask her something — <span className="text-ink">“what’s wrong with my code?”</span>
            </p>
          )}
        </div>

        {(partial || (receiving && lastUser)) && (
          <div className="flex gap-3 border-t border-hair px-5 py-2.5">
            <span className="ef-tag mt-0.5 self-start">You</span>
            <p className="text-[14px] text-sub">
              {partial || lastUser?.text}
              {status === 'user_speaking' && <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-blink bg-ink align-middle" />}
            </p>
          </div>
        )}

        {typing && (
          <form onSubmit={submit} className="flex h-12 items-stretch border-t border-hair">
            <input
              autoFocus
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={live ? 'Type — Agnes answers out loud' : 'Type to Agnes'}
              className="min-w-0 flex-1 bg-white/60 px-5 text-[14px] text-ink placeholder:text-faint focus:bg-white focus:outline-none"
            />
            <button type="submit" disabled={!text.trim() || textBusy} className="ef-btn-dark h-auto">
              {textBusy ? 'Sending' : 'Send'}
            </button>
          </form>
        )}

        {/* Control strip */}
        <div className="flex h-14 items-stretch border-t border-hair">
          <button onClick={() => setShowLog((s) => !s)} className={`${cell} ${showLog ? 'bg-ink text-paper' : 'text-sub hover:bg-paper-2 hover:text-ink'}`}>
            Log
          </button>
          <button onClick={() => setTyping((t) => !t)} className={`${cell} ${typing ? 'bg-ink text-paper' : 'text-sub hover:bg-paper-2 hover:text-ink'}`}>
            Type
          </button>

          {live ? (
            <>
              <div className="relative flex flex-1 items-center overflow-hidden px-4">
                <div ref={meterRef} className="flex h-7 w-full items-center gap-[3px]">
                  {Array.from({ length: BARS }).map((_, i) => (
                    <span key={i} className={`h-full flex-1 origin-center ${status === 'speaking' ? 'bg-ink' : 'bg-ink/55'}`} style={{ transform: 'scaleY(0.08)' }} />
                  ))}
                </div>
                {status === 'thinking' && <span className="pointer-events-none absolute inset-y-0 left-0 w-1/3 animate-scan bg-gradient-to-r from-transparent via-acc/50 to-transparent" />}
              </div>
              <button
                onClick={() => voice.setMuted(!muted)}
                className={`${cell} border-l ${muted ? 'ef-hazard text-ink' : 'text-ink hover:bg-paper-2'}`}
                aria-label={muted ? 'Unmute microphone' : 'Mute microphone'}
              >
                <span className={muted ? 'bg-acc px-1' : ''}>{muted ? 'Unmute' : 'Mute'}</span>
              </button>
              <button onClick={voice.stop} className={`${cell} border-r-0 bg-ink text-paper hover:bg-bad`}>
                End link
              </button>
            </>
          ) : (
            <button
              onClick={() => void voice.start()}
              disabled={status === 'connecting'}
              className="ef-btn-acc h-auto flex-1 text-[14px]"
            >
              {status === 'connecting' ? (
                <span className="flex items-center gap-2">
                  Establishing link <span className="animate-blink">_</span>
                </span>
              ) : (
                <>
                  <MicGlyph /> Open voice link
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-stretch bg-ink text-paper">
          <span className="ef-hazard w-2 shrink-0" />
          <p className="flex-1 px-3 py-2 text-[12.5px]">
            <span className="mr-2 font-cond font-bold uppercase tracking-[0.16em] text-acc">Voice unavailable</span>
            {error}
            {/ASSEMBLYAI_API_KEY/.test(error) && ' — add it to .env and restart the backend. Typing still works.'}
          </p>
          <button onClick={voice.clearError} className="px-3 font-cond text-[11px] font-bold uppercase tracking-[0.16em] text-paper/60 hover:text-acc">
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
};

const MicGlyph: React.FC = () => (
  <svg viewBox="0 0 16 16" className="h-4 w-4" aria-hidden fill="none" stroke="currentColor" strokeWidth="1.8">
    <rect x="5.5" y="1.5" width="5" height="8.5" />
    <path d="M3 7.5v1a5 5 0 0 0 10 0v-1M8 13.5v2" />
  </svg>
);
