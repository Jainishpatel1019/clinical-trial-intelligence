"""Tests for the adaptive trial simulator and power analysis utilities."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.simulation.bandit import AdaptiveTrialSimulator
from src.simulation.power_analysis import compute_mde, compute_power, compute_required_n


class TestAdaptiveTrialSimulator:
    def test_traditional_allocates_equally(self):
        sim = AdaptiveTrialSimulator(n_arms=3, total_budget=300, true_effects=[0.3, 0.5, 0.7])
        result = sim.simulate_traditional()
        assert result["arm_allocations"] == [100, 100, 100]
        assert "winner" in result
        assert "power_achieved" in result

    def test_adaptive_favors_best_arm(self):
        sim = AdaptiveTrialSimulator(
            n_arms=2, total_budget=400, true_effects=[0.3, 0.9], noise_std=0.1, batch_size=20,
        )
        result = sim.simulate_adaptive()
        assert result["arm_allocations"][1] > result["arm_allocations"][0]
        assert result["correct_winner"] is True

    def test_adaptive_returns_allocation_history(self):
        sim = AdaptiveTrialSimulator(n_arms=2, total_budget=200, batch_size=50)
        result = sim.simulate_adaptive()
        assert "allocation_history" in result
        assert len(result["allocation_history"]) > 0

    def test_monte_carlo_returns_dataframe(self):
        sim = AdaptiveTrialSimulator(n_arms=2, total_budget=200, batch_size=50)
        mc_df = sim.run_monte_carlo(n_simulations=10)
        assert len(mc_df) == 20  # 10 sims x 2 designs
        assert set(mc_df["design"].unique()) == {"Traditional", "Adaptive"}
        assert "power" in mc_df.columns
        assert "correct_winner" in mc_df.columns

    def test_plot_allocation_history_returns_figure(self):
        sim = AdaptiveTrialSimulator(n_arms=2, total_budget=200, batch_size=50)
        result = sim.simulate_adaptive()
        fig = sim.plot_allocation_history(result)
        assert fig is not None


class TestPowerAnalysis:
    def test_required_n_positive(self):
        n = compute_required_n(0.5)
        assert n > 0
        assert isinstance(n, int)

    def test_larger_effect_needs_fewer_samples(self):
        n_small = compute_required_n(0.2)
        n_large = compute_required_n(0.8)
        assert n_small > n_large

    def test_compute_power_increases_with_n(self):
        p1 = compute_power(50, 0.5)
        p2 = compute_power(200, 0.5)
        assert p2 > p1
        assert 0 <= p1 <= 1
        assert 0 <= p2 <= 1

    def test_compute_mde_decreases_with_n(self):
        mde_small = compute_mde(50)
        mde_large = compute_mde(500)
        assert mde_large < mde_small

    def test_zero_effect_returns_sentinel(self):
        assert compute_required_n(0.0) == 9999

    def test_zero_n_returns_zero_power(self):
        assert compute_power(0, 0.5) == 0.0
