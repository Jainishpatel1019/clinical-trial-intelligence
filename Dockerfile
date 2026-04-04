FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/raw data/processed data/faiss_index

# Generate demo data so the app works without live API
RUN python scripts/generate_demo_data.py

# HuggingFace Spaces uses port 7860; local Docker uses 8501.
# The CMD picks the right port based on SPACE_ID env (set automatically by HF).
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/_stcore/health || exit 1

EXPOSE 7860 8501

CMD ["sh", "-c", "streamlit run app/main.py \
    --server.port=${PORT:-7860} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false"]
