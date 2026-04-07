"""Minimal FastAPI service for Locust load tests (batch scoring stub)."""

from __future__ import annotations

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="CTI Bench CATE")

# Fixed linear scoring weights (deterministic, cheap)
_rng = np.random.default_rng(0)
_W = _rng.normal(0, 0.05, size=26).astype(np.float32)


class BatchRequest(BaseModel):
    features: list[list[float]] = Field(..., description="Rows of 26-dim feature vectors")


@app.post("/cate_batch")
def cate_batch(body: BatchRequest) -> dict:
    x = np.asarray(body.features, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != 26:
        return {"error": "expected shape (n, 26)", "cate": []}
    scores = (x * _W.reshape(1, -1)).sum(axis=1)
    return {"cate": scores.tolist()}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
