import React, { useState, useEffect } from 'react';
import { GameState, MoodState, StatRank } from '../types';
import { RefreshCw, Activity, Terminal, Shield, Zap, Database, Cpu, Volume2, Volume1, VolumeX } from 'lucide-react';
import { audioService } from '../services/audio';

interface Props {
  state: GameState;
  onScanSampleRepo?: () => void;
  loading?: boolean;
}

const MOOD_DATA: Record<MoodState, { label: string; kanji: string; color: string; border: string }> = {
  great: { label: 'OPTIMAL', kanji: '絶好調', color: 'text-[#ffd000] bg-[#ffd000]/10', border: 'border-[#ffd000]/50' },
  good: { label: 'ELEVATED', kanji: '好調', color: 'text-emerald-400 bg-emerald-500/10', border: 'border-emerald-500/40' },
  normal: { label: 'NOMINAL', kanji: '普通', color: 'text-cyan-400 bg-cyan-500/10', border: 'border-cyan-500/40' },
  poor: { label: 'DEGRADED', kanji: '不調', color: 'text-amber-400 bg-amber-500/10', border: 'border-amber-500/40' },
  terrible: { label: 'CRITICAL', kanji: '絶不調', color: 'text-rose-500 bg-rose-500/15 animate-pulse', border: 'border-rose-500/60' },
};

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

const RANK_BADGE_STYLE: Record<StatRank, string> = {
  SS: 'bg-[#ffd000] text-black font-black border-[#ffd000]',
  S: 'bg-amber-400 text-black font-black border-amber-400',
  A: 'bg-cyan-500 text-black font-black border-cyan-400',
  B: 'bg-emerald-500 text-black font-black border-emerald-400',
  C: 'bg-blue-600 text-white font-bold border-blue-400',
  D: 'bg-indigo-600 text-white font-bold border-indigo-400',
  E: 'bg-slate-700 text-slate-200 font-bold border-slate-600',
  F: 'bg-slate-800 text-slate-400 font-bold border-slate-700',
  G: 'bg-slate-900 text-slate-500 font-bold border-slate-800',
};

export const VNTopHUD: React.FC<Props> = ({ state, onScanSampleRepo, loading = false }) => {
  const mood = MOOD_DATA[state.mood] || MOOD_DATA.normal;
  const [bgmVolume, setBgmVolume] = useState(() => audioService.getBGMVolume());
  const [bgmMuted, setBgmMuted] = useState(() => audioService.isMuted());

  useEffect(() => {
    // Start background soundtrack if not already active
    audioService.playBGM();

    // Subscribe to external changes (e.g. from hotkeys, dialogue ducking, or localStorage sync)
    const unsubscribe = audioService.subscribe(() => {
      setBgmVolume(audioService.getBGMVolume());
      setBgmMuted(audioService.isMuted());
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const handleToggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newMuted = audioService.toggleMute();
    setBgmMuted(newMuted);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    audioService.setBGMVolume(val);
    setBgmVolume(val);
    setBgmMuted(audioService.isMuted());
  };

  const getEnergyBarColor = (val: number) => {
    if (val >= 60) return 'bg-[#00f0ff]';
    if (val >= 30) return 'bg-[#ffd000]';
    return 'bg-[#ff3b30]';
  };

  const statList = [
    { key: 'speed', label: 'SPD', icon: <Zap className="w-3.5 h-3.5 text-[#00f0ff]" />, score: state.attributes.speed },
    { key: 'stamina', label: 'STM', icon: <Database className="w-3.5 h-3.5 text-pink-400" />, score: state.attributes.stamina },
    { key: 'power', label: 'PWR', icon: <Cpu className="w-3.5 h-3.5 text-[#ffd000]" />, score: state.attributes.power },
    { key: 'guts', label: 'GUT', icon: <Shield className="w-3.5 h-3.5 text-rose-400" />, score: state.attributes.guts },
    { key: 'wisdom', label: 'WIS', icon: <Terminal className="w-3.5 h-3.5 text-emerald-400" />, score: state.attributes.wisdom },
  ];

  return (
    <div className="w-full bg-[#0a0d13]/98 border-b border-white/10 px-3 py-1.5 flex flex-nowrap items-center justify-between gap-2 z-30 select-none font-mono overflow-x-auto overflow-y-hidden shrink-0">
      {/* Left: Tactical Target Identity */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Yellow Tactical Accent Bar */}
        <div className="w-1 h-7 bg-[#ffd000] rounded-sm" />

        <div className="flex flex-col">
          <div className="flex items-center gap-1 text-[8px] uppercase tracking-wider text-[#7b8594] leading-tight">
            <span>TARGET SPECIMEN</span>
            <span className="opacity-40">•</span>
            <span>END-ARCH // REPO</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-black tracking-wider text-[#f0f3f6] uppercase truncate max-w-[140px]">
              {state.repo_name}
            </span>
            {onScanSampleRepo && (
              <button
                onClick={onScanSampleRepo}
                disabled={loading}
                title="Re-scan Target Repository (sample_trainee_repo)"
                className="p-1 rounded bg-[#161a22] hover:bg-[#202530] text-[#7b8594] hover:text-[#ffd000] border border-white/10 transition-colors"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>
        </div>

        {/* Phase / Cycle Counter */}
        <div className="ml-1 px-2 py-0.5 rounded bg-[#12161f] border border-white/10 flex items-center gap-1">
          <span className="text-[9px] text-[#7b8594] tracking-wider">CYCLE</span>
          <span className="text-xs font-black text-[#ffd000] tabular-nums">
            {String(state.turn).padStart(2, '0')}/{String(state.max_turns).padStart(2, '0')}
          </span>
        </div>

        {/* Derby Qualification Progress */}
        <div
          className={`ml-1 px-2 py-0.5 rounded border flex items-center gap-1.5 transition-colors ${
            state.race_unlocked
              ? 'bg-[#ffd000]/15 border-[#ffd000] text-[#ffd000] shadow-[0_0_12px_rgba(255,208,0,0.3)] animate-pulse'
              : 'bg-[#12161f] border-white/10 text-[#7b8594]'
          }`}
          title="Grand Derby Qualification: Complete 10 trainings & chat inquiries to unlock"
        >
          <span className="text-[8px] font-black tracking-wider uppercase">DERBY QUAL</span>
          <span
            className={`text-xs font-mono font-black tabular-nums ${
              state.race_unlocked ? 'text-[#ffd000]' : 'text-[#f0f3f6]'
            }`}
          >
            [{state.interactions_in_cycle ?? 0}/{state.interactions_required ?? 10}]
          </span>
          {state.race_unlocked && (
            <span className="text-[8px] bg-[#ffd000] text-black font-black px-1 rounded-sm leading-tight">
              READY
            </span>
          )}
        </div>
      </div>

      {/* Center: Energy Power Matrix & Condition Monitor */}
      <div className="flex items-center gap-2.5 flex-shrink-0 w-36 sm:w-44 md:w-52">
        {/* Power Reserve Gauge */}
        <div className="flex-1 flex flex-col gap-0.5">
          <div className="flex items-center justify-between text-[9px] tracking-wider text-[#7b8594]">
            <span className="flex items-center gap-1 font-bold text-[#c4ccd8]">
              <Activity className="w-2.5 h-2.5 text-[#00f0ff]" />
              POWER MATRIX
            </span>
            <span className="font-mono font-bold text-[#f0f3f6] tabular-nums">
              {state.energy}%
            </span>
          </div>

          <div className="w-full h-1.5 rounded bg-[#161b24] border border-white/10 overflow-hidden">
            <div
              className={`h-full rounded-sm transition-all duration-300 ${getEnergyBarColor(
                state.energy
              )}`}
              style={{ width: `${Math.max(0, Math.min(100, state.energy))}%` }}
            />
          </div>
        </div>

        {/* Tactical Condition Tag */}
        <div
          className={`flex items-center gap-1 px-1.5 py-0.5 rounded border text-[9px] font-black tracking-wider ${mood.color} ${mood.border} flex-shrink-0`}
        >
          <span>{mood.kanji}</span>
          <span className="hidden sm:inline text-[8px] opacity-90">{mood.label}</span>
        </div>
      </div>

      {/* Right: 5 Core Code Attributes Telemetry & BGM Audio Controller */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {statList.map((stat) => {
            const rank = getRank(stat.score);
            const badgeClass = RANK_BADGE_STYLE[rank];
            return (
              <div
                key={stat.key}
                className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#12161f] border border-white/10 shadow-sm"
              >
                <div className="opacity-80">{stat.icon}</div>
                <div className="flex flex-col text-left">
                  <span className="text-[7px] font-bold text-[#7b8594] tracking-wider leading-none">
                    {stat.label}
                  </span>
                  <span className="text-[11px] font-mono font-black text-[#f0f3f6] tabular-nums leading-tight">
                    {stat.score}
                  </span>
                </div>
                <span
                  className={`text-[8px] px-1 rounded border ml-0.5 font-bold tracking-tighter ${badgeClass}`}
                >
                  {rank}
                </span>
              </div>
            );
          })}
        </div>

        {/* Tactical BGM Audio Controller */}
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#12161f] border border-white/10 shadow-sm flex-shrink-0">
          <button
            onClick={handleToggleMute}
            title={bgmMuted ? 'Unmute BGM (Steady Steps)' : 'Mute BGM (Steady Steps)'}
            className="p-1 rounded hover:bg-[#1a202c] text-[#7b8594] hover:text-[#ffd000] transition-colors flex items-center gap-1"
          >
            {bgmMuted ? (
              <VolumeX className="w-3.5 h-3.5 text-rose-400" />
            ) : bgmVolume === 0 ? (
              <VolumeX className="w-3.5 h-3.5 text-[#7b8594]" />
            ) : bgmVolume < 0.5 ? (
              <Volume1 className="w-3.5 h-3.5 text-[#00f0ff]" />
            ) : (
              <Volume2 className="w-3.5 h-3.5 text-[#ffd000]" />
            )}
            <span className="text-[8px] font-black tracking-wider uppercase hidden sm:inline">
              BGM
            </span>
          </button>

          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={bgmMuted ? 0 : bgmVolume}
            onChange={handleVolumeChange}
            title={`BGM Volume: ${bgmMuted ? '0% (Muted)' : `${Math.round(bgmVolume * 100)}%`}`}
            className="w-14 sm:w-16 h-1.5 accent-[#ffd000] bg-[#161b24] rounded-lg appearance-none cursor-pointer"
          />
          <span className="text-[8px] font-mono font-bold text-[#7b8594] tabular-nums w-7 text-right">
            {bgmMuted ? 'OFF' : `${Math.round(bgmVolume * 100)}%`}
          </span>
        </div>
      </div>
    </div>
  );
};
