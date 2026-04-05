"""Report generator - exports analysis results as PDF or HTML."""

import streamlit as st
import pandas as pd
from contextlib import contextmanager
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.data.schema import get_connection
from src.reporting.generator import ReportGenerator
from app.theme import inject_theme

st.set_page_config(page_title="Report Generator", page_icon="📄", layout="wide")
inject_theme()


def _report_hte_ready() -> bool:
    r = st.session_state.get("hte_results")
    return isinstance(r, dict) and bool(r)


def _report_sim_ready() -> bool:
    r = st.session_state.get("sim_results")
    return isinstance(r, dict) and "trad" in r and "adapt" in r


st.markdown('<div class="cti-section-label">Reports</div>', unsafe_allow_html=True)
st.title("📄 Download Your Findings")
st.caption("Generate a PDF report with your analysis results. Ready to share with your team.")

with st.expander("Checklist - what do you need before generating?", expanded=False):
    checks = {
        "Trial data loaded": True,
        "Analysis complete": _report_hte_ready(),
        "Simulation complete": _report_sim_ready(),
    }
    for label, ok in checks.items():
        if ok:
            st.success(f"✅ {label}")
        else:
            st.info(f"⬜ {label} - complete this step first")

st.markdown('<div class="cti-section-label">Configure</div>', unsafe_allow_html=True)
col_l, col_r = st.columns(2)
with col_l:
    report_title = st.text_input(
        "Report Title", value="Clinical Trial Intelligence Brief"
    )
    author_name = st.text_input("Author Name", value="Data Scientist")
    condition_display = st.text_input(
        "Condition / Study Area",
        value="Type 2 Diabetes, Hypertension, Breast Cancer",
    )
with col_r:
    st.markdown("**Include sections**")
    exec_summary = st.checkbox("Executive summary", value=True)
    causal = st.checkbox("Causal analysis", value=True)
    simulation = st.checkbox("Adaptive simulation", value=True)
    insights = st.checkbox("AI insights", value=True)
    methodology = st.checkbox("Methodology", value=True)
    outcome_variable = st.selectbox(
        "Outcome Variable", ["completion_rate", "trial_duration_days"]
    )
    n_insights = st.slider("Number of AI insights to include", 1, 5, 3)

gen_button = st.button(
    "⚡ Generate Report", type="primary", use_container_width=True
)

with st.expander("Enable direct PDF generation"):
    st.markdown("If you see an HTML fallback, install WeasyPrint in your terminal:")
    st.code("pip install weasyprint", language="bash")
    st.caption("Run this in your terminal to enable direct PDF generation")


@contextmanager
def _report_status(label: str):
    if hasattr(st, "status"):
        with st.status(label, expanded=True) as status:
            yield status
    else:
        st.info(label)
        yield None


if gen_button:
    conn = get_connection()
    try:
        df = conn.execute("SELECT * FROM trials").df()
    except Exception as exc:
        st.error("Could not load trials from the database.")
        st.caption(str(exc))
        st.stop()
    finally:
        conn.close()

    if df.empty:
        st.error("No trial rows found. Generate demo data or ingest trials first.")
        st.stop()

    hte_fit = st.session_state.get("hte_results")
    subgroup_df = st.session_state.get("subgroup_df", pd.DataFrame())
    if not isinstance(subgroup_df, pd.DataFrame):
        subgroup_df = pd.DataFrame()

    importance_df = st.session_state.get("importance_df")
    if not isinstance(importance_df, pd.DataFrame):
        importance_df = None

    if causal:
        hte_pack: dict = {**(hte_fit or {}), "subgroup_df": subgroup_df}
        if importance_df is not None:
            hte_pack["importance_df"] = importance_df
        hte_pack["outcome_variable"] = outcome_variable
    else:
        hte_pack = {
            "subgroup_df": pd.DataFrame(),
            "outcome_variable": outcome_variable,
        }

    sim_pack = st.session_state.get("sim_results") if simulation else None
    if isinstance(sim_pack, dict):
        sim_pack = {
            k: v
            for k, v in sim_pack.items()
            if k != "simulator"
        }

    default_insights = [
        f"Median enrollment across {len(df)} trials is "
        f"{int(df['enrollment_count'].median()):,} participants.",
        f"Phase 3 trials show "
        f"{df[df['phase'] == 'Phase 3']['completion_rate'].mean():.1%} "
        f"avg completion rate.",
        f"Randomized trials have "
        f"{df[df['is_randomized'] == True]['completion_rate'].mean():.1%} "
        f"completion rate vs "
        f"{df[df['is_randomized'] == False]['completion_rate'].mean():.1%} "
        f"for observational designs.",
    ]
    raw_insights = st.session_state.get("ai_insights", default_insights)
    if not isinstance(raw_insights, list):
        raw_insights = default_insights
    ai_insights_list = (raw_insights if insights else [])[:n_insights]

    with _report_status("Generating report...") as status:
        st.write("📊 Compiling analysis results...")
        generator = ReportGenerator()
        data = generator.compile_data(
            df=df,
            hte_results=hte_pack,
            sim_results=sim_pack,
            ai_insights=ai_insights_list,
            author_name=author_name,
        )
        data["report_title"] = report_title
        data["condition"] = condition_display
        data["outcome_variable"] = outcome_variable
        data["include_executive_summary"] = exec_summary
        data["include_causal"] = causal
        data["include_simulation"] = simulation
        data["include_ai_insights"] = insights
        data["include_methodology"] = methodology

        st.write("🖨️ Rendering HTML template...")

        try:
            st.write("📄 Converting to PDF…")
            content_bytes, fmt = generator.generate_pdf(data)
            if status is not None:
                status.update(label="✅ Report ready!", state="complete")

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            if fmt == "pdf":
                st.success("PDF generated successfully!")
                filename = f"trial_intelligence_report_{ts}.pdf"
                st.session_state["last_report_bytes"] = content_bytes
                st.session_state["last_report_name"] = filename
                st.session_state["last_report_fmt"] = "pdf"
            else:
                st.info(
                    "Downloaded as HTML. Open in Chrome and use "
                    "**File > Print > Save as PDF** for a PDF version."
                )
                filename = f"trial_intelligence_report_{ts}.html"
                st.session_state["last_report_bytes"] = content_bytes
                st.session_state["last_report_name"] = filename
                st.session_state["last_report_fmt"] = "html"

            st.session_state["last_report_html"] = generator.render_html(data)

        except Exception as e:
            if status is not None:
                status.update(label="Error", state="error")
            st.error(f"Report generation failed: {e}")
            with st.expander("Error details"):
                st.exception(e)

if st.session_state.get("last_report_bytes"):
    _fmt = st.session_state.get("last_report_fmt", "pdf")
    _mime = "application/pdf" if _fmt == "pdf" else "text/html"
    _label = "⬇️ Download PDF Report" if _fmt == "pdf" else "⬇️ Download HTML Report"
    st.download_button(
        label=_label,
        data=st.session_state["last_report_bytes"],
        file_name=st.session_state.get(
            "last_report_name",
            "trial_intelligence_report.pdf",
        ),
        mime=_mime,
        type="primary",
        use_container_width=True,
        key="dl_report_persistent",
    )
    if _fmt == "html":
        st.info(
            "Downloaded as HTML. Open in Chrome and use "
            "**File > Print > Save as PDF** for a PDF version."
        )

with st.expander("📋 Report sections preview"):
    st.markdown(
        """
The PDF report includes:

1. **Executive Summary** - key findings
2. **Data Overview** - trials by phase with enrollment and completion stats
3. **Causal Analysis** - ATE with confidence intervals, subgroup effects, top feature drivers
4. **Adaptive Simulation** - traditional vs adaptive comparison
5. **Insights** - answers grounded in trial data
6. **Methodology** - description of models used
"""
    )
