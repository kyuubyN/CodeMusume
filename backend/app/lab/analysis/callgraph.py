"""Whole-repository symbol table and call graph, resolved through imports.

Two interprocedural questions a per-file linter cannot answer:

* **Blocking reachability** — does an ``async def`` reach a blocking primitive
  (``time.sleep``, ``urllib.request.urlopen``, ``requests.get``…) through any
  chain of calls? A handler that calls a helper that calls an SDK that sleeps
  freezes the event loop just the same.
* **Round trips in loops** — does a loop body call something that (directly or
  through helpers) goes to the database or the network once per iteration?

Calls are resolved statically: local functions, ``self.method``, and names
brought in by ``import``/``from … import`` (including relative imports).
Functions passed as values (``asyncio.to_thread(fn)``) are not calls, which
is exactly why offloading removes them from the blocking chain.
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field

_SKIP_DIRS = {".git", "venv", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build"}

BLOCKING_EXACT = {
    "time.sleep", "urllib.request.urlopen", "subprocess.run", "subprocess.call",
    "subprocess.check_output", "subprocess.check_call", "os.system", "socket.create_connection",
}
BLOCKING_PREFIXES = ("requests.", "httpx.get", "httpx.post", "httpx.put", "httpx.delete", "httpx.request")
ROUND_TRIP_ATTRS = {"execute", "executemany", "executescript", "query", "urlopen"}
ROUND_TRIP_PREFIXES = ("requests.", "httpx.", "urllib.request.urlopen")
CACHE_DECORATORS = {"lru_cache", "cache", "cached"}
_RETRY_NAME = re.compile(r"^_?(attempt|retr|tries|try_|backoff)", re.I)


@dataclass
class CallSite:
    line: int
    raw: str                 # dotted text as written, e.g. "billing.charge"
    target: str              # resolved name: internal qualname or external dotted name
    internal: bool
    in_loop: int | None      # line of the innermost enclosing loop, if any
    awaited: bool
    imported: bool = False   # the head name came from an import (so an external target is trustworthy)


@dataclass
class FuncInfo:
    qual: str
    module: str
    name: str
    file: str
    line: int
    is_async: bool
    cached: bool
    calls: list[CallSite] = field(default_factory=list)


@dataclass
class ChainLink:
    func: str        # qualname of the function the call happens in
    line: int        # line of the call
    callee: str      # what it calls (qualname or primitive)
    file: str


@dataclass
class BlockingChain:
    root: FuncInfo
    links: list[ChainLink]

    @property
    def primitive(self) -> str:
        return self.links[-1].callee

    @property
    def summary(self) -> str:
        path = " → ".join([self.root.name] + [link.callee.split(".")[-1] if i < len(self.links) - 1 else link.callee
                                              for i, link in enumerate(self.links)])
        return f"async `{self.root.name}` reaches blocking `{self.primitive}` via {path}"


@dataclass
class LoopRoundTrip:
    func: FuncInfo
    loop_line: int
    call: CallSite
    links: list[ChainLink]
    cached: bool

    @property
    def summary(self) -> str:
        via = self.links[-1].callee if self.links else self.call.target
        extra = " (cached, so only per distinct key)" if self.cached else ""
        return f"loop on line {self.loop_line} of `{self.func.name}` makes a round trip per iteration via `{via}`{extra}"


def package_prefix(root: str) -> str:
    """If the root itself is a package (has __init__.py), its name prefixes every module."""
    root = os.path.abspath(root)
    return os.path.basename(root) if os.path.exists(os.path.join(root, "__init__.py")) else ""


def module_name(root: str, path: str, prefix: str = "") -> str:
    rel = os.path.relpath(path, root)
    mod = rel[:-3] if rel.endswith(".py") else rel
    mod = mod.replace(os.sep, ".")
    if prefix:
        mod = f"{prefix}.{mod}"
    if mod == "__init__":
        return prefix or "__init__"
    return mod[: -len(".__init__")] if mod.endswith(".__init__") else mod


def iter_py_files(root: str) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS and not d.startswith("."))
        for f in sorted(filenames):
            if f.endswith(".py"):
                out.append(os.path.join(dirpath, f))
    return out


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        inner = dotted(node.value)
        return f"{inner}.{node.attr}" if inner else ""
    return ""


class Program:
    """Parsed repository with resolved imports and a call graph."""

    def __init__(self, root: str) -> None:
        self.root = root
        self.trees: dict[str, ast.Module] = {}
        self.files: dict[str, str] = {}
        self.is_package: dict[str, bool] = {}
        self.aliases: dict[str, dict[str, str]] = {}
        self.funcs: dict[str, FuncInfo] = {}
        self.parse_errors: list[str] = []
        self.lines = 0
        prefix = package_prefix(root)
        for path in iter_py_files(root):
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
                tree = ast.parse(src, filename=path)
            except (SyntaxError, ValueError):
                self.parse_errors.append(path)
                continue
            self.lines += src.count("\n") + 1
            mod = module_name(root, path, prefix)
            self.trees[mod] = tree
            self.files[mod] = path
            self.is_package[mod] = path.endswith("__init__.py")
        # Imports may name a module by a suffix of our path-based name (src/ layouts,
        # a root that is itself a package), so index every dotted suffix.
        self._suffix: dict[str, list[str]] = {}
        for mod in self.trees:
            parts = mod.split(".")
            for i in range(1, len(parts)):
                self._suffix.setdefault(".".join(parts[i:]), []).append(mod)
        for mod, tree in self.trees.items():
            self.aliases[mod] = self._collect_aliases(mod, tree)
        pending: list[tuple[FuncInfo, ast.FunctionDef | ast.AsyncFunctionDef, str | None]] = []
        for mod, tree in self.trees.items():
            self._collect_functions(mod, tree, pending)
        # Calls are resolved once every function in the repository is known.
        for info, node, cls in pending:
            info.calls = self._calls_in(node, info.module, cls, info.qual)
        self._blocking_memo: dict[str, list[ChainLink] | None] = {}
        self._roundtrip_memo: dict[str, list[ChainLink] | None] = {}

    # ------------------------------------------------------------------ #
    # Imports

    def lookup(self, name: str) -> str | None:
        """The repo module an import refers to, or None if it is external."""
        if name in self.trees:
            return name
        cands = self._suffix.get(name, [])
        return min(cands, key=len) if cands else None

    def resolve_symbol(self, dotted: str) -> str | None:
        """Map ``pkg.mod.func`` / ``pkg.mod.Class.method`` to a known function qualname."""
        if dotted in self.funcs:
            return dotted
        parts = dotted.split(".")
        for i in range(len(parts) - 1, 0, -1):
            mod = self.lookup(".".join(parts[:i]))
            if mod:
                q = f"{mod}.{'.'.join(parts[i:])}"
                return q if q in self.funcs else None
        return None

    def resolve_relative(self, mod: str, level: int, target: str | None) -> str:
        pkg_parts = mod.split(".") if self.is_package.get(mod) else mod.split(".")[:-1]
        if level > 1:
            pkg_parts = pkg_parts[: len(pkg_parts) - (level - 1)]
        base = ".".join(pkg_parts)
        if target:
            return f"{base}.{target}" if base else target
        return base

    def _collect_aliases(self, mod: str, tree: ast.Module) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.asname:
                        aliases[a.asname] = a.name
                    else:
                        top = a.name.split(".")[0]
                        aliases.setdefault(top, top)
            elif isinstance(node, ast.ImportFrom):
                base = self.resolve_relative(mod, node.level, node.module) if node.level else (node.module or "")
                for a in node.names:
                    if a.name == "*":
                        continue
                    aliases[a.asname or a.name] = f"{base}.{a.name}" if base else a.name
        return aliases

    # ------------------------------------------------------------------ #
    # Functions and calls

    def _collect_functions(self, mod: str, tree: ast.Module, pending: list) -> None:
        file = self.files[mod]

        def visit(body: list[ast.stmt], prefix: str, cls: str | None) -> None:
            for node in body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qual = f"{prefix}.{node.name}"
                    cached = any(dotted(d.func if isinstance(d, ast.Call) else d).split(".")[-1] in CACHE_DECORATORS
                                 for d in node.decorator_list)
                    info = FuncInfo(qual, mod, node.name, file, node.lineno,
                                    isinstance(node, ast.AsyncFunctionDef), cached)
                    self.funcs[qual] = info
                    pending.append((info, node, cls))
                    visit(node.body, f"{qual}.<locals>", None)
                elif isinstance(node, ast.ClassDef):
                    visit(node.body, f"{prefix}.{node.name}", f"{prefix}.{node.name}")

        visit(tree.body, mod, None)

    def _resolve(self, raw: str, mod: str, cls: str | None, local_defs: set[str], scope: str = "") -> tuple[str, bool, bool]:
        """Resolve a call target. Returns (target, internal, imported)."""
        if not raw:
            return "", False, False
        head, _, rest = raw.partition(".")
        if scope and not rest and f"{scope}.<locals>.{head}" in self.funcs:
            return f"{scope}.<locals>.{head}", True, False
        if head == "self" and cls and rest and "." not in rest:
            q = f"{cls}.{rest}"
            return q, q in self.funcs, False
        if head in local_defs and not rest:
            q = f"{mod}.{head}"
            return q, q in self.funcs, False
        if head in self.aliases.get(mod, {}):
            full = self.aliases[mod][head] + (f".{rest}" if rest else "")
            q = self.resolve_symbol(full)
            return (q, True, True) if q else (full, False, True)
        # A local variable, parameter or builtin: we cannot know what it is.
        return raw, False, False

    def _calls_in(self, fn: ast.FunctionDef | ast.AsyncFunctionDef, mod: str, cls: str | None, scope: str) -> list[CallSite]:
        local_defs = {n.name for n in self.trees[mod].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        sites: list[CallSite] = []

        def walk(node: ast.AST, loop: int | None, awaited: bool) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                    continue  # nested scopes are their own functions
                child_loop = loop
                if isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                    # the iterator runs once; the body runs per iteration
                    head = child.iter if not isinstance(child, ast.While) else child.test
                    walk_expr(head, loop, False)
                    # A retry loop repeats one call on purpose; that is not N+1.
                    retry = isinstance(getattr(child, "target", None), ast.Name) and bool(
                        _RETRY_NAME.match(child.target.id))  # type: ignore[union-attr]
                    for stmt in child.body + child.orelse:
                        walk_stmt(stmt, loop if retry else child.lineno)
                    continue
                if isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    child_loop = child.lineno
                if isinstance(child, ast.Await):
                    walk(child, child_loop, True)
                    continue
                if isinstance(child, ast.Call):
                    raw = dotted(child.func)
                    target, internal, imported = self._resolve(raw, mod, cls, local_defs, scope)
                    if raw:
                        sites.append(CallSite(child.lineno, raw, target, internal, child_loop, awaited, imported))
                walk(child, child_loop, False)

        def walk_stmt(stmt: ast.AST, loop: int | None) -> None:
            wrapper = ast.Module(body=[stmt], type_ignores=[])  # type: ignore[arg-type]
            walk(wrapper, loop, False)

        def walk_expr(expr: ast.AST, loop: int | None, awaited: bool) -> None:
            wrapper = ast.Expr(value=expr)
            walk(wrapper, loop, awaited)

        for stmt in fn.body:
            walk_stmt(stmt, None)
        return sites

    # ------------------------------------------------------------------ #
    # Queries

    def is_external(self, target: str) -> bool:
        """True unless the target lives in this repository (e.g. scanning httpx itself)."""
        parts = target.split(".")
        return not any(self.lookup(".".join(parts[:i])) for i in range(1, len(parts)))

    def is_blocking(self, target: str) -> bool:
        return (target in BLOCKING_EXACT or target.startswith(BLOCKING_PREFIXES)) and self.is_external(target)

    def is_round_trip(self, site: CallSite) -> bool:
        if site.internal:
            return False
        attr = site.raw.split(".")[-1]
        if "." in site.raw and attr in ROUND_TRIP_ATTRS:
            return True
        return site.imported and site.target.startswith(ROUND_TRIP_PREFIXES) and self.is_external(site.target)

    def blocking_path(self, qual: str, stack: frozenset[str] = frozenset()) -> list[ChainLink] | None:
        """Shortest-first DFS for a call chain from ``qual`` to a blocking primitive."""
        if qual in self._blocking_memo:
            return self._blocking_memo[qual]
        if qual in stack:
            return None
        info = self.funcs[qual]
        best: list[ChainLink] | None = None
        for site in info.calls:
            if site.imported and not site.internal and self.is_blocking(site.target):
                best = [ChainLink(qual, site.line, site.target, info.file)]
                break
        if best is None:
            for site in info.calls:
                if site.internal and site.target in self.funcs:
                    sub = self.blocking_path(site.target, stack | {qual})
                    if sub is not None:
                        best = [ChainLink(qual, site.line, site.target, info.file)] + sub
                        break
        if not stack:
            self._blocking_memo[qual] = best
        return best

    def round_trip_path(self, qual: str, stack: frozenset[str] = frozenset()) -> list[ChainLink] | None:
        if qual in self._roundtrip_memo:
            return self._roundtrip_memo[qual]
        if qual in stack:
            return None
        info = self.funcs[qual]
        best: list[ChainLink] | None = None
        for site in info.calls:
            if self.is_round_trip(site):
                best = [ChainLink(qual, site.line, site.target if not site.internal else site.raw, info.file)]
                break
        if best is None:
            for site in info.calls:
                if site.internal and site.target in self.funcs:
                    sub = self.round_trip_path(site.target, stack | {qual})
                    if sub is not None:
                        best = [ChainLink(qual, site.line, site.target, info.file)] + sub
                        break
        if not stack:
            self._roundtrip_memo[qual] = best
        return best

    def blocking_chains(self) -> list[BlockingChain]:
        out = []
        for info in self.funcs.values():
            if info.is_async:
                path = self.blocking_path(info.qual)
                if path:
                    out.append(BlockingChain(info, path))
        return out

    def loop_round_trips(self) -> list[LoopRoundTrip]:
        out: list[LoopRoundTrip] = []
        for info in self.funcs.values():
            seen_loops: set[int] = set()
            for site in info.calls:
                if site.in_loop is None or site.in_loop in seen_loops:
                    continue
                links: list[ChainLink] | None = None
                cached = False
                if self.is_round_trip(site):
                    links = [ChainLink(info.qual, site.line, site.raw, info.file)]
                elif site.internal and site.target in self.funcs:
                    sub = self.round_trip_path(site.target)
                    if sub is not None:
                        links = [ChainLink(info.qual, site.line, site.target, info.file)] + sub
                        cached = self.funcs[site.target].cached
                if links:
                    seen_loops.add(site.in_loop)
                    out.append(LoopRoundTrip(info, site.in_loop, site, links, cached))
        return out
