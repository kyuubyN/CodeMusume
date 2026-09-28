import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';

export interface TourStep {
  /** `data-tour` value of the element to spotlight; omitted = centered card. */
  target?: string;
  kicker: string;
  title: string;
  body: React.ReactNode;
}

interface Props {
  steps: TourStep[];
  onStep?: (index: number, step: TourStep) => void;
  onClose: (finished: boolean) => void;
}

const CARD_W = 380;
const GAP = 16;

type Rect = { x: number; y: number; w: number; h: number };

/** Guided tour: dims the screen, spotlights one real element, explains it. */
export const Tutorial: React.FC<Props> = ({ steps, onStep, onClose }) => {
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const step = steps[i];
  const last = i === steps.length - 1;

  useEffect(() => {
    onStep?.(i, steps[i]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i]);

  // Track the target's box (it can move as panels switch or the window resizes).
  useLayoutEffect(() => {
    let raf = 0;
    const measure = () => {
      const el = step.target ? document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`) : null;
      const r = el?.getBoundingClientRect();
      const next = r && r.width > 0 && r.height > 0 ? { x: r.left, y: r.top, w: r.width, h: r.height } : null;
      setRect((prev) =>
        prev && next && Math.abs(prev.x - next.x) < 1 && Math.abs(prev.y - next.y) < 1 && Math.abs(prev.w - next.w) < 1 && Math.abs(prev.h - next.h) < 1
          ? prev
          : next
      );
      raf = requestAnimationFrame(measure);
    };
    measure();
    return () => cancelAnimationFrame(raf);
  }, [step.target]);

  const go = useCallback(
    (d: number) => {
      const n = i + d;
      if (n < 0) return;
      if (n >= steps.length) onClose(true);
      else setI(n);
    },
    [i, steps.length, onClose]
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose(false);
      if (e.key === 'ArrowRight' || e.key === 'Enter') go(1);
      if (e.key === 'ArrowLeft') go(-1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, onClose]);

  // Place the card beside the spotlight, on the side with the most room.
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let cardStyle: React.CSSProperties;
  if (!rect) {
    cardStyle = { left: Math.max(16, (vw - CARD_W) / 2), top: Math.max(16, vh / 2 - 160) };
  } else {
    const room = { right: vw - (rect.x + rect.w), left: rect.x, below: vh - (rect.y + rect.h), above: rect.y };
    const clampTop = (t: number) => Math.min(Math.max(16, t), vh - 300);
    const clampLeft = (l: number) => Math.min(Math.max(16, l), vw - CARD_W - 16);
    if (room.right >= CARD_W + GAP * 2) cardStyle = { left: rect.x + rect.w + GAP, top: clampTop(rect.y) };
    else if (room.left >= CARD_W + GAP * 2) cardStyle = { left: rect.x - CARD_W - GAP, top: clampTop(rect.y) };
    else if (room.below >= 260) cardStyle = { left: clampLeft(rect.x), top: rect.y + rect.h + GAP };
    else cardStyle = { left: clampLeft(rect.x), top: Math.max(16, rect.y - 280) };
  }

  const pad = 6;
  return (
    <div className="fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-label={`Guide: ${step.title}`}>
      {rect ? (
        <div
          className="pointer-events-none absolute border-2 border-acc transition-all duration-300 ease-out"
          style={{
            left: rect.x - pad,
            top: rect.y - pad,
            width: rect.w + pad * 2,
            height: rect.h + pad * 2,
            boxShadow: '0 0 0 9999px rgba(20,21,23,0.74)',
          }}
        />
      ) : (
        <div className="absolute inset-0 bg-ink/75" />
      )}
      {/* Clicks outside the card do nothing (keeps the tour from being lost by accident). */}
      <div className="absolute inset-0" />

      <div key={i} className="ef-panel absolute animate-fade-up" style={{ ...cardStyle, width: CARD_W }}>
        <div className="flex items-center justify-between border-b border-hair px-4 py-2">
          <span className="ef-label">{step.kicker}</span>
          <span className="font-mono text-[11px] text-sub">
            {String(i + 1).padStart(2, '0')}/{String(steps.length).padStart(2, '0')}
          </span>
        </div>
        <div className="px-4 pb-4 pt-3">
          <h3 className="font-cond text-[21px] font-bold uppercase leading-tight tracking-[0.06em]">{step.title}</h3>
          <div className="mt-2 text-[13.5px] leading-relaxed text-ink/85">{step.body}</div>
          <div className="mt-4 flex gap-0.5">
            {steps.map((_, k) => (
              <span key={k} className={`h-1 flex-1 ${k < i ? 'bg-ink' : k === i ? 'bg-acc' : 'bg-paper-3'}`} />
            ))}
          </div>
          <div className="mt-3 flex items-center gap-2">
            <button onClick={() => onClose(false)} className="ef-label mr-auto hover:text-ink">
              Skip guide
            </button>
            <button onClick={() => go(-1)} disabled={i === 0} className="ef-btn-line h-9 px-3 text-[12px]">
              Back
            </button>
            <button onClick={() => go(1)} className="ef-btn-acc h-9 px-4 text-[12px]" autoFocus>
              {last ? 'Start' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const KEY = 'codemusume.guide.v1';

export function guideSeen(): boolean {
  try {
    return window.localStorage.getItem(KEY) === 'done';
  } catch {
    return false;
  }
}

export function markGuideSeen(): void {
  try {
    window.localStorage.setItem(KEY, 'done');
  } catch {
    /* private mode: the guide simply shows again next time */
  }
}

const B: React.FC<{ children: React.ReactNode }> = ({ children }) => <b className="font-semibold text-ink">{children}</b>;

export const LAB_TOUR: TourStep[] = [
  {
    kicker: 'Guide',
    title: 'Welcome to the Tachyon Lab',
    body: (
      <>
        <p>
          You train a codebase like a racehorse, and Dr. Agnes Tachyon trains <B>you</B>. She will not hand you answers: she runs
          experiments on real code, makes you predict, then measures what really happens.
        </p>
        <p className="mt-2 text-sub">Two minutes. Arrow keys work too.</p>
      </>
    ),
  },
  {
    target: 'dock',
    kicker: 'Voice',
    title: 'Talk to Agnes',
    body: (
      <>
        Open the voice link and just talk: “start an experiment”, “I think it's B, and I'm certain”, “give me a hint”. She hears you
        and drives the game. No microphone? <B>Type</B> works for everything, and every action also has a button.
      </>
    ),
  },
  {
    target: 'stats',
    kicker: 'Trainee',
    title: 'Stats are measurements',
    body: (
      <>
        The trainee is <B>tachyon_lab</B>, a small service that is sick in five ways. Each stat is a fitness function measured on its
        running code: leaked file descriptors, p99 latency, SQL round trips, silent errors, modules dragged into a test. G is sick, S is
        healthy. Fix the code and the number moves.
      </>
    ),
  },
  {
    target: 'side',
    kicker: 'Experiments',
    title: 'Five chapters, one concept each',
    body: (
      <>
        Each experiment costs <B>20 energy</B> and a turn, and teaches one architecture idea: resource lifetimes, event-loop blocking,
        N+1 round trips, timeouts and honest failures, dependency direction.
      </>
    ),
  },
  {
    target: 'side',
    kicker: 'The loop',
    title: 'Predict, point, explain, treat, measure',
    body: (
      <ol className="list-none space-y-1">
        <li><B>01 Hypothesis</B> · bet on the outcome, with confidence. Certain-and-wrong is the lesson you keep.</li>
        <li><B>02 Evidence</B> · click the culprit line. The analyzers know which ones are right.</li>
        <li><B>03 Explain</B> · say why, in your words. Missing ideas come back as questions.</li>
        <li><B>04 Treatment</B> · pick a patch. Some are plausible and wrong; they get measured too.</li>
        <li><B>05 Re-measure</B> · before and after, on real code.</li>
      </ol>
    ),
  },
  {
    target: 'operations',
    kicker: 'Career',
    title: 'Twelve turns to the Derby',
    body: (
      <>
        Low on energy? <B>Rest</B>. When a concept comes due, a <B>pop quiz</B> appears (spaced repetition: right answers come back
        later, wrong ones tomorrow). After three experiments the <B>Grand Derby</B> unlocks: a benchmark race on your measured stats.
      </>
    ),
  },
  {
    target: 'tab-dossier',
    kicker: 'Dossier',
    title: 'What Agnes remembers',
    body: (
      <>
        Mastery per concept, your review schedule, prediction calibration, and your bond with her: at <B>Research Partner</B>
        experiments can trigger Eureka (×1.5). Finished careers enter the Hall of Fame and leave <B>sparks</B> that power your next one.
      </>
    ),
  },
  {
    target: 'mode',
    kicker: 'Free lab',
    title: 'Then bring your own code',
    body: (
      <>
        <B>Your repo</B> scans a local Python project: ten architecture checks (import cycles, volatile hubs, leaks, blocking calls,
        N+1, swallowed errors…), each linked to the chapter that teaches it. Static analysis only; your code never runs.
      </>
    ),
  },
  {
    target: 'guide',
    kicker: 'Ready',
    title: 'Start with experiment 01',
    body: <>The Leaking Lab is waiting. You can reopen this guide any time from here.</>,
  },
];
