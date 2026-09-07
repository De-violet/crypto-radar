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
