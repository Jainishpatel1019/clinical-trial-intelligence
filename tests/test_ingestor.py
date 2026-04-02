"""Tests for demo / ingest data quality (no external API calls)."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REQUIRED_COLS = [
    "nct_id",
    "condition",
    "phase",
    "enrollment_count",
    "completion_rate",
    "is_randomized",
]


@pytest.fixture
def demo_trials_path() -> str:
    return os.path.join(
        os.path.dirname(__file__), "..", "data", "processed", "demo_trials.csv"
    )


def test_demo_data_loads(demo_trials_path):
    df = pd.read_csv(demo_trials_path)
    assert len(df) == 300
    for col in REQUIRED_COLS:
        assert col in df.columns, f"missing column: {col}"


def test_nct_ids_unique(demo_trials_path):
    df = pd.read_csv(demo_trials_path)
    assert df["nct_id"].nunique() == len(df)


def test_completion_rate_range(demo_trials_path):
    df = pd.read_csv(demo_trials_path)
    assert df["completion_rate"].between(0, 1, inclusive="both").all()
