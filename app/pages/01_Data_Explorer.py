"""Data Explorer page for inspecting clinical trial datasets."""

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
from src.data.validator import TrialValidator

st.set_page_config(page_title="Data Explorer", page_icon="📊", layout="wide")

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

filtered = df[
    df["condition"].isin(condition_filter)
    & df["phase"].isin(phase_filter)
    & df["overall_status"].isin(status_filter)
    & (df["enrollment_count"] >= min_enrollment)
]

if filtered.empty:
    st.warning("No trials match your filters. Try adjusting the sidebar.")
    st.stop()

st.title("📊 Clinical Trial Data Explorer")
st.caption(f"Showing {len(filtered):,} of {len(df):,} trials")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Trials", f"{len(filtered):,}")
col2.metric("Median Enrollment", f"{int(filtered['enrollment_count'].median()):,}")
col3.metric("Median Duration", f"{int(filtered['trial_duration_days'].median())} days")
col4.metric("Avg Completion Rate", f"{filtered['completion_rate'].mean():.1%}")

left, right = st.columns(2)
with left:
    fig_hist = px.histogram(
        filtered,
        x="enrollment_count",
        color="phase",
        log_x=True,
        title="Enrollment Distribution (log scale)",
        template="plotly_white",
    )
    st.plotly_chart(fig_hist, use_container_width=True)
with right:
    phase_counts = filtered["phase"].value_counts().reset_index()
    phase_counts.columns = ["phase", "count"]
    fig_bar = px.bar(
        phase_counts,
        x="phase",
        y="count",
        color="phase",
        title="Trials by Phase",
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
    title="Enrollment vs Trial Duration by Phase",
    template="plotly_white",
)
st.plotly_chart(fig_scatter, use_container_width=True)

st.subheader("Trial Details")
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

validator = TrialValidator()
result = validator.validate(filtered)
if result["passed"]:
    st.success(f"✅ Data quality: All {result['total_rules']} checks passed")
else:
    st.error(
        f"⚠️ Data quality: {len(result['failed_rules'])} checks failed: "
        f"{', '.join(result['failed_rules'])}"
    )
