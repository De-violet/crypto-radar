# ══════════════════════════════════════════════
# Crypto Radar v7.0 — Dockerfile for Fly.io (256MB RAM challenge)
# ══════════════════════════════════════════════
# Single container running 2 processes via supervisord:
#   1. FastAPI (uvicorn) — serves /health, /api/v1/* + WebSocket
#   2. Discord bot — runs in background task within FastAPI lifespan
#
# Memory budget (256MB):
#   - Python interpreter: ~30MB
#   - pandas + mplfinance (lazy import di radar): ~80MB when loaded
#   - FastAPI + uvicorn: ~20MB
#   - discord.py + aiohttp: ~25MB
#   - Buffer untuk scanner runtime: ~100MB
# Matplotlib di-disable di chart generation (return None) kalau RAM sempit.
# ══════════════════════════════════════════════

FROM python:3.12-slim AS base

LABEL org.opencontainers.image.title="crypto-radar" \
      org.opencontainers.image.description="Multi-strategy crypto sniper — FastAPI + Discord bot" \
      org.opencontainers.image.source="https://github.com/De-violet/crypto-radar" \
      org.opencontainers.image.licenses="MIT"

# ── System deps (minimal, for 256MB image) ──
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ curl tini \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps (cached layer) ─────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── App code ───────────────────────────────────
COPY . .

# ── Non-root user ──────────────────────────────
RUN useradd --create-home --uid 1000 --shell /bin/bash radarrunner \
    && mkdir -p /app/backtest_reports /app/data \
    && chown -R radarrunner:radarrunner /app
USER radarrunner

# ── Runtime env ────────────────────────────────
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg

EXPOSE 8080

# ── Healthcheck ──
HEALTHCHECK --interval=60s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

# ── Tini as PID 1 for proper SIGTERM ──
ENTRYPOINT ["/usr/bin/tini", "--"]

# ── Default: jalan FastAPI (Discord bot akan start otomatis di lifespan) ──
CMD ["python", "-m", "uvicorn", "apps.api.main:app", \
     "--host", "0.0.0.0", "--port", "8080", \
     "--workers", "1", "--log-level", "info", "--no-access-log"]
