import React from 'react';
import type { LabState } from '../../types';
import { STAT_BY_KEY } from '../../lib/game';

interface Props {
  lab: LabState;
  busy: boolean;
  seasonOver: boolean;
  onStart: (chapter: number) => void;
  onReview: () => void;
  onOpenExperiment: () => void;
}

const pad = (n: number) => String(n).padStart(2, '0');

export const LabBoard: React.FC<Props> = ({ lab, busy, seasonOver, onStart, onReview, onOpenExperiment }) => {
  const next = lab.chapters.find((c) => c.status === 'open');
  const due = lab.mastery.filter((m) => m.due);
  return (
    <div>
      <div className="flex items-baseline justify-between border-b border-hair px-4 py-2">
        <span className="ef-label">Career {pad(lab.career)} · lab day {lab.lab_day}</span>
        <span className="ef-label">
          {lab.experiments_done}/{lab.chapters.length} cleared
        </span>
      </div>
      <ul>
        {lab.chapters.map((c) => {
          const isNext = c === next;
          const active = c.status === 'active';
          return (
            <li key={c.id} className={`group relative flex items-stretch border-b border-hair ${active ? 'bg-acc/20' : ''}`}>
              {isNext && !active && <span className="absolute inset-y-0 left-0 w-[3px] bg-acc" />}
              <div className="flex w-16 shrink-0 items-start justify-center pt-3">
                <span className={`ef-num text-[30px] ${c.status === 'cleared' ? 'text-ink' : 'text-faint group-hover:text-ink'}`}>{pad(c.id)}</span>
              </div>
              <div className="min-w-0 flex-1 py-3 pr-2">
                <div className="flex items-center gap-1.5">
                  <span className="ef-tag">{STAT_BY_KEY[c.stat].short}</span>
                  <span className="truncate font-cond text-[15px] font-bold uppercase tracking-[0.08em]">{c.title}</span>
                </div>
                <div className="mt-0.5 text-[12.5px] text-sub">{c.concept}</div>
                <div className="mt-1 font-mono text-[11px] text-ink">
                  {c.error ? <span className="text-bad">probe error</span> : c.measure ? `${c.measure.value} ${c.measure.unit}` : 'measuring…'}
                  <span className="text-faint"> · {c.measure?.label.toLowerCase()}</span>
                </div>
              </div>
              <div className="flex w-[92px] shrink-0 flex-col items-end justify-center gap-1 pr-4">
                {c.status === 'cleared' ? (
                  <>
                    <span className="ef-num text-[22px]">{c.score}</span>
                    <span className="font-cond text-[10px] font-bold uppercase tracking-[0.16em] text-sub">cleared · {c.fix}</span>
                  </>
                ) : active ? (
                  <button onClick={onOpenExperiment} className="ef-btn-dark h-8 px-3 text-[11px]">
                    Resume
                  </button>
                ) : (
                  <button
                    onClick={() => onStart(c.id)}
                    disabled={busy || seasonOver || !!lab.experiment && lab.experiment.stage !== 'debrief'}
                    className={`${isNext ? 'ef-btn-acc' : 'ef-btn-line'} h-8 px-3 text-[11px]`}
                    title="Costs 20 energy"
                  >
                    Start
                  </button>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      <div className="px-4 py-3">
        {due.length > 0 ? (
          <div className="flex items-stretch">
            <span className="w-1 bg-acc" />
            <div className="flex flex-1 items-center justify-between gap-3 bg-ink px-3 py-2 text-paper">
              <div>
                <div className="font-cond text-[11px] font-bold uppercase tracking-[0.16em] text-acc">Review due</div>
                <div className="text-[12.5px]">{due.map((d) => d.title).join(' · ')}</div>
              </div>
              <button onClick={onReview} disabled={busy || seasonOver} className="ef-btn-acc h-8 px-3 text-[11px]">
                Pop quiz
              </button>
            </div>
          </div>
        ) : (
          <p className="text-[12px] leading-relaxed text-sub">
            Each experiment: predict, find the culprit, explain it, pick a treatment, measure again. The trainee's stats are the measurements.
          </p>
        )}
      </div>
    </div>
  );
};
