"""Feature importance and CATE distribution views for a fitted ``HTEModel``."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

if TYPE_CHECKING:
    from src.causal.hte_model import HTEModel

logger = logging.getLogger(__name__)


class SHAPAnalyzer:
    """Summarize heterogeneous-effect drivers using forest importances and correlations."""

    def __init__(self, hte_model: HTEModel) -> None:
        """Attach a fitted (or to-be-fitted) :class:`HTEModel` instance."""
        self.hte_model = hte_model

    def compute_importance(self) -> pd.DataFrame:
        """Combine forest feature importances with correlation-based effect direction."""
        if not getattr(self.hte_model, "is_fitted", False) or self.hte_model.model is None:
            raise ValueError("HTEModel must be fitted before SHAP analysis")
        if getattr(self.hte_model, "_X", None) is None:
            raise ValueError("HTEModel._X is missing; call fit() first")

        X = np.asarray(self.hte_model._X, dtype=float)
        effects = np.asarray(self.hte_model.model.effect(X), dtype=float).ravel()

        directions: list[str] = []
        for j in range(X.shape[1]):
            col = X[:, j]
            if (
                np.std(col) < 1e-12
                or np.std(effects) < 1e-12
                or not np.isfinite(col).all()
                or not np.isfinite(effects).all()
            ):
                corr = 0.0
            else:
                cmat = np.corrcoef(col, effects)
                c = float(cmat[0, 1])
                corr = c if np.isfinite(c) else 0.0
            directions.append(
                "Increases effect" if corr > 0 else "Decreases effect"
            )

        names = list(self.hte_model.feature_names)
        dir_map = dict(zip(names, directions))

        base = self.hte_model.get_feature_importance().copy()
        base["direction"] = base["feature"].map(dir_map)
        base = base.sort_values("importance", ascending=False).reset_index(drop=True)
        base["rank"] = np.arange(1, len(base) + 1)

        out = base[["feature", "importance", "rank", "direction"]]
        logger.info("SHAPAnalyzer computed importance for %d features", len(out))
        return out

    def plot_importance(self, importance_df: pd.DataFrame) -> Figure:
        """Horizontal bar chart of importances colored by correlation direction."""
        df_plot = importance_df.sort_values("importance", ascending=True)
        fig = px.bar(
            df_plot,
            x="importance",
            y="feature",
            orientation="h",
            color="direction",
            color_discrete_map={
                "Increases effect": "#2ecc71",
                "Decreases effect": "#e74c3c",
            },
            title="Feature Importance: Drivers of Treatment Effect Differences",
            template="plotly_white",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        return fig

    def plot_effect_distribution(self) -> Figure:
        """Histogram of per-row CATE estimates from the causal forest."""
        if not getattr(self.hte_model, "is_fitted", False) or self.hte_model.model is None:
            raise ValueError("HTEModel must be fitted before plotting effect distribution")
        if getattr(self.hte_model, "_X", None) is None:
            raise ValueError("HTEModel._X is missing; call fit() first")

        X = np.asarray(self.hte_model._X, dtype=float)
        effects = np.asarray(self.hte_model.model.effect(X), dtype=float).ravel()
        mean_effect = float(np.mean(effects))

        fig = px.histogram(
            pd.DataFrame({"cate": effects}),
            x="cate",
            nbins=40,
            title="Distribution of Individual Treatment Effects (CATE)",
            template="plotly_white",
        )
        fig.update_xaxes(title_text="Estimated Treatment Effect on Completion Rate")
        fig.update_yaxes(title_text="Number of Trials")
        fig.add_vline(x=0, line_dash="dash", line_color="gray")
        fig.add_vline(x=mean_effect, line_dash="dash", line_color="steelblue")
        return fig
