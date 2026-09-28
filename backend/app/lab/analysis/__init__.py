"""From-scratch static analysis: CFG dataflow, call graph and module graph.

``analyze_repo`` runs all three passes over a repository and
``findings_as_smells`` turns their results into case-file entries that sit
next to the per-file scanner rules.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from app.lab.analysis.archgraph import ArchReport, analyze as analyze_arch
from app.lab.analysis.callgraph import BlockingChain, LoopRoundTrip, Program, iter_py_files
from app.lab.analysis.dataflow import ResourceLeak, analyze_source


@dataclass
class RepoAnalysis:
    root: str
    program: Program
    leaks: list[ResourceLeak]
    blocking: list[BlockingChain]
    loops: list[LoopRoundTrip]
    arch: ArchReport

    def to_dict(self) -> dict:
        rel = lambda p: os.path.relpath(p, self.root)  # noqa: E731
        return {
            "leaks": [
                {"file": rel(l.file), "function": l.function, "name": l.name, "open_line": l.open_line,
                 "kind": l.kind, "raise_lines": l.raise_lines, "close_lines": l.close_lines, "summary": l.summary}
                for l in self.leaks
            ],
            "blocking": [
                {"function": c.root.qual, "file": rel(c.root.file), "line": c.root.line, "summary": c.summary,
                 "chain": [{"func": k.func.split(".")[-1], "line": k.line, "callee": k.callee, "file": rel(k.file)} for k in c.links]}
                for c in self.blocking
            ],
            "loops": [
                {"function": r.func.qual, "file": rel(r.func.file), "loop_line": r.loop_line, "cached": r.cached,
                 "summary": r.summary,
                 "chain": [{"func": k.func.split(".")[-1], "line": k.line, "callee": k.callee, "file": rel(k.file)} for k in r.links]}
                for r in self.loops
            ],
            "modules": self.arch.modules,
            "edges": [{"src": e.src, "dst": e.dst, "line": e.line, "lazy": e.lazy} for e in self.arch.edges],
            "cycles": self.arch.cycles,
            "hidden_cycles": self.arch.hidden_cycles,
            "metrics": {m: vars(x) for m, x in self.arch.metrics.items()},
        }


def analyze_repo(root: str) -> RepoAnalysis:
    program = Program(root)
    leaks: list[ResourceLeak] = []
    for path in iter_py_files(root):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                leaks.extend(analyze_source(fh.read(), path))
        except SyntaxError:
            continue
    return RepoAnalysis(root, program, leaks, program.blocking_chains(), program.loop_round_trips(), analyze_arch(program))
