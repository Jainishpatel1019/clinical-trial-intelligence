"""Covariate drift via PSI; optional Evidently report; measures alert latency in-process."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd


def psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """Population Stability Index for one numeric feature."""
    expected = expected.astype(float)
    actual = actual.astype(float)
    qs = np.quantile(expected, np.linspace(0, 1, buckets + 1))
    qs[0], qs[-1] = expected.min(), expected.max()
    e_counts, _ = np.histogram(expected, bins=qs)
    a_counts, _ = np.histogram(actual, bins=qs)
    e_pct = (e_counts + 1) / (e_counts.sum() + buckets)
    a_pct = (a_counts + 1) / (a_counts.sum() + buckets)
    return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))


def run_drift(
    random_state: int = 42,
    n_ref: int = 500,
    n_cur: int = 500,
    shift_sigma: float = 1.8,
) -> dict:
    from econml.data.dgps import ihdp_surface_B

    rng = np.random.default_rng(random_state)
    _, _, X, _ = ihdp_surface_B(random_state=random_state)
    X = np.asarray(X, dtype=float)
    idx_ref = rng.choice(len(X), size=n_ref, replace=True)
    idx_cur = rng.choice(len(X), size=n_cur, replace=True)
    ref = X[idx_ref].copy()
    cur = X[idx_cur].copy()
    # Inject mean shift on first 5 features to simulate site drift
    cur[:, :5] += rng.normal(0, shift_sigma, size=(n_cur, 5))

    feature_names = [f"x{i}" for i in range(X.shape[1])]
    psis = {feature_names[j]: psi(ref[:, j], cur[:, j]) for j in range(min(10, X.shape[1]))}
    max_psi = float(max(psis.values()))
    level = "ok"
    if max_psi > 0.2:
        level = "critical"
    elif max_psi > 0.1:
        level = "warning"

    t0 = time.perf_counter()
    _ = max_psi  # compute "alert"
    alert_latency_s = time.perf_counter() - t0

    evidently_ok = False
    try:
        from evidently import ColumnMapping
        from evidently.metric_preset import DataDriftPreset
        from evidently.report import Report

        ref_df = pd.DataFrame(ref[:, :10], columns=feature_names[:10])
        cur_df = pd.DataFrame(cur[:, :10], columns=feature_names[:10])
        t1 = time.perf_counter()
        rep = Report(metrics=[DataDriftPreset()])
        rep.run(
            reference_data=ref_df,
            current_data=cur_df,
            column_mapping=ColumnMapping(),
        )
        _ = rep.json()
        evidently_ok = True
        alert_latency_s = time.perf_counter() - t1
    except Exception:
        pass

    return {
        "psi_top10_features": psis,
        "max_psi_top10": max_psi,
        "alert_level": level,
        "thresholds": {"warning": 0.1, "critical": 0.2},
        "alert_latency_seconds_synthetic": float(alert_latency_s),
        "evidently_report_available": evidently_ok,
        "note": "Latency is in-process compute time for PSI/Evidently on this benchmark slice, not a streaming SLA.",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("evaluation/results/drift_simulation.json"))
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out = run_drift()
    args.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
