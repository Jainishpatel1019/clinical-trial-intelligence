---
title: Clinical Trial Intelligence Platform
emoji: 🧬
colorFrom: blue
colorTo: indigo
sdk: docker
app_file: app/Main.py
pinned: false
license: mit
---

# Clinical Trial Intelligence Platform

### Problem Statement

This system improves **trial design and patient allocation decisions**: who is likely to benefit (heterogeneous treatment effects), how to **reduce exposure to inferior arms** while learning faster, and how to **keep those decisions trustworthy** as data and populations shift. The operational goal is fewer wasted enrollments, faster convergence to the right arm, and evidence-linked explanations that a clinician or trial ops team can audit.

The **Streamlit product** (ClinicalTrials.gov, DuckDB, causal forest, Thompson-style simulation, RAG, reports) is the delivery surface. The **IHDP benchmark and simulations** below quantify behavior on data with known effects and on bandit assumptions, so results are reproducible without claiming unverified outcomes on live trials.

### Results Summary Table

Values below are from a committed benchmark run (`evaluation/results/summary.json`, 200 Monte Carlo episodes for adaptive allocation). **Regenerate** anytime:

`python evaluation/run_all.py --out evaluation/results/summary.json`  
(Optional: `pip install -r requirements-evaluation.txt` for Evidently, Locust, RAGAS, FastAPI. Set `EVAL_SKIP_RAG=1` to skip downloading the sentence-transformer model.)

| Component | Metric | Value | Baseline | Delta |
|-----------|--------|-------|----------|-------|
| HTE model (IHDP) | PEHE (RMSE of ITE) | 1.2828 | - | - |
| HTE model (IHDP) | AUUC (normalized uplift curve) | 1.504 | 0 (random ranking) | higher is better |
| HTE model (IHDP) | Qini coefficient | 2.905 | - | - |
| HTE policy (top 30%) | Capture rate of true top-30% ITE | 91.1% | 30.0% (random 30% policy) | 3.04x vs random |
| Adaptive allocation (sim) | Mean % visits on non-optimal arm | 14.0% | 66.8% (equal rotation) | 79.1% relative reduction vs equal |
| Adaptive allocation (sim) | Cost proxy (patient-equiv. × $8k) | $1,125,867 | $0 | 140.7 patient-equivalent slots avoided / horizon |
| RAG retrieval (mini corpus) | Faithfulness (RAGAS) | n/a | - | needs `requirements-evaluation.txt` + evaluator API |
| RAG retrieval (mini corpus) | p95 latency (encode + FAISS) | ~25 ms | - | local CPU |
| Drift monitor (PSI demo) | Max PSI (shifted slice) | 5.49 | <0.1 stable | critical (expected on injected shift) |
| Drift monitor | Alert compute latency | sub-ms | - | in-process only, not streaming SLA |
| Load (stub path) | p95 batch scoring (100 rows) | ~0.02 ms | - | 50 concurrent workers, linear stub |

**Interpretation notes:** (1) **Cost proxy** maps avoided assignment slots to **patient-equivalents** (assignments / number of arms) × **$8,000** as a Phase II-style illustration, not a sponsor CFO sign-off. (2) **IHDP** is a semi-synthetic benchmark; PEHE/AUUC/Qini are **model metrics**, not regulatory endpoints. (3) **PSI “critical”** here is from an **intentional covariate shift** to validate the detector.

### Screenshots

| | |
|---|---|
| ![Home](screenshots/home.png) | ![Data Explorer](screenshots/data_explorer.png) |
| ![Causal Analysis](screenshots/causal_analysis.png) | ![Trial Simulator](screenshots/trial_simulator.png) |
| ![RAG Assistant](screenshots/rag_assistant.png) | ![Geographic Map](screenshots/geographic_map.png) |

### System Architecture

```
ClinicalTrials.gov API --+
                         +--> DuckDB --> EconML CausalForestDML --> Subgroup effects (app)
Demo CSV (demo trials) --+       |
                                 +--> Thompson Sampling (app + evaluation/bandit_simulation.py)
                                 |
                                 +--> FAISS + Gemini/Claude --> Q&A with sources
                                 |
                                 +--> Jinja2 + fpdf2 --> PDF report
                                 |
IHDP (econml.data.dgps) ----------> preprocessing/ + evaluation/causal_eval.py (offline PEHE / AUUC / Qini)
```

### Dataset & Preprocessing

- **App data:** ClinicalTrials.gov (optional fetch) or bundled demo trials in DuckDB.
- **Benchmark:** IHDP surface B via `econml.data.dgps.ihdp_surface_B` (747 rows, known ITE).
- **Pipeline:** `preprocessing/ihdp_pipeline.py` reports propensity overlap trimming (% trimmed), SMD for top covariates before/after PS matching, and optional MCAR missingness + median imputation (`--inject-missing`).

```bash
python preprocessing/ihdp_pipeline.py --out evaluation/results/ihdp_preprocess.json
```

### Model Evaluation

```bash
python evaluation/causal_eval.py --out evaluation/results/causal_eval.json
```

Outputs: **PEHE** on held-out IHDP, **AUUC** and **Qini** (custom numpy implementations in `evaluation/uplift_metrics.py`), **policy tree** (depth ≤ 3) on predicted CATE, and **targeting lift** vs random top-30% policy.

### Adaptive Experimentation Results

```bash
python evaluation/bandit_simulation.py --n-sims 1000 --horizon 800 --out evaluation/results/bandit_simulation.json
```

Compares **Thompson sampling**, **equal rotation**, and **epsilon-greedy** on binary arms: cumulative regret, % assignments to non-optimal arm, posterior “confidence” stopping proxy, and **cost illustration** ($8k × patient-equivalent avoided slots).

### RAG Evaluation

- **Frozen mini-corpus:** `data/eval/rag_mini_corpus.json` (fast, no large download).
- **Script:** `evaluation/rag_eval.py` measures **p50/p95** retrieval latency (MiniLM + FAISS).
- **RAGAS** (faithfulness, answer relevancy, context precision): install `requirements-evaluation.txt` and configure an evaluator LLM per RAGAS docs.

### Deployment & Monitoring

- **Production app:** Docker + HuggingFace Spaces (`Dockerfile`).
- **Load / bench:** `evaluation/bench_server.py` (FastAPI) + `evaluation/locustfile.py`. Start server:  
  `uvicorn evaluation.bench_server:app --port 8765`  
  then `python evaluation/load_test.py --locust --bench-url http://127.0.0.1:8765` (requires Locust).
- **In-process stub:** `evaluation/load_test.py` (default) runs concurrent batch scoring without HTTP.

### Drift & Decision Reliability

```bash
python evaluation/drift_simulation.py --out evaluation/results/drift_simulation.json
```

Computes **PSI** per feature on a reference vs shifted slice; optional **Evidently** `DataDriftPreset` when `evidently` is installed. **PSI > 0.2** is treated as critical in the summary table; tune thresholds to your protocol.

### Reproducing Results

```bash
pip install -r requirements.txt
# optional heavy eval stack:
# pip install -r requirements-evaluation.txt

python scripts/generate_demo_data.py
python evaluation/run_all.py --out evaluation/results/summary.json
# CI-friendly:
# EVAL_SKIP_RAG=1 python evaluation/run_all.py --fast --out /tmp/summary.json
```

### Product Features (Streamlit)

- Browse trials, causal analysis (demo trial schema), adaptive simulator, RAG Q&A, PDF reports, geographic map.
- **Setup:** `streamlit run app/Main.py`

## Tech stack

| What | How |
|------|-----|
| Storage | DuckDB (embedded, no server) |
| Causal inference | EconML CausalForestDML + SHAP (app); IHDP benchmark (evaluation) |
| Simulation | Thompson sampling with Beta-Bernoulli updates |
| Search + Q&A | sentence-transformers (MiniLM-L6-v2), FAISS, Gemini or Claude |
| Frontend | Streamlit (light theme, Inter font) |
| Reports | Jinja2 templates, fpdf2 for PDF |
| Experiment tracking | MLflow |
| Deploy | Docker, HuggingFace Spaces |
| CI | GitHub Actions, pytest |

## Deliverables checklist

| Path | Purpose |
|------|---------|
| `evaluation/causal_eval.py` | PEHE, AUUC, Qini, policy tree, targeting |
| `evaluation/bandit_simulation.py` | Monte Carlo Thompson vs baselines |
| `evaluation/rag_eval.py` | Latency + optional RAGAS |
| `evaluation/drift_simulation.py` | PSI + optional Evidently |
| `evaluation/load_test.py` | Concurrent batch stub; optional Locust |
| `evaluation/bench_server.py` | FastAPI target for Locust |
| `evaluation/locustfile.py` | Locust user definition |
| `evaluation/run_all.py` | One-shot summary JSON + table |
| `preprocessing/ihdp_pipeline.py` | IHDP balance + overlap + optional expansion |
| `requirements-evaluation.txt` | Optional pinned eval dependencies |
| `evaluation/results/summary.json` | Last full benchmark snapshot |

## Tests

```bash
pytest tests/ -v
```

## License

MIT
