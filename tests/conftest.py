"""
Pytest fixtures shared across test modules.
"""
import sys
import os
from pathlib import Path

import pandas as pd
import pytest

# Pastikan root project ada di sys.path (so `import radar` works)
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_4h_df():
    """30 candles of 4H synthetic data dengan support bounce + volume spike.
    End time aligned dengan sample_1h_df & sample_5m_pinbar_df (UTC 2026-06-01 10:00).
    """
    end_time = pd.Timestamp("2026-06-01 10:00", tz="UTC")
    # Generate 30 open_times such that last close_time = end_time.
    # last_open = end_time - 4h, start = last_open - 29*4h
    interval_4h = pd.Timedelta("4h")
    last_open_4h = end_time - interval_4h
    start_4h = last_open_4h - (30 - 1) * interval_4h
    times = pd.date_range(start=start_4h, periods=30, freq="4h")

    # 10 candles ranging 49000-50000 (warm-up)
    # 19 candles decline + consolidate around 48000-49000 (forming support)
    # Last candle: low=48000 (tests support), close=49000 (bounce up), vol=1800
    closes = []
    for i in range(10):
        closes.append(50000 - i * 100)  # 50000 → 49000
    for i in range(19):
        closes.append(48500 + (i % 3) * 50)  # range 48500-48600
    closes.append(49000)  # last candle: bounce up

    opens = [c - 50 for c in closes]
    opens[-1] = 48200  # bullish: open below close (last candle)

    highs = [c + 100 for c in closes]
    highs[-1] = 49200

    lows = [c - 100 for c in closes]
    # Set support level at 47800 (clearly defined low)
    lows[15] = 47800
    # Last candle low touches support zone
    lows[-1] = 48000

    # Volume: avg 1000, candle terakhir 1800 (1.8x spike)
    vols = [1000] * 29 + [1800]

    df = pd.DataFrame({
        "open_time": times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
        "close_time": times + pd.Timedelta("4h"),
        "quote_vol": vols,
        "trades": vols,
        "taker_buy_base": vols,
        "taker_buy_quote": vols,
        "ignore": "",
    })
    return df


@pytest.fixture
def sample_1h_df():
    """50 candles of 1H data dengan stochastic oversold.
    Last close_time aligned dengan sample_5m_pinbar_df.
    Bearish candles (close near low) supaya stochastic %K turun ke <=20.
    """
    end_time = pd.Timestamp("2026-06-01 10:00", tz="UTC")
    interval_1h = pd.Timedelta("1h")
    last_open_1h = end_time - interval_1h
    start_1h = last_open_1h - (50 - 1) * interval_1h
    times = pd.date_range(start=start_1h, periods=50, freq="1h")

    # Trend turun: close[i] = 50000 - i*50, dengan close DEKAT low (bearish momentum)
    closes = [50000 - i * 50 for i in range(50)]
    # High: 100 di atas close (upper wick). Low: 10 di bawah close (close near low).
    # Ini bikin %K = (close - low_5) / (high_5 - low_5) ≈ kecil → oversold.
    highs = [c + 100 for c in closes]
    lows = [c - 10 for c in closes]
    opens = [c + 80 for c in closes]  # open above close → bearish candle
    vols = [1000] * 50

    df = pd.DataFrame({
        "open_time": times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
        "close_time": times + pd.Timedelta("1h"),
        "quote_vol": vols,
        "trades": vols,
        "taker_buy_base": vols,
        "taker_buy_quote": vols,
        "ignore": "",
    })
    return df


@pytest.fixture
def sample_5m_pinbar_df():
    """25 candles of 5m data dengan bullish pinbar di candle terakhir.
    Last close_time = 2026-06-01 10:00 (aligned dengan sample_4h_df & sample_1h_df).
    """
    end_time = pd.Timestamp("2026-06-01 10:00", tz="UTC")
    interval_5m = pd.Timedelta("5min")
    last_open_5m = end_time - interval_5m
    start_5m = last_open_5m - (25 - 1) * interval_5m
    times = pd.date_range(start=start_5m, periods=25, freq="5min")
    # close_time = open_time + 5min, last close_time = end_time

    # 24 candle normal + 1 pinbar di akhir
    closes = [50000 + (i % 5) * 10 for i in range(24)]
    closes.append(50100)  # bullish close

    opens = [c - 5 for c in closes]
    opens[-1] = 50050  # open below close → bullish

    highs = [c + 15 for c in closes]
    highs[-1] = 50110

    lows = [c - 10 for c in closes]
    # Pinbar: lower wick = (min(open, close) - low) = 50050 - 49950 = 100
    # body = close - open = 50. So wick = 2x body. PASS at 1.5x threshold.
    lows[-1] = 49950

    vols = [1000] * 25

    df = pd.DataFrame({
        "open_time": times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
        "close_time": times + pd.Timedelta("5min"),
        "quote_vol": vols,
        "trades": vols,
        "taker_buy_base": vols,
        "taker_buy_quote": vols,
        "ignore": "",
    })
    return df


@pytest.fixture
def sample_5m_no_pinbar_df():
    """25 candles of 5m data tanpa pinbar (doji)."""
    end_time = pd.Timestamp("2026-06-01 10:00", tz="UTC")
    interval_5m = pd.Timedelta("5min")
    last_open_5m = end_time - interval_5m
    start_5m = last_open_5m - (25 - 1) * interval_5m
    times = pd.date_range(start=start_5m, periods=25, freq="5min")

    closes = [50000 + (i % 5) * 10 for i in range(25)]
    opens = [c for c in closes]  # doji: open == close
    highs = [c + 10 for c in closes]
    lows = [c - 10 for c in closes]
    vols = [1000] * 25

    df = pd.DataFrame({
        "open_time": times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
        "close_time": times + pd.Timedelta("5min"),
        "quote_vol": vols,
        "trades": vols,
        "taker_buy_base": vols,
        "taker_buy_quote": vols,
        "ignore": "",
    })
    return df
