"""Probe entry point: ``python -m app.lab.harness.probe <workload> <trainee_root> <out.json>``.

Runs one workload in a fresh interpreter, wrapped in the audit-hook and
sys.monitoring sensors, and writes the measurements as JSON.
"""
from __future__ import annotations

import json
import sys
import time
import traceback


def main() -> int:
    name, root, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    sys.path.insert(0, root)
    sys.dont_write_bytecode = True

    from app.lab.harness.sensors import AuditCounter, CallCounter, install_fd_fallback
    from app.lab.harness.workloads import WORKLOADS

    install_fd_fallback()
    audit = AuditCounter()
    started = time.perf_counter()
    try:
        audit.active = True
        with CallCounter(root) as calls:
            result = WORKLOADS[name](root)
        audit.active = False
        result["calls"] = calls.top()
        result["audit"] = dict(audit.counts)
    except Exception as err:  # the trainee's code is allowed to be broken
        result = {"error": f"{type(err).__name__}: {err}", "trace": traceback.format_exc()[-1500:]}
    result["wall_ms"] = round((time.perf_counter() - started) * 1000, 1)
    result["python"] = sys.version.split()[0]
    with open(out_path, "w") as fh:
        json.dump(result, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
