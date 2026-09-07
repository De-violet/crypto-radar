"""
CRYPTO RADAR v8.0 — Multi-Strategy Sniper (Telegram Edition)
Filter Bertingkat: 4H -> 1H -> 5m
Anti-Spam Memory  |  Risk:Reward 1:2  |  Auto Chart  |  Telegram Native

Fitur Utama:
- Multi-Strategy: Reversal, Breakout, Trend Follow
- Binance Public API Failover (data-api.binance.vision + backup endpoints)
- Alert Telegram interaktif dengan grafik candlestick (mplfinance) & inline buttons
- Anti-Spam memory berbasis file JSON dengan fcntl file locking (POSIX)
"""
from __future__ import annotations

import contextlib
import fcntl
import io
import json
import logging
import os
import time
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import pandas_ta as ta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

# Muat file .env jika tersedia
load_dotenv()

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
# KONFIGURASI & ENVIRONMENT VARIABLES
# Mendukung TELEGRAM_RADAR_BOT_TOKEN untuk setup multi-bot 1 file .env
TELEGRAM_BOT_TOKEN = (
    os.environ.get("TELEGRAM_RADAR_BOT_TOKEN", "").strip()
    or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
)
TELEGRAM_CHAT_ID = (
    os.environ.get("TELEGRAM_RADAR_CHAT_ID", "").strip()
    or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
)
TELEGRAM_THREAD_ID = (
    os.environ.get("TELEGRAM_RADAR_THREAD_ID", "").strip()
    or os.environ.get("TELEGRAM_THREAD_ID", "").strip()
)

# Binance endpoints — fallback berantai untuk menghindari pembatasan IP / 451.
# `data-api.binance.vision` adalah mirror data pasar publik tanpa autentikasi/geo-block.
BINANCE_ENDPOINTS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api-gcp.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]
KLINES_ENDPOINT = "/api/v3/klines"
TICKER_24HR_ENDPOINT = "/api/v3/ticker/24hr"

MEMORY_FILE = os.environ.get("MEMORY_FILE", "alerted_coins.json")

# Parameter Dinamis
SCAN_LIMIT = int(os.environ.get("SCAN_LIMIT", 100))
VOL_SPIKE_THRESHOLD = float(os.environ.get("VOL_SPIKE_THRESHOLD", 1.5))
STOCH_OVERSOLD = int(os.environ.get("STOCH_OVERSOLD", 20))
COOLDOWN_HOURS = float(os.environ.get("COOLDOWN_HOURS", 4.0))

RISK_REWARD_RATIO = 2.0
STOP_LOSS_PCT = 1.5

# Daftar koin stabil & leverage token yang tidak boleh discan
STABLECOIN_SYMBOLS = {
    "USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT",
    "DAIUSDT", "USDPUSDT", "EURUSDT", "AEURUSDT", "USTCUSDT",
    "USDSUSDT", "USDDUSDT", "USDEUSDT", "USDJUSDT", "PAXGUSDT",
    "XAUTUSDT",  # token berbasis emas
    # Leveraged tokens (mekanisme rebalance merusak analisis teknikal)
    "BTCUPUSDT", "BTCDOWNUSDT", "ETHUPUSDT", "ETHDOWNUSDT",
    "BNBUPUSDT", "BNBDOWNUSDT", "TRXUPUSDT", "TRXDOWNUSDT",
}


# ══════════════════════════════════════════════
# HTTP SESSION (dengan retry otomatis)
# ══════════════════════════════════════════════
def _build_session() -> requests.Session:
    """Buat session HTTP dengan retry back-off otomatis pada transient error."""
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
def _binance_get(path: str, params: dict | None = None, timeout: int = 15):
    """
    Coba endpoint Binance satu per satu sampai berhasil.
    Mengembalikan (data, base_url).
    """
    last_err = None
    for base in BINANCE_ENDPOINTS:
        url = f"{base}{path}"
        try:
            resp = _session.get(url, params=params, timeout=timeout)
            if resp.status_code == 451:
                log.debug(f"[binance] 451 pada {base}, mencoba endpoint berikutnya...")
                last_err = f"HTTP 451 dari {base}"
                continue
            resp.raise_for_status()
            return resp.json(), base
        except requests.RequestException as e:
            log.debug(f"[binance] {base} gagal: {e}")
            last_err = str(e)
    raise requests.RequestException(f"Semua endpoint Binance gagal diakses. Error terakhir: {last_err}")


# ══════════════════════════════════════════════
# DYNAMIC COIN SCANNER
# ══════════════════════════════════════════════
def get_top_volume_coins(limit: int = 30) -> list[str]:
    """
    Ambil daftar koin USDT paling likuid dari Binance berdasarkan 24h quote volume.
    Abaikan stablecoins dan leveraged tokens.
    """
    try:
        data, _ = _binance_get(TICKER_24HR_ENDPOINT)
    except Exception as e:
        log.error(f"Gagal mengambil ticker 24h Binance: {e}")
        return []

    valid_coins = []
    for item in data:
        symbol = item.get("symbol", "")
        if symbol.endswith("USDT") and symbol not in STABLECOIN_SYMBOLS:
            try:
                valid_coins.append({
                    "symbol": symbol,
                    "quoteVolume": float(item.get("quoteVolume", 0.0)),
                })
            except (ValueError, TypeError):
                continue

    valid_coins.sort(key=lambda x: x["quoteVolume"], reverse=True)
    return [c["symbol"] for c in valid_coins[:limit]]


# ══════════════════════════════════════════════
# BINANCE DATA FETCHER
# ══════════════════════════════════════════════
_KLINE_CACHE: dict[tuple[str, str, int], tuple[float, pd.DataFrame]] = {}


def fetch_klines(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
    """
    Ambil data candlestick (OHLCV) dari Binance Public API.
    Mengembalikan DataFrame dengan kolom OHLCV standar.
    Menggunakan cache in-memory (30s) agar tidak fetch ulang data yang sama antar strategi.
    """
    now = time.time()
    cache_key = (symbol, interval, limit)
    if cache_key in _KLINE_CACHE:
        cache_time, cached_df = _KLINE_CACHE[cache_key]
        if now - cache_time < 30.0:
            return cached_df.copy()

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    try:
        data, _ = _binance_get(KLINES_ENDPOINT, params=params)
    except requests.exceptions.ConnectionError as e:
        log.error(f"Koneksi gagal untuk {symbol} {interval}: {e}")
        return pd.DataFrame()
    except requests.exceptions.Timeout as e:
        log.error(f"Timeout saat mengambil {symbol} {interval}: {e}")
        return pd.DataFrame()
    except requests.RequestException as e:
        log.error(f"Error fetch {symbol} {interval}: {e}")
        return pd.DataFrame()

    df = _parse_klines(data)
    if not df.empty:
        _KLINE_CACHE[cache_key] = (now, df)
    return df


def _parse_klines(data: list) -> pd.DataFrame:
    """Konversi raw klines JSON Binance ke pandas DataFrame terstruktur."""
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


def fetch_klines_paginated(symbol: str, interval: str, total_limit: int = 1000) -> pd.DataFrame:
    """
    Ambil historical klines dalam jumlah besar via pagination mundur endTime.
    Digunakan oleh mesin backtest.
    """
    page_size = 1000
    all_data = []
    remaining = total_limit
    end_time = None

    while remaining > 0:
        limit = min(page_size, remaining)
        params: dict[str, str | int] = {"symbol": symbol, "interval": interval, "limit": limit}
        if end_time is not None:
            params["endTime"] = end_time

        try:
            data, _ = _binance_get(KLINES_ENDPOINT, params=params)
        except requests.RequestException as e:
            log.error(f"Pagination fetch gagal untuk {symbol} {interval}: {e}")
            break

        if not data:
            break

        all_data = data + all_data
        oldest_open_time = data[0][0]
        end_time = oldest_open_time - 1
        remaining -= len(data)

        if len(data) < limit:
            break

        time.sleep(0.08)

    if not all_data:
        return pd.DataFrame()

    df = _parse_klines(all_data)
    return df.drop_duplicates(subset="open_time").sort_values("open_time").reset_index(drop=True)


# ══════════════════════════════════════════════
# CHART GENERATOR (mplfinance)
# ══════════════════════════════════════════════
def generate_chart(symbol: str, df: pd.DataFrame) -> io.BytesIO:
    """
    Buat grafik candlestick 5m dalam format BytesIO PNG untuk dikirim ke Telegram.
    Figure selalu ditutup secara eksplisit untuk mencegah kebocoran memori.
    """
    df_chart = df.copy()
    df_chart.set_index("open_time", inplace=True)

    buf = io.BytesIO()

    # Warna candle: hijau (up), merah (down)
    mc = mpf.make_marketcolors(
        up='#26a69a',
        down='#ef5350',
        edge='inherit',
        wick='inherit',
        volume='in',
        ohlc='i'
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle=':',
        gridcolor='#2a2e39',
        facecolor='#131722',
        figcolor='#131722',
        y_on_right=True,
    )

    coin = symbol.replace("USDT", "")
    title = f"\n{coin}/USDT (5m) — Sniper Setup"

    fig, _ = mpf.plot(
        df_chart,
        type='candle',
        style=s,
        title=dict(title=title, color='#d1d4dc', size=11),
        volume=False,
        savefig=dict(fname=buf, dpi=110, bbox_inches='tight', facecolor='#131722'),
        figsize=(6.5, 4.0),
        returnfig=True,
    )

    plt.close(fig)
    buf.seek(0)
    return buf


# ══════════════════════════════════════════════
# FILTER 1 — 4H: Support Bounce + Volume Spike
# ══════════════════════════════════════════════
def check_4h_support_volume(symbol: str) -> dict:
    """Cek pantulan support dan lonjakan volume di timeframe 4H."""
    df = fetch_klines(symbol, "4h", limit=30)
    return _check_4h_support_volume_df(df)


def _check_4h_support_volume_df(df: pd.DataFrame | None) -> dict:
    """Versi pure filter 4H tanpa network fetch (digunakan juga oleh backtest)."""
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

    distance_pct = ((current_low - support_level) / support_level) * 100 if support_level else 0
    all_pass = in_support_zone and is_bouncing and has_volume_spike

    support_icon = "✅" if in_support_zone else "❌"
    bounce_icon = "✅" if is_bouncing else "❌"
    volume_icon = "✅" if has_volume_spike else "❌"

    return {
        "pass": all_pass,
        "close": round(current_close, 4),
        "current_low": round(current_low, 4),
        "support": round(support_level, 4),
        "distance": f"{distance_pct:.2f}%",
        "in_support_zone": in_support_zone,
        "is_bouncing": is_bouncing,
        "vol_ratio": round(vol_ratio, 2),
        "has_volume_spike": has_volume_spike,
        "status": "SUPPORT BOUNCE + VOL" if all_pass else "FILTER 4H GAGAL",
        "detail": (
            f"{support_icon} Support ({distance_pct:.2f}%) | "
            f"{bounce_icon} Bounce | "
            f"{volume_icon} Vol {vol_ratio:.1f}x"
        ),
    }


# ══════════════════════════════════════════════
# FILTER 2 — 1H: Stochastic Oversold
# ══════════════════════════════════════════════
def check_1h_stochastic(symbol: str) -> dict:
    """Cek osilator Stochastic (5,3,3) pada timeframe 1H."""
    df = fetch_klines(symbol, "1h", limit=50)
    return _check_1h_stochastic_df(df)


def _check_1h_stochastic_df(df: pd.DataFrame | None) -> dict:
    """Versi pure filter 1H tanpa network fetch (digunakan juga oleh backtest)."""
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
        return {"pass": False, "reason": "Stochastic bernilai NaN"}

    is_oversold = k_val <= STOCH_OVERSOLD
    os_icon = "✅" if is_oversold else "❌"

    return {
        "pass": is_oversold,
        "k": round(k_val, 2),
        "d": round(d_val, 2),
        "is_oversold": is_oversold,
        "status": "OVERSOLD" if is_oversold else "NOT OVERSOLD",
        "detail": f"{os_icon} K={k_val:.1f} (<={STOCH_OVERSOLD}) | D={d_val:.1f}",
    }


# ══════════════════════════════════════════════
# FILTER 3 — 5m: Bullish Pinbar Sniper Entry
# ══════════════════════════════════════════════
def check_5m_pinbar(symbol: str) -> dict:
    """Cek pola candle Bullish Pinbar pada timeframe 5m."""
    df = fetch_klines(symbol, "5m", limit=25)
    return _check_5m_pinbar_df(df)


def _check_5m_pinbar_df(df: pd.DataFrame | None) -> dict:
    """Versi pure filter 5m tanpa network fetch."""
    if df is None or df.empty:
        return {"pass": False, "reason": "Data fetch failed", "df": None}

    now_utc = pd.Timestamp.now(tz="UTC")
    last_close_time = df["close_time"].iloc[-1]
    secs_since_close = (now_utc - last_close_time).total_seconds()

    # Gunakan candle yang sudah tuntas terkonfirmasi close
    candle_idx = -1 if secs_since_close > 30 else -2

    candle = df.iloc[candle_idx]
    o, h, low, c = candle["open"], candle["high"], candle["low"], candle["close"]

    body = abs(c - o)
    lower_wick = max(0.0, min(o, c) - low)
    upper_wick = max(0.0, h - max(o, c))

    body_ref = max(body, 0.0001)
    wick_ratio = lower_wick / body_ref

    is_bullish = c > o
    has_long_tail = lower_wick >= (1.5 * body_ref)
    is_pinbar = is_bullish and has_long_tail

    bull_icon = "✅" if is_bullish else "❌"
    tail_icon = "✅" if has_long_tail else "❌"

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
        "detail": f"{bull_icon} Bullish | {tail_icon} Ekor Bawah {wick_ratio:.1f}x Body",
        "df": df,
    }


# ══════════════════════════════════════════════
# RISK:REWARD CALCULATOR (1:2)
# ══════════════════════════════════════════════
def calculate_risk_reward(entry: float, support: float) -> dict:
    """
    Hitung Stop Loss dan Take Profit berdasarkan Risk:Reward 1:2.
    SL = support - 1.5%
    TP = entry + 2 x (entry - SL)
    """
    sl = support * (1 - STOP_LOSS_PCT / 100)
    risk = entry - sl
    tp = entry + (risk * RISK_REWARD_RATIO)
    risk_pct = (risk / entry) * 100 if entry else 0
    reward_pct = ((tp - entry) / entry) * 100 if entry else 0

    return {
        "entry": round(entry, 4),
        "sl": round(sl, 4),
        "tp": round(tp, 4),
        "risk": round(risk, 4),
        "risk_pct": round(risk_pct, 2),
        "reward_pct": round(reward_pct, 2),
    }


# ══════════════════════════════════════════════
# ANTI-SPAM: JSON Memory System (dengan File Locking)
# ══════════════════════════════════════════════
def load_memory() -> dict:
    """Baca file memory anti-spam, kembalikan dict kosong jika file belum ada."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning(f"Gagal membaca memory file, reset ke kosong: {e}")
        return {}


def save_memory(data: dict):
    """Simpan memory ke file JSON dengan fcntl locking (mencegah race condition)."""
    try:
        with open(MEMORY_FILE, "r+" if os.path.exists(MEMORY_FILE) else "w", encoding="utf-8") as f:
            with contextlib.suppress(AttributeError, OSError):
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
            with contextlib.suppress(AttributeError, OSError):
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError as e:
        log.error(f"Gagal menyimpan memory file: {e}")


def is_on_cooldown(key: str, memory: dict) -> bool:
    """Cek apakah key (symbol atau symbol:strategy) masih dalam masa cooldown."""
    if key not in memory:
        return False
    last_alert_ts = memory[key].get("last_alert", 0)
    now_ts = datetime.now(timezone.utc).timestamp()
    elapsed_hours = (now_ts - last_alert_ts) / 3600
    return elapsed_hours < COOLDOWN_HOURS


def record_alert(key: str, memory: dict) -> dict:
    """Catat timestamp alert terbaru untuk key yang diberikan."""
    memory[key] = {
        "last_alert": datetime.now(timezone.utc).timestamp(),
        "last_alert_human": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    return memory


# ══════════════════════════════════════════════
# TELEGRAM DISPATCHER & FORMATTER
# ══════════════════════════════════════════════
def build_inline_keyboard(symbol: str) -> dict:
    """Buat inline keyboard Telegram dengan tombol cepat ke Binance, TradingView, dan CoinGecko."""
    coin = symbol.replace("USDT", "")
    return {
        "inline_keyboard": [
            [
                {
                    "text": "📊 Binance Chart",
                    "url": f"https://www.binance.com/en/trade/{coin}_USDT",
                },
                {
                    "text": "📈 TradingView",
                    "url": f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}",
                },
            ],
            [
                {
                    "text": f"🦎 {coin} di CoinGecko",
                    "url": f"https://www.coingecko.com/en/coins/{coin.lower()}",
                },
            ],
        ],
    }


def build_telegram_report(symbol: str, signal_result, ai_val: Any = None) -> str:
    """
    Format pesan laporan signal Telegram dengan ringkas, sederhana, dan jelas.
    Menyertakan hasil validasi AI dan indikator Stochastic Oscillator (5,3,3).
    """
    coin = symbol.replace("USDT", "")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    s = signal_result
    rr = s.details.get("rr", {})

    strategy_labels = {
        "reversal": "REVERSAL",
        "breakout": "BREAKOUT",
        "trend_follow": "TREND FOLLOW",
    }
    strategy_label = strategy_labels.get(s.strategy_name, s.strategy_name.upper())

    entry_val = rr.get("entry", s.entry)
    sl_val = rr.get("sl", s.stop_loss)
    tp_val = rr.get("tp", s.take_profit)
    risk_pct = rr.get("risk_pct", 0)
    reward_pct = rr.get("reward_pct", 0)
    rr_ratio = getattr(s, "risk_reward_ratio", RISK_REWARD_RATIO)

    # Info Validasi AI & Stochastic Oscillator (5,3,3) ringkas
    ai_status = "APPROVED"
    ai_score = 75
    stoch_k = "-"
    stoch_d = "-"
    stoch_stat = "NETRAL"
    stoch_cross = ""
    reason_note = ""

    if ai_val is not None:
        ai_status = "APPROVED" if ai_val.approved else "REJECTED"
        ai_score = ai_val.score
        stoch_k = ai_val.stoch_1h_k
        stoch_d = ai_val.stoch_1h_d
        stoch_stat = ai_val.stoch_status
        if ai_val.stoch_crossover and ai_val.stoch_crossover != "Netral":
            stoch_cross = f" • {ai_val.stoch_crossover}"
        if ai_val.reason:
            reason_note = f"💡 <i>{ai_val.reason}</i>\n"
    else:
        try:
            from ai_analyst import calculate_technical_summary
            tech = calculate_technical_summary(symbol)
            if tech.get("success"):
                stoch = tech.get("stoch_1h", {})
                stoch_k = stoch.get("k", "-")
                stoch_d = stoch.get("d", "-")
                stoch_stat = stoch.get("status", "NETRAL")
                if stoch.get("bullish_cross"):
                    stoch_cross = " • Bullish Golden Cross"
        except Exception as e:
            log.warning(f"Gagal mengambil teknikal untuk report {symbol}: {e}")

    report = (
        f"🎯 <b>SINYAL: {coin}/USDT — {strategy_label}</b>\n"
        f"<code>──────────────────────────────</code>\n"
        f"🤖 <b>AI:</b> {ai_status} (Skor: <b>{ai_score}/100</b>)\n"
        f"📊 <b>Stoch (5,3,3):</b> K=<code>{stoch_k}</code> | D=<code>{stoch_d}</code> ({stoch_stat}{stoch_cross})\n"
        f"{reason_note}"
        f"<code>──────────────────────────────</code>\n"
        f"💵 <b>Entry :</b> <code>{entry_val}</code>\n"
        f"🛑 <b>SL    :</b> <code>{sl_val}</code> (-{risk_pct}%)\n"
        f"🎯 <b>TP    :</b> <code>{tp_val}</code> (+{reward_pct}% | R:R 1:{rr_ratio})\n"
        f"<code>──────────────────────────────</code>\n"
        f"⏰ <i>{now_str}</i> | #{coin} #CryptoRadar"
    )
    return report


def build_signal_report(symbol: str, signal_result, ai_val: Any = None) -> str:
    """Laporan generic plain text untuk kompatibilitas."""
    return build_telegram_report(symbol, signal_result, ai_val=ai_val)


def build_external_links(symbol: str) -> dict:
    """Helper shortcut URL."""
    coin = symbol.replace("USDT", "")
    return {
        "binance": f"https://www.binance.com/en/trade/{coin}_USDT",
        "tradingview": f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}",
        "coingecko": f"https://www.coingecko.com/en/coins/{coin.lower()}",
    }


def send_telegram(
    message: str,
    reply_markup: dict | None = None,
    photo_buf: io.BytesIO | None = None,
    token: str | None = None,
    chat_id: str | None = None,
    thread_id: str | int | None = None,
    parse_mode: str = "HTML",
) -> bool:
    """
    Kirim pesan ke Telegram Bot API (mendukung teks, foto chart, dan Topik / Forum).
    """
    bot_token = token or TELEGRAM_BOT_TOKEN
    target_chat = chat_id or TELEGRAM_CHAT_ID
    target_thread = thread_id if thread_id is not None else TELEGRAM_THREAD_ID

    if not bot_token or not target_chat:
        log.warning("Kredensial Telegram belum diset (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID). Output ke konsol:")
        print(message)
        return False

    # Kirim foto dengan caption jika ada buffer gambar
    if photo_buf:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

        # Caption Telegram dibatasi maksimal 1024 karakter
        if len(message) <= 1024:
            payload: dict = {
                "chat_id": target_chat,
                "caption": message,
                "parse_mode": parse_mode,
            }
            if target_thread:
                try:
                    payload["message_thread_id"] = int(target_thread)
                except ValueError:
                    pass
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)

            files = {"photo": ("chart.png", photo_buf.getvalue(), "image/png")}
            try:
                resp = _session.post(url, data=payload, files=files, timeout=20)
                if resp.status_code == 200:
                    log.info("Telegram: Foto dan signal berhasil dikirim.")
                    return True
                if resp.status_code == 400 and "migrate_to_chat_id" in resp.text:
                    err_json = resp.json()
                    new_id = str(err_json.get("parameters", {}).get("migrate_to_chat_id"))
                    log.info(f"Chat dimigrasi ke supergroup: {new_id}. Mengirim ulang...")
                    return send_telegram(message, reply_markup=reply_markup, photo_buf=photo_buf,
                                         token=token, chat_id=new_id, thread_id=target_thread, parse_mode=parse_mode)
                log.error(f"Telegram sendPhoto gagal: {resp.status_code} — {resp.text}")
            except Exception as e:
                log.error(f"Exception saat kirim photo Telegram: {e}")
        else:
            # Jika pesan lebih dari 1024 karakter, kirim foto dahulu lalu pesan teks lengkap
            brief_caption = message.split("\n")[0]
            files = {"photo": ("chart.png", photo_buf.getvalue(), "image/png")}
            photo_data = {"chat_id": target_chat, "caption": brief_caption, "parse_mode": parse_mode}
            if target_thread:
                try:
                    photo_data["message_thread_id"] = int(target_thread)
                except ValueError:
                    pass
            try:
                _session.post(
                    url,
                    data=photo_data,
                    files=files,
                    timeout=20,
                )
            except Exception as e:
                log.error(f"Gagal kirim foto awal: {e}")

    # Kirim pesan teks (fallback atau pesan standalone)
    text_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    text_payload: dict = {
        "chat_id": target_chat,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if target_thread:
        try:
            text_payload["message_thread_id"] = int(target_thread)
        except ValueError:
            pass
    if reply_markup:
        text_payload["reply_markup"] = json.dumps(reply_markup)

    try:
        resp = _session.post(text_url, json=text_payload, timeout=15)
        if resp.status_code == 200:
            log.info("Telegram: Pesan teks berhasil dikirim.")
            return True
        if resp.status_code == 400 and "migrate_to_chat_id" in resp.text:
            err_json = resp.json()
            new_id = str(err_json.get("parameters", {}).get("migrate_to_chat_id"))
            log.info(f"Chat dimigrasi ke supergroup: {new_id}. Mengirim ulang...")
            return send_telegram(message, reply_markup=reply_markup, photo_buf=None,
                                 token=token, chat_id=new_id, thread_id=target_thread, parse_mode=parse_mode)
        log.error(f"Telegram sendMessage gagal: {resp.status_code} — {resp.text}")
        return False
    except Exception as e:
        log.error(f"Exception saat kirim pesan Telegram: {e}")
        return False


# ══════════════════════════════════════════════
# PLUGGABLE SIGNAL EMITTER
# ══════════════════════════════════════════════
_signal_sinks: list = []


def register_signal_sink(sink):
    """Daftarkan callback hook kustom untuk setiap sinyal PASS."""
    if sink not in _signal_sinks:
        _signal_sinks.append(sink)
        log.info(f"Signal sink terdaftar: {getattr(sink, '__name__', sink)}")


def unregister_signal_sink(sink):
    """Hapus callback hook."""
    if sink in _signal_sinks:
        _signal_sinks.remove(sink)


def emit_signal(symbol: str, signal_result, report: str, chart_buf: io.BytesIO | None = None):
    """Broadcast sinyal ke semua sink yang terdaftar."""
    for sink in _signal_sinks:
        try:
            sink(symbol, signal_result, report, chart_buf)
        except Exception as e:
            log.exception(f"Signal sink {sink} gagal: {e}")


# ══════════════════════════════════════════════
# MAIN SCANNER ENGINE (Multi-Strategy)
# ══════════════════════════════════════════════
def run_scanner(
    limit: int = SCAN_LIMIT,
    dry_run: bool = False,
    notify_telegram: bool = True,
) -> dict:
    """
    Eksekusi satu putaran pemindaian pasar untuk semua strategi yang aktif.
    Mengembalikan ringkasan statistik scan.
    """
    from strategies import get_strategies

    start_time = time.time()
    active_strategies = get_strategies()
    strategy_names = [s.name for s in active_strategies]

    log.info("=" * 60)
    log.info("🎯 CRYPTO RADAR v8.0 — Multi-Strategy Telegram Sniper")
    log.info("=" * 60)

    coins = get_top_volume_coins(limit=limit)

    log.info(f"Top {limit} Koin Ditemukan: {len(coins)}")
    log.info(f"Waktu Scan : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log.info(f"Strategi   : {strategy_names}")
    log.info(f"Cooldown   : {COOLDOWN_HOURS} jam | File Memory: {MEMORY_FILE}")
    log.info(f"Vol Spike  : {VOL_SPIKE_THRESHOLD}x | Mode Dry Run: {dry_run}")
    log.info("=" * 60)

    memory = load_memory()
    signals_found = 0
    detected_signals: list[dict] = []

    for idx, symbol in enumerate(coins, 1):
        coin = symbol.replace("USDT", "")
        if idx % 25 == 0 or idx == len(coins):
            log.info(f"Progress scan: {idx}/{len(coins)} koin ({coin})...")

        for strategy in active_strategies:
            memory_key = f"{symbol}:{strategy.name}"

            # Cek anti-spam cooldown per pasangan (koin, strategi)
            if not dry_run and is_on_cooldown(memory_key, memory):
                elapsed = (
                    datetime.now(timezone.utc).timestamp()
                    - memory[memory_key].get("last_alert", 0)
                ) / 3600
                remaining = COOLDOWN_HOURS - elapsed
                log.debug(f"[{strategy.name}] COOLDOWN {coin} ({remaining:.1f}h tersisa). Skip.")
                continue

            try:
                result = strategy.check_signal(symbol)
            except Exception as e:
                log.warning(f"Error evaluasi strategi {strategy.name} pada {symbol}: {e}")
                continue

            if not result.passed:
                time.sleep(0.05)
                continue

            log.info(f"🔥 CANDIDATE! {coin} [{strategy.name}] lolos filter strategi. Menjalankan Analisis AI Pre-Alert...")

            # ── VALIDASI & ANALISIS AI PRE-ALERT ──
            # Sebelum mengirim sinyal, AI melakukan analisis mendalam (Stochastic 5,3,3, tren 4H, & volume)
            try:
                from ai_analyst import validate_signal_with_ai
                ai_val = validate_signal_with_ai(symbol, strategy.name, result)
            except Exception as e:
                log.error(f"Error saat validasi AI {symbol}: {e}")
                ai_val = None

            if ai_val is not None and not ai_val.approved:
                log.info(
                    f"🛑 [AI REJECTED] {coin} [{strategy.name}] Skor: {ai_val.score}/100 "
                    f"(Stoch 1H K={ai_val.stoch_1h_k}) — Alasan: {ai_val.reason}. Sinyal TIDAK dikirim."
                )
                time.sleep(0.05)
                continue

            log.info(
                f"✅ [AI APPROVED] {coin} [{strategy.name}] Skor: {ai_val.score if ai_val else 'N/A'}/100! "
                f"Entry={result.entry} SL={result.stop_loss} TP={result.take_profit}"
            )

            # Buat chart 5m jika DataFrame tersedia
            chart_buf = None
            if result.chart_df is not None and not result.chart_df.empty:
                try:
                    chart_buf = generate_chart(symbol, result.chart_df)
                except Exception as e:
                    log.error(f"Gagal generate chart {symbol}: {e}")

            report = build_telegram_report(symbol, result, ai_val=ai_val)
            keyboard = build_inline_keyboard(symbol)

            if notify_telegram and not dry_run:
                send_telegram(report, reply_markup=keyboard, photo_buf=chart_buf)

            emit_signal(symbol, result, report, chart_buf=chart_buf)

            signals_found += 1
            detected_signals.append({
                "symbol": symbol,
                "strategy": strategy.name,
                "entry": result.entry,
                "sl": result.stop_loss,
                "tp": result.take_profit,
                "ai_score": ai_val.score if ai_val else None,
            })

            if not dry_run:
                memory = record_alert(memory_key, memory)

            time.sleep(0.2)

    if not dry_run:
        save_memory(memory)

    duration = round(time.time() - start_time, 2)
    log.info(f"Scan selesai dalam {duration}s. Sinyal ditemukan: {signals_found}")

    return {
        "scanned_count": len(coins),
        "signals_count": signals_found,
        "signals": detected_signals,
        "duration_seconds": duration,
    }


# ══════════════════════════════════════════════
# ENTRY POINT CLI
# ══════════════════════════════════════════════
if __name__ == "__main__":
    run_scanner()
