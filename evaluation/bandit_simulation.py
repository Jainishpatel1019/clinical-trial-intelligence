"""Monte Carlo bandits: Thompson sampling vs equal allocation vs epsilon-greedy.

Reports regret, inferior-arm exposure, steps-to-confidence proxy, and a simple cost model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _sample_arm_thompson(alphas: np.ndarray, betas: np.ndarray, rng: np.random.Generator) -> int:
    thetas = rng.beta(alphas, betas)
    return int(np.argmax(thetas))


def _regret_step(true_means: np.ndarray, arm: int) -> float:
    return float(np.max(true_means) - true_means[arm])


def run_one_episode(
    true_probs: np.ndarray,
    horizon: int,
    rng: np.random.Generator,
    policy: str,
    epsilon: float = 0.1,
    confidence_threshold: float = 0.95,
) -> dict:
    """One episode of binary rewards; returns cumulative stats."""
    k = len(true_probs)
    best = int(np.argmax(true_probs))
    alphas = np.ones(k)
    betas = np.ones(k)
    n_pull = np.zeros(k, dtype=int)
    successes = np.zeros(k, dtype=int)
    cumulative_regret = 0.0
    inferior_pulls = 0
    t_stop: int | None = None

    for t in range(1, horizon + 1):
        if policy == "thompson":
            arm = _sample_arm_thompson(alphas, betas, rng)
        elif policy == "equal":
            arm = (t - 1) % k
        elif policy == "epsilon_greedy":
            if rng.random() < epsilon:
                arm = int(rng.integers(0, k))
            else:
                means = successes / np.maximum(n_pull, 1)
                arm = int(np.argmax(means))
        else:
            raise ValueError(policy)

        n_pull[arm] += 1
        reward = int(rng.random() < true_probs[arm])
        if reward:
            successes[arm] += 1
            alphas[arm] += 1.0
        else:
            betas[arm] += 1.0

        cumulative_regret += _regret_step(true_probs, arm)
        if arm != best:
            inferior_pulls += 1

        if t_stop is None and t >= k * 5:
            # Posterior P(arm i is best) ~ Monte Carlo from Beta posteriors
            samples = rng.beta(alphas, betas, size=(2000, k))
            best_counts = (samples.argmax(axis=1) == best).mean()
            if best_counts >= confidence_threshold:
                t_stop = t

    return {
        "cumulative_regret": cumulative_regret,
        "inferior_exposure_pct": float(inferior_pulls / horizon * 100.0),
        "steps_to_posterior_confidence": int(t_stop if t_stop is not None else horizon),
    }


def monte_carlo(
    n_sims: int = 1000,
    horizon: int = 800,
    seed: int = 42,
    cost_per_patient: float = 8000.0,
) -> dict:
    rng_master = np.random.default_rng(seed)
    true_probs = np.array([0.42, 0.48, 0.61], dtype=float)
    policies = ["equal", "epsilon_greedy", "thompson"]
    rows: dict[str, list] = {p: [] for p in policies}

    for i in range(n_sims):
        for pol in policies:
            rng = np.random.default_rng(rng_master.integers(0, 2**31 - 1))
            rows[pol].append(run_one_episode(true_probs, horizon, rng, pol))

    def summarize(pol: str) -> dict:
        rs = rows[pol]
        regret = np.mean([r["cumulative_regret"] for r in rs])
        inf = np.mean([r["inferior_exposure_pct"] for r in rs])
        steps = np.mean([r["steps_to_posterior_confidence"] for r in rs])
        return {"mean_cumulative_regret": float(regret), "mean_inferior_exposure_pct": float(inf), "mean_steps_to_confidence": float(steps)}

    summ = {pol: summarize(pol) for pol in policies}
    base_regret = summ["equal"]["mean_cumulative_regret"] + 1e-9
    regret_reduction_ts = float((base_regret - summ["thompson"]["mean_cumulative_regret"]) / base_regret * 100.0)

    steps_eq = summ["equal"]["mean_steps_to_confidence"]
    steps_ts = summ["thompson"]["mean_steps_to_confidence"]
    patients_saved_steps = max(0.0, steps_eq - steps_ts)

    inf_eq = summ["equal"]["mean_inferior_exposure_pct"] + 1e-9
    inf_ts = summ["thompson"]["mean_inferior_exposure_pct"]
    inferior_reduction_pct = float((inf_eq - inf_ts) / inf_eq * 100.0)

    # Visit-level proxy: fewer assignments to the non-optimal arm across the horizon.
    k = float(len(true_probs))
    inferior_assignments_avoided = float(
        horizon * (summ["equal"]["mean_inferior_exposure_pct"] - inf_ts) / 100.0
    )
    # Map avoided assignment-slots to a patient-equivalent count (arms split enrollment).
    patient_equivalent_avoided = float(inferior_assignments_avoided / k)
    cost_saving = float(patient_equivalent_avoided * cost_per_patient)

    return {
        "n_simulations": n_sims,
        "horizon": horizon,
        "true_arm_success_probs": true_probs.tolist(),
        "optimal_arm_index": int(np.argmax(true_probs)),
        "cost_per_patient_usd": cost_per_patient,
        "summary_by_policy": summ,
        "thompson_vs_equal_regret_reduction_pct": regret_reduction_ts,
        "thompson_vs_equal_inferior_exposure_reduction_pct": inferior_reduction_pct,
        "estimated_patients_saved_to_confidence_proxy": float(patients_saved_steps),
        "inferior_arm_assignments_avoided_per_horizon_mean": inferior_assignments_avoided,
        "patient_equivalent_avoided_proxy": patient_equivalent_avoided,
        "estimated_cost_saving_usd_proxy": cost_saving,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n-sims", type=int, default=1000)
    p.add_argument("--horizon", type=int, default=800)
    p.add_argument("--out", type=Path, default=Path("evaluation/results/bandit_simulation.json"))
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out = monte_carlo(n_sims=args.n_sims, horizon=args.horizon)
    args.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
