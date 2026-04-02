"""Script for generating synthetic clinical trial demo datasets."""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

N_ROWS = 300
RNG_SEED = 42

DRUGS = [
    "Metformin",
    "Lisinopril",
    "Tamoxifen",
    "Atorvastatin",
    "Insulin Glargine",
    "Amlodipine",
    "Pembrolizumab",
    "Dapagliflozin",
]
CONDITIONS = [
    "Type 2 Diabetes",
    "Hypertension",
    "Breast Cancer",
    "Heart Failure",
    "COPD",
]
TITLE_TEMPLATES = [
    "A Phase {phase} Study of {drug} in Patients with {condition}",
    "Randomized Trial of {drug} vs Placebo for {condition}",
    "Efficacy and Safety of {drug} in {condition} Patients",
]
PHASES = np.array(["Phase 1", "Phase 2", "Phase 3", "Phase 4"])
PHASE_WEIGHTS = np.array([0.15, 0.40, 0.35, 0.10])
STATUSES = np.array(
    [
        "Completed",
        "Recruiting",
        "Active, not recruiting",
        "Terminated",
    ]
)
STATUS_WEIGHTS = np.array([0.55, 0.25, 0.15, 0.05])


def _unique_nct_ids(n: int, rng: np.random.Generator) -> list[str]:
    seen: set[int] = set()
    out: list[str] = []
    while len(out) < n:
        x = int(rng.integers(10_000_000, 100_000_000))
        if x not in seen:
            seen.add(x)
            out.append(f"NCT{x:08d}")
    return out


def generate_demo_trials(n: int = N_ROWS, seed: int = RNG_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    nct_id = _unique_nct_ids(n, rng)
    condition = rng.choice(CONDITIONS, size=n)
    drug = rng.choice(DRUGS, size=n)
    phase = rng.choice(PHASES, size=n, p=PHASE_WEIGHTS)
    overall_status = rng.choice(STATUSES, size=n, p=STATUS_WEIGHTS)

    template_idx = rng.integers(0, len(TITLE_TEMPLATES), size=n)
    brief_title = np.array(
        [
            TITLE_TEMPLATES[template_idx[i]].format(
                phase=phase[i], drug=drug[i], condition=condition[i]
            )
            for i in range(n)
        ]
    )

    enrollment_count = (
        np.abs(rng.normal(500.0, 300.0, size=n)).clip(20, 3000).astype(int)
    )

    start_base = pd.Timestamp("2010-01-01")
    end_base = pd.Timestamp("2022-01-01")
    max_start_offset = (end_base - start_base).days
    start_offset_days = rng.integers(0, max_start_offset + 1, size=n)
    start_date = start_base + pd.to_timedelta(start_offset_days, unit="D")
    delta_days = rng.integers(365, 1461, size=n)
    completion_date = start_date + pd.to_timedelta(delta_days, unit="D")

    min_age_years = rng.choice(np.array([18, 25, 40, 50, 65]), size=n)
    max_age_years = min_age_years + rng.choice(np.array([20, 30, 40, 50]), size=n)

    sex = rng.choice(
        np.array(["All", "Male", "Female"]), size=n, p=[0.7, 0.15, 0.15]
    )
    is_randomized = rng.random(n) < 0.7
    is_blinded = rng.random(n) < 0.6

    u = rng.random(n)
    completed = overall_status == "Completed"
    has_results = np.where(completed, u < 0.9, u < 0.1)

    trial_duration_days = pd.Series(
        completion_date - start_date
    ).dt.days.astype(int)
    enrollment_log = np.log1p(enrollment_count)

    phase_map = {"Phase 1": 1, "Phase 2": 2, "Phase 3": 3, "Phase 4": 4}
    phase_numeric = pd.Series(phase).map(phase_map).to_numpy()

    completion_rate = np.where(
        is_randomized,
        rng.beta(8, 2, size=n),
        rng.beta(5, 4, size=n),
    )

    is_oncology = condition == "Breast Cancer"
    is_cardiovascular = np.isin(
        condition, np.array(["Hypertension", "Heart Failure"])
    )

    def _age_group(min_age: int) -> str:
        if min_age < 40:
            return "Young"
        if min_age <= 65:
            return "Middle"
        return "Senior"

    age_group = np.array([_age_group(int(m)) for m in min_age_years])

    return pd.DataFrame(
        {
            "nct_id": nct_id,
            "brief_title": brief_title,
            "condition": condition,
            "phase": phase,
            "overall_status": overall_status,
            "enrollment_count": enrollment_count,
            "start_date": start_date,
            "completion_date": completion_date,
            "min_age_years": min_age_years,
            "max_age_years": max_age_years,
            "sex": sex,
            "is_randomized": is_randomized,
            "is_blinded": is_blinded,
            "has_results": has_results,
            "trial_duration_days": trial_duration_days,
            "enrollment_log": enrollment_log,
            "phase_numeric": phase_numeric,
            "completion_rate": completion_rate,
            "is_oncology": is_oncology,
            "is_cardiovascular": is_cardiovascular,
            "age_group": age_group,
        }
    )


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "processed" / "demo_trials.csv"
    db_path = root / "data" / "trials.duckdb"

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_demo_trials()
    df.to_csv(csv_path, index=False)

    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("DROP TABLE IF EXISTS trials")
        conn.register("demo_df", df)
        conn.execute("CREATE TABLE trials AS SELECT * FROM demo_df")
        conn.unregister("demo_df")
    finally:
        conn.close()

    print(f"Generated {len(df)} trials")
    print(df[["condition", "phase", "overall_status"]].value_counts().head(15))
    print(
        f"Enrollment range: {df.enrollment_count.min()} - {df.enrollment_count.max()}"
    )


if __name__ == "__main__":
    main()
