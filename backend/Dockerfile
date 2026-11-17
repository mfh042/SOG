FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY app ./app
COPY run.py ./run.py

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SOP_UPLOAD_DIR=/app/uploads \
    DB_HOST=postgres \
    DB_PORT=5432 \
    DB_NAME=sog \
    DB_USER=sog \
    DB_PASSWORD=sog_pass \
    CORS_ORIGINS=http://localhost,http://localhost:80,http://127.0.0.1

RUN mkdir -p /app/uploads/sop

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uv", "run", "python", "run.py"]