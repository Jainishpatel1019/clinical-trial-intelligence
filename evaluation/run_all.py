"""Run all offline benchmarks and write evaluation/results/summary.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from evaluation.bandit_simulation import monte_carlo
from evaluation.causal_eval import run_causal_eval
from evaluation.drift_simulation import run_drift
from evaluation.load_test import in_process_benchmark, memory_probe_batch100
from evaluation.rag_eval import run_rag_eval
from preprocessing.ihdp_pipeline import run_pipeline


def build_summary(
    *,
    bandit_sims: int | None = None,
    bandit_horizon: int = 800,
    fast: bool = False,
) -> dict:
    if fast:
        bs = 50
        bandit_horizon = 400
    else:
        bs = bandit_sims if bandit_sims is not None else 1000

    preprocess = run_pipeline(expand_n=None, inject_missing=False)
    causal = run_causal_eval()
    bandit = monte_carlo(n_sims=bs, horizon=bandit_horizon)
    drift = run_drift()
    rag = run_rag_eval()
    load = {
        "in_process": in_process_benchmark(
            n_workers=20 if fast else 50,
            repeats=5 if fast else 20,
        ),
        "memory_probe": memory_probe_batch100(),
    }

    targ = causal["targeting"]
    table = [
        {
            "component": "HTE model (IHDP)",
            "metric": "PEHE (RMSE of ITE)",
            "value": round(causal["pehe"], 4),
            "baseline": "-",
            "delta": "-",
        },
        {
            "component": "HTE model (IHDP)",
            "metric": "AUUC (normalized uplift curve)",
            "value": round(causal["auuc_normalized"], 3),
            "baseline": "0 (random ranking)",
            "delta": "higher is better",
        },
        {
            "component": "HTE model (IHDP)",
            "metric": "Qini coefficient (ranking summary)",
            "value": round(causal["qini_coefficient"], 3),
            "baseline": "-",
            "delta": "-",
        },
        {
            "component": "HTE policy (rank top 30%)",
            "metric": "Capture rate of true top 30% ITE",
            "value": f"{targ['model_capture_rate_of_true_top']*100:.1f}%",
            "baseline": f"{targ['random_baseline_capture_rate_mean']*100:.1f}% (random 30% policy)",
            "delta": f"{targ['lift_vs_random']:.2f}x vs random",
        },
        {
            "component": "Adaptive allocation (sim)",
            "metric": "Mean % patient-visits on non-optimal arm",
            "value": f"{bandit['summary_by_policy']['thompson']['mean_inferior_exposure_pct']:.1f}%",
            "baseline": f"{bandit['summary_by_policy']['equal']['mean_inferior_exposure_pct']:.1f}% (equal rotation)",
            "delta": f"{bandit['thompson_vs_equal_inferior_exposure_reduction_pct']:.1f}% relative reduction vs equal",
        },
        {
            "component": "Adaptive allocation (sim)",
            "metric": "Estimated cost proxy (patient-equiv. x $8k)",
            "value": f"${bandit['estimated_cost_saving_usd_proxy']:,.0f}",
            "baseline": "$0",
            "delta": f"{bandit['patient_equivalent_avoided_proxy']:.1f} patient-equivalent slots avoided / horizon (assignments / arms)",
        },
        {
            "component": "RAG retrieval (mini corpus)",
            "metric": "Faithfulness (RAGAS)",
            "value": rag["ragas"].get("faithfulness")
            or ("skipped" if rag.get("skipped") else "n/a (install eval extras + API)"),
            "baseline": "-",
            "delta": "-",
        },
        {
            "component": "RAG retrieval (mini corpus)",
            "metric": "p95 latency (encode + FAISS)",
            "value": (
                f"{rag['retrieval_latency_ms_p95']:.1f}ms"
                if not rag.get("skipped")
                else "skipped"
            ),
            "baseline": "-",
            "delta": "-",
        },
        {
            "component": "Drift monitor (PSI demo)",
            "metric": "Max PSI (top-10 features, shifted slice)",
            "value": round(drift["max_psi_top10"], 4),
            "baseline": "<0.1 stable",
            "delta": drift["alert_level"],
        },
        {
            "component": "Drift monitor",
            "metric": "Alert compute latency (in-process)",
            "value": f"{drift['alert_latency_seconds_synthetic']*1000:.2f}ms",
            "baseline": "-",
            "delta": "not streaming SLA",
        },
        {
            "component": "Load (in-process stub)",
            "metric": "p95 batch scoring (100 patients)",
            "value": f"{load['in_process']['p95_ms']:.2f}ms",
            "baseline": "-",
            "delta": "50 concurrent workers" if not fast else "20 concurrent workers",
        },
    ]

    return {
        "preprocessing": preprocess,
        "causal_eval": causal,
        "bandit_simulation": bandit,
        "drift_simulation": drift,
        "rag_eval": rag,
        "load_test": load,
        "results_summary_table": table,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("evaluation/results/summary.json"))
    p.add_argument("--fast", action="store_true", help="Smaller MC + fewer load threads (for CI)")
    p.add_argument(
        "--bandit-sims",
        type=int,
        default=None,
        help="Monte Carlo runs (default 1000, ignored if --fast)",
    )
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary = build_summary(fast=args.fast, bandit_sims=args.bandit_sims)
    args.out.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary["results_summary_table"], indent=2))


if __name__ == "__main__":
    main()
