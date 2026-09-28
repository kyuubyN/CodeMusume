import React, { useEffect, useRef, useState } from 'react';
import type { ExperimentView, FixVerdict, Measurement, Stage } from '../../types';
import { STAT_BY_KEY, rankIsHigh, rankOf } from '../../lib/game';
import { CodeView, DiffView } from './CodeView';
import { MeasureChart, MetricsStrip } from './MeasureChart';

export type LabAction = (name: string, args: Record<string, unknown>, label: string) => void;

interface Props {
  exp: ExperimentView;
  busy: boolean;
  voiceLive: boolean;
  onAction: LabAction;
  onClose: () => void;
}

const STEPS: { stage: Stage; label: string }[] = [
  { stage: 'predict', label: 'Hypothesis' },
  { stage: 'evidence', label: 'Evidence' },
  { stage: 'explain', label: 'Explain' },
  { stage: 'fix', label: 'Treatment' },
  { stage: 'reprove', label: 'Re-measure' },
];
const ORDER: Stage[] = ['predict', 'evidence', 'explain', 'fix', 'reprove', 'debrief'];
const LETTERS = 'ABCD';
const CONF = [
  { v: 'guess', label: 'Guess' },
  { v: 'likely', label: 'Likely' },
  { v: 'certain', label: 'Certain' },
];

const pad = (n: number) => String(n).padStart(2, '0');

export const VERDICT_LABEL: Record<FixVerdict, string> = { best: 'Best', good: 'Works', partial: 'Partial', wrong: 'No cure' };
const VERDICT_CLS: Record<FixVerdict, string> = {
  best: 'bg-acc text-ink',
  good: 'bg-ink text-paper',
  partial: 'border border-ink text-ink',
  wrong: 'bg-bad text-paper',
};

export const ExperimentBench: React.FC<Props> = ({ exp, busy, voiceLive, onAction, onClose }) => {
  const at = ORDER.indexOf(exp.stage);
  const currentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    currentRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [exp.stage]);

  const hintButton = exp.stage !== 'fix' && exp.stage !== 'reprove' && exp.stage !== 'debrief' && (
    <button
      onClick={() => onAction('get_hint', {}, 'Ask for a hint')}
      disabled={busy || exp.hints_left === 0}
      className="ef-btn-line h-9 px-3 text-[12px]"
      title="Costs 5 energy"
    >
      Hint <span className="font-mono text-[10px] text-sub">−5 EN</span>
    </button>
  );

  return (
    <section className="ef-panel flex h-full min-h-0 flex-col">
      {/* Header */}
      <header className="border-b border-hair px-4 pb-3 pt-3.5">
        <div className="flex items-start gap-3">
          <span className="ef-num text-[44px] text-ink">{pad(exp.chapter)}</span>
          <div className="min-w-0 flex-1 pt-0.5">
            <div className="flex items-center gap-1.5">
              <span className="ef-tag">{STAT_BY_KEY[exp.stat].label}</span>
              <span className="ef-label">{exp.concept}</span>
              {exp.eureka && <span className="ef-tag bg-acc text-ink">Eureka ×1.5</span>}
            </div>
            <h2 className="mt-1 font-cond text-[22px] font-bold uppercase leading-none tracking-[0.06em]">{exp.title}</h2>
          </div>
          {exp.stage === 'debrief' ? (
            <button onClick={onClose} className="ef-label hover:text-ink">Close</button>
          ) : (
            <button
              onClick={() => {
                if (window.confirm('Abandon this experiment? It costs the turn and some bond.')) onAction('abandon_experiment', {}, 'Abandon the experiment');
              }}
              className="ef-label hover:text-bad"
            >
              Abandon
            </button>
          )}
        </div>
        {/* Stepper */}
        <ol className="mt-3 grid grid-cols-5 gap-1">
          {STEPS.map((s, i) => {
            const done = at > i;
            const cur = at === i;
            return (
              <li key={s.stage}>
                <div className={`h-1 ${done ? 'bg-ink' : cur ? 'bg-acc' : 'bg-paper-3'}`} />
                <div className={`mt-1 font-cond text-[10.5px] font-bold uppercase tracking-[0.14em] ${cur ? 'text-ink' : done ? 'text-sub' : 'text-faint'}`}>
                  {pad(i + 1)} {s.label}
                </div>
              </li>
            );
          })}
        </ol>
      </header>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {/* 01 Hypothesis */}
        <Step n={1} title="Hypothesis" active={exp.stage === 'predict'} innerRef={exp.stage === 'predict' ? currentRef : undefined}>
          {exp.stage === 'predict' && (
            <div className="mb-3 border-l-[3px] border-acc pl-3 text-[13.5px] italic leading-relaxed text-sub">
              {exp.intro.map((l) => (
                <p key={l}>{l}</p>
              ))}
            </div>
          )}
          <p className="text-[15px] font-medium leading-relaxed">{exp.question}</p>
          {exp.stage === 'predict' ? (
            <PredictForm exp={exp} busy={busy} voiceLive={voiceLive} onAction={onAction} hint={hintButton} />
          ) : (
            <PredictionResult exp={exp} />
          )}
        </Step>

        {/* Measurement */}
        {exp.baseline && (
          <div className="border-b border-hair px-4 py-4">
            <div className="flex items-baseline justify-between">
              <span className="ef-label">Measured on this machine</span>
              <span className="font-mono text-[10.5px] text-sub">subprocess probe · real code</span>
            </div>
            <Headline m={exp.baseline} />
            <div className="mt-2">
              <MeasureChart stat={exp.stat} before={exp.baseline} after={exp.stage === 'reprove' || exp.stage === 'debrief' ? exp.after : null} />
            </div>
            <MetricsStrip m={exp.baseline} />
          </div>
        )}

        {/* 02 Evidence */}
        {at >= 1 && (
          <Step n={2} title="Evidence" active={exp.stage === 'evidence'} innerRef={exp.stage === 'evidence' ? currentRef : undefined}>
            <p className="mb-2 text-[14px] font-medium">{exp.evidence_prompt}</p>
            <CodeView
              file={exp.code_file}
              lines={exp.code}
              onPick={exp.stage === 'evidence' ? (n) => onAction('present_evidence', { line: n }, `Present line ${n} as evidence`) : undefined}
              disabled={busy}
              best={exp.evidence_lines}
              ok={exp.evidence_ok_lines}
              wrong={exp.evidence_attempts.filter((n) => !exp.evidence_lines.includes(n) && !exp.evidence_ok_lines.includes(n))}
            />
            <div className="mt-2 flex items-center justify-between gap-2">
              <span className="font-mono text-[11px] text-sub">
                {exp.evidence_found
                  ? exp.evidence_found === 'revealed'
                    ? 'Revealed after three attempts.'
                    : `Found in ${exp.evidence_attempts.length} attempt${exp.evidence_attempts.length > 1 ? 's' : ''}.`
                  : `Attempts: ${exp.evidence_attempts.length}/3 · wrong answers cost 3 energy`}
              </span>
              {exp.stage === 'evidence' && hintButton}
            </div>
          </Step>
        )}

        {/* 03 Explain */}
        {at >= 2 && (
          <Step n={3} title="Explain" active={exp.stage === 'explain'} innerRef={exp.stage === 'explain' ? currentRef : undefined}>
            <ExplainStep exp={exp} busy={busy} voiceLive={voiceLive} onAction={onAction} hint={hintButton} />
          </Step>
        )}

        {/* 04 Treatment */}
        {at >= 3 && (
          <Step n={4} title="Treatment" active={exp.stage === 'fix'} innerRef={exp.stage === 'fix' ? currentRef : undefined}>
            <FixStep exp={exp} busy={busy} onAction={onAction} />
          </Step>
        )}

        {/* 05 Re-measure */}
        {at >= 4 && exp.after && (
          <Step n={5} title="Re-measure" active={exp.stage === 'reprove'} innerRef={exp.stage === 'reprove' ? currentRef : undefined}>
            <ResultStep exp={exp} busy={busy} onAction={onAction} />
          </Step>
        )}

        {exp.stage === 'debrief' && exp.summary && (
          <div ref={currentRef}>
            <Debrief exp={exp} onClose={onClose} />
          </div>
        )}
      </div>
    </section>
  );
};

// ---------------------------------------------------------------------------

const Step: React.FC<{ n: number; title: string; active: boolean; innerRef?: React.Ref<HTMLDivElement>; children: React.ReactNode }> = ({
  n,
  title,
  active,
  innerRef,
  children,
}) => (
  <div ref={innerRef} className={`relative scroll-mt-2 border-b border-hair px-4 py-4 ${active ? 'bg-white/50' : ''}`}>
    {active && <span className="absolute inset-y-0 left-0 w-[3px] bg-acc" />}
    <div className="mb-2 flex items-center gap-2">
      <span className={`font-cond text-[12px] font-bold uppercase tracking-[0.2em] ${active ? 'text-ink' : 'text-sub'}`}>
        {pad(n)} / {title}
      </span>
      {!active && <span className="h-px flex-1 bg-hair" />}
    </div>
    {children}
  </div>
);

const Headline: React.FC<{ m: Measurement; compare?: Measurement | null }> = ({ m }) => {
  if (m.error) return <p className="mt-2 font-mono text-[12px] text-bad">{m.error}</p>;
  const h = m.headline;
  if (!h) return null;
  return (
    <div className="mt-1 flex items-baseline gap-2">
      <span className="ef-num text-[40px]">{h.value}</span>
      <span className="font-cond text-[15px] font-bold uppercase tracking-[0.1em] text-sub">{h.unit}</span>
      <span className="ml-2 text-[13px] text-sub">{h.label}</span>
    </div>
  );
};

const PredictForm: React.FC<{ exp: ExperimentView; busy: boolean; voiceLive: boolean; onAction: LabAction; hint: React.ReactNode }> = ({
  exp,
  busy,
  voiceLive,
  onAction,
  hint,
}) => {
  const [choice, setChoice] = useState<number | null>(null);
  const [conf, setConf] = useState('likely');
  return (
    <div className="mt-3">
      <div className="flex flex-col gap-1.5">
        {exp.options.map((o, i) => (
          <button
            key={i}
            onClick={() => setChoice(i)}
            className={`flex items-start gap-3 border px-3 py-2.5 text-left text-[13.5px] leading-snug transition-colors ${
              choice === i ? 'border-ink bg-ink text-paper' : 'border-hair bg-paper hover:border-ink'
            }`}
          >
            <span className={`grid h-6 w-6 shrink-0 place-items-center font-cond text-[13px] font-bold ${choice === i ? 'bg-acc text-ink' : 'bg-ink text-paper'}`}>
              {LETTERS[i]}
            </span>
            <span className="pt-0.5">{o}</span>
          </button>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-3">
        <span className="ef-label">Confidence</span>
        <div className="flex">
          {CONF.map((c) => (
            <button
              key={c.v}
              onClick={() => setConf(c.v)}
              className={`border border-ink/25 px-3 py-1.5 font-cond text-[12px] font-bold uppercase tracking-[0.14em] -ml-px first:ml-0 ${
                conf === c.v ? 'relative z-10 border-ink bg-ink text-paper' : 'text-sub hover:text-ink'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-1.5 text-[11.5px] text-sub">Commit before you see anything. Confident mistakes are the ones you remember.</p>
      <div className="mt-3 flex items-center gap-2">
        <button
          disabled={choice === null || busy}
          onClick={() => choice !== null && onAction('submit_prediction', { option: LETTERS[choice], confidence: conf }, `Predict ${LETTERS[choice]} (${conf})`)}
          className="ef-btn-acc flex-1"
        >
          {busy ? 'Measuring…' : 'Lock in and measure'}
        </button>
        {hint}
      </div>
      {voiceLive && <p className="mt-2 font-mono text-[11px] text-sub">or say it: “B, and I'm certain.”</p>}
    </div>
  );
};

const PredictionResult: React.FC<{ exp: ExperimentView }> = ({ exp }) => {
  const p = exp.prediction;
  if (!p || exp.correct_index === null) return null;
  const conf = ['', 'guess', 'likely', 'certain'][p.confidence];
  return (
    <div className="mt-3 flex flex-col gap-1.5">
      {exp.options.map((o, i) => {
        const mine = p.index === i;
        const right = exp.correct_index === i;
        if (!mine && !right) return null;
        return (
          <div key={i} className={`flex items-start gap-3 px-3 py-2 text-[13px] ${right ? 'bg-acc/30' : 'bg-bad/10'}`}>
            <span className={`grid h-6 w-6 shrink-0 place-items-center font-cond text-[13px] font-bold ${right ? 'bg-ink text-acc' : 'bg-bad text-paper'}`}>
              {LETTERS[i]}
            </span>
            <span className="flex-1 pt-0.5">{o}</span>
            <span className="shrink-0 pt-0.5 font-cond text-[11px] font-bold uppercase tracking-[0.14em]">
              {mine && right ? `Your call · ${conf} · correct` : mine ? `Your call · ${conf}` : 'Measured'}
            </span>
          </div>
        );
      })}
      {!p.correct && p.confidence === 3 && (
        <div className="flex items-stretch">
          <span className="ef-hazard w-2 shrink-0" />
          <p className="bg-ink px-3 py-1.5 text-[12px] text-paper">Certain and wrong. This is the one you will remember.</p>
        </div>
      )}
    </div>
  );
};

const ExplainStep: React.FC<{ exp: ExperimentView; busy: boolean; voiceLive: boolean; onAction: LabAction; hint: React.ReactNode }> = ({
  exp,
  busy,
  voiceLive,
  onAction,
  hint,
}) => {
  const [text, setText] = useState('');
  const active = exp.stage === 'explain';
  return (
    <div>
      <p className="text-[14px] font-medium">{exp.explain_prompt}</p>
      {exp.explanations.map((e, i) => (
        <p key={i} className="mt-2 border-l-2 border-ink/30 pl-3 text-[13px] italic text-sub">“{e}”</p>
      ))}
      {exp.rubric.length > 0 && (
        <ul className="mt-3 grid gap-1">
          {exp.rubric.map((k) => (
            <li key={k.id} className="flex items-center gap-2 text-[12.5px]">
              <span className={`grid h-4 w-4 shrink-0 place-items-center font-mono text-[10px] ${k.hit ? 'bg-ink text-acc' : 'border border-ink/40 text-transparent'}`}>
                ✓
              </span>
              <span className={k.hit ? 'text-ink' : 'text-sub'}>{k.hit || exp.rubric_revealed ? k.label : 'An idea you have not mentioned yet'}</span>
            </li>
          ))}
        </ul>
      )}
      {active && exp.follow_up && (
        <div className="mt-3 bg-ink px-3 py-2 text-[13px] text-paper">
          <span className="mr-2 font-cond text-[11px] font-bold uppercase tracking-[0.16em] text-acc">Agnes asks</span>
          {exp.follow_up}
        </div>
      )}
      {active && (
        <form
          className="mt-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (!text.trim()) return;
            onAction('submit_explanation', { explanation: text.trim() }, 'Explain');
            setText('');
          }}
        >
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            placeholder={voiceLive ? 'Say it out loud, or type it here' : 'In your own words: what happens, and why?'}
            className="w-full resize-none border border-hair bg-white px-3 py-2 text-[13.5px] leading-relaxed placeholder:text-faint focus:border-ink focus:outline-none"
          />
          <div className="mt-2 flex items-center gap-2">
            <button type="submit" disabled={!text.trim() || busy} className="ef-btn-dark flex-1">
              Submit explanation
            </button>
            {hint}
          </div>
          <p className="mt-1.5 text-[11.5px] text-sub">Graded on ideas, not wording. You get one follow-up to fill the gaps.</p>
        </form>
      )}
    </div>
  );
};

const FixStep: React.FC<{ exp: ExperimentView; busy: boolean; onAction: LabAction }> = ({ exp, busy, onAction }) => {
  const [open, setOpen] = useState<string | null>(null);
  const active = exp.stage === 'fix';
  const tried = Object.fromEntries(exp.tries.map((t) => [t.key, t]));
  return (
    <div>
      <p className="text-[14px] font-medium">{exp.fix_prompt}</p>
      <ul className="mt-2 flex flex-col gap-1.5">
        {exp.fixes.map((f) => {
          const t = tried[f.key];
          const isCurrent = exp.current_fix === f.key;
          return (
            <li key={f.key} className={`border ${isCurrent ? 'border-ink' : 'border-hair'} bg-paper`}>
              <div className="flex items-start gap-3 px-3 py-2.5">
                <span className="grid h-6 w-6 shrink-0 place-items-center bg-ink font-cond text-[13px] font-bold text-paper">{f.key}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[13.5px] font-semibold">{f.label}</span>
                    {f.verdict && <span className={`px-1.5 py-px font-cond text-[10px] font-bold uppercase tracking-[0.14em] ${VERDICT_CLS[f.verdict]}`}>{VERDICT_LABEL[f.verdict]}</span>}
                    {t?.result.headline && <span className="font-mono text-[11px] text-sub">→ {t.result.headline.value} {t.result.headline.unit}</span>}
                  </div>
                  <div className="mt-0.5 font-mono text-[11.5px] text-sub">{f.detail}</div>
                  <button onClick={() => setOpen(open === f.key ? null : f.key)} className="mt-1 font-cond text-[11px] font-bold uppercase tracking-[0.14em] text-sub hover:text-ink">
                    {open === f.key ? 'Hide diff' : 'Preview diff'}
                  </button>
                </div>
                {active && (
                  <button
                    onClick={() => onAction('choose_fix', { option: f.key }, `Apply treatment ${f.key}`)}
                    disabled={busy}
                    className="ef-btn-dark h-9 shrink-0 px-3 text-[12px]"
                    title={exp.tries.length ? 'Retrying costs 5 energy' : undefined}
                  >
                    {busy ? '…' : exp.tries.length ? 'Apply −5 EN' : 'Apply'}
                  </button>
                )}
              </div>
              {open === f.key && <DiffView diff={f.diff} />}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

const ResultStep: React.FC<{ exp: ExperimentView; busy: boolean; onAction: LabAction }> = ({ exp, busy, onAction }) => {
  const t = exp.tries[exp.tries.length - 1];
  const fix = exp.fixes.find((f) => f.key === exp.current_fix);
  if (!t || !fix) return null;
  const before = exp.baseline?.headline;
  const after = exp.after?.headline;
  const statAfter = exp.after_score ?? exp.baseline_score;
  const good = t.verdict === 'best' || t.verdict === 'good';
  return (
    <div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-end gap-3">
        <div>
          <div className="ef-label">Before</div>
          <div className="ef-num mt-1 text-[34px] text-sub">{before?.value ?? '–'}</div>
          <div className="font-mono text-[11px] text-sub">{before?.unit}</div>
        </div>
        <div className="pb-4 font-cond text-2xl text-faint">→</div>
        <div>
          <div className="ef-label">After · {fix.key}</div>
          <div className="ef-num mt-1 text-[34px]">{after?.value ?? '–'}</div>
          <div className="font-mono text-[11px] text-sub">{after?.unit}</div>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <span className={`px-1.5 py-px font-cond text-[11px] font-bold uppercase tracking-[0.14em] ${VERDICT_CLS[t.verdict]}`}>{VERDICT_LABEL[t.verdict]}</span>
        <span className="font-mono text-[11.5px] text-sub">
          {STAT_BY_KEY[exp.stat].label} {exp.baseline_score} → <b className="text-ink">{statAfter}</b> ({rankOf(statAfter)})
        </span>
      </div>
      <p className="mt-2 font-mono text-[11.5px] text-sub">static: {t.static}</p>
      <p className="mt-3 border-l-[3px] border-acc pl-3 text-[13.5px] leading-relaxed">{fix.lesson}</p>
      <MetricsStrip m={exp.after} />
      {exp.stage === 'reprove' && (
      <div className="mt-4 grid grid-cols-2 gap-2">
        <button onClick={() => onAction('keep_fix', {}, 'Keep this treatment')} disabled={busy} className={good ? 'ef-btn-acc' : 'ef-btn-line'}>
          Keep this fix
        </button>
        <button onClick={() => onAction('revert_fix', {}, 'Revert and try another treatment')} disabled={busy} className={good ? 'ef-btn-line' : 'ef-btn-dark'}>
          Revert, try another
        </button>
      </div>
      )}
      {!good && exp.stage === 'reprove' && (
        <p className="mt-1.5 text-[11.5px] text-sub">You can keep it, but the specimen stays sick and the Derby will know.</p>
      )}
    </div>
  );
};

const POINT_MAX: Record<string, number> = { prediction: 20, evidence: 25, explanation: 35, fix: 20 };

const Debrief: React.FC<{ exp: ExperimentView; onClose: () => void }> = ({ exp, onClose }) => {
  const s = exp.summary!;
  return (
    <div className="animate-fade-up px-4 py-5">
      <div className="flex items-end justify-between">
        <div>
          <div className="ef-label">Experiment complete</div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="ef-num text-[64px]">{s.score}</span>
            <span className="font-cond text-lg font-bold text-sub">/100</span>
          </div>
        </div>
        <div className="text-right font-mono text-[11px] text-sub">
          {s.multiplier !== 1 && <div>multiplier ×{s.multiplier}</div>}
          {s.eureka && <div className="bg-acc px-1 text-ink">eureka</div>}
        </div>
      </div>

      <div className="mt-3 grid gap-1.5">
        {Object.entries(POINT_MAX).map(([k, max]) => {
          const v = s.points[k] ?? 0;
          return (
            <div key={k} className="grid grid-cols-[92px_1fr_44px] items-center gap-2">
              <span className="font-cond text-[11px] font-bold uppercase tracking-[0.14em] text-sub">{k === 'fix' ? 'treatment' : k}</span>
              <div className="h-2 bg-paper-3">
                <div className="h-full bg-ink" style={{ width: `${(v / max) * 100}%` }} />
              </div>
              <span className="text-right font-mono text-[11px]">{v}/{max}</span>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-3 gap-px bg-hair">
        <Cell label="Mastery" value={`${s.mastery_before} → ${s.mastery_after}`} note={`review in ${s.next_review_in_days}d`} />
        <Cell
          label={STAT_BY_KEY[s.stat].label}
          value={`${s.stat_before} → ${s.stat_after}`}
          note={`rank ${s.rank_after}`}
          hot={rankIsHigh(s.rank_after)}
        />
        <Cell label="Bond" value={`+${s.bond_gained}`} note={s.title_up ? `new title: ${s.bond_title}` : `${s.bond}/100`} />
      </div>

      <p className="mt-4 border-l-[3px] border-acc pl-3 text-[14px] font-medium leading-relaxed">{s.takeaway}</p>

      {s.lore && (
        <div className="mt-4 bg-ink p-4 text-paper">
          <div className="font-cond text-[11px] font-bold uppercase tracking-[0.2em] text-acc">Unlocked · {s.lore.title}</div>
          <p className="mt-1.5 text-[13px] italic leading-relaxed text-paper/85">{s.lore.text}</p>
        </div>
      )}

      {s.derby_unlocked && (
        <div className="mt-3 flex items-stretch">
          <span className="ef-hazard w-2 shrink-0" />
          <p className="flex-1 bg-acc px-3 py-2 font-cond text-[13px] font-bold uppercase tracking-[0.14em]">The Grand Derby is unlocked</p>
        </div>
      )}

      <button onClick={onClose} className="ef-btn-dark mt-4 w-full">
        Back to the lab
      </button>
    </div>
  );
};

const Cell: React.FC<{ label: string; value: string; note: string; hot?: boolean }> = ({ label, value, note, hot }) => (
  <div className={`px-3 py-2 ${hot ? 'bg-acc' : 'bg-paper'}`}>
    <div className="font-cond text-[10px] font-bold uppercase tracking-[0.16em] text-sub">{label}</div>
    <div className="ef-num mt-1 text-[18px]">{value}</div>
    <div className="font-mono text-[10.5px] text-sub">{note}</div>
  </div>
);
