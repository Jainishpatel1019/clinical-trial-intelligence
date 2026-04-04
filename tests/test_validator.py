"""Tests for the TrialValidator clean/validate logic."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.validator import TrialValidator


@pytest.fixture
def validator():
    return TrialValidator()


@pytest.fixture
def valid_df():
    return pd.DataFrame(
        {
            "nct_id": [f"NCT{i:07d}" for i in range(10)],
            "brief_title": [f"Study {i}" for i in range(10)],
            "condition": ["Diabetes"] * 10,
            "phase": ["Phase 2"] * 10,
            "overall_status": ["Completed"] * 10,
            "enrollment_count": [100 + i * 10 for i in range(10)],
            "start_date": pd.to_datetime(["2020-01-01"] * 10),
            "completion_date": pd.to_datetime(["2022-01-01"] * 10),
            "completion_rate": [0.5 + i * 0.04 for i in range(10)],
            "is_randomized": [True] * 5 + [False] * 5,
        }
    )


def test_valid_data_passes(validator, valid_df):
    result = validator.validate(valid_df)
    assert result["passed"] is True
    assert result["total_rules"] == 7
    assert result["passed_rules"] == 7


def test_duplicate_nct_ids_fail(validator, valid_df):
    bad = valid_df.copy()
    bad.loc[1, "nct_id"] = bad.loc[0, "nct_id"]
    result = validator.validate(bad)
    assert result["passed"] is False
    assert any("duplicate" in r.lower() for r in result["failed_rules"])


def test_null_nct_id_fails(validator, valid_df):
    bad = valid_df.copy()
    bad.loc[0, "nct_id"] = None
    result = validator.validate(bad)
    assert result["passed"] is False


def test_negative_enrollment_fails(validator, valid_df):
    bad = valid_df.copy()
    bad.loc[0, "enrollment_count"] = -5
    result = validator.validate(bad)
    assert result["passed"] is False


def test_clean_fills_nulls(validator):
    df = pd.DataFrame(
        {
            "nct_id": ["NCT0000001", "NCT0000002", None],
            "enrollment_count": [100, None, 200],
            "phase": ["Phase 1", None, "Phase 3"],
            "completion_rate": [0.8, None, 0.6],
            "condition": ["A", "B", "C"],
        }
    )
    cleaned = validator.clean(df)
    assert len(cleaned) == 2  # null nct_id row dropped
    assert cleaned["enrollment_count"].isna().sum() == 0
    assert cleaned["phase"].isna().sum() == 0
    assert cleaned["completion_rate"].isna().sum() == 0


def test_clean_clips_enrollment(validator):
    df = pd.DataFrame(
        {
            "nct_id": ["NCT0000001"],
            "enrollment_count": [999999],
            "phase": ["Phase 2"],
            "completion_rate": [1.5],
        }
    )
    cleaned = validator.clean(df)
    assert cleaned["enrollment_count"].iloc[0] <= 50000
    assert cleaned["completion_rate"].iloc[0] <= 1.0
