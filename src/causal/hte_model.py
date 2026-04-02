"""Heterogeneous treatment effect estimation with EconML causal forests."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class HTEModel:
    """Estimate conditional average treatment effects (CATE) with ``CausalForestDML``."""

    def __init__(
        self,
        outcome_col: str = "completion_rate",
        treatment_col: str = "is_randomized",
    ) -> None:
        """Configure outcome/treatment columns, feature lists, and scalers."""
        self.outcome_col = outcome_col
        self.treatment_col = treatment_col
        self.model: Any = None
        self.feature_names = [
            "enrollment_log",
            "phase_numeric",
            "min_age_years",
            "max_age_years",
            "is_oncology",
            "is_cardiovascular",
        ]
        self.confounder_names = ["trial_duration_days"]
        self.scaler_X = StandardScaler()
        self.scaler_W = StandardScaler()
        self.is_fitted = False

    def prepare_data(
        self, df: pd.DataFrame
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
        """Drop incomplete rows, impute medians, and return scaled ``X``/``W`` arrays."""
        subset_cols = [self.outcome_col, self.treatment_col] + self.feature_names
        df_clean = df.dropna(subset=subset_cols).copy()

        Y = df_clean[self.outcome_col].values
        T = df_clean[self.treatment_col].astype(int).values

        feat_medians = df_clean[self.feature_names].median(numeric_only=True)
        X_filled = df_clean[self.feature_names].fillna(feat_medians).fillna(0.0)
        X_raw = X_filled.values.astype(float)

        conf_medians = df_clean[self.confounder_names].median(numeric_only=True)
        W_filled = df_clean[self.confounder_names].fillna(conf_medians).fillna(0.0)
        W_raw = W_filled.values.astype(float)

        X = self.scaler_X.fit_transform(X_raw)
        W = self.scaler_W.fit_transform(W_raw)

        return Y, T, X, W, df_clean

    def fit(self, df: pd.DataFrame) -> dict[str, Any]:
        """Fit ``CausalForestDML`` and return ATE point and interval estimates."""
        Y, T, X, W, df_clean = self.prepare_data(df)

        if len(df_clean) < 50:
            raise ValueError("Need at least 50 rows to fit causal model")

        from econml.dml import CausalForestDML
        from sklearn.ensemble import (
            GradientBoostingClassifier,
            GradientBoostingRegressor,
        )

        self.model = CausalForestDML(
            model_y=GradientBoostingRegressor(
                n_estimators=100, max_depth=3, random_state=42
            ),
            model_t=GradientBoostingClassifier(
                n_estimators=100, max_depth=3, random_state=42
            ),
            n_estimators=200,
            min_samples_leaf=10,
            discrete_treatment=True,
            cv=3,
            random_state=42,
        )
        self.model.fit(Y, T, X=X, W=W)
        self.is_fitted = True
        self._X = X
        self._df_clean = df_clean

        ate_arr = np.asarray(self.model.ate(X))
        ate = float(np.squeeze(ate_arr))

        lb, ub = self.model.ate_interval(X, alpha=0.05)
        ate_lower = float(np.squeeze(np.asarray(lb)))
        ate_upper = float(np.squeeze(np.asarray(ub)))

        logger.info(
            "HTEModel fitted: n=%s ATE=%.4f CI=[%.4f, %.4f]",
            len(df_clean),
            ate,
            ate_lower,
            ate_upper,
        )

        return {
            "ate": ate,
            "ate_lower": ate_lower,
            "ate_upper": ate_upper,
            "n_samples": len(df_clean),
            "n_treated": int(T.sum()),
            "n_control": int((1 - T).sum()),
        }

    def estimate_subgroup_effects(self) -> pd.DataFrame:
        """Aggregate mean CATE and intervals by ``age_group`` and ``condition``."""
        if not self.is_fitted or self.model is None or self._X is None:
            raise ValueError("Call fit() first")
        if self._df_clean is None:
            raise ValueError("Call fit() first")

        effects = self.model.effect(self._X)
        lb, ub = self.model.effect_interval(self._X, alpha=0.05)

        effects = np.asarray(effects).reshape(-1)
        lb = np.asarray(lb).reshape(-1)
        ub = np.asarray(ub).reshape(-1)

        df_effects = self._df_clean.copy()
        df_effects["cate"] = effects
        df_effects["cate_lower"] = lb
        df_effects["cate_upper"] = ub

        results: list[dict[str, Any]] = []
        for age_group in df_effects["age_group"].unique():
            for condition in df_effects["condition"].unique():
                mask = (df_effects["age_group"] == age_group) & (
                    df_effects["condition"] == condition
                )
                sub = df_effects[mask]
                if len(sub) < 5:
                    continue
                results.append(
                    {
                        "age_group": age_group,
                        "condition": condition,
                        "cate_mean": float(sub["cate"].mean()),
                        "cate_lower": float(sub["cate_lower"].mean()),
                        "cate_upper": float(sub["cate_upper"].mean()),
                        "cate_std": float(sub["cate"].std()),
                        "n_samples": len(sub),
                        "significant": bool(
                            (sub["cate_lower"] > 0).all()
                            or (sub["cate_upper"] < 0).all()
                        ),
                    }
                )

        if not results:
            return pd.DataFrame(
                columns=[
                    "age_group",
                    "condition",
                    "cate_mean",
                    "cate_lower",
                    "cate_upper",
                    "cate_std",
                    "n_samples",
                    "significant",
                ]
            )
        return pd.DataFrame(results).sort_values("cate_mean", ascending=False)

    def get_feature_importance(self) -> pd.DataFrame:
        """Return causal-forest feature importances for heterogeneity features ``X``."""
        if not self.is_fitted or self.model is None:
            raise ValueError("Call fit() first")

        importances = np.asarray(self.model.feature_importances_, dtype=float).ravel()
        n_feat = len(self.feature_names)
        if importances.size >= n_feat:
            importances = importances[:n_feat]
        else:
            pad = np.zeros(n_feat, dtype=float)
            pad[: importances.size] = importances
            importances = pad

        return (
            pd.DataFrame(
                {"feature": self.feature_names, "importance": importances}
            ).sort_values("importance", ascending=False)
        )
