import React from 'react';
import type { MasteryView, ReviewView } from '../../types';

interface Props {
  review: ReviewView;
  concept?: MasteryView;
  busy: boolean;
  voiceLive: boolean;
  onAnswer: (letter: string) => void;
  onClose: () => void;
}

const LETTERS = 'ABCD';

export const ReviewCard: React.FC<Props> = ({ review, concept, busy, voiceLive, onAnswer, onClose }) => {
  const answered = review.answered !== null;
  const correct = answered && review.answered === review.correct_index;
  return (
    <section className="ef-panel flex h-full min-h-0 flex-col">
      <header className="flex items-baseline gap-3 border-b border-hair px-4 pb-2.5 pt-3.5">
        <h2 className="ef-title">Pop quiz</h2>
        <span className="ef-label">{concept?.title ?? review.concept}</span>
        <span className="ef-label ml-auto">spaced review</span>
      </header>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <p className="text-[15px] font-medium leading-relaxed">{review.prompt}</p>
        <pre className="scroll-thin mt-3 overflow-x-auto bg-ink px-3 py-2.5 font-mono text-[12px] leading-relaxed text-paper/90">{review.code}</pre>
        <div className="mt-3 flex flex-col gap-1.5">
          {review.options.map((o, i) => {
            const isRight = answered && review.correct_index === i;
            const isMine = answered && review.answered === i;
            return (
              <button
                key={i}
                disabled={answered || busy}
                onClick={() => onAnswer(LETTERS[i])}
                className={`flex items-start gap-3 border px-3 py-2.5 text-left text-[13px] leading-snug transition-colors ${
                  isRight ? 'border-ink bg-acc/40' : isMine ? 'border-bad bg-bad/10' : 'border-hair bg-paper enabled:hover:border-ink'
                }`}
              >
                <span className={`grid h-6 w-6 shrink-0 place-items-center font-cond text-[13px] font-bold ${isRight ? 'bg-ink text-acc' : isMine ? 'bg-bad text-paper' : 'bg-ink text-paper'}`}>
                  {LETTERS[i]}
                </span>
                <span className="whitespace-pre-line pt-0.5">{o}</span>
              </button>
            );
          })}
        </div>
        {answered ? (
          <div className="mt-4">
            <div className={`font-cond text-[20px] font-bold uppercase tracking-[0.08em] ${correct ? 'text-ink' : 'text-bad'}`}>
              {correct ? 'Recalled' : 'Not yet'}
            </div>
            <p className="mt-1 border-l-[3px] border-acc pl-3 text-[13.5px] leading-relaxed">{review.explanation}</p>
            <p className="mt-2 font-mono text-[11px] text-sub">
              {correct ? 'Moved up a box: the next review comes later.' : 'Back to box 1: you will see it again tomorrow.'}
            </p>
            <button onClick={onClose} className="ef-btn-dark mt-4 w-full">
              Back to the lab
            </button>
          </div>
        ) : (
          voiceLive && <p className="mt-3 font-mono text-[11px] text-sub">say the letter, or explain your choice</p>
        )}
      </div>
    </section>
  );
};
