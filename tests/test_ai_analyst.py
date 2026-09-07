"""
Unit tests for ai_analyst module.
"""
import pandas as pd
import ai_analyst


def _mock_klines(n=60, base_price=100.0):
    rows = []
    for i in range(n):
        rows.append({
            "open_time": pd.Timestamp("2026-01-01") + pd.Timedelta(hours=i),
            "open": base_price + i,
            "high": base_price + i + 2,
            "low": base_price + i - 1,
            "close": base_price + i + 1,
            "volume": 1000.0 + (i * 10),
            "close_time": pd.Timestamp("2026-01-01") + pd.Timedelta(hours=i, minutes=59),
        })
    return pd.DataFrame(rows)


def test_calculate_technical_summary(monkeypatch):
    monkeypatch.setattr(ai_analyst.radar, "fetch_klines", lambda sym, interval, limit=100: _mock_klines(limit))
    summary = ai_analyst.calculate_technical_summary("BTC")
    assert summary["success"] is True
    assert summary["coin"] == "BTC"
    assert "stoch_1h" in summary
    assert "k" in summary["stoch_1h"]
    assert "d" in summary["stoch_1h"]
    assert "status" in summary["stoch_1h"]
    assert "trend_4h" in summary


def test_generate_fast_ai_summary():
    mock_data = {
        "success": True,
        "coin": "SOL",
        "stoch_1h": {"k": 14.5, "d": 16.0, "status": "OVERSOLD", "bullish_cross": True},
        "trend_4h": "BULLISH (Di atas EMA 50)",
        "vol_ratio_5m": 2.2,
    }
    summary = ai_analyst.generate_fast_ai_summary("SOL", mock_data, strategy_name="reversal")
    assert isinstance(summary, str)
    assert "Stochastic (5,3,3)" in summary
    assert "Golden Cross" in summary
    assert "2.2x" in summary


def test_run_deep_ai_analysis_fallback(monkeypatch):
    monkeypatch.setattr(ai_analyst.radar, "fetch_klines", lambda sym, interval, limit=100: _mock_klines(limit))
    # Simulasi agy tidak ditemukan / error
    monkeypatch.setattr(ai_analyst, "AGY_PATH", "/nonexistent/path/to/agy")
    report = ai_analyst.run_deep_ai_analysis("ETH")
    assert isinstance(report, str)
    assert "ETH/USDT" in report
    assert "STOCHASTIC OSCILLATOR (5,3,3)" in report
    assert "REKOMENDASI TRADING PLAN" in report


def test_validate_signal_with_ai_approved(monkeypatch):
    mock_tech = {
        "success": True,
        "symbol": "BTCUSDT",
        "coin": "BTC",
        "price": 60000.0,
        "stoch_1h": {
            "k": 18.0,
            "d": 15.0,
            "status": "OVERSOLD",
            "bullish_cross": True,
            "bearish_cross": False,
        },
        "stoch_5m": {"k": 22.0, "d": 20.0},
        "trend_4h": "BULLISH (Di atas EMA 50)",
        "ema50_4h": 58000.0,
        "vol_ratio_5m": 2.0,
        "support": 59000.0,
        "resistance": 62000.0,
        "entry": 60000.0,
        "stop_loss": 58115.0,
        "take_profit": 63770.0,
        "rr_ratio": "1:2",
    }
    monkeypatch.setattr(ai_analyst, "calculate_technical_summary", lambda sym: mock_tech)
    val = ai_analyst.validate_signal_with_ai("BTCUSDT", "reversal")
    assert val.approved is True
    assert val.score >= 65
    assert val.verdict == "APPROVED"
    assert val.stoch_1h_k == 18.0
    assert "Golden Cross" in val.stoch_crossover


def test_validate_signal_with_ai_rejected_overbought(monkeypatch):
    mock_tech = {
        "success": True,
        "symbol": "DOGEUSDT",
        "coin": "DOGE",
        "price": 0.20,
        "stoch_1h": {
            "k": 91.0,
            "d": 88.0,
            "status": "OVERBOUGHT",
            "bullish_cross": False,
            "bearish_cross": False,
        },
        "stoch_5m": {"k": 85.0, "d": 80.0},
        "trend_4h": "BEARISH (Di bawah EMA 50)",
        "ema50_4h": 0.22,
        "vol_ratio_5m": 0.8,
        "support": 0.18,
        "resistance": 0.21,
        "entry": 0.20,
        "stop_loss": 0.177,
        "take_profit": 0.246,
        "rr_ratio": "1:2",
    }
    monkeypatch.setattr(ai_analyst, "calculate_technical_summary", lambda sym: mock_tech)
    val = ai_analyst.validate_signal_with_ai("DOGEUSDT", "breakout")
    assert val.approved is False
    assert val.score < 65 or val.stoch_1h_k > 82
    assert val.verdict == "REJECTED"
    assert "overbought" in val.reason.lower()

