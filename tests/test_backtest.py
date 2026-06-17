"""
Unit tests untuk backtest.py — verify trade simulation & metrics math.
Pakai synthetic trades, no network.
"""
import pandas as pd
import pytest

from backtest import (
    Trade,
    compute_metrics,
    simulate_trade,
)


# ══════════════════════════════════════════════
# Trade simulation
# ══════════════════════════════════════════════
class TestSimulateTrade:
    def _make_df(self, prices):
        """Build 5m df with given close prices (lows = close - 10, highs = close + 10)."""
        base = pd.Timestamp("2026-06-01 00:00", tz="UTC")
        times = pd.date_range(base, periods=len(prices), freq="5min")
        return pd.DataFrame({
            "open_time": times,
            "open": prices,
            "high": [p + 10 for p in prices],
            "low": [p - 10 for p in prices],
            "close": prices,
            "volume": [1000] * len(prices),
            "close_time": times + pd.Timedelta("5min"),
            "quote_vol": [1000]*len(prices), "trades": [1000]*len(prices),
            "taker_buy_base": [1000]*len(prices),
            "taker_buy_quote": [1000]*len(prices),
            "ignore": [None]*len(prices),
        })

    def test_win_when_tp_hit_first(self):
        # Entry=100, SL=95, TP=110. Next candle goes to 115 (high=125, low=105).
        # High (125) >= TP (110) → win.
        prices = [100, 115, 120, 125]
        df = self._make_df(prices)
        outcome, exit_price, hold, _ = simulate_trade(df, 0, 100, 95, 110)
        assert outcome == "win"
        assert exit_price == 110
        assert hold == 1

    def test_loss_when_sl_hit_first(self):
        # Entry=100, SL=95, TP=110. Next candle drops to 90 (high=100, low=80).
        # Low (80) <= SL (95) → loss.
        prices = [100, 90, 85, 80]
        df = self._make_df(prices)
        # Tweak lows supaya jelas kena SL
        df.loc[1, "low"] = 90
        outcome, exit_price, hold, _ = simulate_trade(df, 0, 100, 95, 110)
        assert outcome == "loss"
        assert exit_price == 95
        assert hold == 1

    def test_sl_checked_before_tp_when_both_hit_same_candle(self):
        # Conservative assumption: if both SL and TP hit in same candle, SL wins.
        prices = [100, 100]  # placeholder, will be tweaked
        df = self._make_df(prices)
        # Make candle 1 have BOTH low<=SL and high>=TP
        df.loc[1, "low"] = 90   # <= SL (95)
        df.loc[1, "high"] = 120  # >= TP (110)
        outcome, exit_price, hold, _ = simulate_trade(df, 0, 100, 95, 110)
        assert outcome == "loss"  # SL takes priority
        assert exit_price == 95

    def test_timeout_when_neither_hit_within_max_hold(self):
        # Entry=100, SL=80, TP=120. Prices stay flat at 100.
        prices = [100] * 10  # short, but simulate_trade uses MAX_HOLD_CANDLES
        df = self._make_df(prices)
        # Use entry_idx=0, but df only has 10 rows so end_idx will be min
        outcome, exit_price, hold, _ = simulate_trade(df, 0, 100, 80, 120)
        assert outcome == "timeout"
        assert exit_price == 100  # close of last tracked candle


# ══════════════════════════════════════════════
# Metrics computation
# ══════════════════════════════════════════════
class TestComputeMetrics:
    def _make_trade(self, outcome, entry, exit_price):
        pnl_pct = ((exit_price - entry) / entry) * 100
        return Trade(
            symbol="BTCUSDT", strategy="reversal",
            entry_time="2026-06-01", entry_price=entry,
            stop_loss=entry * 0.985, take_profit=entry * 1.03,
            exit_time="2026-06-02", exit_price=exit_price,
            outcome=outcome, pnl_pct=round(pnl_pct, 4), hold_candles=10,
        )

    def test_empty_trades_returns_zero_metrics(self):
        m = compute_metrics("BTCUSDT", "reversal", 30, [])
        assert m.total_signals == 0
        assert m.wins == 0
        assert m.losses == 0
        assert m.win_rate == 0
        assert m.profit_factor == 0
        assert m.expectancy_pct == 0

    def test_all_wins_metrics(self):
        trades = [
            self._make_trade("win", 100, 103),
            self._make_trade("win", 100, 103),
            self._make_trade("win", 100, 103),
        ]
        m = compute_metrics("BTCUSDT", "reversal", 30, trades)
        assert m.total_signals == 3
        assert m.wins == 3
        assert m.losses == 0
        assert m.win_rate == 100.0
        assert m.profit_factor == float("inf")  # no losses → infinity
        assert m.expectancy_pct > 0

    def test_all_losses_metrics(self):
        trades = [
            self._make_trade("loss", 100, 98.5),
            self._make_trade("loss", 100, 98.5),
        ]
        m = compute_metrics("BTCUSDT", "reversal", 30, trades)
        assert m.total_signals == 2
        assert m.wins == 0
        assert m.losses == 2
        assert m.win_rate == 0
        assert m.profit_factor == 0  # no wins
        assert m.expectancy_pct < 0

    def test_mixed_trades_metrics(self):
        # 2 wins at +3% each, 1 loss at -1.5%
        # gross_profit = 6, gross_loss = 1.5, PF = 4.0
        trades = [
            self._make_trade("win", 100, 103),
            self._make_trade("win", 100, 103),
            self._make_trade("loss", 100, 98.5),
        ]
        m = compute_metrics("BTCUSDT", "reversal", 30, trades)
        assert m.total_signals == 3
        assert m.wins == 2
        assert m.losses == 1
        assert m.win_rate == pytest.approx(66.67, rel=0.01)
        assert m.profit_factor == pytest.approx(4.0, rel=0.01)
        assert m.avg_win_pct == pytest.approx(3.0, rel=0.01)
        assert m.avg_loss_pct == pytest.approx(-1.5, rel=0.01)

    def test_max_drawdown_calculation(self):
        # Trades: +5%, -10%, +5% → cum PnL: 5, -5, 0
        # Peak=5, trough=-5 → DD = 10
        trades = [
            Trade("BTCUSDT", "test", "t1", 100, 98, 105, exit_price=105, outcome="win", pnl_pct=5.0, hold_candles=5),
            Trade("BTCUSDT", "test", "t2", 100, 98, 105, exit_price=90, outcome="loss", pnl_pct=-10.0, hold_candles=5),
            Trade("BTCUSDT", "test", "t3", 100, 98, 105, exit_price=105, outcome="win", pnl_pct=5.0, hold_candles=5),
        ]
        m = compute_metrics("BTCUSDT", "test", 30, trades)
        assert m.max_drawdown_pct == pytest.approx(10.0, rel=0.01)

    def test_expectancy_calculation(self):
        # 1 win at +3%, 1 loss at -1.5% → avg = (3 - 1.5) / 2 = 0.75
        trades = [
            self._make_trade("win", 100, 103),
            self._make_trade("loss", 100, 98.5),
        ]
        m = compute_metrics("BTCUSDT", "reversal", 30, trades)
        assert m.expectancy_pct == pytest.approx(0.75, rel=0.01)

    def test_metrics_to_dict_serializable(self):
        trades = [self._make_trade("win", 100, 103)]
        m = compute_metrics("BTCUSDT", "reversal", 30, trades)
        import json
        from dataclasses import asdict
        d = asdict(m)
        # Must be JSON serializable
        json_str = json.dumps(d, default=str)
        assert "total_signals" in json_str
