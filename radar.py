"""
CRYPTO RADAR v5.0 — Dynamic Reversal Sniper
Filter Bertingkat: 4H -> 1H -> 5m (Bottom Fishing)
Anti-Spam Memory  |  Risk:Reward 1:2  |  Inline Keyboard | Auto Chart
"""

import io
import json
import os
import time
from datetime import datetime, timezone

import mplfinance as mpf
import pandas as pd
import pandas_ta as ta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ══════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

<<<<<<< HEAD
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

BINANCE_BASE = "https://data-api.binance.vision"
=======
BINANCE_BASE = "https://api.binance.com"
>>>>>>> 4c44f24 (add feat: revamp sniper logic to dynamic reversal and add Telegram chart alerts)
KLINES_ENDPOINT = "/api/v3/klines"

MEMORY_FILE = "alerted_coins.json"
COOLDOWN_HOURS = 4

RISK_REWARD_RATIO = 2
STOP_LOSS_PCT = 1.5


# ══════════════════════════════════════════════
# HTTP SESSION (shared, with automatic retry)
# ══════════════════════════════════════════════
def _build_session():
    """
    Build a requests.Session with automatic retry on transient errors.
    Retries up to 3x on 429/500/502/503/504, with exponential back-off.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_session = _build_session()


# ══════════════════════════════════════════════
# DYNAMIC COIN SCANNER
# ══════════════════════════════════════════════
def get_top_volume_coins(limit=30):
    """
    Ambil daftar top koin USDT-Margined berdasarkan 24h quote volume.
    Abaikan stablecoins.
    """
    url = f"{BINANCE_BASE}/api/v3/ticker/24hr"
    try:
        resp = _session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [ERROR] Gagal fetch 24hr ticker: {e}")
        return []

    # Filter out stablecoins
    stablecoins = {
        "USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT", 
        "DAIUSDT", "USDPUSDT", "EURUSDT", "AEURUSDT", "USTCUSDT"
    }
    
    valid_coins = []
    for item in data:
        symbol = item['symbol']
        if symbol.endswith("USDT") and symbol not in stablecoins:
            valid_coins.append({
                "symbol": symbol,
                "quoteVolume": float(item['quoteVolume'])
            })
            
    # Urutkan berdasarkan quoteVolume tertinggi
    valid_coins.sort(key=lambda x: x["quoteVolume"], reverse=True)
    return [c["symbol"] for c in valid_coins[:limit]]


# ══════════════════════════════════════════════
# BINANCE DATA FETCHER
# ══════════════════════════════════════════════
def fetch_klines(symbol, interval, limit=100):
    """
    Fetch kline/candlestick data dari Binance Public API.
    Returns DataFrame dengan kolom OHLCV standar.
    """
    url = f"{BINANCE_BASE}{KLINES_ENDPOINT}"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    try:
        resp = _session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError as e:
        print(f"  [ERROR] Connection to Binance failed for {symbol} {interval}: {e}")
        return pd.DataFrame()
    except requests.exceptions.Timeout as e:
        print(f"  [ERROR] Timeout fetching {symbol} {interval}: {e}")
        return pd.DataFrame()
    except requests.RequestException as e:
        print(f"  [ERROR] Fetch {symbol} {interval}: {e}")
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    return df


# ══════════════════════════════════════════════
# CHART GENERATOR
# ══════════════════════════════════════════════
def generate_chart(symbol, df):
    """
    Generate 5m candlestick chart and return as BytesIO.
    df should have datetime index and OHLC columns.
    """
    # Create a copy and set datetime index for mplfinance
    df_chart = df.copy()
    df_chart.set_index("open_time", inplace=True)
    
    buf = io.BytesIO()
    
    # Customize the style
    mc = mpf.make_marketcolors(up='g', down='r', edge='inherit', wick='inherit', volume='in', ohlc='i')
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=False)
    
    # Plot to buffer
    title = f"\n{symbol} 5m Rejection"
    mpf.plot(df_chart, type='candle', style=s, title=title, 
             volume=False, savefig=dict(fname=buf, dpi=100, bbox_inches='tight'),
             figsize=(6, 4))
    
    buf.seek(0)
    return buf


# ══════════════════════════════════════════════
# FILTER 1 — 4H: Support Bounce + Volume Spike
# Syarat: (1) Low masuk zona buffer support
#         (2) Close > Open (bounce/memantul)
#         (3) Volume >= 1.5x rata-rata 20 candle
# ══════════════════════════════════════════════
def check_4h_support_volume(symbol):
    """
    Cek apakah harga menyentuh support, memantul, dan volume spike.
    Support = lowest low dari 20 candle terakhir.
    Buffer = 1.5% dari support level.
    Volume spike = volume candle terakhir >= 1.5x avg 20 candle.
    """
    df = fetch_klines(symbol, "4h", limit=30)
    if df.empty:
        return {"pass": False, "reason": "Data fetch failed"}

    recent_20 = df.tail(20)
    support_level = recent_20["low"].min()

    last = df.iloc[-1]
    current_low = last["low"]
    current_close = last["close"]
    current_open = last["open"]
    current_vol = last["volume"]

    buffer = support_level * 0.015
    in_support_zone = current_low <= (support_level + buffer)

    is_bouncing = current_close > current_open

    avg_vol_20 = recent_20["volume"].mean()
    vol_ratio = current_vol / avg_vol_20 if avg_vol_20 > 0 else 0
    has_volume_spike = vol_ratio >= 1.2

    distance_pct = ((current_low - support_level) / support_level) * 100

    all_pass = in_support_zone and is_bouncing and has_volume_spike

    support_icon = "[Y]" if in_support_zone else "[N]"
    bounce_icon = "[Y]" if is_bouncing else "[N]"
    volume_icon = "[Y]" if has_volume_spike else "[N]"

    return {
        "pass": all_pass,
        "close": round(current_close, 2),
        "current_low": round(current_low, 2),
        "support": round(support_level, 2),
        "distance": f"{distance_pct:.2f}%",
        "in_support_zone": in_support_zone,
        "is_bouncing": is_bouncing,
        "vol_ratio": round(vol_ratio, 2),
        "has_volume_spike": has_volume_spike,
        "status": "SUPPORT BOUNCE + VOL" if all_pass else "FILTER 4H GAGAL",
        "detail": (
            f"{support_icon} Support Zone ({distance_pct:.2f}%)  "
            f"{bounce_icon} Bounce  "
            f"{volume_icon} Vol {vol_ratio:.1f}x"
        ),
    }


# ══════════════════════════════════════════════
# FILTER 2 — 1H: Stochastic Oversold
# Syarat: %K <= 20 (Oversold)
# Stochastic parameter: (5, 3, 3)
# ══════════════════════════════════════════════
def check_1h_stochastic(symbol):
    """
    Cek Stochastic (5,3,3) di TF 1H.
    PASS jika K <= 20 (oversold).
    """
    df = fetch_klines(symbol, "1h", limit=50)
    if df.empty:
        return {"pass": False, "reason": "Data fetch failed"}

    stoch = ta.stoch(df["high"], df["low"], df["close"], k=5, d=3, smooth_k=3)
    if stoch is None or stoch.empty:
        return {"pass": False, "reason": "Stochastic gagal dihitung"}

    k_col = [c for c in stoch.columns if "STOCHk" in c][0]
    d_col = [c for c in stoch.columns if "STOCHd" in c][0]

    k_val = stoch[k_col].iloc[-1]
    d_val = stoch[d_col].iloc[-1]

    if pd.isna(k_val) or pd.isna(d_val):
        return {"pass": False, "reason": "Stochastic NaN"}

    is_oversold = k_val <= 20
    
    os_icon = "[Y]" if is_oversold else "[N]"

    if is_oversold:
        status = "OVERSOLD"
    else:
        status = "NOT OVERSOLD"

    return {
        "pass": is_oversold,
        "k": round(k_val, 2),
        "d": round(d_val, 2),
        "is_oversold": is_oversold,
        "status": status,
        "detail": f"{os_icon} K={k_val:.1f} (<=20)",
    }


# ══════════════════════════════════════════════
# FILTER 3 — 5m: Bullish Pinbar Sniper Entry
# Syarat: (1) Close > Open (bullish candle)
#         (2) Lower wick >= 2x body
# ══════════════════════════════════════════════
def check_5m_pinbar(symbol):
    """
    Cek apakah 1 closed candle 5m terakhir adalah Bullish Pinbar.
    Bullish Pinbar = Close > Open DAN lower wick >= 2x body.
    Menggunakan candle [-2] (last closed) bukan [-1] (still forming).
    """
    # Load enough data for the chart, e.g. 25 candles
    df = fetch_klines(symbol, "5m", limit=25)
    if df.empty:
        return {"pass": False, "reason": "Data fetch failed", "df": None}

    candle = df.iloc[-2]
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]

    body = abs(c - o)
    # Gunakan max(0, ...) untuk menghindari nilai negatif jika terjadi anomali data (misal: open < low)
    lower_wick = max(0, min(o, c) - l)
    upper_wick = max(0, h - max(o, c))

    body_ref = max(body, 0.0001)
    wick_ratio = lower_wick / body_ref

    is_bullish = c > o
    # Ubah syarat tail dari 2x menjadi 1.5x body
    has_long_tail = lower_wick >= (1.5 * body_ref)
    is_pinbar = is_bullish and has_long_tail

    bull_icon = "[Y]" if is_bullish else "[N]"
    tail_icon = "[Y]" if has_long_tail else "[N]"

    return {
        "pass": is_pinbar,
        "open": round(o, 4),
        "high": round(h, 4),
        "low": round(l, 4),
        "close": round(c, 4),
        "body": round(body, 6),
        "lower_wick": round(lower_wick, 6),
        "upper_wick": round(upper_wick, 6),
        "ratio": round(wick_ratio, 2),
        "status": "BULLISH PINBAR" if is_pinbar else "NO PINBAR",
        "detail": f"{bull_icon} Bullish  {tail_icon} Tail {wick_ratio:.1f}x body",
        "df": df
    }


# ══════════════════════════════════════════════
# RISK:REWARD CALCULATOR (1:2)
# ══════════════════════════════════════════════
def calculate_risk_reward(entry, support):
    """
    Hitung Stop Loss dan Take Profit berdasarkan Risk:Reward 1:2.
    SL = support - 1.5%
    TP = entry + 2 x (entry - SL)
    """
    sl = support * (1 - STOP_LOSS_PCT / 100)
    risk = entry - sl
    tp = entry + (risk * RISK_REWARD_RATIO)
    risk_pct = (risk / entry) * 100
    reward_pct = ((tp - entry) / entry) * 100

    return {
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "risk": round(risk, 2),
        "risk_pct": round(risk_pct, 2),
        "reward_pct": round(reward_pct, 2),
    }


# ══════════════════════════════════════════════
# ANTI-SPAM: JSON Memory System
# ══════════════════════════════════════════════
def load_memory():
    """Baca alerted_coins.json, return dict kosong jika file belum ada."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  [WARN] Gagal baca memory file, reset: {e}")
        return {}


def save_memory(data):
    """Simpan data ke alerted_coins.json dengan error handling."""
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"  [ERROR] Gagal simpan memory file: {e}")


def is_on_cooldown(symbol, memory):
    """
    Cek apakah koin masih dalam cooldown period.
    Return True jika masih cooldown (jangan kirim ulang).
    """
    if symbol not in memory:
        return False

    last_alert_ts = memory[symbol].get("last_alert", 0)
    now_ts = datetime.now(timezone.utc).timestamp()
    elapsed_hours = (now_ts - last_alert_ts) / 3600

    return elapsed_hours < COOLDOWN_HOURS


def record_alert(symbol, memory):
    """Catat timestamp alert terbaru untuk koin ini."""
    memory[symbol] = {
        "last_alert": datetime.now(timezone.utc).timestamp(),
        "last_alert_human": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    return memory


# ══════════════════════════════════════════════
# TELEGRAM NOTIFICATION (Inline Keyboard)
# ══════════════════════════════════════════════
def send_telegram(message, reply_markup=None, photo_buf=None):
    """Kirim pesan ke Telegram via Bot API, support kirim gambar."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [WARN] Telegram credentials not set. Printing to console.")
        print(message)
        return

    if photo_buf:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": message,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
            
        files = {
            "photo": ("chart.png", photo_buf.getvalue(), "image/png")
        }
        try:
            resp = _session.post(url, data=payload, files=files, timeout=20)
            if resp.status_code == 200:
                print("  [OK] Telegram photo sent.")
            else:
                print(f"  [ERROR] Telegram photo: {resp.status_code} -- {resp.text}")
        except Exception as e:
            print(f"  [ERROR] Telegram photo send failed: {e}")
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)

        try:
            resp = _session.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                print("  [OK] Telegram message sent.")
            else:
                print(f"  [ERROR] Telegram: {resp.status_code} -- {resp.text}")
        except Exception as e:
            print(f"  [ERROR] Telegram send failed: {e}")


def build_inline_keyboard(symbol):
    """Buat inline keyboard dengan tombol link ke chart Binance dan TradingView."""
    coin = symbol.replace("USDT", "")
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Binance Chart",
                    "url": f"https://www.binance.com/en/trade/{coin}_USDT",
                },
                {
                    "text": "TradingView",
                    "url": f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}",
                },
            ],
            [
                {
                    "text": f"{coin} Detail -- CoinGecko",
                    "url": f"https://www.coingecko.com/en/coins/{coin.lower()}",
                },
            ],
        ],
    }


def build_report(symbol, h4, h1, m5, rr):
    """
    Buat format laporan Multi-Timeframe Sniper untuk Telegram.
    Menampilkan checklist filter + Risk:Reward calculator.
    """
    coin = symbol.replace("USDT", "")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    report = (
        f"<b>🎯 SNIPER SIGNAL -- {coin}/USDT</b>\n"
        f"<code>------------------------------</code>\n\n"
        f"<b>📋 STRATEGY CHECKLIST (REVERSAL)</b>\n\n"
        f"  <b>4H | Support and Volume</b>\n"
        f"  {h4['status']}\n"
        f"  {h4['detail']}\n"
        f"  Support: <code>{h4['support']}</code>  Jarak: <code>{h4['distance']}</code>\n\n"
        f"  <b>1H | Stochastic (5,3,3)</b>\n"
        f"  {h1['status']}\n"
        f"  {h1['detail']}\n\n"
        f"  <b>5m | Pinbar Entry</b>\n"
        f"  {m5['status']}\n"
        f"  {m5['detail']}\n\n"
        f"<code>------------------------------</code>\n"
        f"<b>💰 EXECUTION PLAN (R:R 1:{RISK_REWARD_RATIO})</b>\n\n"
        f"  Entry  : <code>{rr['entry']}</code>\n"
        f"  SL     : <code>{rr['sl']}</code>  (-{rr['risk_pct']}%)\n"
        f"  TP     : <code>{rr['tp']}</code>  (+{rr['reward_pct']}%)\n\n"
        f"<code>------------------------------</code>\n"
        f"<b>🟢 VERDICT: HIGH CONVICTION ENTRY</b>\n"
        f"<i>Reversal pattern detected</i>\n"
        f"{now_str}\n"
        f"<code>#{coin} #Reversal #BottomFishing</code>"
    )

    return report


# ══════════════════════════════════════════════
# MAIN SCANNER ENGINE
# ══════════════════════════════════════════════
def run_scanner():
    """
    Main loop: Filter Bertingkat (Top-Down Analysis).
    4H -> 1H -> 5m, dengan anti-spam memory.
    Setiap filter yang gagal langsung drop (continue) ke koin berikutnya.
    """
    print("=" * 60)
    print("  🎯 CRYPTO RADAR v5.0 -- Dynamic Reversal Sniper")
    print("=" * 60)
    
    coins = get_top_volume_coins(limit=40)
    
    print(f"  Dynamic Top 40 : {len(coins)} Coins found")
    print(f"  Time   : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Memory : {MEMORY_FILE} (cooldown {COOLDOWN_HOURS}h)")
    print("=" * 60)

    memory = load_memory()
    signals_found = 0

    for symbol in coins:
        coin = symbol.replace("USDT", "")
        print(f"\n{'-' * 50}")
        print(f"  Scanning: {coin}/USDT")
        print(f"{'-' * 50}")

        # Anti-spam check
        if is_on_cooldown(symbol, memory):
            elapsed = (
                datetime.now(timezone.utc).timestamp()
                - memory[symbol].get("last_alert", 0)
            ) / 3600
            remaining = COOLDOWN_HOURS - elapsed
            print(f"  COOLDOWN -- {coin} masih cooldown ({remaining:.1f}h tersisa). Skip.")
            continue

        # == FILTER 1: 4H Support + Volume ==
        print("  [1/3] 4H Support+Vol ...", end=" ")
        h4 = check_4h_support_volume(symbol)
        print(h4.get("status", "ERROR"))
        if not h4["pass"]:
            reason = h4.get("detail", h4.get("reason", ""))
            print(f"        {coin} {reason}. DROP.")
            continue
        time.sleep(0.15)

        # == FILTER 2: 1H Stochastic ==
        print("  [2/3] 1H Stoch(5,3,3) ...", end=" ")
        h1 = check_1h_stochastic(symbol)
        print(h1.get("status", "ERROR"))
        if not h1["pass"]:
            reason = h1.get("detail", h1.get("reason", ""))
            print(f"        {coin} {reason}. DROP.")
            continue
        time.sleep(0.15)

        # == FILTER 3: 5m Pinbar ==
        print("  [3/3] 5m Pinbar ...", end=" ")
        m5 = check_5m_pinbar(symbol)
        print(m5.get("status", "ERROR"))
        if not m5["pass"]:
            reason = m5.get("detail", m5.get("reason", ""))
            print(f"        {coin} {reason}. DROP.")
            continue

        # == ALL FILTERS PASSED ==
        print(f"\n  {coin} LOLOS SEMUA FILTER REVERSAL!")

        entry_price = m5["close"]
        support_price = h4["support"]
        rr = calculate_risk_reward(entry_price, support_price)
        print(f"  Entry: {rr['entry']} | SL: {rr['sl']} | TP: {rr['tp']}")

        # Generate Chart
        print("  Generating chart...")
        photo_buf = generate_chart(symbol, m5["df"])

        report = build_report(symbol, h4, h1, m5, rr)
        keyboard = build_inline_keyboard(symbol)
        send_telegram(report, reply_markup=keyboard, photo_buf=photo_buf)
        signals_found += 1

        memory = record_alert(symbol, memory)
        print("  Sinyal & Chart terkirim & tercatat di memory.")

    save_memory(memory)

    print(f"\n{'=' * 60}")
    print(f"  Scan selesai. Sinyal dikirim: {signals_found}/{len(coins)}")
    print(f"{'=' * 60}")


# ══════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════
if __name__ == "__main__":
    run_scanner()
