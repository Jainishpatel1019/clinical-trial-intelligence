"""IHDP benchmark: CausalForestDML, PEHE, AUUC, Qini, policy tree, targeting vs random."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from evaluation.uplift_metrics import auuc_score, qini_coefficient


def _fit_cate_model(
    X: np.ndarray,
    y: np.ndarray,
    t: np.ndarray,
    random_state: int = 42,
):
    from econml.dml import CausalForestDML
    from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

    est = CausalForestDML(
        model_y=GradientBoostingRegressor(
            n_estimators=80, max_depth=3, random_state=random_state
        ),
        model_t=GradientBoostingClassifier(
            n_estimators=80, max_depth=3, random_state=random_state
        ),
        n_estimators=200,
        min_samples_leaf=10,
        discrete_treatment=True,
        cv=3,
        random_state=random_state,
    )
    est.fit(y, t, X=X, W=None)
    return est


def _policy_tree_text(tree: DecisionTreeRegressor, feature_names: list[str]) -> str:
    from sklearn.tree import export_text

    return export_text(tree, feature_names=feature_names, max_depth=3)


def targeting_metrics(
    tau_true: np.ndarray,
    tau_pred: np.ndarray,
    top_frac: float = 0.30,
    n_mc: int = 400,
    random_state: int = 0,
) -> dict[str, float]:
    """Share of true top responders captured in predicted top fraction vs random policy."""
    rng = np.random.default_rng(random_state)
    n = len(tau_true)
    k = max(1, int(round(top_frac * n)))
    true_top = set(np.argsort(-tau_true)[:k])
    pred_top = set(np.argsort(-tau_pred)[:k])
    model_capture = len(true_top & pred_top) / k

    random_captures: list[float] = []
    for _ in range(n_mc):
        rand_top = set(rng.choice(n, size=k, replace=False))
        random_captures.append(len(true_top & rand_top) / k)
    random_mean = float(np.mean(random_captures))
    lift = model_capture / (random_mean + 1e-9)
    return {
        "top_fraction": top_frac,
        "model_capture_rate_of_true_top": float(model_capture),
        "random_baseline_capture_rate_mean": random_mean,
        "lift_vs_random": float(lift),
    }


def run_causal_eval(
    random_state: int = 42,
    test_size: float = 0.2,
) -> dict:
    from econml.data.dgps import ihdp_surface_B

    y, t, X, tau = ihdp_surface_B(random_state=random_state)
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=int)
    X = np.asarray(X, dtype=float)
    tau = np.asarray(tau, dtype=float)

    X_tr, X_te, y_tr, y_te, t_tr, t_te, tau_tr, tau_te = train_test_split(
        X, y, t, tau, test_size=test_size, random_state=random_state, stratify=t
    )

    est = _fit_cate_model(X_tr, y_tr, t_tr, random_state=random_state)
    tau_pred_te = np.asarray(est.effect(X_te)).reshape(-1)

    pehe = float(np.sqrt(np.mean((tau_pred_te - tau_te) ** 2)))

    auuc = float(auuc_score(y_te, t_te, tau_pred_te))
    qini = float(qini_coefficient(y_te, t_te, tau_pred_te))

    tau_pred_tr = np.asarray(est.effect(X_tr)).reshape(-1)
    feat_names = [f"x{i}" for i in range(X_tr.shape[1])]
    ptree = DecisionTreeRegressor(max_depth=3, random_state=random_state)
    ptree.fit(X_tr, tau_pred_tr)
    rules_text = _policy_tree_text(ptree, feat_names)

    targ = targeting_metrics(tau_te, tau_pred_te, top_frac=0.30, random_state=random_state)

    return {
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
        "pehe": pehe,
        "auuc_normalized": auuc,
        "qini_coefficient": qini,
        "policy_tree_depth": int(ptree.get_depth()),
        "policy_tree_export": rules_text[:2000],
        "targeting": targ,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("evaluation/results/causal_eval.json"))
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out = run_causal_eval()
    args.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
