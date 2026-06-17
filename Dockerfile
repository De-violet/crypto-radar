# ══════════════════════════════════════════════
# Crypto Radar v7.0 — Dockerfile for HuggingFace Spaces
# ══════════════════════════════════════════════
# HuggingFace Spaces Docker SDK specifics:
#   - Must listen on port 7860 (HF Spaces default)
#   - Free tier: 16GB RAM, 2 vCPU shared (much more than Fly.io 256MB!)
#   - Persistent storage: /data (must opt-in via Space settings)
#   - Filesystem mostly read-only except /data, /tmp
#   - Auto-build on every push to HF repo (we sync from GitHub)
#
# Single container running 1 process:
#   - FastAPI (uvicorn) — serves /health, /api/v1/* + WebSocket
#   - Discord bot — runs as background task within FastAPI lifespan
# ══════════════════════════════════════════════

FROM python:3.12-slim

LABEL org.opencontainers.image.title="crypto-radar" \
      org.opencontainers.image.description="Multi-strategy crypto sniper — FastAPI + Discord bot (HF Spaces)" \
      org.opencontainers.image.source="https://github.com/De-violet/crypto-radar" \
      org.opencontainers.image.licenses="MIT"

# ── System deps ──
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

# ── Non-root user (HF Spaces requires UID 1000 named "user") ──
# Ref: https://huggingface.co/docs/hub/spaces-sdks-docker#permissions
RUN useradd -m -u 1000 user \
    && mkdir -p /data /app/backtest_reports \
    && chown -R user:user /data /app
USER user

# ── HF Spaces mandatory env vars ──
ENV PORT=7860 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# HF Spaces expects container to listen on 7860
EXPOSE 7860

# ── Healthcheck ──
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:7860/health" || exit 1

# ── Tini as PID 1 for proper SIGTERM ──
ENTRYPOINT ["/usr/bin/tini", "--"]

# ── Run FastAPI (Discord bot starts inside lifespan) ──
CMD ["python", "-m", "uvicorn", "apps.api.main:app", \
     "--host", "0.0.0.0", "--port", "7860", \
     "--workers", "1", "--log-level", "info"]
