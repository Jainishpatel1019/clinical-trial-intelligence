"""Tests for TrialIngestor.parse_raw — no network calls."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.ingestor import TrialIngestor


@pytest.fixture
def raw_df():
    """Minimal raw DataFrame mimicking ClinicalTrials.gov API output."""
    return pd.DataFrame(
        {
            "NCTId": ["NCT00000001", "NCT00000002", "NCT00000003"],
            "BriefTitle": [
                "A Randomized Study of Drug X",
                "Observational cohort of Y",
                "Phase 3 Randomized Trial of Z",
            ],
            "OverallStatus": ["COMPLETED", "RECRUITING", "ACTIVE_NOT_RECRUITING"],
            "Phase": [["PHASE2"], ["PHASE3"], ["PHASE1"]],
            "EnrollmentCount": [200, 500, None],
            "StartDate": ["2020-01-15", "2021-06-01", "2019-03-10"],
            "CompletionDate": ["2022-01-15", None, "2023-03-10"],
            "EligibilityCriteria": [
                "Age 18 years or older",
                "Minimum age 40",
                "Aged 65 to 80 years",
            ],
            "InterventionName": ["Drug X", "Observation", "Drug Z"],
            "PrimaryOutcomeMeasure": ["Survival", "HbA1c", "Response rate"],
            "LeadSponsorName": ["Pharma Inc", "University", "Biotech Co"],
            "lookup_condition": ["Breast Cancer", "Type 2 Diabetes", "Hypertension"],
            "_eligibility_module": [
                {"minimumAge": "18 Years", "maximumAge": "75 Years", "sex": "ALL"},
                {"minimumAge": "40 Years", "sex": "FEMALE"},
                {"minimumAge": "65 Years", "maximumAge": "80 Years"},
            ],
            "_has_results": [True, False, None],
        }
    )


def test_parse_raw_returns_correct_columns(raw_df):
    ingestor = TrialIngestor.__new__(TrialIngestor)
    parsed = ingestor.parse_raw(raw_df)
    expected_cols = {
        "nct_id", "brief_title", "condition", "phase", "overall_status",
        "enrollment_count", "start_date", "completion_date",
        "min_age_years", "max_age_years", "sex", "is_randomized",
        "is_blinded", "has_results", "trial_duration_days",
        "enrollment_log", "phase_numeric", "completion_rate",
        "is_oncology", "is_cardiovascular", "age_group",
    }
    assert expected_cols.issubset(set(parsed.columns))


def test_parse_raw_detects_randomized(raw_df):
    ingestor = TrialIngestor.__new__(TrialIngestor)
    parsed = ingestor.parse_raw(raw_df)
    assert parsed.loc[0, "is_randomized"] == True   # "Randomized" in title
    assert parsed.loc[1, "is_randomized"] == False


def test_parse_raw_normalizes_phase(raw_df):
    ingestor = TrialIngestor.__new__(TrialIngestor)
    parsed = ingestor.parse_raw(raw_df)
    assert parsed.loc[0, "phase"] == "Phase 2"
    assert parsed.loc[1, "phase"] == "Phase 3"
    assert parsed.loc[2, "phase"] == "Phase 1"


def test_parse_raw_normalizes_status(raw_df):
    ingestor = TrialIngestor.__new__(TrialIngestor)
    parsed = ingestor.parse_raw(raw_df)
    assert parsed.loc[0, "overall_status"] == "Completed"
    assert parsed.loc[1, "overall_status"] == "Recruiting"
    assert parsed.loc[2, "overall_status"] == "Active, not recruiting"


def test_parse_raw_extracts_ages(raw_df):
    ingestor = TrialIngestor.__new__(TrialIngestor)
    parsed = ingestor.parse_raw(raw_df)
    assert parsed.loc[0, "min_age_years"] == 18.0
    assert parsed.loc[0, "max_age_years"] == 75.0
    assert parsed.loc[2, "min_age_years"] == 65.0


def test_parse_raw_detects_oncology(raw_df):
    ingestor = TrialIngestor.__new__(TrialIngestor)
    parsed = ingestor.parse_raw(raw_df)
    assert parsed.loc[0, "is_oncology"] == True   # Breast Cancer
    assert parsed.loc[1, "is_oncology"] == False   # Diabetes


def test_parse_raw_handles_empty():
    ingestor = TrialIngestor.__new__(TrialIngestor)
    parsed = ingestor.parse_raw(pd.DataFrame())
    assert len(parsed) == 0
    assert "nct_id" in parsed.columns
