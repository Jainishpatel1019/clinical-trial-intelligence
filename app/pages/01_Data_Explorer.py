"""Data explorer - browse and filter clinical trials."""

import sys, os

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.data.schema import (
    get_connection,
    get_table_stats,
    initialize_schema,
    load_demo_data,
)
from src.data.ingestor import TrialIngestor
from src.data.validator import TrialValidator
from app.theme import inject_theme

st.set_page_config(page_title="Data Explorer", page_icon="📊", layout="wide")
inject_theme()

if "demo_loaded" not in st.session_state:
    conn = get_connection()
    try:
        try:
            count = conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
            if count == 0:
                raise RuntimeError("Empty")
            st.session_state["demo_loaded"] = True
        except Exception:
            if os.path.exists("data/processed/demo_trials.csv"):
                initialize_schema(conn)
                n = load_demo_data(conn)
                st.session_state["demo_loaded"] = True
                st.success(f"✅ Auto-loaded {n:,} demo trials")
    finally:
        conn.close()

_LIVE_CONDITIONS = [
    "Type 2 Diabetes",
    "Breast Cancer",
    "Hypertension",
    "Alzheimer Disease",
    "COPD",
    "Major Depressive Disorder",
]


def _run_live_ingest(conditions: list[str], max_per: int) -> dict:
    """Fetch real trials from ClinicalTrials.gov and upsert into DuckDB."""
    ingestor = TrialIngestor()
    result = ingestor.ingest_live(conditions, max_per_condition=max_per)
    load_data.clear()
    return result


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    conn = get_connection()
    df = conn.execute("SELECT * FROM trials").df()
    conn.close()
    return df


try:
    df = load_data()
except Exception:
    st.error("Please run: python scripts/generate_demo_data.py first")
    st.stop()

with st.sidebar:
    st.header("Filters")
    condition_filter = st.multiselect(
        "Condition",
        options=sorted(df["condition"].unique()),
        default=sorted(df["condition"].unique()),
    )
    phase_filter = st.multiselect(
        "Phase",
        options=["Phase 1", "Phase 2", "Phase 3", "Phase 4"],
        default=["Phase 2", "Phase 3"],
    )
    status_filter = st.multiselect(
        "Status",
        options=sorted(df["overall_status"].unique()),
        default=["Completed"],
    )
    min_enrollment = st.number_input(
        "Min Enrollment", min_value=0, max_value=5000, value=0, step=50
    )
    st.divider()
    st.caption(f"Total rows in DB: {len(df):,}")

    st.divider()
    with st.expander("Fetch real ClinicalTrials.gov data", expanded=False):
        st.caption(
            "Pull live trials from the public API. "
            "No API key needed. ClinicalTrials.gov is free and open."
        )
        live_conditions = st.multiselect(
            "Conditions to fetch",
            options=_LIVE_CONDITIONS,
            default=["Type 2 Diabetes", "Breast Cancer"],
            key="live_cond",
        )
        max_per_condition = st.slider(
            "Max trials per condition", 50, 500, 200, step=50, key="live_max"
        )
        if st.button("🌐 Fetch from ClinicalTrials.gov", use_container_width=True):
            if not live_conditions:
                st.warning("Select at least one condition.")
            else:
                try:
                    with st.spinner(f"Fetching trials for {len(live_conditions)} conditions..."):
                        result = _run_live_ingest(live_conditions, max_per_condition)
                except Exception as exc:
                    st.error(f"Network request failed: {exc}")
                    st.caption(
                        "Make sure you have internet access. "
                        "ClinicalTrials.gov may also be temporarily unavailable."
                    )
                    result = None

                if result is not None:
                    if result["errors"]:
                        for e in result["errors"]:
                            st.error(e)
                    if result["total_ingested"] > 0:
                        st.success(
                            f"✅ Ingested **{result['total_ingested']:,}** real trials "
                            f"({', '.join(f'{k}: {v}' for k, v in result['by_condition'].items())})"
                        )
                        st.rerun()
                    else:
                        st.warning("No trials returned. Check your network connection.")

filtered = df[
    df["condition"].isin(condition_filter)
    & df["phase"].isin(phase_filter)
    & df["overall_status"].isin(status_filter)
    & (df["enrollment_count"] >= min_enrollment)
]

if filtered.empty:
    st.warning("No trials match your filters. Try adjusting the sidebar.")
    st.stop()

st.markdown('<div class="cti-section-label">Data Explorer</div>', unsafe_allow_html=True)
st.title("📊 Browse Clinical Trials")
st.caption(f"Showing {len(filtered):,} of {len(df):,} trials from the database")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Trials Found", f"{len(filtered):,}")
col2.metric("Typical Size", f"{int(filtered['enrollment_count'].median()):,} patients")
col3.metric("Typical Length", f"{int(filtered['trial_duration_days'].median())} days")
col4.metric("Finish Rate", f"{filtered['completion_rate'].mean():.0%}")

left, right = st.columns(2)
with left:
    plot_df = filtered[filtered["enrollment_count"] >= 1].copy()
    fig_hist = px.histogram(
        plot_df,
        x="enrollment_count",
        color="phase",
        log_x=True,
        title="How Many Patients Per Trial",
        template="plotly_white",
        labels={"enrollment_count": "Number of patients (log scale)", "count": "Number of trials"},
    )
    fig_hist.update_xaxes(title_text="Number of patients (log scale)")
    fig_hist.update_yaxes(title_text="Number of trials")
    st.plotly_chart(fig_hist, use_container_width=True)
with right:
    phase_counts = filtered["phase"].value_counts().reset_index()
    phase_counts.columns = ["phase", "count"]
    fig_bar = px.bar(
        phase_counts,
        x="phase",
        y="count",
        color="phase",
        title="Trial Count by Phase",
        template="plotly_white",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

fig_scatter = px.scatter(
    filtered,
    x="trial_duration_days",
    y="enrollment_count",
    color="phase",
    size_max=8,
    opacity=0.6,
    hover_data=["brief_title", "nct_id", "overall_status"],
    title="Bigger Trials Take Longer",
    template="plotly_white",
)
st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown('<div class="cti-section-label">Raw data</div>', unsafe_allow_html=True)
display_cols = [
    "nct_id",
    "brief_title",
    "condition",
    "phase",
    "overall_status",
    "enrollment_count",
    "trial_duration_days",
    "completion_rate",
]
st.dataframe(
    filtered[display_cols].reset_index(drop=True),
    use_container_width=True,
    height=400,
)
csv = filtered[display_cols].to_csv(index=False)
st.download_button("⬇️ Download CSV", csv, "trials.csv", "text/csv")

with st.expander("Data quality check"):
    validator = TrialValidator()
    result = validator.validate(filtered)
    if result["passed"]:
        st.success(f"All {result['total_rules']} quality checks passed")
    else:
        st.warning(
            f"{len(result['failed_rules'])} issue(s): "
            f"{', '.join(result['failed_rules'])}"
        )
