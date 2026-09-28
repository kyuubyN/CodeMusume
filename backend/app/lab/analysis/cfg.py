"""Statement-level control-flow graphs with exceptional edges, built from ``ast``.

Every statement becomes a node. Compound statements (``if``, ``for``,
``while``, ``with``) get a *header* node that stands for evaluating their test,
iterator or context expressions. Two synthetic sinks close the graph:
``EXIT`` (normal return) and ``RAISE`` (an exception escapes the function).

Edges come in two kinds:

* ``succ``  — normal control flow;
* ``exc``   — "this statement raised": to the innermost ``except`` dispatch,
  through a copy of the enclosing ``finally`` block, or out to ``RAISE``.

``finally`` bodies are built once per way of leaving the ``try`` (fall-through,
exception, ``return``), so a dataflow analysis over the graph stays
path-precise without special cases for ``finally``.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

ENTRY, EXIT, RAISE = 0, 1, 2


@dataclass
class Node:
    id: int
    kind: str                      # "entry" | "exit" | "raise" | "stmt" | "header" | "dispatch" | "handler"
    stmt: ast.AST | None = None
    succ: set[int] = field(default_factory=set)
    exc: set[int] = field(default_factory=set)

    @property
    def line(self) -> int:
        return getattr(self.stmt, "lineno", 0)


@dataclass
class _Loop:
    brk: int
    cont: int


class CFG:
    """Control-flow graph of one function body."""

    def __init__(self, func: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.func = func
        self.nodes: dict[int, Node] = {}
        self._new("entry")
        self._new("exit")
        self._new("raise")
        self._exc: list[int] = [RAISE]       # where an exception goes right now
        self._ret: list[int] = [EXIT]        # where `return` goes right now
        self._loops: list[_Loop] = []
        first = self._seq(func.body, EXIT)
        self.nodes[ENTRY].succ.add(first)

    # ------------------------------------------------------------------ #

    def _new(self, kind: str, stmt: ast.AST | None = None) -> Node:
        node = Node(id=len(self.nodes), kind=kind, stmt=stmt)
        self.nodes[node.id] = node
        return node

    def _seq(self, stmts: list[ast.stmt], nxt: int) -> int:
        """Build a statement list backwards; return the id of its first node."""
        for s in reversed(stmts):
            nxt = self._stmt(s, nxt)
        return nxt

    def _raises_to(self, node: Node, s: ast.AST) -> None:
        if may_raise(s):
            node.exc.add(self._exc[-1])

    def _stmt(self, s: ast.stmt, nxt: int) -> int:
        if isinstance(s, ast.If):
            n = self._new("header", s)
            n.succ.add(self._seq(s.body, nxt))
            n.succ.add(self._seq(s.orelse, nxt) if s.orelse else nxt)
            self._raises_to(n, s.test)
            return n.id

        if isinstance(s, (ast.For, ast.AsyncFor, ast.While)):
            n = self._new("header", s)
            after = self._seq(s.orelse, nxt) if s.orelse else nxt
            self._loops.append(_Loop(brk=nxt, cont=n.id))
            body = self._seq(s.body, n.id)
            self._loops.pop()
            n.succ.update({body, after})
            self._raises_to(n, s.test if isinstance(s, ast.While) else s.iter)
            return n.id

        if isinstance(s, (ast.With, ast.AsyncWith)):
            n = self._new("header", s)
            n.succ.add(self._seq(s.body, nxt))
            n.exc.add(self._exc[-1])
            return n.id

        if isinstance(s, ast.Try) or type(s).__name__ == "TryStar":
            return self._try(s, nxt)  # type: ignore[arg-type]

        if isinstance(s, ast.Match):
            n = self._new("header", s)
            for case in s.cases:
                n.succ.add(self._seq(case.body, nxt))
            n.succ.add(nxt)
            self._raises_to(n, s.subject)
            return n.id

        n = self._new("stmt", s)
        if isinstance(s, ast.Return):
            n.succ.add(self._ret[-1])
            if s.value is not None:
                self._raises_to(n, s.value)
        elif isinstance(s, ast.Raise):
            n.exc.add(self._exc[-1])
        elif isinstance(s, ast.Break) and self._loops:
            n.succ.add(self._loops[-1].brk)
        elif isinstance(s, ast.Continue) and self._loops:
            n.succ.add(self._loops[-1].cont)
        else:
            n.succ.add(nxt)
            self._raises_to(n, s)
        return n.id

    def _try(self, s: ast.Try, nxt: int) -> int:
        outer_exc = self._exc[-1]
        outer_ret = self._ret[-1]
        if s.finalbody:
            # One copy of `finally` per way out of the try statement.
            fin_normal = self._seq(s.finalbody, nxt)
            fin_exc = self._seq(s.finalbody, outer_exc)
            fin_ret = self._seq(s.finalbody, outer_ret)
        else:
            fin_normal, fin_exc, fin_ret = nxt, outer_exc, outer_ret

        # Handlers run with exceptions going through `finally`.
        self._exc.append(fin_exc)
        self._ret.append(fin_ret)
        dispatch = self._new("dispatch", s)
        catch_all = False
        for h in s.handlers:
            hn = self._new("handler", h)
            hn.succ.add(self._seq(h.body, fin_normal))
            dispatch.succ.add(hn.id)
            if h.type is None or (isinstance(h.type, ast.Name) and h.type.id in ("Exception", "BaseException")):
                catch_all = True
        if not catch_all:
            dispatch.succ.add(fin_exc)
        orelse = self._seq(s.orelse, fin_normal) if s.orelse else fin_normal
        self._exc.pop()

        # The body raises into the handler dispatch (or straight to finally).
        self._exc.append(dispatch.id if s.handlers else fin_exc)
        body = self._seq(s.body, orelse)
        self._exc.pop()
        self._ret.pop()
        return body

    # ------------------------------------------------------------------ #

    def predecessors(self) -> dict[int, set[int]]:
        preds: dict[int, set[int]] = {i: set() for i in self.nodes}
        for n in self.nodes.values():
            for t in n.succ | n.exc:
                preds[t].add(n.id)
        return preds

    def reachable(self) -> set[int]:
        seen, stack = {ENTRY}, [ENTRY]
        while stack:
            n = self.nodes[stack.pop()]
            for t in n.succ | n.exc:
                if t not in seen:
                    seen.add(t)
                    stack.append(t)
        return seen


def header_exprs(node: Node) -> list[ast.AST]:
    """The expressions a node actually evaluates (headers only evaluate their test)."""
    s = node.stmt
    if s is None or node.kind in ("dispatch", "handler"):
        return []
    if node.kind == "header":
        if isinstance(s, ast.If | ast.While):
            return [s.test]
        if isinstance(s, (ast.For, ast.AsyncFor)):
            return [s.iter, s.target]
        if isinstance(s, (ast.With, ast.AsyncWith)):
            return [i.context_expr for i in s.items]
        if isinstance(s, ast.Match):
            return [s.subject]
        return []
    return [s]


def may_raise(tree: ast.AST) -> bool:
    """Conservative: anything that calls, indexes, awaits, asserts or raises can raise."""
    for n in ast.walk(tree):
        if isinstance(n, (ast.Call, ast.Subscript, ast.Await, ast.Raise, ast.Assert)):
            return True
    return False


def functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
