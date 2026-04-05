"""Adaptive trial simulation using Thompson sampling (Beta-Bernoulli)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.graph_objects import Figure
from scipy import stats


def _pvalue_from_ttest(res: Any) -> float:
    if hasattr(res, "pvalue"):
        return float(res.pvalue)
    return float(res[1])


class AdaptiveTrialSimulator:
    """Compare equal allocation to Thompson sampling on Gaussian arm rewards clipped to [0, 1]."""

    def __init__(
        self,
        n_arms: int = 3,
        total_budget: int = 600,
        true_effects: list[float] | None = None,
        noise_std: float = 0.15,
        batch_size: int = 50,
    ) -> None:
        self.n_arms = n_arms
        self.total_budget = total_budget
        default_three = [0.45, 0.60, 0.75]
        if true_effects is None:
            self.true_effects = default_three[:n_arms]
            if len(self.true_effects) < n_arms:
                self.true_effects.extend(
                    [default_three[-1]] * (n_arms - len(self.true_effects))
                )
        else:
            self.true_effects = list(true_effects)[:n_arms]
            if len(self.true_effects) < n_arms:
                raise ValueError("true_effects must have length >= n_arms.")
        self.noise_std = noise_std
        self.batch_size = batch_size

    def _observe_outcome(self, arm: int) -> float:
        """Draw a noisy surrogate outcome for ``arm``, clipped to ``[0, 1]``."""
        x = float(np.random.normal(self.true_effects[arm], self.noise_std))
        return float(np.clip(x, 0.0, 1.0))

    def simulate_traditional(self) -> dict[str, Any]:
        """Equal allocation across arms; pick winner by highest sample mean."""
        n_per_arm = self.total_budget // self.n_arms
        if n_per_arm < 1:
            raise ValueError("total_budget must be at least n_arms for traditional design.")

        outcomes_by_arm: list[list[float]] = []
        for arm in range(self.n_arms):
            outcomes = [self._observe_outcome(arm) for _ in range(n_per_arm)]
            outcomes_by_arm.append(outcomes)

        arm_means = [float(np.mean(o)) for o in outcomes_by_arm]
        winner = int(np.argmax(arm_means))
        correct = winner == int(np.argmax(self.true_effects))

        order = sorted(range(self.n_arms), key=lambda i: arm_means[i])
        second_idx = order[-2]
        best = outcomes_by_arm[winner]
        second = outcomes_by_arm[second_idx]
        pvalue = _pvalue_from_ttest(stats.ttest_ind(best, second))

        return {
            "design": "Traditional (Equal Allocation)",
            "arm_allocations": [n_per_arm] * self.n_arms,
            "arm_means_observed": arm_means,
            "winner": winner,
            "correct_winner": correct,
            "total_n": n_per_arm * self.n_arms,
            "power_achieved": float(pvalue < 0.05),
            "p_value": pvalue,
        }

    def simulate_adaptive(self) -> dict[str, Any]:
        """Thompson sampling with Beta priors updated from Bernoulli successes (outcome > 0.5)."""
        alphas = [1.0] * self.n_arms
        betas = [1.0] * self.n_arms
        arm_counts = [0] * self.n_arms
        all_outcomes: list[list[float]] = [[] for _ in range(self.n_arms)]
        allocation_history: list[dict[str, Any]] = []
        total_enrolled = 0

        while total_enrolled < self.total_budget:
            batch_allocations = [0] * self.n_arms
            remaining = self.total_budget - total_enrolled
            batch_limit = min(self.batch_size, remaining)
            for _ in range(batch_limit):
                thetas = [
                    float(np.random.beta(alphas[k], betas[k])) for k in range(self.n_arms)
                ]
                arm = int(np.argmax(thetas))
                outcome = self._observe_outcome(arm)
                if outcome > 0.5:
                    alphas[arm] += 1.0
                else:
                    betas[arm] += 1.0
                arm_counts[arm] += 1
                batch_allocations[arm] += 1
                all_outcomes[arm].append(outcome)
                total_enrolled += 1

            total_batch = sum(batch_allocations)
            pct_map = {
                f"arm_{k}_pct": (
                    batch_allocations[k] / total_batch * 100.0 if total_batch else 0.0
                )
                for k in range(self.n_arms)
            }
            allocation_history.append(
                {
                    "batch": len(allocation_history) + 1,
                    "enrolled_so_far": total_enrolled,
                    **pct_map,
                }
            )

        arm_means = [float(np.mean(o)) if o else 0.0 for o in all_outcomes]
        winner = int(np.argmax(arm_means))
        correct = winner == int(np.argmax(self.true_effects))

        best = all_outcomes[winner]
        second_idx = sorted(range(self.n_arms), key=lambda i: arm_means[i])[-2]
        second = all_outcomes[second_idx]
        if len(best) > 1 and len(second) > 1:
            pvalue = _pvalue_from_ttest(stats.ttest_ind(best, second))
        else:
            pvalue = 1.0

        n_saved_vs_traditional = (
            (self.total_budget - total_enrolled)
            + (self.total_budget // self.n_arms - min(arm_counts)) * (self.n_arms - 1)
        )

        return {
            "design": "Adaptive (Thompson Sampling)",
            "arm_allocations": arm_counts,
            "arm_means_observed": arm_means,
            "winner": winner,
            "correct_winner": correct,
            "total_n": total_enrolled,
            "power_achieved": float(pvalue < 0.05),
            "p_value": pvalue,
            "allocation_history": allocation_history,
            "n_saved_vs_traditional": n_saved_vs_traditional,
        }

    def run_monte_carlo(self, n_simulations: int = 100) -> pd.DataFrame:
        """Run paired traditional vs adaptive simulations and stack long-form rows."""
        rows: list[dict[str, Any]] = []
        for i in range(n_simulations):
            np.random.seed(i)
            trad = self.simulate_traditional()
            adapt = self.simulate_adaptive()
            rows.append(
                {
                    "sim": i,
                    "design": "Traditional",
                    "correct_winner": trad["correct_winner"],
                    "power": trad["power_achieved"],
                    "total_n": trad["total_n"],
                }
            )
            rows.append(
                {
                    "sim": i,
                    "design": "Adaptive",
                    "correct_winner": adapt["correct_winner"],
                    "power": adapt["power_achieved"],
                    "total_n": adapt["total_n"],
                }
            )
        return pd.DataFrame(rows)

    def plot_allocation_history(self, adaptive_result: dict[str, Any]) -> Figure:
        """Stacked area chart of per-batch allocation percentages by arm."""
        history_df = pd.DataFrame(adaptive_result["allocation_history"])
        pct_cols = [c for c in history_df.columns if c.startswith("arm_")]
        pct_cols.sort(key=lambda c: int(c.split("_")[1]))

        base_colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6"]
        colors = [
            base_colors[j % len(base_colors)] for j in range(len(pct_cols))
        ]

        fig = go.Figure()
        for i, col in enumerate(pct_cols):
            arm_idx = int(col.split("_")[1])
            arm_label = arm_idx + 1  # match UI sliders "Arm 1, Arm 2, ..."
            fig.add_trace(
                go.Scatter(
                    x=history_df["enrolled_so_far"],
                    y=history_df[col],
                    mode="lines",
                    stackgroup="one",
                    name=(
                        f"Arm {arm_label} "
                        f"(true effect: {self.true_effects[arm_idx]:.0%})"
                    ),
                    fillcolor=colors[i],
                    line=dict(width=0.5),
                )
            )
        fig.update_layout(
            title="Adaptive Allocation Over Time",
            xaxis_title="Total Participants Enrolled",
            yaxis_title="% Allocation to Arm",
            template="plotly_white",
        )
        return fig
