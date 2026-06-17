"""
Backtest Engine untuk Crypto Radar Multi-Strategy.

Cara kerja:
1. Fetch historical klines (4H + 1H + 5m) untuk symbol tertentu via paginated fetcher.
2. Walk-forward per 5m candle close. Pada setiap step:
   - Run semua strategi aktif via `check_signal_at(dfs, current_time)`
   - Kalau ada signal PASS, simulate entry pada close candle tsb.
   - Track forward: cek candle 5m berikutnya sampai kena SL atau TP.
3. Hitung metrics: total signals, wins, losses, win rate, profit factor,
   max drawdown, average R:R.

Usage:
    python backtest.py --symbol BTCUSDT --days 30 --strategy reversal
    python backtest.py --symbol BTCUSDT --days 30 --strategy all
    python backtest.py --symbol ETHUSDT,BTCUSDT --days 14

Output:
    - Console table dengan metrics
    - JSON report di ./backtest_reports/<symbol>_<strategy>_<timestamp>.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import pandas as pd

import radar
from strategies import STRATEGY_REGISTRY, get_strategies

# ══════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════
REPORT_DIR = "backtest_reports"

# Maksimum candle berikutnya yang di-track sebelum force-close (timeout)
MAX_HOLD_CANDLES = 288  # 288 × 5m = 24 jam

# 5m interval in minutes
M5_MINUTES = 5


# ══════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════
@dataclass
class Trade:
    symbol: str
    strategy: str
    entry_time: str
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_time: str | None = None
    exit_price: float | None = None
    outcome: str | None = None  # "win", "loss", "timeout"
    pnl_pct: float | None = None
    hold_candles: int | None = None


@dataclass
class BacktestMetrics:
    symbol: str
    strategy: str
    period_days: int
    total_signals: int
    wins: int
    losses: int
    timeouts: int
    win_rate: float
    profit_factor: float
    avg_win_pct: float
    avg_loss_pct: float
    avg_hold_candles: float
    max_drawdown_pct: float
    expectancy_pct: float  # expected PnL per trade
    trades: list = field(default_factory=list)


# ══════════════════════════════════════════════
# DATA FETCHING
# ══════════════════════════════════════════════
def fetch_historical_data(symbol: str, days: int) -> dict:
    """
    Fetch 4H, 1H, dan 5m klines untuk `days` terakhir.
    Returns dict {"4h": df, "1h": df, "5m": df}.
    """
    print(f"\n📥 Fetching {symbol} historical data ({days} days)...")

    # Hitung jumlah candle yang dibutuhkan per TF
    # Tambah buffer 300 candle untuk lookback strategi (max: trend_follow 4H needs 220)
    candles_4h = (days * 6) + 300
    candles_1h = (days * 24) + 300
    candles_5m = (days * 288) + 300

    print(f"  4H: ~{candles_4h} candles")
    df_4h = radar.fetch_klines_paginated(symbol, "4h", total_limit=candles_4h)
    print(f"  1H: ~{candles_1h} candles")
    df_1h = radar.fetch_klines_paginated(symbol, "1h", total_limit=candles_1h)
    print(f"  5m: ~{candles_5m} candles (this may take a while)")
    df_5m = radar.fetch_klines_paginated(symbol, "5m", total_limit=candles_5m)

    print(f"  ✅ Fetched: 4H={len(df_4h)}, 1H={len(df_1h)}, 5m={len(df_5m)}")
    return {"4h": df_4h, "1h": df_1h, "5m": df_5m}


# ══════════════════════════════════════════════
# TRADE SIMULATION
# ══════════════════════════════════════════════
def simulate_trade(
    df_5m: pd.DataFrame,
    entry_idx: int,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
) -> tuple[str | None, float | None, int, str | None]:
    """
    Walk forward dari entry_idx+1 sampai kena SL atau TP (atau timeout).
    Returns: (outcome, exit_price, hold_candles, exit_time_str)
    """
    end_idx = min(entry_idx + 1 + MAX_HOLD_CANDLES, len(df_5m))

    for i in range(entry_idx + 1, end_idx):
        candle = df_5m.iloc[i]
        # Cek SL dulu (asumsi worst-case: kena SL dulu kalau candle menembus kedua sisi)
        if candle["low"] <= stop_loss:
            return ("loss", stop_loss, i - entry_idx, str(candle["close_time"]))
        if candle["high"] >= take_profit:
            return ("win", take_profit, i - entry_idx, str(candle["close_time"]))

    # Timeout: close pada candle terakhir yang di-track
    last_candle = df_5m.iloc[end_idx - 1]
    return (
        "timeout",
        float(last_candle["close"]),
        end_idx - 1 - entry_idx,
        str(last_candle["close_time"]),
    )


# ══════════════════════════════════════════════
# BACKTEST RUNNER
# ══════════════════════════════════════════════
def run_backtest(
    symbol: str,
    strategies: list,
    days: int,
    step_minutes: int = M5_MINUTES,
) -> list[BacktestMetrics]:
    """
    Run backtest untuk satu symbol, multiple strategies.
    Returns: list of BacktestMetrics (one per strategy).
    """
    dfs = fetch_historical_data(symbol, days)
    df_5m = dfs["5m"]
    if df_5m.empty:
        print(f"❌ No 5m data for {symbol}")
        return []

    # Tentukan window backtest: mulai dari `days` yang lalu sampai sekarang
    now_utc = pd.Timestamp.now(tz="UTC")
    start_time = now_utc - pd.Timedelta(days=days)
    df_5m_window = df_5m.loc[df_5m["close_time"] >= start_time].copy()

    print(f"\n🔬 Backtesting {symbol} from {start_time} to {now_utc}")
    print(f"  5m candles in window: {len(df_5m_window)}")
    print(f"  Strategies: {[s.name for s in strategies]}")
    print(f"  Step: every {step_minutes} minutes (per 5m close)")

    all_metrics = []

    for strategy in strategies:
        print(f"\n  ▶️  Strategy: {strategy.name}")
        trades: list[Trade] = []
        last_signal_time = None
        # Cooldown: 4 jam antara signal yang sama (sama seperti live mode)
        COOLDOWN_MS = 4 * 3600 * 1000

        # Get index in df_5m_window
        for window_idx in range(len(df_5m_window)):
            current_time = df_5m_window["close_time"].iloc[window_idx]

            # Cooldown check
            if last_signal_time is not None:
                elapsed_ms = (current_time - last_signal_time).total_seconds() * 1000
                if elapsed_ms < COOLDOWN_MS:
                    continue

            try:
                result = strategy.check_signal_at(dfs, current_time)
            except Exception:
                # Skip step kalau strategi error
                continue

            if not result.passed:
                continue

            # Signal! Simulate trade
            # Cari entry_idx di df_5m asli (bukan window) untuk forward tracking
            entry_time = current_time
            try:
                # cari index di df_5m yang close_time-nya sama dengan entry_time
                entry_idx_in_full = df_5m.index[df_5m["close_time"] == entry_time].tolist()[0]
            except (IndexError, KeyError):
                continue

            if entry_idx_in_full + 1 >= len(df_5m):
                continue  # tidak ada candle berikutnya untuk simulate exit

            outcome, exit_price, hold, exit_time = simulate_trade(
                df_5m,
                entry_idx_in_full,
                result.entry,
                result.stop_loss,
                result.take_profit,
            )

            pnl_pct = ((exit_price - result.entry) / result.entry) * 100

            trade = Trade(
                symbol=symbol,
                strategy=strategy.name,
                entry_time=str(entry_time),
                entry_price=result.entry,
                stop_loss=result.stop_loss,
                take_profit=result.take_profit,
                exit_time=exit_time,
                exit_price=exit_price,
                outcome=outcome,
                pnl_pct=round(pnl_pct, 4),
                hold_candles=hold,
            )
            trades.append(trade)
            last_signal_time = entry_time

        # Hitung metrics
        metrics = compute_metrics(symbol, strategy.name, days, trades)
        all_metrics.append(metrics)

    return all_metrics


def compute_metrics(
    symbol: str, strategy_name: str, days: int, trades: list[Trade]
) -> BacktestMetrics:
    """Compute aggregate metrics from list of trades."""
    total = len(trades)
    wins = sum(1 for t in trades if t.outcome == "win")
    losses = sum(1 for t in trades if t.outcome == "loss")
    timeouts = sum(1 for t in trades if t.outcome == "timeout")

    win_rate = (wins / total * 100) if total > 0 else 0

    gross_profit = sum(t.pnl_pct for t in trades if t.pnl_pct and t.pnl_pct > 0)
    gross_loss = abs(sum(t.pnl_pct for t in trades if t.pnl_pct and t.pnl_pct < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0

    win_pnls = [t.pnl_pct for t in trades if t.outcome == "win" and t.pnl_pct is not None]
    loss_pnls = [t.pnl_pct for t in trades if t.outcome == "loss" and t.pnl_pct is not None]
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0

    avg_hold = (
        sum(t.hold_candles for t in trades if t.hold_candles is not None) / total
        if total > 0 else 0
    )

    # Max drawdown: peak-to-trough pada cumulative PnL curve
    if trades:
        cum_pnl = 0
        peak = 0
        max_dd = 0
        for t in trades:
            if t.pnl_pct is None:
                continue
            cum_pnl += t.pnl_pct
            if cum_pnl > peak:
                peak = cum_pnl
            dd = peak - cum_pnl
            if dd > max_dd:
                max_dd = dd
    else:
        max_dd = 0

    expectancy = (sum(t.pnl_pct for t in trades if t.pnl_pct is not None) / total) if total > 0 else 0

    return BacktestMetrics(
        symbol=symbol,
        strategy=strategy_name,
        period_days=days,
        total_signals=total,
        wins=wins,
        losses=losses,
        timeouts=timeouts,
        win_rate=round(win_rate, 2),
        profit_factor=round(profit_factor, 4) if profit_factor != float("inf") else float("inf"),
        avg_win_pct=round(avg_win, 4),
        avg_loss_pct=round(avg_loss, 4),
        avg_hold_candles=round(avg_hold, 2),
        max_drawdown_pct=round(max_dd, 4),
        expectancy_pct=round(expectancy, 4),
        trades=[asdict(t) for t in trades],
    )


# ══════════════════════════════════════════════
# REPORTING
# ══════════════════════════════════════════════
def print_metrics_table(metrics_list: list[BacktestMetrics]):
    """Print metrics as a nicely formatted table."""
    if not metrics_list:
        print("No metrics to display.")
        return

    print("\n" + "=" * 110)
    print(f"  📊 BACKTEST RESULTS — {metrics_list[0].symbol} — {metrics_list[0].period_days} days")
    print("=" * 110)
    print(f"  {'Strategy':<14} {'Signals':>8} {'Win':>5} {'Loss':>5} {'TO':>5} {'WinRate':>8} "
          f"{'PF':>8} {'AvgWin':>8} {'AvgLoss':>8} {'MaxDD':>8} {'Expect':>8}")
    print("-" * 110)

    for m in metrics_list:
        pf_str = "∞" if m.profit_factor == float("inf") else f"{m.profit_factor:.2f}"
        print(
            f"  {m.strategy:<14} {m.total_signals:>8} {m.wins:>5} {m.losses:>5} {m.timeouts:>5} "
            f"{m.win_rate:>7.1f}% {pf_str:>8} {m.avg_win_pct:>7.2f}% {m.avg_loss_pct:>7.2f}% "
            f"{m.max_drawdown_pct:>7.2f}% {m.expectancy_pct:>7.2f}%"
        )

    print("=" * 110)
    print("  Legend: PF=Profit Factor | TO=Timeout | MaxDD=Max Drawdown | Expect=Expectancy/trade")
    print()


def save_report(metrics_list: list[BacktestMetrics], output_dir: str = REPORT_DIR):
    """Save metrics to JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    symbol = metrics_list[0].symbol if metrics_list else "unknown"
    path = os.path.join(output_dir, f"{symbol}_{timestamp}.json")

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "metrics": [asdict(m) for m in metrics_list],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"💾 Report saved to: {path}")
    return path


# ══════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════
def parse_args():
    p = argparse.ArgumentParser(description="Crypto Radar Backtest Engine")
    p.add_argument(
        "--symbol", required=True,
        help="Symbol atau comma-separated list (e.g. BTCUSDT or BTCUSDT,ETHUSDT)"
    )
    p.add_argument("--days", type=int, default=30, help="Backtest period in days (default 30)")
    p.add_argument(
        "--strategy", default="all",
        help=f"Strategy name or 'all'. Available: {','.join(STRATEGY_REGISTRY.keys())}"
    )
    p.add_argument("--no-save", action="store_true", help="Skip saving JSON report")
    return p.parse_args()


def main():
    args = parse_args()
    symbols = [s.strip().upper() for s in args.symbol.split(",")]

    # Resolve strategies
    if args.strategy.lower() == "all":
        strategies = get_strategies()  # all registered
    else:
        strategies = get_strategies([s.strip() for s in args.strategy.split(",")])

    if not strategies:
        print(f"❌ No valid strategies selected. Available: {list(STRATEGY_REGISTRY.keys())}")
        sys.exit(1)

    all_metrics = []
    for symbol in symbols:
        metrics_list = run_backtest(symbol, strategies, args.days)
        all_metrics.extend(metrics_list)
        print_metrics_table(metrics_list)

    if all_metrics and not args.no_save:
        # Save per-symbol reports
        for symbol in symbols:
            sym_metrics = [m for m in all_metrics if m.symbol == symbol]
            if sym_metrics:
                save_report(sym_metrics)

    print(f"\n✅ Backtest complete. {len(all_metrics)} strategy-symbol combinations evaluated.")


if __name__ == "__main__":
    main()
