"""Tests for DuckDB schema helpers."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.schema import get_connection, get_table_stats, initialize_schema, load_demo_data


def test_initialize_schema_creates_table(tmp_path):
    db = str(tmp_path / "test.duckdb")
    conn = get_connection(db)
    initialize_schema(conn)
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    assert "trials" in table_names
    conn.close()


def test_get_table_stats_on_empty(tmp_path):
    db = str(tmp_path / "test.duckdb")
    conn = get_connection(db)
    initialize_schema(conn)
    stats = get_table_stats(conn)
    assert stats["total_trials"] == 0
    assert stats["conditions"] == []
    conn.close()


def test_load_demo_data_populates_table():
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "processed", "demo_trials.csv"
    )
    if not os.path.exists(csv_path):
        pytest.skip("demo_trials.csv not generated yet")
    conn = get_connection(":memory:")
    initialize_schema(conn)
    n = load_demo_data(conn, csv_path)
    assert n == 300
    stats = get_table_stats(conn)
    assert stats["total_trials"] == 300
    assert len(stats["conditions"]) > 0
    conn.close()
