"""
Unit tests untuk strategi (reversal, breakout, trend_follow).
Tests pakai pre-fetched synthetic DataFrames — no network.
"""
import pandas as pd

from strategies import (
    STRATEGY_REGISTRY,
    BreakoutStrategy,
    ReversalStrategy,
    TrendFollowStrategy,
    get_strategies,
)
from strategies.base import SignalResult


# ══════════════════════════════════════════════
# Registry / factory
# ══════════════════════════════════════════════
class TestStrategyRegistry:
    def test_registry_has_three_strategies(self):
        assert set(STRATEGY_REGISTRY.keys()) == {"reversal", "breakout", "trend_follow"}

    def test_get_strategies_returns_all_when_no_args(self, monkeypatch):
        monkeypatch.delenv("STRATEGIES", raising=False)
        strategies = get_strategies()
        assert len(strategies) == 3
        names = {s.name for s in strategies}
        assert names == {"reversal", "breakout", "trend_follow"}

    def test_get_strategies_filters_by_env(self, monkeypatch):
        monkeypatch.setenv("STRATEGIES", "reversal,breakout")
        strategies = get_strategies()
        assert len(strategies) == 2
        names = {s.name for s in strategies}
        assert names == {"reversal", "breakout"}

    def test_get_strategies_handles_unknown_name(self, monkeypatch):
        monkeypatch.setenv("STRATEGIES", "reversal,nonexistent")
        strategies = get_strategies()
        assert len(strategies) == 1  # only the valid one
        assert strategies[0].name == "reversal"

    def test_get_strategies_handles_empty_env(self, monkeypatch):
        monkeypatch.setenv("STRATEGIES", "")
        strategies = get_strategies()
        assert len(strategies) == 3  # falls back to all


# ══════════════════════════════════════════════
# Base strategy RR calculator
# ══════════════════════════════════════════════
class TestBaseStrategyRR:
    def test_reversal_rr_default_ratio(self):
        s = ReversalStrategy()
        rr = s.calculate_rr(100, 100)
        # SL = 100 * 0.985 = 98.5, risk = 1.5, TP = 100 + 2*1.5 = 103
        assert abs(rr["sl"] - 98.5) < 0.01
        assert abs(rr["tp"] - 103) < 0.01

    def test_breakout_rr_with_1_pct_sl(self):
        s = BreakoutStrategy()
        # stop_loss_pct = 1.0 for breakout
        assert s.stop_loss_pct == 1.0
        rr = s.calculate_rr(100, 100)
        # SL = 100 * 0.99 = 99, risk = 1, TP = 100 + 2*1 = 102
        assert abs(rr["sl"] - 99) < 0.01
        assert abs(rr["tp"] - 102) < 0.01


# ══════════════════════════════════════════════
# Reversal Strategy
# ══════════════════════════════════════════════
class TestReversalStrategy:
    def test_pass_when_all_filters_align(self, monkeypatch, sample_5m_pinbar_df):
        s = ReversalStrategy()
        monkeypatch.setattr("radar.check_4h_support_volume", lambda sym: {
            "pass": True, "support": 48000.0, "reason": "Support bounce",
        })
        monkeypatch.setattr("radar.check_1h_stochastic", lambda sym: {
            "pass": True, "k": 15.0, "d": 18.0, "reason": "Oversold",
        })
        monkeypatch.setattr("radar.check_5m_pinbar", lambda sym: {
            "pass": True, "close": 50000.0, "df": sample_5m_pinbar_df, "reason": "Pinbar",
        })
        result = s.check_signal("BTCUSDT")

        assert result.passed
        assert result.strategy_name == "reversal"
        assert result.entry == 50000.0
        assert result.stop_loss is not None
        assert result.take_profit is not None
        assert result.take_profit > result.entry > result.stop_loss

    def test_fail_when_pinbar_missing(self, monkeypatch):
        s = ReversalStrategy()
        monkeypatch.setattr("radar.check_4h_support_volume", lambda sym: {"pass": True, "support": 48000.0})
        monkeypatch.setattr("radar.check_1h_stochastic", lambda sym: {"pass": True, "k": 15.0})
        monkeypatch.setattr("radar.check_5m_pinbar", lambda sym: {"pass": False, "reason": "No pinbar"})
        result = s.check_signal("BTCUSDT")
        assert not result.passed

    def test_fail_when_4h_filter_fails(self, monkeypatch):
        s = ReversalStrategy()
        monkeypatch.setattr("radar.check_4h_support_volume", lambda sym: {"pass": False, "reason": "Below support"})
        result = s.check_signal("BTCUSDT")
        assert not result.passed


# ══════════════════════════════════════════════
# Breakout Strategy
# ══════════════════════════════════════════════
class TestBreakoutStrategy:
    def test_4h_trend_pass_when_price_above_rising_ema(self):
        s = BreakoutStrategy()
        # Strong uptrend: 60 candles of steady increase
        base_time = pd.Timestamp("2026-06-01 00:00", tz="UTC")
        times = pd.date_range(base_time, periods=60, freq="4h")
        closes = [50000 + i * 200 for i in range(60)]  # 50000 → 61800
        df = pd.DataFrame({
            "open_time": times, "open": closes, "high": [c + 100 for c in closes],
            "low": [c - 100 for c in closes], "close": closes, "volume": [1000] * 60,
            "close_time": times + pd.Timedelta("4h"),
            "quote_vol": [1000]*60, "trades": [1000]*60,
            "taker_buy_base": [1000]*60, "taker_buy_quote": [1000]*60, "ignore": [None]*60,
        })
        result = s._check_4h_trend(df)
        assert result["pass"]
        assert result["price_above_ema"]
        assert result["ema_rising"]

    def test_4h_trend_fail_when_price_below_ema(self):
        s = BreakoutStrategy()
        # Strong downtrend
        base_time = pd.Timestamp("2026-06-01 00:00", tz="UTC")
        times = pd.date_range(base_time, periods=60, freq="4h")
        closes = [50000 - i * 200 for i in range(60)]
        df = pd.DataFrame({
            "open_time": times, "open": closes, "high": [c + 100 for c in closes],
            "low": [c - 100 for c in closes], "close": closes, "volume": [1000] * 60,
            "close_time": times + pd.Timedelta("4h"),
            "quote_vol": [1000]*60, "trades": [1000]*60,
            "taker_buy_base": [1000]*60, "taker_buy_quote": [1000]*60, "ignore": [None]*60,
        })
        result = s._check_4h_trend(df)
        assert not result["pass"]

    def test_1h_consolidation_break_pass_when_close_above_prev_high(self):
        s = BreakoutStrategy()
        base_time = pd.Timestamp("2026-06-01 00:00", tz="UTC")
        times = pd.date_range(base_time, periods=25, freq="1h")
        # 24 candles range bound (high max 50500), last candle breaks 51000
        highs = [50500] * 24 + [51500]
        closes = [50400] * 24 + [51100]  # last close > prev resistance
        df = pd.DataFrame({
            "open_time": times, "open": closes, "high": highs,
            "low": [c - 50 for c in closes], "close": closes, "volume": [1000]*25,
            "close_time": times + pd.Timedelta("1h"),
            "quote_vol": [1000]*25, "trades": [1000]*25,
            "taker_buy_base": [1000]*25, "taker_buy_quote": [1000]*25, "ignore": [None]*25,
        })
        result = s._check_1h_consolidation_break(df)
        assert result["pass"]
        assert result["resistance"] == 50500  # max of first 24 (excluding current)

    def test_5m_volume_breakout_pass_when_vol_spike_and_close_above_prev_high(self):
        s = BreakoutStrategy()
        base_time = pd.Timestamp("2026-06-01 00:00", tz="UTC")
        times = pd.date_range(base_time, periods=25, freq="5min")
        # 24 candles normal, 25th breaks prev high with vol spike
        closes = [50000] * 24 + [50150]  # last close > prev candle high (50100)
        opens = [49990] * 24 + [50050]
        highs = [50100] * 24 + [50200]
        lows = [49980] * 24 + [50040]
        vols = [1000] * 24 + [2000]  # 2x avg
        df = pd.DataFrame({
            "open_time": times, "open": opens, "high": highs, "low": lows,
            "close": closes, "volume": vols,
            "close_time": times + pd.Timedelta("5min"),
            "quote_vol": vols, "trades": vols,
            "taker_buy_base": vols, "taker_buy_quote": vols, "ignore": [None]*25,
        })
        result = s._check_5m_volume_breakout(df)
        assert result["pass"]
        assert result["vol_ratio"] >= 1.5


# ══════════════════════════════════════════════
# Trend-Follow Strategy
# ══════════════════════════════════════════════
class TestTrendFollowStrategy:
    def test_4h_trend_pass_when_strong_uptrend(self):
        s = TrendFollowStrategy()
        base_time = pd.Timestamp("2026-01-01 00:00", tz="UTC")
        times = pd.date_range(base_time, periods=220, freq="4h")
        closes = [50000 + i * 50 for i in range(220)]  # long uptrend
        df = pd.DataFrame({
            "open_time": times, "open": closes, "high": [c + 50 for c in closes],
            "low": [c - 50 for c in closes], "close": closes, "volume": [1000]*220,
            "close_time": times + pd.Timedelta("4h"),
            "quote_vol": [1000]*220, "trades": [1000]*220,
            "taker_buy_base": [1000]*220, "taker_buy_quote": [1000]*220, "ignore": [None]*220,
        })
        result = s._check_4h_trend(df)
        assert result["pass"]

    def test_4h_trend_fail_when_strong_downtrend(self):
        s = TrendFollowStrategy()
        base_time = pd.Timestamp("2026-01-01 00:00", tz="UTC")
        times = pd.date_range(base_time, periods=220, freq="4h")
        closes = [50000 - i * 50 for i in range(220)]  # long downtrend
        df = pd.DataFrame({
            "open_time": times, "open": closes, "high": [c + 50 for c in closes],
            "low": [c - 50 for c in closes], "close": closes, "volume": [1000]*220,
            "close_time": times + pd.Timedelta("4h"),
            "quote_vol": [1000]*220, "trades": [1000]*220,
            "taker_buy_base": [1000]*220, "taker_buy_quote": [1000]*220, "ignore": [None]*220,
        })
        result = s._check_4h_trend(df)
        assert not result["pass"]


# ══════════════════════════════════════════════
# SignalResult dataclass
# ══════════════════════════════════════════════
class TestSignalResult:
    def test_default_construction(self):
        s = SignalResult(strategy_name="test", passed=False)
        assert s.strategy_name == "test"
        assert not s.passed
        assert s.entry is None
        assert s.stop_loss is None
        assert s.take_profit is None
        assert s.direction == "long"
        assert s.details == {}
        assert s.reason == ""

    def test_passed_signal_with_all_fields(self):
        s = SignalResult(
            strategy_name="reversal", passed=True,
            entry=50000, stop_loss=48000, take_profit=54000,
            support=48500, details={"rr": {"sl": 48000}},
        )
        assert s.passed
        assert s.entry == 50000
        assert s.take_profit > s.entry > s.stop_loss
