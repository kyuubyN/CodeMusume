"""Workloads: the experiments the harness runs against the trainee's code.

Each workload imports the trainee module from ``root``, drives it with a
realistic load, and returns measurements plus a time series for the chart.
They run inside the probe subprocess, never in the API server.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

from app.lab.harness.sensors import LoopLagSentinel, fd_count, fd_sensor_name


def _pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    k = min(len(vals) - 1, max(0, round(q * (len(vals) - 1))))
    return round(vals[k], 1)


# ---------------------------------------------------------------------------
# Stamina: file handles under bad input
# ---------------------------------------------------------------------------

def stamina(root: str) -> dict:
    import reports  # type: ignore[import-not-found]

    n, bad_every = 400, 20
    tmp = tempfile.mkdtemp(prefix="lab-reports-")
    paths = []
    for i in range(n):
        p = os.path.join(tmp, f"report_{i:03d}.json")
        with open(p, "w") as fh:
            if i % bad_every == bad_every - 1:
                fh.write('{"title": "Report %d", "rows": [1, 2' % i)  # truncated upload
            else:
                json.dump({"title": f"Report {i}", "rows": list(range(8))}, fh)
        paths.append(p)

    # The dashboard keeps failed requests for its error page, like most error trackers do.
    failures: list = []
    fd0 = fd_count()
    series = [[0, 0]]
    t0 = time.perf_counter()
    for i, p in enumerate(paths):
        try:
            reports.load_report(p)
        except Exception:
            failures.append(sys.exc_info())
        if i % 10 == 9:
            series.append([i + 1, fd_count() - fd0])
    elapsed = time.perf_counter() - t0
    leaked = fd_count() - fd0
    return {
        "metrics": {
            "requests": n,
            "bad_requests": len(failures),
            "leaked_fds": leaked,
            "us_per_request": round(elapsed / n * 1e6, 1),
        },
        "headline": {"label": "File descriptors still open", "value": leaked, "unit": "fds"},
        "series": {"x": "requests", "y": "open fds", "points": series},
        "notes": [f"fd sensor: {fd_sensor_name()}", f"{len(failures)} malformed reports kept by the error tracker"],
    }


# ---------------------------------------------------------------------------
# Speed: 40 concurrent requests on one event loop
# ---------------------------------------------------------------------------

def speed(root: str) -> dict:
    import profiles  # type: ignore[import-not-found]

    n = 40
    latencies: list[float] = []
    errors = 0

    async def main() -> float:
        nonlocal errors
        sentinel = LoopLagSentinel(0.005)
        sentinel.start()
        await asyncio.sleep(0.03)

        arrival = time.perf_counter()  # all requests arrive together

        async def one(uid: int) -> None:
            nonlocal errors
            try:
                out = await profiles.handle_request(uid)
                if not isinstance(out, dict) or out.get("id") != uid:
                    errors += 1
            except Exception:
                errors += 1
            latencies.append((time.perf_counter() - arrival) * 1000)

        await asyncio.gather(*(one(i) for i in range(n)))
        total = (time.perf_counter() - arrival) * 1000
        await asyncio.sleep(0.03)
        await sentinel.stop()
        main.sentinel = sentinel  # type: ignore[attr-defined]
        return total

    total = asyncio.run(main())
    sentinel = main.sentinel  # type: ignore[attr-defined]
    return {
        "metrics": {
            "requests": n,
            "total_ms": round(total, 1),
            "p50_ms": _pct(latencies, 0.5),
            "p99_ms": _pct(latencies, 0.99),
            "max_loop_lag_ms": round(sentinel.max_lag, 1),
            "errors": errors,
        },
        "headline": {"label": "p99 latency", "value": _pct(latencies, 0.99), "unit": "ms"},
        "series": {"x": "ms", "y": "event-loop lag (ms)", "points": sentinel.samples[:400]},
        "notes": ["each request waits ~40 ms on its upstream", "heartbeat every 5 ms measures loop lag"],
    }


# ---------------------------------------------------------------------------
# Power: rendering the order page
# ---------------------------------------------------------------------------

RTT_S = 0.0005  # simulated network round trip to the database


def power(root: str) -> dict:
    import orders  # type: ignore[import-not-found]

    with closing(sqlite3.connect(":memory:", check_same_thread=False)) as conn:
        conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL)")
        conn.executemany("INSERT INTO customers VALUES (?, ?)", [(i, f"Customer {i}") for i in range(1, 21)])
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?)",
            [(i, (i % 20) + 1, round(10 + i * 1.5, 2)) for i in range(1, 201)],
        )
        conn.commit()

        queries = 0
        series: list[list[float]] = [[0, 0]]
        t0 = 0.0

        def on_statement(_sql: str) -> None:
            nonlocal queries
            queries += 1
            time.sleep(RTT_S)  # every statement pays a network round trip
            series.append([round((time.perf_counter() - t0) * 1000, 2), queries])

        conn.set_trace_callback(on_statement)
        t0 = time.perf_counter()
        page = orders.render_orders(conn)
        elapsed = (time.perf_counter() - t0) * 1000
        conn.set_trace_callback(None)

    correct = (
        len(page) == 200
        and all(row["customer"] == f"Customer {(row['order'] % 20) + 1}" for row in page)
    )
    return {
        "metrics": {
            "orders": 200,
            "queries": queries,
            "render_ms": round(elapsed, 1),
            "correct": correct,
        },
        "headline": {"label": "SQL round trips per page", "value": queries, "unit": "queries"},
        "series": {"x": "ms", "y": "queries sent", "points": series[:: max(1, len(series) // 300)] + [series[-1]]},
        "notes": [f"each statement pays a simulated {RTT_S * 1000:.1f} ms round trip"],
    }


# ---------------------------------------------------------------------------
# Guts: a flaky pricing service
# ---------------------------------------------------------------------------

HANG_S = 1.2


def _price(sku: int) -> float:
    return round(5 + sku * 0.25, 2)


def guts(root: str) -> dict:
    import upstream  # type: ignore[import-not-found]

    attempts: dict[int, int] = {}
    lock = threading.Lock()

    class Chaos(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # silence
            pass

        def do_GET(self) -> None:  # noqa: N802
            try:
                sku = int(self.path.rsplit("/", 1)[-1])
            except ValueError:
                self.send_error(404)
                return
            with lock:
                attempts[sku] = attempts.get(sku, 0) + 1
                first = attempts[sku] == 1
            if first and sku % 10 == 3:
                time.sleep(HANG_S)           # the upstream stalls
            if first and sku % 10 == 7:
                self.send_error(500, "upstream exploded")
                return
            body = json.dumps({"price": _price(sku)}).encode()
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Chaos)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    upstream.PRICING_URL = f"http://127.0.0.1:{server.server_address[1]}"

    n = 40
    results: list[tuple[int, float, str]] = []

    def one(sku: int) -> tuple[int, float, str]:
        s = time.perf_counter()
        try:
            total = upstream.cart_total([sku])
            outcome = "ok" if total is not None and abs(float(total) - _price(sku)) < 1e-6 else "silent_wrong"
        except Exception:
            outcome = "raised"
        return sku, (time.perf_counter() - s) * 1000, outcome

    t = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(one, range(n)))
    total_ms = (time.perf_counter() - t) * 1000
    server.shutdown()

    lat = [r[1] for r in results]
    outcomes = [r[2] for r in results]
    return {
        "metrics": {
            "requests": n,
            "ok": outcomes.count("ok"),
            "silent_wrong": outcomes.count("silent_wrong"),
            "raised": outcomes.count("raised"),
            "p50_ms": _pct(lat, 0.5),
            "p99_ms": _pct(lat, 0.99),
            "total_ms": round(total_ms, 1),
            "upstream_calls": sum(attempts.values()),
        },
        "headline": {"label": "Checkouts with a silently wrong total", "value": outcomes.count("silent_wrong"), "unit": "orders"},
        "series": {
            "x": "request",
            "y": "latency (ms)",
            "points": [[sku, round(ms, 1)] for sku, ms, _ in results],
            "flags": {str(sku): o for sku, _, o in results if o != "ok"},
        },
        "notes": ["10% of first calls hang for 1.2 s, 10% return HTTP 500", "a correct total is the upstream price"],
    }


# ---------------------------------------------------------------------------
# Wisdom: what does it take to test billing?
# ---------------------------------------------------------------------------

def wisdom(root: str) -> dict:
    from app.lab.analysis.archgraph import analyze
    from app.lab.analysis.callgraph import Program

    report = analyze(Program(root))
    before = set(sys.modules)
    t = time.perf_counter()
    try:
        import shop.billing as billing  # type: ignore[import-not-found]
        charge = billing.charge
        target = "shop.billing"
    except ModuleNotFoundError:
        import shop.orders as orders_mod  # type: ignore[import-not-found]
        charge = orders_mod.charge
        target = "shop.orders"
    import_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    receipt = charge(SimpleNamespace(id=1, email="lab@tachyon.test", lines=[("serum", 2, 3.5)]))
    call_ms = (time.perf_counter() - t) * 1000
    loaded = sorted(m for m in set(sys.modules) - before if m.startswith("shop."))

    shop_mods = [m for m in report.modules if m.startswith("shop.")]
    return {
        "metrics": {
            "modules_loaded": len(loaded),
            "shop_modules": len(shop_mods),
            "cycles": len(report.cycles),
            "hidden_cycles": len(report.hidden_cycles),
            "import_ms": round(import_ms, 1),
            "call_ms": round(call_ms, 1),
            "correct": receipt.get("charged") == 7.2,
            "charge_lives_in": target,
        },
        "headline": {"label": "Modules loaded to test billing.charge()", "value": len(loaded), "unit": "modules"},
        "series": {"x": "module", "y": "loaded", "points": []},
        "graph": {
            "nodes": [
                {"id": m, "loaded": m in loaded, "blast_radius": report.metrics[m].blast_radius,
                 "instability": report.metrics[m].instability}
                for m in shop_mods
            ],
            "edges": [
                {"src": e.src, "dst": e.dst, "lazy": e.lazy,
                 "cycle": any(e.src in c and e.dst in c for c in report.cycles)}
                for e in report.edges if e.src.startswith("shop.") and e.dst.startswith("shop.")
            ],
        },
        "loaded": loaded,
        "notes": ["counts shop modules imported to call charge() once", "graph includes function-level imports"],
    }


WORKLOADS = {"stamina": stamina, "speed": speed, "power": power, "guts": guts, "wisdom": wisdom}
