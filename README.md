# 🎯 Crypto Radar v8.0 — Multi-Strategy Sniper (Telegram Edition)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot%20API-2CA5E0?logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **High-performance 24/7 crypto scanner & interactive Telegram bot.**  
> Memindai pasar Binance secara real-time menggunakan konfirmasi multi-timeframe (4H → 1H → 5m), menghitung Risk:Reward 1:2 otomatis, dan mengirim sinyal sniper lengkap dengan grafik candlestick ke Telegram Anda.

---

## 📑 Daftar Isi

- [Arsitektur Sistem](#-arsitektur-sistem)
- [Fitur Utama](#-fitur-utama)
- [Arsitektur Filter Bertingkat](#-arsitektur-filter-bertingkat)
- [Perintah Interaktif Telegram](#-perintah-interaktif-telegram)
- [Panduan Instalasi & Penggunaan](#-panduan-instalasi--penggunaan)
  - [1. Buat Bot Telegram](#1-buat-bot-telegram)
  - [2. Clone & Siapkan Environment](#2-clone--siapkan-environment)
  - [3. Jalankan Aplikasi](#3-jalankan-aplikasi)
- [Deployment 24/7](#-deployment-247)
- [Referensi Konfigurasi (.env)](#-referensi-konfigurasi-env)
- [Disclaimer Risiko](#-disclaimer-risiko)

---

## 🏗 Arsitektur Sistem

```
                         ┌─────────────────────────────────┐
                         │   Binance Public Market Data    │
                         │   (Multi-Endpoint Failover)     │
                         └───────────────┬─────────────────┘
                                         │ Klines / 24h Ticker
                                         ▼
                         ┌─────────────────────────────────┐
                         │      Dynamic Coin Scanner       │
                         │   (Top 100 USDT Quote Volume)   │
                         └───────────────┬─────────────────┘
                                         │ Filter Stables & Leveraged
                                         ▼
                         ┌─────────────────────────────────┐
                         │     Multi-Strategy Engine       │
                         │  • Reversal (Support Bounce)    │
                         │  • Breakout (Momentum Trend)    │
                         │  • Trend Follow (Pullback EMA)  │
                         └───────────────┬─────────────────┘
                                         │ Sinyal PASS
                                         ▼
                         ┌─────────────────────────────────┐
                         │       Risk & Anti-Spam          │
                         │  • R:R 1:2 (SL Buffer 1.5%)     │
                         │  • JSON Memory (File Locking)   │
                         └───────────────┬─────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
       ┌─────────────────────────┐               ┌─────────────────────────┐
       │   Auto Chart Generator  │               │   Telegram Bot Engine   │
       │   (mplfinance Dark PNG) │               │   (Alerts + Commands)   │
       └────────────┬────────────┘               └────────────┬────────────┘
                    └────────────────────┬────────────────────┘
                                         │ Photo + HTML Alert + Buttons
                                         ▼
                         ┌─────────────────────────────────┐
                         │    Kanal / Chat Telegram Anda   │
                         └─────────────────────────────────┘
```

---

## ✨ Fitur Utama

- 🎯 **Multi-Strategy Sniper**: Dilengkapi 3 strategi bawaan: **Reversal**, **Breakout**, dan **Trend Follow**.
- ⏱ **Multi-Timeframe Validation**: Menyaring noise dengan analisis berurutan dari 4H (Support/Tren), 1H (Momentum/Stochastic), hingga 5m (Candle Pinbar Entry).
- 🤖 **Interactive Telegram Bot**: Mendukung perintah slash (`/scan`, `/status`, `/top`, `/strategies`, `/help`, `/ping`) langsung dari aplikasi Telegram Anda.
- 📊 **Automated Candlestick Charts**: Setiap sinyal valid otomatis dilengkapi gambar grafik candlestick 5m yang digenerate secara lokal (`mplfinance`).
- 🔘 **One-Click Trading Buttons**: Tombol inline menuju Binance Chart, TradingView, dan CoinGecko pada setiap notifikasi sinyal.
- 🛡 **Anti-Spam Memory**: Cooldown per koin & strategi dengan POSIX file locking (`fcntl`) untuk mencegah alert ganda saat restart atau race condition.
- 🌐 **Anti Geo-Block Failover**: Menggunakan `data-api.binance.vision` dan fallback endpoint resmi lainnya sehingga dapat dijalankan dari IP mana pun (termasuk server US) tanpa batasan HTTP 451.

---

## 🔍 Arsitektur Filter Bertingkat

Setiap koin harus lolos 3 gerbang verifikasi sebelum sinyal dikirim:

| Timeframe | Komponen yang Diperiksa | Kriteria Lolos (Contoh: Reversal) |
|---|---|---|
| **4H** | Support Level & Volume | Harga menguji support 20-candle + Candle memantul (Bullish) + Volume spike $\ge 1.5\times$ rata-rata. |
| **1H** | Osilator Stochastic (5, 3, 3) | Garis %K berada di area oversold ($\le 20$). |
| **5m** | Pinbar Rejection | Candle 5m terkonfirmasi Bullish dengan lower wick (ekor bawah) $\ge 1.5\times$ ukuran body. |

### Rencana Eksekusi (Risk:Reward 1:2)
- **Entry**: Harga penutupan candle 5m sinyal.
- **Stop Loss (SL)**: Level support dikurangi buffer 1.5%.
- **Take Profit (TP)**: `Entry + (2 × (Entry - SL))` (Target reward minimal 2x lipat risiko).

---

## 💬 Perintah Interaktif Telegram

Kirim perintah berikut langsung ke bot Anda di Telegram:

| Perintah | Deskripsi |
|---|---|
| `/scan` | Memicu scanner pasar seketika di Binance (Top 100 koin). |
| `/status` | Menampilkan uptime bot, waktu scan terakhir, dan jumlah cooldown. |
| `/top` | Menampilkan daftar 10 koin USDT dengan volume transaksi tertinggi. |
| `/strategies` | Menampilkan detail logika 3 strategi trading yang aktif. |
| `/help` | Panduan lengkap cara kerja sistem dan manajemen risiko. |
| `/ping` | Cek koneksi dan respon bot ke Telegram API. |

---

## 🚀 Panduan Instalasi & Penggunaan

### 1. Buat Bot Telegram

1. Buka Telegram dan cari **[@BotFather](https://t.me/BotFather)**.
2. Kirim `/newbot` dan ikuti instruksi hingga mendapatkan **Bot Token** (contoh: `7123456789:AAH...`).
3. Dapatkan **Chat ID** Anda:
   - Mulai chat dengan bot Anda (kirim `/start`).
   - Buka `@userinfobot` di Telegram untuk melihat User ID Anda, **atau**
   - Akses: `https://api.telegram.org/bot<TOKEN_ANDA>/getUpdates` di browser dan cari `"id"` chat Anda.

### 2. Clone & Siapkan Environment

```bash
# Clone repository
git clone https://github.com/De-violet/crypto-radar.git
cd crypto-radar

# Buat virtual environment (Python 3.10, 3.11, atau 3.12)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Konfigurasi Variabel Lingkungan

Salin template konfigurasi:
```bash
cp .env.example .env
```

Buka file `.env` dan masukkan kredensial Telegram Anda:
```env
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="123456789"
```

### 4. Jalankan Aplikasi

#### A. Mode Daemon Penuh (Bot + Background Scanner)
Menjalankan bot Telegram interaktif sekaligus scanner berkala setiap 15 menit:
```bash
python main.py
```

#### B. Mode One-Shot (1x Scan & Selesai)
Sangat cocok untuk dieksekusi via Linux `cron` atau CI runner:
```bash
python main.py --once
```

#### C. Mode Uji Coba Tanpa Mengirim Alert (`--dry-run`)
```bash
python main.py --once --dry-run
```

---

## 🐳 Deployment 24/7

### Opsi 1: Docker Compose (Direkomendasikan untuk VPS)

Pastikan file `.env` sudah terisi, lalu jalankan:
```bash
docker compose up -d
```

Cek log kontainer:
```bash
docker compose logs -f
```

### Opsi 2: Linux systemd Service

Buat file unit `/etc/systemd/system/crypto-radar.service`:
```ini
[Unit]
Description=Crypto Radar Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/crypto-radar
ExecStart=/home/ubuntu/crypto-radar/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/ubuntu/crypto-radar/.env

[Install]
WantedBy=multi-user.target
```

Aktifkan service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now crypto-radar
sudo journalctl -u crypto-radar -f
```



---

## ⚙️ Referensi Konfigurasi (.env)

| Variabel | Tipe | Default | Keterangan |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | string | `""` | Token bot dari @BotFather. |
| `TELEGRAM_CHAT_ID` | string | `""` | ID penerima alert Telegram. |
| `SCAN_LIMIT` | integer | `100` | Jumlah top volume koin yang dipantau. |
| `SCAN_INTERVAL_MINUTES` | integer | `15` | Interval scan otomatis dalam mode daemon. |
| `VOL_SPIKE_THRESHOLD` | float | `1.5` | Faktor pengali volume spike rata-rata 20 candle. |
| `STOCH_OVERSOLD` | integer | `20` | Batas bawah Stochastic %K 1H. |
| `COOLDOWN_HOURS` | float | `4.0` | Jeda anti-spam antar sinyal pada koin yang sama. |
| `STRATEGIES` | string | `""` | Filter strategi aktif (kosong = semua aktif). |
| `MEMORY_FILE` | string | `alerted_coins.json` | Path file penyimpanan memori cooldown. |

---

## ⚠️ Disclaimer Risiko

> **PENTING**: Perangkat lunak ini dibuat hanya untuk tujuan edukasi dan analisis data pasar. Trading cryptocurrency mengandung risiko tinggi dan tidak cocok untuk semua orang. Selalu terapkan manajemen risiko yang ketat dan gunakan modal yang siap Anda tanggung jika terjadi kerugian. Penulis tidak bertanggung jawab atas keputusan finansial apa pun yang dibuat berdasarkan sinyal dari aplikasi ini.

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah ketentuan [MIT License](LICENSE).
