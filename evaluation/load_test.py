"""Concurrent inference benchmark and optional Locust against bench_server.

1) In-process: 50 threads each submit a 100-patient batch through the same scoring path as bench_server.
2) Optional: start uvicorn + locust if ``--locust`` and deps installed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import urllib.error
import urllib.request


def _batch_scores(features: np.ndarray) -> np.ndarray:
    rng = np.random.default_rng(0)
    w = rng.normal(0, 0.05, size=26).astype(np.float32)
    x = features.astype(np.float32)
    return (x * w.reshape(1, -1)).sum(axis=1)


def in_process_benchmark(
    n_workers: int = 50,
    batch_size: int = 100,
    repeats: int = 20,
) -> dict:
    latencies_ms: list[float] = []
    peak_rows = 0

    def job(_: int) -> float:
        nonlocal peak_rows
        x = np.random.randn(batch_size, 26).astype(np.float32)
        t0 = time.perf_counter()
        out = _batch_scores(x)
        peak_rows = max(peak_rows, out.shape[0])
        return (time.perf_counter() - t0) * 1000.0

    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        futs = [ex.submit(job, i) for i in range(repeats * n_workers)]
        for f in as_completed(futs):
            latencies_ms.append(f.result())

    arr = np.asarray(latencies_ms, dtype=float)
    return {
        "mode": "in_process_threadpool",
        "n_workers": n_workers,
        "batch_size": batch_size,
        "total_batches": len(latencies_ms),
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
        "peak_batch_rows_observed": int(peak_rows),
        "note": "Uses the same linear stub as bench_server for apples-to-apples CPU scoring.",
    }


def memory_probe_batch100() -> dict:
    try:
        import tracemalloc

        tracemalloc.start()
        x = np.random.randn(100, 26)
        _ = _batch_scores(x)
        cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return {
            "tracemalloc_current_bytes": int(cur),
            "tracemalloc_peak_bytes": int(peak),
        }
    except Exception as exc:
        return {"tracemalloc_error": str(exc)}


def run_locust_quick(host: str, duration_s: int = 30) -> dict | None:
    locust = Path(sys.executable).parent / "locust"
    if not locust.exists():
        locust = "locust"
    env = os.environ.copy()
    env["BENCH_HOST"] = host
    cmd = [
        str(locust),
        "-f",
        str(Path(__file__).with_name("locustfile.py")),
        "--headless",
        "-u",
        "50",
        "-r",
        "10",
        "--run-time",
        f"{duration_s}s",
        "--only-summary",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration_s + 60,
            env=env,
        )
        return {
            "locust_exit_code": proc.returncode,
            "locust_stdout_tail": proc.stdout[-4000:],
            "locust_stderr_tail": proc.stderr[-2000:],
        }
    except Exception as exc:
        return {"locust_error": str(exc)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("evaluation/results/load_test.json"))
    p.add_argument("--locust", action="store_true", help="Hit bench_server (must be running)")
    p.add_argument("--bench-url", default="http://127.0.0.1:8765")
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    result: dict = {"in_process": in_process_benchmark(), "memory_probe": memory_probe_batch100()}
    if args.locust:
        try:
            urllib.request.urlopen(args.bench_url + "/health", timeout=2).read()
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            result["locust"] = {"skipped": f"bench not reachable: {exc}"}
        else:
            result["locust"] = run_locust_quick(args.bench_url)

    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
