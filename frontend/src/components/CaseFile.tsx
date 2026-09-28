import React, { useEffect, useState } from 'react';
import type { AttributeType, CodeSmell } from '../types';
import { STAT_BY_KEY } from '../lib/game';

export type CaseView =
  | { mode: 'list'; attribute?: AttributeType | null }
  | { mode: 'detail'; smellId: number }
  | { mode: 'prescription'; smellId: number; text: string };

interface Props {
  smells: CodeSmell[];
  view: CaseView;
  highlight: number[];
  busy: boolean;
  onView: (v: CaseView) => void;
  onTrainSmell: (s: CodeSmell) => void;
  onPrescribe: (s: CodeSmell) => void;
  onClose?: () => void;
}

const pad = (n: number) => String(n).padStart(2, '0');

export const CaseFile: React.FC<Props> = ({ smells, view, highlight, busy, onView, onTrainSmell, onPrescribe, onClose }) => {
  const open = smells.filter((s) => !s.drilled);
  const drilled = smells.filter((s) => s.drilled);
  const crumb = view.mode === 'list' ? 'Index' : view.mode === 'detail' ? `Case ${pad(view.smellId)}` : 'Fix prompt';

  return (
    <section className="ef-panel flex h-full min-h-0 flex-col">
      <header className="flex items-baseline gap-3 border-b border-hair px-4 pb-2.5 pt-3.5">
        <h2 className="ef-title">
          <span className="mr-2 text-faint">03</span>Case file
        </h2>
        {view.mode !== 'list' && (
          <button onClick={() => onView({ mode: 'list' })} className="ef-label hover:text-ink">
            ← Index
          </button>
        )}
        <span className="ef-label ml-auto">
          {crumb} · {open.length} open
        </span>
        {onClose && (
          <button onClick={onClose} className="ef-label hover:text-ink xl:hidden" aria-label="Close">
            Close
          </button>
        )}
      </header>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {view.mode === 'list' && (
          <SmellList
            open={open}
            drilled={drilled}
            filter={view.attribute ?? null}
            highlight={highlight}
            onFilter={(a) => onView({ mode: 'list', attribute: a })}
            onOpen={(s) => onView({ mode: 'detail', smellId: s.id })}
          />
        )}
        {view.mode === 'detail' && (
          <SmellDetail smell={smells.find((s) => s.id === view.smellId)} busy={busy} onTrain={onTrainSmell} onPrescribe={onPrescribe} />
        )}
        {view.mode === 'prescription' && <Prescription smell={smells.find((s) => s.id === view.smellId)} text={view.text} />}
      </div>
    </section>
  );
};

// ---------------------------------------------------------------------------

const SmellList: React.FC<{
  open: CodeSmell[];
  drilled: CodeSmell[];
  filter: AttributeType | null;
  highlight: number[];
  onFilter: (a: AttributeType | null) => void;
  onOpen: (s: CodeSmell) => void;
}> = ({ open, drilled, filter, highlight, onFilter, onOpen }) => {
  const shown = filter ? open.filter((s) => s.attribute === filter) : open;
  const attrs = Array.from(new Set(open.map((s) => s.attribute)));

  if (open.length === 0 && drilled.length === 0) {
    return (
      <div className="px-6 py-14 text-center">
        <div className="ef-num text-5xl">00</div>
        <p className="ef-title mt-3">No smells found</p>
        <p className="mt-1 text-sm text-sub">This repository is suspiciously healthy.</p>
      </div>
    );
  }

  return (
    <div>
      {attrs.length > 1 && (
        <div className="flex border-b border-hair">
          {[null, ...attrs].map((a) => (
            <button
              key={a ?? 'all'}
              onClick={() => onFilter(a)}
              className={`flex-1 py-2 font-cond text-[11px] font-bold uppercase tracking-[0.16em] transition-colors ${
                filter === a ? 'bg-ink text-paper' : 'text-sub hover:bg-paper-2 hover:text-ink'
              }`}
            >
              {a ? STAT_BY_KEY[a].short : 'All'}
            </button>
          ))}
        </div>
      )}
      <ul>
        {shown.map((s, i) => (
          <li key={s.id} className="animate-slide-in" style={{ animationDelay: `${i * 25}ms` }}>
            <button
              onClick={() => onOpen(s)}
              className={`group flex w-full gap-3 border-b border-hair px-4 py-3 text-left transition-colors hover:bg-paper-2 ${
                highlight.includes(s.id) ? 'bg-acc/25' : ''
              }`}
            >
              <span className="ef-num w-7 shrink-0 pt-0.5 text-[22px] text-faint group-hover:text-ink">{pad(s.id)}</span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="ef-tag">{STAT_BY_KEY[s.attribute].short}</span>
                  <span className="truncate font-mono text-[11px] text-sub">
                    {basename(s.file_path)}:{s.line_number}
                  </span>
                </span>
                <span className="mt-1 block text-[13.5px] font-medium leading-snug text-ink">{plain(s.description)}</span>
              </span>
              <span className="self-center font-cond text-sm text-faint group-hover:text-ink">→</span>
            </button>
          </li>
        ))}
      </ul>
      {drilled.length > 0 && !filter && (
        <div className="px-4 py-3">
          <div className="ef-label mb-1.5">Drilled in training</div>
          {drilled.map((s) => (
            <button key={s.id} onClick={() => onOpen(s)} className="flex w-full gap-2 py-1 text-left text-[12px] text-sub hover:text-ink">
              <span className="ef-num text-[12px]">{pad(s.id)}</span>
              <span className="truncate">{plain(s.description)}</span>
            </button>
          ))}
          <p className="mt-2 text-[11.5px] leading-relaxed text-faint">
            Drilling trains the stat, but the smell stays in your code until you fix it and rescan.
          </p>
        </div>
      )}
    </div>
  );
};

const SmellDetail: React.FC<{
  smell?: CodeSmell;
  busy: boolean;
  onTrain: (s: CodeSmell) => void;
  onPrescribe: (s: CodeSmell) => void;
}> = ({ smell, busy, onTrain, onPrescribe }) => {
  if (!smell) return <p className="p-4 text-sm text-sub">That smell is gone. Maybe you fixed it?</p>;
  const firstLine = Math.max(1, smell.line_number - 1);
  const lines = smell.code_snippet.split('\n');

  return (
    <div className="animate-fade-up">
      <div className="flex items-end gap-3 px-4 pb-3 pt-4">
        <span className="ef-num text-5xl">{pad(smell.id)}</span>
        <div className="pb-1">
          <div className="flex items-center gap-1.5">
            <span className="ef-tag">{STAT_BY_KEY[smell.attribute].label}</span>
            <span className="font-mono text-[11px] text-sub">{smell.rule_id}</span>
            {smell.drilled && <span className="ef-tag bg-ok">Drilled</span>}
          </div>
        </div>
      </div>
      <h3 className="px-4 text-[16px] font-semibold leading-snug">{plain(smell.description)}</h3>

      <div className="mx-4 mt-3 bg-ink text-paper">
        <div className="flex justify-between border-b border-paper/10 px-3 py-1.5 font-mono text-[11px] text-paper/50">
          <span>{smell.file_path}</span>
          <span>L{smell.line_number}</span>
        </div>
        <pre className="scroll-thin overflow-x-auto py-2 font-mono text-[12.5px] leading-relaxed">
          {lines.map((ln, i) => {
            const n = firstLine + i;
            const hit = n === smell.line_number;
            return (
              <div key={i} className={`flex pr-3 ${hit ? 'bg-acc/15 shadow-[inset_3px_0_0_#ffe100]' : ''}`}>
                <span className={`w-10 shrink-0 select-none pr-3 text-right ${hit ? 'text-acc' : 'text-paper/30'}`}>{n}</span>
                <code className="whitespace-pre">{ln || ' '}</code>
              </div>
            );
          })}
        </pre>
      </div>

      <dl className="mt-4 px-4">
        <dt className="ef-label">Diagnosis</dt>
        <dd className="mt-1 text-[13.5px] leading-relaxed">{plain(smell.tachyon_critique)}</dd>
        <dt className="ef-label mt-4">Prescription</dt>
        <dd className="mt-1 border-l-[3px] border-acc pl-3 text-[13.5px] leading-relaxed">{plain(smell.suggested_fix)}</dd>
      </dl>

      <div className="mt-5 grid grid-cols-2 gap-2 px-4 pb-4">
        <button onClick={() => onTrain(smell)} disabled={busy || smell.drilled} className="ef-btn-line">
          Drill
        </button>
        <button onClick={() => onPrescribe(smell)} className="ef-btn-dark">
          Fix prompt
        </button>
      </div>
    </div>
  );
};

const Prescription: React.FC<{ smell?: CodeSmell; text: string }> = ({ smell, text }) => {
  const [copied, setCopied] = useState(false);
  useEffect(() => setCopied(false), [text]);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="animate-fade-up p-4">
      <h3 className="text-[16px] font-semibold">Prompt for your coding agent</h3>
      <p className="mt-1 text-[12.5px] text-sub">
        {smell ? `Case ${pad(smell.id)} · ${basename(smell.file_path)}:${smell.line_number}. ` : ''}
        Paste it, apply the change, then tell Agnes to check again.
      </p>
      <pre className="scroll-thin mt-3 max-h-[46vh] overflow-auto whitespace-pre-wrap bg-ink p-3 font-mono text-[12px] leading-relaxed text-paper/85">
        {text}
      </pre>
      <button onClick={copy} className={`${copied ? 'ef-btn-acc' : 'ef-btn-dark'} mt-3 w-full`}>
        {copied ? 'Copied' : 'Copy prompt'}
      </button>
    </div>
  );
};

function basename(p: string): string {
  return p.split(/[\\/]/).pop() ?? p;
}

/** Scanner text uses markdown backticks; show them as plain text. */
function plain(s: string): string {
  return s.replace(/`([^`]+)`/g, '$1');
}
