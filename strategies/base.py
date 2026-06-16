"""
Base classes for trading strategies.

Each strategy implements `check_signal(symbol)` for live mode and
`check_signal_at(dfs, current_time)` for backtest mode. Both return a
`SignalResult` dataclass so the orchestrator can treat all strategies
uniformly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd


@dataclass
class SignalResult:
    """Hasil evaluasi sebuah strategi untuk satu symbol/step."""
    strategy_name: str
    passed: bool
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    support: Optional[float] = None           # level acuan untuk SL
    direction: str = "long"                    # "long" atau "short" (future-proof)
    details: dict = field(default_factory=dict)
    chart_df: Optional[pd.DataFrame] = None    # untuk chart generation di live mode
    reason: str = ""                           # kalau fail, kenapa


class BaseStrategy(ABC):
    """
    Abstract base untuk semua strategi.

    Subclass wajib implement:
      - name: identifier string (unik)
      - check_signal(symbol) -> SignalResult (live mode)
      - check_signal_at(dfs, current_time) -> SignalResult (backtest mode)
      - required_lookback() -> dict[tf, int] (candle count per TF yang dibutuhkan)
    """
    name: str = "base"
    direction: str = "long"
    risk_reward_ratio: float = 2.0
    stop_loss_pct: float = 1.5

    @abstractmethod
    def check_signal(self, symbol: str) -> SignalResult:
        """Live mode: fetch fresh data via radar.fetch_klines, evaluate."""
        ...

    @abstractmethod
    def check_signal_at(
        self, dfs: dict, current_time: pd.Timestamp
    ) -> SignalResult:
        """
        Backtest mode: evaluate strategy at `current_time` using pre-fetched
        DataFrames in `dfs` (keyed by timeframe, e.g. {"4h": df_4h, ...}).
        Strategy should slice dfs[tf].loc[:current_time] to simulate "as of
        that moment" data.
        """
        ...

    @abstractmethod
    def required_lookback(self) -> dict:
        """Return {"4h": 30, "1h": 50, "5m": 25} etc."""
        ...

    def calculate_rr(self, entry: float, reference: float) -> dict:
        """
        Hitung SL/TP dari reference level (biasanya support untuk long).
        SL = reference * (1 - stop_loss_pct/100)
        TP = entry + risk_reward_ratio * (entry - SL)
        """
        sl = reference * (1 - self.stop_loss_pct / 100)
        risk = entry - sl
        tp = entry + (risk * self.risk_reward_ratio)
        return {
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "risk": risk,
            "risk_pct": round((risk / entry) * 100, 4) if entry else 0,
            "reward_pct": round(((tp - entry) / entry) * 100, 4) if entry else 0,
        }
