FROM python:3.12-slim

# Python 3.12 to match the local venv and ADR-004: torch/faiss wheels resolve on
# 3.14 too, but 3.12 is the more battle-tested runtime for native extensions.

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # Bake the model into the image rather than downloading at container start.
    HF_HOME=/opt/hf \
    # Refuse to boot multi-worker. See ADR-007: the FAISS index is in-process,
    # so N workers means N divergent indexes and silent search failures.
    WEB_CONCURRENCY=1

WORKDIR /app

# curl for the healthcheck; default-mysql-client so `docker compose exec` can
# inspect the database without a host install. Removed from the layer to keep
# the image lean.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Install torch from the CPU-only wheel index BEFORE anything else pulls it in.
# On Linux, plain `pip install torch` resolves to the CUDA build: ~2.5GB of
# nvidia libraries this app never touches, since inference runs on CPU. Doing
# this first means sentence-transformers finds torch already satisfied.
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.13.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model at build time. Without this the first container
# start pulls ~80MB from HuggingFace, which makes a cold boot look like a hang
# and breaks entirely on an offline machine.
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
print('embedding model cached into image')"

COPY . .

# The index and uploads are runtime state, mounted as volumes in compose.
RUN mkdir -p data uploads

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

# 127.0.0.1 rather than localhost, for the same IPv6-first resolution reason as
# the frontend healthcheck.
HEALTHCHECK --interval=10s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
