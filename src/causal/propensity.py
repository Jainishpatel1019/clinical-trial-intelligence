"""Propensity score estimation and overlap diagnostics for treatment assignment."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "enrollment_log",
    "phase_numeric",
    "min_age_years",
    "max_age_years",
    "is_oncology",
    "is_cardiovascular",
]


class PropensityScorer:
    """Fit a logistic propensity model and summarize overlap between treatment arms."""

    def __init__(self) -> None:
        self.model: LogisticRegression | None = None
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame) -> dict[str, Any]:
        """Fit propensity scores on ``df`` and return discrimination and overlap metrics."""
        X = df[FEATURE_COLS].copy()
        medians = X.median(numeric_only=True)
        X_imputed = X.fillna(medians)
        X_imputed = X_imputed.fillna(0.0)

        T = df["is_randomized"].astype(int)
        model = LogisticRegression(
            C=1.0, max_iter=1000, random_state=42, solver="lbfgs"
        )
        model.fit(X_imputed, T)

        propensity_scores = model.predict_proba(X_imputed)[:, 1]

        self.model = model
        self.propensity_scores = propensity_scores
        self.T = T
        self.is_fitted = True

        treated_mask = T.to_numpy() == 1
        control_mask = T.to_numpy() == 0
        treated_ps = propensity_scores[treated_mask]
        control_ps = propensity_scores[control_mask]

        n_treated = int(T.sum())
        n_control = int((1 - T).sum())

        if len(treated_ps) > 0 and len(control_ps) > 0:
            overlap_min = max(float(np.min(treated_ps)), float(np.min(control_ps)))
            overlap_max = min(float(np.max(treated_ps)), float(np.max(control_ps)))
            overlap_ok = bool(overlap_min < overlap_max)
            mean_ps_treated = float(np.mean(treated_ps))
            mean_ps_control = float(np.mean(control_ps))
        else:
            overlap_min = float("nan")
            overlap_max = float("nan")
            overlap_ok = False
            mean_ps_treated = float(np.mean(treated_ps)) if len(treated_ps) else float("nan")
            mean_ps_control = float(np.mean(control_ps)) if len(control_ps) else float("nan")

        logger.info(
            "Propensity overlap_ok=%s overlap_region=(%s, %s)",
            overlap_ok,
            overlap_min,
            overlap_max,
        )

        try:
            auc_roc = float(roc_auc_score(T, propensity_scores))
        except ValueError:
            auc_roc = float("nan")

        return {
            "auc_roc": auc_roc,
            "overlap_ok": overlap_ok,
            "overlap_region": (float(overlap_min), float(overlap_max)),
            "n_treated": n_treated,
            "n_control": n_control,
            "mean_ps_treated": mean_ps_treated,
            "mean_ps_control": mean_ps_control,
        }

    def plot_overlap(self) -> go.Figure:
        """Plot overlapping histograms of propensity scores by treatment arm."""
        if not self.is_fitted:
            raise ValueError("Call fit() first")

        T = self.T.to_numpy()
        ps = self.propensity_scores
        treated_ps = ps[T == 1]
        control_ps = ps[T == 0]

        fig = go.Figure()
        fig.add_trace(
            go.Histogram(
                x=treated_ps,
                name="Randomized",
                marker_color="rgba(31,119,180,0.6)",
                opacity=0.6,
            )
        )
        fig.add_trace(
            go.Histogram(
                x=control_ps,
                name="Observational",
                marker_color="rgba(255,127,14,0.6)",
                opacity=0.6,
            )
        )
        fig.update_layout(
            title="Propensity Score Overlap",
            xaxis_title="Propensity Score",
            yaxis_title="Count",
            barmode="overlay",
            template="plotly_dark",
        )
        fig.add_vline(x=0.5, line_dash="dash", line_color="gray")
        return fig
