import React, { useEffect, useState } from 'react';
import type { LabState, StandardsReport as Report } from '../../types';
import { api } from '../../services/api';
import { STAT_BY_KEY } from '../../lib/game';
import { ModuleGraph } from './MeasureChart';

interface Props {
  /** Bumped whenever the code may have changed (scan, rescan), to refetch. */
  version: number;
  lab: LabState | null;
  onPractice: (chapter: number) => void;
  onOpenCase: (file: string, line: number) => void;
}

const STATUS_CLS = {
  pass: 'bg-ink text-paper',
  warn: 'bg-acc text-ink',
  fail: 'bg-bad text-paper',
};

const pad = (n: number) => String(n).padStart(2, '0');

/** The architecture standards check of your own repository. */
export const StandardsReport: React.FC<Props> = ({ version, lab, onPractice, onOpenCase }) => {
  const [rep, setRep] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    api
      .getRepoReport()
      .then((r) => {
        if (!alive) return;
        setRep(r);
        setOpen((o) => o ?? r.checks.find((c) => c.status !== 'pass')?.id ?? null);
      })
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [version]);

  if (error) return <p className="p-4 text-sm text-bad">{error}</p>;
  if (!rep) return <p className="p-4 font-mono text-[12px] text-sub">Building the module graph and running ten checks…</p>;

  const cleared = new Set(lab?.chapters.filter((c) => c.status === 'cleared').map((c) => c.id) ?? []);
  return (
    <div className="pb-4">
      <div className="flex items-stretch border-b border-hair">
        <div className={`flex w-24 shrink-0 flex-col items-center justify-center ${'SA'.includes(rep.grade) ? 'bg-acc' : 'bg-ink text-paper'}`}>
          <span className="font-cond text-[10px] font-bold uppercase tracking-[0.2em] opacity-70">Grade</span>
          <span className="ef-num text-[48px]">{rep.grade}</span>
        </div>
        <div className="flex-1 px-4 py-3">
          <div className="ef-label">Architecture standards</div>
          <div className="mt-1 font-mono text-[14px]">{rep.root}</div>
          <div className="mt-1 font-mono text-[11px] text-sub">
            {rep.passed}/{rep.total} checks pass · {rep.modules} modules · {rep.lines.toLocaleString()} lines
            {rep.parse_errors.length ? ` · ${rep.parse_errors.length} unparsable` : ''}
          </div>
          <div className="mt-2 flex gap-0.5">
            {rep.checks.map((c) => (
              <span key={c.id} className={`h-1.5 flex-1 ${c.status === 'pass' ? 'bg-ink' : c.status === 'warn' ? 'bg-acc' : 'bg-bad'}`} />
            ))}
          </div>
        </div>
      </div>

      <ul>
        {rep.checks.map((c, i) => {
          const isOpen = open === c.id;
          return (
            <li key={c.id} className="border-b border-hair">
              <button onClick={() => setOpen(isOpen ? null : c.id)} className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-paper-2">
                <span className="ef-num w-6 text-[15px] text-faint">{pad(i + 1)}</span>
                <span className={`w-11 shrink-0 py-px text-center font-cond text-[10px] font-bold uppercase tracking-[0.14em] ${STATUS_CLS[c.status]}`}>
                  {c.status}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-semibold">{c.title}</span>
                  <span className="block truncate font-mono text-[10.5px] text-sub">
                    {c.value} · target {c.target}
                  </span>
                </span>
                <span className="ef-tag">{STAT_BY_KEY[c.stat].short}</span>
              </button>
              {isOpen && (
                <div className="animate-fade-up px-4 pb-3 pl-[52px]">
                  <p className="text-[12.5px] leading-relaxed text-sub">{c.detail}</p>
                  {c.evidence.length > 0 && (
                    <ul className="mt-2 bg-ink py-1.5 font-mono text-[11px] text-paper/85">
                      {c.evidence.map((e, k) => (
                        <li key={k}>
                          <button
                            onClick={() => e.line && onOpenCase(e.file, e.line)}
                            className={`block w-full px-3 py-1 text-left ${e.line ? 'hover:bg-paper/10' : 'cursor-default'}`}
                          >
                            <span className="text-acc">
                              {e.file}
                              {e.line ? `:${e.line}` : ''}
                            </span>
                            {e.code && <span className="ml-2 text-paper/70">{e.code}</span>}
                            {e.note && <span className="block text-paper/45">{e.note}</span>}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  {c.status !== 'pass' && (
                    <button onClick={() => onPractice(c.chapter)} className="ef-btn-line mt-2 h-8 px-3 text-[11px]">
                      {cleared.has(c.chapter) ? `Revisit in the lab · chapter ${pad(c.chapter)}` : `Learn it first · lab chapter ${pad(c.chapter)}`}
                    </button>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {rep.graph.nodes.length > 1 && (
        <section className="px-4 pt-3">
          <div className="flex items-baseline justify-between">
            <span className="ef-label">Module graph</span>
            <span className="font-mono text-[10.5px] text-sub">{rep.graph.truncated ? 'most connected 16' : 'all modules'}</span>
          </div>
          <div className="mt-1">
            <ModuleGraph m={{ graph: rep.graph }} baseline={null} filledLabel="in an import cycle" />
          </div>
        </section>
      )}
      <p className="px-4 pt-3 text-[11.5px] leading-relaxed text-sub">
        Static analysis only (CFG dataflow, call graph, module graph). Your code is never executed. Stats here are scored per thousand lines.
      </p>
    </div>
  );
};
