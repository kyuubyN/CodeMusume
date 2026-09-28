import React from 'react';

interface Props {
  file: string;
  lines: string[];
  /** Clickable lines (evidence step). */
  onPick?: (line: number) => void;
  disabled?: boolean;
  best?: number[];
  ok?: number[];
  wrong?: number[];
}

const KEYWORDS = new Set([
  'def', 'return', 'import', 'from', 'with', 'as', 'try', 'except', 'finally', 'for', 'in', 'if', 'elif', 'else',
  'async', 'await', 'raise', 'class', 'pass', 'while', 'lambda', 'not', 'and', 'or', 'is', 'None', 'True', 'False',
  'yield', 'break', 'continue', 'global', 'nonlocal', 'del',
]);

/** Tiny Python highlighter: keywords, strings, comments, decorators. */
function highlight(src: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(#.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(@\w+)|(\b[A-Za-z_]\w*\b)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(src))) {
    if (m.index > last) out.push(src.slice(last, m.index));
    const [tok] = m;
    if (m[1]) out.push(<span key={k++} className="text-paper/40">{tok}</span>);
    else if (m[2]) out.push(<span key={k++} className="text-[#b9d99a]">{tok}</span>);
    else if (m[3]) out.push(<span key={k++} className="text-info">{tok}</span>);
    else if (KEYWORDS.has(tok)) out.push(<span key={k++} className="font-semibold text-acc">{tok}</span>);
    else out.push(tok);
    last = m.index + tok.length;
  }
  if (last < src.length) out.push(src.slice(last));
  return out;
}

export const CodeView: React.FC<Props> = ({ file, lines, onPick, disabled, best = [], ok = [], wrong = [] }) => {
  const pickable = !!onPick && !disabled;
  return (
    <div className="bg-ink text-paper">
      <div className="flex justify-between border-b border-paper/10 px-3 py-1.5 font-mono text-[11px] text-paper/50">
        <span>{file}</span>
        {pickable && <span className="text-acc">click the culprit line</span>}
      </div>
      <pre className="scroll-thin overflow-x-auto py-2 font-mono text-[12.5px] leading-[1.65]">
        {lines.map((ln, i) => {
          const n = i + 1;
          const isBest = best.includes(n);
          const isOk = ok.includes(n);
          const isWrong = wrong.includes(n);
          const blank = !ln.trim();
          const cls = isBest
            ? 'bg-acc/20 shadow-[inset_3px_0_0_#ffe100]'
            : isOk
              ? 'bg-paper/[0.07] shadow-[inset_3px_0_0_rgba(255,225,0,0.45)]'
              : isWrong
                ? 'bg-bad/15 shadow-[inset_3px_0_0_#e5484d]'
                : '';
          const Tag = pickable && !blank ? 'button' : 'div';
          return (
            <Tag
              key={i}
              type={Tag === 'button' ? 'button' : undefined}
              onClick={pickable && !blank ? () => onPick!(n) : undefined}
              className={`flex w-full pr-3 text-left ${cls} ${pickable && !blank ? 'cursor-pointer hover:bg-acc/10' : ''}`}
              aria-label={pickable && !blank ? `Present line ${n}` : undefined}
            >
              <span className={`w-10 shrink-0 select-none pr-3 text-right ${isBest ? 'text-acc' : isWrong ? 'text-bad' : 'text-paper/30'}`}>
                {n}
              </span>
              <code className={`whitespace-pre ${isWrong ? 'line-through decoration-bad/70' : ''}`}>{ln ? highlight(ln) : ' '}</code>
            </Tag>
          );
        })}
      </pre>
    </div>
  );
};

export const DiffView: React.FC<{ diff: string }> = ({ diff }) => (
  <pre className="scroll-thin max-h-72 overflow-auto bg-ink py-2 font-mono text-[11.5px] leading-[1.6] text-paper/80">
    {diff.split('\n').map((l, i) => {
      const cls = l.startsWith('+++') || l.startsWith('---')
        ? 'text-paper/40'
        : l.startsWith('@@')
          ? 'text-info'
          : l.startsWith('+')
            ? 'bg-ok/20 text-paper'
            : l.startsWith('-')
              ? 'bg-bad/20 text-paper/70'
              : '';
      return (
        <div key={i} className={`whitespace-pre px-3 ${cls}`}>
          {l || ' '}
        </div>
      );
    })}
  </pre>
);
