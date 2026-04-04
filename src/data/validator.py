"""Dataset validation for clinical trial tables using pandas/numpy checks (no Great Expectations)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, TypedDict

import pandas as pd

logger = logging.getLogger(__name__)


class ValidationResult(TypedDict):
    """Structured output from :meth:`TrialValidator.validate`."""

    passed: bool
    total_rules: int
    passed_rules: int
    failed_rules: list[str]
    row_count: int
    null_summary: dict[str, int]


class TrialValidator:
    """Run declarative validation rules and light cleaning on trial DataFrames."""

    def __init__(self) -> None:
        """Register built-in validation rules (name, check lambda, error_message)."""
        self.rules: list[dict[str, Any]] = [
            {
                "name": "nct_id_not_null",
                "check": lambda df: df["nct_id"].notna().all(),
                "error_message": "nct_id has null values",
            },
            {
                "name": "nct_id_unique",
                "check": lambda df: df["nct_id"].nunique() == len(df),
                "error_message": "nct_id has duplicates",
            },
            {
                "name": "enrollment_positive",
                "check": lambda df: (df["enrollment_count"] > 0).all(),
                "error_message": "enrollment_count has non-positive values",
            },
            {
                "name": "enrollment_reasonable",
                "check": lambda df: (df["enrollment_count"] < 100000).all(),
                "error_message": "enrollment_count has unreasonably large values",
            },
            {
                "name": "phase_valid",
                "check": lambda df: df["phase"]
                .isin(["Phase 1", "Phase 2", "Phase 3", "Phase 4", "N/A"])
                .all(),
                "error_message": "phase has invalid values",
            },
            {
                "name": "completion_rate_range",
                "check": lambda df: df["completion_rate"].between(0, 1).all()
                if "completion_rate" in df.columns
                else True,
                "error_message": "completion_rate must be between 0 and 1",
            },
            {
                "name": "dates_mostly_present",
                "check": lambda df: (
                    df["start_date"].notna().mean() >= 0.80
                    if "start_date" in df.columns
                    else True
                ),
                "error_message": "start_date is missing in more than 20% of rows",
            },
        ]

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """Run all rules on ``df`` and return pass/fail summary plus null counts."""
        failed_rules: list[str] = []
        passed_count = 0
        for rule in self.rules:
            check_fn: Callable[[pd.DataFrame], bool] = rule["check"]
            ok = bool(check_fn(df))
            if ok:
                passed_count += 1
            else:
                failed_rules.append(rule["error_message"])
                logger.warning(
                    "Validation failed [%s]: %s", rule["name"], rule["error_message"]
                )

        total = len(self.rules)
        null_summary = {
            str(col): int(df[col].isna().sum())
            for col in df.columns
            if df[col].isna().any()
        }

        return {
            "passed": len(failed_rules) == 0,
            "total_rules": total,
            "passed_rules": passed_count,
            "failed_rules": failed_rules,
            "row_count": int(len(df)),
            "null_summary": null_summary,
        }

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy with standard imputations and bounds for trial fields."""
        out = df.copy()
        out = out.loc[out["nct_id"].notna()].copy()

        med = out["enrollment_count"].median()
        if pd.isna(med):
            med = 1.0
        out["enrollment_count"] = out["enrollment_count"].fillna(med)
        out["phase"] = out["phase"].fillna("N/A")
        if "completion_rate" in out.columns:
            out["completion_rate"] = out["completion_rate"].fillna(0.5)

        out["enrollment_count"] = out["enrollment_count"].clip(1, 50000)
        if "completion_rate" in out.columns:
            out["completion_rate"] = out["completion_rate"].clip(0, 1)

        return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    _root = Path(__file__).resolve().parent.parent.parent
    _csv = _root / "data" / "processed" / "demo_trials.csv"
    _df = pd.read_csv(_csv, parse_dates=["start_date", "completion_date"])
    _validator = TrialValidator()
    _result = _validator.validate(_df)
    print(_result)
