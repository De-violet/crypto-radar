import requests
import os
import time
import json
import pandas as pd
import pandas_ta as ta

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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KONFIGURASI BOUNCE REJECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUPPORT_LOOKBACK = 20       # Jumlah candle untuk menghitung Support
SUPPORT_BUFFER = 0.01       # Buffer zone 1% — low cukup mendekati 1% dari support
VOLUME_SPIKE_RATIO = 1.5    # Volume candle harus >= 1.5x rata-rata 20 candle sebelumnya

# Stochastic Oscillator (5, 3, 3)
STOCH_K_LENGTH = 5          # %K length
STOCH_K_SMOOTH = 3          # %K smoothing
STOCH_D_SMOOTH = 3          # %D smoothing
STOCH_OVERSOLD = 20         # Batas area oversold

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

def calculate_support(candles, lookback=20):
    """Hitung Support = harga terendah (low) dari N candle terakhir yang sudah closed.

    Args:
        candles: list candle yang sudah CLOSED (tanpa candle berjalan).
        lookback: jumlah candle ke belakang untuk dihitung.

    Returns:
        (support_price, support_index) atau (None, None) jika data tidak cukup.
        support_index = posisi candle dengan harga terendah (0 = paling lama).
    """
    if len(candles) < lookback:
        return None, None

    recent = candles[-lookback:]
    lows = [float(c[3]) for c in recent]  # index 3 = Low price
    support = min(lows)
    support_idx = lows.index(support)  # posisi dalam window lookback

    return support, support_idx


def calculate_stochastic(candles):
    """Hitung Stochastic Oscillator (5,3,3) dari list candle Binance menggunakan pandas_ta.

    Args:
        candles: list candle dari Binance API (sudah CLOSED).

    Returns:
        (k_value, d_value) atau (None, None) jika data tidak cukup.
    """
    if len(candles) < STOCH_K_LENGTH + STOCH_K_SMOOTH + STOCH_D_SMOOTH:
        return None, None

    df = pd.DataFrame(candles, columns=[
        "open_time", "open", "high", "low", "close",
        "volume", "close_time", "quote_volume",
        "trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)

    stoch = ta.stoch(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        k=STOCH_K_LENGTH,
        d=STOCH_D_SMOOTH,
        smooth_k=STOCH_K_SMOOTH
    )

    if stoch is None or stoch.empty:
        return None, None

    # pandas_ta returns columns: STOCHk_5_3_3 and STOCHd_5_3_3
    k_col = stoch.columns[0]  # STOCHk
    d_col = stoch.columns[1]  # STOCHd

    k_value = stoch[k_col].iloc[-1]
    d_value = stoch[d_col].iloc[-1]

    if pd.isna(k_value) or pd.isna(d_value):
        return None, None

    return float(k_value), float(d_value)


def scan_bounce_rejection():
    """Scan semua koin USDT di Binance.
    Kirim alert jika terdeteksi BOUNCE / REJECTION di area Support.

    Syarat trigger (harus lolos SEMUA):
    1. Pinbar Rejection: low menyentuh/tembus support, TAPI close mantul di atas support.
    2. Buffer Zone: low cukup masuk zona 1% di atas support (low <= support * 1.01).
    3. Volume Spike: volume candle >= 1.5x rata-rata volume 20 candle sebelumnya.
    4. Stochastic Oversold: %K <= 20 (oversold) DAN %K > %D (golden cross / momentum naik).
    """

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🛡️  BOUNCE RADAR — Support Rejection Detector")
    print(f"📐 Support = Lowest Low dari {SUPPORT_LOOKBACK} candle 4H")
    print(f"🎯 Buffer = {SUPPORT_BUFFER * 100:.0f}% | Vol Spike = {VOLUME_SPIKE_RATIO}x | Stoch({STOCH_K_LENGTH},{STOCH_K_SMOOTH},{STOCH_D_SMOOTH}) ≤ {STOCH_OVERSOLD}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

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

    print(f"📊 {len(candidates)} koin USDT lolos filter volume (>$1M).\n")

    # 🧠 Load memori koin yang sudah pernah di-alert
    alerted_coins = load_alerted_coins()

    # Step 2: Cek setiap koin — apakah ada bounce / rejection di Support?
    found = 0
    for coin in candidates:
        symbol = coin["symbol"]
        volume_24h = coin["volume_24h"]

        # Ambil 50 candle: cukup untuk support (20) + Stoch warmup + 1 berjalan
        klines = get_klines(symbol, interval="4h", limit=50)
        time.sleep(0.1)  # ⏳ Rate limit guard

        if not klines or not isinstance(klines, list) or len(klines) < SUPPORT_LOOKBACK + 2 + STOCH_K_LENGTH:
            continue

        # Pisahkan candle yang sudah closed (buang candle terakhir yang masih berjalan)
        closed_candles = klines[:-1]

        # Candle closed terakhir = yang baru saja selesai (candle sinyal)
        last_closed = closed_candles[-1]
        close_price = float(last_closed[4])
        open_price = float(last_closed[1])
        high_price = float(last_closed[2])
        low_price = float(last_closed[3])
        candle_volume = float(last_closed[7])  # Quote Asset Volume (USDT)

        if open_price == 0:
            continue

        # 📐 Hitung Support dari 20 candle SEBELUM candle sinyal
        support_candles = closed_candles[:-1]  # semua closed kecuali candle sinyal
        support, support_idx = calculate_support(support_candles, lookback=SUPPORT_LOOKBACK)

        if support is None:
            continue

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 🎯 SYARAT 1 — PINBAR REJECTION
        # Low harus menyentuh atau menembus support,
        # TAPI close harus mantul dan tutup DI ATAS support.
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if close_price <= support:
            # Close tidak mantul, masih di bawah/sama dengan support → bukan bounce
            continue

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 🎯 SYARAT 2 — BUFFER ZONE (toleransi 1%)
        # Low harus masuk ke zona support:
        #   low <= support * (1 + buffer)
        # Artinya low cukup turun hingga 1% mendekati support.
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        support_zone = support * (1 + SUPPORT_BUFFER)
        if low_price > support_zone:
            # Low terlalu jauh dari support, tidak menyentuh zona
            continue

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 🎯 SYARAT 3 — VOLUME SPIKE
        # Volume candle sinyal harus >= 1.5x rata-rata volume
        # dari 20 candle sebelumnya (support_candles).
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        volumes_20 = [float(c[7]) for c in support_candles[-SUPPORT_LOOKBACK:]]
        avg_volume_20 = sum(volumes_20) / len(volumes_20) if volumes_20 else 0
        volume_ratio = candle_volume / avg_volume_20 if avg_volume_20 > 0 else 0

        if volume_ratio < VOLUME_SPIKE_RATIO:
            # Volume terlalu kecil, bukan bounce yang meyakinkan
            continue

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 🎯 SYARAT 4 — STOCHASTIC OVERSOLD + GOLDEN CROSS
        # %K harus <= 20 (area oversold)
        # %K harus > %D (momentum sedang naik / golden cross)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        stoch_k, stoch_d = calculate_stochastic(closed_candles)

        if stoch_k is None or stoch_d is None:
            continue

        if stoch_k > STOCH_OVERSOLD:
            # %K tidak di area oversold
            continue

        if stoch_k <= stoch_d:
            # %K masih di bawah %D, belum ada golden cross
            continue

        # ✅ SEMUA 4 SYARAT LOLOS — Bounce + Momentum Confirmed!

        pct_change_4h = ((close_price - open_price) / open_price) * 100
        pct_bounce = ((close_price - support) / support) * 100  # seberapa tinggi mantul dari support
        pct_low_from_support = ((low_price - support) / support) * 100  # seberapa dalam low menyentuh

        # 💰 Kalkulator Risk:Reward 1:2
        stop_loss_price = low_price * 0.995       # SL = 0.5% di bawah ekor candle
        risk = close_price - stop_loss_price       # Jarak risiko
        target_profit_price = close_price + (risk * 2)  # TP = close + 2x risk (R:R 1:2)
        pct_sl = ((stop_loss_price - close_price) / close_price) * 100
        pct_tp = ((target_profit_price - close_price) / close_price) * 100

        # 🧠 Cek memori: sudah pernah dikirim dalam 2 jam terakhir?
        now = time.time()
        if symbol in alerted_coins:
            last_alerted = alerted_coins[symbol]
            if now - last_alerted < COOLDOWN_SECONDS:
                mins_ago = int((now - last_alerted) / 60)
                print(f"⏭️  SKIP {symbol} — sudah di-alert {mins_ago} menit lalu.")
                continue

        found += 1

        # 📊 Format pesan Telegram
        bounce_emoji = "🟢" if low_price <= support else "🟡"
        pierce_status = "TEMBUS & MANTUL" if low_price <= support else "SENTUH ZONA & MANTUL"

        msg = (
            f"🛡️ <b>BOUNCE RADAR — REJECTION ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💎 <b>ASSET:</b> {symbol}\n\n"
            f"📊 <b>PRICE ACTION</b>\n"
            f"• Low: <b>${low_price:.8g}</b>\n"
            f"• Close: <b>${close_price:.8g}</b>\n"
            f"• Support: <b>${support:.8g}</b>\n"
            f"• Buffer Zone: <b>${support_zone:.8g}</b> (+{SUPPORT_BUFFER * 100:.0f}%)\n\n"
            f"🎯 <b>RISK:REWARD 1:2</b>\n"
            f"• 🔴 SL: <b>${stop_loss_price:.8g}</b> ({pct_sl:+.2f}%)\n"
            f"• 🟢 TP: <b>${target_profit_price:.8g}</b> (+{pct_tp:.2f}%)\n"
            f"• 📏 Risk: <b>${risk:.8g}</b>\n\n"
            f"{bounce_emoji} <b>STATUS:</b> {pierce_status}\n"
            f"📏 <b>Low → Support:</b> {pct_low_from_support:+.2f}%\n"
            f"📈 <b>Bounce dari Support:</b> +{pct_bounce:.2f}%\n"
            f"🕯️ <b>Candle 4H:</b> {pct_change_4h:+.2f}%\n\n"
            f"〽️ <b>STOCHASTIC ({STOCH_K_LENGTH},{STOCH_K_SMOOTH},{STOCH_D_SMOOTH})</b>\n"
            f"• %K: <b>{stoch_k:.2f}</b>\n"
            f"• %D: <b>{stoch_d:.2f}</b>\n"
            f"• Status: <b>OVERSOLD + GOLDEN CROSS</b> ✅\n\n"
            f"🔊 <b>VOLUME CONFIRMATION</b>\n"
            f"• Candle Vol: <b>${candle_volume:,.0f}</b>\n"
            f"• Avg 20 Vol: <b>${avg_volume_20:,.0f}</b>\n"
            f"• Spike: <b>{volume_ratio:.1f}x</b> ✅\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>\"Bounce + momentum confirmed di area oversold.\"</i>"
        )

        print(f"🎯 BOUNCE: {symbol} | Low ${low_price:.8g} → Close ${close_price:.8g} | Support ${support:.8g} | Vol {volume_ratio:.1f}x | %K {stoch_k:.2f} > %D {stoch_d:.2f}")
        send_telegram_message(msg, symbol=symbol)

        # 🧠 Update memori setelah berhasil kirim
        alerted_coins[symbol] = now
        save_alerted_coins(alerted_coins)
        time.sleep(1)

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if found == 0:
        print("😴 Tidak ada koin yang bounce di Support saat ini.")
    else:
        print(f"✅ {found} koin terdeteksi BOUNCE / REJECTION di Support.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    scan_bounce_rejection()