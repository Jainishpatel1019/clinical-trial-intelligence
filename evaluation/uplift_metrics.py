"""AUUC-style uplift curve area and Qini coefficient (numpy only)."""

from __future__ import annotations

import numpy as np


def _uplift_curve_points(
    y: np.ndarray,
    t: np.ndarray,
    scores: np.ndarray,
    n_bins: int = 50,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (fractions, uplift_at_fraction) for top-k% by score (descending)."""
    order = np.argsort(-scores)
    y = y[order].astype(float)
    t = t[order].astype(int)
    n = len(y)
    fracs: list[float] = []
    uplifts: list[float] = []
    step = max(1, n // n_bins)
    for k in range(step, n + 1, step):
        ys, ts = y[:k], t[:k]
        nt = int(ts.sum())
        nc = k - nt
        if nt < 2 or nc < 2:
            continue
        m1 = float(ys[ts == 1].mean())
        m0 = float(ys[ts == 0].mean())
        fracs.append(k / n)
        uplifts.append(m1 - m0)
    if not fracs:
        return np.array([0.0, 1.0]), np.array([0.0, 0.0])
    return np.asarray(fracs), np.asarray(uplifts)


def auuc_score(y: np.ndarray, t: np.ndarray, scores: np.ndarray) -> float:
    """Area under the uplift curve (trapezoid), normalized by random baseline area.

    Random baseline approximated as straight line from 0 to global ATE.
    """
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=int)
    scores = np.asarray(scores, dtype=float)
    ate = float(y[t == 1].mean() - y[t == 0].mean()) if (t == 1).any() and (t == 0).any() else 0.0
    fx, uplift = _uplift_curve_points(y, t, scores)
    if fx.size < 2:
        return 0.0
    area_model = float(np.trapezoid(uplift, fx))
    area_random = float(np.trapezoid(np.linspace(0, ate, len(fx)), fx))
    denom = abs(area_random) + 1e-9
    return (area_model - area_random) / denom


def qini_coefficient(y: np.ndarray, t: np.ndarray, scores: np.ndarray) -> float:
    """Scalar Qini summary: mean incremental Qini ordinate over sorted population.

    Simplified Qini-style accumulation (Radcliffe-style ranking gain).
    """
    order = np.argsort(-scores)
    y = y[order].astype(float)
    t = t[order].astype(int)
    n = len(y)
    n_t = max(int(t.sum()), 1)
    n_c = max(n - n_t, 1)
    cum_t_y = np.cumsum(y * t)
    cum_c_y = np.cumsum(y * (1 - t))
    cum_t = np.cumsum(t)
    cum_c = np.cumsum(1 - t)
    ratio = cum_t / np.maximum(cum_c, 1)
    qini = cum_t_y - ratio * cum_c_y
    return float(np.mean(qini) / (n_t + 1e-9))
