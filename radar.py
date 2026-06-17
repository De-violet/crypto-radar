"""
CRYPTO RADAR v7.0 — Multi-Strategy Sniper (Discord + Web Edition)
Filter Bertingkat: 4H -> 1H -> 5m
Anti-Spam Memory  |  Risk:Reward 1:2  |  Auto Chart | Signal Emitter

Changes vs v6.0:
- Telegram mode removed (use legacy-telegram branch for backup)
- Signal emitter decoupled from notification backend (Discord + Web API ready)
- Binance API geo-restriction workaround (multiple endpoints + data-api.binance.vision)
- Pinbar candle selection uses close_time verification (not blind iloc[-2])
- matplotlib figure explicitly closed after savefig (memory leak fix)
- logging module replaces print() for structured logs
- File locking on alerted_coins.json (fcntl on POSIX)
"""

import contextlib
import fcntl
import io
import json
import logging
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
# LOGGING SETUP
# ══════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("crypto-radar")


# ══════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════
# Telegram mode has been removed in v7.0. Use Discord (cogs/) or Web API (apps/api/) instead.
# Legacy Telegram code is preserved on the `legacy-telegram` branch / tag `v6.0-telegram-final`.

# Binance endpoints — multiple fallbacks to bypass 451 geo-restriction on US IPs.
# `data-api.binance.vision` is the public market-data mirror (no auth, no geo-block).
BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision",  # public market data, no geo-block
    "https://api.binance.com",
    "https://api-gcp.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]
KLINES_ENDPOINT = "/api/v3/klines"
TICKER_24HR_ENDPOINT = "/api/v3/ticker/24hr"

MEMORY_FILE = "alerted_coins.json"

# Dynamic parameters (bisa di-override via env)
SCAN_LIMIT = int(os.environ.get("SCAN_LIMIT", 120))
VOL_SPIKE_THRESHOLD = float(os.environ.get("VOL_SPIKE_THRESHOLD", 1.5))  # was 1.2 — too noisy
STOCH_OVERSOLD = int(os.environ.get("STOCH_OVERSOLD", 20))
COOLDOWN_HOURS = float(os.environ.get("COOLDOWN_HOURS", 4.0))

RISK_REWARD_RATIO = 2
STOP_LOSS_PCT = 1.5

# Expanded stablecoin list (USDT pairs that should never be scanned)
STABLECOIN_SYMBOLS = {
    "USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT",
    "DAIUSDT", "USDPUSDT", "EURUSDT", "AEURUSDT", "USTCUSDT",
    "USDSUSDT", "USDDUSDT", "USDEUSDT", "USDJUSDT", "PAXGUSDT",
    "XAUTUSDT",  # gold-backed
    # Leveraged tokens (reset mechanism breaks TA)
    "BTCUPUSDT", "BTCDOWNUSDT", "ETHUPUSDT", "ETHDOWNUSDT",
    "BNBUPUSDT", "BNBDOWNUSDT", "TRXUPUSDT", "TRXDOWNUSDT",
}


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
# BINANCE REQUEST HELPER (multi-endpoint failover)
# ══════════════════════════════════════════════
def _binance_get(path, params=None, timeout=15):
    """
    Try each Binance endpoint until one succeeds.
    Returns (data, used_base) on success, raises after all endpoints fail.
    """
    last_err = None
    for base in BINANCE_ENDPOINTS:
        url = f"{base}{path}"
        try:
            resp = _session.get(url, params=params, timeout=timeout)
            if resp.status_code == 451:
                log.debug(f"  [binance] 451 on {base}, trying next")
                last_err = f"HTTP 451 from {base}"
                continue
            resp.raise_for_status()
            return resp.json(), base
        except requests.RequestException as e:
            log.debug(f"  [binance] {base} failed: {e}")
            last_err = str(e)
    raise requests.RequestException(f"All Binance endpoints failed. Last: {last_err}")


# ══════════════════════════════════════════════
# DYNAMIC COIN SCANNER
# ══════════════════════════════════════════════
def get_top_volume_coins(limit=30):
    """
    Ambil daftar top koin USDT-Margined berdasarkan 24h quote volume.
    Abaikan stablecoins dan leveraged tokens.
    """
    try:
        data, _ = _binance_get(TICKER_24HR_ENDPOINT)
    except Exception as e:
        log.error(f"Gagal fetch 24hr ticker: {e}")
        return []

    valid_coins = []
    for item in data:
        symbol = item['symbol']
        if symbol.endswith("USDT") and symbol not in STABLECOIN_SYMBOLS:
            valid_coins.append({
                "symbol": symbol,
                "quoteVolume": float(item['quoteVolume'])
            })

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
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    try:
        data, _ = _binance_get(KLINES_ENDPOINT, params=params)
    except requests.exceptions.ConnectionError as e:
        log.error(f"Connection failed for {symbol} {interval}: {e}")
        return pd.DataFrame()
    except requests.exceptions.Timeout as e:
        log.error(f"Timeout fetching {symbol} {interval}: {e}")
        return pd.DataFrame()
    except requests.RequestException as e:
        log.error(f"Fetch {symbol} {interval}: {e}")
        return pd.DataFrame()

    return _parse_klines(data)


def _parse_klines(data):
    """Parse raw Binance klines JSON into DataFrame."""
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_vol", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    return df


def fetch_klines_paginated(symbol, interval, total_limit=1000):
    """
    Fetch large historical klines by paginating backwards via endTime.
    Binance allows max 1000 candles per request; this function transparently
    fetches up to `total_limit` candles.

    Used by the backtest engine which needs weeks/months of data.
    """
    page_size = 1000
    all_data = []
    remaining = total_limit
    end_time = None

    while remaining > 0:
        limit = min(page_size, remaining)
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        if end_time is not None:
            params["endTime"] = end_time

        try:
            data, _ = _binance_get(KLINES_ENDPOINT, params=params)
        except requests.RequestException as e:
            log.error(f"Paginated fetch failed for {symbol} {interval}: {e}")
            break

        if not data:
            break

        all_data = data + all_data  # prepend older candles
        oldest_open_time = data[0][0]
        end_time = oldest_open_time - 1
        remaining -= len(data)

        if len(data) < limit:
            break  # no more historical data available

        time.sleep(0.1)  # be polite to Binance API

    if not all_data:
        return pd.DataFrame()

    # Dedup by open_time (in case overlap)
    df = _parse_klines(all_data)
    df = df.drop_duplicates(subset="open_time").sort_values("open_time").reset_index(drop=True)
    return df


# ══════════════════════════════════════════════
# CHART GENERATOR
# ══════════════════════════════════════════════
def generate_chart(symbol, df):
    """
    Generate 5m candlestick chart and return as BytesIO.
    df should have datetime index and OHLC columns.
    """
    import matplotlib.pyplot as plt  # local import to allow global mplfinance config

    df_chart = df.copy()
    df_chart.set_index("open_time", inplace=True)

    buf = io.BytesIO()

    mc = mpf.make_marketcolors(up='g', down='r', edge='inherit', wick='inherit', volume='in', ohlc='i')
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=False)

    title = f"\n{symbol} 5m Rejection"
    fig, _ = mpf.plot(
        df_chart, type='candle', style=s, title=title,
        volume=False, savefig=dict(fname=buf, dpi=100, bbox_inches='tight'),
        figsize=(6, 4),
        returnfig=True,
    )

    # IMPORTANT: explicitly close figure to prevent memory leak in long-running bots
    plt.close(fig)

    buf.seek(0)
    return buf


# ══════════════════════════════════════════════
# FILTER 1 — 4H: Support Bounce + Volume Spike
# Syarat: (1) Low masuk zona buffer support
#         (2) Close > Open (bounce/memantul)
#         (3) Volume >= VOL_SPIKE_THRESHOLD (default 1.5x) rata-rata 20 candle
# ══════════════════════════════════════════════
def check_4h_support_volume(symbol):
    """
    Cek apakah harga menyentuh support, memantul, dan volume spike.
    Support = lowest low dari 20 candle terakhir.
    Buffer = 1.5% di atas support level.
    Volume spike = volume candle terakhir >= VOL_SPIKE_THRESHOLD x avg 20 candle.
    """
    df = fetch_klines(symbol, "4h", limit=30)
    return _check_4h_support_volume_df(df)


def _check_4h_support_volume_df(df):
    """Pure (no-fetch) variant of check_4h_support_volume. Used by backtest."""
    if df is None or df.empty:
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
    has_volume_spike = vol_ratio >= VOL_SPIKE_THRESHOLD

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
    return _check_1h_stochastic_df(df)


def _check_1h_stochastic_df(df):
    """Pure (no-fetch) variant of check_1h_stochastic. Used by backtest."""
    if df is None or df.empty:
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

    is_oversold = k_val <= STOCH_OVERSOLD

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
        "detail": f"{os_icon} K={k_val:.1f} (<={STOCH_OVERSOLD})",
    }


# ══════════════════════════════════════════════
# FILTER 3 — 5m: Bullish Pinbar Sniper Entry
# Syarat: (1) Close > Open (bullish candle)
#         (2) Lower wick >= 1.5x body
# Catatan: candle [-1] di-resolve secara close_time:
#   - kalau candle [-1] sudah close lebih dari 30 detik lalu → pakai [-1]
#   - kalau belum close (masih forming) → pakai [-2]
# ══════════════════════════════════════════════
def check_5m_pinbar(symbol):
    """
    Cek apakah candle 5m terakhir (yang sudah close) adalah Bullish Pinbar.
    Bullish Pinbar = Close > Open DAN lower wick >= 1.5x body.
    Pemilihan candle disesuaikan dengan close_time agar tidak salah ambil
    candle yang masih forming.
    """
    df = fetch_klines(symbol, "5m", limit=25)
    return _check_5m_pinbar_df(df)


def _check_5m_pinbar_df(df):
    """
    Pure (no-fetch) variant of check_5m_pinbar.
    NOTE: di mode backtest, kita anggap df.iloc[-1] sudah closed
    (backtest walk-forward selalu slice sampai candle yang closed).
    """
    if df is None or df.empty:
        return {"pass": False, "reason": "Data fetch failed", "df": None}

    # Tentukan candle yang sudah close
    now_utc = pd.Timestamp.now(tz="UTC")
    last_close_time = df["close_time"].iloc[-1]
    secs_since_close = (now_utc - last_close_time).total_seconds()

    # Kalau candle [-1] sudah close lebih dari 30 detik lalu, pakai [-1].
    # Kalau belum (masih forming), pakai [-2].
    candle_idx = -1 if secs_since_close > 30 else -2

    candle = df.iloc[candle_idx]
    o, h, low, c = candle["open"], candle["high"], candle["low"], candle["close"]

    body = abs(c - o)
    lower_wick = max(0, min(o, c) - low)
    upper_wick = max(0, h - max(o, c))

    body_ref = max(body, 0.0001)
    wick_ratio = lower_wick / body_ref

    is_bullish = c > o
    has_long_tail = lower_wick >= (1.5 * body_ref)
    is_pinbar = is_bullish and has_long_tail

    bull_icon = "[Y]" if is_bullish else "[N]"
    tail_icon = "[Y]" if has_long_tail else "[N]"

    return {
        "pass": is_pinbar,
        "open": round(o, 4),
        "high": round(h, 4),
        "low": round(low, 4),
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
# ANTI-SPAM: JSON Memory System (with file locking)
# ══════════════════════════════════════════════
def load_memory():
    """Baca alerted_coins.json, return dict kosong jika file belum ada."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning(f"Gagal baca memory file, reset: {e}")
        return {}


def save_memory(data):
    """
    Simpan data ke alerted_coins.json dengan file locking (POSIX only).
    Mencegah race condition saat bot + GH Actions cron jalan bersamaan.
    """
    try:
        with open(MEMORY_FILE, "r+" if os.path.exists(MEMORY_FILE) else "w",
                   encoding="utf-8") as f:
            # POSIX-only file lock; silently skipped on Windows
            with contextlib.suppress(AttributeError, OSError):
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
            with contextlib.suppress(AttributeError, OSError):
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError as e:
        log.error(f"Gagal simpan memory file: {e}")


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
# SIGNAL EMITTER — generic hook untuk Discord / Web / DB
# ══════════════════════════════════════════════
# Pluggable signal sink. Default = log only. Discord bot & Web API can
# register their own sinks via `register_signal_sink(...)`.
_signal_sinks: list = []


def register_signal_sink(sink):
    """
    Daftarkan callable yang akan dipanggil untuk setiap signal PASS.

    Signature sink:
        sink(symbol: str, signal: SignalResult, report: str, chart_buf: BytesIO | None)

    Contoh:
        # Discord bot mendaftarkan sink yang kirim embed ke channel
        radar.register_signal_sink(my_discord_sink)

        # Web API mendaftarkan sink yang simpan ke Supabase + emit SSE
        radar.register_signal_sink(my_web_sink)
    """
    if sink not in _signal_sinks:
        _signal_sinks.append(sink)
        log.info(f"Signal sink registered: {getattr(sink, '__name__', sink)}")


def unregister_signal_sink(sink):
    """Hapus sink dari daftar."""
    if sink in _signal_sinks:
        _signal_sinks.remove(sink)


def emit_signal(symbol, signal_result, report, chart_buf=None):
    """
    Broadcast signal ke semua sink yang terdaftar.
    Failures di salah satu sink tidak mengganggu sink lainnya.
    """
    if not _signal_sinks:
        log.info(f"[no-sink] Signal for {symbol}: {report[:100]}...")
        return

    for sink in _signal_sinks:
        try:
            sink(symbol, signal_result, report, chart_buf)
        except Exception as e:
            log.exception(f"Signal sink {sink} failed: {e}")


def build_signal_report(symbol, signal_result):
    """
    Buat format laporan generic (plain text, bukan HTML Telegram) dari SignalResult.
    Sink (Discord embed, Web SSE, DB) bisa reformat sesuai kebutuhan.
    """
    coin = symbol.replace("USDT", "")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    s = signal_result
    rr = s.details.get("rr", {})
    strategy_label = {
        "reversal": "Reversal / Bottom Fishing",
        "breakout": "Breakout / Momentum",
        "trend_follow": "Trend Follow / Pullback",
    }.get(s.strategy_name, s.strategy_name.title())

    checklist_lines = []
    for tf_key, tf_label in [("4h", "4H"), ("1h", "1H"), ("5m", "5m")]:
        tf_data = s.details.get(tf_key, {})
        if not tf_data:
            continue
        status = tf_data.get("status", "")
        detail = tf_data.get("detail", "")
        checklist_lines.append(f"  {tf_label} | {status} | {detail}")
    checklist_block = "\n".join(checklist_lines)

    report = (
        f"SNIPER SIGNAL — {coin}/USDT\n"
        f"──────────────────────────────\n"
        f"Strategy: {strategy_label}\n\n"
        f"{checklist_block}\n\n"
        f"──────────────────────────────\n"
        f"EXECUTION PLAN (R:R 1:{s.risk_reward_ratio})\n"
        f"  Entry  : {rr.get('entry', s.entry)}\n"
        f"  SL     : {rr.get('sl', s.stop_loss)}  (-{rr.get('risk_pct', 0)}%)\n"
        f"  TP     : {rr.get('tp', s.take_profit)}  (+{rr.get('reward_pct', 0)}%)\n\n"
        f"──────────────────────────────\n"
        f"VERDICT: HIGH CONVICTION ENTRY\n"
        f"{strategy_label}\n"
        f"{now_str}\n"
        f"#{coin} #{s.strategy_name}"
    )
    return report


def build_external_links(symbol):
    """URL shortcuts untuk Binance / TradingView / CoinGecko."""
    coin = symbol.replace("USDT", "")
    return {
        "binance": f"https://www.binance.com/en/trade/{coin}_USDT",
        "tradingview": f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}",
        "coingecko": f"https://www.coingecko.com/en/coins/{coin.lower()}",
    }


# ══════════════════════════════════════════════
# MAIN SCANNER ENGINE (Multi-Strategy)
# ══════════════════════════════════════════════
def run_scanner():
    """
    Main loop: jalankan semua strategi yang aktif (env STRATEGIES) untuk
    setiap top coin. Anti-spam memory key = (symbol, strategy_name).
    """
    # Lazy import to avoid circular import (strategies -> radar)
    from strategies import get_strategies

    active_strategies = get_strategies()
    strategy_names = [s.name for s in active_strategies]

    print("=" * 60)
    print("  🎯 CRYPTO RADAR v6.0 -- Multi-Strategy Sniper (Hardened)")
    print("=" * 60)

    coins = get_top_volume_coins(limit=SCAN_LIMIT)

    print(f"  Dynamic Top {SCAN_LIMIT} : {len(coins)} Coins found")
    print(f"  Time     : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Strategies: {strategy_names}")
    print(f"  Memory   : {MEMORY_FILE} (cooldown {COOLDOWN_HOURS}h)")
    print(f"  Vol Spike: {VOL_SPIKE_THRESHOLD}x")
    print("=" * 60)

    memory = load_memory()
    signals_found = 0

    for symbol in coins:
        coin = symbol.replace("USDT", "")
        print(f"\n{'-' * 50}")
        print(f"  Scanning: {coin}/USDT")
        print(f"{'-' * 50}")

        for strategy in active_strategies:
            memory_key = f"{symbol}:{strategy.name}"

            # Anti-spam check per (symbol, strategy)
            if is_on_cooldown(memory_key, memory):
                elapsed = (
                    datetime.now(timezone.utc).timestamp()
                    - memory[memory_key].get("last_alert", 0)
                ) / 3600
                remaining = COOLDOWN_HOURS - elapsed
                print(f"  [{strategy.name}] COOLDOWN -- {coin} ({remaining:.1f}h tersisa). Skip.")
                continue

            print(f"  [{strategy.name}] evaluating...", end=" ")
            try:
                result = strategy.check_signal(symbol)
            except Exception as e:
                log.exception(f"Strategy {strategy.name} error on {symbol}: {e}")
                print(f"ERROR: {e}")
                continue

            if not result.passed:
                print(f"FAIL -- {result.reason}")
                time.sleep(0.15)
                continue

            print(f"PASS! Entry={result.entry} SL={result.stop_loss} TP={result.take_profit}")

            # Generate chart (5m) bila chart_df tersedia
            chart_buf = None
            if result.chart_df is not None and not result.chart_df.empty:
                print("  Generating chart...")
                try:
                    chart_buf = generate_chart(symbol, result.chart_df)
                except Exception as e:
                    log.error(f"Chart generation failed: {e}")

            report = build_signal_report(symbol, result)
            emit_signal(symbol, result, report, chart_buf=chart_buf)
            signals_found += 1

            memory = record_alert(memory_key, memory)
            print(f"  [{strategy.name}] {coin} signal sent & recorded.")
            time.sleep(0.25)  # throttle antar strategy

    save_memory(memory)

    print(f"\n{'=' * 60}")
    print(f"  Scan selesai. Sinyal dikirim: {signals_found} ({len(coins)} coins × {len(active_strategies)} strategies)")
    print(f"{'=' * 60}")


# ══════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════
if __name__ == "__main__":
    run_scanner()
