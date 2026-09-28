import React, { useMemo } from 'react';
import type { AttributeType, Measurement } from '../../types';

interface Props {
  stat: AttributeType;
  before: Measurement | null;
  after?: Measurement | null;
}

const W = 600;
const H = 190;
const PAD = { l: 44, r: 12, t: 12, b: 26 };

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}

/** The measurement, drawn: before in grey, after in black. */
export const MeasureChart: React.FC<Props> = ({ stat, before, after }) => {
  if (stat === 'wisdom') return <ModuleGraph m={after ?? before} baseline={after ? before : null} />;
  const bars = stat === 'guts';
  const a = before?.series?.points ?? [];
  const b = after?.series?.points ?? [];
  const xMax = Math.max(1, ...a.map((p) => p[0]), ...b.map((p) => p[0]));
  const yMax = niceMax(Math.max(1, ...a.map((p) => p[1]), ...b.map((p) => p[1])));
  const x = (v: number) => PAD.l + (v / xMax) * (W - PAD.l - PAD.r);
  const y = (v: number) => H - PAD.b - (v / yMax) * (H - PAD.t - PAD.b);
  const path = (pts: [number, number][], step: boolean) =>
    pts
      .map((p, i) => {
        if (i === 0) return `M${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`;
        return step
          ? `H${x(p[0]).toFixed(1)}V${y(p[1]).toFixed(1)}`
          : `L${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`;
      })
      .join('');
  const step = stat === 'stamina';
  const series = (after ?? before)?.series;
  const flags = (after ?? before)?.series?.flags ?? {};

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label={`${series?.y ?? ''} over ${series?.x ?? ''}`}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(yMax * f)} y2={y(yMax * f)} stroke="rgba(20,21,23,0.12)" />
            <text x={PAD.l - 6} y={y(yMax * f) + 4} textAnchor="end" className="fill-sub font-mono text-[10px]">
              {Math.round(yMax * f)}
            </text>
          </g>
        ))}
        <text x={W - PAD.r} y={H - 6} textAnchor="end" className="fill-sub font-mono text-[10px]">
          {series?.x} →
        </text>

        {bars ? (
          <>
            {(b.length ? b : a).map((p, i) => {
              const bw = Math.max(2, (W - PAD.l - PAD.r) / (xMax + 1) - 3);
              const flag = flags[String(p[0])];
              const fill = flag === 'silent_wrong' ? '#e5484d' : flag === 'raised' ? '#96989d' : '#141517';
              const ghost = b.length ? a.find((q) => q[0] === p[0]) : null;
              return (
                <g key={i}>
                  {ghost && <rect x={x(p[0]) - bw / 2} y={y(ghost[1])} width={bw} height={y(0) - y(ghost[1])} fill="rgba(20,21,23,0.14)" />}
                  <rect
                    x={x(p[0]) - bw / 2}
                    y={y(p[1])}
                    width={bw}
                    height={Math.max(1, y(0) - y(p[1]))}
                    fill={fill}
                    className="origin-bottom animate-[fade-up_0.4s_ease-out_both]"
                    style={{ animationDelay: `${i * 12}ms` }}
                  />
                </g>
              );
            })}
          </>
        ) : (
          <>
            {b.length > 0 && a.length > 0 && (
              <path d={path(a, step)} fill="none" stroke="rgba(20,21,23,0.28)" strokeWidth={2} strokeDasharray="5 4" />
            )}
            <path
              key={b.length ? 'after' : 'before'}
              d={path(b.length ? b : a, step)}
              fill="none"
              stroke="#141517"
              strokeWidth={2.4}
              pathLength={1}
              className="animate-draw"
              style={{ strokeDasharray: 1 }}
            />
          </>
        )}
        <line x1={PAD.l} x2={W - PAD.r} y1={y(0)} y2={y(0)} stroke="#141517" />
      </svg>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[10.5px] text-sub">
        <span>y: {series?.y}</span>
        {b.length > 0 && (
          <>
            <span><span className="mr-1 inline-block h-0.5 w-4 bg-ink/30 align-middle" />before</span>
            <span><span className="mr-1 inline-block h-0.5 w-4 bg-ink align-middle" />after</span>
          </>
        )}
        {bars && (
          <>
            <span><span className="mr-1 inline-block h-2 w-2 bg-bad align-middle" />silently wrong total</span>
            <span><span className="mr-1 inline-block h-2 w-2 bg-faint align-middle" />error raised</span>
          </>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------

export const ModuleGraph: React.FC<{ m: Measurement | null; baseline: Measurement | null; filledLabel?: string }> = ({
  m,
  baseline,
  filledLabel = 'loaded to test billing.charge()',
}) => {
  const g = m?.graph;
  const { layout, H, colW } = useMemo(() => {
    const nodes = g?.nodes ?? [];
    const edges = g?.edges ?? [];
    if (nodes.length <= 7) {
      // Small graphs read best as a ring.
      const pos = Object.fromEntries(
        nodes.map((n, i) => {
          const ang = -Math.PI / 2 + (i / Math.max(1, nodes.length)) * Math.PI * 2;
          return [n.id, { x: 300 + Math.cos(ang) * 72 * 2.8, y: 98 + Math.sin(ang) * 72 * 1.05 }];
        })
      ) as Record<string, { x: number; y: number }>;
      return { layout: pos, H: 196, colW: 150 };
    }
    // Larger graphs: layers by dependency depth. Importers on the left, what they import on the right.
    const level: Record<string, number> = Object.fromEntries(nodes.map((n) => [n.id, 0]));
    for (let pass = 0; pass < nodes.length; pass++) {
      let changed = false;
      for (const e of edges) {
        if (e.cycle || !(e.src in level) || !(e.dst in level)) continue;
        if (level[e.dst] < level[e.src] + 1) {
          level[e.dst] = level[e.src] + 1;
          changed = true;
        }
      }
      if (!changed) break;
    }
    const cols = Math.max(...Object.values(level)) + 1;
    const byCol: string[][] = Array.from({ length: cols }, () => []);
    nodes.forEach((n) => byCol[level[n.id]].push(n.id));
    const rows = Math.max(...byCol.map((c) => c.length));
    const h = Math.max(196, rows * 32 + 24);
    const cw = cols > 1 ? 520 / (cols - 1) : 520;
    const pos: Record<string, { x: number; y: number }> = {};
    byCol.forEach((col, ci) => {
      col.forEach((id, ri) => {
        pos[id] = { x: cols > 1 ? 40 + ci * cw : 300, y: (h - col.length * 32) / 2 + ri * 32 + 16 };
      });
    });
    return { layout: pos, H: h, colW: cw };
  }, [g]);
  if (!g) return <p className="text-sm text-sub">No graph measured.</p>;
  const short = (id: string) => {
    const parts = id.split('.');
    return parts.length > 2 ? parts.slice(-2).join('.') : parts[parts.length - 1];
  };
  const loadedBefore = new Set(baseline?.loaded ?? []);

  return (
    <div>
      <svg viewBox={`0 0 600 ${H}`} className="block h-auto w-full" role="img" aria-label="Module import graph">
        <defs>
          <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 z" fill="#141517" />
          </marker>
          <marker id="arrow-bad" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L8,4 L0,8 z" fill="#e5484d" />
          </marker>
        </defs>
        {g.edges.map((e, i) => {
          const a = layout[e.src];
          const b = layout[e.dst];
          if (!a || !b) return null;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const len = Math.hypot(dx, dy) || 1;
          const ux = dx / len;
          const uy = dy / len;
          const off = e.cycle ? 5 : 0; // separate the two directions of a cycle
          return (
            <line
              key={i}
              x1={a.x + ux * Math.min(46, colW / 2) - uy * off}
              y1={a.y + uy * 13 + ux * off}
              x2={b.x - ux * Math.min(48, colW / 2) - uy * off}
              y2={b.y - uy * 14 + ux * off}
              stroke={e.cycle ? '#e5484d' : 'rgba(20,21,23,0.55)'}
              strokeWidth={e.cycle ? 2.2 : 1.3}
              strokeDasharray={e.lazy ? '4 3' : undefined}
              markerEnd={e.cycle ? 'url(#arrow-bad)' : 'url(#arrow)'}
            />
          );
        })}
        {g.nodes.map((n) => {
          const p = layout[n.id];
          const newlyFree = baseline && loadedBefore.has(n.id) && !n.loaded;
          const w = Math.min(colW - 8, 150, Math.max(56, (short(n.id)?.length ?? 6) * 6.6 + 14));
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`}>
              <rect x={-w / 2} y={-12} width={w} height={24} fill={n.loaded ? '#141517' : '#f1f1ee'} stroke="#141517" />
              {newlyFree && <rect x={-w / 2} y={-13} width={w} height={3} fill="#ffe100" />}
              <text textAnchor="middle" y={4} className={`font-mono text-[10.5px] ${n.loaded ? 'fill-paper' : 'fill-ink'}`}>
                {(short(n.id) ?? '').length * 6.4 > w - 8 ? `${(short(n.id) ?? '').slice(0, Math.floor((w - 8) / 6.4) - 1)}…` : short(n.id)}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[10.5px] text-sub">
        <span><span className="mr-1 inline-block h-2 w-2 bg-ink align-middle" />{filledLabel}</span>
        <span><span className="mr-1 inline-block h-0.5 w-4 bg-bad align-middle" />import cycle</span>
        <span>- - lazy import (inside a function)</span>
      </div>
    </div>
  );
};

/** Compact key metrics + sensor notes under a chart. */
export const MetricsStrip: React.FC<{ m: Measurement | null }> = ({ m }) => {
  if (!m) return null;
  if (m.error) return <p className="font-mono text-[12px] text-bad">{m.error}</p>;
  const entries = Object.entries(m.metrics ?? {}).filter(([, v]) => typeof v !== 'object');
  return (
    <div className="mt-3">
      <div className="grid grid-cols-2 border-l border-t border-hair sm:grid-cols-3">
        {entries.map(([k, v]) => (
          <div key={k} className="border-b border-r border-hair bg-paper px-2.5 py-1.5">
            <div className="font-cond text-[10px] uppercase tracking-[0.16em] text-sub">{k.replace(/_/g, ' ')}</div>
            <div className="font-mono text-[13px] text-ink">{String(v)}</div>
          </div>
        ))}
      </div>
      {(m.calls?.length || m.notes?.length) ? (
        <div className="mt-2 space-y-0.5 font-mono text-[10.5px] leading-relaxed text-sub">
          {m.calls && m.calls.length > 0 && (
            <div>
              sys.monitoring: {m.calls.filter((c) => !c.function.endsWith('<module>')).slice(0, 3).map((c) => `${c.function.split(':').pop()}×${c.calls}`).join(' · ')}
            </div>
          )}
          {m.notes?.map((n) => <div key={n}>{n}</div>)}
          {m.python && <div>python {m.python} · probe {m.wall_ms} ms</div>}
        </div>
      ) : null}
    </div>
  );
};
