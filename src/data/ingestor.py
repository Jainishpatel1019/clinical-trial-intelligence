"""ClinicalTrials.gov API v2 client and DuckDB ingestion for trial records."""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Mapping

import duckdb
import numpy as np
import pandas as pd
import requests

from src.data.schema import get_connection, initialize_schema
from src.data.validator import TrialValidator

logger = logging.getLogger(__name__)

_FIELDS = (
    "NCTId,BriefTitle,OverallStatus,Phase,EnrollmentCount,StartDate,CompletionDate,"
    "EligibilityCriteria,InterventionName,PrimaryOutcomeMeasure,LeadSponsorName"
)

_RAW_COLUMNS = [
    "NCTId",
    "BriefTitle",
    "OverallStatus",
    "Phase",
    "EnrollmentCount",
    "StartDate",
    "CompletionDate",
    "EligibilityCriteria",
    "InterventionName",
    "PrimaryOutcomeMeasure",
    "LeadSponsorName",
    "lookup_condition",
]

_STATUS_MAP: dict[str, str] = {
    "RECRUITING": "Recruiting",
    "COMPLETED": "Completed",
    "ACTIVE_NOT_RECRUITING": "Active, not recruiting",
    "TERMINATED": "Terminated",
    "WITHDRAWN": "Withdrawn",
    "SUSPENDED": "Suspended",
    "NOT_YET_RECRUITING": "Not yet recruiting",
    "ENROLLING_BY_INVITATION": "Enrolling by invitation",
    "AVAILABLE": "Available",
    "NO_LONGER_AVAILABLE": "No longer available",
    "APPROVED_FOR_MARKETING": "Approved for marketing",
    "UNKNOWN": "Unknown",
}


def _map_overall_status(raw: object) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    return _STATUS_MAP.get(s, s.replace("_", " ").title())


def _normalize_api_phase(phase_val: object) -> str:
    if phase_val is None or (isinstance(phase_val, float) and pd.isna(phase_val)):
        return "N/A"
    if isinstance(phase_val, list):
        raw = phase_val[0] if phase_val else None
    else:
        raw = phase_val
    if raw is None:
        return "N/A"
    s = str(raw).strip().upper().replace(" ", "")
    if s in ("NA", "N/A"):
        return "N/A"
    mapping = {
        "PHASE1": "Phase 1",
        "EARLYPHASE1": "Phase 1",
        "PHASE2": "Phase 2",
        "PHASE3": "Phase 3",
        "PHASE4": "Phase 4",
    }
    return mapping.get(s, "N/A")


def _parse_years_from_text(text: object) -> float | None:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", str(text))
    if not m:
        return None
    return float(m.group(1))


def _sex_display(raw: object) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return "All"
    s = str(raw).strip().upper()
    if s == "MALE":
        return "Male"
    if s == "FEMALE":
        return "Female"
    return "All"


def _age_group_from_min(min_age: float | None) -> str:
    if min_age is None or (isinstance(min_age, float) and np.isnan(min_age)):
        return "Unknown"
    if min_age < 40:
        return "Young"
    if min_age <= 65:
        return "Middle"
    return "Senior"


def _min_age_from_criteria(text: object) -> float | None:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    s = str(text)
    m = re.search(r"(?i)\b(\d+)\s+years?\s+or\s+older\b", s)
    if m:
        return float(m.group(1))
    m = re.search(r"(?i)minimum\s*age[^0-9]{0,20}(\d+)", s)
    if m:
        return float(m.group(1))
    m = re.search(r"(?i)aged?\s*(\d+)\s*(?:to|-)\s*(\d+)\s*years?", s)
    if m:
        return float(m.group(1))
    return None


def _oncology_hit(condition: str) -> bool:
    c = condition.lower()
    return any(
        k in c
        for k in (
            "cancer",
            "carcinoma",
            "oncology",
            "melanoma",
            "lymphoma",
            "leukemia",
            "tumor",
            "tumour",
            "neoplasm",
            "myeloma",
            "sarcoma",
        )
    )


def _cardiovascular_hit(condition: str) -> bool:
    c = condition.lower()
    return any(
        k in c
        for k in (
            "hypertension",
            "heart failure",
            "cardiac",
            "cardiovascular",
            "coronary",
            "atrial fibrillation",
            "stroke",
        )
    )


def _study_to_raw_row(study: Mapping[str, Any], lookup_condition: str) -> dict[str, Any]:
    ps = study.get("protocolSection") or {}
    idm = ps.get("identificationModule") or {}
    sm = ps.get("statusModule") or {}
    dm = ps.get("designModule") or {}
    em = ps.get("eligibilityModule") or {}
    aim = ps.get("armsInterventionsModule") or {}
    om = ps.get("outcomesModule") or {}
    scm = ps.get("sponsorCollaboratorsModule") or {}

    interventions = aim.get("interventions") or []
    intervention_names = ", ".join(
        str(i.get("name") or "").strip() for i in interventions if i.get("name")
    )

    phases = dm.get("phases")
    enroll = dm.get("enrollmentInfo") or {}
    start_struct = sm.get("startDateStruct") or {}
    comp_struct = sm.get("completionDateStruct") or {}
    primary_outcomes = om.get("primaryOutcomes") or []
    primary_measure = None
    if primary_outcomes:
        primary_measure = primary_outcomes[0].get("measure")

    return {
        "NCTId": idm.get("nctId"),
        "BriefTitle": idm.get("briefTitle"),
        "OverallStatus": sm.get("overallStatus"),
        "Phase": phases,
        "EnrollmentCount": enroll.get("count"),
        "StartDate": start_struct.get("date"),
        "CompletionDate": comp_struct.get("date"),
        "EligibilityCriteria": em.get("eligibilityCriteria"),
        "InterventionName": intervention_names,
        "PrimaryOutcomeMeasure": primary_measure,
        "LeadSponsorName": (scm.get("leadSponsor") or {}).get("name"),
        "lookup_condition": lookup_condition,
        "_eligibility_module": em,
        "_has_results": study.get("hasResults"),
    }


class TrialIngestor:
    """Fetch trials from ClinicalTrials.gov v2, normalize, validate, and upsert into DuckDB."""

    def __init__(self, db_path: str = "data/trials.duckdb") -> None:
        """Configure API base URL, DuckDB connection, validator, and class logger."""
        self.base_url = "https://clinicaltrials.gov/api/v2/studies"
        self.db_path = db_path
        self.conn = get_connection(db_path)
        self.validator = TrialValidator()
        self.logger = logging.getLogger(__name__)

    def fetch_trials(self, condition: str, max_results: int = 200) -> pd.DataFrame:
        """Page through the v2 studies API for ``condition`` and return a flat field DataFrame."""
        params: dict[str, Any] = {
            "query.cond": condition,
            "pageSize": 100,
            "format": "json",
            "fields": _FIELDS,
        }
        rows: list[dict[str, Any]] = []
        page_token: str | None = None

        while len(rows) < max_results:
            req_params = dict(params)
            if page_token:
                req_params["pageToken"] = page_token
            try:
                resp = requests.get(
                    self.base_url, params=req_params, timeout=90
                )
                resp.raise_for_status()
                payload = resp.json()
            except Exception as exc:
                self.logger.error("ClinicalTrials.gov request failed: %s", exc)
                raise RuntimeError(
                    f"ClinicalTrials.gov API request failed for '{condition}': {exc}"
                ) from exc

            studies = payload.get("studies") or []
            for study in studies:
                rows.append(_study_to_raw_row(study, condition))
                if len(rows) >= max_results:
                    break

            page_token = payload.get("nextPageToken")
            if len(rows) >= max_results or not page_token:
                break
            time.sleep(0.5)

        if not rows:
            return pd.DataFrame(columns=_RAW_COLUMNS)
        return pd.DataFrame(rows)

    def parse_raw(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Map API-style columns to the local ``trials`` schema and add derived fields."""
        if raw_df.empty:
            return pd.DataFrame(
                columns=[
                    "nct_id",
                    "brief_title",
                    "condition",
                    "phase",
                    "overall_status",
                    "enrollment_count",
                    "start_date",
                    "completion_date",
                    "min_age_years",
                    "max_age_years",
                    "sex",
                    "is_randomized",
                    "is_blinded",
                    "has_results",
                    "trial_duration_days",
                    "enrollment_log",
                    "phase_numeric",
                    "completion_rate",
                    "is_oncology",
                    "is_cardiovascular",
                    "age_group",
                ]
            )

        brief = raw_df["BriefTitle"].fillna("").astype(str)
        interv = raw_df["InterventionName"].fillna("").astype(str)
        mask_rand = (
            brief.str.contains("randomized", case=False, na=False)
            | interv.str.contains("randomized", case=False, na=False)
        )

        n = len(raw_df)
        phases_norm = [_normalize_api_phase(x) for x in raw_df["Phase"]]
        phase_numeric = []
        phase_map = {"Phase 1": 1, "Phase 2": 2, "Phase 3": 3, "Phase 4": 4}
        for p in phases_norm:
            phase_numeric.append(phase_map.get(p))

        start_dates = pd.to_datetime(raw_df["StartDate"], errors="coerce")
        comp_dates = pd.to_datetime(raw_df["CompletionDate"], errors="coerce")
        duration = (comp_dates - start_dates).dt.days.astype("Int64")

        enroll = pd.to_numeric(raw_df["EnrollmentCount"], errors="coerce")
        enrollment_log = np.log1p(enroll)

        lookup = raw_df["lookup_condition"].fillna("").astype(str)

        min_ages: list[float | None] = []
        max_ages: list[float | None] = []
        sexes: list[str] = []
        age_groups: list[str] = []

        for i in range(n):
            ser = raw_df.iloc[i]
            em = ser.get("_eligibility_module")
            if not isinstance(em, dict):
                em = {}
            min_a = _parse_years_from_text(em.get("minimumAge"))
            max_a = _parse_years_from_text(em.get("maximumAge"))
            crit_text = em.get("eligibilityCriteria") or ser.get("EligibilityCriteria")
            if min_a is None:
                min_a = _min_age_from_criteria(crit_text)
            if min_a is None and crit_text is not None and not (
                isinstance(crit_text, float) and pd.isna(crit_text)
            ):
                m = re.search(
                    r"minimum\s*age[^0-9]*(\d+)",
                    str(crit_text),
                    flags=re.IGNORECASE,
                )
                if m:
                    min_a = float(m.group(1))
            sexes.append(_sex_display(em.get("sex")))
            min_ages.append(min_a)
            max_ages.append(max_a)
            age_groups.append(_age_group_from_min(min_a))

        is_oncology = [_oncology_hit(c) for c in lookup]
        is_cardiovascular = [_cardiovascular_hit(c) for c in lookup]

        if "_has_results" in raw_df.columns:
            has_results_list = []
            for v in raw_df["_has_results"]:
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    has_results_list.append(False)
                else:
                    has_results_list.append(bool(v))
        else:
            has_results_list = [False] * n

        out = pd.DataFrame(
            {
                "nct_id": raw_df["NCTId"],
                "brief_title": raw_df["BriefTitle"],
                "condition": raw_df["lookup_condition"],
                "phase": phases_norm,
                "overall_status": [_map_overall_status(x) for x in raw_df["OverallStatus"]],
                "enrollment_count": enroll,
                "start_date": start_dates,
                "completion_date": comp_dates,
                "min_age_years": min_ages,
                "max_age_years": max_ages,
                "sex": sexes,
                "is_randomized": mask_rand.tolist(),
                "is_blinded": [False] * n,
                "has_results": has_results_list,
                "trial_duration_days": duration,
                "enrollment_log": enrollment_log,
                "phase_numeric": pd.array(phase_numeric, dtype="Int64"),
                "completion_rate": pd.Series(np.nan, index=raw_df.index, dtype=float),
                "is_oncology": is_oncology,
                "is_cardiovascular": is_cardiovascular,
                "age_group": age_groups,
            }
        )
        return out

    def _upsert_trials(self, df: pd.DataFrame) -> None:
        """Write ``df`` into ``trials`` using INSERT OR REPLACE when supported."""
        if df.empty:
            return
        self.conn.register("_ingest_trials_df", df)
        insert_sql = """
        INSERT{replace} INTO trials (
            nct_id, brief_title, condition, phase, overall_status, enrollment_count,
            start_date, completion_date, min_age_years, max_age_years, sex,
            is_randomized, is_blinded, has_results, trial_duration_days,
            enrollment_log, phase_numeric, completion_rate, is_oncology,
            is_cardiovascular, age_group
        )
        SELECT
            nct_id, brief_title, condition, phase, overall_status, enrollment_count,
            start_date, completion_date, min_age_years, max_age_years, sex,
            is_randomized, is_blinded, has_results, trial_duration_days,
            enrollment_log, phase_numeric, completion_rate, is_oncology,
            is_cardiovascular, age_group
        FROM _ingest_trials_df
        """
        try:
            self.conn.execute(insert_sql.format(replace=" OR REPLACE"))
        except duckdb.BinderException as exc:
            if "PRIMARY KEY" not in str(exc) and "UNIQUE" not in str(exc):
                raise
            self.conn.execute(
                "DELETE FROM trials WHERE nct_id IN (SELECT nct_id FROM _ingest_trials_df)"
            )
            self.conn.execute(insert_sql.format(replace=""))
        finally:
            self.conn.unregister("_ingest_trials_df")

    def ingest_live(
        self, conditions: list[str], max_per_condition: int = 200
    ) -> dict[str, Any]:
        """Always fetch from the real ClinicalTrials.gov API (ignores DEMO_MODE)."""
        initialize_schema(self.conn)
        errors: list[str] = []
        total_ingested = 0
        by_condition: dict[str, int] = {}
        for cond in conditions:
            try:
                raw = self.fetch_trials(cond, max_per_condition)
                if raw.empty:
                    by_condition[cond] = 0
                    continue
                parsed = self.parse_raw(raw)
                cleaned = self.validator.clean(parsed)
                self._upsert_trials(cleaned)
                by_condition[cond] = int(len(cleaned))
                total_ingested += int(len(cleaned))
            except Exception as exc:
                self.logger.exception("Live ingest failed for %r", cond)
                errors.append(f"{cond}: {exc}")
                by_condition[cond] = 0
        return {
            "total_ingested": total_ingested,
            "by_condition": by_condition,
            "errors": errors,
        }

    def ingest(
        self, conditions: list[str], max_per_condition: int = 200
    ) -> dict[str, Any]:
        """Fetch or load demo data per mode, clean rows, and upsert into DuckDB."""
        initialize_schema(self.conn)
        errors: list[str] = []
        if os.getenv("DEMO_MODE", "true").lower() == "true":
            try:
                df = self.demo_mode_load()
            except Exception as exc:
                self.logger.error("demo_mode_load failed: %s", exc)
                return {
                    "total_ingested": 0,
                    "by_condition": {},
                    "errors": [str(exc)],
                }
            cleaned = self.validator.clean(df)
            self._upsert_trials(cleaned)
            by_condition = (
                cleaned.groupby("condition").size().astype(int).to_dict()
                if not cleaned.empty
                else {}
            )
            by_condition_str = {str(k): int(v) for k, v in by_condition.items()}
            return {
                "total_ingested": int(len(cleaned)),
                "by_condition": by_condition_str,
                "errors": errors,
            }

        total_ingested = 0
        by_condition: dict[str, int] = {}
        for cond in conditions:
            try:
                raw = self.fetch_trials(cond, max_per_condition)
                if raw.empty:
                    by_condition[cond] = 0
                    continue
                parsed = self.parse_raw(raw)
                cleaned = self.validator.clean(parsed)
                self._upsert_trials(cleaned)
                by_condition[cond] = int(len(cleaned))
                total_ingested += int(len(cleaned))
            except Exception as exc:
                self.logger.exception("Ingest failed for condition %r", cond)
                errors.append(f"{cond}: {exc}")
                by_condition[cond] = 0
        return {
            "total_ingested": total_ingested,
            "by_condition": by_condition,
            "errors": errors,
        }

    def demo_mode_load(self) -> pd.DataFrame:
        """Load processed demo trials from CSV (used when ``DEMO_MODE`` is true)."""
        root = Path(__file__).resolve().parent.parent.parent
        csv_path = root / "data" / "processed" / "demo_trials.csv"
        return pd.read_csv(
            csv_path,
            parse_dates=["start_date", "completion_date"],
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo = os.getenv("DEMO_MODE", "true").lower() == "true"
    ingestor = TrialIngestor()
    if demo:
        result = ingestor.ingest([], max_per_condition=200)
        logger.info("DEMO_MODE ingest: %s", result)
    else:
        result = ingestor.ingest(["Type 2 Diabetes"], max_per_condition=200)
        logger.info("API ingest: %s", result)
