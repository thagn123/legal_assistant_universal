FROM python:3.11-slim

WORKDIR /app

# System dependencies for OCR (tesseract + Vietnamese language pack)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    antiword \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
# Install CPU-only torch first so sentence-transformers doesn't pull the full
# CUDA wheel (~1.5 GB of cudnn/nccl/triton we don't need in Docker).
RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Application source
COPY . .

# Persistent data directory (mounted as a volume in production)
RUN mkdir -p /data

EXPOSE 8000

# Pre-warm the embedding model cache so the first request isn't slow.
# Uses python -m uvicorn (avoids PATH issues in some base images).
CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
