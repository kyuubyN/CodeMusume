import React from 'react';
import type { AttributeType, CodeSmell, GameState, LabState } from '../types';
import { STATS, STAT_BAR_MAX, rankIsHigh, rankOf } from '../lib/game';

interface Props {
  state: GameState;
  lab: LabState | null;
  smells: CodeSmell[];
  busy: boolean;
  flash: Partial<Record<AttributeType, number>>;
  onTrain: (attr: AttributeType) => void;
  onExperiment: (chapter: number) => void;
  onReview: () => void;
  onRest: () => void;
  onRace: () => void;
  onShowSmells: (attr: AttributeType) => void;
}

export const StatsPanel: React.FC<Props> = ({
  state,
  lab,
  smells,
  busy,
  flash,
  onTrain,
  onExperiment,
  onReview,
  onRest,
  onRace,
  onShowSmells,
}) => {
  const inLab = state.mode === 'lab' && !!lab;
  const done = inLab ? lab!.experiments_done : state.interactions_in_cycle ?? 0;
  const required = inLab ? lab!.experiments_required : state.interactions_required ?? 3;
  const unlocked = state.race_unlocked ?? false;
  const over = state.is_game_over;
  const running =
    inLab && ((!!lab!.experiment && lab!.experiment.stage !== 'debrief') || (!!lab!.review && lab!.review.answered === null));
  const next = inLab ? lab!.chapters.find((c) => c.status === 'open') : undefined;
  const due = inLab ? lab!.mastery.filter((m) => m.due).length : 0;

  return (
    <div className="flex flex-col gap-3">
      <section className="ef-panel" data-tour="stats">
        <header className="flex items-baseline justify-between border-b border-hair px-4 pb-2.5 pt-3.5">
          <h2 className="ef-title">
            <span className="mr-2 text-faint">01</span>Trainee
          </h2>
          <span className="ef-label">{inLab ? 'measured, not guessed' : 'from real code'}</span>
        </header>
        <ul>
          {STATS.map((s) => {
            const score = state.attributes[s.key];
            const rank = rankOf(score);
            const gained = flash[s.key];
            const chapter = inLab ? lab!.chapters.find((c) => c.stat === s.key) : undefined;
            const open = smells.filter((x) => x.attribute === s.key && !x.drilled).length;
            const canAct = inLab ? chapter?.status === 'open' && !running && !over : !over;
            return (
              <li key={s.key} className="group relative border-b border-hair px-4 py-2.5 last:border-b-0">
                <div className="flex items-center gap-3">
                  <span
                    className={`grid h-9 w-9 shrink-0 place-items-center font-cond text-lg font-bold ${
                      rankIsHigh(rank) ? 'bg-acc text-ink' : 'bg-ink text-paper'
                    }`}
                    title={`Rank ${rank}`}
                  >
                    {rank}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between">
                      <span className="font-cond text-[15px] font-bold uppercase tracking-[0.1em]">{s.label}</span>
                      <span className="relative ef-num text-[22px]">
                        {score}
                        {gained ? (
                          <span key={gained} className="absolute -top-3.5 right-0 animate-fade-up bg-acc px-1 font-cond text-[11px] font-bold text-ink">
                            {gained > 0 ? '+' : ''}
                            {gained}
                          </span>
                        ) : null}
                      </span>
                    </div>
                    <div className="mt-1 h-[3px] bg-paper-3">
                      <div className="h-full bg-ink transition-[width] duration-700" style={{ width: `${Math.min(100, (score / STAT_BAR_MAX) * 100)}%` }} />
                    </div>
                    <div className="mt-1 flex items-center justify-between gap-2 text-[12px] text-sub">
                      {inLab ? (
                        <>
                          <span className="truncate font-mono text-[11px]">
                            {chapter?.measure ? `${chapter.measure.value} ${chapter.measure.unit}` : '…'}
                          </span>
                          <span className={`shrink-0 font-semibold ${chapter?.status === 'cleared' ? 'text-ink' : ''}`}>
                            {chapter?.status === 'cleared' ? `Ch.${chapter.id} cleared` : `Ch.${chapter?.id}`}
                          </span>
                        </>
                      ) : (
                        <>
                          <span className="truncate">{s.blurb}</span>
                          {open > 0 ? (
                            <button onClick={() => onShowSmells(s.key)} className="shrink-0 font-semibold text-ink underline-offset-2 hover:underline">
                              {open} smell{open > 1 ? 's' : ''}
                            </button>
                          ) : (
                            <span className="font-semibold text-ok">Clean</span>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
                {canAct && (
                  <button
                    onClick={() => (inLab && chapter ? onExperiment(chapter.id) : onTrain(s.key))}
                    disabled={busy}
                    className="ef-btn-acc absolute inset-y-0 right-0 hidden h-auto px-4 group-focus-within:flex group-hover:flex"
                  >
                    {inLab ? 'Experiment' : 'Train'}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="ef-panel" data-tour="operations">
        <header className="border-b border-hair px-4 pb-2.5 pt-3.5">
          <h2 className="ef-title">
            <span className="mr-2 text-faint">02</span>Operations
          </h2>
        </header>
        <div className="p-4">
          {over ? (
            <div className="mb-3 flex items-stretch">
              <span className="ef-hazard w-2 shrink-0" />
              <p className="flex-1 bg-ink px-3 py-2 text-[12.5px] text-paper">The season is over. The Grand Derby decides this career.</p>
            </div>
          ) : null}
          <div className="grid grid-cols-2 gap-2">
            {inLab ? (
              <button
                onClick={() => next && onExperiment(next.id)}
                disabled={busy || !next || running || over}
                className="ef-btn-dark col-span-2"
                title="Costs 20 energy"
              >
                {running ? (lab!.review ? 'Quiz open' : 'Experiment running') : next ? `Experiment ${String(next.id).padStart(2, '0')}` : 'All experiments cleared'}
              </button>
            ) : null}
            {inLab && (
              <button onClick={onReview} disabled={busy || due === 0 || running || over} className="ef-btn-line" title="Costs 10 energy">
                Review{due ? ` · ${due}` : ''}
              </button>
            )}
            <button onClick={onRest} disabled={busy || over || running} className="ef-btn-line">
              Rest
            </button>
            <button
              onClick={onRace}
              disabled={!unlocked || busy || running}
              className={`${unlocked ? 'ef-btn-acc' : 'ef-btn-line'} ${inLab ? 'col-span-2' : ''}`}
            >
              Grand Derby
            </button>
          </div>
          <div className="mt-4 flex items-baseline justify-between">
            <span className="ef-label">{inLab ? 'Experiments to qualify' : 'Derby qualification'}</span>
            <span className="ef-num text-sm">
              {Math.min(done, required)}/{required}
            </span>
          </div>
          <div className="mt-1.5 flex gap-1">
            {Array.from({ length: required }).map((_, i) => (
              <div key={i} className={`h-1.5 flex-1 transition-colors duration-500 ${i < done ? 'bg-acc' : 'bg-paper-3'}`} />
            ))}
          </div>
          {state.energy < 40 && !over && (
            <div className="mt-4 flex items-stretch">
              <span className="ef-hazard w-2 shrink-0" />
              <p className="bg-ink px-3 py-2 text-[12px] text-paper">
                Low energy. {inLab ? 'An experiment needs 20.' : 'Training may fail.'} Rest first.
              </p>
            </div>
          )}
          <p className="mt-4 text-[12px] leading-relaxed text-sub">
            {inLab ? 'Hover a stat to run its experiment, or just tell Agnes.' : 'Hover a stat to train it, or just tell Agnes.'}
          </p>
        </div>
      </section>
    </div>
  );
};
