"""Module dependency graph: cycles, coupling metrics and blast radius.

* Edges come from every ``import`` in a module, including imports inside
  functions. Those are flagged ``lazy``: they dodge the import-time error, but
  the dependency (and the cycle) is still there, just hidden.
* Cycles are strongly connected components (Tarjan, iterative).
* Coupling follows Robert C. Martin: afferent ``Ca`` (who depends on me),
  efferent ``Ce`` (whom I depend on) and instability ``I = Ce / (Ca + Ce)``.
* Blast radius of a module = how many other modules transitively depend on it,
  i.e. what may break (or need retesting) when it changes.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

from app.lab.analysis.callgraph import Program


@dataclass
class ImportEdge:
    src: str
    dst: str
    line: int
    lazy: bool
    facade: bool = False     # a package __init__ re-exporting its own submodule
    type_only: bool = False  # inside `if TYPE_CHECKING:`; never executed at runtime


@dataclass
class ModuleMetrics:
    name: str
    ca: int
    ce: int
    instability: float
    blast_radius: int
    transitive_deps: int
    lines: int


@dataclass
class ArchReport:
    modules: list[str]
    edges: list[ImportEdge]
    cycles: list[list[str]]
    metrics: dict[str, ModuleMetrics]
    cycle_edges: list[ImportEdge] = field(default_factory=list)

    @property
    def hidden_cycles(self) -> list[list[str]]:
        """Cycles that only exist through function-level (lazy) imports."""
        out = []
        for cyc in self.cycles:
            members = set(cyc)
            eager = [e for e in self.edges if e.src in members and e.dst in members and not e.lazy and not e.facade and not e.type_only]
            if not _has_cycle(members, eager):
                out.append(cyc)
        return out


def _has_cycle(members: set[str], edges: list[ImportEdge]) -> bool:
    adj: dict[str, list[str]] = {m: [] for m in members}
    for e in edges:
        adj[e.src].append(e.dst)
    return any(len(c) > 1 for c in tarjan(list(members), adj))


def tarjan(nodes: list[str], adj: dict[str, list[str]]) -> list[list[str]]:
    """Strongly connected components, iterative (no recursion limit surprises)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    comps: list[list[str]] = []
    counter = 0
    for start in nodes:
        if start in index:
            continue
        work = [(start, iter(adj.get(start, [])))]
        index[start] = low[start] = counter
        counter += 1
        stack.append(start)
        on_stack.add(start)
        while work:
            v, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, iter(adj.get(w, []))))
                    advanced = True
                    break
                if w in on_stack:
                    low[v] = min(low[v], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                comps.append(sorted(comp))
    return comps


def _is_type_checking(test: ast.AST) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def import_edges(program: Program) -> list[ImportEdge]:
    mods = set(program.trees)
    edges: dict[tuple[str, str], ImportEdge] = {}

    def add(src: str, dst: str, line: int, lazy: bool, type_only: bool) -> None:
        if dst == src or dst not in mods:
            return
        key = (src, dst)
        prev = edges.get(key)
        facade = program.is_package.get(src, False) and dst.startswith(src + ".")
        rank = (type_only, lazy)  # prefer the strongest (eager, runtime) import
        if prev is None or rank < (prev.type_only, prev.lazy):
            edges[key] = ImportEdge(src, dst, line, lazy, facade, type_only)

    def target_module(name: str) -> str | None:
        # Longest prefix that names a module in the repo (by path or by suffix).
        parts = name.split(".")
        for i in range(len(parts), 0, -1):
            cand = program.lookup(".".join(parts[:i]))
            if cand:
                return cand
        return None

    for mod, tree in program.trees.items():
        lazy_nodes: set[int] = set()
        typing_nodes: set[int] = set()
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for inner in ast.walk(fn):
                    if isinstance(inner, (ast.Import, ast.ImportFrom)):
                        lazy_nodes.add(id(inner))
            if isinstance(fn, ast.If) and _is_type_checking(fn.test):
                for stmt in fn.body:
                    for inner in ast.walk(stmt):
                        if isinstance(inner, (ast.Import, ast.ImportFrom)):
                            typing_nodes.add(id(inner))
        for node in ast.walk(tree):
            lazy = id(node) in lazy_nodes
            type_only = id(node) in typing_nodes
            if isinstance(node, ast.Import):
                for a in node.names:
                    t = target_module(a.name)
                    if t:
                        add(mod, t, node.lineno, lazy, type_only)
            elif isinstance(node, ast.ImportFrom):
                base = program.resolve_relative(mod, node.level, node.module) if node.level else (node.module or "")
                for a in node.names:
                    full = f"{base}.{a.name}" if base else a.name
                    t = program.lookup(full) or (target_module(base) if base else None)
                    if t:
                        add(mod, t, node.lineno, lazy, type_only)
    return sorted(edges.values(), key=lambda e: (e.src, e.line, e.dst))


def analyze(program: Program) -> ArchReport:
    modules = sorted(program.trees)
    edges = import_edges(program)
    adj: dict[str, list[str]] = {m: [] for m in modules}
    radj: dict[str, list[str]] = {m: [] for m in modules}
    cyc_adj: dict[str, list[str]] = {m: [] for m in modules}
    for e in edges:
        if e.type_only:
            continue  # annotations only: no runtime dependency
        adj[e.src].append(e.dst)
        radj[e.dst].append(e.src)
        if not e.facade:
            cyc_adj[e.src].append(e.dst)

    # Facade edges (package __init__ re-exporting its submodules) are how Python
    # packages present an API; they would put every package in a "cycle".
    cycles = [c for c in tarjan(modules, cyc_adj) if len(c) > 1]
    in_cycle = {m: i for i, c in enumerate(cycles) for m in c}
    cycle_edges = [e for e in edges if not e.facade and not e.type_only and e.src in in_cycle and in_cycle.get(e.dst) == in_cycle[e.src]]

    def closure(start: str, graph: dict[str, list[str]]) -> int:
        seen, stack = {start}, [start]
        while stack:
            for p in graph[stack.pop()]:
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        return len(seen) - 1

    metrics: dict[str, ModuleMetrics] = {}
    for m in modules:
        ca = len(set(radj[m]))
        ce = len(set(adj[m]))
        with open(program.files[m], encoding="utf-8", errors="replace") as fh:
            lines = sum(1 for _ in fh)
        metrics[m] = ModuleMetrics(
            name=m,
            ca=ca,
            ce=ce,
            instability=round(ce / (ca + ce), 2) if ca + ce else 0.0,
            blast_radius=closure(m, radj),
            transitive_deps=closure(m, adj),
            lines=lines,
        )
    return ArchReport(modules, edges, cycles, metrics, cycle_edges)
