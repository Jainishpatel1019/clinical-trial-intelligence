"""Report Generator page for PDF/HTML trial intelligence briefs."""

import streamlit as st
import pandas as pd
from contextlib import contextmanager
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.data.schema import get_connection
from src.reporting.generator import ReportGenerator

st.set_page_config(page_title="Report Generator", page_icon="📄", layout="wide")

st.title("📄 Insight Report Generator")
st.markdown(
    "Auto-generate a **PDF brief** from your causal analysis and simulation results."
)

st.subheader("Prerequisites")
checks = {
    "Trial data loaded": True,
    "Causal model fitted": "hte_results" in st.session_state,
    "Simulation run": "sim_results" in st.session_state,
}
for label, ok in checks.items():
    if ok:
        st.success(f"✅ {label}")
    else:
        if label == "Causal model fitted":
            st.warning(
                f"⚠️ **{label}** — Open **Causal Analysis** in the sidebar, "
                "configure filters, and click **Run Causal Analysis**."
            )
        elif label == "Simulation run":
            st.warning(
                f"⚠️ **{label}** — Open **Trial Simulator** in the sidebar "
                "and click **Run Simulation**."
            )
        else:
            st.warning(f"⚠️ **{label}**")

st.divider()
st.subheader("Report configuration")
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
    "⚡ Generate PDF Report", type="primary", use_container_width=True
)


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
            st.write("📄 Converting to PDF...")
            pdf_bytes = generator.generate_pdf(data)
            if status is not None:
                status.update(label="✅ Report ready!", state="complete")

            st.success("Report generated successfully!")
            filename = (
                f"trial_intelligence_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            st.session_state["last_pdf_bytes"] = pdf_bytes
            st.session_state["last_pdf_name"] = filename
            st.session_state["last_report_html"] = generator.render_html(data)

        except ImportError:
            if status is not None:
                status.update(label="WeasyPrint not available", state="error")
            st.warning(
                "PDF generation requires WeasyPrint. Install it with: `pip install weasyprint`"
            )
            st.markdown("**HTML Preview (download as HTML instead):**")
            html_string = generator.render_html(data)
            st.session_state["last_report_html"] = html_string
            st.download_button(
                "⬇️ Download HTML Report",
                html_string,
                f"report_{datetime.now().strftime('%Y%m%d')}.html",
                "text/html",
                use_container_width=True,
            )
        except Exception as e:
            if status is not None:
                status.update(label="Error", state="error")
            st.error(f"Report generation failed: {e}")
            with st.expander("Error details"):
                st.exception(e)

if st.session_state.get("last_pdf_bytes"):
    st.download_button(
        label="⬇️ Download PDF Report",
        data=st.session_state["last_pdf_bytes"],
        file_name=st.session_state.get(
            "last_pdf_name",
            "trial_intelligence_report.pdf",
        ),
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        key="dl_pdf_persistent",
    )

with st.expander("📋 Report sections preview"):
    st.markdown(
        """
The PDF report includes:

1. **Executive Summary** — 4 auto-generated key findings  
2. **Data Overview** — Trials table by phase with enrollment and completion stats  
3. **Causal Analysis** — ATE with confidence intervals, subgroup effects table, top feature drivers  
4. **Adaptive Simulation** — Traditional vs Adaptive comparison table  
5. **AI Insights** — RAG-generated answers grounded in trial data (or defaults from this page)  
6. **Methodology** — Technical description of all models used  
"""
    )
