# ══════════════════════════════════════════════
# Crypto Radar v8.0 — Docker Container
# ══════════════════════════════════════════════
FROM python:3.12-slim

LABEL org.opencontainers.image.title="crypto-radar" \
      org.opencontainers.image.description="Multi-strategy crypto sniper scanner & Telegram alert bot" \
      org.opencontainers.image.source="https://github.com/De-violet/crypto-radar" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Instalasi dependency sistem minimal & tini untuk penanganan sinyal PID 1 yang bersih
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Layer dependency Python terpisah agar build cache optimal
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Salin kode aplikasi
COPY . .

# Pastikan file memory anti-spam siap
RUN touch /app/alerted_coins.json

# Environment variables dasar
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MPLBACKEND=Agg

# Gunakan tini sebagai entrypoint untuk handling SIGTERM & SIGINT
ENTRYPOINT ["/usr/bin/tini", "--"]

# Jalankan Telegram Bot Daemon secara default
CMD ["python", "main.py"]
