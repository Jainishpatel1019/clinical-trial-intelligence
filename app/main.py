"""Streamlit entrypoint for the Clinical Trial Intelligence application."""

import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.data.schema import get_connection, get_table_stats

st.set_page_config(
    page_title="Clinical Trial Intelligence Platform",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main .block-container { padding-top: 2rem; }
    .stMetric { background: #f8f9fa; border-radius: 8px; padding: 16px; border-left: 4px solid #1e3a5f; }
    div[data-testid="metric-container"] { background: #f8f9fa; border-radius: 8px; padding: 12px; border-left: 3px solid #1e3a5f; }
    .hero-title { font-size: 2.5rem; font-weight: 700; color: #1e3a5f; margin-bottom: 0.5rem; }
    .hero-sub { font-size: 1.1rem; color: #555; margin-bottom: 1.5rem; }
    .tech-badge { display: inline-block; background: #e8f0fe; color: #1e3a5f; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; margin: 3px; font-weight: 500; }
    footer { visibility: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

defaults = {
    "messages": [],
    "hte_model": None,
    "hte_results": None,
    "sim_results": None,
    "subgroup_df": None,
    "pending_question": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.markdown(
    '<div class="hero-title">🧬 Clinical Trial Intelligence Platform</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-sub">End-to-end causal inference, adaptive simulation, and GenAI-powered insights on public clinical trial data</div>',
    unsafe_allow_html=True,
)

badges = [
    "Python 3.11",
    "EconML Causal Forest",
    "Bayesian Simulation",
    "RAG + Claude API",
    "DuckDB",
    "FAISS",
    "Streamlit",
]
badge_html = " ".join([f'<span class="tech-badge">{b}</span>' for b in badges])
st.markdown(badge_html, unsafe_allow_html=True)
st.divider()

conn = None
try:
    conn = get_connection()
    stats = get_table_stats(conn)
    cols = st.columns(4)
    cols[0].metric("Trials in Database", f"{stats['total_trials']:,}")
    cols[1].metric("Conditions", str(len(stats["conditions"])))
    dr = stats.get("date_range") or {}
    cols[2].metric(
        "Date Range",
        f"{dr.get('min', '—')} – {dr.get('max', '—')}",
    )
    lu = stats.get("last_updated") or ""
    cols[3].metric("Last Updated", lu if lu else "Unknown")
except Exception:
    st.info(
        "📂 No data loaded yet. Demo data will auto-load when you visit the Data Explorer page."
    )
finally:
    if conn is not None:
        conn.close()

st.subheader("How It Works")
steps = [
    (
        "1️⃣",
        "Load Data",
        "Pull trials from ClinicalTrials.gov API or use 300 pre-loaded demo trials",
    ),
    (
        "2️⃣",
        "Causal Analysis",
        "EconML Causal Forest estimates treatment effects across patient subgroups",
    ),
    (
        "3️⃣",
        "Simulate Trials",
        "Thompson Sampling shows how adaptive allocation beats fixed designs",
    ),
    (
        "4️⃣",
        "Ask Questions",
        "RAG pipeline answers natural language questions grounded in trial data",
    ),
    (
        "5️⃣",
        "Generate Report",
        "One-click PDF brief with all findings, ready to share",
    ),
]
cols = st.columns(5)
for col, (icon, title, desc) in zip(cols, steps):
    col.markdown(f"### {icon} {title}")
    col.caption(desc)

st.sidebar.markdown("## 🧬 Trial Intelligence")
st.sidebar.markdown("Navigate using the pages above.")
st.sidebar.divider()
demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
if demo_mode:
    st.sidebar.info("📊 Demo Mode: Using 300 synthetic trials")
else:
    st.sidebar.success("🌐 Live Mode: ClinicalTrials.gov API")
st.sidebar.divider()
st.sidebar.markdown("[GitHub](https://github.com) | [HuggingFace](https://huggingface.co)")
