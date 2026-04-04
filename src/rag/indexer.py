"""FAISS-backed dense retrieval index over trial text built from a DataFrame."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _safe_str(val: Any, default: str = "Unknown") -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    return str(val)


def _safe_num(val: Any, default: float = 0.0) -> float:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return float(default)
    return float(val)


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    return int(val)


def _yes_no_randomized(val: Any) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "No"
    if val is True or val is np.True_:
        return "Yes"
    if val in (1, 1.0):
        return "Yes"
    return "No"


class TrialIndexer:
    """Encode trial rows with SentenceTransformer and store in a FAISS inner-product index."""

    def __init__(
        self,
        index_path: str = "data/faiss_index",
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.index_path = index_path
        self.model_name = model_name
        self.model = None
        self.index = None
        self.documents: list[dict[str, Any]] = []
        os.makedirs(index_path, exist_ok=True)

    def _load_model(self) -> None:
        if self.model is None:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)

    def build_documents(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Turn each trial row into a single retrieval string plus structured metadata."""
        out: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            cr = row.get("completion_rate")
            if cr is None or (isinstance(cr, float) and np.isnan(cr)):
                cr_fmt = "N/A"
            else:
                cr_fmt = f"{float(cr):.1%}"

            text = f"""Trial: {_safe_str(row.get('brief_title'))} (NCT ID: {_safe_str(row.get('nct_id'))})
Condition: {_safe_str(row.get('condition'))}
Phase: {_safe_str(row.get('phase'))} | Status: {_safe_str(row.get('overall_status'))}
Enrollment: {_safe_int(row.get('enrollment_count'), 0):,} participants
Duration: {_safe_int(row.get('trial_duration_days'), 0)} days
Age Range: {_safe_num(row.get('min_age_years'), 0):.0f}–{_safe_num(row.get('max_age_years'), 0):.0f} years | Sex: {_safe_str(row.get('sex'), 'All')}
Randomized: {_yes_no_randomized(row.get('is_randomized'))}
Completion Rate: {cr_fmt}"""

            cr_meta = row.get("completion_rate")
            if cr_meta is not None and not (isinstance(cr_meta, float) and np.isnan(cr_meta)):
                cr_meta = float(cr_meta)
            else:
                cr_meta = None

            meta = {
                "nct_id": _safe_str(row.get("nct_id")),
                "brief_title": _safe_str(row.get("brief_title")),
                "condition": _safe_str(row.get("condition")),
                "phase": _safe_str(row.get("phase")),
                "status": _safe_str(row.get("overall_status")),
                "enrollment_count": _safe_int(row.get("enrollment_count"), 0),
                "completion_rate": cr_meta,
            }
            out.append({"text": text, "metadata": meta})
        return out

    def build_index(self, df: pd.DataFrame) -> None:
        """Encode documents, build ``IndexFlatIP``, and persist index + JSON sidecar."""
        self._load_model()
        documents = self.build_documents(df)
        self.documents = documents

        texts = [d["text"] for d in documents]
        embeddings = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        import faiss

        dimension = int(embeddings.shape[1])
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(np.asarray(embeddings, dtype=np.float32))

        os.makedirs(self.index_path, exist_ok=True)
        faiss.write_index(self.index, os.path.join(self.index_path, "index.faiss"))
        with open(
            os.path.join(self.index_path, "documents.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)

        logger.info("Built FAISS index with %s documents", len(documents))

    def load_index(self) -> bool:
        """Load ``index.faiss`` and ``documents.json`` from disk; return success."""
        index_fp = os.path.join(self.index_path, "index.faiss")
        docs_fp = os.path.join(self.index_path, "documents.json")
        if not os.path.isfile(index_fp) or not os.path.isfile(docs_fp):
            return False
        try:
            import faiss

            self.index = faiss.read_index(index_fp)
            with open(docs_fp, encoding="utf-8") as f:
                self.documents = json.load(f)
            logger.info(
                "Loaded FAISS index (%s vectors)", self.index.ntotal
            )
            return True
        except Exception:
            logger.exception("Failed to load FAISS index from %s", self.index_path)
            return False

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Return top-``k`` documents by cosine similarity (IP on normalized vectors)."""
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")
        self._load_model()
        query_embedding = np.asarray(
            self.model.encode([query], normalize_embeddings=True),
            dtype=np.float32,
        )
        scores, indices = self.index.search(query_embedding, k)

        results: list[dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            results.append(
                {
                    "text": self.documents[idx]["text"],
                    "metadata": self.documents[idx]["metadata"],
                    "score": float(score),
                }
            )
        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def index_exists(self) -> bool:
        """Return whether a persisted FAISS index file is present."""
        return os.path.exists(os.path.join(self.index_path, "index.faiss"))
