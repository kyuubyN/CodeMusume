import React, { useEffect, useRef, useState } from 'react';
import { RaceTick } from '../types';
import { api } from '../services/api';
import { sounds } from '../services/audio';
import confetti from 'canvas-confetti';
import { Flag, Trophy, Sparkles, Volume2, ArrowLeft } from 'lucide-react';

interface Props {
  onBackToTraining: () => void;
}

export const RaceTrackCanvas: React.FC<Props> = ({ onBackToTraining }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [ticks, setTicks] = useState<RaceTick[]>([]);
  const [currentTickIndex, setCurrentTickIndex] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [isFinished, setIsFinished] = useState(false);
  const [liveCommentary, setLiveCommentary] = useState(
    'Atenção! As corredoras de arquitetura estão no portão de largada dos 2.000 metros!'
  );
  const [activeCallout, setActiveCallout] = useState<string | null>(null);

  // Load and start simulation
  useEffect(() => {
    let isMounted = true;

    async function loadRace() {
      try {
        const simulationTicks = await api.simulateRace();
        if (!isMounted) return;
        setTicks(simulationTicks);
        setIsRunning(true);
        sounds.playRaceStart();
      } catch (err) {
        console.error('Failed to load race:', err);
      }
    }

    loadRace();
    return () => {
      isMounted = false;
    };
  }, []);

  // Tick advancement timer (60ms per tick = ~6 seconds race)
  useEffect(() => {
    if (!isRunning || ticks.length === 0) return;

    if (currentTickIndex >= ticks.length - 1) {
      setIsRunning(false);
      setIsFinished(true);
      sounds.playSuccess();
      confetti({
        particleCount: 120,
        spread: 80,
        origin: { y: 0.6 },
      });
      return;
    }

    const timer = setTimeout(() => {
      const nextIndex = currentTickIndex + 1;
      setCurrentTickIndex(nextIndex);

      const tick = ticks[nextIndex];
      if (tick) {
        if (tick.commentary) {
          setLiveCommentary(tick.commentary);
        }
        if (tick.active_incident) {
          setActiveCallout(`${tick.active_incident.name}: ${tick.active_incident.tachyon_callout}`);
          sounds.playSkill();
        }
      }
    }, 65);

    return () => clearTimeout(timer);
  }, [isRunning, currentTickIndex, ticks]);

  // Canvas 2D Rendering Loop
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

    // Track dimensions
    const width = canvas.width;
    const height = canvas.height;

    // Clear background
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, width, height);

    // Draw Turf / Track lines
    ctx.fillStyle = '#166534'; // Grass top
    ctx.fillRect(0, 0, width, 40);

    ctx.fillStyle = '#78350f'; // Dirt track
    ctx.fillRect(0, 40, width, height - 80);

    ctx.fillStyle = '#166534'; // Grass bottom
    ctx.fillRect(0, height - 40, width, 40);

    // Lane dividing lines
    ctx.strokeStyle = '#fef08a';
    ctx.setLineDash([12, 10]);
    ctx.lineWidth = 2;

    const lane1Y = 70;
    const lane2Y = 120;
    const lane3Y = 170;

    [lane1Y, lane2Y].forEach((y) => {
      ctx.beginPath();
      ctx.moveTo(0, y + 25);
      ctx.lineTo(width, y + 25);
      ctx.stroke();
    });
    ctx.setLineDash([]); // Reset line dash

    // Distance calculation relative to viewport
    // Track 2000m mapped to canvas width (keeping runners in view)
    const maxDistance = 2000;
    const scale = (width - 100) / maxDistance;

    // Helper to draw runner
    const drawRunner = (
      name: string,
      distance: number,
      y: number,
      color: string,
      labelBg: string
    ) => {
      const x = 30 + Math.min(distance * scale, width - 60);

      // Dust / Speed trail
      if (isRunning) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.25)';
        ctx.beginPath();
        ctx.arc(x - 12, y + 10, 6, 0, Math.PI * 2);
        ctx.arc(x - 22, y + 12, 4, 0, Math.PI * 2);
        ctx.fill();
      }

      // Runner Avatar circle
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, 16, 0, Math.PI * 2);
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#ffffff';
      ctx.stroke();

      // Name tag
      ctx.fillStyle = labelBg;
      ctx.fillRect(x - 30, y - 28, 60, 14);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 8px Nunito, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(name.slice(0, 10), x, y - 18);
    };

    // Draw Runners
    // Player
    drawRunner('CodeMusume', currentTick.player_distance, lane1Y, '#06b6d4', '#0891b2');

    // Rival 1: Legacy Monolith
    const rival1Dist = currentTick.rivals?.[0]?.current_distance || 0;
    drawRunner('Monolith', rival1Dist, lane2Y, '#dc2626', '#991b1b');

    // Rival 2: Uncached Script
    const rival2Dist = currentTick.rivals?.[1]?.current_distance || 0;
    drawRunner('Uncached', rival2Dist, lane3Y, '#eab308', '#a16207');

    // Finish Line at 2,000m
    const finishX = 30 + 2000 * scale;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(finishX, 40);
    ctx.lineTo(finishX, height - 40);
    ctx.stroke();

    // Checkered pattern on finish line
    for (let py = 40; py < height - 40; py += 10) {
      ctx.fillStyle = (py / 10) % 2 === 0 ? '#000000' : '#ffffff';
      ctx.fillRect(finishX - 4, py, 8, 10);
    }
  }, [currentTickIndex, ticks, isRunning]);

  const currentTick = ticks[currentTickIndex];
  const distance = Math.round(currentTick?.player_distance || 0);

  return (
    <div className="w-full flex flex-col gap-2 p-3 bg-slate-950 text-slate-100">
      {/* Race Header */}
      <div className="flex items-center justify-between bg-slate-900/90 border border-slate-700 rounded-xl px-3 py-2">
        <div className="flex items-center gap-2">
          <Flag className="w-4 h-4 text-yellow-400" />
          <span className="text-xs font-black text-amber-300">
            URA PRODUCTION DERBY (2.000m)
          </span>
        </div>
        <div className="text-xs font-black text-cyan-300 tabular-nums">
          {distance}m / 2.000m
        </div>
      </div>

      {/* 2D Canvas Track */}
      <div className="relative rounded-2xl overflow-hidden border-2 border-slate-700 shadow-2xl bg-slate-900">
        <canvas
          ref={canvasRef}
          width={400}
          height={240}
          className="w-full h-auto block"
        />

        {/* Live Callout overlay */}
        {activeCallout && (
          <div className="absolute top-2 left-2 right-2 bg-gradient-to-r from-amber-500 to-rose-600 border border-yellow-200 text-white font-black text-[11px] px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-2 animate-bounce">
            <Sparkles className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{activeCallout}</span>
          </div>
        )}
      </div>

      {/* Live Jikkyou Commentary Box */}
      <div className="bg-slate-900/95 border border-slate-700/80 rounded-xl p-2.5 flex items-start gap-2 shadow-md">
        <Volume2 className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <span className="text-[10px] font-black text-amber-400 uppercase tracking-wider block">
            Jikkyou (Comentarista ao Vivo):
          </span>
          <p className="text-xs text-slate-200 font-semibold leading-relaxed">
            {liveCommentary}
          </p>
        </div>
      </div>

      {/* Result & Back Button */}
      {isFinished && (
        <div className="flex flex-col gap-2 mt-1 animate-fade-in">
          <div className="p-3 bg-gradient-to-r from-emerald-600 to-teal-700 rounded-xl border border-emerald-400 shadow-lg text-center">
            <div className="flex items-center justify-center gap-1.5 text-amber-300 font-black text-sm">
              <Trophy className="w-5 h-5 fill-amber-300" />
              <span>VITÓRIA! O REPOSITÓRIO CRUZA EM 1º LUGAR!</span>
            </div>
            <p className="text-xs text-emerald-100 font-semibold mt-0.5">
              O Legacy Monolith travou em gargalos e o Uncached Script estourou a memória!
            </p>
          </div>

          <button
            onClick={onBackToTraining}
            className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-600 font-black text-xs text-white transition-all flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>VOLTAR AO CENTRO DE TREINAMENTO</span>
          </button>
        </div>
      )}
    </div>
  );
};
