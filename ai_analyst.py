"""
AI ANALYST MODULE — Crypto Radar v8.0
Integrasi Kecerdasan Buatan (AI) & Indikator Stochastic Oscillator (5,3,3).

Fitur:
1. Perhitungan Indikator Teknis:
   - Stochastic Oscillator (5,3,3) pada timeframe 1H dan 5m (K, D, status, dan Crossover)
   - Tren Multi-Timeframe (4H EMA50, EMA200, 1H EMA20)
   - Volume Surge Ratio (5m vs SMA 20)
   - Support & Resistance (Dynamic 20-candle)
2. Ulasan AI Cepat (Fast AI Insight) untuk setiap alert sinyal otomatis tanpa lag
3. Analisis AI Mendalam (Deep AI Analysis) via Antigravity CLI untuk perintah /ai <koin>
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import time
from typing import Any, Dict

import pandas as pd
import pandas_ta as ta

import radar

log = logging.getLogger("crypto-radar.ai")

# Path eksekusi Antigravity CLI untuk inferensi AI
AGY_PATH = shutil.which("agy") or "/home/deviolete/.local/bin/agy"


def calculate_technical_summary(symbol: str) -> Dict[str, Any]:
    """
    Mengambil data live Binance (4H, 1H, 5m) dan menghitung seluruh indikator teknikal:
    Stochastic Oscillator (5,3,3), EMA 20/50/200, Volume Ratio, dan Level S/R.
    """
    clean_sym = symbol.upper()
    if not clean_sym.endswith("USDT"):
        clean_sym = f"{clean_sym}USDT"
    coin = clean_sym.replace("USDT", "")

    # 1. Ambil data klines multi-timeframe
    df_4h = radar.fetch_klines(clean_sym, "4h", limit=60)
    df_1h = radar.fetch_klines(clean_sym, "1h", limit=60)
    df_5m = radar.fetch_klines(clean_sym, "5m", limit=30)

    if df_1h.empty:
        return {"success": False, "symbol": clean_sym, "coin": coin, "reason": "Gagal mengambil data pasar dari Binance"}

    curr_price = float(df_1h["close"].iloc[-1])

    # 2. Perhitungan Stochastic Oscillator (5, 3, 3) pada 1H
    stoch_1h = ta.stoch(df_1h["high"], df_1h["low"], df_1h["close"], k=5, d=3, smooth_k=3)
    k_1h, d_1h = 50.0, 50.0
    stoch_status_1h = "NETRAL"
    bullish_cross_1h = False
    bearish_cross_1h = False

    if stoch_1h is not None and not stoch_1h.empty:
        k_col = [c for c in stoch_1h.columns if "STOCHk" in c][0]
        d_col = [c for c in stoch_1h.columns if "STOCHd" in c][0]
        k_1h = float(stoch_1h[k_col].iloc[-1])
        d_1h = float(stoch_1h[d_col].iloc[-1])
        prev_k = float(stoch_1h[k_col].iloc[-2]) if len(stoch_1h) >= 2 else k_1h
        prev_d = float(stoch_1h[d_col].iloc[-2]) if len(stoch_1h) >= 2 else d_1h

        bullish_cross_1h = (prev_k <= prev_d) and (k_1h > d_1h)
        bearish_cross_1h = (prev_k >= prev_d) and (k_1h < d_1h)

        if k_1h <= 15:
            stoch_status_1h = "DEEP OVERSOLD (Sangat Jenuh Jual)"
        elif k_1h <= 25:
            stoch_status_1h = "OVERSOLD (Jenuh Jual)"
        elif k_1h >= 80:
            stoch_status_1h = "OVERBOUGHT (Jenuh Beli)"
        else:
            stoch_status_1h = "NETRAL / MOMENTUM"

    # 3. Perhitungan Stochastic Oscillator (5, 3, 3) pada 5m (Micro-Timing)
    k_5m, d_5m = 50.0, 50.0
    if not df_5m.empty:
        stoch_5m = ta.stoch(df_5m["high"], df_5m["low"], df_5m["close"], k=5, d=3, smooth_k=3)
        if stoch_5m is not None and not stoch_5m.empty:
            k_col5 = [c for c in stoch_5m.columns if "STOCHk" in c][0]
            d_col5 = [c for c in stoch_5m.columns if "STOCHd" in c][0]
            k_5m = float(stoch_5m[k_col5].iloc[-1])
            d_5m = float(stoch_5m[d_col5].iloc[-1])

    # 4. Tren 4H & EMA
    trend_4h = "NETRAL"
    ema50_4h = curr_price
    ema200_4h = curr_price
    if not df_4h.empty and len(df_4h) >= 50:
        ema50_s = ta.ema(df_4h["close"], length=50)
        ema50_4h = float(ema50_s.iloc[-1]) if ema50_s is not None else curr_price
        if curr_price > ema50_4h:
            trend_4h = "BULLISH (Di atas EMA 50)"
        else:
            trend_4h = "BEARISH (Di bawah EMA 50)"

    # 5. Volume Spike 5m
    vol_ratio = 1.0
    if not df_5m.empty and len(df_5m) >= 20:
        vol_sma = df_5m["volume"].rolling(20).mean().iloc[-2]
        curr_vol = df_5m["volume"].iloc[-1]
        if vol_sma and vol_sma > 0:
            vol_ratio = round(curr_vol / vol_sma, 2)

    # 6. Support & Resistance (20 candle terakhir 1H)
    support_20 = float(df_1h["low"].tail(20).min())
    resistance_20 = float(df_1h["high"].tail(20).max())

    # Stop Loss & Take Profit (R:R 1:2)
    sl_price = round(support_20 * 0.985, 4)
    risk = max(curr_price - sl_price, curr_price * 0.015)
    tp_price = round(curr_price + (risk * 2.0), 4)

    return {
        "success": True,
        "symbol": clean_sym,
        "coin": coin,
        "price": curr_price,
        "stoch_1h": {
            "k": round(k_1h, 1),
            "d": round(d_1h, 1),
            "status": stoch_status_1h,
            "bullish_cross": bullish_cross_1h,
            "bearish_cross": bearish_cross_1h,
        },
        "stoch_5m": {
            "k": round(k_5m, 1),
            "d": round(d_5m, 1),
        },
        "trend_4h": trend_4h,
        "ema50_4h": round(ema50_4h, 4),
        "vol_ratio_5m": vol_ratio,
        "support": round(support_20, 4),
        "resistance": round(resistance_20, 4),
        "entry": curr_price,
        "stop_loss": sl_price,
        "take_profit": tp_price,
        "rr_ratio": "1:2",
    }


def generate_fast_ai_summary(symbol: str, tech_data: Dict[str, Any], strategy_name: str = "") -> str:
    """
    Menghasilkan ulasan AI reasoning ringkas dan tajam untuk pesan alert real-time.
    Berjalan secara deterministik instan (0ms) agar loop background tetap cepat.
    """
    if not tech_data or not tech_data.get("success"):
        return "Analisis momentum teknikal menunjukkan setup terkonfirmasi dengan risiko terukur."

    coin = tech_data["coin"]
    stoch = tech_data.get("stoch_1h", {})
    k_val = stoch.get("k", 50.0)
    d_val = stoch.get("d", 50.0)
    b_cross = stoch.get("bullish_cross", False)
    trend = tech_data.get("trend_4h", "NETRAL")
    vol_ratio = tech_data.get("vol_ratio_5m", 1.0)

    parts = []
    if k_val <= 20:
        if b_cross:
            parts.append(
                f"Stochastic (5,3,3) berada di area oversold (K={k_val}, D={d_val}) dengan sinyal konfirmasi Golden Cross. Tekanan jual telah habis dan momentum pembalikan arah terbentuk."
            )
        else:
            parts.append(
                f"Stochastic (5,3,3) mengonfirmasi area jenuh jual (K={k_val}, D={d_val}). Menandakan potensi kuat terjadinya technical bounce dari support kunci."
            )
    elif k_val >= 80:
        parts.append(
            f"Stochastic (5,3,3) di area overbought (K={k_val}), didorong oleh momentum beli yang kuat."
        )
    else:
        if b_cross:
            parts.append(
                f"Stochastic (5,3,3) memicu Golden Cross sehat di level K={k_val}, D={d_val}, memperkuat dorongan momentum harga."
            )
        else:
            parts.append(
                f"Stochastic (5,3,3) berada pada zona ekspansi momentum stabil (K={k_val}, D={d_val})."
            )

    if vol_ratio >= 1.5:
        parts.append(f"Aktivitas volume 5m melonjak {vol_ratio}x rata-rata, menandakan partisipasi beli signifikan.")
    else:
        parts.append(f"Struktur tren 4H berjalan {trend} dengan toleransi risiko terkendali.")

    parts.append(f"Setup memiliki probabilitas terarah dengan target Risk-to-Reward 1:2.")
    return " ".join(parts)


def run_deep_ai_analysis(symbol: str) -> str:
    """
    Menjalankan analisis teknikal mendalam berbasis AI untuk perintah /ai <koin>.
    Menggabungkan metrik teknikal live dengan model AI Antigravity (agy).
    """
    tech = calculate_technical_summary(symbol)
    if not tech.get("success"):
        return f"❌ Gagal mengambil data pasar untuk <b>{symbol}</b>. Pastikan simbol koin valid di Binance."

    coin = tech["coin"]
    price = tech["price"]
    stoch = tech["stoch_1h"]
    stoch_5m = tech["stoch_5m"]
    k_val = stoch["k"]
    d_val = stoch["d"]
    stoch_stat = stoch["status"]
    b_cross = "Ya (Bullish Golden Cross)" if stoch["bullish_cross"] else ("Ya (Bearish Death Cross)" if stoch["bearish_cross"] else "Belum Cross")
    trend_4h = tech["trend_4h"]
    vol_ratio = tech["vol_ratio_5m"]
    supp = tech["support"]
    res = tech["resistance"]
    entry = tech["entry"]
    sl = tech["stop_loss"]
    tp = tech["take_profit"]

    ai_commentary = ""
    prompt = (
        f"Sebagai analis crypto kuantitatif profesional, berikan ulasan teknikal ringkas 3-4 poin dalam bahasa Indonesia "
        f"untuk koin {coin}/USDT berdasarkan data live berikut:\n"
        f"- Harga Saat Ini: {price} USDT\n"
        f"- Stochastic Oscillator (5,3,3) 1H: K={k_val}, D={d_val} ({stoch_stat}, Crossover: {b_cross})\n"
        f"- Stochastic (5,3,3) 5m: K={stoch_5m['k']}, D={stoch_5m['d']}\n"
        f"- Tren 4H: {trend_4h}\n"
        f"- Volume Spike 5m: {vol_ratio}x rata-rata 20 candle\n"
        f"- Support Kunci: {supp} | Resistance Kunci: {res}\n"
        f"Jelaskan implikasi Stochastic (5,3,3), reaksi volume, dan panduan manajemen risiko tanpa pengantar panjang."
    )

    try:
        res_proc = subprocess.run(
            [AGY_PATH, "-p", prompt, "--dangerously-skip-permissions"],
            capture_output=True,
            text=True,
            timeout=25,
        )
        if res_proc.returncode == 0 and res_proc.stdout.strip():
            ai_commentary = res_proc.stdout.strip()
    except Exception as e:
        log.warning(f"Antigravity CLI tidak merespons atau timeout ({e}), menggunakan engine teknis fallback.")

    if not ai_commentary:
        ai_commentary = (
            f"1. <b>Momentum Stochastic (5,3,3):</b> Level K={k_val} dan D={d_val} berada pada fase {stoch_stat}. "
            f"Kondisi ini memberikan sinyal bahwa pergerakan harga berada dalam zona teknikal yang jelas.\n"
            f"2. <b>Tren & Struktur Pasar (4H):</b> {trend_4h}. Level support kunci di {supp} menjadi batas pertahanan penting dari koreksi harga.\n"
            f"3. <b>Konfirmasi Volume:</b> Volume pada timeframe 5m tercatat sebesar {vol_ratio}x rata-rata, menunjukkan respons pasar aktif terhadap level saat ini."
        )

    report = (
        f"🤖 <b>ANALISIS AI & TEKNIKAL — {coin}/USDT</b>\n"
        f"<code>──────────────────────────────</code>\n"
        f"💵 <b>Harga Live:</b> <code>{price} USDT</code>\n\n"
        f"📊 <b>INDIKATOR STOCHASTIC OSCILLATOR (5,3,3):</b>\n"
        f"  • Timeframe 1H : <b>K={k_val}</b> | <b>D={d_val}</b>\n"
        f"  • Status 1H    : <code>{stoch_stat}</code>\n"
        f"  • Crossover    : <code>{b_cross}</code>\n"
        f"  • Timeframe 5m : K={stoch_5m['k']} | D={stoch_5m['d']}\n\n"
        f"📈 <b>STRUKTUR TREN & VOLUME:</b>\n"
        f"  • Tren Utama (4H) : <code>{trend_4h}</code>\n"
        f"  • Rasio Volume 5m : <code>{vol_ratio}x rata-rata</code>\n"
        f"  • Support / Resist: <code>{supp}</code> / <code>{res}</code>\n\n"
        f"<code>──────────────────────────────</code>\n"
        f"🧠 <b>ULASAN ANALISIS AI:</b>\n"
        f"{ai_commentary}\n\n"
        f"<code>──────────────────────────────</code>\n"
        f"🎯 <b>REKOMENDASI TRADING PLAN (R:R 1:2):</b>\n"
        f"  • <b>Entry Area</b>: <code>{entry}</code>\n"
        f"  • <b>Stop Loss</b> : <code>{sl}</code>\n"
        f"  • <b>Take Profit</b>: <code>{tp}</code>\n\n"
        f"<i>Analisis otomatis dihasilkan dengan data live Binance Public API.</i>"
    )
    return report


from dataclasses import dataclass, field


@dataclass
class AIValidationResult:
    """Hasil evaluasi dan validasi AI pre-alert."""
    approved: bool
    score: int
    stoch_1h_k: float
    stoch_1h_d: float
    stoch_status: str
    stoch_crossover: str
    verdict: str
    reason: str
    ai_commentary: str
    tech_data: Dict[str, Any] = field(default_factory=dict)


def validate_signal_with_ai(symbol: str, strategy_name: str, signal_result: Any = None) -> AIValidationResult:
    """
    Evaluasi & validasi koin oleh AI sebelum sinyal diizinkan dikirim ke Telegram.
    Menganalisis Stochastic Oscillator (5,3,3), tren 4H, dan volume spike.
    Hanya mengembalikan approved=True jika skor keyakinan AI memenuhi ambang batas (>=65).
    """
    tech = calculate_technical_summary(symbol)
    coin = symbol.replace("USDT", "")

    # Ambil data Stochastic 1H
    stoch = tech.get("stoch_1h", {}) if tech.get("success") else {}
    k_1h = stoch.get("k", 50.0)
    d_1h = stoch.get("d", 50.0)
    stoch_stat = stoch.get("status", "NETRAL")
    b_cross = stoch.get("bullish_cross", False)
    bear_cross = stoch.get("bearish_cross", False)
    crossover_label = "Bullish Golden Cross" if b_cross else ("Bearish Death Cross" if bear_cross else "Netral")

    score = 50
    reasons = []

    # 1. Evaluasi Stochastic Oscillator (5,3,3)
    if k_1h > 85:
        score -= 40
        reasons.append(f"Stochastic 1H overbought ekstrim (K={k_1h}), risiko koreksi tinggi")
    elif k_1h > 80:
        score -= 20
        reasons.append(f"Stochastic 1H di area jenuh beli (K={k_1h})")
    elif k_1h <= 20:
        score += 25
        reasons.append(f"Stochastic 1H di area oversold (K={k_1h}), zona risiko rendah")
    elif k_1h <= 30:
        score += 15
        reasons.append(f"Stochastic 1H mendekati oversold (K={k_1h})")
    else:
        score += 10
        reasons.append(f"Stochastic 1H berada di zona momentum ekspansi (K={k_1h})")

    if b_cross:
        score += 15
        reasons.append("Golden cross Stochastic (5,3,3) terkonfirmasi")
    elif bear_cross and k_1h > 70:
        score -= 20
        reasons.append("Death cross Stochastic (5,3,3) di area tinggi")

    # 2. Evaluasi Tren 4H
    trend_4h = tech.get("trend_4h", "NETRAL")
    if "BULLISH" in trend_4h:
        score += 15
        reasons.append("Tren 4H terkonfirmasi Bullish di atas EMA 50")
    elif strategy_name == "reversal":
        score += 10
        reasons.append("Pola reversal dasar (bottom fishing) terdeteksi")
    else:
        score -= 10
        reasons.append("Harga di bawah EMA 50 pada 4H")

    # 3. Evaluasi Volume
    vol_ratio = tech.get("vol_ratio_5m", 1.0)
    if vol_ratio >= 1.5:
        score += 15
        reasons.append(f"Volume spike {vol_ratio}x rata-rata")
    elif vol_ratio < 0.9:
        score -= 10
        reasons.append("Volume di bawah rata-rata")

    score = max(0, min(100, score))

    # Kriteria persetujuan AI: Skor >= 65 dan Stochastic K <= 82
    approved = (score >= 65 and k_1h <= 82)

    verdict = "APPROVED" if approved else "REJECTED"
    primary_reason = reasons[0] if reasons else ("Skor mencukupi" if approved else "Skor tidak mencukupi")

    # Ulasan AI commentary untuk dimasukkan ke laporan
    ai_commentary = generate_fast_ai_summary(symbol, tech, strategy_name=strategy_name)

    return AIValidationResult(
        approved=approved,
        score=score,
        stoch_1h_k=k_1h,
        stoch_1h_d=d_1h,
        stoch_status=stoch_stat,
        stoch_crossover=crossover_label,
        verdict=verdict,
        reason=primary_reason,
        ai_commentary=ai_commentary,
        tech_data=tech,
    )
