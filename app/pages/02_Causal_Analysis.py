"""Causal Analysis page for treatment effect exploration workflows."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.data.schema import get_connection
from src.causal.hte_model import HTEModel
from src.causal.propensity import PropensityScorer
from src.causal.shap_analysis import SHAPAnalyzer

st.set_page_config(page_title="Causal Analysis", page_icon="🔬", layout="wide")


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    conn = get_connection()
    out = conn.execute("SELECT * FROM trials").df()
    conn.close()
    return out


try:
    df = load_data()
except Exception:
    st.error("Please run: python scripts/generate_demo_data.py first")
    st.stop()

with st.sidebar:
    condition_options = sorted(df["condition"].dropna().unique().tolist())
    condition_filter = st.multiselect(
        "Condition",
        options=condition_options,
        default=condition_options,
    )
    selected_outcome = st.selectbox(
        "Outcome",
        ["completion_rate", "trial_duration_days"],
        index=0,
    )
    st.divider()
    run_button = st.button(
        "▶ Run Causal Analysis", type="primary", use_container_width=True
    )
    st.caption("⏱ Takes ~15 seconds on demo data")

st.title("🔬 Heterogeneous Treatment Effect Analysis")
st.markdown(
    "Using **EconML Causal Forest** to estimate how randomization affects trial "
    "completion across patient subgroups."
)

filtered_df = df[df["condition"].isin(condition_filter)]

if run_button or "hte_results" in st.session_state:
    if run_button:
        if len(filtered_df) < 50:
            st.error(
                "Need at least 50 trials after filtering to fit the causal model. "
                "Broaden the condition filter."
            )
        else:
            with st.spinner("Fitting causal forest... please wait"):
                scorer = PropensityScorer()
                ps_result = scorer.fit(filtered_df)

                model = HTEModel(outcome_col=selected_outcome)
                fit_result = model.fit(filtered_df)

                analyzer = SHAPAnalyzer(model)
                importance_df = analyzer.compute_importance()
                subgroup_df = model.estimate_subgroup_effects()

                st.session_state["hte_results"] = fit_result
                st.session_state["hte_model"] = model
                st.session_state["ps_result"] = ps_result
                st.session_state["scorer"] = scorer
                st.session_state["importance_df"] = importance_df
                st.session_state["subgroup_df"] = subgroup_df
                st.session_state["analyzer"] = analyzer
                st.session_state["hte_outcome"] = selected_outcome

    if "hte_results" not in st.session_state:
        st.info(
            "Configure your analysis in the sidebar and click **Run Causal Analysis**."
        )
        st.stop()

    fit_result = st.session_state["hte_results"]
    ps_result = st.session_state["ps_result"]
    scorer = st.session_state["scorer"]
    importance_df = st.session_state["importance_df"]
    subgroup_df = st.session_state["subgroup_df"]
    analyzer = st.session_state["analyzer"]
    outcome_label = st.session_state.get("hte_outcome", selected_outcome)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Average Treatment Effect",
        f"{fit_result['ate']:+.3f}",
        delta=(
            f"95% CI [{fit_result['ate_lower']:+.3f}, "
            f"{fit_result['ate_upper']:+.3f}]"
        ),
    )
    m2.metric("Samples Analyzed", f"{fit_result['n_samples']:,}")
    m3.metric("Randomized Trials", f"{fit_result['n_treated']:,}")
    m4.metric(
        "Overlap Check",
        "✅ PASS" if ps_result["overlap_ok"] else "❌ FAIL",
    )

    c_left, c_right = st.columns(2)
    with c_left:
        st.plotly_chart(scorer.plot_overlap(), use_container_width=True)
    with c_right:
        st.plotly_chart(
            analyzer.plot_effect_distribution(),
            use_container_width=True,
        )

    st.plotly_chart(
        analyzer.plot_importance(importance_df),
        use_container_width=True,
    )

    st.subheader("Treatment Effects by Subgroup")
    col_tbl, col_forest = st.columns([0.6, 0.4])

    with col_tbl:
        if subgroup_df.empty:
            st.warning("No subgroup summaries met the minimum sample size (n ≥ 5).")
        else:
            try:
                styler = subgroup_df.style.map(
                    lambda v: (
                        "background-color: #d5f5e3"
                        if pd.notna(v) and float(v) > 0
                        else (
                            "background-color: #fadbd8"
                            if pd.notna(v) and float(v) < 0
                            else ""
                        )
                    ),
                    subset=["cate_mean"],
                )
            except AttributeError:
                styler = subgroup_df.style.applymap(
                    lambda v: (
                        "background-color: #d5f5e3"
                        if pd.notna(v) and float(v) > 0
                        else (
                            "background-color: #fadbd8"
                            if pd.notna(v) and float(v) < 0
                            else ""
                        )
                    ),
                    subset=["cate_mean"],
                )
            st.dataframe(styler, use_container_width=True, height=420)

    with col_forest:
        if not subgroup_df.empty:
            fig_forest = go.Figure()
            for _, row in subgroup_df.iterrows():
                label = f"{row['age_group']} / {row['condition']}"
                fig_forest.add_trace(
                    go.Scatter(
                        x=[
                            row["cate_lower"],
                            row["cate_mean"],
                            row["cate_upper"],
                        ],
                        y=[label, label, label],
                        mode="lines+markers",
                        showlegend=False,
                        line=dict(color="steelblue", width=2),
                        marker=dict(size=[5, 8, 5], color="steelblue"),
                    )
                )
            fig_forest.add_vline(
                x=0, line_dash="dash", line_color="gray", line_width=1
            )
            fig_forest.update_layout(
                title="Subgroup CATE Estimates (95% CI)",
                template="plotly_white",
                xaxis_title="CATE",
                yaxis_title="",
                margin=dict(l=160, r=40, t=60, b=40),
                height=max(320, 40 * len(subgroup_df) + 120),
            )
            st.plotly_chart(fig_forest, use_container_width=True)

    if not subgroup_df.empty and not importance_df.empty:
        top_subgroup = subgroup_df.iloc[0]
        top_feat = importance_df.iloc[0]
        if outcome_label == "completion_rate":
            ate_txt = f"{fit_result['ate']:+.1%}"
        else:
            ate_txt = f"{fit_result['ate']:+.3f}"
        st.info(
            f"""
**Key Finding:** Randomized trials show a {ate_txt} average effect on {outcome_label}.
The strongest effect is in **{top_subgroup["age_group"]}** patients with **{top_subgroup["condition"]}**
(CATE = {top_subgroup["cate_mean"]:+.3f}).
Top driver of heterogeneity: **{top_feat["feature"]}**
(importance score: {top_feat["importance"]:.3f}).
"""
        )
    elif not importance_df.empty:
        st.info(
            f"**Key Finding:** Average effect on **{outcome_label}**: "
            f"{fit_result['ate']:+.3f} (95% CI "
            f"[{fit_result['ate_lower']:+.3f}, {fit_result['ate_upper']:+.3f}]). "
            f"Top heterogeneity driver: **{importance_df.iloc[0]['feature']}**."
        )

else:
    st.info(
        "Configure your analysis in the sidebar and click **Run Causal Analysis**."
    )
    st.markdown(
        """
After you run the analysis, this page will show:

- **ATE** with a 95% confidence interval, sample counts, and a propensity **overlap** check  
- **Propensity overlap** histograms and a **CATE** distribution  
- **Feature importance** bars (direction = correlation with individual effects)  
- **Subgroup table** (colored CATE) and a **forest-style** interval plot  

Use the sidebar to choose conditions and outcome, then press **Run**.
"""
    )
