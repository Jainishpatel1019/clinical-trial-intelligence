"""Tests for causal / HTE components (no external API calls)."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """100-row frame with all columns required by PropensityScorer and HTEModel."""
    np.random.seed(42)
    n = 100
    rng = np.random.default_rng(42)
    treated = np.array([True] * 50 + [False] * 50)
    rng.shuffle(treated)

    enrollment_log = rng.normal(6.0, 0.4, n).clip(3.0, 9.0)
    enrollment_log = np.where(treated, enrollment_log + 0.35, enrollment_log)

    phase_numeric = rng.integers(1, 4, size=n)
    min_age = rng.integers(18, 65, size=n).astype(float)
    max_age = np.minimum(
        min_age + rng.integers(10, 40, size=n).astype(float), 90.0
    )
    is_onc = rng.random(n) < 0.25
    is_cardio = (~is_onc) & (rng.random(n) < 0.2)

    completion_rate = rng.uniform(0.35, 0.92, n)
    completion_rate = np.where(treated, completion_rate + 0.03, completion_rate).clip(
        0.0, 1.0
    )

    conditions = np.array(["Diabetes", "Hypertension", "Breast Cancer"])
    age_labels = np.array(["Young", "Middle", "Senior"])
    cond = conditions[rng.integers(0, 3, size=n)]
    age_group = age_labels[rng.integers(0, 3, size=n)]

    return pd.DataFrame(
        {
            "completion_rate": completion_rate,
            "is_randomized": treated,
            "enrollment_log": enrollment_log,
            "phase_numeric": phase_numeric,
            "min_age_years": min_age,
            "max_age_years": max_age,
            "is_oncology": is_onc,
            "is_cardiovascular": is_cardio,
            "trial_duration_days": rng.integers(180, 900, size=n).astype(float),
            "condition": cond,
            "age_group": age_group,
        }
    )


def test_propensity_scorer_fits(sample_df):
    from src.causal.propensity import PropensityScorer

    scorer = PropensityScorer()
    result = scorer.fit(sample_df)
    assert "auc_roc" in result
    assert 0 <= result["auc_roc"] <= 1
    assert "overlap_ok" in result


def test_hte_model_fits(sample_df):
    from src.causal.hte_model import HTEModel

    model = HTEModel()
    result = model.fit(sample_df)
    assert "ate" in result
    assert isinstance(result["ate"], float)
    assert not np.isnan(result["ate"])
    assert result["n_samples"] > 0


def test_hte_model_requires_min_rows():
    from src.causal.hte_model import HTEModel

    tiny_df = pd.DataFrame(
        {
            "completion_rate": [0.5] * 10,
            "is_randomized": [True] * 5 + [False] * 5,
            "enrollment_log": [5.0] * 10,
            "phase_numeric": [2] * 10,
            "min_age_years": [40.0] * 10,
            "max_age_years": [70.0] * 10,
            "is_oncology": [False] * 10,
            "is_cardiovascular": [False] * 10,
            "trial_duration_days": [365] * 10,
            "condition": ["Diabetes"] * 10,
            "age_group": ["Middle"] * 10,
        }
    )
    model = HTEModel()
    with pytest.raises(ValueError, match="at least 50 rows"):
        model.fit(tiny_df)
