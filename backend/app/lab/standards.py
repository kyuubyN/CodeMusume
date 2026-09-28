"""Architecture standards check for a local repository (the free lab).

Ten fitness functions, each a pass / warn / fail with the measured value, the
threshold, and evidence (file:line). Every check is tied to the lab chapter
that teaches it, so a failing check becomes "go learn this, then come back and
fix it in your own code".

Stats in the free lab are derived from these checks by *density* (findings per
thousand lines), so a large healthy repository is not punished for its size.
"""
from __future__ import annotations

import ast
import math
import os
from dataclasses import dataclass, field

from app.lab.analysis import RepoAnalysis, analyze_repo
from app.models.schemas import AttributeScores
from app.services.scanner_service import DetectedSmell, RepoScanner

LO, HI = 120, 1120


@dataclass
class Check:
    id: str
    title: str
    stat: str
    chapter: int
    status: str            # "pass" | "warn" | "fail"
    value: str
    target: str
    detail: str
    evidence: list[dict] = field(default_factory=list)


def _rel(root: str, path: str) -> str:
    return os.path.relpath(path, root)


def _line(path: str, n: int) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for i, text in enumerate(fh, 1):
                if i == n:
                    return text.strip()[:120]
    except OSError:
        pass
    return ""


def _ev(root: str, path: str, line: int, note: str = "") -> dict:
    return {"file": _rel(root, path), "line": line, "code": _line(path, line), "note": note}


def _status(bad: float, warn_at: float = 0.0, fail_at: float = 0.0) -> str:
    if bad <= warn_at:
        return "pass"
    return "fail" if bad > fail_at else "warn"


def _annotation_coverage(a: RepoAnalysis) -> tuple[int, int]:
    total = annotated = 0
    for tree in a.program.trees.values():
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("__"):
                total += 1
                annotated += n.returns is not None
    return annotated, total


def build_report(root: str, analysis: RepoAnalysis | None = None, scanner: list[DetectedSmell] | None = None) -> dict:
    a = analysis or analyze_repo(root)
    if scanner is None:
        _, scanner = RepoScanner(target_path=root).scan_repository()
    arch = a.arch
    mods = [m for m in arch.modules]
    n_mods = max(1, len(mods))
    kloc = max(0.3, a.program.lines / 1000)
    rule = lambda r: [s for s in scanner if s.rule_id == r]  # noqa: E731
    checks: list[Check] = []

    # 1. Acyclic imports ---------------------------------------------------
    eager = [c for c in arch.cycles if c not in arch.hidden_cycles]
    in_cycles = sorted({m for c in eager for m in c})
    ev = []
    for e in arch.cycle_edges[:6]:
        if not e.lazy:
            ev.append(_ev(root, a.program.files[e.src], e.line, f"{e.src} → {e.dst}"))
    checks.append(Check(
        "acyclic", "Imports form no cycles", "wisdom", 5, "pass" if not eager else "fail",
        f"{len(eager)} cycle{'s' if len(eager) != 1 else ''} · {len(in_cycles)} modules", "0 cycles",
        "Modules in a cycle cannot be understood, tested or changed alone."
        + (f" Largest: {len(max(eager, key=len))} modules." if eager else ""),
        ev,
    ))

    # 2. No hidden cycles -----------------------------------------------------
    hidden = arch.hidden_cycles
    ev = [_ev(root, a.program.files[e.src], e.line, "function-level import")
          for e in arch.cycle_edges if e.lazy][:6]
    checks.append(Check(
        "hidden_cycles", "No cycles hidden in function-level imports", "wisdom", 5, "pass" if not hidden else "warn",
        f"{len(hidden)}", "0", "A lazy import avoids the ImportError, not the coupling.", ev,
    ))

    # 3. Blast radius ---------------------------------------------------------
    # Being depended on is fine for small, stable modules (that is the point of
    # them). The risk is a hub that is also volatile or big.
    others = max(1, n_mods - 1)
    ranked = sorted(arch.metrics.values(), key=lambda m: -m.blast_radius)
    risky = [m for m in ranked if m.blast_radius / others > 0.5 and (m.instability > 0.3 or m.lines > 400)]
    worst = risky[0] if risky else (ranked[0] if ranked else None)
    checks.append(Check(
        "blast_radius", "No volatile hub can break most of the codebase", "wisdom", 5,
        "pass" if n_mods < 6 or not risky else ("warn" if len(risky) <= 2 else "fail"),
        (f"{len(risky)} risky hub{'s' if len(risky) != 1 else ''}" + (f" · {worst.name} reaches {worst.blast_radius}/{others}" if worst else ""))
        if n_mods >= 6 else "n/a (under 6 modules)",
        "no module over 50% that is unstable or > 400 lines",
        "Blast radius = modules that transitively depend on this one. Keep the widely used ones small and stable.",
        [{"file": m.name, "line": 0, "code": f"blast radius {m.blast_radius} · I {m.instability} · {m.lines} lines", "note": ""}
         for m in (risky or ranked)[:4] if m.blast_radius],
    ))

    # 4. Stable dependencies principle -------------------------------------
    sdp = []
    for e in arch.edges:
        if e.type_only or e.facade:
            continue
        src, dst = arch.metrics.get(e.src), arch.metrics.get(e.dst)
        if src and dst and dst.ca + dst.ce >= 3 and dst.instability > src.instability + 0.3:
            sdp.append(e)
    runtime_edges = max(1, sum(1 for e in arch.edges if not e.type_only and not e.facade))
    checks.append(Check(
        "stable_deps", "Dependencies point toward stability", "wisdom", 5,
        _status(len(sdp) / runtime_edges, 0.05, 0.2),
        f"{len(sdp)} of {runtime_edges} imports", "≤ 5%",
        "Robert C. Martin's SDP: a stable module (many dependents) should not depend on a volatile one.",
        [_ev(root, a.program.files[e.src], e.line,
             f"I {arch.metrics[e.src].instability} → I {arch.metrics[e.dst].instability}") for e in sdp[:5]],
    ))

    # 5. Resource lifetimes ------------------------------------------------
    checks.append(Check(
        "resources", "Every resource is closed on every path", "stamina", 1,
        "pass" if not a.leaks else "fail", f"{len(a.leaks)} leak{'s' if len(a.leaks) != 1 else ''}", "0",
        "Found by CFG dataflow, including exception paths.",
        [_ev(root, l.file, l.open_line, l.summary.replace("`", "")) for l in a.leaks[:6]],
    ))

    # 6. Event loop ----------------------------------------------------------
    direct = rule("SPEED-001")
    chains = [c for c in a.blocking if len(c.links) > 1]
    checks.append(Check(
        "event_loop", "No async code reaches a blocking call", "speed", 2,
        "pass" if not (direct or chains) else "fail", f"{len(direct) + len(chains)}", "0",
        "Checked through the call graph, not just inside each async def.",
        [_ev(root, s.file_path, s.line_number, "direct blocking call") for s in direct[:3]]
        + [_ev(root, c.root.file, c.links[0].line, c.summary.replace("`", "")) for c in chains[:4]],
    ))

    # 7. Round trips in loops ---------------------------------------------
    checks.append(Check(
        "round_trips", "No database or network round trip per loop iteration", "power", 3,
        _status(len(a.loops), 0, 3), f"{len(a.loops)}", "0",
        "N+1: each iteration pays a full round trip. Batch it.",
        [_ev(root, r.func.file, r.call.line, r.summary.replace("`", "")) for r in a.loops[:6]],
    ))

    # 8. Honest failures ----------------------------------------------------
    swallowed, no_timeout = rule("GUTS-001"), rule("GUTS-002")
    checks.append(Check(
        "failures", "Remote calls have deadlines and errors are not swallowed", "guts", 4,
        "pass" if not (swallowed or no_timeout) else "fail",
        f"{len(swallowed)} swallowed · {len(no_timeout)} without timeout", "0 · 0",
        "A hidden failure is worse than a loud one.",
        [_ev(root, s.file_path, s.line_number, s.description.replace("`", "")) for s in (swallowed + no_timeout)[:6]],
    ))

    # 9. Module size ---------------------------------------------------------
    gods = [m for m in arch.metrics.values() if m.lines > 800 and m.ca >= 5]
    checks.append(Check(
        "god_modules", "No oversized module that everyone depends on", "wisdom", 5,
        "pass" if not gods else "warn", f"{len(gods)}", "0 over 800 lines with ≥ 5 dependents",
        "Big and central means every change is risky.",
        [{"file": m.name, "line": 0, "code": f"{m.lines} lines · {m.ca} dependents", "note": ""} for m in gods[:4]],
    ))

    # 10. Type annotations ---------------------------------------------------
    annotated, total = _annotation_coverage(a)
    cov = annotated / total if total else 1.0
    checks.append(Check(
        "annotations", "Public functions declare return types", "wisdom", 5,
        "pass" if cov >= 0.8 else ("warn" if cov >= 0.5 else "fail"), f"{round(cov * 100)}%", "≥ 80%",
        "Types are the cheapest documentation of a contract.", [],
    ))

    passed = sum(c.status == "pass" for c in checks)
    return {
        "root": os.path.basename(os.path.abspath(root)),
        "files": len(a.program.files),
        "modules": len(mods),
        "lines": a.program.lines,
        "parse_errors": [_rel(root, p) for p in a.program.parse_errors][:5],
        "passed": passed,
        "total": len(checks),
        "grade": _grade(checks),
        "checks": [vars(c) for c in checks],
        "graph": _graph(a),
        "scores": scores_from(a, scanner, kloc, cov).model_dump(),
    }


def _grade(checks: list[Check]) -> str:
    pts = sum({"pass": 2, "warn": 1, "fail": 0}[c.status] for c in checks) / (2 * len(checks))
    for g, cut in (("S", 0.95), ("A", 0.85), ("B", 0.7), ("C", 0.55), ("D", 0.4), ("E", 0.25)):
        if pts >= cut:
            return g
    return "F"


def _graph(a: RepoAnalysis, limit: int = 16) -> dict:
    """The most connected modules and the runtime imports among them."""
    arch = a.arch
    ranked = sorted(arch.metrics.values(), key=lambda m: -(m.ca + m.ce + 3 * any(m.name in c for c in arch.cycles)))
    keep = {m.name for m in ranked[:limit]}
    in_cycle = {m for c in arch.cycles for m in c}
    return {
        "nodes": [{"id": m, "loaded": m in in_cycle, "blast_radius": arch.metrics[m].blast_radius,
                   "instability": arch.metrics[m].instability} for m in sorted(keep)],
        "edges": [{"src": e.src, "dst": e.dst, "lazy": e.lazy,
                   "cycle": any(e.src in c and e.dst in c for c in arch.cycles)}
                  for e in arch.edges if e.src in keep and e.dst in keep and not e.type_only and not e.facade],
        "truncated": len(arch.modules) > limit,
    }


def _q(weighted: float, kloc: float, k: float) -> float:
    """1.0 for zero findings, decaying with findings per thousand lines."""
    return math.exp(-k * weighted / kloc)


def scores_from(a: RepoAnalysis, scanner: list[DetectedSmell], kloc: float, coverage: float) -> AttributeScores:
    count = lambda *rules: sum(1 for s in scanner if s.rule_id in rules)  # noqa: E731
    chains = sum(1 for c in a.blocking if len(c.links) > 1)
    speed = _q(count("SPEED-001") + chains + 0.25 * count("SPEED-002"), kloc, 0.6)
    stamina = _q(len(a.leaks) + 0.5 * count("STAMINA-001", "STAMINA-002"), kloc, 0.8)
    power = _q(len(a.loops) + 0.3 * count("POWER-001"), kloc, 0.5)
    guts = _q(count("GUTS-001") + 0.5 * count("GUTS-002"), kloc, 0.5)
    n = max(1, len(a.arch.modules))
    in_cycles = len({m for c in a.arch.cycles for m in c})
    wisdom = 0.45 * (1 - in_cycles / n) + 0.25 * coverage + 0.3 * _q(count("WISDOM-002"), kloc, 0.5)
    to = lambda q: round(LO + (HI - LO) * max(0.0, min(1.0, q)))  # noqa: E731
    return AttributeScores(speed=to(speed), stamina=to(stamina), power=to(power), guts=to(guts), wisdom=to(wisdom))
