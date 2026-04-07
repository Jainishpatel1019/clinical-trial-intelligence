"""Fast smoke tests for offline evaluation modules (no heavy RAG model)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("EVAL_SKIP_RAG", "1")


def test_ihdp_preprocess_runs():
    from preprocessing.ihdp_pipeline import run_pipeline

    r = run_pipeline(expand_n=None, inject_missing=False)
    assert r["n_rows_final"] > 100
    assert r["max_smd_after_match"] < 1.0


def test_causal_eval_runs():
    from evaluation.causal_eval import run_causal_eval

    out = run_causal_eval()
    assert "pehe" in out
    assert out["n_test"] > 20


def test_bandit_monte_carlo_small():
    from evaluation.bandit_simulation import monte_carlo

    b = monte_carlo(n_sims=8, horizon=300, seed=7)
    assert b["n_simulations"] == 8
    assert "thompson" in b["summary_by_policy"]


def test_drift_simulation_runs():
    from evaluation.drift_simulation import run_drift

    d = run_drift()
    assert "max_psi_top10" in d


def test_run_all_fast(tmp_path):
    from evaluation.run_all import build_summary

    os.environ["EVAL_SKIP_RAG"] = "1"
    s = build_summary(fast=True)
    assert "results_summary_table" in s
    assert s["causal_eval"]["pehe"] > 0
