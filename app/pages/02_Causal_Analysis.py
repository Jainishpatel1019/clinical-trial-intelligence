"""Causal Analysis page for treatment effect exploration workflows."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.data.schema import get_connection
from src.causal.hte_model import HTEModel
from src.causal.propensity import PropensityScorer
from src.causal.shap_analysis import SHAPAnalyzer
from app.theme import inject_theme

try:
    import mlflow
    _HAS_MLFLOW = True
except ImportError:
    _HAS_MLFLOW = False

st.set_page_config(page_title="Causal Analysis", page_icon="🔬", layout="wide")
inject_theme()


def _log_mlflow_run(
    fit_result: dict,
    ps_result: dict,
    importance_df: pd.DataFrame,
    subgroup_df: pd.DataFrame,
    outcome: str,
    conditions: list[str],
    n_rows: int,
) -> None:
    """Log a causal analysis run to MLflow."""
    try:
        mlflow.set_experiment("CausalTrialAnalysis")
        with mlflow.start_run(run_name=f"HTE_{outcome}_{datetime.now():%Y%m%d_%H%M%S}"):
            mlflow.log_params({
                "outcome_variable": outcome,
                "n_conditions": len(conditions),
                "conditions": ", ".join(conditions[:5]),
                "n_rows_input": n_rows,
                "model_type": "CausalForestDML",
                "n_estimators": 200,
                "min_samples_leaf": 10,
                "cv_folds": 3,
            })
            mlflow.log_metrics({
                "ate": fit_result["ate"],
                "ate_lower": fit_result["ate_lower"],
                "ate_upper": fit_result["ate_upper"],
                "n_samples_fitted": fit_result["n_samples"],
                "n_treated": fit_result["n_treated"],
                "n_control": fit_result["n_control"],
                "propensity_auc": ps_result["auc_roc"],
                "overlap_ok": float(ps_result["overlap_ok"]),
            })
            if not importance_df.empty:
                for _, row in importance_df.iterrows():
                    mlflow.log_metric(f"importance_{row['feature']}", row["importance"])
            if not subgroup_df.empty:
                n_sig = int(subgroup_df["significant"].sum())
                mlflow.log_metric("n_significant_subgroups", n_sig)
                mlflow.log_metric("max_cate", float(subgroup_df["cate_mean"].max()))
                mlflow.log_metric("min_cate", float(subgroup_df["cate_mean"].min()))
            mlflow.set_tags({
                "pipeline": "clinical-trial-intelligence",
                "stage": "causal_analysis",
            })
    except Exception:
        pass


def _causal_fit_ready() -> bool:
    """True only after a successful Run (avoids pre-initialized None session keys)."""
    r = st.session_state.get("hte_results")
    return isinstance(r, dict) and bool(r)


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
    log_to_mlflow = _HAS_MLFLOW
    run_button = st.button(
        "▶ Run Analysis", type="primary", use_container_width=True
    )
    st.caption("Takes about 15 seconds")

st.markdown('<div class="cti-section-label">Causal Analysis</div>', unsafe_allow_html=True)
st.title("🔬 Who Benefits Most?")
st.caption(
    "This page answers: does a treatment work equally for everyone, "
    "or do some patient groups benefit more than others?"
)

filtered_df = df[df["condition"].isin(condition_filter)]

if run_button or _causal_fit_ready():
    if run_button:
        if len(filtered_df) < 50:
            st.error(
                "Need at least 50 trials after filtering to fit the causal model. "
                "Broaden the condition filter."
            )
        else:
            st.markdown(
                '<div class="cti-progress-bar"></div>',
                unsafe_allow_html=True,
            )
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

                if _HAS_MLFLOW and log_to_mlflow:
                    _log_mlflow_run(
                        fit_result, ps_result, importance_df, subgroup_df,
                        selected_outcome, condition_filter, len(filtered_df),
                    )

    if not _causal_fit_ready():
        st.info(
            "Select your filters in the sidebar and click **Run Analysis**."
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
        "Treatment Benefit",
        f"{fit_result['ate']:+.3f}",
        delta=f"Range: {fit_result['ate_lower']:+.3f} to {fit_result['ate_upper']:+.3f}",
    )
    m2.metric("Trials Analyzed", f"{fit_result['n_samples']:,}")
    m3.metric(
        "Randomized Trials",
        f"{fit_result['n_treated']:,} of {fit_result['n_samples']:,}",
    )
    m4.metric(
        "Data Quality",
        "✅ Good" if ps_result["overlap_ok"] else "⚠️ Check",
    )
    st.caption(
        "Randomized trials = patients were randomly assigned to treatment or control. "
        "Higher proportion = stronger causal validity."
    )

    c_left, c_right = st.columns(2)
    with c_left:
        st.plotly_chart(scorer.plot_overlap(), use_container_width=True)
        auc = ps_result.get("auc_roc", 0)
        if auc < 0.6:
            st.caption(
                f"AUC-ROC = {auc:.3f} — close to 0.5 means treatment assignment was nearly random. "
                "This actually **strengthens** our causal estimates since selection bias is minimal."
            )
    with c_right:
        st.plotly_chart(
            analyzer.plot_effect_distribution(),
            use_container_width=True,
        )

    st.plotly_chart(
        analyzer.plot_importance(importance_df),
        use_container_width=True,
    )

    st.markdown('<div class="cti-section-label">Breakdown by patient group</div>', unsafe_allow_html=True)
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
                title="Treatment Benefit by Group",
                template="plotly_white",
                xaxis_title="Benefit Score",
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
        finding_text = (
            f"The treatment changes <strong>{outcome_label.replace('_', ' ')}</strong> "
            f"by {ate_txt} on average. "
            f"The biggest benefit goes to <strong>{top_subgroup['age_group']}</strong> patients with "
            f"<strong>{top_subgroup['condition']}</strong>. "
            f"The factor that matters most: <strong>{top_feat['feature'].replace('_', ' ')}</strong>."
        )
        st.markdown(
            f'<div class="cti-finding">'
            f'<div class="cti-finding-label">Key Finding</div>'
            f'<div class="cti-finding-text">{finding_text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    elif not importance_df.empty:
        finding_text = (
            f"Average change in <strong>{outcome_label.replace('_', ' ')}</strong>: "
            f"{fit_result['ate']:+.3f}. "
            f"The biggest differentiator: <strong>{importance_df.iloc[0]['feature'].replace('_', ' ')}</strong>."
        )
        st.markdown(
            f'<div class="cti-finding">'
            f'<div class="cti-finding-label">Key Finding</div>'
            f'<div class="cti-finding-text">{finding_text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

else:
    st.info(
        "Select your filters in the sidebar and click **Run Analysis**."
    )
    st.markdown(
        """
After you run the analysis, this page shows:

- **Overall treatment benefit** — does the treatment help on average?
- **Which patient groups** benefit more (or less) than average
- **What drives the difference** — which factors matter most
- **Visual breakdown** by age group and disease

Select conditions and an outcome in the sidebar, then press **Run Analysis**.
"""
    )

# MLflow experiment history (shown regardless of run state)
if _HAS_MLFLOW:
    st.divider()
    with st.expander("📊 MLflow Experiment History", expanded=False):
        try:
            exp = mlflow.get_experiment_by_name("CausalTrialAnalysis")
            if exp is not None:
                runs_df = mlflow.search_runs(
                    experiment_ids=[exp.experiment_id],
                    order_by=["start_time DESC"],
                    max_results=20,
                )
                if not runs_df.empty:
                    display_cols = []
                    col_map = {}
                    for col_pair in [
                        ("start_time", "Time"),
                        ("params.outcome_variable", "Outcome"),
                        ("params.n_rows_input", "Rows"),
                        ("metrics.ate", "ATE"),
                        ("metrics.ate_lower", "ATE Lower"),
                        ("metrics.ate_upper", "ATE Upper"),
                        ("metrics.n_samples_fitted", "Fitted"),
                        ("metrics.propensity_auc", "PS AUC"),
                        ("metrics.n_significant_subgroups", "Sig. Subgroups"),
                    ]:
                        if col_pair[0] in runs_df.columns:
                            display_cols.append(col_pair[0])
                            col_map[col_pair[0]] = col_pair[1]
                    if display_cols:
                        show = runs_df[display_cols].rename(columns=col_map)
                        st.dataframe(show, use_container_width=True, height=300)
                        st.caption(
                            f"{len(runs_df)} run(s) logged. "
                            "View full details with `mlflow ui` → http://localhost:5000"
                        )
                    else:
                        st.info("Runs exist but no metrics columns found yet.")
                else:
                    st.info("No runs logged yet. Run an analysis with MLflow enabled.")
            else:
                st.info("No MLflow experiment yet. Run an analysis with MLflow enabled.")
        except Exception as exc:
            st.caption(f"Could not load MLflow history: {exc}")
