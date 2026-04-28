import requests
import os
import time
import json

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text, symbol):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}

    # 🎹 Inline Keyboard: tombol Binance & TradingView
    if symbol:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {
                    "text": "📈 Buka Binance",
                    "url": f"https://www.binance.com/en/trade/{symbol}?type=spot"
                },
                {
                    "text": "📊 Chart TradingView",
                    "url": f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
                }
            ]]
        }

    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Gagal ngirim pesan: {e}")

BASE_URL = "https://data-api.binance.vision/api/v3"
ALERTED_FILE = "alerted_coins.json"
COOLDOWN_SECONDS = 7200  # 2 jam

def load_alerted_coins():
    """Baca file memori koin yang sudah pernah di-alert."""
    if os.path.exists(ALERTED_FILE):
        try:
            with open(ALERTED_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_alerted_coins(data):
    """Simpan dictionary koin ke file JSON."""
    try:
        with open(ALERTED_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"⚠️ Gagal simpan memori: {e}")

def get_tickers_24hr():
    """Tarik semua ticker 24hr dari Binance Data API."""
    try:
        url = f"{BASE_URL}/ticker/24hr"
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error nyambung ke Binance: {e}")
        return None

def get_klines_15m(symbol):
    """Ambil 2 candle 15m terakhir untuk satu koin."""
    try:
        url = f"{BASE_URL}/klines"
        params = {"symbol": symbol, "interval": "15m", "limit": 2}
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"Error ambil klines {symbol}: {e}")
        return None

def scan_anomalies():
    print("🎯 MODE SNIPER 15 MENIT AKTIF! Mencari lonjakan...")
    tickers = get_tickers_24hr()

    # 🛡️ SABUK PENGAMAN: Kalau Binance ngasih pesan error / bukan list
    if isinstance(tickers, dict):
        print(f"❌ DICEGAT BINANCE! Pesan server: {tickers}")
        return
    if not tickers:
        print("❌ Gagal dapat data dari Binance.")
        return

    # Step 1: Filter koin USDT dengan volume > 1 juta
    candidates = []
    for ticker in tickers:
        if isinstance(ticker, dict) and 'symbol' in ticker:
            symbol = ticker['symbol']
            if symbol.endswith("USDT"):
                volume_24h = float(ticker['quoteVolume'])
                if volume_24h > 1000000:
                    candidates.append({
                        "symbol": symbol,
                        "volume_24h": volume_24h
                    })

    print(f"📊 {len(candidates)} koin USDT lolos filter volume.")

    # 🧠 Load memori koin yang sudah pernah di-alert
    alerted_coins = load_alerted_coins()

    # Step 2: Cek candle 15m terakhir satu per satu
    found = 0
    for coin in candidates:
        symbol = coin["symbol"]
        volume_24h = coin["volume_24h"]

        klines = get_klines_15m(symbol)
        time.sleep(0.1)  # ⏳ Rate limit guard

        if not klines or not isinstance(klines, list) or len(klines) < 2:
            continue

        # Candle terakhir yang sudah CLOSED = index [-2] (index [-1] masih berjalan)
        last_candle = klines[-2]
        open_price = float(last_candle[1])
        close_price = float(last_candle[4])
        candle_volume = float(last_candle[7])  # 💰 Quote Asset Volume / USDT (index 7)

        if open_price == 0:
            continue

        pct_change_15m = ((close_price - open_price) / open_price) * 100

        # 📊 Hitung rasio volume: volume candle 15m vs rata-rata volume per 15m
        avg_volume_15m = volume_24h / 96  # 96 candle 15m dalam 24 jam
        volume_ratio = candle_volume / avg_volume_15m if avg_volume_15m > 0 else 0

        # 🎯 Syarat Sniper: naik >= 3% DAN volume 2x lipat dari rata-rata
        if pct_change_15m >= 3.0 and volume_ratio >= 2.0:
            # 🧠 Cek memori: sudah pernah dikirim dalam 2 jam terakhir?
            now = time.time()
            if symbol in alerted_coins:
                last_alerted = alerted_coins[symbol]
                if now - last_alerted < COOLDOWN_SECONDS:
                    print(f"⏭️ SKIP {symbol} — sudah di-alert {int((now - last_alerted) / 60)} menit lalu.")
                    continue

            found += 1
            msg = (
                f"🎯 <b>SNIPER 15M — LONJAKAN TERDETEKSI</b> 🎯\n\n"
                f"💎 Koin: <b>{symbol}</b>\n"
                f"🚀 Naik 15m: <b>+{pct_change_15m:.2f}%</b>\n"
                f"🔥 Rasio Volume: <b>{volume_ratio:.1f}x lipat</b>\n"
                f"💵 Open: {open_price:.8g} → Close: {close_price:.8g}\n"
                f"💰 Vol (24h): ${volume_24h:,.0f}"
            )
            print(f"🎯 SNIPER HIT: {symbol} +{pct_change_15m:.2f}% | Vol {volume_ratio:.1f}x")
            send_telegram_message(msg, symbol=symbol)

            # 🧠 Update memori setelah berhasil kirim
            alerted_coins[symbol] = now
            save_alerted_coins(alerted_coins)
            time.sleep(1)

    if found == 0:
        print("😴 Tidak ada lonjakan >= 3% dengan volume spike 2x di candle 15m terakhir.")

if __name__ == "__main__":
    scan_anomalies()
