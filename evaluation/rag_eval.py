"""Retrieval latency on a small frozen corpus; optional RAGAS when dependencies and API allow."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np


def _load_corpus(root: Path) -> tuple[list[str], list[str]]:
    raw = json.loads((root / "data" / "eval" / "rag_mini_corpus.json").read_text())
    ids = [r["id"] for r in raw]
    texts = [f"{r['title']}. {r['text']}" for r in raw]
    return ids, texts


def embed_and_index(texts: list[str], model_name: str):
    import faiss
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    emb = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    dim = emb.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(emb.astype(np.float32))
    return model, index, emb


def run_rag_eval(
    root: Path | None = None,
    n_queries: int = 50,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> dict:
    import os

    if os.environ.get("EVAL_SKIP_RAG", "").lower() in ("1", "true", "yes"):
        return {
            "skipped": True,
            "embedding_model": model_name,
            "corpus_docs": 0,
            "retrieval_latency_ms_p50": 0.0,
            "retrieval_latency_ms_p95": 0.0,
            "ragas": {
                "faithfulness": None,
                "note": "Skipped (EVAL_SKIP_RAG=1)",
            },
        }

    root = root or Path(__file__).resolve().parents[1]
    _, texts = _load_corpus(root)
    model, index, _ = embed_and_index(texts, model_name=model_name)

    queries = [
        "How do adaptive trials reduce sample size?",
        "What affects pediatric enrollment speed?",
        "Why monitor drift across hospital sites?",
        "How do heterogeneous effects appear in heart failure?",
        "Why cite sources in clinical assistants?",
    ]
    latencies_ms: list[float] = []
    for _ in range(max(1, n_queries // len(queries))):
        for q in queries:
            t0 = time.perf_counter()
            qv = model.encode([q], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
            _, _ = index.search(qv, k=min(3, len(texts)))
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

    latencies_ms = np.asarray(latencies_ms, dtype=float)
    p50 = float(np.percentile(latencies_ms, 50))
    p95 = float(np.percentile(latencies_ms, 95))

    ragas_block: dict = {
        "faithfulness": None,
        "answer_relevancy": None,
        "context_precision": None,
        "context_recall": None,
        "note": "Install requirements-evaluation.txt and set OPENAI_API_KEY (or compatible) to run RAGAS; not required for CI.",
    }

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, faithfulness

        question = "What is the role of Bayesian adaptive trials?"
        answer = "They can reduce sample size while controlling error when response rates differ by subgroup."
        contexts = [texts[0]]
        ds = Dataset.from_dict(
            {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts],
            }
        )
        result = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision])
        df = result.to_pandas()
        ragas_block["faithfulness"] = float(df["faithfulness"].iloc[0])
        ragas_block["answer_relevancy"] = float(df["answer_relevancy"].iloc[0])
        ragas_block["context_precision"] = float(df["context_precision"].iloc[0])
        ragas_block["note"] = "RAGAS computed with default evaluator backend."
    except Exception as exc:
        ragas_block["error"] = str(exc)[:200]

    return {
        "embedding_model": model_name,
        "corpus_docs": len(texts),
        "retrieval_latency_ms_p50": p50,
        "retrieval_latency_ms_p95": p95,
        "ragas": ragas_block,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("evaluation/results/rag_eval.json"))
    p.add_argument("--n-queries", type=int, default=50)
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out = run_rag_eval(n_queries=args.n_queries)
    args.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
