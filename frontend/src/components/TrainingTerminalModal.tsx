import React, { useState } from 'react';
import { AttributeType } from '../types';
import { Terminal, Send, X, AlertTriangle, Sparkles, CheckCircle2 } from 'lucide-react';

interface Props {
  attribute: AttributeType;
  currentEnergy: number;
  onClose: () => void;
  onSubmit: (attr: AttributeType, customPrompt: string) => void;
}

const ATTRIBUTE_METRICS: Record<
  AttributeType,
  { title: string; subtitle: string; presets: string[]; hint: string }
> = {
  speed: {
    title: 'SPEED CALIBRATION // ASYNC & LATENCY',
    subtitle: 'Otimização de hot paths, conversão síncrona para assíncrona e redução de tempo de build.',
    presets: [
      'Substituir time.sleep por await asyncio.sleep(n) em fluxos concorrentes.',
      'Refatorar chamadas requests.get síncronas para httpx.AsyncClient.',
      'Reduzir profundidade de dependências cíclicas e complexidade ciclomática para < 6.',
    ],
    hint: 'Ex: "Implementar pipeline assíncrono com asyncio.Queue e workers desacoplados."',
  },
  stamina: {
    title: 'STAMINA CALIBRATION // MEMORY & HANDLES',
    subtitle: 'Prevenção de vazamento de memória, gerenciamento de conexões e retenção de estado.',
    presets: [
      'Envolver todos os file handles open() em blocos with context manager.',
      'Implementar pool assíncrono de conexões de banco de dados com limite de vida.',
      'Configurar garbage collection explícito e desalocação de buffers pesados.',
    ],
    hint: 'Ex: "Garantir context managers em todos os cursores de banco para evitar vazamentos."',
  },
  power: {
    title: 'POWER CALIBRATION // CONCURRENCY & BATCHING',
    subtitle: 'Vazão de requisições, paralelismo de threads e processamento em lote (batching).',
    presets: [
      'Agrupar itens em micro-batches com asyncio.gather ao invés de loops sequenciais.',
      'Utilizar ThreadPoolExecutor para chamadas I/O bound e ProcessPool para CPU bound.',
      'Adicionar indexação composta e particionamento em tabelas de alto volume.',
    ],
    hint: 'Ex: "Transformar loop sequencial de processamento em execução paralela com asyncio.gather."',
  },
  guts: {
    title: 'GUTS CALIBRATION // RESILIENCE & ERROR HANDLING',
    subtitle: 'Tolerância a falhas de rede, circuit breakers e degradação suave de serviços.',
    presets: [
      'Eliminar bare except: pass e implementar log estruturado com exceções tipadas.',
      'Aplicar timeout estrito de 10s em todas as chamadas HTTP e filas de mensageria.',
      'Configurar retry exponencial com jitter e fallback gracioso em caso de queda.',
    ],
    hint: 'Ex: "Implementar Circuit Breaker com fallback para cache local em caso de falha de rede."',
  },
  wisdom: {
    title: 'WISDOM CALIBRATION // CLEAN ARCHITECTURE & RAG',
    subtitle: 'Estruturação de domínios puros, inversão de dependência (DDD) e tipagem rigorosa PEP 484.',
    presets: [
      'Adicionar anotações de tipo de retorno estritas em 100% das funções.',
      'Desacoplar controllers do domínio com Domain Services e Repository Interfaces.',
      'Adicionar suite de testes unitários com fixtures idempotentes e cobertura > 90%.',
    ],
    hint: 'Ex: "Adicionar tipagem estrita com Pydantic v2 e isolar lógica de negócio em Bounded Contexts."',
  },
};

export const TrainingTerminalModal: React.FC<Props> = ({
  attribute,
  currentEnergy,
  onClose,
  onSubmit,
}) => {
  const meta = ATTRIBUTE_METRICS[attribute];
  const [customText, setCustomText] = useState(meta.presets[0]);
  const hasEnoughEnergy = currentEnergy >= 20;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasEnoughEnergy) return;
    onSubmit(attribute, customText.trim());
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/92 animate-fade-in font-mono select-none" style={{ contain: 'layout paint' }}>
      <div className="relative w-full max-w-2xl bg-[#0c0f16] border-2 border-[#ffd000]/60 rounded-2xl p-6 shadow-[0_0_60px_rgba(255,208,0,0.25)] flex flex-col gap-4 text-[#f0f3f6]">
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-[#ffd000]/10 border border-[#ffd000]/40 text-[#ffd000]">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] tracking-widest text-[#7b8594] uppercase block">
                ARQUITETURA END-FIELD // INJEÇÃO DE CONHECIMENTO
              </span>
              <h2 className="text-sm md:text-base font-black tracking-wider text-[#ffd000] uppercase">
                {meta.title}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded bg-[#161b24] hover:bg-[#202734] text-[#7b8594] hover:text-white border border-white/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Subtitle / Objective */}
        <p className="text-xs text-[#a0aec0] font-sans leading-relaxed">
          {meta.subtitle}
        </p>

        {/* Quick Suggestion Chips */}
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] text-[#7b8594] tracking-widest uppercase flex items-center gap-1 font-bold">
            <Sparkles className="w-3 h-3 text-[#ffd000]" />
            DIRETRIZES RÁPIDAS DE ARQUITETURA (CLIQUE PARA SELECIONAR):
          </span>
          <div className="flex flex-col gap-1.5">
            {meta.presets.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setCustomText(preset)}
                className={`text-left text-xs p-2 rounded-lg border transition-all ${
                  customText === preset
                    ? 'bg-[#ffd000]/10 border-[#ffd000] text-[#ffd000] font-bold shadow-sm'
                    : 'bg-[#141720] border-white/10 text-[#c4ccd8] hover:border-white/30'
                }`}
              >
                <div className="flex items-center gap-2">
                  <CheckCircle2 className={`w-3.5 h-3.5 flex-shrink-0 ${customText === preset ? 'text-[#ffd000]' : 'opacity-30'}`} />
                  <span className="truncate">{preset}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Interactive Custom Mini-Chat Input */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-[#7b8594] tracking-widest uppercase font-bold">
              CONSOLE DE INSTRUÇÕES PERSONALIZADAS PARA A AGNES:
            </label>
            <textarea
              rows={3}
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              placeholder={meta.hint}
              className="w-full bg-[#121620] border border-white/20 rounded-xl p-3 text-xs md:text-sm text-[#f0f3f6] font-mono focus:outline-none focus:border-[#ffd000] transition-colors resize-none placeholder:text-[#4b5563]"
            />
          </div>

          {/* Energy Cost & Status Info */}
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-[#141824] border border-white/10 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-[#7b8594] tracking-wider uppercase font-bold text-[10px]">
                CUSTO DO TREINO:
              </span>
              <span className="text-[#00f0ff] font-bold tabular-nums">
                -20 HP
              </span>
              <span className="text-[#7b8594] text-[10px]">
                (Energia Atual: {currentEnergy}%)
              </span>
            </div>

            {!hasEnoughEnergy && (
              <div className="flex items-center gap-1.5 text-rose-400 font-bold text-xs animate-pulse">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>ENERGIA ESGOTADA! NECESSÁRIO DESCANSAR (60s).</span>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 mt-1">
            <button
              type="button"
              onClick={onClose}
              className="py-2.5 px-4 rounded-xl bg-[#161a24] hover:bg-[#202634] border border-white/10 text-xs font-bold tracking-wider text-[#a0aec0] transition-all"
            >
              CANCELAR
            </button>

            <button
              type="submit"
              disabled={!hasEnoughEnergy || !customText.trim()}
              className="py-2.5 px-6 rounded-xl bg-[#ffd000] hover:bg-[#ffdb33] disabled:opacity-40 disabled:cursor-not-allowed text-black font-black text-xs tracking-wider shadow-[0_0_20px_rgba(255,208,0,0.4)] transition-all active:scale-95 flex items-center gap-2"
            >
              <Send className="w-3.5 h-3.5" />
              <span>INICIAR APRENDIZADO & CALIBRAÇÃO</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
