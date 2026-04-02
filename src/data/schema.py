"""DuckDB schema helpers: connections, table DDL, demo loads, stats, and ad-hoc queries."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TypedDict

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


class DateRangeDict(TypedDict):
    """Min/max date strings describing trial activity span."""

    min: str
    max: str


class TableStatsDict(TypedDict):
    """Aggregated metadata for the trials table."""

    total_trials: int
    conditions: list[str]
    phases: list[str]
    date_range: DateRangeDict
    last_updated: str


def get_connection(db_path: str = "data/trials.duckdb") -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection, ensuring the database parent directory exists."""
    path = Path(os.path.expanduser(db_path))
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def initialize_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create core tables if they do not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trials (
            nct_id VARCHAR PRIMARY KEY,
            brief_title VARCHAR,
            condition VARCHAR,
            phase VARCHAR,
            overall_status VARCHAR,
            enrollment_count INTEGER,
            start_date DATE,
            completion_date DATE,
            min_age_years FLOAT,
            max_age_years FLOAT,
            sex VARCHAR,
            is_randomized BOOLEAN,
            is_blinded BOOLEAN,
            has_results BOOLEAN,
            trial_duration_days INTEGER,
            enrollment_log FLOAT,
            phase_numeric INTEGER,
            completion_rate FLOAT,
            is_oncology BOOLEAN,
            is_cardiovascular BOOLEAN,
            age_group VARCHAR,
            ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _insert_trials_from_registered_df(
    conn: duckdb.DuckDBPyConnection, *, use_replace: bool
) -> None:
    """Run INSERT (optionally OR REPLACE) from ``_load_demo_trials_df`` into ``trials``."""
    replace_kw = " OR REPLACE" if use_replace else ""
    conn.execute(
        f"""
        INSERT{replace_kw} INTO trials (
            nct_id,
            brief_title,
            condition,
            phase,
            overall_status,
            enrollment_count,
            start_date,
            completion_date,
            min_age_years,
            max_age_years,
            sex,
            is_randomized,
            is_blinded,
            has_results,
            trial_duration_days,
            enrollment_log,
            phase_numeric,
            completion_rate,
            is_oncology,
            is_cardiovascular,
            age_group
        )
        SELECT
            nct_id,
            brief_title,
            condition,
            phase,
            overall_status,
            enrollment_count,
            start_date,
            completion_date,
            min_age_years,
            max_age_years,
            sex,
            is_randomized,
            is_blinded,
            has_results,
            trial_duration_days,
            enrollment_log,
            phase_numeric,
            completion_rate,
            is_oncology,
            is_cardiovascular,
            age_group
        FROM _load_demo_trials_df
        """
    )


def load_demo_data(
    conn: duckdb.DuckDBPyConnection,
    csv_path: str = "data/processed/demo_trials.csv",
) -> int:
    """Load rows from a CSV into ``trials`` using INSERT OR REPLACE; return rows loaded."""
    df = pd.read_csv(
        csv_path,
        parse_dates=["start_date", "completion_date"],
    )
    n = len(df)
    conn.register("_load_demo_trials_df", df)
    try:
        try:
            _insert_trials_from_registered_df(conn, use_replace=True)
        except duckdb.BinderException as exc:
            if "PRIMARY KEY" not in str(exc) and "UNIQUE" not in str(exc):
                raise
            conn.execute("DELETE FROM trials")
            _insert_trials_from_registered_df(conn, use_replace=False)
    finally:
        conn.unregister("_load_demo_trials_df")
    return n


def get_table_stats(conn: duckdb.DuckDBPyConnection) -> TableStatsDict:
    """Return row counts, distinct dimensions, date span, and latest ingestion time."""
    total = conn.execute("SELECT COUNT(*) FROM trials").fetchone()
    total_trials = int(total[0]) if total else 0

    cond_rows = conn.execute(
        "SELECT DISTINCT condition FROM trials ORDER BY 1"
    ).fetchall()
    conditions = [str(r[0]) for r in cond_rows if r[0] is not None]

    phase_rows = conn.execute(
        "SELECT DISTINCT phase FROM trials ORDER BY 1"
    ).fetchall()
    phases = [str(r[0]) for r in phase_rows if r[0] is not None]

    dr = conn.execute(
        """
        SELECT
            CAST(MIN(start_date) AS VARCHAR),
            CAST(MAX(completion_date) AS VARCHAR)
        FROM trials
        """
    ).fetchone()
    date_range: DateRangeDict = {
        "min": str(dr[0]) if dr and dr[0] is not None else "",
        "max": str(dr[1]) if dr and dr[1] is not None else "",
    }

    try:
        lu = conn.execute(
            "SELECT CAST(MAX(ingestion_timestamp) AS VARCHAR) FROM trials"
        ).fetchone()
    except duckdb.BinderException:
        lu = (None,)
    last_updated = str(lu[0]) if lu and lu[0] is not None else ""

    return {
        "total_trials": total_trials,
        "conditions": conditions,
        "phases": phases,
        "date_range": date_range,
        "last_updated": last_updated,
    }


def run_query(conn: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    """Execute arbitrary SQL and return the result as a DataFrame."""
    logger.debug("query: %s", sql)
    return conn.execute(sql).df()
