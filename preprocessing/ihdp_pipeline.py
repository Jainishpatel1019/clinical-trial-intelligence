"""IHDP-style benchmark data, balance checks, overlap trimming, and optional expansion.

Uses ``econml.data.dgps.ihdp_surface_B`` (747 rows, 26 covariates) with known ITE for PEHE.
Optional bootstrap expansion resamples rows and adds small outcome noise for scale experiments;
expanded rows reuse the resampled unit's true ITE (documented in README).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors


def _smd_binary(treated: np.ndarray, control: np.ndarray) -> float:
    """Standardized mean difference for one continuous covariate."""
    m1, m0 = float(np.mean(treated)), float(np.mean(control))
    s1, s0 = float(np.std(treated, ddof=1)), float(np.std(control, ddof=1))
    sp = np.sqrt((s1**2 + s0**2) / 2) + 1e-12
    return abs(m1 - m0) / sp


@dataclass
class OverlapReport:
    propensity_min: float
    propensity_max: float
    trim_low: float
    trim_high: float
    n_before: int
    n_after: int
    pct_trimmed: float


def load_ihdp_econml(random_state: int = 42) -> tuple[pd.DataFrame, np.ndarray]:
    """Return features DataFrame (with ``y``, ``treatment``) and true ITE vector."""
    from econml.data.dgps import ihdp_surface_B

    Y, T, X, tau = ihdp_surface_B(random_state=random_state)
    cols = [f"x{i}" for i in range(X.shape[1])]
    df = pd.DataFrame(X, columns=cols)
    df["treatment"] = T.astype(int)
    df["y"] = Y.astype(float)
    return df, np.asarray(tau, dtype=float)


def report_missingness(df: pd.DataFrame, feature_cols: list[str]) -> dict[str, float]:
    """Fraction missing per feature."""
    return {c: float(df[c].isna().mean()) for c in feature_cols}


def inject_mcar_missing(
    df: pd.DataFrame,
    feature_cols: list[str],
    missing_rate: float = 0.02,
    random_state: int = 0,
) -> pd.DataFrame:
    """Optional MCAR missingness for methodology demo; pair with median imputation."""
    rng = np.random.default_rng(random_state)
    out = df.copy()
    for c in feature_cols:
        mask = rng.random(len(out)) < missing_rate
        out.loc[mask, c] = np.nan
    return out


def impute_median(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in feature_cols:
        med = float(out[c].median())
        out[c] = out[c].fillna(med)
    return out


def propensity_and_overlap(
    X: np.ndarray,
    T: np.ndarray,
    trim_q: tuple[float, float] = (0.05, 0.95),
) -> tuple[np.ndarray, OverlapReport]:
    """Fit propensity e(X); trim extreme support (positivity / overlap)."""
    ps = LogisticRegression(max_iter=500, random_state=42).fit(X, T).predict_proba(X)[:, 1]
    low, high = float(np.quantile(ps, trim_q[0])), float(np.quantile(ps, trim_q[1]))
    keep = (ps >= low) & (ps <= high)
    n_before = int(len(T))
    n_after = int(keep.sum())
    rep = OverlapReport(
        propensity_min=float(ps.min()),
        propensity_max=float(ps.max()),
        trim_low=low,
        trim_high=high,
        n_before=n_before,
        n_after=n_after,
        pct_trimmed=float((n_before - n_after) / n_before * 100.0),
    )
    return ps, rep


def smd_top_k(
    df: pd.DataFrame,
    feature_cols: list[str],
    treatment_col: str = "treatment",
    k: int = 5,
) -> dict[str, float]:
    """Absolute SMD per feature for treated vs control; return k largest."""
    t = df[treatment_col].astype(bool).values
    scores: dict[str, float] = {}
    for c in feature_cols:
        x = df[c].astype(float).values
        scores[c] = _smd_binary(x[t], x[~t])
    top = sorted(scores.items(), key=lambda kv: -kv[1])[:k]
    return {c: float(s) for c, s in top}


def match_on_propensity(
    df: pd.DataFrame,
    feature_cols: list[str],
    ps: np.ndarray,
    treatment_col: str = "treatment",
) -> pd.DataFrame:
    """1:1 nearest-neighbor matching on propensity score (control reservoir)."""
    df = df.copy()
    df["_ps"] = ps
    treat = df[df[treatment_col] == 1].reset_index(drop=True)
    ctrl = df[df[treatment_col] == 0].reset_index(drop=True)
    if len(treat) == 0 or len(ctrl) == 0:
        return df.drop(columns=["_ps"])
    nn = NearestNeighbors(n_neighbors=1).fit(ctrl["_ps"].values.reshape(-1, 1))
    _, idx = nn.kneighbors(treat["_ps"].values.reshape(-1, 1))
    matched_ctrl = ctrl.iloc[idx.ravel()].reset_index(drop=True)
    out = pd.concat([treat, matched_ctrl], axis=0, ignore_index=True)
    return out.drop(columns=["_ps"])


def expand_covariates(
    df: pd.DataFrame,
    tau: np.ndarray,
    target_n: int,
    feature_cols: list[str],
    random_state: int = 42,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Bootstrap-expand: resample rows; reuse true ITE; add small outcome noise."""
    rng = np.random.default_rng(random_state)
    n = len(df)
    idx = rng.integers(0, n, size=target_n)
    d2 = df.iloc[idx].reset_index(drop=True)
    tau2 = tau[idx].copy()
    d2["y"] = d2["y"].values + rng.normal(0, 0.01, size=target_n)
    return d2, tau2


def run_pipeline(
    *,
    expand_n: int | None,
    inject_missing: bool,
    random_state: int = 42,
) -> dict:
    df, tau = load_ihdp_econml(random_state=random_state)
    feature_cols = [c for c in df.columns if c.startswith("x")]

    if inject_missing:
        df = inject_mcar_missing(df, feature_cols, random_state=random_state)
        df = impute_median(df, feature_cols)

    missing_report = report_missingness(df, feature_cols)

    X = df[feature_cols].values
    T = df["treatment"].values
    ps, overlap = propensity_and_overlap(X, T)
    smd_raw = smd_top_k(df, feature_cols, k=5)

    keep = (ps >= overlap.trim_low) & (ps <= overlap.trim_high)
    df_trim = df.loc[keep].reset_index(drop=True)
    tau_trim = tau[np.asarray(keep)]
    ps_trim = ps[np.asarray(keep)]

    df_matched = match_on_propensity(df_trim, feature_cols, ps_trim)
    smd_matched = smd_top_k(df_matched, feature_cols, k=5)

    if expand_n and expand_n > len(df_trim):
        df_out, tau_out = expand_covariates(df_trim, tau_trim, expand_n, feature_cols, random_state)
    else:
        df_out, tau_out = df_trim.copy(), tau_trim.copy()

    max_smd_after = max(smd_matched.values()) if smd_matched else 0.0

    return {
        "n_rows_final": int(len(df_out)),
        "overlap": asdict(overlap),
        "smd_top5_before_trim": smd_raw,
        "smd_top5_after_ps_match": smd_matched,
        "max_smd_after_match": float(max_smd_after),
        "missingness_rate_per_feature": missing_report,
        "feature_cols": feature_cols,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="IHDP preprocessing diagnostics")
    p.add_argument("--expand-n", type=int, default=None, help="Bootstrap-expand to N rows")
    p.add_argument("--inject-missing", action="store_true")
    p.add_argument("--out", type=Path, default=Path("evaluation/results/ihdp_preprocess.json"))
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report = run_pipeline(
        expand_n=args.expand_n,
        inject_missing=args.inject_missing,
    )
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
