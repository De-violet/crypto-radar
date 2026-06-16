"""
Reversal Strategy (extracted from radar.py v5.1).

3-Filter Bottom Fishing:
  4H Support Bounce + Volume Spike  ->  1H Stochastic Oversold  ->  5m Bullish Pinbar

Coin yang lolos semua filter = high-conviction reversal entry.
"""
from __future__ import annotations

import pandas as pd

import radar
from .base import BaseStrategy, SignalResult


class ReversalStrategy(BaseStrategy):
    name = "reversal"
    direction = "long"
    risk_reward_ratio = 2.0
    stop_loss_pct = 1.5

    def required_lookback(self) -> dict:
        return {"4h": 30, "1h": 50, "5m": 25}

    def check_signal(self, symbol: str) -> SignalResult:
        h4 = radar.check_4h_support_volume(symbol)
        if not h4["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=h4.get("detail", h4.get("reason", "4H fail")),
                details={"4h": h4},
            )

        h1 = radar.check_1h_stochastic(symbol)
        if not h1["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=h1.get("detail", h1.get("reason", "1H fail")),
                details={"4h": h4, "1h": h1},
            )

        m5 = radar.check_5m_pinbar(symbol)
        if not m5["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=m5.get("detail", m5.get("reason", "5m fail")),
                details={"4h": h4, "1h": h1, "5m": m5},
            )

        entry = m5["close"]
        support = h4["support"]
        rr = self.calculate_rr(entry, support)

        return SignalResult(
            strategy_name=self.name,
            passed=True,
            entry=entry,
            stop_loss=rr["sl"],
            take_profit=rr["tp"],
            support=support,
            details={"4h": h4, "1h": h1, "5m": m5, "rr": rr},
            chart_df=m5["df"],
        )

    def check_signal_at(self, dfs: dict, current_time: pd.Timestamp) -> SignalResult:
        # Slice data "as of current_time" untuk simulasi backtest
        df_4h = dfs.get("4h")
        df_1h = dfs.get("1h")
        df_5m = dfs.get("5m")
        if df_4h is None or df_1h is None or df_5m is None:
            return SignalResult(strategy_name=self.name, passed=False, reason="Missing TF data")

        df_4h = df_4h.loc[df_4h["close_time"] <= current_time]
        df_1h = df_1h.loc[df_1h["close_time"] <= current_time]
        df_5m = df_5m.loc[df_5m["close_time"] <= current_time]

        if len(df_4h) < 30 or len(df_1h) < 50 or len(df_5m) < 25:
            return SignalResult(strategy_name=self.name, passed=False, reason="Insufficient history")

        # Ambil window terakhir sesuai lookback
        h4 = radar._check_4h_support_volume_df(df_4h.tail(30))
        if not h4["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=h4.get("detail", h4.get("reason", "4H fail")),
                details={"4h": h4},
            )

        h1 = radar._check_1h_stochastic_df(df_1h.tail(50))
        if not h1["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=h1.get("detail", h1.get("reason", "1H fail")),
                details={"4h": h4, "1h": h1},
            )

        m5 = radar._check_5m_pinbar_df(df_5m.tail(25))
        if not m5["pass"]:
            return SignalResult(
                strategy_name=self.name, passed=False,
                reason=m5.get("detail", m5.get("reason", "5m fail")),
                details={"4h": h4, "1h": h1, "5m": m5},
            )

        entry = m5["close"]
        support = h4["support"]
        rr = self.calculate_rr(entry, support)

        return SignalResult(
            strategy_name=self.name,
            passed=True,
            entry=entry,
            stop_loss=rr["sl"],
            take_profit=rr["tp"],
            support=support,
            details={"4h": h4, "1h": h1, "5m": m5, "rr": rr},
            chart_df=None,  # no chart in backtest
        )
