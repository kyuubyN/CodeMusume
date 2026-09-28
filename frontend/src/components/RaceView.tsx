import React, { useCallback, useEffect, useRef, useState } from 'react';
import confetti from 'canvas-confetti';
import type { CareerSummary, DerbyQuestion, DerbySetup, QuizEvaluationResponse } from '../types';
import { api } from '../services/api';
import { sounds } from '../services/audio';
import { STAT_BY_KEY } from '../lib/game';

export interface QuizAnswerResult {
  correct: boolean;
  correct_option: string;
  explanation: string;
}

interface Props {
  voiceLive: boolean;
  onBack: () => void;
  onCheckpoint: (q: DerbyQuestion, index: number) => void;
  onFinished: (place: number, score: number) => void;
  onCareerComplete: (summary: CareerSummary) => void;
  /** The race registers how to answer the open checkpoint by voice. */
  registerAnswer: (fn: ((optionIndex: number) => Promise<QuizAnswerResult>) | null) => void;
}

const CHECKPOINTS = [500, 1000, 1500];
const TRACK = 2000;
const LETTERS = ['A', 'B', 'C', 'D'];
const PLACE = ['', '1st', '2nd', '3rd', '4th'];

export const RaceView: React.FC<Props> = ({ voiceLive, onBack, onCheckpoint, onFinished, onCareerComplete, registerAnswer }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgs = useRef<Record<string, HTMLImageElement>>({});
  const [setup, setSetup] = useState<DerbySetup | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState<number | null>(null);
  const [commentary, setCommentary] = useState('Benchmarking the trainee: every workload runs on the real code…');
  const [answered, setAnswered] = useState<boolean[]>([false, false, false]);
  const [quiz, setQuiz] = useState<{ q: DerbyQuestion; i: number } | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<QuizEvaluationResponse | null>(null);
  const [score, setScore] = useState(0);
  const [boost, setBoost] = useState(1);

  const ticks = setup?.ticks ?? [];
  const questions = setup?.questions ?? [];

  useEffect(() => {
    for (const src of ['/assets/race/runner_player.png', '/assets/race/runner_rival.png']) {
      if (!imgs.current[src]) {
        const im = new Image();
        im.src = src;
        imgs.current[src] = im;
      }
    }
  }, []);

  useEffect(() => {
    let alive = true;
    api
      .setupDerby()
      .then((s) => {
        if (!alive) return;
        setSetup(s);
        setCommentary('The contenders are in the gate. Measured stats set the pace; mastered concepts fire as skills.');
        setRunning(true);
        sounds.playRaceStart();
      })
      .catch((err: Error) => setError(err.message));
    return () => {
      alive = false;
    };
  }, []);

  const playerDist = (i: number) => Math.min(TRACK, (ticks[i]?.player_distance ?? 0) * boost);

  // Checkpoints
  useEffect(() => {
    if (!running || !ticks.length) return;
    const d = playerDist(idx);
    const i = CHECKPOINTS.findIndex((m, k) => d >= m && !answered[k]);
    if (i >= 0 && questions[i]) {
      setRunning(false);
      setQuiz({ q: questions[i], i });
      setSelected(null);
      setFeedback(null);
      sounds.playSkill();
      onCheckpoint(questions[i], i);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, running, ticks, questions, answered]);

  // Tick loop
  useEffect(() => {
    if (!running || !ticks.length) return;
    if (idx >= ticks.length - 1) {
      const last = ticks[ticks.length - 1];
      const p = playerDist(ticks.length - 1);
      let place = 1 + (last.rivals ?? []).filter((r) => r.current_distance > p).length;
      if (score === 0) place = Math.max(place, 3);
      else if (score === 1 && place === 1) place = 2;
      setRunning(false);
      setFinished(place);
      if (place === 1) {
        sounds.playSuccess();
        confetti({ particleCount: 140, spread: 80, origin: { y: 0.55 }, colors: ['#ffe100', '#141517', '#f1f1ee'] });
      } else sounds.playFailure();
      onFinished(place, score);
      api
        .completeDerby(place, score)
        .then((summary) => window.setTimeout(() => onCareerComplete(summary), 1600))
        .catch(console.error);
      return;
    }
    const t = window.setTimeout(() => {
      const next = ticks[idx + 1];
      if (next?.commentary) setCommentary(next.commentary);
      if (next?.active_incident) setCommentary(`${next.active_incident.name}. ${next.active_incident.tachyon_callout}`);
      setIdx(idx + 1);
    }, 60);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, idx, ticks]);

  const resume = useCallback(() => {
    setQuiz((cur) => {
      if (cur) setAnswered((a) => a.map((v, k) => (k === cur.i ? true : v)));
      return null;
    });
    setRunning(true);
  }, []);

  const answer = useCallback(
    async (option: number): Promise<QuizAnswerResult> => {
      if (!quiz) throw new Error('No checkpoint question is open right now.');
      if (feedback) {
        return { correct: feedback.correct, correct_option: LETTERS[feedback.correct_index], explanation: 'Already answered.' };
      }
      setSelected(option);
      let fb: QuizEvaluationResponse;
      try {
        fb = await api.answerCheckpoint(quiz.q.id, option);
      } catch {
        fb = { correct: false, correct_index: 0, explanation: 'Evaluation timed out.', speed_delta: -1.8 };
      }
      setFeedback(fb);
      if (fb.correct) {
        sounds.playSuccess();
        setScore((s) => s + 1);
        setBoost((b) => b + 0.15);
      } else {
        sounds.playFailure();
        setBoost((b) => Math.max(0.6, b - 0.2));
      }
      if (voiceLive) window.setTimeout(resume, 5500);
      return { correct: fb.correct, correct_option: LETTERS[fb.correct_index], explanation: fb.explanation };
    },
    [quiz, feedback, voiceLive, resume]
  );

  useEffect(() => {
    registerAnswer(quiz && !feedback ? answer : null);
  }, [quiz, feedback, answer, registerAnswer]);
  useEffect(() => () => registerAnswer(null), [registerAnswer]);

  // Draw
  useEffect(() => {
    const c = canvasRef.current;
    const ctx = c?.getContext('2d');
    if (!c || !ctx || !setup) return;
    const W = c.width;
    const H = c.height;
    const left = 90;
    const right = W - 60;
    const scale = (right - left) / TRACK;
    const lanes = setup.runners.length;
    const laneH = (H - 40) / lanes;

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#141517';
    ctx.fillRect(0, 0, W, H);
    for (let l = 0; l < lanes; l++) {
      ctx.fillStyle = l % 2 ? '#1a1b1e' : '#1d1e21';
      ctx.fillRect(0, 20 + l * laneH, W, laneH);
    }
    ctx.font = '600 11px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    for (let m = 0; m <= TRACK; m += 250) {
      const x = left + m * scale;
      ctx.fillStyle = 'rgba(241,241,238,0.08)';
      ctx.fillRect(x, 20, 1, H - 40);
      ctx.fillStyle = 'rgba(241,241,238,0.35)';
      ctx.fillText(`${m}`, x, H - 6);
    }
    CHECKPOINTS.forEach((m, k) => {
      const x = left + m * scale;
      ctx.fillStyle = answered[k] ? 'rgba(241,241,238,0.5)' : '#ffe100';
      ctx.fillRect(x - 1, 20, 2, H - 40);
      ctx.font = '700 12px "Barlow Condensed", sans-serif';
      ctx.fillText(`CP${k + 1}`, x, 13);
    });
    const fx = left + TRACK * scale;
    for (let y = 20; y < H - 20; y += 8) {
      ctx.fillStyle = (y / 8) % 2 ? '#f1f1ee' : '#141517';
      ctx.fillRect(fx - 4, y, 4, 8);
      ctx.fillStyle = (y / 8) % 2 ? '#141517' : '#f1f1ee';
      ctx.fillRect(fx, y, 4, 8);
    }

    const tick = ticks[idx];
    setup.runners.forEach((r, l) => {
      const d = l === 0 ? playerDist(idx) : tick?.rivals?.[l - 1]?.current_distance ?? 0;
      const x = left + Math.min(d, TRACK) * scale;
      const cy = 20 + l * laneH + laneH / 2;
      const img = imgs.current[l === 0 ? '/assets/race/runner_player.png' : '/assets/race/runner_rival.png'];
      const h = laneH * 0.92;
      const w = h * (2 / 3);
      const bob = running ? Math.sin(idx * 1.3 + l) * 2 : 0;
      if (l === 0) {
        ctx.fillStyle = 'rgba(255,225,0,0.12)';
        ctx.fillRect(0, 20 + l * laneH, x, laneH);
      }
      if (img?.complete && img.naturalWidth) {
        ctx.globalAlpha = r.id === 'ghost' ? 0.55 : 1;
        ctx.drawImage(img, x - w / 2, cy - h / 2 + bob, w, h);
        ctx.globalAlpha = 1;
      }
      // lane label
      ctx.textAlign = 'left';
      ctx.font = '700 12px "Barlow Condensed", sans-serif';
      ctx.fillStyle = l === 0 ? '#ffe100' : 'rgba(241,241,238,0.75)';
      ctx.fillText(r.name.toUpperCase().slice(0, 14), 8, cy + 4);
      ctx.textAlign = 'center';
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, ticks, answered, boost, running, setup]);

  const dist = Math.round(playerDist(idx));

  return (
    <div className="relative z-10 flex h-full flex-col gap-3 p-4 md:p-6">
      <header className="ef-panel flex items-center gap-5 px-5 py-3">
        <button onClick={onBack} className="ef-label hover:text-ink" disabled={running}>
          ← Lab
        </button>
        <div>
          <div className="ef-label">Grand Derby</div>
          <div className="font-cond text-[20px] font-bold uppercase leading-none tracking-[0.08em]">2,000 m benchmark race</div>
        </div>
        <div className="flex-1" />
        {setup && setup.skills.length > 0 && (
          <div className="hidden items-center gap-1.5 lg:flex">
            {setup.skills.map((s) => (
              <span key={s.concept} className="border border-ink px-1.5 py-0.5 font-cond text-[11px] font-bold uppercase tracking-[0.12em]">
                {STAT_BY_KEY[s.stat].short} lv{s.level}
              </span>
            ))}
          </div>
        )}
        <div className="text-right">
          <div className="ef-label">Checkpoints</div>
          <div className="ef-num text-[20px]">{score}/3</div>
        </div>
        <div className="w-44">
          <div className="flex justify-between">
            <span className="ef-label">Distance</span>
            <span className="font-mono text-[12px]">{dist} m</span>
          </div>
          <div className="mt-1.5 h-1.5 bg-paper-3">
            <div className="h-full bg-ink" style={{ width: `${(dist / TRACK) * 100}%` }} />
          </div>
        </div>
      </header>

      <div className="ef-panel my-auto overflow-hidden">
        {error ? (
          <div className="p-6">
            <p className="font-cond text-[18px] font-bold uppercase">The Derby could not start</p>
            <p className="mt-1 text-sm text-sub">{error}</p>
            <button onClick={onBack} className="ef-btn-dark mt-4">Back to the lab</button>
          </div>
        ) : (
          <>
            <canvas ref={canvasRef} width={1200} height={320} className="block h-auto w-full" />
            <div className="flex items-center gap-3 border-t border-hair px-5 py-3">
              <span className={`h-2 w-2 ${running ? 'animate-blink bg-acc' : 'bg-faint'}`} />
              <p className="text-[13.5px] font-medium">{setup ? commentary : 'Benchmarking the trainee…'}</p>
            </div>
            {setup && (
              <div className="grid grid-cols-5 gap-px border-t border-hair bg-hair">
                {Object.entries(setup.attributes).map(([k, v]) => (
                  <div key={k} className="bg-paper px-3 py-1.5">
                    <div className="font-cond text-[10px] font-bold uppercase tracking-[0.16em] text-sub">{k}</div>
                    <div className="font-mono text-[13px]">{v}</div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {finished !== null && (
        <div className="ef-panel mx-auto flex w-full max-w-2xl animate-pop-in items-stretch">
          <div className={`flex items-center px-6 ${finished === 1 ? 'bg-acc' : 'bg-ink text-paper'}`}>
            <span className="ef-num text-[48px]">{PLACE[finished]}</span>
          </div>
          <div className="flex-1 px-5 py-4">
            <div className="font-cond text-[18px] font-bold uppercase tracking-[0.08em]">
              {finished === 1 ? 'Your trainee won the Derby' : 'Not first this time'}
            </div>
            <div className="text-[13px] text-sub">{score}/3 checkpoints correct. Tallying the career…</div>
          </div>
        </div>
      )}

      {quiz && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/75 p-4">
          <div className="ef-panel w-full max-w-xl animate-pop-in">
            <div className="flex items-center gap-2 border-b border-hair px-5 py-3">
              <span className="ef-tag bg-acc text-ink">Checkpoint {quiz.i + 1}/3</span>
              <span className="ef-label">{CHECKPOINTS[quiz.i]} m</span>
            </div>
            <div className="px-5 py-4">
              <p className="text-[15px] font-medium leading-relaxed">{quiz.q.question}</p>
              <pre className="scroll-thin mt-3 overflow-x-auto bg-ink px-3 py-2 font-mono text-[12px] leading-relaxed text-paper/90">{quiz.q.code}</pre>
              <div className="mt-3 flex flex-col gap-1.5">
                {quiz.q.options.map((opt, k) => {
                  const isSel = selected === k;
                  const isRight = feedback && feedback.correct_index === k;
                  const isWrong = feedback && isSel && !feedback.correct;
                  return (
                    <button
                      key={k}
                      disabled={!!feedback || selected !== null}
                      onClick={() => void answer(k)}
                      className={`flex items-start gap-3 border px-3 py-2.5 text-left text-[13px] leading-snug transition-colors ${
                        isRight ? 'border-ink bg-acc/40' : isWrong ? 'border-bad bg-bad/10' : isSel ? 'border-ink bg-paper-2' : 'border-hair bg-paper enabled:hover:border-ink'
                      }`}
                    >
                      <span className="grid h-6 w-6 shrink-0 place-items-center bg-ink font-cond text-[13px] font-bold text-paper">{LETTERS[k]}</span>
                      <span className="whitespace-pre-line pt-0.5">{opt}</span>
                    </button>
                  );
                })}
              </div>
              {feedback ? (
                <div className="mt-4">
                  <div className={`font-cond text-[16px] font-bold uppercase tracking-[0.1em] ${feedback.correct ? '' : 'text-bad'}`}>
                    {feedback.correct ? 'Correct · speed up' : 'Wrong · the pack closes in'}
                  </div>
                  <p className="mt-1 border-l-[3px] border-acc pl-3 text-[13px] leading-relaxed">{feedback.explanation}</p>
                  <button onClick={resume} className="ef-btn-dark mt-3 w-full">
                    {voiceLive ? 'Resume now' : 'Resume race'}
                  </button>
                </div>
              ) : (
                voiceLive && <p className="mt-3 font-mono text-[11px] text-sub">say your answer: “B”, or describe it</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
