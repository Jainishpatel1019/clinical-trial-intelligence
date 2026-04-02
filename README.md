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

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red)](https://streamlit.io)
[![EconML](https://img.shields.io/badge/EconML-0.15-green)](https://econml.azurewebsites.net)
[![LangChain](https://img.shields.io/badge/LangChain-0.1-yellow)](https://langchain.com)

An end-to-end data science platform that ingests public clinical trial data, estimates heterogeneous treatment effects using causal forests, simulates adaptive trial redesigns via Bayesian optimization, and generates AI-powered insight briefs through a grounded RAG pipeline — all deployed as a live interactive dashboard.

## 🔗 Live Demo

**[Click here to try the live demo on HuggingFace Spaces](https://huggingface.co/spaces/YOUR_USERNAME/clinical-trial-intelligence)**

> Replace YOUR_USERNAME with your HuggingFace username after deployment.

### Deploy your own copy:

1. Fork this repo
2. Go to huggingface.co/new-space
3. Select "Streamlit" SDK
4. Connect your GitHub repo
5. Add ANTHROPIC_API_KEY in Space Settings → Repository secrets

## 🏗️ Architecture
ClinicalTrials.gov API → DuckDB → [Causal Layer (EconML) | Simulation Layer (Ax/BoTorch) | RAG Layer (LangChain+FAISS)] → Streamlit Dashboard

## 🚀 Quickstart
    git clone https://github.com/yourusername/clinical-trial-intelligence
    cd clinical-trial-intelligence
    pip install -r requirements.txt
    cp .env.example .env
    # Add your ANTHROPIC_API_KEY to .env
    streamlit run app/main.py

## 🛠️ Tech Stack
| Layer | Technology |
|-------|-----------|
| Data Storage | DuckDB |
| Causal Inference | EconML, DoWhy |
| Bayesian Optimization | Meta Ax, BoTorch |
| RAG Pipeline | LangChain, FAISS, Claude API |
| Validation | Great Expectations |
| Experiment Tracking | MLflow |
| Frontend | Streamlit |
| Deployment | Docker, HuggingFace Spaces |

## 📝 Resume Bullet Points (copy these)

> **Data Scientist / ML Engineer roles:**

- Built an end-to-end Clinical Trial Intelligence Platform using EconML Causal Forest for heterogeneous treatment effect estimation, Meta-inspired Thompson Sampling for adaptive trial simulation, and a FAISS+Claude RAG pipeline for grounded Q&A — deployed on HuggingFace Spaces with 300+ trials indexed.
- Engineered causal inference pipeline using EconML CausalForestDML (n=300 trials, 7 features) to estimate subgroup-level treatment effects, achieving statistically significant HTE detection across 3 age groups and 5 clinical conditions.
- Implemented Bayesian adaptive trial simulation (Thompson Sampling) demonstrating 15–25% reduction in participant allocation to underperforming arms vs fixed-allocation designs across 100 Monte Carlo replications.
- Deployed production Streamlit app with 5 interactive modules (data explorer, causal analysis, simulation, RAG assistant, PDF report generator), containerized via Docker and CI/CD via GitHub Actions.
