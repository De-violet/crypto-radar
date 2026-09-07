"""
CRYPTO RADAR v8.0 — Telegram Bot & Background Scanner Daemon
Entry point utama untuk menjalankan Crypto Radar secara penuh di Telegram.

Fitur:
- Mode Daemon: Menjalankan periodic scanner + bot Telegram interaktif bersamaan.
- Mode One-Shot (--once): Menjalankan satu kali scan pasar lalu keluar (cocok untuk cron/GitHub Actions).
- Perintah Telegram:
    /start      - Selamat datang dan informasi bot
    /help       - Panduan lengkap dan daftar perintah
    /scan       - Memicu pemindaian pasar Binance secara langsung
    /status     - Status bot, uptime, waktu scan terakhir, dan cooldown
    /top        - Menampilkan 10 koin USDT dengan volume tertinggi
    /strategies - Ringkasan strategi trading yang aktif
    /ping       - Cek latensi dan konektivitas bot
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

import radar

# Muat variabel lingkungan dari .env jika ada
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("crypto-radar-bot")

# ══════════════════════════════════════════════
# GLOBAL STATE & THREADING LOCK
# ══════════════════════════════════════════════
_START_TIME = time.time()
_LAST_SCAN_TIME: float | None = None
_SCAN_LOCK = threading.Lock()
_RUNNING = True


def get_uptime_str() -> str:
    """Mengembalikan format durasi uptime bot (misal: '2h 15m 30s')."""
    uptime_sec = int(time.time() - _START_TIME)
    hours, rem = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(rem, 60)
    days, hours = divmod(hours, 24)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s"


# ══════════════════════════════════════════════
# HANDLER PERINTAH TELEGRAM
# ══════════════════════════════════════════════
def handle_start(chat_id: int | str):
    """Respon untuk perintah /start."""
    text = (
        "🤖 <b>Selamat datang di Crypto Radar v8.0!</b>\n\n"
        "Saya adalah bot pendeteksi momentum dan sinyal sniper crypto berbasis "
        "analisis multi-timeframe (4H, 1H, 5m) langsung dari Binance Public API.\n\n"
        "⚡ <b>Perintah yang tersedia:</b>\n"
        "• /scan — Jalankan scanner pasar sekarang\n"
        "• /ai <koin> — Analisis AI + Stochastic (5,3,3) koin (misal: /ai BTC)\n"
        "• /status — Cek kesehatan bot, uptime, & memori\n"
        "• /top — Lihat top 10 koin volume Binance\n"
        "• /strategies — Penjelasan 3 strategi aktif\n"
        "• /help — Panduan parameter & R:R\n"
        "• /ping — Tes konektivitas bot\n\n"
        "<i>Gunakan /scan untuk mencari peluang atau /ai BTC untuk analisis AI.</i>"
    )
    radar.send_telegram(text, chat_id=str(chat_id))


def handle_help(chat_id: int | str):
    """Respon untuk perintah /help."""
    text = (
        "📖 <b>PANDUAN PENGGUNAAN CRYPTO RADAR</b>\n"
        "<code>──────────────────────────────</code>\n\n"
        "🎯 <b>Arsitektur Filter Bertingkat:</b>\n"
        "1. <b>4H</b> — Filter Tren & Support Bounce dengan lonjakan volume.\n"
        "2. <b>1H</b> — Filter Momentum / Oscillator (Stochastic 5,3,3 oversold).\n"
        "3. <b>5m</b> — Filter Sniper Entry (Pola Bullish Pinbar terkonfirmasi).\n\n"
        "💰 <b>Manajemen Risiko:</b>\n"
        "• Stop Loss (SL): Berada di bawah level support (-1.5% buffer)\n"
        "• Take Profit (TP): Risk-to-Reward 1:2 otomatis\n"
        "• Anti-Spam: Koin yang memicu sinyal akan masuk cooldown 4 jam.\n\n"
        "🔧 <b>Daftar Perintah:</b>\n"
        "/scan — Memindai top koin secara real-time\n"
        "/ai <koin> — Analisis AI mendalam + Stochastic (5,3,3)\n"
        "/status — Memeriksa status operasional bot\n"
        "/top — Melihat 10 koin paling aktif\n"
        "/strategies — Melihat detail logika strategi\n"
        "/ping — Memastikan bot merespon"
    )
    radar.send_telegram(text, chat_id=str(chat_id))


def handle_ping(chat_id: int | str):
    """Respon untuk perintah /ping."""
    radar.send_telegram("🏓 <b>Pong!</b> Bot aktif dan terhubung ke Binance Public API.", chat_id=str(chat_id))


def handle_strategies(chat_id: int | str):
    """Respon untuk perintah /strategies."""
    from strategies import get_strategies
    active = [s.name for s in get_strategies()]
    text = (
        "📊 <b>STRATEGI TRADING AKTIF</b>\n"
        "<code>──────────────────────────────</code>\n\n"
        f"Status Konfigurasi: <code>{', '.join(active)}</code>\n\n"
        "1️⃣ <b>Reversal (Bottom Fishing)</b>\n"
        "• 4H: Harga menyentuh level support 20-candle + Volume spike >= 1.5x\n"
        "• 1H: Stochastic (5,3,3) Oversold (K <= 20)\n"
        "• 5m: Bullish Pinbar (lower wick >= 1.5x body)\n\n"
        "2️⃣ <b>Breakout (Momentum Continuation)</b>\n"
        "• 4H: Tren naik di atas EMA 50\n"
        "• 1H: Breakout resistance konsolidasi 20-candle\n"
        "• 5m: Konfirmasi volume tinggi pada candle breakout\n\n"
        "3️⃣ <b>Trend Follow (Pullback Entry)</b>\n"
        "• 4H: Tren kuat di atas EMA 20 & EMA 50\n"
        "• 1H: Koreksi sehat mendekati EMA 20\n"
        "• 5m: Rejection pantulan ke arah tren utama"
    )
    radar.send_telegram(text, chat_id=str(chat_id))


def handle_top(chat_id: int | str):
    """Respon untuk perintah /top."""
    radar.send_telegram("⏳ Mengambil data top volume dari Binance...", chat_id=str(chat_id))
    try:
        coins = radar.get_top_volume_coins(limit=10)
        if not coins:
            radar.send_telegram("❌ Gagal mengambil data pasar Binance.", chat_id=str(chat_id))
            return

        lines = ["🏆 <b>TOP 10 KOIN USDT PALING AKTIF (24H)</b>", "<code>──────────────────────────────</code>"]
        for idx, symbol in enumerate(coins, 1):
            coin = symbol.replace("USDT", "")
            lines.append(f"{idx}. <b>{coin}</b> — <code>{symbol}</code>")
        lines.append("\n<i>Data bersumber dari Binance Public API.</i>")
        radar.send_telegram("\n".join(lines), chat_id=str(chat_id))
    except Exception as e:
        log.error(f"Error pada perintah /top: {e}")
        radar.send_telegram(f"❌ Terjadi kesalahan: {e}", chat_id=str(chat_id))


def handle_status(chat_id: int | str):
    """Respon untuk perintah /status."""
    global _LAST_SCAN_TIME
    memory = radar.load_memory()
    cooldown_count = sum(1 for k in memory if radar.is_on_cooldown(k, memory))

    if _LAST_SCAN_TIME:
        last_scan_str = datetime.fromtimestamp(_LAST_SCAN_TIME, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        last_scan_str = "Belum pernah dijalankan"

    from strategies import get_strategies
    active_strats = [s.name for s in get_strategies()]

    text = (
        "📡 <b>STATUS SISTEM CRYPTO RADAR</b>\n"
        "<code>──────────────────────────────</code>\n"
        f"• Status: 🟢 <b>ONLINE</b>\n"
        f"• Uptime: <code>{get_uptime_str()}</code>\n"
        f"• Terakhir Scan: <code>{last_scan_str}</code>\n"
        f"• Koin dalam Cooldown: <code>{cooldown_count}</code> koin\n"
        f"• Limit Pantau: <code>Top {radar.SCAN_LIMIT} Koin</code>\n"
        f"• Strategi Aktif: <code>{', '.join(active_strats)}</code>\n"
        f"• Volume Spike: <code>{radar.VOL_SPIKE_THRESHOLD}x</code>\n"
        f"• Cooldown Period: <code>{radar.COOLDOWN_HOURS} jam</code>\n"
        "<code>──────────────────────────────</code>\n"
        "<i>Sistem berjalan normal.</i>"
    )
    radar.send_telegram(text, chat_id=str(chat_id))


def handle_scan(chat_id: int | str):
    """Respon untuk perintah /scan (trigger scanner manual)."""
    global _LAST_SCAN_TIME
    if _SCAN_LOCK.locked():
        radar.send_telegram(
            "⚠️ <b>Pemindaian sedang berlangsung!</b>\n"
            "Sistem sedang memeriksa pasar Binance. Mohon tunggu sinyal selesai diproses.",
            chat_id=str(chat_id),
        )
        return

    def run_worker():
        global _LAST_SCAN_TIME
        with _SCAN_LOCK:
            radar.send_telegram(
                f"🔍 <b>Memulai pemindaian pasar...</b>\n"
                f"Memeriksa Top {radar.SCAN_LIMIT} koin USDT di Binance untuk sinyal sniper.",
                chat_id=str(chat_id),
            )
            try:
                summary = radar.run_scanner(limit=radar.SCAN_LIMIT, dry_run=False, notify_telegram=True)
                _LAST_SCAN_TIME = time.time()
                signals_found = summary.get("signals_count", 0)
                duration = summary.get("duration_seconds", 0)
                scanned = summary.get("scanned_count", 0)

                if signals_found > 0:
                    radar.send_telegram(
                        f"✅ <b>Pemindaian Selesai!</b>\n"
                        f"• Koin discan: {scanned}\n"
                        f"• Sinyal ditemukan: <b>{signals_found}</b>\n"
                        f"• Waktu proses: {duration}s\n\n"
                        "<i>Detail sinyal dan grafik telah dikirim di atas.</i>",
                        chat_id=str(chat_id),
                    )
                else:
                    radar.send_telegram(
                        f"ℹ️ <b>Pemindaian Selesai</b>\n"
                        f"• Koin discan: {scanned}\n"
                        f"• Sinyal valid: <b>0</b> (Tidak ada koin yang memenuhi seluruh filter saat ini)\n"
                        f"• Waktu proses: {duration}s",
                        chat_id=str(chat_id),
                    )
            except Exception as e:
                log.exception(f"Error saat scan manual: {e}")
                radar.send_telegram(f"❌ Terjadi kesalahan saat scanning: {e}", chat_id=str(chat_id))

    threading.Thread(target=run_worker, daemon=True).start()


def handle_ai(chat_id: int | str, symbol_or_coin: str = "BTC"):
    """Respon untuk perintah /ai <koin> (Analisis AI + Stochastic 5,3,3)."""
    coin = symbol_or_coin.strip().upper().replace("USDT", "")
    if not coin:
        coin = "BTC"
    symbol = f"{coin}USDT"

    radar.send_telegram(
        f"🧠 <b>AI sedang menganalisis {coin}/USDT...</b>\n"
        f"<i>Mengambil klines Binance, menghitung Stochastic Oscillator (5,3,3), EMA, Support/Resistance & merumuskan ulasan teknikal. Mohon tunggu...</i>",
        chat_id=str(chat_id),
    )

    def run_worker():
        try:
            import ai_analyst
            report = ai_analyst.run_deep_ai_analysis(symbol)
            radar.send_telegram(report, chat_id=str(chat_id))
        except Exception as e:
            log.exception(f"Error saat analisis AI {symbol}: {e}")
            radar.send_telegram(f"❌ Gagal memproses analisis AI untuk {coin}: {e}", chat_id=str(chat_id))

    threading.Thread(target=run_worker, daemon=True).start()


# ══════════════════════════════════════════════
# PENDAFTARAN MENU PERINTAH TELEGRAM
# ══════════════════════════════════════════════
def register_telegram_commands(token: str):
    """Mendaftarkan tombol dan daftar perintah resmi ke Telegram Bot API."""
    commands = [
        {"command": "scan", "description": "Pindai pasar Binance sekarang"},
        {"command": "ai", "description": "Analisis AI + Stochastic (5,3,3) koin (misal: /ai BTC)"},
        {"command": "status", "description": "Status scanner, uptime & cooldown"},
        {"command": "top", "description": "Top 10 koin volume tertinggi di Binance"},
        {"command": "strategies", "description": "Daftar strategi teknikal aktif"},
        {"command": "ping", "description": "Cek latensi dan respon bot"},
        {"command": "help", "description": "Panduan & daftar perintah radar"},
    ]
    try:
        url = f"https://api.telegram.org/bot{token}/setMyCommands"
        res = radar._session.post(url, json={"commands": commands}, timeout=10)
        if res.status_code == 200:
            log.info("✅ Menu perintah Bot Telegram berhasil didaftarkan (setMyCommands).")
        else:
            log.warning(f"Gagal mendaftarkan setMyCommands: {res.text}")
    except Exception as e:
        log.warning(f"Gagal mendaftarkan setMyCommands: {e}")


# ══════════════════════════════════════════════
# TELEGRAM LONG POLLING ENGINE
# ══════════════════════════════════════════════
def telegram_polling_worker(token: str):
    """
    Loop polling pesan masuk dari Telegram menggunakan Bot API getUpdates.
    Memastikan hanya memproses perintah yang ditujukan untuk Bot Crypto Radar.
    """
    global _RUNNING
    session = radar._session
    offset = 0
    base_url = f"https://api.telegram.org/bot{token}"

    log.info("🤖 Worker Telegram Polling aktif.")

    while _RUNNING:
        try:
            params = {
                "offset": offset,
                "timeout": 20,
                "allowed_updates": ["message"],
            }
            resp = session.get(f"{base_url}/getUpdates", params=params, timeout=25)
            if resp.status_code != 200:
                time.sleep(2)
                continue

            data = resp.json()
            if not data.get("ok"):
                time.sleep(2)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg:
                    continue

                text = msg.get("text", "").strip()
                chat = msg.get("chat", {})
                chat_id = chat.get("id")

                if not text or not chat_id:
                    continue

                is_group_chat = int(chat_id) < 0
                parts = text.split()
                raw_cmd = parts[0].lower()

                target_bot = ""
                if "@" in raw_cmd:
                    cmd, target_bot = raw_cmd.split("@", 1)
                else:
                    cmd = raw_cmd

                # Isolasi grup: Jika di grup, abaikan perintah yang ditujukan untuk bot lain
                # atau perintah umum (/start, /help, /ai, /status, /top) yang merupakan ranah Bot AI Agentic (8951283878)
                if is_group_chat:
                    if target_bot and target_bot != "devioleteradarbot":
                        continue
                    # Jika tidak ditargetkan eksplisit ke @devioleteradarbot, hanya respon perintah khusus radar
                    if target_bot != "devioleteradarbot" and not cmd.startswith("/radar"):
                        continue

                if cmd in ("/start", "/radar_start"):
                    handle_start(chat_id)
                elif cmd in ("/help", "/radar_help"):
                    handle_help(chat_id)
                elif cmd in ("/ping", "/radar_ping"):
                    handle_ping(chat_id)
                elif cmd in ("/status", "/radar_status"):
                    handle_status(chat_id)
                elif cmd in ("/top", "/radar_top"):
                    handle_top(chat_id)
                elif cmd in ("/strategies", "/radar_strategies"):
                    handle_strategies(chat_id)
                elif cmd in ("/scan", "/radar_scan", "/radar"):
                    handle_scan(chat_id)
                elif cmd in ("/ai", "/analyze", "/radar_ai"):
                    coin_arg = parts[1].upper() if len(parts) > 1 else "BTC"
                    handle_ai(chat_id, coin_arg)
                elif cmd in ("/id", "/radar_id"):
                    thread_id = msg.get("message_thread_id")
                    info = (
                        "🆔 <b>INFORMASI ID (CRYPTO RADAR)</b>\n\n"
                        f"• <b>Chat ID:</b> <code>{chat_id}</code>\n"
                        f"• <b>Topic ID (Thread ID):</b> <code>{thread_id or '(Topik Umum / General)'}</code>\n\n"
                        f"💡 <i>Masukkan TELEGRAM_THREAD_ID={thread_id} pada .env agar sinyal otomatis terkirim ke topik ini.</i>"
                    )
                    radar.send_telegram(info, chat_id=chat_id, thread_id=thread_id)

        except requests.exceptions.RequestException as e:
            log.debug(f"Network error pada getUpdates: {e}")
            time.sleep(3)
        except Exception as e:
            log.error(f"Error tak terduga pada polling Telegram: {e}")
            time.sleep(3)


# ══════════════════════════════════════════════
# BACKGROUND SCANNER LOOP (Autonomous Daemon)
# ══════════════════════════════════════════════
def scheduled_scanner_worker(interval_minutes: int):
    """
    Thread terjadwal yang memindai pasar Binance secara otomatis dan kontinu 24/7.
    Berjalan dalam loop tanpa henti tanpa perlu perintah manual apapun.
    """
    global _RUNNING, _LAST_SCAN_TIME
    interval_seconds = interval_minutes * 60
    log.info(f"⏰ Background loop scanner aktif. Interval: setiap {interval_minutes} menit.")

    # Kirim notifikasi bot aktif ke grup/channel
    try:
        radar.send_telegram(
            "🚀 <b>Crypto Radar v8.0 Aktif (24/7 Auto-Scan)</b>\n"
            f"• Target Pantau: <code>Top {radar.SCAN_LIMIT} Koin Binance</code>\n"
            f"• Interval Loop: <code>Setiap {interval_minutes} Menit Otomatis</code>\n"
            "• Strategi     : <code>Reversal, Breakout, Trend Follow</code>\n"
            "• Mode         : <b>Autonomous Loop (Selalu Aktif)</b>\n\n"
            "<i>Scanner otomatis berjalan di latar belakang dan langsung mengirim alert jika sinyal sniper terdeteksi.</i>"
        )
    except Exception as e:
        log.warning(f"Gagal mengirim pesan startup loop: {e}")

    # Jeda 3 detik lalu langsung jalankan pemindaian pertama
    time.sleep(3)
    first_run = True

    while _RUNNING:
        log.info("⏰ [AUTO-LOOP] Memulai pemindaian pasar Binance otomatis...")
        with _SCAN_LOCK:
            try:
                summary = radar.run_scanner(limit=radar.SCAN_LIMIT, dry_run=False, notify_telegram=True)
                _LAST_SCAN_TIME = time.time()
                signals_count = summary.get("signals_count", 0)
                duration = summary.get("duration_seconds", 0)
                log.info(f"⏰ [AUTO-LOOP] Selesai ({duration}s). Sinyal sniper ditemukan: {signals_count}")

                # Pada scan awal, beri konfirmasi ringkas bila pasar belum ada sinyal
                if first_run and signals_count == 0:
                    try:
                        radar.send_telegram(
                            f"ℹ️ <b>Pemindaian Awal Selesai</b>\n"
                            f"• Koin Diperiksa: <code>{summary.get('scanned_count', 0)} Koin</code>\n"
                            f"• Waktu Proses: <code>{duration}s</code>\n"
                            f"• Sinyal Ditemukan: <code>0 (Pasar sedang konsolidasi)</code>\n\n"
                            f"<i>Sistem otomatis standby dan memindai ulang setiap {interval_minutes} menit tanpa henti.</i>"
                        )
                    except Exception as msg_err:
                        log.warning(f"Gagal mengirim notifikasi status scan awal: {msg_err}")
                first_run = False
            except Exception as e:
                log.exception(f"Error pada loop scanner terjadwal: {e}")

        # Tidur bertahap selama jeda interval
        slept = 0
        while _RUNNING and slept < interval_seconds:
            time.sleep(5)
            slept += 5


# ══════════════════════════════════════════════
# ENTRY POINT & CLI ARGUMENTS
# ══════════════════════════════════════════════
def main():
    """Fungsi utama pengelola mode aplikasi."""
    global _RUNNING

    parser = argparse.ArgumentParser(description="Crypto Radar v8.0 — Telegram Sniper Scanner")
    parser.add_argument("--once", action="store_true", help="Jalankan 1x scan lalu selesai (untuk cron / CI).")
    parser.add_argument("--dry-run", action="store_true", help="Jalankan scanner tanpa mengirim alert Telegram.")
    parser.add_argument("--interval", type=int, default=int(os.environ.get("SCAN_INTERVAL_MINUTES", 15)),
                        help="Interval scan otomatis dalam menit (default: 15).")
    parser.add_argument("--no-bot", action="store_true", help="Hanya jalankan scanner background tanpa bot Telegram.")
    parser.add_argument("--no-scan", action="store_true", help="Hanya jalankan bot Telegram tanpa scanner berkala.")
    parser.add_argument("--limit", type=int, default=radar.SCAN_LIMIT, help="Jumlah koin teratas yang dipindai.")
    args = parser.parse_args()

    if args.once:
        log.info("🚀 Menjalankan Crypto Radar dalam mode ONE-SHOT...")
        summary = radar.run_scanner(limit=args.limit, dry_run=args.dry_run, notify_telegram=not args.dry_run)
        log.info(f"Selesai. Sinyal terdeteksi: {summary.get('signals_count', 0)}")
        return

    token = (
        os.environ.get("TELEGRAM_RADAR_BOT_TOKEN", "").strip()
        or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    )
    if not token and not args.no_bot:
        log.warning("⚠️ Token bot Telegram tidak ditemukan di environment (TELEGRAM_RADAR_BOT_TOKEN atau TELEGRAM_BOT_TOKEN).")
        log.warning("   Bot interaktif Telegram dimatikan. Hanya scanner lokal yang akan berjalan.")
        log.warning("   Untuk mengaktifkan bot, masukkan token Anda ke file .env.")

    def handle_exit(signum, frame):
        global _RUNNING
        log.info("🛑 Menerima sinyal keluar, menghentikan bot...")
        _RUNNING = False
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    threads = []

    if not args.no_scan:
        scanner_thread = threading.Thread(
            target=scheduled_scanner_worker,
            args=(args.interval,),
            daemon=True,
            name="ScheduledScannerThread",
        )
        scanner_thread.start()
        threads.append(scanner_thread)

    if token and not args.no_bot:
        register_telegram_commands(token)
        bot_thread = threading.Thread(
            target=telegram_polling_worker,
            args=(token,),
            daemon=True,
            name="TelegramPollingThread",
        )
        bot_thread.start()
        threads.append(bot_thread)

    log.info("=" * 60)
    log.info("✨ Crypto Radar v8.0 Berjalan Normal!")
    log.info(f"   • Mode Daemon     : {'Aktif' if not args.no_scan else 'Bot Only'}")
    log.info(f"   • Scan Interval   : Setiap {args.interval} menit")
    log.info(f"   • Telegram Bot    : {'Aktif' if (token and not args.no_bot) else 'Nonaktif'}")
    log.info("   Tekan Ctrl+C untuk berhenti.")
    log.info("=" * 60)

    try:
        while _RUNNING:
            time.sleep(1)
    except KeyboardInterrupt:
        handle_exit(None, None)


if __name__ == "__main__":
    main()
