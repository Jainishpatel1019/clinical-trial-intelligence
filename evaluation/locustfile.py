"""Locust load test for evaluation/bench_server.py (run uvicorn separately)."""

from __future__ import annotations

import json
import os
import random

from locust import HttpUser, between, task


class CateBenchUser(HttpUser):
    wait_time = between(0.05, 0.2)
    host = os.environ.get("BENCH_HOST", "http://127.0.0.1:8765")

    @task
    def post_cate(self) -> None:
        payload = {
            "features": [
                [random.random() for _ in range(26)] for _ in range(100)
            ]
        }
        self.client.post("/cate_batch", data=json.dumps(payload), headers={"Content-Type": "application/json"})
