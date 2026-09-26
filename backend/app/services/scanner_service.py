"""Static AST code scanner — maps Python anti-patterns to CodeMusume attributes."""
from __future__ import annotations

import ast
import os
from typing import Any

from pydantic import BaseModel

from app.models.schemas import AttributeScores, AttributeType

# ---------------------------------------------------------------------------
# Skip directories when walking a repository
# ---------------------------------------------------------------------------
_SKIP_DIRS: frozenset[str] = frozenset({
    ".git", "venv", ".venv", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", "dist", "build",
})

# ---------------------------------------------------------------------------
# Penalty / bonus constants
# ---------------------------------------------------------------------------
_PENALTY_SPEED_BLOCKING = 40   # time.sleep / sync requests inside async def
_PENALTY_SPEED_COMPLEX = 30    # cyclomatic complexity > 10
_PENALTY_STAMINA_UNCLOSED = 50 # open() not in with-block
_PENALTY_STAMINA_DB = 40       # DB cursor/connection not in with-block
_PENALTY_POWER_SERIAL = 30     # sequential processing (loop with single call per iter)
_PENALTY_GUTS_BARE_EXCEPT = 30 # bare except / swallowed exception
_PENALTY_GUTS_NO_TIMEOUT = 25  # HTTP call without timeout arg
_PENALTY_WISDOM_NO_RETURN = 20 # missing return type annotation
_PENALTY_WISDOM_LONG_FUNC = 35 # function > 80 lines

_BONUS_TYPE_ANNOTATED = 30     # per annotated function (capped internally)
_BONUS_TEST_FILE = 50          # per test file detected in the repo


# ---------------------------------------------------------------------------
# DetectedSmell model
# ---------------------------------------------------------------------------
class DetectedSmell(BaseModel):
    file_path: str
    line_number: int
    attribute: AttributeType
    rule_id: str
    description: str
    tachyon_critique: str
    suggested_fix: str
    code_snippet: str


# ---------------------------------------------------------------------------
# Internal AST helpers
# ---------------------------------------------------------------------------

def _cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return a simple cyclomatic-complexity estimate for a function node.

    Counts decision points: if/elif, for, while, except handlers, with, assert,
    boolean operators (and/or), comprehensions (if clauses), ternary (IfExp).
    Starts at 1 (the function itself).
    """
    count = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.AsyncFor,
                               ast.ExceptHandler, ast.With, ast.AsyncWith,
                               ast.Assert, ast.IfExp)):
            count += 1
        elif isinstance(child, ast.BoolOp):
            # Each additional value in a BoolOp is one extra branch
            count += len(child.values) - 1
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            for gen in child.generators:
                count += len(gen.ifs)
    return count


def _func_line_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return the number of source lines spanned by this function."""
    return node.end_lineno - node.lineno + 1  # type: ignore[operator]


def _is_inside_with(node: ast.Call, parents: list[ast.AST]) -> bool:
    """Return True if any ancestor in *parents* is a With/AsyncWith context manager
    that directly wraps the call (i.e., the call appears in the *items* of the with)."""
    for p in parents:
        if isinstance(p, (ast.With, ast.AsyncWith)):
            return True
    return False


def _call_name(node: ast.Call) -> str:
    """Best-effort dotted name of a Call node (e.g. 'time.sleep', 'requests.get')."""
    func = node.func
    if isinstance(func, ast.Attribute):
        value = func.value
        if isinstance(value, ast.Name):
            return f"{value.id}.{func.attr}"
        return f"?.{func.attr}"
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _has_keyword(call: ast.Call, kw: str) -> bool:
    """Return True if *call* has a keyword argument named *kw*."""
    return any(k.arg == kw for k in call.keywords)


def _snippet(lines: list[str], lineno: int, context: int = 1) -> str:
    """Return *context* lines around *lineno* (1-based), joined as a string."""
    start = max(0, lineno - 1 - context)
    end = min(len(lines), lineno + context)
    return "\n".join(lines[start:end]).strip()


# ---------------------------------------------------------------------------
# Per-rule detectors  (each receives the full AST + source lines + file path)
# ---------------------------------------------------------------------------

# HTTP call targets that should carry a timeout
_HTTP_CALL_PREFIXES = (
    "requests.get", "requests.post", "requests.put", "requests.patch",
    "requests.delete", "requests.request", "requests.head", "requests.options",
    "httpx.get", "httpx.post", "httpx.put", "httpx.patch",
    "httpx.delete", "httpx.request",
    "aiohttp.ClientSession",
    "urllib.request.urlopen",
)

# DB acquisition patterns (attribute names that imply cursor/connection)
_DB_ACQUIRE_ATTRS = frozenset({
    "cursor", "connect", "connection", "acquire", "get_connection",
    "create_connection", "execute",
})


class _ParentTracker(ast.NodeVisitor):
    """Visitor that keeps a stack of parent nodes for context-sensitive checks."""

    def __init__(self, file_path: str, source_lines: list[str]) -> None:
        self.file_path = file_path
        self.lines = source_lines
        self._parents: list[ast.AST] = []
        self.smells: list[DetectedSmell] = []

        # Tracking state
        self._in_async_func: bool = False
        self._async_func_stack: list[bool] = []

    # ------------------------------------------------------------------ #
    #  Visitor infrastructure
    # ------------------------------------------------------------------ #

    def _visit_children(self, node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            self._parents.append(node)
            self.visit(child)
            self._parents.pop()

    def generic_visit(self, node: ast.AST) -> None:
        self._visit_children(node)

    # ------------------------------------------------------------------ #
    #  Function-level checks (Speed: complexity, Wisdom: annotations+length)
    # ------------------------------------------------------------------ #

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # Speed: cyclomatic complexity > 10
        cc = _cyclomatic_complexity(node)
        if cc > 10:
            self.smells.append(DetectedSmell(
                file_path=self.file_path,
                line_number=node.lineno,
                attribute=AttributeType.SPEED,
                rule_id="SPEED-002",
                description=f"Function '{node.name}' has cyclomatic complexity {cc} (> 10).",
                tachyon_critique=(
                    "Ufufu… a function with that many branches is like a race horse "
                    "tripping over its own hooves. Fascinating in the worst possible way."
                ),
                suggested_fix="Break the function into smaller, single-responsibility units.",
                code_snippet=_snippet(self.lines, node.lineno),
            ))

        # Wisdom: missing return type annotation
        if node.returns is None and node.name != "__init__":
            self.smells.append(DetectedSmell(
                file_path=self.file_path,
                line_number=node.lineno,
                attribute=AttributeType.WISDOM,
                rule_id="WISDOM-001",
                description=f"Function '{node.name}' is missing a return type annotation.",
                tachyon_critique=(
                    "How wonderfully reckless — leaving your function's return type "
                    "as a mystery for future readers. I do enjoy a puzzle, but not in "
                    "production code."
                ),
                suggested_fix="Add a return type annotation, e.g. `def foo() -> None:`.",
                code_snippet=_snippet(self.lines, node.lineno),
            ))

        # Wisdom: function longer than 80 lines
        line_count = _func_line_count(node)
        if line_count > 80:
            self.smells.append(DetectedSmell(
                file_path=self.file_path,
                line_number=node.lineno,
                attribute=AttributeType.WISDOM,
                rule_id="WISDOM-002",
                description=(
                    f"Function '{node.name}' spans {line_count} lines "
                    "(> 80). Consider decomposing it."
                ),
                tachyon_critique=(
                    "A function of that length? Even my most elaborate experiments "
                    "fit on a single page of notes. Decompose it — for science."
                ),
                suggested_fix="Extract logical sub-steps into helper functions.",
                code_snippet=_snippet(self.lines, node.lineno),
            ))

        # Walk body with async context updated
        self._async_func_stack.append(self._in_async_func)
        self._in_async_func = is_async
        self._visit_children(node)
        self._in_async_func = self._async_func_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)

    # ------------------------------------------------------------------ #
    #  Call-level checks
    # ------------------------------------------------------------------ #

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)

        # ---- Speed: blocking calls inside async def ----
        if self._in_async_func:
            if name == "time.sleep":
                self.smells.append(DetectedSmell(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    attribute=AttributeType.SPEED,
                    rule_id="SPEED-001",
                    description="`time.sleep()` called inside an async function — blocks the event loop.",
                    tachyon_critique=(
                        "Ufufu… `time.sleep` inside an `async def`? "
                        "You have just frozen the entire event loop. "
                        "Truly a breathtaking act of self-sabotage."
                    ),
                    suggested_fix="Replace `time.sleep(n)` with `await asyncio.sleep(n)`.",
                    code_snippet=_snippet(self.lines, node.lineno),
                ))
            elif name.startswith("requests."):
                self.smells.append(DetectedSmell(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    attribute=AttributeType.SPEED,
                    rule_id="SPEED-001",
                    description=f"Synchronous `{name}()` call inside an async function — blocks the event loop.",
                    tachyon_critique=(
                        "A synchronous `requests` call lurking inside `async def` — "
                        "how delightfully catastrophic. Every coroutine is now waiting "
                        "for *your* network round-trip."
                    ),
                    suggested_fix="Switch to `httpx.AsyncClient` or `aiohttp` for async HTTP calls.",
                    code_snippet=_snippet(self.lines, node.lineno),
                ))

        # ---- Stamina: open() not wrapped in a with ----
        if name == "open":
            in_with = any(isinstance(p, (ast.With, ast.AsyncWith)) for p in self._parents)
            if not in_with:
                self.smells.append(DetectedSmell(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    attribute=AttributeType.STAMINA,
                    rule_id="STAMINA-001",
                    description="`open()` called without a `with` context manager — file handle may leak.",
                    tachyon_critique=(
                        "An `open()` without a `with` block? Leaving file handles "
                        "dangling in the wind. Elegance demands you close what you open."
                    ),
                    suggested_fix="Use `with open(...) as f:` to ensure the file is always closed.",
                    code_snippet=_snippet(self.lines, node.lineno),
                ))

        # ---- Stamina: DB cursor/connection without context manager ----
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _DB_ACQUIRE_ATTRS:
            in_with = any(isinstance(p, (ast.With, ast.AsyncWith)) for p in self._parents)
            if not in_with:
                self.smells.append(DetectedSmell(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    attribute=AttributeType.STAMINA,
                    rule_id="STAMINA-002",
                    description=(
                        f"Database `.{func.attr}()` call not enclosed in a `with` block — "
                        "connection/cursor may not be released."
                    ),
                    tachyon_critique=(
                        "A database resource acquired without a context manager — "
                        "how unscientific. Resource leaks accumulate like failed hypotheses."
                    ),
                    suggested_fix="Wrap with `with conn.cursor() as cur:` or use an async context manager.",
                    code_snippet=_snippet(self.lines, node.lineno),
                ))

        # ---- Guts: HTTP calls without timeout ----
        for prefix in _HTTP_CALL_PREFIXES:
            if name == prefix or name.startswith(prefix + "."):
                if not _has_keyword(node, "timeout"):
                    self.smells.append(DetectedSmell(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        attribute=AttributeType.GUTS,
                        rule_id="GUTS-002",
                        description=f"`{name}()` called without an explicit `timeout` argument.",
                        tachyon_critique=(
                            "An HTTP call with no timeout? Courageous — or simply reckless. "
                            "Your service will hang indefinitely waiting for a response "
                            "that may never arrive."
                        ),
                        suggested_fix=f"Add `timeout=` to the call, e.g. `{name}(url, timeout=10)`.",
                        code_snippet=_snippet(self.lines, node.lineno),
                    ))
                break

        self._visit_children(node)

    # ------------------------------------------------------------------ #
    #  Exception handler checks (Guts)
    # ------------------------------------------------------------------ #

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        is_bare = node.type is None
        is_broad_exception = (
            isinstance(node.type, ast.Name) and node.type.id == "Exception"
        )

        if is_bare or is_broad_exception:
            # Check if the body is just a pass / ... / empty
            body = node.body
            is_swallowed = all(
                isinstance(stmt, (ast.Pass, ast.Expr)) and (
                    isinstance(stmt, ast.Pass) or (
                        isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)
                        and stmt.value.value is ...
                    )
                )
                for stmt in body
            )
            if is_swallowed:
                kind = "bare `except:`" if is_bare else "`except Exception: pass`"
                self.smells.append(DetectedSmell(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    attribute=AttributeType.GUTS,
                    rule_id="GUTS-001",
                    description=f"Swallowed exception: {kind} silently discards errors.",
                    tachyon_critique=(
                        "Swallowing an exception and saying nothing — the "
                        "scientific equivalent of sweeping data under the rug. "
                        "Even a failed experiment deserves to be *logged*."
                    ),
                    suggested_fix=(
                        "Catch only the specific exception you expect and at minimum "
                        "log it: `except ValueError as e: logger.warning(e)`."
                    ),
                    code_snippet=_snippet(self.lines, node.lineno),
                ))

        self._visit_children(node)

    # ------------------------------------------------------------------ #
    #  Loop-level checks (Power: sequential processing)
    # ------------------------------------------------------------------ #

    def visit_For(self, node: ast.For) -> None:
        self._check_loop_sequential(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._check_loop_sequential(node)

    def _check_loop_sequential(self, node: ast.For | ast.AsyncFor) -> None:
        """Flag loops where every body statement is a single blocking call (sequential pattern)."""
        call_count = 0
        for stmt in node.body:
            # Direct call statement: foo(x)
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call_count += 1
            # Assignment with a call on the right: result = foo(x)
            elif isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                call_count += 1
            elif isinstance(stmt, (ast.AugAssign, ast.AnnAssign)):
                if isinstance(getattr(stmt, "value", None), ast.Call):
                    call_count += 1

        # If every non-trivial body statement is a bare call → sequential pattern
        non_trivial = [
            s for s in node.body
            if not isinstance(s, (ast.Pass, ast.Continue, ast.Break))
        ]
        if non_trivial and call_count == len(non_trivial) and call_count >= 1:
            self.smells.append(DetectedSmell(
                file_path=self.file_path,
                line_number=node.lineno,
                attribute=AttributeType.POWER,
                rule_id="POWER-001",
                description=(
                    "Sequential item processing inside a loop — "
                    "consider batching or concurrent execution."
                ),
                tachyon_critique=(
                    "Processing items one by one in a loop — how pedestrian. "
                    "Have you heard of `asyncio.gather`, thread pools, or bulk APIs? "
                    "Power comes from parallelism."
                ),
                suggested_fix=(
                    "Use `asyncio.gather()`, `concurrent.futures`, or a batch API "
                    "to process items concurrently."
                ),
                code_snippet=_snippet(self.lines, node.lineno),
            ))

        self._visit_children(node)


# ---------------------------------------------------------------------------
# RepoScanner
# ---------------------------------------------------------------------------

class RepoScanner:
    """Walks a Python repository and maps code smells to CodeMusume attributes."""

    def __init__(self, target_path: str) -> None:
        self.target_path = target_path

    # ------------------------------------------------------------------ #

    def scan_file(self, file_path: str, content: str) -> list[DetectedSmell]:
        """Parse *content* via AST and return all detected smells."""
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return []

        lines = content.splitlines()
        visitor = _ParentTracker(file_path=file_path, source_lines=lines)
        visitor.visit(tree)
        return visitor.smells

    # ------------------------------------------------------------------ #

    def scan_repository(self) -> tuple[AttributeScores, list[DetectedSmell]]:
        """Walk *target_path*, aggregate smells, and compute attribute scores."""
        all_smells: list[DetectedSmell] = []
        has_test_files = False
        annotated_functions = 0
        total_functions = 0

        for dirpath, dirnames, filenames in os.walk(self.target_path):
            # Prune ignored directories in-place (affects os.walk recursion)
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

            for filename in filenames:
                if not filename.endswith(".py"):
                    continue

                full_path = os.path.join(dirpath, filename)

                # Detect test files for bonus
                if filename.startswith("test_") or filename.endswith("_test.py"):
                    has_test_files = True

                try:
                    content = full_path
                    with open(full_path, encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                except OSError:
                    continue

                # Count annotated functions for Wisdom bonus
                try:
                    tree = ast.parse(content, filename=full_path)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if node.name != "__init__":
                                total_functions += 1
                                if node.returns is not None:
                                    annotated_functions += 1
                except SyntaxError:
                    pass

                smells = self.scan_file(full_path, content)
                all_smells.extend(smells)

        # ---- Score calculation ----
        BASELINE = 400

        speed = BASELINE
        stamina = BASELINE
        power = BASELINE
        guts = BASELINE
        wisdom = BASELINE

        for smell in all_smells:
            attr = smell.attribute
            rule = smell.rule_id
            if attr == AttributeType.SPEED:
                if rule == "SPEED-001":
                    speed -= _PENALTY_SPEED_BLOCKING
                elif rule == "SPEED-002":
                    speed -= _PENALTY_SPEED_COMPLEX
            elif attr == AttributeType.STAMINA:
                if rule == "STAMINA-001":
                    stamina -= _PENALTY_STAMINA_UNCLOSED
                elif rule == "STAMINA-002":
                    stamina -= _PENALTY_STAMINA_DB
            elif attr == AttributeType.POWER:
                power -= _PENALTY_POWER_SERIAL
            elif attr == AttributeType.GUTS:
                if rule == "GUTS-001":
                    guts -= _PENALTY_GUTS_BARE_EXCEPT
                elif rule == "GUTS-002":
                    guts -= _PENALTY_GUTS_NO_TIMEOUT
            elif attr == AttributeType.WISDOM:
                if rule == "WISDOM-001":
                    wisdom -= _PENALTY_WISDOM_NO_RETURN
                elif rule == "WISDOM-002":
                    wisdom -= _PENALTY_WISDOM_LONG_FUNC

        # Bonuses
        if has_test_files:
            guts += _BONUS_TEST_FILE
            wisdom += _BONUS_TEST_FILE

        if total_functions > 0:
            annotation_ratio = annotated_functions / total_functions
            wisdom += int(annotation_ratio * _BONUS_TYPE_ANNOTATED * total_functions)

        # Clamp
        def _clamp(v: int) -> int:
            return max(100, min(1200, v))

        scores = AttributeScores(
            speed=_clamp(speed),
            stamina=_clamp(stamina),
            power=_clamp(power),
            guts=_clamp(guts),
            wisdom=_clamp(wisdom),
        )
        return scores, all_smells
