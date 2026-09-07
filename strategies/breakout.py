"""
Breakout Strategy — Momentum Continuation

3-Filter Resistance Breakout:
  4H Trend Confirmation (price > EMA50, EMA50 sloping up)
   -> 1H Consolidation Break (close > rolling max of last 20 highs)
   -> 5m Volume-Confirmed Breakout Entry (close > breakout level + vol spike)

Entry di breakout 5m, SL di bawah breakout candle low, TP = R:R 1:2.

Berbeda dengan Reversal:
- Reversal cari bottom (oversold, support bounce)
- Breakout cari momentum (resistance break, volume confirmation)
"""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta

import radar

from .base import BaseStrategy, SignalResult

BREAKOUT_VOL_THRESHOLD = 1.5  # 5m volume must be >= 1.5x avg 20


class BreakoutStrategy(BaseStrategy):
    name = "breakout"
    direction = "long"
    risk_reward_ratio = 2.0
    stop_loss_pct = 1.0  # tighter SL for breakout (1% below breakout candle low)

    # ───────────────────────────────────────────────
    # Filter helpers (pure, accept DataFrame)
    # ───────────────────────────────────────────────
    @staticmethod
    def _check_4h_trend(df_4h: pd.DataFrame) -> dict:
        """
        4H trend confirmation: close > EMA50 AND EMA50 > EMA50.shift(5).
        Means price is above an upward-sloping EMA50.
        """
        if df_4h is None or len(df_4h) < 55:
            return {"pass": False, "reason": "Insufficient 4H data"}

        ema50 = ta.ema(df_4h["close"], length=50)
        last_close = df_4h["close"].iloc[-1]
        last_ema = ema50.iloc[-1]
        prev_ema = ema50.iloc[-6] if len(ema50) >= 6 else None

        if pd.isna(last_ema) or prev_ema is None or pd.isna(prev_ema):
            return {"pass": False, "reason": "EMA NaN"}

        price_above_ema = last_close > last_ema
        ema_rising = last_ema > prev_ema

        passed = price_above_ema and ema_rising
        return {
            "pass": passed,
            "close": round(last_close, 4),
            "ema50": round(last_ema, 4),
            "price_above_ema": price_above_ema,
            "ema_rising": ema_rising,
            "status": "UPTREND" if passed else "NO TREND",
            "detail": (
                f"[{'Y' if price_above_ema else 'N'}] Price > EMA50  "
                f"[{'Y' if ema_rising else 'N'}] EMA Rising"
            ),
        }

    @staticmethod
    def _check_1h_consolidation_break(df_1h: pd.DataFrame) -> dict:
        """
        1H break of last 20-candle high (excluding current candle).
        """
        if df_1h is None or len(df_1h) < 25:
            return {"pass": False, "reason": "Insufficient 1H data"}

        prior_20 = df_1h.iloc[-21:-1]  # exclude current candle
        resistance = prior_20["high"].max()
        last_close = df_1h["close"].iloc[-1]

        broke = last_close > resistance
        return {
            "pass": broke,
            "close": round(last_close, 4),
            "resistance": round(resistance, 4),
            "status": "BROKEN" if broke else "BELOW RESISTANCE",
            "detail": f"Close {last_close:.4f} vs Resistance {resistance:.4f}",
        }

    @staticmethod
    def _check_5m_volume_breakout(df_5m: pd.DataFrame) -> dict:
        """
        5m breakout entry: candle close > prev_candle_high AND volume >= 1.5x avg.
        """
        if df_5m is None or len(df_5m) < 25:
            return {"pass": False, "reason": "Insufficient 5m data"}

        last = df_5m.iloc[-1]
        prev = df_5m.iloc[-2]
        prev_high = prev["high"]
        last_close = last["close"]
        last_high = last["high"]
        last_low = last["low"]
        last_vol = last["volume"]

        avg_vol = df_5m["volume"].iloc[-21:-1].mean()
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 0

        broke_prev_high = last_close > prev_high
        has_vol_spike = vol_ratio >= BREAKOUT_VOL_THRESHOLD

        passed = broke_prev_high and has_vol_spike
        return {
            "pass": passed,
            "close": round(last_close, 4),
            "high": round(last_high, 4),
            "low": round(last_low, 4),
            "vol_ratio": round(vol_ratio, 2),
            "status": "VOLUME BREAKOUT" if passed else "NO BREAKOUT",
            "detail": (
                f"[{'Y' if broke_prev_high else 'N'}] Close > PrevHigh  "
                f"[{'Y' if has_vol_spike else 'N'}] Vol {vol_ratio:.1f}x"
            ),
        }

    # ───────────────────────────────────────────────
    # Strategy interface
    # ───────────────────────────────────────────────
    def check_signal(self, symbol: str) -> SignalResult:
        df_4h = radar.fetch_klines(symbol, "4h", limit=60)
        df_1h = radar.fetch_klines(symbol, "1h", limit=50)
        df_5m = radar.fetch_klines(symbol, "5m", limit=30)
        return self._evaluate(df_4h, df_1h, df_5m)

    def _evaluate(self, df_4h, df_1h, df_5m) -> SignalResult:
        h4 = self._check_4h_trend(df_4h)
        if not h4["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=h4.get("detail", h4.get("reason", "4H fail")),
                details={"4h": h4},
            )

        h1 = self._check_1h_consolidation_break(df_1h)
        if not h1["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=h1.get("detail", h1.get("reason", "1H fail")),
                details={"4h": h4, "1h": h1},
            )

        m5 = self._check_5m_volume_breakout(df_5m)
        if not m5["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=m5.get("detail", m5.get("reason", "5m fail")),
                details={"4h": h4, "1h": h1, "5m": m5},
            )

        # Entry: 5m close. SL: 1% below 5m low. Reference: 5m low.
        entry = m5["close"]
        reference = m5["low"]
        rr = self.calculate_rr(entry, reference)

        return SignalResult(
            strategy_name=self.name,
            passed=True,
            entry=entry,
            stop_loss=rr["sl"],
            take_profit=rr["tp"],
            support=reference,  # reuse field as "reference level"
            details={"4h": h4, "1h": h1, "5m": m5, "rr": rr},
            chart_df=df_5m.tail(25) if df_5m is not None else None,
        )
