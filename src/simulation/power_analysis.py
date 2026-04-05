"""Two-sample t-test power and sample size utilities (statsmodels ``TTestIndPower``)."""

from __future__ import annotations

import logging
from typing import Iterable

import numpy as np
import plotly.graph_objects as go
from plotly.graph_objects import Figure
from statsmodels.stats.power import TTestIndPower

logger = logging.getLogger(__name__)

_power = TTestIndPower()


def compute_required_n(
    effect_size: float, alpha: float = 0.05, power: float = 0.80
) -> int:
    """Return required **per-arm** sample size for a balanced two-sample t-test."""
    if effect_size <= 0:
        logger.warning("compute_required_n: effect_size <= 0; returning sentinel 9999")
        return 9999
    n = _power.solve_power(
        effect_size=effect_size,
        nobs1=None,
        alpha=alpha,
        power=power,
        ratio=1.0,
        alternative="two-sided",
    )
    n_int = int(np.ceil(n))
    return max(n_int, 10)


def compute_power(n: int, effect_size: float, alpha: float = 0.05) -> float:
    """Return achieved power for ``n`` subjects per arm (balanced design)."""
    if n < 1:
        return 0.0
    p = _power.solve_power(
        effect_size=effect_size,
        nobs1=n,
        alpha=alpha,
        power=None,
        ratio=1.0,
        alternative="two-sided",
    )
    if p is None or not np.isfinite(p):
        return 0.0
    return float(np.clip(p, 0.0, 1.0))


def plot_power_curve(
    effect_sizes: Iterable[float], total_budget: int, alpha: float = 0.05
) -> Figure:
    """Plot power vs per-arm sample size for several Cohen's *d* effect sizes."""
    fig = go.Figure()
    budget_per_arm = total_budget // 2
    n_values = list(range(20, budget_per_arm, 10))
    if not n_values:
        n_values = [20]

    for es in effect_sizes:
        powers = [compute_power(n, es, alpha=alpha) for n in n_values]
        fig.add_trace(
            go.Scatter(
                x=n_values,
                y=powers,
                mode="lines",
                name=f"d = {es:g}",
            )
        )

    fig.add_hline(y=0.80, line_dash="dash", line_color="gray")
    fig.add_vline(x=budget_per_arm, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="Statistical Power Curve by Sample Size",
        xaxis_title="n per arm (total N = 2 × n)",
        yaxis_title="Power",
        template="plotly_white",
        yaxis_range=[0, 1.05],
        legend_title="Effect size",
    )
    return fig


def compute_mde(n_per_arm: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable standardized effect (Cohen's *d*) for two equal arms."""
    if n_per_arm < 1:
        return float("nan")
    d = _power.solve_power(
        effect_size=None,
        nobs1=n_per_arm,
        alpha=alpha,
        power=power,
        ratio=1.0,
        alternative="two-sided",
    )
    return float(d)
