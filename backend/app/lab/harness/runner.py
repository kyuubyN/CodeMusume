"""Runs workloads in isolated subprocesses and caches results by code hash."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile

from app.core.config import BACKEND_DIR

# Which trainee files each workload depends on (for the cache key).
WORKLOAD_FILES = {
    "stamina": ["reports.py"],
    "speed": ["profiles.py"],
    "power": ["orders.py"],
    "guts": ["upstream.py"],
    "wisdom": ["shop"],
}

_cache: dict[tuple[str, str], dict] = {}


def code_hash(root: str, name: str) -> str:
    h = hashlib.sha256()
    for rel in WORKLOAD_FILES[name]:
        path = os.path.join(root, rel)
        paths = []
        if os.path.isdir(path):
            for dp, dn, fn in os.walk(path):
                dn[:] = sorted(d for d in dn if d != "__pycache__")
                paths += [os.path.join(dp, f) for f in sorted(fn) if f.endswith(".py")]
        elif os.path.exists(path):
            paths = [path]
        for p in paths:
            h.update(os.path.relpath(p, root).encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:16]


def run_workload(name: str, root: str, timeout: float = 40.0, use_cache: bool = True) -> dict:
    key = (name, code_hash(root, name))
    if use_cache and key in _cache:
        return {**_cache[key], "cached": True}
    fd, out_path = tempfile.mkstemp(suffix=".json", prefix=f"probe-{name}-")
    os.close(fd)
    env = {**os.environ, "PYTHONPATH": str(BACKEND_DIR), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "app.lab.harness.probe", name, os.path.abspath(root), out_path],
            cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            return {"error": f"probe exited with {proc.returncode}", "trace": proc.stderr[-1500:]}
        with open(out_path) as fh:
            result = json.load(fh)
    except subprocess.TimeoutExpired:
        return {"error": f"workload '{name}' timed out after {timeout:.0f}s"}
    finally:
        try:
            os.remove(out_path)
        except OSError:
            pass
    if "error" not in result:
        _cache[key] = result
    return {**result, "cached": False}


async def run_workload_async(name: str, root: str, use_cache: bool = True) -> dict:
    # The probe blocks on a subprocess, so it goes to a worker thread, not the event loop.
    return await asyncio.to_thread(run_workload, name, root, 40.0, use_cache)


async def run_all(root: str) -> dict[str, dict]:
    names = list(WORKLOAD_FILES)
    results = await asyncio.gather(*(run_workload_async(n, root) for n in names))
    return dict(zip(names, results))
