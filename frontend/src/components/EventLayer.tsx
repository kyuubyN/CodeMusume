import React, { useEffect, useRef } from 'react';

/** A full-width banner for big moments (experiment verdicts, eureka, rank ups). */
export interface CutIn {
  id: number;
  kicker: string;
  title: string;
  detail?: string;
  tone: 'good' | 'bad' | 'acc';
  image?: string;
}

export interface Toast {
  id: number;
  tone: 'good' | 'bad' | 'info';
  title: string;
  body?: string;
}

interface Props {
  cutIn: CutIn | null;
  toasts: Toast[];
  onCutInDone: () => void;
  onToastDone: (id: number) => void;
}

const TONE_BAR = { good: 'bg-ok', bad: 'bg-bad', info: 'bg-ink', acc: 'bg-acc' };

export const EventLayer: React.FC<Props> = ({ cutIn, toasts, onCutInDone, onToastDone }) => {
  useEffect(() => {
    if (!cutIn) return;
    const t = window.setTimeout(onCutInDone, 1900);
    return () => window.clearTimeout(t);
  }, [cutIn, onCutInDone]);

  return (
    <>
      {cutIn && <Banner key={cutIn.id} cutIn={cutIn} />}
      <div className="pointer-events-none fixed right-4 top-[68px] z-50 flex w-[min(92vw,360px)] flex-col gap-2">
        {toasts.map((t) => (
          <ToastCard key={t.id} toast={t} onDone={() => onToastDone(t.id)} />
        ))}
      </div>
    </>
  );
};

const Banner: React.FC<{ cutIn: CutIn }> = ({ cutIn }) => {
  const accent = cutIn.tone === 'bad' ? 'bg-bad' : cutIn.tone === 'good' ? 'bg-ok' : 'bg-acc';
  return (
    <div className="pointer-events-none fixed inset-0 z-40 flex items-center overflow-hidden">
      <div className="relative w-full animate-cut-in">
        <div className={`h-1.5 w-full ${cutIn.tone === 'acc' ? 'ef-hazard' : accent}`} />
        <div className="relative flex items-stretch overflow-hidden bg-ink text-paper">
          {cutIn.image && (
            <img src={cutIn.image} alt="" className="absolute inset-y-0 right-0 h-full w-1/2 object-cover opacity-35 grayscale" />
          )}
          <div className="relative flex items-center gap-8 px-[8vw] py-7">
            <span className={`h-16 w-3 ${accent}`} />
            <div>
              <div className="font-cond text-[13px] font-bold uppercase tracking-[0.35em] text-paper/60">{cutIn.kicker}</div>
              <div className="font-cond text-6xl font-bold uppercase leading-none tracking-[0.04em]">{cutIn.title}</div>
              {cutIn.detail && <div className="mt-2 font-mono text-[13px] text-acc">{cutIn.detail}</div>}
            </div>
          </div>
        </div>
        <div className="h-px w-full bg-paper/30" />
      </div>
    </div>
  );
};

const ToastCard: React.FC<{ toast: Toast; onDone: () => void }> = ({ toast, onDone }) => {
  const doneRef = useRef(onDone);
  doneRef.current = onDone;
  // Timer starts once per toast; parent re-renders must not restart it.
  useEffect(() => {
    const t = window.setTimeout(() => doneRef.current(), 4200);
    return () => window.clearTimeout(t);
  }, []);
  return (
    <div className="ef-panel pointer-events-auto flex animate-slide-in" role="status">
      <span className={`w-1 shrink-0 ${TONE_BAR[toast.tone]}`} />
      <div className="px-3.5 py-2.5">
        <div className="font-cond text-[14px] font-bold uppercase tracking-[0.1em]">{toast.title}</div>
        {toast.body && <div className="mt-0.5 text-[12.5px] leading-snug text-sub">{toast.body}</div>}
      </div>
    </div>
  );
};
