"""
Trend-Follow Strategy — Pullback Continuation

3-Filter Trend Following:
  4H Long-term Trend (price > EMA200)
   -> 1H MACD Bullish (histogram > 0, signal cross)
   -> 5m Pullback Entry (price touch EMA20, then bullish engulfing candle)

Entry di bullish engulfing setelah pullback ke EMA20 5m.
SL di bawah EMA20 5m, TP = R:R 1:2.

Berbeda dengan Breakout:
- Breakout cari momentum baru (resistance break)
- Trend-Follow cari continuation (pullback ke MA dalam tren yang established)
"""
from __future__ import annotations

import pandas as pd
import pandas_ta as ta

import radar

from .base import BaseStrategy, SignalResult


class TrendFollowStrategy(BaseStrategy):
    name = "trend_follow"
    direction = "long"
    risk_reward_ratio = 2.0
    stop_loss_pct = 1.0

    def required_lookback(self) -> dict:
        return {"4h": 220, "1h": 100, "5m": 50}

    # ───────────────────────────────────────────────
    # Filter helpers (pure)
    # ───────────────────────────────────────────────
    @staticmethod
    def _check_4h_trend(df_4h: pd.DataFrame) -> dict:
        """4H: price > EMA200 (long-term uptrend)."""
        if df_4h is None or len(df_4h) < 210:
            return {"pass": False, "reason": "Insufficient 4H data (need 210+)"}

        ema200 = ta.ema(df_4h["close"], length=200)
        last_close = df_4h["close"].iloc[-1]
        last_ema = ema200.iloc[-1]

        if pd.isna(last_ema):
            return {"pass": False, "reason": "EMA200 NaN"}

        passed = last_close > last_ema
        return {
            "pass": passed,
            "close": round(last_close, 4),
            "ema200": round(last_ema, 4),
            "status": "UPTREND" if passed else "BELOW EMA200",
            "detail": f"Close {last_close:.4f} vs EMA200 {last_ema:.4f}",
        }

    @staticmethod
    def _check_1h_macd(df_1h: pd.DataFrame) -> dict:
        """1H: MACD histogram > 0 (bullish momentum)."""
        if df_1h is None or len(df_1h) < 50:
            return {"pass": False, "reason": "Insufficient 1H data"}

        macd = ta.macd(df_1h["close"], fast=12, slow=26, signal=9)
        if macd is None or macd.empty:
            return {"pass": False, "reason": "MACD NaN"}

        hist_col = [c for c in macd.columns if "MACDh" in c][0]
        hist = macd[hist_col]
        last_hist = hist.iloc[-1]
        prev_hist = hist.iloc[-2]

        if pd.isna(last_hist) or pd.isna(prev_hist):
            return {"pass": False, "reason": "MACD hist NaN"}

        # Bullish: histogram positive AND increasing
        passed = last_hist > 0 and last_hist > prev_hist
        return {
            "pass": passed,
            "hist": round(last_hist, 6),
            "status": "BULLISH MOMENTUM" if passed else "NO MOMENTUM",
            "detail": f"Hist {last_hist:.6f} (prev {prev_hist:.6f})",
        }

    @staticmethod
    def _check_5m_pullback_engulfing(df_5m: pd.DataFrame) -> dict:
        """
        5m: Bullish engulfing pattern setelah pullback ke EMA20.
        - Candle [-2] bearish (close < open)
        - Candle [-1] bullish (close > open) dengan body engulfing candle [-2]
        - Low candle [-2] ATAU [-1] dekat EMA20 (dalam 0.3%)
        """
        if df_5m is None or len(df_5m) < 40:
            return {"pass": False, "reason": "Insufficient 5m data"}

        ema20 = ta.ema(df_5m["close"], length=20)
        if ema20 is None or ema20.empty:
            return {"pass": False, "reason": "EMA20 NaN"}

        prev = df_5m.iloc[-2]
        last = df_5m.iloc[-1]
        last_ema = ema20.iloc[-1]

        if pd.isna(last_ema):
            return {"pass": False, "reason": "EMA20 NaN at last candle"}

        prev_bearish = prev["close"] < prev["open"]
        last_bullish = last["close"] > last["open"]
        engulfing = (last["close"] >= prev["open"]) and (last["open"] <= prev["close"])

        # Pullback: low candle [-2] atau [-1] dekat EMA20 (within 0.3%)
        pullback_to_ema = (
            abs(prev["low"] - last_ema) / last_ema < 0.003 or
            abs(last["low"] - last_ema) / last_ema < 0.003
        )

        passed = prev_bearish and last_bullish and engulfing and pullback_to_ema
        return {
            "pass": passed,
            "close": round(last["close"], 4),
            "ema20": round(last_ema, 4),
            "engulfing": engulfing,
            "pullback": pullback_to_ema,
            "status": "ENGULFING AT EMA20" if passed else "NO PATTERN",
            "detail": (
                f"[{'Y' if prev_bearish else 'N'}] Prev Bear  "
                f"[{'Y' if last_bullish else 'N'}] Last Bull  "
                f"[{'Y' if engulfing else 'N'}] Engulf  "
                f"[{'Y' if pullback_to_ema else 'N'}] @EMA20"
            ),
        }

    # ───────────────────────────────────────────────
    # Strategy interface
    # ───────────────────────────────────────────────
    def check_signal(self, symbol: str) -> SignalResult:
        df_4h = radar.fetch_klines(symbol, "4h", limit=220)
        df_1h = radar.fetch_klines(symbol, "1h", limit=100)
        df_5m = radar.fetch_klines(symbol, "5m", limit=50)
        return self._evaluate(df_4h, df_1h, df_5m)

    def check_signal_at(self, dfs: dict, current_time: pd.Timestamp) -> SignalResult:
        df_4h = dfs.get("4h")
        df_1h = dfs.get("1h")
        df_5m = dfs.get("5m")
        if df_4h is None or df_1h is None or df_5m is None:
            return SignalResult(strategy_name=self.name, passed=False, reason="Missing TF data")

        df_4h = df_4h.loc[df_4h["close_time"] <= current_time]
        df_1h = df_1h.loc[df_1h["close_time"] <= current_time]
        df_5m = df_5m.loc[df_5m["close_time"] <= current_time]

        return self._evaluate(df_4h, df_1h, df_5m)

    def _evaluate(self, df_4h, df_1h, df_5m) -> SignalResult:
        h4 = self._check_4h_trend(df_4h)
        if not h4["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=h4.get("detail", h4.get("reason", "4H fail")),
                details={"4h": h4},
            )

        h1 = self._check_1h_macd(df_1h)
        if not h1["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=h1.get("detail", h1.get("reason", "1H fail")),
                details={"4h": h4, "1h": h1},
            )

        m5 = self._check_5m_pullback_engulfing(df_5m)
        if not m5["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=m5.get("detail", m5.get("reason", "5m fail")),
                details={"4h": h4, "1h": h1, "5m": m5},
            )

        # Entry: 5m close. SL: 1% below EMA20. Reference: EMA20.
        entry = m5["close"]
        reference = m5["ema20"]
        rr = self.calculate_rr(entry, reference)

        return SignalResult(
            strategy_name=self.name,
            passed=True,
            entry=entry,
            stop_loss=rr["sl"],
            take_profit=rr["tp"],
            support=reference,
            details={"4h": h4, "1h": h1, "5m": m5, "rr": rr},
            chart_df=df_5m.tail(25) if df_5m is not None else None,
        )
