# 🚀 Panduan Deployment — Crypto Radar v8.0 (Telegram Edition)

Panduan lengkap untuk men-deploy Crypto Radar ke lingkungan produksi agar dapat memantau pasar kripto 24/7 dan mengirim sinyal secara stabil ke Telegram Anda.

---

## 📋 Pilihan Metode Deployment

Pilih metode yang paling sesuai dengan kebutuhan Anda:

| Metode | Biaya | Tingkat Kesulitan | Kebutuhan Server |
|---|---|---|---|
| **1. Docker Compose** | Murah ($3–5/bln) | Sangat Mudah ⭐ | VPS Linux (Ubuntu / Debian) |
| **2. Systemd Service** | Murah ($3–5/bln) | Mudah ⭐⭐ | VPS Linux (Ubuntu / Debian) |

---

## 🐳 Metode 1: Docker Compose (Direkomendasikan untuk VPS)

Metode ini paling stabil, terisolasi, dan mudah di-manage di VPS mana pun (DigitalOcean, Hetzner, AWS Lightsail, Linode, dll).

### Langkah 1: Siapkan VPS & Docker
Pastikan Docker dan Docker Compose sudah terpasang di VPS Anda:
```bash
# Update paket
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### Langkah 2: Clone Repository & Konfigurasi
```bash
git clone https://github.com/De-violet/crypto-radar.git
cd crypto-radar

# Buat file konfigurasi .env
cp .env.example .env
nano .env
```
Isi variabel wajib:
```env
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="123456789"
SCAN_LIMIT=100
SCAN_INTERVAL_MINUTES=15
```

### Langkah 3: Jalankan Kontainer
```bash
# Build dan jalankan di background
docker compose up -d

# Cek status kontainer
docker compose ps

# Pantau log secara real-time
docker compose logs -f
```

Kontainer dikonfigurasi dengan `restart: unless-stopped`, sehingga otomatis hidup kembali saat VPS reboot.

---

## ⚙️ Metode 2: Linux systemd Service Daemon

Cocok jika Anda ingin menjalankan bot langsung di sistem Linux tanpa Docker.

### Langkah 1: Siapkan Python & Virtualenv
```bash
sudo apt update && sudo apt install -y python3 python3-venv git

git clone https://github.com/De-violet/crypto-radar.git /opt/crypto-radar
cd /opt/crypto-radar

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

cp .env.example .env
nano .env
```

### Langkah 2: Buat Unit File systemd
Buat file service di `/etc/systemd/system/crypto-radar.service`:
```ini
[Unit]
Description=Crypto Radar v8.0 Telegram Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/crypto-radar
ExecStart=/opt/crypto-radar/venv/bin/python main.py
Restart=always
RestartSec=15
EnvironmentFile=/opt/crypto-radar/.env

# Proteksi memori & sistem
LimitNOFILE=65536
KillMode=mixed
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
```

### Langkah 3: Aktifkan dan Jalankan Service
```bash
# Muat ulang konfigurasi systemd
sudo systemctl daemon-reload

# Aktifkan auto-start saat boot
sudo systemctl enable crypto-radar

# Jalankan service sekarang
sudo systemctl start crypto-radar

# Cek status operasional
sudo systemctl status crypto-radar

# Pantau log live
sudo journalctl -u crypto-radar -f
```


---

## 🔒 Keamanan & Praktik Terbaik (Token Hygiene)

1. **JANGAN PERNAH Commit File `.env`:**
   File `.gitignore` sudah memblokir `.env`, tetapi selalu periksa `git status` sebelum melakukan commit.
2. **Revoke Token Jika Bocor:**
   Jika token bot Telegram Anda tidak sengaja ter-publish ke internet, segera buka `@BotFather` dan jalankan `/revoke` untuk mengganti token baru dalam hitungan detik.
3. **Batasi Hak Akses Chat:**
   Gunakan ID pengguna spesifik Anda pada `TELEGRAM_CHAT_ID`. Jika ingin digunakan di grup atau channel, pastikan bot memiliki hak kirim pesan & gambar.

---

## 🛠 Troubleshooting

### 1. Bot Telegram tidak merespon perintah
- Pastikan bot dijalankan dalam mode daemon (`python main.py`), bukan mode one-shot (`--once`).
- Periksa `TELEGRAM_BOT_TOKEN` di `.env` apakah sudah sesuai tanpa spasi tambahan.
- Uji koneksi ke bot dengan mengirim `/ping`.

### 2. Binance API Error (451 / Geo-Restriction)
- Crypto Radar sudah dilengkapi failover ke `https://data-api.binance.vision`.
- Mirror publik ini tidak membatasi wilayah geografi (AS / Eropa / Asia).
- Jika ada masalah jaringan pada VPS, periksa koneksi DNS (`curl -I https://data-api.binance.vision/api/v3/ping`).

### 3. Memori Cooldown Tidak Tersimpan
- Pastikan direktori bot memiliki hak tulis (write permission).
- Pada Docker, pastikan volume `./alerted_coins.json` di-mount dengan benar di `docker-compose.yml`.
