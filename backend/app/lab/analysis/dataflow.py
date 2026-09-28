"""Resource-lifetime analysis: a forward "may be open" dataflow over the CFG.

A resource is *generated* when a name is bound to an opener call
(``f = open(p)``, ``conn = sqlite3.connect(db)``, ``s = socket.socket()``) and
*killed* when it is closed (``f.close()``, ``with f:``) or ownership escapes
the function (returned, yielded, stored on an object or in a container).

Normal edges carry the state after the statement; exceptional edges carry the
state *before* it (a statement that raised did not complete its effect).
Any resource still open when control reaches ``EXIT`` leaks on a normal path;
any resource open at ``RAISE`` leaks when an exception escapes. For the
latter, a backward search from ``RAISE`` names the statements whose exception
carries the open handle out of the function.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

from app.lab.analysis.cfg import CFG, ENTRY, EXIT, RAISE, Node, functions, header_exprs

_OPENER_NAMES = {"open", "io.open", "socket.socket", "socket.create_connection", "tempfile.TemporaryFile"}
_OPENER_ATTRS = {"connect", "cursor", "urlopen", "open"}
_CLOSERS = {"close", "release", "shutdown", "__exit__"}
_STORERS = {"append", "add", "put", "extend", "insert", "setdefault", "register"}

Res = tuple[str, int]  # (variable name, line it was opened on)


@dataclass
class ResourceLeak:
    file: str
    function: str
    name: str
    open_line: int
    kind: str                                  # "exception_path" | "normal_path"
    raise_lines: list[int] = field(default_factory=list)
    close_lines: list[int] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.kind == "normal_path":
            return f"`{self.name}` opened on line {self.open_line} is never closed on some normal path"
        where = ", ".join(str(n) for n in self.raise_lines) or "a raising statement"
        return (
            f"`{self.name}` opened on line {self.open_line} leaks when line {where} raises: "
            "the exception skips the close()"
        )


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        inner = _dotted(node.value)
        return f"{inner}.{node.attr}" if inner else node.attr
    return ""


def _is_opener(call: ast.AST) -> bool:
    if not isinstance(call, ast.Call):
        return False
    name = _dotted(call.func)
    if name in _OPENER_NAMES:
        return True
    return isinstance(call.func, ast.Attribute) and call.func.attr in _OPENER_ATTRS


def _escaping(expr: ast.AST) -> set[str]:
    """Names whose *object* the expression hands on (not names merely used by a call)."""
    if isinstance(expr, ast.Name):
        return {expr.id}
    if isinstance(expr, (ast.Tuple, ast.List, ast.Set)):
        return set().union(*(_escaping(e) for e in expr.elts)) if expr.elts else set()
    if isinstance(expr, ast.Dict):
        return set().union(*(_escaping(v) for v in expr.values if v is not None)) if expr.values else set()
    if isinstance(expr, ast.Starred):
        return _escaping(expr.value)
    if isinstance(expr, ast.Call):
        name = _dotted(expr.func).split(".")[-1]
        if name[:1].isupper():  # Wrapper(f): the new object now owns the handle
            return set().union(*(_escaping(a) for a in expr.args)) if expr.args else set()
    return set()


def _gen(node: Node) -> str | None:
    s = node.stmt
    if node.kind != "stmt":
        return None
    if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name):
        return s.targets[0].id if _is_opener(s.value) else None
    if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name) and s.value is not None:
        return s.target.id if _is_opener(s.value) else None
    return None


def _killed(node: Node, open_names: set[str]) -> tuple[set[str], set[str]]:
    """Names this node closes, and names whose ownership escapes."""
    closed: set[str] = set()
    escaped: set[str] = set()
    s = node.stmt
    for expr in header_exprs(node):
        for n in ast.walk(expr):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                target = n.func.value
                if isinstance(target, ast.Name) and target.id in open_names:
                    if n.func.attr in _CLOSERS:
                        closed.add(target.id)
                if n.func.attr in _STORERS:
                    for arg in n.args:
                        escaped |= _escaping(arg) & open_names
    if node.kind == "header" and isinstance(s, (ast.With, ast.AsyncWith)):
        for item in s.items:
            if isinstance(item.context_expr, ast.Name) and item.context_expr.id in open_names:
                closed.add(item.context_expr.id)
    if node.kind == "stmt":
        if isinstance(s, ast.Return) and s.value is not None:
            escaped |= _escaping(s.value) & open_names
        if isinstance(s, ast.Expr) and isinstance(s.value, (ast.Yield, ast.YieldFrom)) and s.value.value is not None:
            escaped |= _escaping(s.value.value) & open_names
        if isinstance(s, ast.Assign):
            value_names = _escaping(s.value) & open_names
            for t in s.targets:
                if isinstance(t, (ast.Attribute, ast.Subscript)):
                    escaped |= value_names
                elif isinstance(t, ast.Name) and isinstance(s.value, ast.Name):
                    escaped |= value_names  # aliased: ownership moves to the new name
    return closed, escaped


class _Flow:
    def __init__(self, cfg: CFG) -> None:
        self.cfg = cfg
        self.IN: dict[int, frozenset[Res]] = {i: frozenset() for i in cfg.nodes}
        self.OUT: dict[int, frozenset[Res]] = {}
        self.OUT_EXC: dict[int, frozenset[Res]] = {}
        self.closes: dict[str, set[int]] = {}
        self._solve()

    def _transfer(self, node: Node, state: frozenset[Res]) -> frozenset[Res]:
        names = {r[0] for r in state}
        closed, escaped = _killed(node, names)
        for c in closed:
            self.closes.setdefault(c, set()).add(node.line)
        gone = closed | escaped
        out = {r for r in state if r[0] not in gone}
        g = _gen(node)
        if g is not None:
            out = {r for r in out if r[0] != g}   # rebinding drops the old tracking
            out.add((g, node.line))
        return frozenset(out)

    def _solve(self) -> None:
        cfg = self.cfg
        work = [ENTRY]
        seen: set[int] = set()
        while work:
            nid = work.pop()
            node = cfg.nodes[nid]
            out = self._transfer(node, self.IN[nid])
            # A statement that raised did not complete, except that a close()
            # which raised still counts as handled.
            closed, _ = _killed(node, {r[0] for r in self.IN[nid]})
            out_exc = frozenset(r for r in self.IN[nid] if r[0] not in closed)
            changed = nid not in seen or self.OUT.get(nid) != out or self.OUT_EXC.get(nid) != out_exc
            seen.add(nid)
            self.OUT[nid], self.OUT_EXC[nid] = out, out_exc
            if not changed:
                continue
            for t in node.succ:
                merged = self.IN[t] | out
                if merged != self.IN[t] or t not in seen:
                    self.IN[t] = merged
                    work.append(t)
            for t in node.exc:
                merged = self.IN[t] | out_exc
                if merged != self.IN[t] or t not in seen:
                    self.IN[t] = merged
                    work.append(t)

    def raise_points(self, res: Res) -> list[int]:
        """Statements whose exception carries ``res`` (still open) out of the function."""
        cfg = self.cfg
        preds: dict[int, list[tuple[int, str]]] = {i: [] for i in cfg.nodes}
        for n in cfg.nodes.values():
            for t in n.succ:
                preds[t].append((n.id, "n"))
            for t in n.exc:
                preds[t].append((n.id, "e"))
        reach = {RAISE}
        stack = [RAISE]
        while stack:
            b = stack.pop()
            for p, kind in preds[b]:
                state = self.OUT_EXC.get(p, frozenset()) if kind == "e" else self.OUT.get(p, frozenset())
                if res in state and p not in reach:
                    reach.add(p)
                    stack.append(p)
        lines = set()
        for nid in reach:
            n = cfg.nodes[nid]
            if n.kind not in ("stmt", "header") or n.line == res[1]:
                continue
            if res in self.OUT_EXC.get(nid, frozenset()) and any(t in reach for t in n.exc):
                closed, _ = _killed(n, {res[0]})
                if not closed:
                    lines.add(n.line)
        return sorted(lines)


def analyze_function(func: ast.FunctionDef | ast.AsyncFunctionDef, file: str) -> list[ResourceLeak]:
    cfg = CFG(func)
    flow = _Flow(cfg)
    leaks: list[ResourceLeak] = []
    at_exit = flow.IN[EXIT]
    at_raise = flow.IN[RAISE]
    for res in sorted(at_exit | at_raise, key=lambda r: r[1]):
        name, line = res
        close_lines = sorted(flow.closes.get(name, set()))
        if res in at_exit:
            leaks.append(ResourceLeak(file, func.name, name, line, "normal_path", [], close_lines))
        else:
            leaks.append(ResourceLeak(file, func.name, name, line, "exception_path", flow.raise_points(res), close_lines))
    return leaks


def analyze_source(source: str, file: str = "<string>") -> list[ResourceLeak]:
    tree = ast.parse(source)
    out: list[ResourceLeak] = []
    for fn in functions(tree):
        out.extend(analyze_function(fn, file))
    return out
