import React from 'react';
import type { CareerSummary, LabState } from '../types';
import { STATS, rankIsHigh, rankOf } from '../lib/game';

interface Props {
  summary: CareerSummary;
  lab: LabState | null;
  onNewCareer: () => void;
  onClose: () => void;
}

const PLACE = ['', '1st', '2nd', '3rd', '4th'];

export const CareerResult: React.FC<Props> = ({ summary, lab, onNewCareer, onClose }) => {
  const h = summary.hall_entry;
  const sparks = Object.entries(summary.sparks_earned);
  const conceptTitle = (key: string) => lab?.mastery.find((m) => m.concept === key)?.title ?? key;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-4">
      <div className="ef-panel w-full max-w-lg animate-pop-in">
        <div className="flex items-stretch border-b border-hair">
          <div className="flex flex-col justify-center bg-ink px-5 py-4 text-paper">
            <span className="font-cond text-[11px] font-bold uppercase tracking-[0.24em] text-paper/60">Grand Derby</span>
            <span className={`ef-num text-[56px] ${h.place === 1 ? 'text-acc' : 'text-paper'}`}>{PLACE[h.place] ?? `${h.place}th`}</span>
          </div>
          <div className="flex-1 px-5 py-4">
            <div className="ef-label">Career {String(h.career).padStart(2, '0')} complete</div>
            <h2 className="mt-1 font-cond text-[24px] font-bold uppercase leading-none tracking-[0.06em]">{h.trainee}</h2>
            <p className="mt-2 text-[12.5px] text-sub">
              {h.checkpoint_score}/3 checkpoints · {h.chapters_cleared.length} experiments cleared
            </p>
          </div>
        </div>

        <div className="grid grid-cols-5 gap-px border-b border-hair bg-hair">
          {STATS.map((s) => {
            const v = h.attributes[s.key];
            const r = rankOf(v);
            return (
              <div key={s.key} className={`px-2 py-2 text-center ${rankIsHigh(r) ? 'bg-acc' : 'bg-paper'}`}>
                <div className="font-cond text-[10px] font-bold uppercase tracking-[0.16em] text-sub">{s.short}</div>
                <div className="ef-num mt-1 text-[20px]">{r}</div>
                <div className="font-mono text-[10.5px] text-sub">{v}</div>
              </div>
            );
          })}
        </div>

        <div className="px-5 py-4">
          <div className="ef-label">Sparks inherited by your next career</div>
          {sparks.length === 0 ? (
            <p className="mt-1 text-[12.5px] text-sub">None this time. Score 60+ in an experiment to leave a spark behind.</p>
          ) : (
            <ul className="mt-2 flex flex-col gap-1">
              {sparks.map(([k, n]) => (
                <li key={k} className="flex items-center gap-2 text-[13px]">
                  <span className="flex gap-0.5">
                    {Array.from({ length: 3 }).map((_, i) => (
                      <span key={i} className={`h-3 w-2 ${i < n ? 'bg-acc' : 'bg-paper-3'}`} />
                    ))}
                  </span>
                  <span className="font-semibold">{conceptTitle(k)}</span>
                  <span className="font-mono text-[10.5px] text-sub">Derby skill +{n * 60}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-[12.5px] leading-relaxed text-sub">
            Bond {summary.bond}/100 · {summary.title}. This career joins the Hall of Fame; your best one returns as the ghost you race next time.
          </p>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button onClick={onClose} className="ef-btn-line">
              Stay
            </button>
            <button onClick={onNewCareer} className="ef-btn-acc">
              Career {String(summary.next_career).padStart(2, '0')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
