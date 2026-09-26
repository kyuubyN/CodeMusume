# IBM Bob 2.0 Refactoring Prompt Specification

Use this prompt inside IBM Bob (`bobide`) when demonstrating the live refactoring capability on `sample_trainee_repo/legacy_service.py` for the hackathon pitch video.

## Target File
`sample_trainee_repo/legacy_service.py`

## Prompt to copy into IBM Bob 2.0:
```text
You are IBM Bob 2.0 acting as the Enterprise Lead Developer for CodeMusume.
Refactor `sample_trainee_repo/legacy_service.py` to fix all 5 architectural bottlenecks:

1. SPEED: Replace the blocking `time.sleep(2)` inside `process_orders_batch` with non-blocking `await asyncio.sleep(2)`.
2. STAMINA: Fix the file handle leak by wrapping the `open("orders.log", "a")` in an asynchronous or synchronous `with` context manager.
3. POWER: Transform the sequential for-loop that calls `fetch_external_status` into a concurrent execution using `asyncio.gather(*tasks)`.
4. GUTS: Replace the bare `except:` clause with explicit exception handling (`httpx.HTTPError`, `Exception`) with error logging and ensure `httpx.get` uses an explicit `timeout=10.0`.
5. WISDOM: Add comprehensive PEP 484 type annotations for arguments and return types to all functions (`list[str]`, `list[dict[str, Any] | None]`, etc.).

Ensure clean, modular, production-ready code with 100% typing strictness.
```

## Expected Outcome
After Bob refactors the file, scanning `sample_trainee_repo` with CodeMusume elevates all attribute ranks from **Rank E (350)** to **Rank S / SS (800+)**!
