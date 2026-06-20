# Redrob Hackathon — Candidate Discovery System
# CPU-only, offline ranking pipeline

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (including gdown for data download)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gdown

# Pre-download the BGE-small model
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('BAAI/bge-small-en-v1.5')"

# Copy the codebase (large files excluded via .dockerignore)
COPY . .

# Download pre-computed embeddings and cache from Google Drive
# This bakes the data into the image so the container runs offline
RUN python download_precomputed.py

# Environment variables for offline operation
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_DISABLE_TELEMETRY=1
ENV PYTHONUNBUFFERED=1
ENV DATASET_DIR="/app/Dataset/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge"

RUN mkdir -p /app/results

CMD ["python", "generate_submission.py"]