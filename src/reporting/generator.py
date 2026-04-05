"""HTML/PDF report generation from trial data, HTE outputs, and simulation summaries."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


def _econml_version() -> str:
    try:
        import econml

        return str(getattr(econml, "__version__", "unknown"))
    except Exception:
        return "N/A"


class ReportGenerator:
    """Render ``report.html`` with Jinja2 and optional WeasyPrint PDF output."""

    def __init__(self) -> None:
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        self.template = env.get_template("report.html")

    def compile_data(
        self,
        df: pd.DataFrame,
        hte_results: dict[str, Any] | None = None,
        sim_results: dict[str, Any] | None = None,
        ai_insights: list[str] | None = None,
        author_name: str = "Data Scientist",
    ) -> dict[str, Any]:
        """Assemble all Jinja context fields for ``report.html``."""
        hte_results = hte_results or {}
        sim_results = sim_results or {}
        ai_insights = list(ai_insights or [])

        n_trials = int(len(df))
        uniq_conditions = (
            df["condition"].dropna().astype(str).unique().tolist()
            if "condition" in df.columns
            else []
        )
        if len(uniq_conditions) == 1:
            condition = uniq_conditions[0]
        elif len(uniq_conditions) <= 3:
            condition = ", ".join(sorted(uniq_conditions))
        elif uniq_conditions:
            head = ", ".join(sorted(uniq_conditions)[:3])
            condition = f"{len(uniq_conditions)} conditions ({head}…)"
        else:
            condition = "All trials"

        med_enr = (
            float(df["enrollment_count"].median())
            if "enrollment_count" in df.columns and n_trials
            else 0.0
        )
        med_dur = (
            float(df["trial_duration_days"].median())
            if "trial_duration_days" in df.columns and n_trials
            else 0.0
        )
        avg_cr = (
            float(df["completion_rate"].mean())
            if "completion_rate" in df.columns and n_trials
            else float("nan")
        )
        avg_cr_fmt = f"{avg_cr:.1%}" if pd.notna(avg_cr) else "-"

        phase_table: list[dict[str, Any]] = []
        if n_trials and "phase" in df.columns and "nct_id" in df.columns:
            phase_agg = (
                df.groupby("phase", dropna=False)
                .agg(
                    count=("nct_id", "count"),
                    avg_enrollment=("enrollment_count", "mean"),
                    completion_rate=("completion_rate", "mean"),
                )
                .reset_index()
            )
            for _, r in phase_agg.iterrows():
                cr = r["completion_rate"]
                phase_table.append(
                    {
                        "phase": str(r["phase"]),
                        "count": f"{int(r['count']):,}",
                        "avg_enrollment": f"{float(r['avg_enrollment']):,.0f}"
                        if pd.notna(r["avg_enrollment"])
                        else "-",
                        "completion_rate": f"{float(cr):.1%}"
                        if pd.notna(cr)
                        else "-",
                    }
                )

        fit = hte_results.get("fit_result", hte_results)
        if isinstance(fit, dict) and "ate" in fit:
            ate = float(fit["ate"])
            ate_lo = float(fit.get("ate_lower", 0.0))
            ate_hi = float(fit.get("ate_upper", 0.0))
            ate_formatted = f"{ate:+.3f}"
            ate_ci = f"[{ate_lo:+.3f}, {ate_hi:+.3f}]"
            ate_positive = ate > 0
        else:
            ate_formatted = "N/A"
            ate_ci = "N/A"
            ate_positive = False

        subgroup_df = hte_results.get("subgroup_df")
        subgroup_table: list[dict[str, Any]] = []
        if isinstance(subgroup_df, pd.DataFrame) and not subgroup_df.empty:
            for _, r in subgroup_df.iterrows():
                cm = float(r.get("cate_mean", 0.0))
                lo = float(r.get("cate_lower", 0.0))
                hi = float(r.get("cate_upper", 0.0))
                subgroup_table.append(
                    {
                        "age_group": str(r.get("age_group", "")),
                        "condition": str(r.get("condition", "")),
                        "cate_formatted": f"{cm:+.3f}",
                        "cate_positive": cm > 0,
                        "ci_formatted": f"[{lo:+.3f}, {hi:+.3f}]",
                        "n_samples": int(r.get("n_samples", 0)),
                        "significant": bool(r.get("significant", False)),
                    }
                )

        importance_df = hte_results.get("importance_df")
        top_features: list[str] = []
        if isinstance(importance_df, pd.DataFrame) and not importance_df.empty:
            sub = importance_df.sort_values(
                "importance", ascending=False
            ).head(5)
            for _, r in sub.iterrows():
                feat = str(r.get("feature", ""))
                imp = float(r.get("importance", 0.0))
                top_features.append(f"{feat} (importance: {imp:.3f})")
        if not top_features:
            top_features = ["(run the causal analysis to populate drivers)"]

        trad = sim_results.get("trad", {})
        adapt = sim_results.get("adapt", {})
        mc = sim_results.get("mc_df")

        trad_n = int(trad.get("total_n", n_trials or 0))
        adapt_n = int(adapt.get("total_n", n_trials or 0))

        if isinstance(mc, pd.DataFrame) and not mc.empty and "design" in mc.columns:
            tdf = mc[mc["design"] == "Traditional"]
            adf = mc[mc["design"] == "Adaptive"]
            trad_correct = float(tdf["correct_winner"].mean()) if len(tdf) else 0.0
            adapt_correct = float(adf["correct_winner"].mean()) if len(adf) else 0.0
            trad_power = float(tdf["power"].mean()) if len(tdf) else 0.0
            adapt_power = float(adf["power"].mean()) if len(adf) else 0.0
            n_simulations = int(mc["sim"].nunique()) if "sim" in mc.columns else 0
        else:
            trad_correct = float(bool(trad.get("correct_winner", False)))
            adapt_correct = float(bool(adapt.get("correct_winner", False)))
            trad_power = float(trad.get("power_achieved", 0.0))
            adapt_power = float(adapt.get("power_achieved", 0.0))
            n_simulations = int(sim_results.get("n_simulations", 0))

        if n_simulations == 0:
            n_simulations = int(sim_results.get("n_simulations", 100))

        simulation_table = [
            {
                "metric": "Participants Used",
                "traditional": f"{trad_n:,}",
                "adaptive": f"{adapt_n:,}",
                "improvement": f"{trad_n - adapt_n:+,}",
                "improved": adapt_n < trad_n,
            },
            {
                "metric": "Correct Winner",
                "traditional": f"{trad_correct:.0%}",
                "adaptive": f"{adapt_correct:.0%}",
                "improvement": "-",
                "improved": False,
            },
            {
                "metric": "Statistical Power",
                "traditional": f"{trad_power:.0%}",
                "adaptive": f"{adapt_power:.0%}",
                "improvement": f"{(adapt_power - trad_power):+.0%}",
                "improved": adapt_power > trad_power,
            },
        ]

        outcome_variable = str(
            hte_results.get("outcome_variable", "completion_rate")
        )

        gen_dt = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        exec_lines: list[str] = [
            (
                f"Dataset contains {n_trials:,} trials covering "
                f"{len(uniq_conditions)} distinct condition(s); "
                f"median enrollment {med_enr:,.0f} and median duration "
                f"{med_dur:,.0f} days."
            ),
            (
                f"Overall mean completion rate is {avg_cr_fmt} across included studies."
            ),
        ]
        if isinstance(fit, dict) and "ate" in fit:
            exec_lines.append(
                f"Heterogeneous treatment analysis estimates an average treatment effect "
                f"of {ate_formatted} on {outcome_variable} (95% CI {ate_ci})."
            )
        else:
            exec_lines.append(
                "Causal effect estimates were not attached; run the HTE workflow to populate ATE and subgroups."
            )

        if isinstance(mc, pd.DataFrame) and not mc.empty:
            exec_lines.append(
                f"Adaptive Thompson sampling identified the best arm {adapt_correct:.0%} of "
                f"Monte Carlo runs vs {trad_correct:.0%} under equal allocation "
                f"({n_simulations} simulations)."
            )
        else:
            exec_lines.append(
                "Adaptive trial simulation summaries were not provided for this export."
            )

        return {
            "report_title": "Clinical Trial Intelligence Report",
            "condition": condition,
            "generated_date": gen_dt,
            "author_name": author_name,
            "executive_summary": exec_lines,
            "total_trials": f"{n_trials:,}",
            "median_enrollment": f"{med_enr:,.0f}",
            "median_duration_days": f"{med_dur:,.0f}",
            "avg_completion_rate": avg_cr_fmt,
            "phase_table": phase_table,
            "ate_positive": ate_positive,
            "ate_formatted": ate_formatted,
            "ate_ci": ate_ci,
            "subgroup_table": subgroup_table,
            "top_features": top_features,
            "simulation_table": simulation_table,
            "ai_insights": ai_insights,
            "outcome_variable": outcome_variable,
            "n_simulations": n_simulations,
            "econml_version": _econml_version(),
        }

    def render_html(self, data: dict[str, Any]) -> str:
        """Render the PDF HTML shell with the given context."""
        return self.template.render(**data)

    def generate_pdf(self, data: dict[str, Any]) -> tuple[bytes, str]:
        """Build a PDF directly using fpdf2 (pure Python, no system deps).

        Returns (pdf_bytes, "pdf") on success, or (html_bytes, "html") as fallback.
        """
        try:
            return self._build_pdf(data), "pdf"
        except Exception as exc:
            logger.warning("PDF generation failed (%s), falling back to HTML.", exc)
            return self.render_html(data).encode("utf-8"), "html"

    def _build_pdf(self, data: dict[str, Any]) -> bytes:
        from fpdf import FPDF

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        accent = (198, 106, 62)
        dark = (45, 42, 38)
        gray = (120, 120, 120)
        light_bg = (247, 245, 240)

        def heading(text: str, size: int = 16) -> None:
            pdf.set_font("Helvetica", "B", size)
            pdf.set_text_color(*accent)
            pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(*accent)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(4)

        def body(text: str, size: int = 10) -> None:
            pdf.set_font("Helvetica", "", size)
            pdf.set_text_color(*dark)
            pdf.multi_cell(0, 5.5, text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

        def table_row(cells: list[str], widths: list[float], bold: bool = False) -> None:
            pdf.set_font("Helvetica", "B" if bold else "", 9)
            h = 7
            for i, (cell, w) in enumerate(zip(cells, widths)):
                if bold:
                    pdf.set_fill_color(*accent)
                    pdf.set_text_color(255, 255, 255)
                else:
                    pdf.set_fill_color(*light_bg)
                    pdf.set_text_color(*dark)
                pdf.cell(w, h, str(cell), border=0, fill=True)
            pdf.ln(h)

        # Title block
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(*accent)
        pdf.cell(0, 14, data.get("report_title", "Clinical Trial Report"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*gray)
        pdf.cell(0, 6, f"{data.get('condition', '')}  |  {data.get('generated_date', '')}  |  {data.get('author_name', '')}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # Executive summary
        if data.get("include_executive_summary", True):
            heading("Executive Summary")
            for line in data.get("executive_summary", []):
                body(f"  {line}")
            pdf.ln(3)

        # Data overview
        heading("Data Overview")
        metrics = [
            ("Total Trials", data.get("total_trials", "-")),
            ("Median Enrollment", data.get("median_enrollment", "-")),
            ("Median Duration (days)", data.get("median_duration_days", "-")),
            ("Avg Completion Rate", data.get("avg_completion_rate", "-")),
        ]
        pdf.set_font("Helvetica", "", 10)
        col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / len(metrics)
        pdf.set_text_color(*gray)
        for label, _ in metrics:
            pdf.cell(col_w, 5, label, align="C")
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*dark)
        for _, val in metrics:
            pdf.cell(col_w, 8, str(val), align="C")
        pdf.ln(12)

        phase_table = data.get("phase_table", [])
        if phase_table:
            widths = [40, 30, 45, 45]
            table_row(["Phase", "Count", "Avg Enrollment", "Completion Rate"], widths, bold=True)
            for row in phase_table:
                table_row([row["phase"], row["count"], row["avg_enrollment"], row["completion_rate"]], widths)
            pdf.ln(6)

        # Causal analysis
        if data.get("include_causal", True):
            heading("Causal Analysis")
            ate_fmt = data.get("ate_formatted", "N/A")
            ate_ci = data.get("ate_ci", "N/A")
            outcome = data.get("outcome_variable", "completion_rate")
            body(f"Average Treatment Effect on {outcome}: {ate_fmt}  (95% CI: {ate_ci})")

            subgroup_table = data.get("subgroup_table", [])
            if subgroup_table:
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*dark)
                pdf.cell(0, 7, "Subgroup Effects", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
                widths = [35, 40, 30, 40, 20, 20]
                table_row(["Age Group", "Condition", "CATE", "95% CI", "N", "Sig."], widths, bold=True)
                for sg in subgroup_table:
                    table_row([
                        sg["age_group"], sg["condition"], sg["cate_formatted"],
                        sg["ci_formatted"], str(sg["n_samples"]),
                        "Yes" if sg["significant"] else "No",
                    ], widths)
                pdf.ln(4)

            top_features = data.get("top_features", [])
            if top_features:
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*dark)
                pdf.cell(0, 7, "Top Feature Drivers", new_x="LMARGIN", new_y="NEXT")
                for feat in top_features:
                    body(f"  - {feat}")
            pdf.ln(3)

        # Simulation
        if data.get("include_simulation", True):
            heading("Adaptive Trial Simulation")
            sim_table = data.get("simulation_table", [])
            n_sim = data.get("n_simulations", 0)
            if n_sim:
                body(f"Based on {n_sim:,} Monte Carlo simulations.")
            if sim_table:
                widths = [50, 35, 35, 35]
                table_row(["Metric", "Traditional", "Adaptive", "Improvement"], widths, bold=True)
                for row in sim_table:
                    table_row([row["metric"], row["traditional"], row["adaptive"], row["improvement"]], widths)
            pdf.ln(4)

        # AI insights
        if data.get("include_ai_insights", True):
            insights = data.get("ai_insights", [])
            if insights:
                heading("AI-Generated Insights")
                for i, insight in enumerate(insights, 1):
                    body(f"{i}. {insight}")
                pdf.ln(3)

        # Methodology
        if data.get("include_methodology", True):
            heading("Methodology")
            econml_v = data.get("econml_version", "N/A")
            body(f"Causal inference: EconML CausalForestDML (v{econml_v}) with 200 estimators, "
                 f"3-fold cross-validation, and SHAP feature importance.")
            body("Adaptive simulation: Thompson Sampling with Beta-Bernoulli conjugate updates.")
            body("Retrieval-augmented Q&A: FAISS index with MiniLM-L6-v2 embeddings.")

        return bytes(pdf.output())
