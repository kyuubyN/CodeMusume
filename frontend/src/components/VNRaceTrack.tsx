import React, { useEffect, useRef, useState } from 'react';
import { QuizEvaluationResponse, QuizQuestion, RaceTick } from '../types';
import { api } from '../services/api';
import { sounds } from '../services/audio';
import confetti from 'canvas-confetti';
import {
  Flag,
  Trophy,
  Award,
  Sparkles,
  Volume2,
  CheckCircle2,
  XCircle,
  Brain,
  Play,
  RotateCcw,
} from 'lucide-react';

interface Props {
  onBackToTraining: () => void;
}

export const VNRaceTrack: React.FC<Props> = ({ onBackToTraining }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [ticks, setTicks] = useState<RaceTick[]>([]);
  const [currentTickIndex, setCurrentTickIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [isFinished, setIsFinished] = useState(false);
  const [finalPlace, setFinalPlace] = useState(1);
  const [liveCommentary, setLiveCommentary] = useState(
    'Alert: Contenders locked in starting gates for the 2,000m Grand Architecture Derby!'
  );
  const [activeCallout, setActiveCallout] = useState<string | null>(null);

  // Personalized Architecture Quiz State
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
  const [answeredCheckpoints, setAnsweredCheckpoints] = useState<Record<number, boolean>>({});
  const [currentCheckpointQuiz, setCurrentCheckpointQuiz] = useState<{
    question: QuizQuestion;
    checkpointIndex: number;
    distance: number;
  } | null>(null);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [quizFeedback, setQuizFeedback] = useState<QuizEvaluationResponse | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [quizScore, setQuizScore] = useState(0);
  const [playerSpeedMultiplier, setPlayerSpeedMultiplier] = useState(1.0);

  // Load race simulation & personalized architecture exam
  useEffect(() => {
    let isMounted = true;

    async function loadRaceAndQuiz() {
      try {
        const [simulationTicks, questions] = await Promise.all([
          api.simulateRace(),
          api.getRaceQuiz().catch((err) => {
            console.warn('Failed to load dynamic quiz, using default fallback:', err);
            return [];
          }),
        ]);
        if (!isMounted) return;
        setTicks(simulationTicks);
        setQuizQuestions(questions);
        setIsRunning(true);
        sounds.playRaceStart();
      } catch (err) {
        console.error('Failed to load race:', err);
      }
    }

    loadRaceAndQuiz();
    return () => {
      isMounted = false;
    };
  }, []);

  // Checkpoint Triggers (500m, 1000m, 1500m)
  useEffect(() => {
    if (!isRunning || ticks.length === 0 || quizQuestions.length === 0) return;
    const currentTick = ticks[currentTickIndex];
    if (!currentTick) return;

    const currentDist = currentTick.player_distance;

    if (currentDist >= 500 && !answeredCheckpoints[0] && quizQuestions[0]) {
      setIsRunning(false);
      setCurrentCheckpointQuiz({
        question: quizQuestions[0],
        checkpointIndex: 0,
        distance: 500,
      });
      setSelectedOption(null);
      setQuizFeedback(null);
      sounds.playSkill();
    } else if (currentDist >= 1000 && !answeredCheckpoints[1] && quizQuestions[1]) {
      setIsRunning(false);
      setCurrentCheckpointQuiz({
        question: quizQuestions[1],
        checkpointIndex: 1,
        distance: 1000,
      });
      setSelectedOption(null);
      setQuizFeedback(null);
      sounds.playSkill();
    } else if (currentDist >= 1500 && !answeredCheckpoints[2] && quizQuestions[2]) {
      setIsRunning(false);
      setCurrentCheckpointQuiz({
        question: quizQuestions[2],
        checkpointIndex: 2,
        distance: 1500,
      });
      setSelectedOption(null);
      setQuizFeedback(null);
      sounds.playSkill();
    }
  }, [currentTickIndex, isRunning, ticks, quizQuestions, answeredCheckpoints]);

  // Tick advancement — requestAnimationFrame with 60 ms delta accumulator
  useEffect(() => {
    if (!isRunning || ticks.length === 0) return;

    if (currentTickIndex >= ticks.length - 1) {
      const lastTick = ticks[ticks.length - 1];
      const pDist = (lastTick?.player_distance || 0) * playerSpeedMultiplier;
      const r1Dist = lastTick?.rivals?.[0]?.current_distance || 0;
      const r2Dist = lastTick?.rivals?.[1]?.current_distance || 0;

      let place = 1;
      if (r1Dist > pDist) place += 1;
      if (r2Dist > pDist) place += 1;

      // Architecture exam grading policy:
      // If 0 questions correct -> catastrophic outage (3rd place)
      // If 1 question correct -> at most 2nd place
      if (quizScore === 0) {
        place = 3;
      } else if (quizScore === 1 && place === 1) {
        place = 2;
      }

      setFinalPlace(place);
      setIsRunning(false);
      setIsFinished(true);

      if (place === 1) {
        sounds.playSuccess();
        confetti({
          particleCount: 150,
          spread: 90,
          origin: { y: 0.6 },
        });
      } else {
        sounds.playFailure();
      }

      // Complete race in backend to reset cycle
      api.completeRace(place, quizScore * 100).catch(console.error);
      return;
    }

    const TICK_MS = 60;
    let rafId: number;
    let lastTime: number | null = null;
    let accumulated = 0;

    const step = (now: number) => {
      if (lastTime !== null) {
        accumulated += now - lastTime;
      }
      lastTime = now;

      if (accumulated >= TICK_MS) {
        accumulated -= TICK_MS;
        setCurrentTickIndex((prev) => {
          const nextIndex = prev + 1;
          const tick = ticks[nextIndex];
          if (tick) {
            if (tick.commentary) setLiveCommentary(tick.commentary);
            if (tick.active_incident) {
              setActiveCallout(`${tick.active_incident.name}: ${tick.active_incident.tachyon_callout}`);
              sounds.playSkill();
            }
          }
          return nextIndex;
        });
      } else {
        rafId = requestAnimationFrame(step);
      }
    };

    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [isRunning, currentTickIndex, ticks, quizScore, playerSpeedMultiplier]);

  // Handle Quiz Answer Choice
  const handleSelectOption = async (optionIndex: number) => {
    if (isEvaluating || quizFeedback || !currentCheckpointQuiz) return;
    setSelectedOption(optionIndex);
    setIsEvaluating(true);

    try {
      const feedback = await api.evaluateRaceQuiz(
        currentCheckpointQuiz.question.id,
        optionIndex
      );
      setQuizFeedback(feedback);

      if (feedback.correct) {
        sounds.playSuccess();
        setQuizScore((prev) => prev + 1);
        setPlayerSpeedMultiplier((prev) => prev + 0.15);
        confetti({
          particleCount: 60,
          spread: 70,
          origin: { y: 0.5 },
        });
      } else {
        sounds.playFailure();
        setPlayerSpeedMultiplier((prev) => Math.max(0.6, prev - 0.2));
      }
    } catch (err) {
      console.error('Quiz evaluation error:', err);
      // Strictly treat evaluation failures as incorrect to avoid free victories
      setQuizFeedback({
        correct: false,
        correct_index: 0,
        explanation: 'Hehehe… Evaluation comms timed out! An architectural drag penalty was assessed.',
        speed_delta: -1.8,
      });
      setPlayerSpeedMultiplier((prev) => Math.max(0.6, prev - 0.2));
      sounds.playFailure();
    } finally {
      setIsEvaluating(false);
    }
  };

  // Resume Race after Checkpoint
  const handleResumeRace = () => {
    if (!currentCheckpointQuiz) return;
    sounds.playClick();
    setAnsweredCheckpoints((prev) => ({
      ...prev,
      [currentCheckpointQuiz.checkpointIndex]: true,
    }));
    setCurrentCheckpointQuiz(null);
    setIsRunning(true);
  };

  // 2D Canvas Racetrack Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const currentTick = ticks[currentTickIndex] || {
      player_distance: 0,
      rivals: [
        { name: 'Legacy Monolith', current_distance: 0 },
        { name: 'Uncached Script', current_distance: 0 },
      ],
    };

    const width = canvas.width;
    const height = canvas.height;

    // Clear background
    ctx.clearRect(0, 0, width, height);

    // Track bed background
    ctx.fillStyle = 'rgba(15, 20, 28, 0.85)';
    ctx.fillRect(0, 30, width, height - 60);

    // Turf rails
    ctx.fillStyle = '#166534';
    ctx.fillRect(0, 0, width, 30);
    ctx.fillRect(0, height - 30, width, 30);

    // White technical rail borders
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 30);
    ctx.lineTo(width, 30);
    ctx.moveTo(0, height - 30);
    ctx.lineTo(width, height - 30);
    ctx.stroke();

    // 3 Running Lanes
    const lane1Y = 65;
    const lane2Y = 125;
    const lane3Y = 185;

    ctx.strokeStyle = 'rgba(255, 208, 0, 0.35)';
    ctx.setLineDash([16, 12]);
    ctx.lineWidth = 1.5;

    [lane1Y + 30, lane2Y + 30].forEach((y) => {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    });
    ctx.setLineDash([]);

    // 2,000m scale
    const maxDistance = 2000;
    const scale = (width - 160) / maxDistance;

    // Checkpoint markers on the track
    [500, 1000, 1500].forEach((m, idx) => {
      const cx = 60 + m * scale;
      const isPassed = answeredCheckpoints[idx];
      ctx.strokeStyle = isPassed ? 'rgba(0, 240, 255, 0.6)' : 'rgba(255, 208, 0, 0.9)';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(cx, 30);
      ctx.lineTo(cx, height - 30);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = isPassed ? '#00f0ff' : '#ffd000';
      ctx.font = 'bold 8px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`AUDIT ${idx + 1} (${m}M)`, cx, 24);
    });

    // Draw individual runner
    const drawRunner = (
      name: string,
      distance: number,
      y: number,
      color: string,
      borderColor: string,
      isPlayer = false
    ) => {
      const x = 60 + Math.min(distance * scale, width - 90);

      // Speed dust/aura particles
      if (isRunning) {
        ctx.fillStyle = isPlayer && playerSpeedMultiplier > 1.0 ? 'rgba(0, 240, 255, 0.5)' : 'rgba(255, 255, 255, 0.3)';
        ctx.beginPath();
        ctx.arc(x - 16, y + 8, isPlayer ? 10 : 8, 0, Math.PI * 2);
        ctx.arc(x - 26, y + 10, isPlayer ? 7 : 5, 0, Math.PI * 2);
        ctx.fill();
      }

      // Runner circle
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, 18, 0, Math.PI * 2);
      ctx.fill();

      ctx.lineWidth = 2.5;
      ctx.strokeStyle = borderColor;
      ctx.stroke();

      // Tactical chevron / ears
      ctx.fillStyle = borderColor;
      ctx.beginPath();
      ctx.moveTo(x - 10, y - 16);
      ctx.lineTo(x - 5, y - 26);
      ctx.lineTo(x, y - 16);
      ctx.fill();

      ctx.beginPath();
      ctx.moveTo(x, y - 16);
      ctx.lineTo(x + 5, y - 26);
      ctx.lineTo(x + 10, y - 16);
      ctx.fill();

      // Tactical Name tag
      ctx.fillStyle = 'rgba(10, 14, 20, 0.95)';
      ctx.fillRect(x - 45, y - 44, 90, 14);
      ctx.strokeStyle = borderColor;
      ctx.lineWidth = 1;
      ctx.strokeRect(x - 45, y - 44, 90, 14);

      ctx.fillStyle = '#f0f3f6';
      ctx.font = 'bold 9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(name.toUpperCase(), x, y - 33);
    };

    // 1. Player: CodeMusume (Cyan + speed multiplier effect)
    const adjustedPlayerDist = (currentTick.player_distance || 0) * playerSpeedMultiplier;
    drawRunner('CodeMusume', adjustedPlayerDist, lane1Y, '#06b6d4', '#00f0ff', true);

    // 2. Rival 1: Legacy Monolith (Red)
    const rival1Dist = currentTick.rivals?.[0]?.current_distance || 0;
    drawRunner('Monolith', rival1Dist, lane2Y, '#dc2626', '#f87171');

    // 3. Rival 2: Uncached Script (Gold)
    const rival2Dist = currentTick.rivals?.[1]?.current_distance || 0;
    drawRunner('Uncached', rival2Dist, lane3Y, '#d97706', '#ffd000');

    // Finish Line at 2,000m
    const finishX = 60 + 2000 * scale;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(finishX, 20);
    ctx.lineTo(finishX, height - 20);
    ctx.stroke();

    // Checkered banner
    for (let py = 20; py < height - 20; py += 12) {
      ctx.fillStyle = (py / 12) % 2 === 0 ? '#000000' : '#ffffff';
      ctx.fillRect(finishX - 6, py, 12, 12);
    }
  }, [currentTickIndex, ticks, isRunning, playerSpeedMultiplier, answeredCheckpoints]);

  const currentTick = ticks[currentTickIndex];
  const distance = Math.min(2000, Math.round((currentTick?.player_distance || 0) * playerSpeedMultiplier));

  return (
    <div className="relative w-full h-full flex flex-col justify-between p-4 sm:p-6 z-20 text-[#f0f3f6] select-none font-mono">
      {/* Race Top Bar */}
      <div className="flex items-center justify-between bg-[#0a0d13]/98 border border-[#ffd000]/60 rounded-xl px-4 sm:px-6 py-2.5 shadow-xl">
        <div className="flex items-center gap-2.5">
          <Flag className="w-5 h-5 text-[#ffd000] fill-[#ffd000]" />
          <div>
            <span className="text-[10px] text-[#7b8594] tracking-widest block uppercase">
              PRODUCTION TELEMETRY // TRACK 01
            </span>
            <span className="text-xs sm:text-sm font-black text-[#ffd000] tracking-wider uppercase">
              GRAND ARCHITECTURE DERBY // 2,000M EXAM
            </span>
          </div>
        </div>

        {/* Exam Score & Progress Telemetry */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded bg-[#121620] border border-white/10">
            <Brain className="w-3.5 h-3.5 text-[#00f0ff]" />
            <span className="text-[10px] text-[#7b8594] uppercase font-bold">AUDIT SCORE:</span>
            <span className="text-xs font-black text-[#00f0ff]">{quizScore} / 3</span>
          </div>
          <div className="text-xs sm:text-sm font-black text-[#ffd000] tabular-nums tracking-widest">
            PROGRESS: {distance}M / 2,000M
          </div>
        </div>
      </div>

      {/* Racetrack Canvas Overlay */}
      <div className="relative w-full my-auto rounded-2xl overflow-hidden border border-white/20 shadow-[0_20px_60px_rgba(0,0,0,0.9)] bg-[#0c1017]/95">
        <canvas
          ref={canvasRef}
          width={1100}
          height={260}
          className="w-full h-auto block"
        />

        {/* Live Incident Callout */}
        {activeCallout && !currentCheckpointQuiz && (
          <div className="absolute top-4 left-6 right-6 bg-[#0f141f]/95 border-2 border-[#ffd000] text-white font-black text-xs md:text-sm px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2.5 animate-bounce">
            <Sparkles className="w-5 h-5 flex-shrink-0 text-[#ffd000]" />
            <span className="truncate text-[#ffd000]">{activeCallout}</span>
          </div>
        )}
      </div>

      {/* INTERACTIVE ARCHITECTURE CHECKPOINT EXAM MODAL (FULL SCREEN OVERLAY - NEVER CLIPPED) */}
      {currentCheckpointQuiz && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-3 sm:p-6 animate-fade-in font-mono">
          <div className="relative w-full max-w-xl max-h-[88vh] bg-[#0c1017] border-2 border-[#ffd000] rounded-2xl p-5 sm:p-6 shadow-[0_0_80px_rgba(255,208,0,0.45)] flex flex-col gap-3.5 text-[#f0f3f6] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-[#ffd000]/10 border border-[#ffd000]/40 text-[#ffd000]">
                  <Brain className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[9px] text-[#ffd000] font-black tracking-widest uppercase block">
                    CHECKPOINT AUDIT [{currentCheckpointQuiz.checkpointIndex + 1}/3] // {currentCheckpointQuiz.distance}M
                  </span>
                  <h3 className="text-sm font-black text-white tracking-wide">
                    DR. AGNES TACHYON'S ARCHITECTURE EXAM
                  </h3>
                </div>
              </div>
              {currentCheckpointQuiz.question.context_hint && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-[#161c28] border border-white/10 text-[#00f0ff] font-bold">
                  {currentCheckpointQuiz.question.context_hint}
                </span>
              )}
            </div>

            {/* Question Statement */}
            <div className="bg-[#121622] border border-white/10 rounded-xl p-3.5">
              <p className="text-xs sm:text-sm text-[#f0f3f6] font-semibold leading-relaxed">
                {currentCheckpointQuiz.question.question}
              </p>
            </div>

            {/* 4 Options Grid */}
            <div className="grid grid-cols-1 gap-2">
              {currentCheckpointQuiz.question.options.map((opt, idx) => {
                const isSelected = selectedOption === idx;
                const isCorrectAnswer = quizFeedback && quizFeedback.correct_index === idx;
                const isWrongSelected = quizFeedback && isSelected && !quizFeedback.correct;

                let cardStyle = 'bg-[#141a26] hover:bg-[#1a2233] border-white/10 text-white';
                if (isSelected && !quizFeedback) {
                  cardStyle = 'bg-[#ffd000]/15 border-[#ffd000] text-[#ffd000]';
                } else if (isCorrectAnswer) {
                  cardStyle = 'bg-emerald-500/20 border-emerald-400 text-emerald-300 font-bold';
                } else if (isWrongSelected) {
                  cardStyle = 'bg-rose-500/20 border-rose-400 text-rose-300';
                }

                return (
                  <button
                    key={idx}
                    disabled={isEvaluating || quizFeedback !== null}
                    onClick={() => handleSelectOption(idx)}
                    className={`flex items-start text-left gap-2.5 p-3 rounded-xl border text-xs sm:text-sm transition-all active:scale-[0.99] disabled:cursor-default ${cardStyle}`}
                  >
                    <span className="font-mono font-black text-xs opacity-75 shrink-0">
                      {String.fromCharCode(65 + idx)})
                    </span>
                    <span className="leading-snug">{opt.replace(/^[A-D]\)\s*/, '')}</span>
                  </button>
                );
              })}
            </div>

            {/* Feedback and Resume Button */}
            {quizFeedback ? (
              <div className="flex flex-col gap-2.5 pt-1 animate-fade-in">
                <div
                  className={`p-3 rounded-xl border text-xs sm:text-sm flex items-start gap-2.5 leading-relaxed ${
                    quizFeedback.correct
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                      : 'bg-rose-500/10 border-rose-500/40 text-rose-300'
                  }`}
                >
                  {quizFeedback.correct ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-black uppercase tracking-wider text-[10px]">
                        {quizFeedback.correct ? 'SURGE BOOST (+3.0 M/S)' : 'LATENCY DRAG (-1.8 M/S)'}
                      </span>
                    </div>
                    <p className="font-mono italic">"{quizFeedback.explanation}"</p>
                  </div>
                </div>

                <button
                  onClick={handleResumeRace}
                  className="w-full py-3 px-4 rounded-xl bg-[#ffd000] hover:bg-[#ffdb33] text-black font-black text-xs sm:text-sm tracking-wider transition-all active:scale-95 flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(255,208,0,0.4)] mt-1"
                >
                  <Play className="w-4 h-4 fill-black text-black" />
                  <span>RESUME DERBY & APPLY SPEED ADJUSTMENT</span>
                </button>
              </div>
            ) : (
              <div className="text-[10px] text-center text-[#7b8594] tracking-widest uppercase py-1">
                SELECT AN ARCHITECTURAL SOLUTION TO PROCEED
              </div>
            )}
          </div>
        </div>
      )}

      {/* Live Jikkyou Commentary & Controls */}
      <div className="w-full flex flex-col gap-2.5">
        <div className="bg-[#0a0d14]/98 border border-white/15 rounded-xl p-4 flex items-start gap-3 shadow-2xl">
          <Volume2 className="w-5 h-5 text-[#ffd000] flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="text-[10px] font-black text-[#ffd000] uppercase tracking-widest block mb-0.5">
              JIKKYOU COMMS // PLAY-BY-PLAY TELEMETRY:
            </span>
            <p className="text-xs sm:text-sm font-mono text-[#f0f3f6] leading-relaxed">
              "{liveCommentary}"
            </p>
          </div>
        </div>

        {/* Dynamic Race Finish Banner based on real placement */}
        {isFinished && (
          <div
            className={`flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-xl border shadow-2xl animate-fade-in ${
              finalPlace === 1
                ? 'bg-[#0f1826] border-emerald-400'
                : finalPlace === 2
                ? 'bg-[#18140e] border-amber-400/80'
                : 'bg-[#1a0e12] border-rose-500/80'
            }`}
          >
            <div className="flex items-center gap-3">
              {finalPlace === 1 ? (
                <Trophy className="w-8 h-8 text-[#ffd000] fill-[#ffd000] shrink-0" />
              ) : finalPlace === 2 ? (
                <Award className="w-8 h-8 text-amber-400 shrink-0" />
              ) : (
                <XCircle className="w-8 h-8 text-rose-500 shrink-0" />
              )}
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm sm:text-base font-black ${
                      finalPlace === 1
                        ? 'text-[#ffd000]'
                        : finalPlace === 2
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    }`}
                  >
                    {finalPlace === 1
                      ? '🏆 1ST PLACE — VICTORY! CodeMusume conquers the Grand Derby!'
                      : finalPlace === 2
                      ? '🥈 2ND PLACE — ARCHITECTURAL DEFEAT! Legacy Monolith was faster!'
                      : '🥉 3RD PLACE — PRODUCTION OUTAGE! CodeMusume finished last!'}
                  </span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold border ${
                      finalPlace === 1
                        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                        : finalPlace === 2
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                        : 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                    }`}
                  >
                    EXAM: {quizScore}/3 {finalPlace === 1 ? 'PASSED (Grade: SS)' : finalPlace === 2 ? 'CORRECT (Grade: C)' : 'FAILED (Grade: F)'}
                  </span>
                </div>
                <span className="text-[10px] text-[#7b8594] block mt-0.5">
                  {finalPlace === 1
                    ? 'ALL ENTERPRISE ARCHITECTURAL SLAS MET! QUALIFICATION CYCLE COMPLETED // RE-ENGAGING FRESH 10-INTERACTION LOOP'
                    : finalPlace === 2
                    ? 'LATENCY DRAG DETECTED! UNRESOLVED ANTI-PATTERNS COST THE VICTORY // CYCLE RESET TO 0/10 — TRAIN AND REFACTOR MORE'
                    : 'CATASTROPHIC ARCHITECTURAL FAILURES UNDER PRODUCTION LOAD! CYCLE RESET TO 0/10 — STUDY ENTERPRISE PATTERNS AND RETRY'}
                </span>
              </div>
            </div>

            <button
              onClick={onBackToTraining}
              className="py-2.5 px-6 rounded-lg bg-[#ffd000] hover:bg-[#ffdb33] text-black font-black text-xs tracking-wider transition-all active:scale-95 flex items-center gap-2 shrink-0 shadow-lg cursor-pointer"
            >
              <RotateCcw className="w-4 h-4" />
              <span>RETURN TO OPERATIONS (CYCLE RESET 0/10)</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
