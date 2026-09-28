import React from 'react';
import type { LabState } from '../../types';
import { STAT_BY_KEY } from '../../lib/game';

const TITLES = [
  { at: 0, name: 'Test Subject' },
  { at: 30, name: 'Lab Assistant' },
  { at: 60, name: 'Research Partner' },
  { at: 90, name: 'Co-author' },
];

const pad = (n: number) => String(n).padStart(2, '0');

/** What Agnes knows about you: mastery, memory schedule, bond, calibration, history. */
export const Dossier: React.FC<{ lab: LabState }> = ({ lab }) => {
  const nextTitle = TITLES.find((t) => t.at > lab.bond);
  const [right, total] = lab.predictions;
  const [cRight, cWrong] = lab.certain;
  return (
    <div className="pb-4">
      {/* Bond */}
      <section className="border-b border-hair px-4 py-3">
        <div className="flex items-baseline justify-between">
          <span className="ef-label">Bond with Agnes</span>
          <span className="font-mono text-[11px] text-sub">{lab.bond}/100</span>
        </div>
        <div className="mt-1 font-cond text-[22px] font-bold uppercase leading-none tracking-[0.06em]">{lab.title}</div>
        <div className="mt-2 flex gap-[2px]">
          {Array.from({ length: 20 }).map((_, i) => (
            <span key={i} className={`h-2 flex-1 ${i < Math.round(lab.bond / 5) ? 'bg-ink' : 'bg-paper-3'} ${TITLES.some((t) => t.at && t.at / 5 === i) ? 'ml-1' : ''}`} />
          ))}
        </div>
        <p className="mt-1.5 text-[11.5px] text-sub">
          {nextTitle ? `${nextTitle.at - lab.bond} to ${nextTitle.name}. ` : ''}
          From Research Partner up, experiments can trigger Eureka (×1.5).
        </p>
      </section>

      {/* Mastery map */}
      <section className="border-b border-hair px-4 py-3">
        <div className="flex items-baseline justify-between">
          <span className="ef-label">Mastery map</span>
          <span className="font-mono text-[10.5px] text-sub">spaced review · leitner boxes</span>
        </div>
        <ul className="mt-2 flex flex-col gap-2.5">
          {lab.mastery.map((m) => (
            <li key={m.concept}>
              <div className="flex items-center gap-2">
                <span className="ef-tag">{STAT_BY_KEY[m.stat].short}</span>
                <span className="flex-1 truncate text-[13px] font-semibold">{m.title}</span>
                {m.sparks > 0 && (
                  <span className="flex gap-0.5" title={`${m.sparks} inherited spark${m.sparks > 1 ? 's' : ''}`}>
                    {Array.from({ length: m.sparks }).map((_, i) => (
                      <span key={i} className="h-2.5 w-1.5 bg-acc" />
                    ))}
                  </span>
                )}
                <span className="ef-num w-8 text-right text-[16px]">{m.mastery}</span>
              </div>
              <div className="relative mt-1 h-1.5 bg-paper-3">
                <div className="h-full bg-ink transition-[width] duration-700" style={{ width: `${m.mastery}%` }} />
                <span className="absolute top-0 h-full w-px bg-paper" style={{ left: '60%' }} />
                <span className="absolute top-0 h-full w-px bg-paper" style={{ left: '80%' }} />
              </div>
              <div className="mt-1 flex items-center justify-between font-mono text-[10.5px] text-sub">
                <span className="flex items-center gap-1">
                  box
                  {Array.from({ length: 5 }).map((_, i) => (
                    <span key={i} className={`h-1.5 w-1.5 ${i < m.box ? 'bg-ink' : 'border border-ink/30'}`} />
                  ))}
                </span>
                <span className={m.due ? 'bg-acc px-1 text-ink' : ''}>
                  {m.box === 0 ? 'not studied' : m.due ? 'review due' : `review in ${m.due_in}d`}
                  {m.reviews[0] + m.reviews[1] > 0 && ` · ${m.reviews[0]}/${m.reviews[0] + m.reviews[1]} recalled`}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* Calibration */}
      <section className="grid grid-cols-3 gap-px border-b border-hair bg-hair">
        <Stat label="Predictions" value={total ? `${right}/${total}` : '–'} />
        <Stat label="Certain calls right" value={cRight + cWrong ? `${cRight}/${cRight + cWrong}` : "–"} />
        <Stat label="Calibration" value={lab.calibration === null ? '–' : `${Math.round(lab.calibration * 100)}%`} hot={(lab.calibration ?? 0) >= 0.8} />
      </section>

      {/* Derby skills */}
      {lab.skills.length > 0 && (
        <section className="border-b border-hair px-4 py-3">
          <span className="ef-label">Derby skills</span>
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {lab.skills.map((s) => (
              <li key={s.concept} className="flex items-center gap-1.5 border border-ink px-2 py-0.5 text-[12px]">
                <span className="font-semibold">{s.title}</span>
                <span className="font-mono text-[10.5px] text-sub">lv{s.level} · +{s.level * 60} {STAT_BY_KEY[s.stat].short}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Hall of fame */}
      <section className="border-b border-hair px-4 py-3">
        <span className="ef-label">Hall of fame</span>
        {lab.hall.length === 0 ? (
          <p className="mt-1 text-[12px] text-sub">Finish a career with the Grand Derby. Your best one becomes the ghost you race next time.</p>
        ) : (
          <table className="mt-1.5 w-full text-left text-[12px]">
            <thead>
              <tr className="font-cond text-[10px] uppercase tracking-[0.14em] text-sub">
                <th className="font-semibold">Career</th>
                <th className="font-semibold">Place</th>
                <th className="font-semibold">Total</th>
                <th className="font-semibold">Sparks</th>
              </tr>
            </thead>
            <tbody>
              {[...lab.hall].reverse().map((h) => (
                <tr key={h.career} className="border-t border-hair">
                  <td className="py-1 font-mono">{pad(h.career)}</td>
                  <td className="py-1 font-cond text-[14px] font-bold">{h.place === 1 ? '1st' : h.place === 2 ? '2nd' : h.place === 3 ? '3rd' : `${h.place}th`}</td>
                  <td className="py-1 font-mono">{Object.values(h.attributes).reduce((a, b) => a + b, 0)}</td>
                  <td className="py-1 font-mono">{Object.values(h.sparks).reduce((a, b) => a + b, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Journal */}
      <section className="px-4 py-3">
        <span className="ef-label">Agnes's journal · {lab.journal.length}/5</span>
        {lab.journal.length === 0 ? (
          <p className="mt-1 text-[12px] text-sub">Entries unlock as you clear experiments.</p>
        ) : (
          <div className="mt-2 flex flex-col gap-2">
            {lab.journal.map((j) => (
              <article key={j.chapter} className="bg-ink px-3 py-2.5 text-paper">
                <div className="font-cond text-[11px] font-bold uppercase tracking-[0.18em] text-acc">{j.title}</div>
                <p className="mt-1 text-[12.5px] italic leading-relaxed text-paper/85">{j.text}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

const Stat: React.FC<{ label: string; value: string; hot?: boolean }> = ({ label, value, hot }) => (
  <div className={`px-3 py-2 ${hot ? 'bg-acc' : 'bg-paper'}`}>
    <div className="font-cond text-[10px] font-bold uppercase tracking-[0.14em] text-sub">{label}</div>
    <div className="ef-num mt-1 text-[20px]">{value}</div>
  </div>
);
