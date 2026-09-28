"""Runtime sensors used inside the probe process.

* ``fd_count``      — open file descriptors, read from ``/proc/self/fd``
                      (falls back to tracking file objects returned by ``open``).
* ``AuditCounter``  — ``sys.addaudithook`` (PEP 578): counts ``open`` and
                      ``socket.connect`` events raised by the interpreter itself.
* ``CallCounter``   — ``sys.monitoring`` (PEP 669): counts calls into the
                      trainee's own functions with near-zero overhead.
* ``LoopLagSentinel`` — a heartbeat coroutine that measures how late the event
                      loop wakes it up; lag means something blocked the loop.
"""
from __future__ import annotations

import asyncio
import builtins
import os
import sys
import time
import weakref
from collections import Counter

_PROC_FD = "/proc/self/fd"
_tracked: "weakref.WeakSet" = weakref.WeakSet()
_real_open = builtins.open


def _tracking_open(*args, **kwargs):  # pragma: no cover - only without /proc
    f = _real_open(*args, **kwargs)
    try:
        _tracked.add(f)
    except TypeError:
        pass
    return f


def fd_sensor_name() -> str:
    return "/proc/self/fd" if os.path.isdir(_PROC_FD) else "open() tracker"


def install_fd_fallback() -> None:
    if not os.path.isdir(_PROC_FD):  # pragma: no cover
        builtins.open = _tracking_open


def fd_count() -> int:
    if os.path.isdir(_PROC_FD):
        return len(os.listdir(_PROC_FD))
    return sum(1 for f in list(_tracked) if not f.closed)  # pragma: no cover


class AuditCounter:
    """Counts selected audit events. Audit hooks cannot be removed, so it can be paused."""

    EVENTS = ("open", "socket.connect", "sqlite3.connect", "import")

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.active = False
        sys.addaudithook(self._hook)

    def _hook(self, event: str, args: tuple) -> None:
        if self.active and event in self.EVENTS:
            self.counts[event] += 1


class CallCounter:
    """Counts calls into code objects defined under ``root`` using sys.monitoring."""

    TOOL_ID = 4

    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        self.counts: Counter[str] = Counter()
        self.enabled = hasattr(sys, "monitoring")

    def _on_start(self, code, offset):  # noqa: ANN001
        if code.co_filename.startswith(self.root):
            rel = os.path.relpath(code.co_filename, self.root)
            self.counts[f"{rel}:{code.co_qualname}"] += 1
        else:
            return sys.monitoring.DISABLE
        return None

    def __enter__(self) -> "CallCounter":
        if self.enabled:
            mon = sys.monitoring
            try:
                mon.use_tool_id(self.TOOL_ID, "codemusume-probe")
            except ValueError:
                self.enabled = False
                return self
            mon.register_callback(self.TOOL_ID, mon.events.PY_START, self._on_start)
            mon.set_events(self.TOOL_ID, mon.events.PY_START)
        return self

    def __exit__(self, *exc) -> None:
        if self.enabled:
            mon = sys.monitoring
            mon.set_events(self.TOOL_ID, 0)
            mon.register_callback(self.TOOL_ID, mon.events.PY_START, None)
            mon.free_tool_id(self.TOOL_ID)

    def top(self, n: int = 6) -> list[dict]:
        return [{"function": k, "calls": v} for k, v in self.counts.most_common(n)]


class LoopLagSentinel:
    """Heartbeat every ``interval`` seconds; records how late each wake-up was."""

    def __init__(self, interval: float = 0.005) -> None:
        self.interval = interval
        self.samples: list[list[float]] = []   # [t_ms, lag_ms]
        self._stop = False
        self._task: asyncio.Task | None = None
        self._t0 = 0.0

    async def _run(self) -> None:
        self._t0 = last = time.perf_counter()
        while not self._stop:
            await asyncio.sleep(self.interval)
            now = time.perf_counter()
            lag = max(0.0, (now - last - self.interval) * 1000)
            self.samples.append([round((now - self._t0) * 1000, 1), round(lag, 1)])
            last = now

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def stop(self) -> None:
        self._stop = True
        if self._task:
            await self._task

    @property
    def max_lag(self) -> float:
        return max((s[1] for s in self.samples), default=0.0)
