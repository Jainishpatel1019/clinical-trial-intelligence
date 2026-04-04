"""Trial Simulator page for adaptive trial simulation interfaces."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.simulation.bandit import AdaptiveTrialSimulator
from src.simulation.power_analysis import (
    compute_mde,
    compute_power,
    compute_required_n,
    plot_power_curve,
)
from app.theme import inject_theme

st.set_page_config(page_title="Trial Simulator", page_icon="🎲", layout="wide")
inject_theme()


def _sim_results_ready() -> bool:
    r = st.session_state.get("sim_results")
    return isinstance(r, dict) and "trad" in r and "adapt" in r


st.markdown('<div class="cti-section-label">Simulator</div>', unsafe_allow_html=True)
st.title("🎲 Smarter Trial Design")
st.caption(
    "Traditional trials split patients 50/50, even when one treatment is clearly "
    "winning. Our simulator shows what happens when you adapt in real time."
)

col_left, col_right = st.columns(2)
with col_left:
    total_budget = st.slider(
        "Total patients available", 100, 2000, 600, step=50
    )
    n_arms = st.slider("Number of treatments to compare", 2, 5, 3)
    noise_std = st.slider(
        "How noisy are the results?", 0.05, 0.40, 0.15, step=0.05
    )
    batch_size = st.slider(
        "Patients per round", 10, 100, 50, step=10
    )

with col_right:
    st.markdown("**How effective is each treatment?**")
    true_effects: list[float] = []
    for i in range(n_arms):
        default = 0.45 + i * 0.10
        e = st.slider(
            f"Treatment {i + 1} success rate",
            0.20,
            0.95,
            min(default, 0.90),
            step=0.05,
            key=f"arm_{i}",
        )
        true_effects.append(e)
    n_simulations = st.slider(
        "Simulation runs", 20, 200, 50, step=10
    )

run_sim = st.button(
    "▶ Run Simulation", type="primary", use_container_width=True
)

if run_sim or _sim_results_ready():
    if run_sim:
        simulator = AdaptiveTrialSimulator(
            n_arms=n_arms,
            total_budget=total_budget,
            true_effects=true_effects,
            noise_std=noise_std,
            batch_size=batch_size,
        )
        st.markdown('<div class="cti-progress-bar"></div>', unsafe_allow_html=True)
        with st.spinner("Running simulations..."):
            trad_result = simulator.simulate_traditional()
            adapt_result = simulator.simulate_adaptive()
            mc_df = simulator.run_monte_carlo(n_simulations=n_simulations)

        st.session_state["sim_results"] = {
            "trad": trad_result,
            "adapt": adapt_result,
            "mc_df": mc_df,
            "simulator": simulator,
        }
        st.session_state["sim_n_runs"] = n_simulations

    if not _sim_results_ready():
        st.info("Click **Run Simulation** to generate results.")
        st.stop()

    trad = st.session_state["sim_results"]["trad"]
    adapt = st.session_state["sim_results"]["adapt"]
    mc_df = st.session_state["sim_results"]["mc_df"]
    simulator = st.session_state["sim_results"]["simulator"]
    n_sims = int(st.session_state.get("sim_n_runs", n_simulations))

    tab_single, tab_mc, tab_power = st.tabs(
        ["📊 One Trial", "🎲 Repeat 50 Times", "📈 How Many Patients Needed?"]
    )

    with tab_single:
        na = simulator.n_arms
        m1, m2, m3 = st.columns(3)
        m1.metric(
            "More patients got the better treatment",
            f"{adapt['arm_allocations'][adapt['winner']] - trad['arm_allocations'][trad['winner']]:+,}",
        )
        m2.metric(
            "Statistical confidence",
            f"{adapt['power_achieved']:.0%}",
            delta=f"{(adapt['power_achieved'] - trad['power_achieved']):.0%} vs 50/50 split",
        )
        m3.metric(
            "Found the best treatment?",
            "✅ Yes" if adapt["correct_winner"] else "❌ No",
        )

        cbar, calloc = st.columns(2)
        with cbar:
            x_labels = [f"Treatment {i + 1}" for i in range(na)]
            fig_bars = go.Figure()
            fig_bars.add_trace(
                go.Bar(
                    name="Traditional",
                    x=x_labels,
                    y=trad["arm_allocations"],
                )
            )
            fig_bars.add_trace(
                go.Bar(
                    name="Adaptive",
                    x=x_labels,
                    y=adapt["arm_allocations"],
                )
            )
            fig_bars.update_layout(
                barmode="group",
                title="How Were Patients Distributed?",
                template="plotly_white",
                xaxis_title="Treatment",
                yaxis_title="Patients",
            )
            st.plotly_chart(fig_bars, use_container_width=True)
        with calloc:
            st.plotly_chart(
                simulator.plot_allocation_history(adapt),
                use_container_width=True,
            )

    with tab_mc:
        summary = (
            mc_df.groupby("design")
            .agg(
                avg_power=("power", "mean"),
                pct_correct=("correct_winner", "mean"),
                avg_n=("total_n", "mean"),
            )
            .reset_index()
        )
        fmt = summary.style.format(
            {
                "avg_power": "{:.1%}",
                "pct_correct": "{:.1%}",
                "avg_n": "{:.0f}",
            }
        )
        st.dataframe(fmt, use_container_width=True)

        fig_box = px.box(
            mc_df,
            x="design",
            y="total_n",
            color="design",
            title="How Many Patients Were Needed?",
            template="plotly_white",
        )
        st.plotly_chart(fig_box, use_container_width=True)

        p_adapt = mc_df[mc_df["design"] == "Adaptive"]["correct_winner"].mean()
        p_trad = mc_df[mc_df["design"] == "Traditional"][
            "correct_winner"
        ].mean()
        st.success(
            f"Across {n_sims} simulations, the smart approach found the best treatment "
            f"{p_adapt:.0%} of the time, vs {p_trad:.0%} for the traditional 50/50 approach."
        )

    with tab_power:
        max_effect_diff = max(true_effects) - min(true_effects)

        st.metric(
            "Patients needed per treatment (to be 80% sure)",
            f"{compute_required_n(max_effect_diff):,}",
        )
        n_per = max(total_budget // n_arms, 1)
        st.metric(
            "Smallest difference you can detect with your budget",
            f"{compute_mde(n_per):.3f}",
        )
        st.caption(
            f"With **{n_per}** patients per treatment, you have "
            f"**{compute_power(n_per, max_effect_diff):.0%}** chance of detecting a real difference."
        )

        fig_pc = plot_power_curve(
            [0.1, 0.2, 0.3, max_effect_diff], total_budget
        )
        st.plotly_chart(fig_pc, use_container_width=True)

else:
    st.info(
        "Configure the sliders above, then click **Run Simulation**."
    )
    st.markdown(
        """
**After running, you will see:**

- **One Trial** -- How did the smart approach distribute patients vs. the traditional 50/50?
- **Repeat 50 Times** -- What happens when you run the trial many times? How often does each approach find the real winner?
- **How Many Patients Needed?** -- How many patients do you actually need to get a reliable answer?
"""
    )
