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

st.set_page_config(page_title="Trial Simulator", page_icon="🎲", layout="wide")

st.title("🎲 Adaptive Trial Design Simulator")
st.markdown(
    "Compare **fixed equal-allocation** vs **Thompson Sampling adaptive allocation** — "
    "see how Bayesian optimization saves participants while maintaining statistical power."
)

col_left, col_right = st.columns(2)
with col_left:
    total_budget = st.slider(
        "Total participant budget", 100, 2000, 600, step=50
    )
    n_arms = st.slider("Number of treatment arms", 2, 5, 3)
    noise_std = st.slider(
        "Outcome noise (std dev)", 0.05, 0.40, 0.15, step=0.05
    )
    batch_size = st.slider(
        "Adaptive batch size", 10, 100, 50, step=10
    )

with col_right:
    st.markdown("**Expected effect sizes per arm:**")
    true_effects: list[float] = []
    for i in range(n_arms):
        default = 0.45 + i * 0.10
        e = st.slider(
            f"Arm {i + 1} true effect",
            0.20,
            0.95,
            min(default, 0.90),
            step=0.05,
            key=f"arm_{i}",
        )
        true_effects.append(e)
    n_simulations = st.slider(
        "Monte Carlo runs", 20, 200, 50, step=10
    )

run_sim = st.button(
    "▶ Run Simulation", type="primary", use_container_width=True
)

if run_sim or "sim_results" in st.session_state:
    if run_sim:
        simulator = AdaptiveTrialSimulator(
            n_arms=n_arms,
            total_budget=total_budget,
            true_effects=true_effects,
            noise_std=noise_std,
            batch_size=batch_size,
        )
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

    if "sim_results" not in st.session_state:
        st.info("Click **Run Simulation** to generate results.")
        st.stop()

    trad = st.session_state["sim_results"]["trad"]
    adapt = st.session_state["sim_results"]["adapt"]
    mc_df = st.session_state["sim_results"]["mc_df"]
    simulator = st.session_state["sim_results"]["simulator"]
    n_sims = int(st.session_state.get("sim_n_runs", n_simulations))

    tab_single, tab_mc, tab_power = st.tabs(
        ["📊 Single Run", "🎲 Monte Carlo", "📈 Power Analysis"]
    )

    with tab_single:
        na = simulator.n_arms
        m1, m2, m3 = st.columns(3)
        m1.metric(
            "Participants Saved",
            f"{adapt['arm_allocations'][adapt['winner']] - trad['arm_allocations'][trad['winner']]:+,}",
        )
        m2.metric(
            "Adaptive Power",
            f"{adapt['power_achieved']:.0%}",
            delta=f"{(adapt['power_achieved'] - trad['power_achieved']):.0%} vs Traditional",
        )
        m3.metric(
            "Correct Winner",
            "✅ Yes" if adapt["correct_winner"] else "❌ No",
        )

        cbar, calloc = st.columns(2)
        with cbar:
            x_labels = [f"Arm {i + 1}" for i in range(na)]
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
                title="Participant Allocation per Arm",
                template="plotly_white",
                xaxis_title="Arm",
                yaxis_title="Participants",
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
            title="Distribution of Participants Used (Monte Carlo)",
            template="plotly_white",
        )
        st.plotly_chart(fig_box, use_container_width=True)

        p_adapt = mc_df[mc_df["design"] == "Adaptive"]["correct_winner"].mean()
        p_trad = mc_df[mc_df["design"] == "Traditional"][
            "correct_winner"
        ].mean()
        st.success(
            f"Across {n_sims} simulations, adaptive allocation identified the correct "
            f"winner {p_adapt:.0%} of the time, vs {p_trad:.0%} for traditional design."
        )

    with tab_power:
        avg_effect = sum(true_effects) / len(true_effects)
        max_effect_diff = max(true_effects) - min(true_effects)
        st.caption(
            f"Configured mean effect ≈ **{avg_effect:.2f}**; largest arm gap "
            f"(used as effect size for power) = **{max_effect_diff:.2f}**."
        )

        st.metric(
            "Required N per arm (80% power)",
            f"{compute_required_n(max_effect_diff):,}",
        )
        n_per = max(total_budget // n_arms, 1)
        st.metric(
            "MDE at your budget",
            f"{compute_mde(n_per):.3f}",
        )
        st.caption(
            f"Achieved power at **{n_per}** per arm (Cohen's *d* = gap above): "
            f"**{compute_power(n_per, max_effect_diff):.0%}** (two-sided *t*-test, α=0.05)."
        )

        fig_pc = plot_power_curve(
            [0.1, 0.2, 0.3, max_effect_diff], total_budget
        )
        st.plotly_chart(fig_pc, use_container_width=True)

else:
    st.info(
        "Use the configuration panel above, then click **Run Simulation** to compare "
        "traditional equal allocation with Thompson sampling."
    )
    st.markdown(
        """
**What you’ll get**

- **Single run:** allocations per arm, adaptive allocation history over enrollment, and quick metrics  
- **Monte Carlo:** distribution of sample sizes and how often each design picks the best arm  
- **Power analysis:** rough required **N** per arm, **MDE** at your budget, and power curves across effect sizes  
"""
    )
