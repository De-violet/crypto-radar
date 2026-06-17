# ══════════════════════════════════════════════
# Crypto Radar — Multi-Strategy Sniper (v6.0)
# Multi-purpose Docker image:
#   - main.py     → Discord bot + keep-alive HTTP server (default)
#   - radar.py    → Telegram sniper one-shot scan
#   - backtest.py → Backtest engine
# ══════════════════════════════════════════════

FROM python:3.12-slim AS base

# ── Metadata ────────────────────────────────────
LABEL org.opencontainers.image.title="crypto-radar" \
      org.opencontainers.image.description="Multi-strategy crypto sniper bot with Telegram + Discord modes" \
      org.opencontainers.image.source="https://github.com/De-violet/crypto-radar" \
      org.opencontainers.image.licenses="MIT"

# ── System deps (gcc/g++ needed to build pandasTa, matplotlib wheels) ──
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

# ── Non-root user for security ─────────────────
RUN useradd --create-home --uid 1000 --shell /bin/bash radarrunner \
    && mkdir -p /app/backtest_reports \
    && chown -R radarrunner:radarrunner /app
USER radarrunner

# ── Runtime env defaults ───────────────────────
# PORT 7860 is HuggingFace Spaces default; override for Render/Railway.
ENV PORT=7860 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

EXPOSE 7860

# ── Healthcheck: hits keep_alive /health endpoint ──
# Only meaningful for Discord mode (main.py). For radar.py one-shot mode,
# container exits after scan, so healthcheck is a no-op.
HEALTHCHECK --interval=60s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

# Use tini as PID 1 for proper signal forwarding (SIGTERM → bot shutdown)
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default: Discord bot mode.
# Override with: docker run ... python radar.py
#                docker run ... python backtest.py --symbol BTCUSDT --days 30
CMD ["python", "main.py"]
