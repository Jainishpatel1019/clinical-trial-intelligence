# Clinical Trial Intelligence — Complete Project Handoff for Claude

> Paste this entire file into Claude, optionally attach screenshots of each page.
> Ask: *"Based on this brief, what should I improve next?"*

---

## 1. What Is This Project?

A **6-page Streamlit web app** that helps anyone (technical or not) understand clinical trial data.

**The core problem it solves:**
Thousands of medical trials happen every year but the data is scattered, technical, and impossible to search or reason about without a research background. This platform:
- Pulls public data from **ClinicalTrials.gov** (free, no API key needed)
- Runs **AI/ML analysis** to find which patient groups benefit most from treatments
- Simulates **smarter trial designs** that route more patients to the winning treatment
- Answers **plain-English questions** about trials with sources cited
- Shows **where trials happen** on an interactive 3D globe
- Exports **PDF reports** of findings

**Target audience:** Data Scientists, ML Engineers, Pharma analysts, Biotech researchers.

---

## 2. Repository Layout

```
clinical-trial-intelligence/
│
├── app/
│   ├── main.py                    ← Landing page (hero, stats, feature cards)
│   ├── theme.py                   ← Injected CSS (Inter + Playfair Display fonts,
│   │                                warm #F7F5F0 palette, all components styled)
│   └── pages/
│       ├── 01_Data_Explorer.py    ← Browse/filter trials, charts, CSV download
│       ├── 02_Causal_Analysis.py  ← HTE model, SHAP importance, subgroup table
│       ├── 03_Trial_Simulator.py  ← Adaptive vs traditional trial design
│       ├── 04_RAG_Assistant.py    ← Chat interface with RAG over indexed trials
│       ├── 05_Report_Generator.py ← PDF/HTML report export
│       └── 06_Geographic_Map.py   ← 3D Plotly orthographic globe
│
├── src/
│   ├── data/
│   │   ├── schema.py              ← DuckDB setup, get_connection(), get_table_stats()
│   │   ├── ingestor.py            ← ClinicalTrials.gov API v2 client + DuckDB upsert
│   │   └── validator.py           ← 7 data quality rules (pandas-based)
│   ├── causal/
│   │   ├── propensity.py          ← PropensityScorer (logistic regression, AUC)
│   │   ├── hte_model.py           ← HTEModel (EconML CausalForestDML)
│   │   └── shap_analysis.py       ← SHAPAnalyzer (feature importance, CATE dist)
│   ├── simulation/
│   │   ├── bandit.py              ← AdaptiveTrialSimulator (Thompson sampling)
│   │   └── power_analysis.py      ← compute_required_n, compute_power, compute_mde
│   ├── rag/
│   │   ├── indexer.py             ← TrialIndexer (FAISS IndexFlatIP + SentenceTransformer)
│   │   ├── qa_chain.py            ← TrialQAChain (Gemini → Claude → demo fallback)
│   │   └── retriever.py           ← Helper retrieval utilities
│   └── reporting/
│       └── generator.py           ← ReportGenerator (Jinja2 HTML → WeasyPrint/pdfkit PDF)
│
├── tests/                         ← 38 pytest tests (all passing)
├── scripts/
│   ├── generate_demo_data.py      ← Creates ~300 synthetic trials in DuckDB + CSV
│   ├── smoke_test.py              ← End-to-end sanity check
│   └── setup_check.py             ← Dependency verification
│
├── .streamlit/config.toml         ← Theme colors + headless server config
├── .env.example                   ← API key template
├── Dockerfile                     ← Production image (installs pango for WeasyPrint)
├── app.py                         ← HuggingFace Spaces entry point
├── requirements.txt               ← 55 pinned dependencies
└── README.md                      ← Full docs with real benchmark results
```

---

## 3. All 6 Pages — What Each Does

### Page 1 — Home (`app/main.py`)
- **Hero section** with eyebrow label, serif title, subtitle in plain English
- **Live KPI metrics** (total trials, diseases covered, data source) pulled from DuckDB
- **5-column feature cards** explaining each module in plain language
- No jargon. Designed for a non-clinical reader

### Page 2 — Browse Trials (`01_Data_Explorer.py`)
- **Sidebar filters:** Disease (multiselect), Phase (multiselect), Status, min enrollment
- **Live fetch button** → calls `ingestor.ingest_live()` → hits ClinicalTrials.gov API v2 → upserts into DuckDB
- **4 KPIs:** Trials Found, Typical Size (patients), Typical Length (days), Finish Rate
- **Charts:** "How Many Patients Per Trial" (log histogram), "Trial Count by Phase" (bar), "Bigger Trials Take Longer" (scatter)
- **Data table** + CSV download button
- **Data quality check** (collapsible expander) — 7 rules, shows pass/fail

### Page 3 — Who Benefits Most? (`02_Causal_Analysis.py`)
- **Sidebar:** condition filter + outcome selector (completion_rate or trial_duration_days) + Run button
- Runs `PropensityScorer` → `HTEModel` (EconML `CausalForestDML`) → `SHAPAnalyzer`
- **4 KPIs:** Treatment Benefit (ATE), Trials Analyzed, Treatment Group, Data Quality
- **Charts:** propensity overlap histogram, CATE distribution, feature importance bars
- **Subgroup table** with green/red CATE coloring + forest-plot intervals
- **Plain-English key finding** ("The biggest benefit goes to X patients with Y condition")
- **MLflow logging** — silently logs params/metrics to `CausalTrialAnalysis` experiment after each run
- MLflow history in collapsible expander at bottom

### Page 4 — Smarter Trial Design (`03_Trial_Simulator.py`)
- **Sliders (left column):** Total patients, Number of treatments, Noise level, Patients per round
- **Sliders (right column):** Per-treatment success rate (2–5 sliders dynamically), Simulation runs
- Tabs:
  - **"One Trial"** — patient distribution bar chart + allocation history line chart + 3 KPIs
  - **"Repeat 50 Times"** — Monte Carlo box plot + summary table (avg power, % correct)
  - **"How Many Patients Needed?"** — required N, MDE, power curve chart
- All labels in plain English (no "Thompson sampling", "Beta-Bernoulli", "MDE" jargon visible)

### Page 5 — Ask Anything (`04_RAG_Assistant.py`)
- **Backend indicator** in sidebar — `✅ Powered by Google Gemini` / `✅ Powered by Claude` / `⚠️ Demo mode`
- **"Trials to retrieve" slider** (3–10)
- **5 example question buttons** → inject into chat
- **Chat interface** (Streamlit `st.chat_message`)
- Each answer shows: confidence badge + source expander with trial cards + scores
- **Confidence display** (calibrated for `all-MiniLM-L6-v2` cosine similarity on short text):
  - Score > 0.55 → `🟢 High confidence`
  - Score > 0.38 → `🟡 Good match`
  - Score ≤ 0.38 → `🔵 Partial match` (blue, not red — Gemini still answers correctly)
- Source icons use same thresholds consistently
- Collapsible LLM troubleshooting expander (shows env key lengths, active backend)

### Page 6 — Global View (`06_Geographic_Map.py`)
- **Plotly orthographic globe** — drag to rotate, scroll to zoom
- Dark (#1A1816) container, 5 colored region dot sets (North America, Europe, Asia Pacific, Africa, Middle East)
- Hover shows: Disease, City, Region, Trials, Avg patients, Completion %
- **4 KPIs:** Trials Shown, Diseases, Regions, Research Sites
- **Regional bar chart** (horizontal, colored) + **Disease donut chart** (center count)
- **Clean summary table** in expander (condition-level, not city-level — no duplicates)
- Caption: *"Trial locations are derived from condition-to-region mapping. Dots on the globe show research activity density, not individual trial sites."*
- `_CONDITION_COORDS` maps all 5 demo conditions to 5 different regions for visual coverage:
  - Type 2 Diabetes → North America
  - Breast Cancer → Europe
  - Hypertension → Asia Pacific
  - COPD → Middle East
  - Heart Failure → Africa

### Page 7 — Download Your Findings (`05_Report_Generator.py`)
- Checklist expander (trial data / analysis / simulation complete?)
- Config: title, author, condition, which sections to include, outcome variable, N insights
- **3-backend PDF fallback chain:**
  1. WeasyPrint (works with `DYLD_LIBRARY_PATH=/opt/homebrew/lib` on macOS after `brew install pango`)
  2. pdfkit (needs `wkhtmltopdf` binary)
  3. HTML bytes — download as `.html`, open in Chrome → Print → Save as PDF
- Shows info message and correct mime type based on which backend fired
- Persistent download button stays visible after generation

---

## 4. APIs & External Services

| Service | Endpoint / Library | Auth | Notes |
|--------|-------------------|------|-------|
| ClinicalTrials.gov v2 | `GET https://clinicaltrials.gov/api/v2/studies` | **None** (public) | Fetched in `ingestor.py`; `DEMO_MODE=false` or `ingest_live()` |
| Google Gemini | `google-generativeai` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Auto-tries `gemini-2.5-flash → gemini-flash-latest → gemini-2.5-flash-lite → gemini-2.5-pro` |
| Anthropic Claude | `anthropic` SDK | `ANTHROPIC_API_KEY` | Model: `claude-sonnet-4-20250514`; fallback if Gemini not set |
| Demo mode | Deterministic stub | None | Used if neither API key is set |
| MLflow | Local (port 5000) | None | `mlflow ui` to browse; experiment: `CausalTrialAnalysis` |

**Priority:** Gemini → Anthropic → Demo

---

## 5. ML / Data Stack

| Component | Library | What It Does |
|-----------|---------|--------------|
| Data store | DuckDB 0.10 | In-process SQL, zero config, stores `trials` table |
| Data fetch | `requests` + `tenacity` | ClinicalTrials.gov API v2, retry on failure |
| Data quality | Custom pandas rules | 7 rules: NCT ID, enrollment, dates, duplicates, etc. |
| Propensity | scikit-learn `LogisticRegression` | Estimates treatment selection probability (AUC) |
| Causal Forest | EconML `CausalForestDML` | Estimates CATE (individual-level treatment effects) |
| SHAP | `shap` | Feature importance for driving CATE heterogeneity |
| Adaptive sim | Custom Thompson sampling | Beta-Bernoulli bandit, batch allocation, Monte Carlo |
| Power analysis | `statsmodels` `TTestIndPower` | Required N, MDE, power at budget |
| Embeddings | `sentence-transformers` `all-MiniLM-L6-v2` | 384-dim normalized vectors |
| Vector search | FAISS `IndexFlatIP` | Inner product = cosine on normalized vectors |
| LLM | Gemini / Claude / demo | RAG answers grounded in retrieved trial passages |
| Reporting | Jinja2 + WeasyPrint + pdfkit | HTML → PDF with 3-level fallback |
| Experiment tracking | MLflow | Params, metrics, tags per causal run |
| Frontend | Streamlit 1.32 | Multi-page app, custom CSS injected |
| CI | GitHub Actions | 38 tests, coverage, Docker build |
| Deployment | Docker + HuggingFace Spaces | PORT env var, pre-generates demo data at build |

---

## 6. Design System (`app/theme.py` + `.streamlit/config.toml`)

**Fonts:** `Playfair Display` (headings, serif, editorial) + `Inter` (body, sans-serif)

**Palette:**
```
Background:    #F7F5F0  (warm off-white)
Sidebar:       #EFEDE7  (slightly darker)
Primary/CTA:   #C66A3E  (warm terracotta)
Text:          #2D2A26  (near-black warm)
Dark text:     #1A1816  (deep warm black)
Muted text:    #8A857D  (warm gray)
```

**Key CSS classes:**
- `.cti-hero` / `.cti-hero-eyebrow` / `.cti-hero-title` / `.cti-accent` — landing page hero
- `.cti-step-card` — feature cards with hover lift
- `.cti-section-label` — uppercase eyebrow labels before section titles
- `.cti-map-container` — dark rounded container for the globe
- `.cti-chat-shell` / `.cti-chat-brand` / `.cti-chat-title` / `.cti-chat-welcome` — RAG page
- `.cti-glass-card` — frosted card effect

---

## 7. Benchmark Results (Real, from demo data — 300 trials)

| Metric | Value |
|--------|-------|
| ATE (completion_rate) | +24.4% |
| 95% CI | [+18.5%, +30.4%] |
| Subgroup estimates | 10 groups (age × condition) |
| Top effect group | Middle-aged Breast Cancer (CATE +25.1%) |
| Propensity AUC-ROC | 0.566 |
| Validation rules passed | 7/7 |
| RAG index size | 300 trials |
| FAISS index type | `IndexFlatIP` (cosine via normalized IP) |
| Embedding model | `all-MiniLM-L6-v2` (384 dim) |
| Typical top retrieval score | 0.60–0.65 |
| Test suite | 38/38 passing |
| Adaptive sim patient gain | +371 more patients on best arm |
| Monte Carlo power | 100% correct arm identification |

---

## 8. Environment Setup

**`.env` keys:**
```
ANTHROPIC_API_KEY=...       # Optional: Claude for RAG
GEMINI_API_KEY=...          # Optional: Gemini for RAG (priority)
DEMO_MODE=true              # false = fetch from ClinicalTrials.gov API
DB_PATH=data/trials.duckdb
FAISS_INDEX_PATH=data/faiss_index
```

**macOS WeasyPrint fix:**
```bash
# Required once — Pango system lib
brew install pango
# Required each session (or add to ~/.zprofile permanently)
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
```
After this, `from weasyprint import HTML` imports cleanly and reports generate as real PDFs.

**Run locally:**
```bash
pip install -r requirements.txt
python scripts/generate_demo_data.py
DYLD_LIBRARY_PATH=/opt/homebrew/lib streamlit run app/main.py
```

---

## 9. Tests (38 total, all green)

| File | Count | What Is Covered |
|------|-------|----------------|
| `test_causal.py` | 3 | Propensity scorer AUC, HTE model ATE, SHAP importance df |
| `test_ingestor.py` | ~4 | Full ingest pipeline |
| `test_ingestor_parse.py` | 7 | Column mapping, randomized flag, phase/status norm, age, oncology, empty df |
| `test_rag.py` | 2 | Indexer build + search, QA chain demo mode |
| `test_schema.py` | 3 | Schema create, empty stats, demo data load |
| `test_simulator.py` | 5+ | Traditional vs adaptive, MC output, power functions |
| `test_theme.py` | 3 | `inject_theme` import, palette colors in CSS, chat CSS |
| `test_validator.py` | 5 | Valid data, duplicate NCT IDs, null NCT, negative enrollment, clipping |

---

## 10. CI/CD + Deployment

**GitHub Actions** (`.github/workflows/ci.yml`):
- `pip install -r requirements.txt` with caching
- `python scripts/generate_demo_data.py`
- `pytest tests/ --cov=src --cov-report=term-missing`
- Core module import smoke checks
- Docker image build (validates Dockerfile + Pango system libs)

**Docker** (`Dockerfile`):
- Base: `python:3.11-slim`
- Installs: `libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 fonts-liberation`
- Pre-generates demo data at build time
- `EXPOSE 7860 8501` — PORT env var picks the right one
- HuggingFace Spaces: PORT=7860

**HuggingFace Spaces:**
- Username: `jainishpatel1019`
- URL: `https://huggingface.co/spaces/jainishpatel1019/clinical-trial-intelligence`
- SDK: Streamlit (or Docker)
- `app.py` is the HF entry point (launches `app/main.py` via subprocess with correct flags)

---

## 11. Known Limitations & Honest Gaps

| Area | Issue | Status |
|------|-------|--------|
| Globe coordinates | Derived from condition→region mapping, not real per-trial lat/lon from API | By design, noted in caption |
| WeasyPrint on macOS | Needs `DYLD_LIBRARY_PATH=/opt/homebrew/lib` — env var added to `~/.zprofile` | Fixed |
| FAISS re-ranking | Explicit `.sort()` added; FAISS `IndexFlatIP` already returns sorted but now guaranteed | Fixed |
| RAG confidence | Recalibrated to 0.55/0.38 thresholds for `all-MiniLM-L6-v2` on short domain text | Fixed |
| `wkhtmltopdf` | Not installed — pdfkit silently falls through to HTML | Works via fallback |
| Demo data | Synthetic 300 trials, not real patient outcomes | Acceptable for portfolio |
| `streamlit` constraint | Can't do custom React frontend — limited interactive feel vs full web app | Accepted |
| Readme badges | GitHub Actions badge points to `jainishpatel1019` — repo must be public | Pending deploy |
| Screenshots | Placeholder `*(add screenshot)*` in README | Pending HF deployment |

---

## 12. Suggested Prompt to Give Claude

```
I'm building a clinical trial intelligence platform. The full project brief is above.
Please analyze the codebase description and tell me:

1. What are the top 3 things that would make this most impressive to a Data Science hiring manager?
2. What technical gaps or bugs might a senior engineer spot?
3. What UX improvements would make this feel like a real product vs a student project?
4. What would you add to the RAG pipeline to make it more robust?
5. Give me a prioritized improvement backlog with effort estimates (S/M/L).

If I attach screenshots of the running app, also comment on visual consistency and hierarchy.
```

---

## 13. Images to Attach

Take screenshots of these pages and attach them alongside this document:

1. **Home page** — hero, KPI metrics, feature cards
2. **Data Explorer** — with filters active, showing charts
3. **Causal Analysis** — after running (showing ATE metrics + subgroup table)
4. **Trial Simulator** — "One Trial" tab with charts visible
5. **RAG Assistant** — a real answer with 🟢 High confidence showing
6. **Geographic Map** — globe rotated to show Africa/Middle East dots
7. **Report Generator** — after generating (PDF or HTML download button visible)

> App is running at: **http://localhost:8501**
