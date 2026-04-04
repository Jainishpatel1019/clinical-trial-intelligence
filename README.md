---
title: Clinical Trial Intelligence Platform
emoji: 🧬
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.32.0
app_file: app/main.py
pinned: false
license: mit
---

# 🧬 Clinical Trial Intelligence Platform

[![CI](https://github.com/jainishpatel1019/clinical-trial-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/jainishpatel1019/clinical-trial-intelligence/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-38%20passed-brightgreen)](tests/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red)](https://streamlit.io)
[![EconML](https://img.shields.io/badge/EconML-0.15-green)](https://econml.azurewebsites.net)
[![Gemini API](https://img.shields.io/badge/Gemini%20API-GenAI-4285F4)](https://ai.google.dev/)
[![HuggingFace Spaces](https://img.shields.io/badge/🤗%20HuggingFace-Spaces-yellow)](https://huggingface.co/spaces/jainishpatel1019/clinical-trial-intelligence)

An end-to-end data science platform that ingests public clinical trial data, estimates heterogeneous treatment effects with EconML causal forests, simulates adaptive allocation via Thompson sampling, and answers grounded questions with FAISS retrieval plus Gemini or Claude — packaged as a Streamlit dashboard.

## 🔗 Live Demo

**[Try the live demo on HuggingFace Spaces](https://huggingface.co/spaces/jainishpatel1019/clinical-trial-intelligence)**

## 📸 Screenshots

| Home | Data Explorer | Causal Analysis |
|------|--------------|-----------------|
| *(add screenshot)* | *(add screenshot)* | *(add screenshot)* |

| Trial Simulator | RAG Assistant | Geographic Map |
|----------------|---------------|----------------|
| *(add screenshot)* | *(add screenshot)* | *(add screenshot)* |

> Screenshots coming after HuggingFace deployment

## 📊 Results

| Metric | Value | What It Means |
|--------|-------|---------------|
| Average Treatment Effect (ATE) | +24.4% | Randomized trials complete 24.4% more often on average |
| 95% Confidence Interval | [+18.5%, +30.4%] | Statistically significant positive effect |
| Subgroup Estimates | 10 groups | HTE detected across age × condition combinations |
| Top Effect Group | Middle-aged Breast Cancer | CATE = +25.1% above average |
| Propensity AUC-ROC | 0.566 | Moderate selection bias — causal adjustment warranted |
| Validation Rules | 7/7 passed | All data quality checks green |
| RAG Index | 300 trials | FAISS IndexFlatIP, MiniLM-L6-v2 embeddings |
| Test Suite | 38 tests passing | Full pytest coverage with GitHub Actions CI |
| Adaptive Simulation | +371 patients | More patients on best arm vs fixed 50/50 split |
| Simulation Power | 100% | Correct arm identified in all Monte Carlo runs |

## 🏗️ Architecture

```
ClinicalTrials.gov API ─┐
                        ├─▶ DuckDB ─▶ EconML CausalForestDML ─▶ Subgroup Effects
Demo CSV (300 trials) ──┘      │
                               ├─▶ Thompson Sampling Simulator ─▶ Adaptive vs Fixed
                               │
                               └─▶ FAISS + Gemini/Claude RAG ──▶ Grounded Q&A
                                                                       │
                                               Jinja2 + WeasyPrint ◀───┘
                                                       │
                                                   PDF Report
```

## 🚀 Quickstart

```bash
git clone https://github.com/jainishpatel1019/clinical-trial-intelligence
cd clinical-trial-intelligence
pip install -r requirements.txt
cp .env.example .env          # Optional: add GEMINI_API_KEY for RAG
python scripts/generate_demo_data.py
streamlit run app/main.py
```

## 🌐 Fetch Real Data (No API Key Needed)

The ClinicalTrials.gov API is **free and open** — no authentication required. Two ways to use real data:

1. **In the app:** Open Data Explorer → sidebar → "Fetch real ClinicalTrials.gov data" → pick conditions → click Fetch
2. **From the CLI:**
```bash
DEMO_MODE=false python -m src.data.ingestor
```

This pulls live trial records for conditions like Type 2 Diabetes, Breast Cancer, Hypertension, etc.

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Storage | DuckDB (in-process, zero config) |
| Causal Inference | EconML CausalForestDML, SHAP |
| Adaptive Simulation | Thompson sampling (SciPy Beta–Bernoulli) |
| RAG | sentence-transformers → FAISS → Gemini / Claude |
| Validation | Custom rule engine (pandas-based) |
| Frontend | Streamlit with Claude-inspired theme |
| Deployment | Docker, HuggingFace Spaces |
| CI | GitHub Actions (38 tests, Docker build) |

## 📦 6 Modules

1. **Data Explorer** — Browse and filter thousands of real clinical trials; download CSV
2. **Causal Analysis** — EconML CausalForestDML estimates who benefits most from treatment
3. **Trial Simulator** — Thompson Sampling adaptive design vs fixed 50/50 allocation
4. **RAG Assistant** — Ask plain-English questions, answered from indexed trial data via Gemini/Claude
5. **Report Generator** — Export PDF/HTML briefs from your analysis session
6. **Geographic Intelligence** — Interactive 3D globe showing global trial distribution across 5 regions

## 🧪 Tests

```bash
pytest tests/ -v
```

**38 tests** covering:
- Causal model fitting + propensity scores (3 tests)
- Demo data quality + NCT ID uniqueness (3 tests)
- Ingestor API parsing: phases, statuses, ages, oncology flags (7 tests)
- Thompson sampling simulator + Monte Carlo (5 tests)
- Power analysis: required N, MDE, power curves (6 tests)
- Validator: clean/validate logic, clipping, null handling (5 tests)
- DuckDB schema: create, stats, load (3 tests)
- RAG indexer + QA chain demo mode (2 tests)
- Theme CSS: palette, chat elements (3 tests)
- Smoke: core imports (1 test)

## 🚢 Deploy to HuggingFace Spaces

1. Fork this repo
2. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
3. Select **Docker** SDK (or **Streamlit**)
4. Connect your GitHub repo
5. (Optional) Add **GEMINI_API_KEY** in Space Settings → Repository secrets

The Dockerfile generates demo data at build time, so the app works immediately.

## 📝 Resume Bullet Points

> **Data Scientist / ML Engineer roles:**

- Built Clinical Trial Intelligence Platform: 6-module Streamlit app using EconML CausalForestDML (ATE +24.4%, 95% CI [+18.5%, +30.4%]), Thompson Sampling adaptive simulation (+371 patients to best arm), and Gemini-powered RAG over 300 indexed trials — deployed on HuggingFace Spaces with Docker + GitHub Actions CI (38 tests passing)
- Estimated heterogeneous treatment effects across 10 patient subgroups (age × condition); identified Middle-aged Breast Cancer patients as highest-benefit group (CATE +25.1%)
- Implemented adaptive Bayesian trial simulator demonstrating 100% correct arm identification vs 50/50 fixed allocation across Monte Carlo replications
- Engineered end-to-end RAG pipeline: FAISS IndexFlatIP + sentence-transformers (MiniLM-L6-v2) + Google Gemini, answering plain-English clinical trial questions grounded in ClinicalTrials.gov public data

## 📄 License

MIT
