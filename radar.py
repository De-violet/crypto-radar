import requests
import os
import time
import json

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text, symbol):
    """Kirim foto chart + caption ke Telegram via sendPhoto API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    photo_url = f"https://api.chart-img.com/v1/tradingview/advanced-chart?symbol=BINANCE:{symbol}&interval=4h&theme=dark"

    payload = {
        "chat_id": CHAT_ID,
        "photo": photo_url,
        "caption": text,
        "parse_mode": "HTML"
    }

    # 🎹 Inline Keyboard: tombol Binance & TradingView
    if symbol:
        payload["reply_markup"] = json.dumps({
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
        })

    try:
        response = requests.post(url, data=payload)
        # Fallback: jika sendPhoto gagal (misal chart-img down), kirim teks biasa
        if not response.ok:
            print(f"⚠️ sendPhoto gagal ({response.status_code}), fallback ke sendMessage...")
            fallback_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            fallback_payload = {
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML"
            }
            if symbol:
                fallback_payload["reply_markup"] = payload["reply_markup"]
            requests.post(fallback_url, data=fallback_payload)
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

def get_klines(symbol, interval="4h", limit=2):
    """Ambil candle terakhir untuk satu koin."""
    try:
        url = f"{BASE_URL}/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"Error ambil klines {symbol}: {e}")
        return None

def calculate_rsi(prices, period=14):
    """Hitung RSI manual dari list harga close. Pure Python, tanpa pandas/numpy."""
    if len(prices) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))

    # Rata-rata gain & loss pertama (SMA)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Smoothing (Wilder's EMA) untuk sisa data
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0  # Tidak ada loss sama sekali = RSI maksimal

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(prices, period=200):
    """Hitung EMA manual dari list harga close. Pure Python, tanpa pandas/numpy."""
    if len(prices) < period:
        return None

    # Mulai dari SMA sebagai seed pertama
    sma = sum(prices[:period]) / period
    multiplier = 2 / (period + 1)

    ema = sma
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema

    return ema

def get_order_book_imbalance(symbol):
    """Cek kedalaman order book. Return rasio total Bids / total Asks (dalam USDT)."""
    try:
        url = f"{BASE_URL}/depth"
        params = {"symbol": symbol, "limit": 100}
        response = requests.get(url, params=params)
        data = response.json()

        total_bids = sum(float(bid[0]) * float(bid[1]) for bid in data.get("bids", []))
        total_asks = sum(float(ask[0]) * float(ask[1]) for ask in data.get("asks", []))

        if total_asks == 0:
            return 0
        return total_bids / total_asks
    except Exception as e:
        print(f"Error ambil order book {symbol}: {e}")
        return 0

def check_btc_trend():
    """Cek apakah BTC sedang naik di candle 4H terakhir. Return False jika turun."""
    klines = get_klines("BTCUSDT", interval="4h", limit=2)
    if not klines or not isinstance(klines, list) or len(klines) < 2:
        print("⚠️ Gagal cek tren BTC, skip scan untuk safety.")
        return False
    last_candle = klines[-2]
    open_price = float(last_candle[1])
    close_price = float(last_candle[4])
    change = close_price - open_price
    pct = ((change) / open_price) * 100 if open_price > 0 else 0
    print(f"₿ BTC 4H: {open_price:.2f} → {close_price:.2f} ({pct:+.2f}%)")
    return change >= 0

def scan_anomalies():
    # 🔒 GEMBOK BTC: Jangan scan altcoin jika BTC lagi turun
    if not check_btc_trend():
        print("🛑 BTC lagi turun, mode puasa aktif!")
        return

    print("🎯 HEDGE FUND RADAR 4H AKTIF! Scanning...")
    tickers = get_tickers_24hr()

    # 🛡️ SABUK PENGAMAN: Kalau Binance ngasih pesan error / bukan list
    if isinstance(tickers, dict):
        print(f"❌ DICEGAT BINANCE! Pesan server: {tickers}")
        return
    if not tickers:
        print("❌ Gagal dapat data dari Binance.")
        return

    # Step 1: Filter koin USDT dengan volume > 1 juta + simpan count untuk whale detector
    candidates = []
    for ticker in tickers:
        if isinstance(ticker, dict) and 'symbol' in ticker:
            symbol = ticker['symbol']
            if symbol.endswith("USDT"):
                volume_24h = float(ticker['quoteVolume'])
                trade_count_24h = int(ticker.get('count', 0))
                if volume_24h > 1000000:
                    candidates.append({
                        "symbol": symbol,
                        "volume_24h": volume_24h,
                        "trade_count_24h": trade_count_24h
                    })

    print(f"📊 {len(candidates)} koin USDT lolos filter volume.")

    # 🧠 Load memori koin yang sudah pernah di-alert
    alerted_coins = load_alerted_coins()

    # Step 2: Cek candle 4H terakhir satu per satu
    found = 0
    for coin in candidates:
        symbol = coin["symbol"]
        volume_24h = coin["volume_24h"]
        trade_count_24h = coin["trade_count_24h"]

        klines = get_klines(symbol, limit=250)
        time.sleep(0.1)  # ⏳ Rate limit guard

        if not klines or not isinstance(klines, list) or len(klines) < 2:
            continue

        # Candle terakhir yang sudah CLOSED = index [-2] (index [-1] masih berjalan)
        last_candle = klines[-2]
        open_price = float(last_candle[1])
        high_price = float(last_candle[2])
        low_price = float(last_candle[3])
        close_price = float(last_candle[4])
        candle_volume = float(last_candle[7])  # 💰 Quote Asset Volume / USDT (index 7)
        num_trades = int(last_candle[8])       # 🐋 Number of Trades (index 8)

        if open_price == 0:
            continue

        # 🕯️ WICK FILTER (Anti-Pucuk): tolak candle dengan jarum atas > 50%
        upper_wick = high_price - max(open_price, close_price)
        total_length = high_price - low_price
        if total_length > 0 and (upper_wick / total_length) > 0.5:
            continue

        # 📈 Hitung indikator teknikal dari semua candle closed
        closed_candles = klines[:-1]  # Buang candle terakhir yang masih berjalan
        close_prices = [float(c[4]) for c in closed_candles]
        rsi_value = calculate_rsi(close_prices, period=14)
        ema_200 = calculate_ema(close_prices, period=200)

        # 〽️ EMA 200 FILTER: hanya ambil koin yang harga di atas tren jangka panjang
        if ema_200 is not None and close_price <= ema_200:
            continue

        pct_change_4h = ((close_price - open_price) / open_price) * 100

        # 📊 Hitung rasio volume: volume candle 4H vs rata-rata volume per 4H
        avg_volume_4h = volume_24h / 6  # 6 candle 4H dalam 24 jam
        volume_ratio = candle_volume / avg_volume_4h if avg_volume_4h > 0 else 0

        # 🐋 WHALE DETECTOR: rata-rata ukuran transaksi candle vs rata-rata harian
        avg_trade_size_candle = candle_volume / num_trades if num_trades > 0 else 0
        avg_trade_size_24h = volume_24h / trade_count_24h if trade_count_24h > 0 else 0
        trade_size_ratio = avg_trade_size_candle / avg_trade_size_24h if avg_trade_size_24h > 0 else 0

        # 🎯 Syarat Swing: naik >= 5% DAN volume 1.5x DAN whale 1.5x
        if pct_change_4h >= 5.0 and volume_ratio >= 1.5 and trade_size_ratio >= 1.5:
            # 🧠 Cek memori: sudah pernah dikirim dalam 2 jam terakhir?
            now = time.time()
            if symbol in alerted_coins:
                last_alerted = alerted_coins[symbol]
                if now - last_alerted < COOLDOWN_SECONDS:
                    print(f"⏭️ SKIP {symbol} — sudah di-alert {int((now - last_alerted) / 60)} menit lalu.")
                    continue

            # 🧱 ORDER BOOK IMBALANCE
            bid_ask_ratio = get_order_book_imbalance(symbol)
            time.sleep(0.1)  # ⏳ Rate limit guard

            found += 1

            # 💰 Hitung Target Profit & Stop Loss
            tp_price = close_price * 1.30  # +30%
            sl_price = close_price * 0.90  # -10%
            rsi_display = f"{rsi_value:.2f}" if rsi_value is not None else "N/A"
            ema_display = f"{ema_200:.8g}" if ema_200 is not None else "N/A"

            msg = (
                f"🎯 <b>[HEDGE FUND RADAR] {symbol}</b>\n\n"
                f"📈 Naik 4H: <b>+{pct_change_4h:.2f}%</b> | Vol: <b>{volume_ratio:.1f}x</b>\n"
                f"🐋 Whale Index: <b>{trade_size_ratio:.1f}x</b> (Uang Besar Masuk)\n"
                f"🧱 Order Book: Bids <b>{bid_ask_ratio:.1f}x</b> lebih tebal\n"
                f"🎛️ RSI(14): <b>{rsi_display}</b>\n"
                f"〽️ EMA(200): <b>${ema_display}</b>\n"
                f"🎯 TP: <b>${tp_price:.8g}</b> (+30%) | 🛑 SL: <b>${sl_price:.8g}</b> (-10%)\n\n"
                f"🛡️ <b>RISK PROTOCOL ($9 Strategy):</b>\n"
                f"  • Entry: Buy Spot (No Leverage)\n"
                f"  • Risk Amount: Full modal ($9) untuk 1 tembakan\n"
                f"  • Psychology: Sabar, ini Swing! Jangan cek tiap menit."
            )
            print(f"🎯 HIT: {symbol} +{pct_change_4h:.2f}% | Vol {volume_ratio:.1f}x | Whale {trade_size_ratio:.1f}x | OB {bid_ask_ratio:.1f}x | RSI {rsi_display} | EMA200 {ema_display}")
            send_telegram_message(msg, symbol=symbol)

            # 🧠 Update memori setelah berhasil kirim
            alerted_coins[symbol] = now
            save_alerted_coins(alerted_coins)
            time.sleep(1)

    if found == 0:
        print("😴 Tidak ada koin yang lolos semua filter Hedge Fund Grade.")

if __name__ == "__main__":
    scan_anomalies()