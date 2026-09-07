"""
Unit tests for radar.py filter functions.
Tests hanya pakai pure functions (_check_X_df) — no network calls.
"""
import pandas as pd

import radar


# ══════════════════════════════════════════════
# Filter 1: 4H Support + Volume
# ══════════════════════════════════════════════
class TestCheck4HSupportVolume:
    def test_pass_with_support_bounce_and_volume_spike(self, sample_4h_df):
        result = radar._check_4h_support_volume_df(sample_4h_df)
        assert result["pass"]
        assert result["in_support_zone"]
        assert result["is_bouncing"]
        assert result["has_volume_spike"]
        assert result["vol_ratio"] >= 1.5
        assert "support" in result
        assert "distance" in result

    def test_fail_on_empty_df(self):
        result = radar._check_4h_support_volume_df(pd.DataFrame())
        assert not result["pass"]
        assert "fail" in result.get("reason", "").lower() or "fail" in result.get("detail", "").lower()

    def test_fail_on_none(self):
        result = radar._check_4h_support_volume_df(None)
        assert not result["pass"]

    def test_fail_when_volume_below_threshold(self, sample_4h_df):
        # Override volume terakhir jadi 1000 (sama dengan avg, no spike)
        df = sample_4h_df.copy()
        df.iloc[-1, df.columns.get_loc("volume")] = 1000
        result = radar._check_4h_support_volume_df(df)
        assert not result["pass"]
        assert not result["has_volume_spike"]

    def test_fail_when_not_bouncing(self, sample_4h_df):
        # Override candle terakhir jadi bearish (close < open)
        df = sample_4h_df.copy()
        last_idx = df.index[-1]
        df.loc[last_idx, "close"] = df.loc[last_idx, "open"] - 100
        result = radar._check_4h_support_volume_df(df)
        assert not result["pass"]
        assert not result["is_bouncing"]


# ══════════════════════════════════════════════
# Filter 2: 1H Stochastic
# ══════════════════════════════════════════════
class TestCheck1HStochastic:
    def test_oversold_when_strong_downtrend(self, sample_1h_df):
        result = radar._check_1h_stochastic_df(sample_1h_df)
        assert result["pass"]
        assert result["is_oversold"]
        assert result["k"] <= 20

    def test_fail_on_empty_df(self):
        result = radar._check_1h_stochastic_df(pd.DataFrame())
        assert not result["pass"]

    def test_returns_k_and_d_values(self, sample_1h_df):
        result = radar._check_1h_stochastic_df(sample_1h_df)
        assert "k" in result
        assert "d" in result
        assert isinstance(result["k"], float)
        assert isinstance(result["d"], float)


# ══════════════════════════════════════════════
# Filter 3: 5m Pinbar
# ══════════════════════════════════════════════
class TestCheck5MPinbar:
    def test_pass_with_bullish_pinbar(self, sample_5m_pinbar_df):
        result = radar._check_5m_pinbar_df(sample_5m_pinbar_df)
        assert result["pass"]
        assert result["ratio"] >= 1.5

    def test_fail_on_doji(self, sample_5m_no_pinbar_df):
        result = radar._check_5m_pinbar_df(sample_5m_no_pinbar_df)
        assert not result["pass"]

    def test_fail_on_empty_df(self):
        result = radar._check_5m_pinbar_df(pd.DataFrame())
        assert not result["pass"]

    def test_fail_on_short_lower_wick(self, sample_5m_pinbar_df):
        # Set lower wick jadi kecil (1x body atau kurang)
        df = sample_5m_pinbar_df.copy()
        last_idx = df.index[-1]
        # body = 50, lower wick = 49990 → 60 (1.2x, fail)
        df.loc[last_idx, "low"] = 49990
        result = radar._check_5m_pinbar_df(df)
        assert not result["pass"]
        assert result["ratio"] < 1.5


# ══════════════════════════════════════════════
# Risk:Reward Calculator
# ══════════════════════════════════════════════
class TestCalculateRiskReward:
    def test_basic_rr_calculation(self):
        # entry=100, support=100, SL=98.5 (-1.5%), TP=103 (+3%)
        # R:R 1:2 → risk 1.5%, reward 3%
        rr = radar.calculate_risk_reward(100, 100)
        assert rr["entry"] == 100
        assert rr["sl"] == 98.5
        assert rr["tp"] == 103
        assert abs(rr["risk_pct"] - 1.5) < 0.01
        assert abs(rr["reward_pct"] - 3.0) < 0.01

    def test_rr_with_different_support(self):
        # entry=100, support=99, SL = 99 * 0.985 = 97.515
        # risk = 100 - 97.515 = 2.485
        # TP = 100 + 2 * 2.485 = 104.97
        rr = radar.calculate_risk_reward(100, 99)
        assert abs(rr["sl"] - 97.515) < 0.01
        assert abs(rr["tp"] - 104.97) < 0.01

    def test_rr_with_btc_prices(self):
        # entry=50000, support=48000, SL = 48000 * 0.985 = 47280
        # risk = 50000 - 47280 = 2720
        # TP = 50000 + 2 * 2720 = 55440
        rr = radar.calculate_risk_reward(50000, 48000)
        assert abs(rr["sl"] - 47280) < 1
        assert abs(rr["tp"] - 55440) < 1


# ══════════════════════════════════════════════
# Memory / Anti-Spam
# ══════════════════════════════════════════════
class TestAntiSpamMemory:
    def test_is_on_cooldown_returns_false_for_new_symbol(self):
        memory = {}
        assert radar.is_on_cooldown("BTCUSDT", memory) is False

    def test_is_on_cooldown_returns_true_for_recent_alert(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).timestamp()
        memory = {"BTCUSDT": {"last_alert": now}}
        assert radar.is_on_cooldown("BTCUSDT", memory) is True

    def test_is_on_cooldown_returns_false_after_expiry(self):
        from datetime import datetime, timedelta, timezone
        # Default COOLDOWN_HOURS = 4. Set alert 5 hours ago → expired.
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=5)).timestamp()
        memory = {"BTCUSDT": {"last_alert": old_ts}}
        assert radar.is_on_cooldown("BTCUSDT", memory) is False

    def test_record_alert_creates_entry(self):
        memory = {}
        new_mem = radar.record_alert("ETHUSDT", memory)
        assert "ETHUSDT" in new_mem
        assert "last_alert" in new_mem["ETHUSDT"]
        assert "last_alert_human" in new_mem["ETHUSDT"]


# ══════════════════════════════════════════════
# Stablecoin filtering
# ══════════════════════════════════════════════
class TestStablecoinFiltering:
    def test_stablecoin_blacklist_includes_common_stables(self):
        for sym in ["USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT", "DAIUSDT"]:
            assert sym in radar.STABLECOIN_SYMBOLS, f"{sym} should be in stablecoin blacklist"

    def test_stablecoin_blacklist_includes_usds(self):
        # New stables added in v5.1
        assert "USDSUSDT" in radar.STABLECOIN_SYMBOLS
        assert "USDDUSDT" in radar.STABLECOIN_SYMBOLS

    def test_stablecoin_blacklist_includes_leveraged_tokens(self):
        assert "BTCUPUSDT" in radar.STABLECOIN_SYMBOLS
        assert "BTCDOWNUSDT" in radar.STABLECOIN_SYMBOLS


# ══════════════════════════════════════════════
# Telegram integration & formatting
# ══════════════════════════════════════════════
class TestTelegramIntegration:
    def test_build_inline_keyboard(self):
        keyboard = radar.build_inline_keyboard("BTCUSDT")
        assert "inline_keyboard" in keyboard
        rows = keyboard["inline_keyboard"]
        assert len(rows) == 2
        assert "binance.com" in rows[0][0]["url"]
        assert "tradingview.com" in rows[0][1]["url"]
        assert "coingecko.com" in rows[1][0]["url"]

    def test_build_telegram_report(self):
        from strategies.base import SignalResult
        result = SignalResult(
            strategy_name="reversal",
            passed=True,
            entry=50000.0,
            stop_loss=48000.0,
            take_profit=54000.0,
            details={
                "4h": {"status": "SUPPORT BOUNCE + VOL", "detail": "Bounce tested"},
                "1h": {"status": "OVERSOLD", "detail": "K=15.0"},
                "5m": {"status": "BULLISH PINBAR", "detail": "Tail 2.0x body"},
                "rr": {"entry": 50000.0, "sl": 48000.0, "tp": 54000.0, "risk_pct": 4.0, "reward_pct": 8.0},
            },
        )
        report = radar.build_telegram_report("BTCUSDT", result)
        assert "BTC/USDT" in report
        assert "REVERSAL" in report
        assert "50000.0" in report
        assert "48000.0" in report
        assert "54000.0" in report
        assert "#BTC" in report

    def test_build_telegram_report_with_ai_val(self):
        from strategies.base import SignalResult
        from ai_analyst import AIValidationResult
        result = SignalResult(
            strategy_name="breakout",
            passed=True,
            entry=100.0,
            stop_loss=98.5,
            take_profit=103.0,
            details={"rr": {"entry": 100.0, "sl": 98.5, "tp": 103.0, "risk_pct": 1.5, "reward_pct": 3.0}},
        )
        ai_val = AIValidationResult(
            approved=True,
            score=85,
            stoch_1h_k=22.0,
            stoch_1h_d=20.0,
            stoch_status="MOMENTUM_HEALTHY",
            stoch_crossover="Bullish Golden Cross",
            verdict="APPROVED",
            reason="Volume spike kuat dan Golden Cross Stochastic (5,3,3)",
            ai_commentary="Setup momentum ideal.",
        )
        report = radar.build_telegram_report("SOLUSDT", result, ai_val=ai_val)
        assert "APPROVED" in report
        assert "85/100" in report
        assert "Stoch (5,3,3)" in report
        assert "22.0" in report
        assert "Bullish Golden Cross" in report
        assert "Volume spike" in report

    def test_send_telegram_dry_without_token(self, monkeypatch, capsys):
        monkeypatch.setattr(radar, "TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setattr(radar, "TELEGRAM_CHAT_ID", "")
        success = radar.send_telegram("Test message")
        assert success is False
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_send_telegram_success(self, monkeypatch):
        class MockResponse:
            status_code = 200
            text = "ok"

        monkeypatch.setattr(radar._session, "post", lambda url, **kwargs: MockResponse())
        success = radar.send_telegram("Hello", token="test_token", chat_id="12345")
        assert success is True

