"""Turn analyzer results into case-file smells for the free lab (your own repo).

These rules need whole-program reasoning that the per-file scanner cannot do:

* STAMINA-003 — a resource leaks on an exception path (CFG dataflow)
* STAMINA-004 — a resource is never closed on some normal path (CFG dataflow)
* SPEED-003   — an async function reaches a blocking call through other functions (call graph)
* POWER-002   — a loop makes a database or network round trip per iteration (call graph)
* WISDOM-003  — modules import each other in a cycle (module graph)
* WISDOM-004  — a cycle hidden behind a function-level import (module graph)
"""
from __future__ import annotations

import os
import textwrap

from app.lab.analysis import RepoAnalysis, analyze_repo
from app.models.schemas import AttributeScores, AttributeType
from app.services.scanner_service import DetectedSmell, RepoScanner

def _snippet(path: str, line: int, before: int = 1, after: int = 1) -> tuple[str, int]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return "", line
    start = max(0, line - 1 - before)
    end = min(len(lines), line + after)
    return textwrap.dedent("\n".join(lines[start:end])).rstrip(), start + 1


def analyzer_smells(root: str, analysis: RepoAnalysis | None = None) -> list[DetectedSmell]:
    a = analysis or analyze_repo(root)
    out: list[DetectedSmell] = []
    for leak in a.leaks:
        rule = "STAMINA-003" if leak.kind == "exception_path" else "STAMINA-004"
        snippet, _ = _snippet(leak.file, leak.open_line, 1, 2)
        out.append(DetectedSmell(
            file_path=leak.file, line_number=leak.open_line, attribute=AttributeType.STAMINA, rule_id=rule,
            description=leak.summary,
            tachyon_critique=(
                "My dataflow followed every path out of this function, including the exceptional ones. "
                "On at least one, the handle walks out still open."
            ),
            suggested_fix=f"Acquire `{leak.name}` in a `with` block (or close it in `finally`) so every path releases it.",
            code_snippet=snippet,
        ))
    for chain in a.blocking:
        if len(chain.links) < 2:
            continue  # direct blocking calls are already caught by the scanner (SPEED-001)
        root_link = chain.links[0]
        snippet, _ = _snippet(chain.root.file, root_link.line)
        hops = " → ".join(link.callee.split(".")[-1] for link in chain.links)
        out.append(DetectedSmell(
            file_path=chain.root.file, line_number=root_link.line, attribute=AttributeType.SPEED, rule_id="SPEED-003",
            description=f"async `{chain.root.name}` blocks the event loop through {hops}",
            tachyon_critique=(
                f"`{chain.root.name}` looks asynchronous, but {len(chain.links)} calls down it reaches "
                f"`{chain.primitive}`, which holds the only thread the event loop has."
            ),
            suggested_fix="Use an async client for the slow call, or offload the chain with `await asyncio.to_thread(...)`.",
            code_snippet=snippet,
        ))
    for loop in a.loops:
        snippet, _ = _snippet(loop.func.file, loop.call.line)
        via = loop.links[-1].callee
        out.append(DetectedSmell(
            file_path=loop.func.file, line_number=loop.call.line, attribute=AttributeType.POWER, rule_id="POWER-002",
            description=f"loop in `{loop.func.name}` makes a round trip per iteration via `{via}`"
                        + (" (cached)" if loop.cached else ""),
            tachyon_critique="Each iteration knocks on a remote door. The latency of every trip adds up: N+1 in the flesh.",
            suggested_fix="Fetch everything in one batched call: a JOIN, `WHERE id IN (...)`, or a bulk API endpoint.",
            code_snippet=snippet,
        ))
    hidden = {tuple(c) for c in a.arch.hidden_cycles}
    for cyc in a.arch.cycles:
        edges = [e for e in a.arch.cycle_edges if e.src in cyc and e.dst in cyc]
        if not edges:
            continue
        e = edges[0]
        path = a.program.files[e.src]
        is_hidden = tuple(cyc) in hidden
        snippet, _ = _snippet(path, e.line, 0, 0)
        out.append(DetectedSmell(
            file_path=path, line_number=e.line, attribute=AttributeType.WISDOM,
            rule_id="WISDOM-004" if is_hidden else "WISDOM-003",
            description=("hidden import cycle " if is_hidden else "import cycle ") + " ↔ ".join(m.split(".")[-1] for m in cyc),
            tachyon_critique=(
                "These modules depend on each other, so neither can be understood, tested or changed alone. "
                + ("A function-level import hides it from Python, not from me." if is_hidden else "")
            ),
            suggested_fix="Extract what both need into a small module that depends on neither, so arrows point one way.",
            code_snippet=snippet,
        ))
    return out


def scan_repo_full(root: str) -> tuple[AttributeScores, list[DetectedSmell]]:
    """Per-file scanner rules plus the whole-program analyzer rules.

    Stats come from the standards check (findings per thousand lines), so the
    score reflects how healthy the code is, not how big it is.
    """
    from app.lab.standards import build_report

    _, scanner = RepoScanner(target_path=root).scan_repository()
    smells = list(scanner)
    try:
        analysis = analyze_repo(root)
        extra = analyzer_smells(root, analysis)
    except (RecursionError, ValueError):
        return AttributeScores(), smells
    index = {(os.path.abspath(s.file_path), s.line_number, s.attribute): i for i, s in enumerate(smells)}
    for s in extra:
        key = (os.path.abspath(s.file_path), s.line_number, s.attribute)
        if key in index:
            # Same spot as a per-file rule: keep the deeper, path-aware explanation.
            smells[index[key]] = s
            continue
        index[key] = len(smells)
        smells.append(s)
    report = build_report(root, analysis, scanner)
    return AttributeScores(**report["scores"]), smells
