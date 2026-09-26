import React, { useState } from 'react';
import { AttributeType } from '../types';
import { Zap, Database, Cpu, Shield, Terminal, Coffee, Flag, ChevronRight, ChevronLeft, Lock } from 'lucide-react';

interface Props {
  energy: number;
  loading: boolean;
  onTrain: (attr: AttributeType) => void;
  onRest: () => void;
  onRace: () => void;
  interactionsInCycle?: number;
  interactionsRequired?: number;
  raceUnlocked?: boolean;
}

export const VNTrainingMenu: React.FC<Props> = ({
  energy,
  loading,
  onTrain,
  onRest,
  onRace,
  interactionsInCycle = 0,
  interactionsRequired = 10,
  raceUnlocked = false,
}) => {
  const [isOpen, setIsOpen] = useState(true);

  // Failure rate calculation matching TrainerEngine
  const getFailureRate = (attr: AttributeType): number => {
    if (attr === 'wisdom') return 0;
    if (energy >= 80) return 0;
    if (energy >= 60) return 5;
    if (energy >= 40) return 18;
    if (energy >= 20) return 45;
    return 75;
  };

  const trainActions: Array<{
    type: AttributeType;
    code: string;
    label: string;
    sublabel: string;
    icon: React.ReactNode;
    accentColor: string;
  }> = [
    {
      type: 'speed',
      code: '01 // SPD',
      label: 'SPEED',
      sublabel: 'Async & Event Loop',
      icon: <Zap className="w-3.5 h-3.5 text-[#00f0ff]" />,
      accentColor: 'hover:border-[#00f0ff] hover:text-[#00f0ff]',
    },
    {
      type: 'stamina',
      code: '02 // STM',
      label: 'STAMINA',
      sublabel: 'Memory & Context Handles',
      icon: <Database className="w-3.5 h-3.5 text-pink-400" />,
      accentColor: 'hover:border-pink-400 hover:text-pink-400',
    },
    {
      type: 'power',
      code: '03 // PWR',
      label: 'POWER',
      sublabel: 'Concurrency & Batching',
      icon: <Cpu className="w-3.5 h-3.5 text-[#ffd000]" />,
      accentColor: 'hover:border-[#ffd000] hover:text-[#ffd000]',
    },
    {
      type: 'guts',
      code: '04 // GUT',
      label: 'GUTS',
      sublabel: 'Resilience & Circuit Breakers',
      icon: <Shield className="w-3.5 h-3.5 text-rose-400" />,
      accentColor: 'hover:border-rose-400 hover:text-rose-400',
    },
    {
      type: 'wisdom',
      code: '05 // WIS',
      label: 'WISDOM',
      sublabel: 'DDD & Clean Architecture RAG',
      icon: <Terminal className="w-3.5 h-3.5 text-emerald-400" />,
      accentColor: 'hover:border-emerald-400 hover:text-emerald-400',
    },
  ];

  return (
    <div
      className="absolute right-4 top-16 z-20 flex items-start gap-1 select-none font-mono"
      style={{ contain: 'layout paint' }}
    >
      {/* Toggle Tab */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="mt-2 p-1.5 rounded-l-lg bg-[#0c0f16] hover:bg-[#161a24] text-[#ffd000] border-l border-y border-white/10 transition-colors"
        title={isOpen ? 'Collapse Commands' : 'Open Training Menu'}
      >
        {isOpen ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>

      {/* Main Tactical Command Console */}
      {isOpen && (
        <div className="w-68 bg-[#0c0f16] border border-white/15 rounded-xl p-3 flex flex-col gap-2 text-[#f0f3f6]">
          {/* Header */}
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-3 bg-[#ffd000] rounded-sm" />
              <span className="text-[10px] font-black uppercase tracking-widest text-[#ffd000]">
                TRAINER COMMANDS
              </span>
            </div>
            <span className="text-[9px] text-[#7b8594] tracking-wider uppercase">
              ENERGY: {energy}%
            </span>
          </div>

          {/* 5 Training Actions */}
          <div className="flex flex-col gap-1.5">
            {trainActions.map((act) => {
              const failRate = getFailureRate(act.type);
              const isDisabled = loading || energy < 20;

              return (
                <button
                  key={act.type}
                  disabled={isDisabled}
                  onClick={() => onTrain(act.type)}
                  className={`group relative flex items-center justify-between p-2 rounded-lg bg-[#121620] hover:bg-[#191f2c] border border-white/10 ${act.accentColor} transition-colors duration-100 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed`}
                >
                  <div className="flex items-center gap-2">
                    <div className="p-1 rounded bg-[#0a0d13] border border-white/10">
                      {act.icon}
                    </div>
                    <div className="flex flex-col text-left">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[8px] text-[#7b8594] tracking-widest">
                          {act.code}
                        </span>
                        <span className="text-[11px] font-black tracking-wide text-white group-hover:text-[#ffd000] transition-colors">
                          {act.label}
                        </span>
                      </div>
                      <span className="text-[9px] font-sans text-[#7b8594] truncate max-w-[130px]">
                        {act.sublabel}
                      </span>
                    </div>
                  </div>

                  {/* Failure Risk Tag */}
                  <span
                    className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold tracking-tighter ${
                      failRate === 0
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : failRate > 30
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/50'
                        : 'bg-amber-400/10 text-amber-300 border border-amber-400/30'
                    }`}
                  >
                    {failRate}%
                  </span>
                </button>
              );
            })}
          </div>

          {/* Rest Button */}
          <button
            disabled={loading}
            onClick={onRest}
            className="w-full py-2 px-3 rounded-lg bg-[#141a28] hover:bg-[#1c2438] border border-[#00f0ff]/40 text-[#00f0ff] font-bold text-xs tracking-wider transition-colors active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2 mt-0.5"
          >
            <Coffee className="w-3.5 h-3.5" />
            <span>REST (+HP)</span>
          </button>

          {/* URA Derby Race Button */}
          <button
            disabled={loading || !raceUnlocked}
            onClick={onRace}
            title={
              raceUnlocked
                ? 'Engage Grand Derby Architecture Exam'
                : `Grand Derby Locked: Requires ${interactionsRequired} interactions (${interactionsInCycle}/${interactionsRequired})`
            }
            className={`w-full py-2.5 px-3 rounded-lg font-black text-xs tracking-wider transition-all active:scale-95 flex items-center justify-center gap-2 ${
              raceUnlocked
                ? 'bg-[#ffd000] hover:bg-[#ffdb33] text-black shadow-[0_0_20px_rgba(255,208,0,0.4)] animate-pulse cursor-pointer'
                : 'bg-[#141a24] text-[#7b8594] border border-white/10 cursor-not-allowed opacity-65'
            }`}
          >
            {raceUnlocked ? (
              <Flag className="w-3.5 h-3.5 fill-black text-black" />
            ) : (
              <Lock className="w-3.5 h-3.5 text-[#7b8594]" />
            )}
            <span>
              {raceUnlocked
                ? 'ENGAGE URA DERBY (QUALIFIED!)'
                : `LOCKED // DERBY [${interactionsInCycle}/${interactionsRequired}]`}
            </span>
          </button>
        </div>
      )}
    </div>
  );
};
