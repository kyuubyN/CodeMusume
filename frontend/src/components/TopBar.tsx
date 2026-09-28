import React, { useEffect, useRef, useState } from 'react';
import type { GameState, LabState } from '../types';
import { MOOD_LEVEL } from '../lib/game';
import { audioService } from '../services/audio';

interface Props {
  state: GameState;
  lab: LabState | null;
  busy: boolean;
  onEnterLab: () => void;
  onScanRepo: (path: string) => void;
  onRescan: () => void;
  onToggleStats?: () => void;
  onToggleCase?: () => void;
  onGuide: () => void;
}

const Segments: React.FC<{ total: number; filled: number; warn?: boolean }> = ({ total, filled, warn }) => (
  <div className="flex gap-[2px]">
    {Array.from({ length: total }).map((_, i) => (
      <span
        key={i}
        className={`h-2.5 w-[5px] transition-colors duration-500 ${
          i < filled ? (warn ? 'bg-bad' : 'bg-acc') : 'bg-paper/15'
        }`}
      />
    ))}
  </div>
);

export const TopBar: React.FC<Props> = ({ state, lab, busy, onEnterLab, onScanRepo, onRescan, onToggleStats, onToggleCase, onGuide }) => {
  const inLab = state.mode === 'lab';
  const mood = MOOD_LEVEL[state.mood] ?? MOOD_LEVEL.normal;
  const [muted, setMuted] = useState(audioService.isMuted());
  const [repoOpen, setRepoOpen] = useState(false);
  const [path, setPath] = useState('');
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => audioService.subscribe(() => setMuted(audioService.isMuted())), []);

  useEffect(() => {
    if (!repoOpen) return;
    const close = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) setRepoOpen(false);
    };
    window.addEventListener('mousedown', close);
    return () => window.removeEventListener('mousedown', close);
  }, [repoOpen]);

  const turn = Math.min(state.turn, state.max_turns);

  return (
    <header className="relative z-30 flex h-14 shrink-0 items-stretch bg-ink text-paper">
      {/* Brand */}
      <div className="flex items-center gap-3 border-r border-paper/10 px-4">
        <div className="grid h-7 w-7 place-items-center bg-acc font-cond text-sm font-bold text-ink">CM</div>
        <div className="hidden leading-none sm:block">
          <div className="font-cond text-[17px] font-bold uppercase tracking-[0.14em]">CodeMusume</div>
          <div className="mt-0.5 font-cond text-[10px] uppercase tracking-[0.24em] text-paper/45">Voice repo trainer</div>
        </div>
      </div>

      {/* Mode + trainee */}
      <div className="relative flex items-center gap-3 border-r border-paper/10 px-4" ref={popRef}>
        <div className="flex" data-tour="mode">
          <button
            onClick={() => !inLab && onEnterLab()}
            disabled={busy}
            className={`px-2.5 py-1 font-cond text-[11px] font-bold uppercase tracking-[0.18em] ${inLab ? 'bg-acc text-ink' : 'text-paper/60 hover:text-acc'}`}
          >
            Lab
          </button>
          <button
            onClick={() => setRepoOpen((o) => !o)}
            disabled={busy}
            className={`px-2.5 py-1 font-cond text-[11px] font-bold uppercase tracking-[0.18em] ${!inLab ? 'bg-acc text-ink' : 'text-paper/60 hover:text-acc'}`}
          >
            Your repo
          </button>
        </div>
        <div className="hidden leading-none lg:block">
          <div className="font-cond text-[10px] uppercase tracking-[0.24em] text-paper/45">Trainee</div>
          <div className="mt-1 max-w-[180px] truncate font-mono text-[13px]">{state.repo_name}</div>
        </div>
        {!inLab && (
          <button
            onClick={onRescan}
            disabled={busy}
            className="font-cond text-[11px] font-bold uppercase tracking-[0.18em] text-acc hover:text-paper disabled:opacity-40"
            title="Rescan after editing your code"
          >
            {busy ? 'Scanning…' : 'Rescan'}
          </button>
        )}
        {repoOpen && (
          <form
            className="ef-panel absolute left-4 top-full mt-2 w-80 animate-fade-up p-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (path.trim()) onScanRepo(path.trim());
              setRepoOpen(false);
            }}
          >
            <label className="ef-label mb-2 block" htmlFor="repo-path">
              Free lab: scan a Python repository
            </label>
            <input
              id="repo-path"
              autoFocus
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="~/projects/my-api"
              className="h-10 w-full border border-hair bg-white px-3 font-mono text-sm text-ink placeholder:text-faint focus:border-ink focus:outline-none"
            />
            <p className="mt-2 text-[11.5px] leading-relaxed text-sub">
              Static analysis only: the harness never runs your code. Your lab career is saved.
            </p>
            <div className="mt-3 flex gap-2">
              <button type="submit" className="ef-btn-dark flex-1">
                Scan
              </button>
              <button
                type="button"
                className="ef-btn-line"
                onClick={() => {
                  onScanRepo('sample_trainee_repo');
                  setRepoOpen(false);
                }}
              >
                Sample
              </button>
            </div>
          </form>
        )}
      </div>

      <div className="flex-1" />

      {/* Season telemetry */}
      <div className="hidden items-center gap-6 px-4 md:flex">
        {lab && (
          <div className="hidden leading-none xl:block">
            <div className="font-cond text-[10px] uppercase tracking-[0.24em] text-paper/45">
              Career {String(lab.career).padStart(2, '0')} · Day {lab.lab_day}
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="font-cond text-[13px] font-bold uppercase tracking-[0.12em]">{lab.title}</span>
              <Segments total={10} filled={Math.round(lab.bond / 10)} />
            </div>
          </div>
        )}
        <div className="leading-none">
          <div className="font-cond text-[10px] uppercase tracking-[0.24em] text-paper/45">Turn</div>
          <div className="ef-num mt-1 text-xl">
            {String(turn).padStart(2, '0')}
            <span className="text-paper/35">/{String(state.max_turns).padStart(2, '0')}</span>
          </div>
        </div>
        <div className="leading-none">
          <div className="flex justify-between font-cond text-[10px] uppercase tracking-[0.24em] text-paper/45">
            <span>Energy</span>
            <span className={`tabular-nums ${state.energy < 40 ? 'text-bad' : 'text-paper'}`}>{state.energy}</span>
          </div>
          <div className="mt-1.5">
            <Segments total={20} filled={Math.round(state.energy / 5)} warn={state.energy < 40} />
          </div>
        </div>
        <div className="leading-none">
          <div className="flex justify-between gap-3 font-cond text-[10px] uppercase tracking-[0.24em] text-paper/45">
            <span>Mood</span>
            <span className="text-paper">{mood.label}</span>
          </div>
          <div className="mt-1.5">
            <Segments total={5} filled={mood.level} warn={mood.level <= 2} />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1 border-l border-paper/10 px-3">
        {onToggleStats && (
          <button onClick={onToggleStats} className="px-2 font-cond text-[11px] font-bold uppercase tracking-[0.18em] text-paper/70 hover:text-acc lg:hidden">
            Stats
          </button>
        )}
        {onToggleCase && (
          <button
            onClick={onToggleCase}
            className={`px-2 font-cond text-[11px] font-bold uppercase tracking-[0.18em] xl:hidden ${
              lab?.experiment && lab.experiment.stage !== 'debrief' ? 'bg-acc text-ink' : 'text-paper/70 hover:text-acc'
            }`}
          >
            {inLab ? 'Bench' : 'Report'}
          </button>
        )}
        <button
          onClick={onGuide}
          data-tour="guide"
          className="px-2 font-cond text-[11px] font-bold uppercase tracking-[0.18em] text-paper/70 hover:text-acc"
        >
          Guide
        </button>
        <button
          onClick={() => setMuted(audioService.toggleMute())}
          className="px-2 font-cond text-[11px] font-bold uppercase tracking-[0.18em] text-paper/70 hover:text-acc"
          aria-label={muted ? 'Unmute music' : 'Mute music'}
        >
          BGM <span className={muted ? 'text-paper/35' : 'text-acc'}>{muted ? 'Off' : 'On'}</span>
        </button>
      </div>
    </header>
  );
};
