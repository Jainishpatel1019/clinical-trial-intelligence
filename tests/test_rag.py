"""Tests for RAG indexing and QA (mocked ST — no model download or LLM API calls)."""

import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_trial_df() -> pd.DataFrame:
    rows = []
    for i in range(20):
        rows.append(
            {
                "nct_id": f"NCT{i+1:07d}",
                "brief_title": f"Study of Condition Alpha — arm {i}",
                "condition": "Type 2 Diabetes",
                "phase": "Phase 2",
                "overall_status": "Completed",
                "enrollment_count": 100 + i * 10,
                "trial_duration_days": 365,
                "min_age_years": 40.0,
                "max_age_years": 75.0,
                "sex": "All",
                "is_randomized": i % 2 == 0,
                "completion_rate": 0.75 + i * 0.01,
            }
        )
    return pd.DataFrame(rows)


def _fake_encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True):
    if isinstance(texts, str):
        texts = [texts]
    n = len(texts)
    rng = np.random.RandomState(0)
    arr = rng.randn(n, 384).astype(np.float32)
    if normalize_embeddings:
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        arr = arr / np.clip(norms, 1e-9, None)
    return arr


@pytest.fixture
def mock_sentence_transformer():
    with patch("sentence_transformers.SentenceTransformer") as mock_cls:
        instance = MagicMock()
        instance.encode = MagicMock(side_effect=_fake_encode)
        mock_cls.return_value = instance
        yield mock_cls


def test_indexer_builds_documents(sample_trial_df):
    from src.rag.indexer import TrialIndexer

    indexer = TrialIndexer()
    docs = indexer.build_documents(sample_trial_df)
    assert len(docs) == 20
    assert "text" in docs[0]
    assert "metadata" in docs[0]
    assert "NCT" in docs[0]["text"]


def test_qa_chain_demo_mode(sample_trial_df, tmp_path, mock_sentence_transformer):
    from src.rag.indexer import TrialIndexer
    from src.rag.qa_chain import TrialQAChain

    indexer = TrialIndexer(index_path=str(tmp_path))
    indexer.build_index(sample_trial_df)
    chain = TrialQAChain(indexer, api_key=None)
    result = chain.ask("Which trials had high enrollment?")
    assert "answer" in result
    assert "source_trials" in result
    assert "confidence" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 0
