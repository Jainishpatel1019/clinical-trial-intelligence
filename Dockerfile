FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/raw data/processed data/faiss_index

RUN python scripts/generate_demo_data.py

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/_stcore/health || exit 1

EXPOSE 7860 8501

CMD ["sh", "-c", "streamlit run app/main.py \
    --server.port=${PORT:-7860} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false"]
