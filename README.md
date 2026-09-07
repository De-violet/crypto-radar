# 🎯 Crypto Radar v8.0 — Multi-Strategy Sniper (Telegram Edition)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot%20API-2CA5E0?logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **High-performance 24/7 crypto scanner & interactive Telegram bot.**  
> Memindai pasar Binance secara real-time menggunakan konfirmasi multi-timeframe (4H → 1H → 5m), validasi AI Analyst cerdas, kalkulasi otomatis Risk:Reward 1:2, serta pengiriman sinyal sniper berfoto candlestick ke Telegram Topic / Supergroup Anda.

---

## 📑 Daftar Isi

- [Arsitektur Sistem](#-arsitektur-sistem)
- [Fitur Utama](#-fitur-utama)
- [Arsitektur Filter Bertingkat](#-arsitektur-filter-bertingkat)
- [Perintah Interaktif Telegram](#-perintah-interaktif-telegram)
- [Panduan Instalasi & Penggunaan](#-panduan-instalasi--penggunaan)
  - [1. Buat Bot Telegram](#1-buat-bot-telegram)
  - [2. Clone & Siapkan Environment](#2-clone--siapkan-environment)
  - [3. Konfigurasi Variabel Lingkungan](#3-konfigurasi-variabel-lingkungan)
  - [4. Jalankan Aplikasi](#4-jalankan-aplikasi)
- [Deployment 24/7 (Linux systemd)](#-deployment-247-linux-systemd)
- [Referensi Konfigurasi (.env)](#-referensi-konfigurasi-env)
- [Disclaimer Risiko](#-disclaimer-risiko)
- [Lisensi](#-lisensi)

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
                                         │ Sinyal Lolos Strategi
                                         ▼
                         ┌─────────────────────────────────┐
                         │      AI Technical Analyst       │
                         │  • Technical Score (0-100)      │
                         │  • Volume & Trend Validation    │
                         └───────────────┬─────────────────┘
                                         │ Sinyal Disetujui
                                         ▼
                         ┌─────────────────────────────────┐
                         │       Risk & Anti-Spam          │
                         │  • R:R 1:2 (SL Buffer 1.0-1.5%) │
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
                         │    Kanal / Topic Telegram Anda  │
                         │    (Forum Thread ID Support)    │
                         └─────────────────────────────────┘
```

---

## ✨ Fitur Utama

- 🎯 **Multi-Strategy Sniper**: Dilengkapi 3 strategi bawaan: **Reversal** (pantulan support), **Breakout** (tembus resistensi), dan **Trend Follow** (pullback EMA).
- 🧠 **AI Technical Analyst**: Validasi sinyal otomatis berbasis skor teknikal (Trend, Volume, Stochastic/RSI, Volatilitas ATR) serta analisis instan on-demand via perintah `/ai <COIN>`.
- ⏱ **Multi-Timeframe Validation**: Menyaring noise pasar dengan analisis bertingkat dari 4H (Support & Trend makro), 1H (Momentum & Stochastic), hingga 5m (Candle Pinbar / Volume Entry).
- 🏷 **Dukungan Forum Topics (Thread ID)**: Pengiriman sinyal dapat diarahkan langsung ke sub-topik tertentu pada Telegram Supergroup tanpa mengganggu topik obrolan utama.
- 🤖 **Interactive Telegram Bot**: Mendukung polling perintah interaktif (`/scan`, `/ai`, `/status`, `/top`, `/strategies`, `/id`, `/help`, `/ping`).
- 📊 **Automated Candlestick Charts**: Setiap sinyal valid otomatis dilengkapi gambar grafik candlestick 5m berlatar gelap yang digenerate secara lokal (`mplfinance`).
- 🔘 **One-Click Trading Buttons**: Tombol interaktif langsung menuju Binance Chart, TradingView, dan CoinGecko pada setiap alert.
- 🛡 **Anti-Spam Memory Cooldown**: Mencegah spam sinyal koin berulang dengan cooldown berbasis jam dan proteksi POSIX file locking (`fcntl`).
- 🌐 **Anti Geo-Block Failover**: Dilengkapi multi-endpoint fallback Binance (`data-api.binance.vision`) agar bot tetap berjalan lancar dari VPS mana pun tanpa terhalang geo-restriction (HTTP 451).

---

## 🔍 Arsitektur Filter Bertingkat

Setiap koin harus melewati seluruh tahapan filter sebelum sinyal dikirim:

| Timeframe | Komponen yang Diperiksa | Kriteria Lolos (Contoh: Reversal) |
|---|---|---|
| **4H** | Support Level & Volume | Menguji level support 20-candle + Candle memantul (Bullish) + Volume spike $\ge 1.5\times$ rata-rata. |
| **1H** | Osilator Stochastic (5, 3, 3) | Garis %K berada di area oversold ($\le 20$). |
| **5m** | Pinbar Rejection | Candle 5m Bullish dengan ekor bawah (lower wick) $\ge 1.5\times$ ukuran body. |
| **AI Filter** | Validasi Skor Teknikal | Memastikan kondisi tidak overbought ekstrem dan volume sehat. |

### Rencana Eksekusi (Risk:Reward 1:2)
- **Entry**: Harga penutupan candle 5m sinyal.
- **Stop Loss (SL)**: Level support/low candle dikurangi buffer 1.0% – 1.5%.
- **Take Profit (TP)**: `Entry + (2 × (Entry - SL))` (Target reward minimal 2x lipat risiko).

---

## 💬 Perintah Interaktif Telegram

Kirim perintah berikut langsung ke bot Anda di Telegram:

| Perintah | Deskripsi |
|---|---|
| `/scan` atau `/radar` | Memicu scanner pasar seketika di Binance (Top 100 koin). |
| `/ai <COIN>` | Analisis teknikal mendalam untuk koin tertentu (contoh: `/ai BTC`, `/ai SOL`). |
| `/status` | Menampilkan uptime bot, waktu scan terakhir, dan jumlah cooldown aktif. |
| `/top` | Menampilkan daftar 10 koin USDT dengan volume transaksi tertinggi. |
| `/strategies` | Menampilkan ringkasan logika 3 strategi sniper yang aktif. |
| `/id` | Menampilkan Chat ID dan Topic/Thread ID saat ini (berguna untuk konfigurasi topik). |
| `/help` | Panduan lengkap penggunaan bot dan penjelasan manajemen risiko. |
| `/ping` | Cek koneksi bot ke Telegram Bot API dan Binance API. |

> **Tips Grup/Forum**: Di supergroup dengan banyak bot, Anda juga dapat menggunakan perintah ber-prefix `/radar_*` (misal: `/radar_scan`, `/radar_status`, `/radar_ai`).

---

## 🚀 Panduan Instalasi & Penggunaan

### 1. Buat Bot Telegram

1. Buka Telegram dan cari **[@BotFather](https://t.me/BotFather)**.
2. Kirim `/newbot` dan ikuti instruksi hingga mendapatkan **Bot Token** (contoh: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`).
3. Dapatkan **Chat ID** Anda:
   - Mulai chat dengan bot Anda (kirim `/start`).
   - Cek ID chat Anda via perintah `/id` ke bot atau via `@userinfobot`.

### 2. Clone & Siapkan Environment

```bash
# Clone repository
git clone https://github.com/De-violet/crypto-radar.git
cd crypto-radar

# Buat virtual environment (Python 3.10+)
python3 -m venv venv
source venv/bin/activate

# Install dependensi
pip install -r requirements.txt
```

### 3. Konfigurasi Variabel Lingkungan

Salin template konfigurasi:
```bash
cp .env.example .env
```

Buka file `.env` dan masukkan konfigurasi Anda:
```env
# Kredensial Telegram
TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID="123456789"

# ID Topik / Thread Supergroup (Opsional, isi jika ingin sinyal masuk ke topik spesifik)
TELEGRAM_THREAD_ID="107"
```

### 4. Jalankan Aplikasi

#### A. Mode Daemon Penuh (Bot Interaktif + Autonomous Scanner)
Menjalankan bot Telegram interaktif sekaligus scanner otomatis berkala:
```bash
python main.py
```

#### B. Mode One-Shot (1x Scan & Selesai)
Sangat cocok untuk testing atau integrasi scheduler:
```bash
python main.py --once
```

#### C. Mode Uji Coba Tanpa Mengirim Alert (`--dry-run`)
```bash
python main.py --once --dry-run
```

---

## ⚙️ Deployment 24/7 (Linux systemd)

Untuk menjalankan Crypto Radar tanpa henti di latar belakang pada server Linux atau VPS, gunakan `systemd`.

### Sebagai User Service (Tanpa Akses Root)
Buat file `~/.config/systemd/user/telegram-radar.service`:
```ini
[Unit]
Description=Crypto Radar v8.0 Sniper Scanner (24/7 Auto-Loop)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/deviolete/Projects/crypto-radar
ExecStart=/home/deviolete/Projects/crypto-radar/venv/bin/python -u main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/deviolete/Projects/crypto-radar/.env

# Proteksi limit resource
LimitNOFILE=65536

[Install]
WantedBy=default.target
```

Aktifkan dan jalankan service:
```bash
systemctl --user daemon-reload
systemctl --user enable --now telegram-radar
systemctl --user status telegram-radar
```

Pantau log secara langsung:
```bash
journalctl --user -u telegram-radar -f
```

---

## ⚙️ Referensi Konfigurasi (.env)

| Variabel | Tipe | Default | Keterangan |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | string | `""` | Token bot dari @BotFather. |
| `TELEGRAM_CHAT_ID` | string | `""` | ID penerima alert Telegram (User ID atau Group ID). |
| `TELEGRAM_THREAD_ID` | string | `""` | ID Topik / Thread forum Telegram (opsional). |
| `SCAN_LIMIT` | integer | `100` | Jumlah koin Binance paling likuid yang dipantau. |
| `SCAN_INTERVAL_MINUTES` | integer | `15` | Interval scan otomatis latar belakang (menit). |
| `VOL_SPIKE_THRESHOLD` | float | `1.5` | Pengali volume spike dari rata-rata 20 candle. |
| `STOCH_OVERSOLD` | integer | `20` | Batas bawah Stochastic %K 1H untuk strategi reversal. |
| `COOLDOWN_HOURS` | float | `4.0` | Jeda anti-spam antar sinyal pada koin yang sama. |
| `STRATEGIES` | string | `""` | Filter strategi aktif (`reversal,breakout,trend_follow`). |
| `MEMORY_FILE` | string | `alerted_coins.json` | Path file penyimpanan memori cooldown lokal. |

---

## ⚠️ Disclaimer Risiko

> **PENTING**: Perangkat lunak ini dibuat hanya untuk tujuan edukasi dan analisis data pasar. Perdagangan cryptocurrency memiliki volatilitas dan risiko finansial yang tinggi. Selalu terapkan manajemen risiko serta ukuran posisi yang terukur. Penulis tidak bertanggung jawab atas keputusan investasi atau kerugian finansial apa pun yang terjadi.

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah ketentuan [MIT License](LICENSE).
