FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GIT_PYTHON_REFRESH=quiet \
    PATH="/opt/venv/bin:$PATH" \
    MODEL_STORAGE_PATH=/app/model_artifacts \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends curl libgomp1 libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 temperature \
    && useradd --system --uid 10001 --gid temperature --home-dir /app temperature

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY --chown=temperature:temperature . .

RUN mkdir -p /app/model_artifacts && chown -R temperature:temperature /app

USER temperature
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl --fail --silent "http://127.0.0.1:${PORT}/health" >/dev/null || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
