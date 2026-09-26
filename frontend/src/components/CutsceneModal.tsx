import React from 'react';
import { CurriculumCard, AttributeType } from '../types';
import { BookOpen, Award, CheckCircle2, FlaskConical, X } from 'lucide-react';

interface Props {
  curriculum: CurriculumCard;
  attribute: AttributeType;
  onClose: () => void;
}

export const CutsceneModal: React.FC<Props> = ({ curriculum, attribute, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in select-none">
      <div className="relative w-full max-w-lg bg-gradient-to-b from-slate-900 via-slate-900 to-indigo-950 border-2 border-cyan-500/60 rounded-3xl p-6 shadow-[0_0_50px_rgba(6,182,212,0.3)] flex flex-col gap-3.5 text-slate-100">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-full bg-slate-800 text-slate-400 hover:text-white border border-slate-700 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Cutscene Tag */}
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-400/40">
            <FlaskConical className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-black tracking-widest text-cyan-400 block">
              ProofRay Architecture RAG • {attribute.toUpperCase()}
            </span>
            <h3 className="text-sm font-black text-white leading-tight">
              {curriculum.cutscene.title}
            </h3>
          </div>
        </div>

        {/* Cutscene Visual / Description */}
        <div className="relative rounded-2xl overflow-hidden border border-slate-700/80 bg-slate-950/80 p-3 shadow-inner">
          <div className="flex items-center gap-2 mb-1.5">
            <BookOpen className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-[11px] font-black text-amber-300">
              {curriculum.title}
            </span>
          </div>
          <p className="text-xs text-slate-300 italic leading-relaxed">
            "{curriculum.cutscene.description}"
          </p>
        </div>

        {/* Core Architectural Principle */}
        <div className="flex flex-col gap-1 bg-slate-800/60 rounded-xl p-2.5 border border-slate-700">
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400">
            <Award className="w-3 h-3 text-cyan-400" />
            <span>Padrão Primário:</span>
          </div>
          <span className="text-xs font-bold text-cyan-200">
            {curriculum.primary_pattern}
          </span>
          <p className="text-[11px] text-slate-400 mt-1 leading-normal">
            {curriculum.core_principle}
          </p>
        </div>

        {/* Canonical Remedy for IBM Bob */}
        <div className="bg-emerald-950/30 border border-emerald-500/30 rounded-xl p-2.5">
          <span className="text-[10px] uppercase font-black text-emerald-400 block mb-0.5">
            Prescrição do Treino (IBM Bob 2.0):
          </span>
          <p className="text-[11px] text-emerald-200 leading-snug">
            {curriculum.canonical_remedy}
          </p>
        </div>

        {/* Action Button */}
        <button
          onClick={onClose}
          className="w-full mt-1 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black text-xs shadow-lg transition-all active:scale-95 flex items-center justify-center gap-1.5"
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>INCORPORAR CONHECIMENTO AO REPO</span>
        </button>
      </div>
    </div>
  );
};
