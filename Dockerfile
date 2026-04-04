# # syntax=docker/dockerfile:1

# # ===== Base image =====
# FROM python:3.10-slim AS base

# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PIP_NO_CACHE_DIR=1

# # System deps (add build tools only if needed)
# RUN apt-get update \
#  && apt-get install -y --no-install-recommends \
#       curl ca-certificates build-essential \
#  && rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# # ===== Dependencies layer =====
# FROM base AS deps

# # Leverage Docker cache for dependencies
# COPY requirements.txt ./
# RUN pip install --upgrade pip \
#  && pip install -r requirements.txt

# # ===== Runtime image =====
# FROM python:3.10-slim AS runtime

# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PIP_NO_CACHE_DIR=1

# # Smaller runtime image
# RUN apt-get update \
#  && apt-get install -y --no-install-recommends \
#       ca-certificates fonts-dejavu-core \
#  && rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# # Copy installed deps from deps stage
# COPY --from=deps /usr/local/lib/python3.10 /usr/local/lib/python3.10
# COPY --from=deps /usr/local/bin /usr/local/bin

# # Copy app code (only necessary files)
# COPY alembic.ini ./
# COPY alembic ./alembic
# COPY config ./config
# COPY enums ./enums
# COPY models ./models
# COPY routers ./routers
# COPY schemas ./schemas
# COPY templates ./templates
# COPY routers ./routers
# COPY utils ./utils
# COPY main.py ./

# # Expose API port
# EXPOSE 8000

# # Healthcheck (simple TCP check)
# HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
#   CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',8000)); s.close()" || exit 1

# # Run DB migrations then start the server
# CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers"] 

# syntax=docker/dockerfile:1

# =========================
# Base image
# =========================
FROM python:3.10-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  DEBIAN_FRONTEND=noninteractive

# System deps (only what is needed to build wheels)
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  curl \
  ca-certificates \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# =========================
# Dependencies layer
# =========================
FROM base AS deps

COPY requirements.txt ./

RUN pip install --upgrade pip \
  && pip install -r requirements.txt

# =========================
# Runtime image
# =========================
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  DEBIAN_FRONTEND=noninteractive

# Install runtime system dependencies
# - ffmpeg: audio/video processing
# - libreoffice: document conversion
# - fonts: avoid blank PDFs
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  ca-certificates \
  ffmpeg \
  libreoffice \
  libreoffice-writer \
  libreoffice-calc \
  libreoffice-impress \
  fonts-dejavu-core \
  fonts-liberation \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies from deps stage
COPY --from=deps /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application files
COPY alembic.ini ./
COPY alembic ./alembic
COPY config ./config
COPY enums ./enums
COPY models ./models
COPY routers ./routers
COPY schemas ./schemas
COPY templates ./templates
COPY utils ./utils
COPY tasks ./tasks
COPY celery_app.py ./
COPY main.py ./

# Expose API port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',8000)); s.close()" || exit 1

# Run DB migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers"]
# CMD ["sh", "-c", "alembic upgrade head && gunicorn main:app \
#   --worker-class gthread \
#   --workers 4 \
#   --threads 2 \
#   --timeout 600 \
#   --bind 0.0.0.0:8000"]