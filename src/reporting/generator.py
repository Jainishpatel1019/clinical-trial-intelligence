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
        avg_cr_fmt = f"{avg_cr:.1%}" if pd.notna(avg_cr) else "—"

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
                        else "—",
                        "completion_rate": f"{float(cr):.1%}"
                        if pd.notna(cr)
                        else "—",
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
            top_features = ["— (fit heterogeneous effect model to populate drivers)"]

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
                "improvement": "—",
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

    def generate_pdf(self, data: dict[str, Any]) -> bytes:
        """Render context to HTML and convert to PDF bytes via WeasyPrint."""
        html_string = self.render_html(data)
        try:
            from weasyprint import HTML

            return HTML(string=html_string).write_pdf()
        except ImportError:
            raise ImportError(
                "WeasyPrint not installed. Run: pip install weasyprint"
            ) from None
        except Exception as e:
            logger.error("PDF generation failed: %s", e)
            raise
