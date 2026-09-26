import React, { useState, useEffect, useRef } from 'react';
import { AttributeType } from '../types';
import { Activity, Dumbbell, Zap, Flame, Brain, FlaskConical, Globe, Search, Radio, Sparkles } from 'lucide-react';
import './TrainingAnimationModal.css';

interface Props {
  attribute: AttributeType;
  customPrompt?: string;
}

interface TrainingArtworkMeta {
  src: string;
  name: string;
  category: string;
  japaneseTitle: string;
  kanjiBadge: string;
  themeColor: string;
  glowColor: string;
  borderColor: string;
  accentTextColor: string;
  badgeBg: string;
  icon: (className?: string) => React.ReactNode;
  loreSubtitle: string;
}

export const TRAINING_ARTWORK_MAP: Record<AttributeType, TrainingArtworkMeta> = {
  speed: {
    src: '/assets/animations/speed_training.png',
    name: 'SPEED // ASYNC LATENCY ACCELERATION',
    category: 'TRAINING CUTSCENE // PROTOCOL 01',
    japaneseTitle: 'スピード特訓・非同期超加速演算',
    kanjiBadge: '速',
    themeColor: '#00f0ff',
    glowColor: 'rgba(0, 240, 255, 0.45)',
    borderColor: '#00f0ff',
    accentTextColor: 'text-[#00f0ff]',
    badgeBg: 'bg-[#00f0ff]/15',
    icon: (cls = 'w-5 h-5') => <Zap className={`${cls} text-[#00f0ff]`} />,
    loreSubtitle: 'Python Asyncio Event Loop & Microsecond Tail Latency Tuning',
  },
  stamina: {
    src: '/assets/animations/stamina_training.png',
    name: 'STAMINA // MEMORY INTEGRITY MATRIX',
    category: 'TRAINING CUTSCENE // PROTOCOL 02',
    japaneseTitle: 'スタミナ特訓・メモリ保護持続回路',
    kanjiBadge: '耐',
    themeColor: '#ff3385',
    glowColor: 'rgba(255, 51, 133, 0.45)',
    borderColor: '#ff3385',
    accentTextColor: 'text-pink-400',
    badgeBg: 'bg-pink-500/15',
    icon: (cls = 'w-5 h-5') => <FlaskConical className={`${cls} text-pink-400`} />,
    loreSubtitle: 'Tracemalloc Heap Profiling & Reference Cycle Elimination',
  },
  power: {
    src: '/assets/animations/power_training.jpeg',
    name: 'POWER // CONCURRENCY THROUGHPUT',
    category: 'TRAINING CUTSCENE // PROTOCOL 03',
    japaneseTitle: 'パワー特訓・高並行スループット爆縮',
    kanjiBadge: '力',
    themeColor: '#ffd000',
    glowColor: 'rgba(255, 208, 0, 0.45)',
    borderColor: '#ffd000',
    accentTextColor: 'text-[#ffd000]',
    badgeBg: 'bg-[#ffd000]/15',
    icon: (cls = 'w-5 h-5') => <Dumbbell className={`${cls} text-[#ffd000]`} />,
    loreSubtitle: 'Distributed Multiprocessing & High-Batch Workload Bandwidth',
  },
  guts: {
    src: '/assets/animations/guts_training.jpeg',
    name: 'GUTS // CHAOS FAULT RESILIENCE',
    category: 'TRAINING CUTSCENE // PROTOCOL 04',
    japaneseTitle: '根性特訓・耐障害カオスエンジニアリング',
    kanjiBadge: '根',
    themeColor: '#ff4d4d',
    glowColor: 'rgba(255, 77, 77, 0.45)',
    borderColor: '#ff4d4d',
    accentTextColor: 'text-rose-500',
    badgeBg: 'bg-rose-500/15',
    icon: (cls = 'w-5 h-5') => <Flame className={`${cls} text-rose-500`} />,
    loreSubtitle: 'Circuit Breaker Fallback & Cascading Failure Containment',
  },
  wisdom: {
    src: '/assets/animations/wise_training.jpeg',
    name: 'WISDOM // DOMAIN CLEAN ARCHITECTURE',
    category: 'TRAINING CUTSCENE // PROTOCOL 05',
    japaneseTitle: '賢さ特訓・ドメイン駆動クリーン統合',
    kanjiBadge: '賢',
    themeColor: '#00ff9d',
    glowColor: 'rgba(0, 255, 157, 0.45)',
    borderColor: '#00ff9d',
    accentTextColor: 'text-emerald-400',
    badgeBg: 'bg-emerald-500/15',
    icon: (cls = 'w-5 h-5') => <Brain className={`${cls} text-emerald-400`} />,
    loreSubtitle: 'DDD Bounded Contexts & Decoupled Event-Driven Synapses',
  },
};

// Global background preloading for instant zero-flicker display
if (typeof window !== 'undefined') {
  const preloadArtwork = () => {
    Object.values(TRAINING_ARTWORK_MAP).forEach((meta) => {
      const img = new Image();
      img.src = meta.src;
    });
  };
  if (document.readyState === 'complete') {
    preloadArtwork();
  } else {
    window.addEventListener('load', preloadArtwork, { once: true });
  }
}

const MCP_RESEARCH_QUERIES: Record<AttributeType, string> = {
  speed: 'python asyncio event loop latency optimization best practices 2026',
  stamina: 'python memory leak detection garbage collection tracemalloc reference cycles',
  power: 'high throughput concurrency multiprocessing distributed batching python',
  guts: 'circuit breaker pattern resilience chaos engineering python',
  wisdom: 'domain driven design event driven architecture clean architecture 2026',
};

const STATUS_MSGS = [
  'INITIALIZING DUCKDUCKGO MCP STDIO CLIENT PROTOCOL...',
  'QUERYING LIVE WEB LITERATURE VIA DUCKDUCKGO-MCP-SERVER...',
  'SYNCHRONIZING RECENT 2026 ARCHITECTURAL STANDARDS...',
  'INGESTING NEW FINDINGS INTO DR. AGNES TACHYON SYNAPTIC MEMORY...',
  'COMPOUNDING PHARMACOLOGICAL REFACTORING ELIXIR...',
  'EVALUATING P99 LATENCY SLAS & TAIL LATENCY BUFFERS...',
];

export const TrainingAnimationModal: React.FC<Props> = ({ attribute, customPrompt }) => {
  const [msgIndex, setMsgIndex] = useState(0);
  const [dots, setDots] = useState('');
  const [imageLoaded, setImageLoaded] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  const meta = TRAINING_ARTWORK_MAP[attribute] || TRAINING_ARTWORK_MAP.speed;

  // Check image caching & load state
  useEffect(() => {
    setImageLoaded(false);
    const testImg = new Image();
    testImg.src = meta.src;
    if (testImg.complete && testImg.naturalWidth > 0) {
      setImageLoaded(true);
    } else {
      testImg.onload = () => setImageLoaded(true);
      testImg.onerror = () => setImageLoaded(true); // gracefully fall back
    }
  }, [attribute, meta.src]);

  useEffect(() => {
    const msgTimer = setInterval(() => {
      setMsgIndex((prev) => (prev + 1) % STATUS_MSGS.length);
    }, 1100);

    const dotTimer = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? '' : prev + '.'));
    }, 300);

    return () => {
      clearInterval(msgTimer);
      clearInterval(dotTimer);
    };
  }, []);

  const activeQuery = customPrompt || MCP_RESEARCH_QUERIES[attribute] || 'enterprise architecture 2026';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-5 bg-black/90 backdrop-blur-md animate-fade-in font-mono select-none overflow-y-auto"
      style={{ contain: 'layout paint' }}
    >
      {/* Scanline CRT overlay */}
      <div
        className="fixed inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.4) 50%)',
          backgroundSize: '100% 4px',
        }}
      />

      {/* Main Modal Card */}
      <div
        className="relative w-full max-w-xl md:max-w-2xl lg:max-w-3xl bg-[#0c1017] border-2 rounded-2xl p-4 md:p-6 flex flex-col gap-3.5 text-[#f0f3f6] shadow-2xl my-auto transition-all duration-300"
        style={{
          borderColor: meta.borderColor,
          boxShadow: `0 0 60px ${meta.glowColor}, inset 0 0 20px rgba(0,0,0,0.8)`,
        }}
      >
        {/* Top Header Bar */}
        <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-xl ${meta.badgeBg} border`} style={{ borderColor: `${meta.borderColor}55` }}>
              {meta.icon('w-5 h-5')}
            </div>
            <div>
              <div className="flex items-center gap-1.5 text-[9px] md:text-[10px] tracking-widest font-black uppercase" style={{ color: meta.themeColor }}>
                <Globe className="w-3.5 h-3.5 animate-spin" />
                <span>{meta.category}</span>
              </div>
              <h2 className="text-xs md:text-sm font-black tracking-wide text-white flex items-center gap-2">
                <span>{meta.name}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-white/10 text-slate-300 font-normal">
                  {meta.kanjiBadge}
                </span>
              </h2>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-[#121620] border border-white/10">
            <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span className="text-[9px] text-[#7b8594] font-black tracking-widest uppercase">
              LIVE RESEARCH ACTIVE
            </span>
          </div>
        </div>

        {/* 16:9 Cutscene Artwork Frame */}
        <div
          className="relative w-full aspect-video rounded-xl overflow-hidden border bg-[#080b10] shadow-[0_12px_40px_rgba(0,0,0,0.9)] flex items-center justify-center group"
          style={{
            borderColor: `${meta.borderColor}77`,
            aspectRatio: '16 / 9',
          }}
        >
          {/* Skeleton Shimmer while image resolves */}
          {!imageLoaded && (
            <div className="absolute inset-0 bg-[#10141f] flex flex-col items-center justify-center gap-3">
              <div
                className="w-16 h-16 rounded-full flex items-center justify-center animate-pulse border-2"
                style={{ borderColor: meta.themeColor, backgroundColor: `${meta.themeColor}15` }}
              >
                {meta.icon('w-8 h-8')}
              </div>
              <span className="text-[10px] tracking-widest uppercase animate-pulse" style={{ color: meta.themeColor }}>
                SYNCHRONIZING CUTSCENE DATA{dots}
              </span>
            </div>
          )}

          {/* Actual Cutscene Image */}
          <img
            ref={imgRef}
            src={meta.src}
            alt={`${attribute} training cutscene artwork`}
            className={`w-full h-full object-cover object-center transition-all duration-700 ease-out transform ${
              imageLoaded ? 'opacity-100 scale-100' : 'opacity-0 scale-105'
            }`}
            onLoad={() => setImageLoaded(true)}
            loading="eager"
            decoding="async"
          />

          {/* CRT scanline texture over cutscene */}
          <div
            className="absolute inset-0 pointer-events-none opacity-20"
            style={{
              backgroundImage: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.4) 50%)',
              backgroundSize: '100% 3px',
            }}
          />

          {/* Vertical moving laser scanline */}
          <div
            className="cutscene-scanline-v absolute left-0 right-0 h-[2px] pointer-events-none"
            style={{
              background: `linear-gradient(90deg, transparent, ${meta.themeColor}, transparent)`,
              boxShadow: `0 0 8px ${meta.themeColor}`,
            }}
          />

          {/* HUD Corner Reticles */}
          <div
            className="reticle-breathe-fx absolute top-2.5 left-2.5 w-4 h-4 border-t-2 border-l-2 pointer-events-none"
            style={{ borderColor: meta.themeColor }}
          />
          <div
            className="reticle-breathe-fx absolute top-2.5 right-2.5 w-4 h-4 border-t-2 border-r-2 pointer-events-none"
            style={{ borderColor: meta.themeColor }}
          />
          <div
            className="reticle-breathe-fx absolute bottom-2.5 left-2.5 w-4 h-4 border-b-2 border-l-2 pointer-events-none"
            style={{ borderColor: meta.themeColor }}
          />
          <div
            className="reticle-breathe-fx absolute bottom-2.5 right-2.5 w-4 h-4 border-b-2 border-r-2 pointer-events-none"
            style={{ borderColor: meta.themeColor }}
          />

          {/* Lens sweep sheen effect */}
          <div className="cutscene-sweep-fx absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-white/10 to-transparent pointer-events-none skew-x-12" />

          {/* Bottom Cutscene Info Scrim */}
          <div className="absolute inset-x-0 bottom-0 p-3 pt-8 bg-gradient-to-t from-black/95 via-black/60 to-transparent flex items-end justify-between pointer-events-none">
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] md:text-[11px] font-black tracking-widest uppercase flex items-center gap-1.5" style={{ color: meta.themeColor }}>
                <Sparkles className="w-3 h-3" />
                <span>{meta.japaneseTitle}</span>
              </span>
              <span className="text-[9px] md:text-[10px] text-slate-300 font-sans tracking-wide">
                {meta.loreSubtitle}
              </span>
            </div>

            <div className="hidden sm:flex flex-col items-end">
              <span className="text-[8px] text-[#7b8594] tracking-widest uppercase font-mono">
                VISUAL NOVEL PROTOCOL
              </span>
              <span className="text-[9px] font-black text-white/90">
                16:9 HIGH-FIDELITY CUTSCENE
              </span>
            </div>
          </div>
        </div>

        {/* Live DuckDuckGo Query Box */}
        <div className="w-full bg-[#121620] border border-white/10 rounded-xl p-2.5 md:p-3 flex flex-col gap-1 text-left">
          <div className="flex items-center gap-1.5 text-[9px] text-[#7b8594] font-black tracking-wider uppercase">
            <Search className="w-3 h-3 text-[#00f0ff]" />
            <span>ACTIVE MCP SEARCH QUERY (DUCKDUCKGO-MCP-SERVER):</span>
          </div>
          <p className="text-xs text-[#00f0ff] font-bold truncate">
            "{activeQuery}"
          </p>
        </div>

        {/* Rotating Telemetry Status Line */}
        <div
          className="w-full bg-[#161c28] border rounded-xl p-2.5 md:p-3 min-h-[44px] flex items-center justify-center transition-colors"
          style={{ borderColor: `${meta.borderColor}55` }}
        >
          <p
            className="text-[11px] md:text-xs font-bold tracking-wide animate-pulse text-center"
            style={{ color: meta.themeColor }}
          >
            {STATUS_MSGS[msgIndex]}
          </p>
        </div>

        {/* Striped Cyber Progress Bar */}
        <div className="w-full h-2.5 rounded-full bg-[#161c28] border border-white/10 overflow-hidden relative">
          <div
            className="h-full progress-striped w-full rounded-full transition-all duration-300"
            style={{
              background: `linear-gradient(90deg, ${meta.themeColor}aa, ${meta.themeColor}, #00f0ff)`,
            }}
          />
        </div>

        {/* Footer Status Telemetry */}
        <div className="flex items-center justify-between text-[9px] text-[#7b8594] tracking-widest uppercase font-mono">
          <span className="flex items-center gap-1">
            <Activity className="w-3 h-3 text-emerald-400 animate-pulse" />
            DR. AGNES TACHYON LABORATORY SYNAPSE // ACTIVE
          </span>
          <span className="hidden sm:inline">
            STAND BY // COMPILING ARCHITECTURAL COMMENTARY...
          </span>
        </div>
      </div>
    </div>
  );
};
