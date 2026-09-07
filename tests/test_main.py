"""
Unit tests for main.py Telegram bot handlers and utilities.
"""
import main


class TestMainBotHandlers:
    def test_get_uptime_str(self):
        uptime = main.get_uptime_str()
        assert isinstance(uptime, str)
        assert len(uptime) > 0

    def test_handle_ping(self, monkeypatch):
        sent = []
        monkeypatch.setattr(main.radar, "send_telegram", lambda msg, chat_id=None: sent.append((msg, chat_id)))
        main.handle_ping("12345")
        assert len(sent) == 1
        assert "Pong" in sent[0][0]
        assert sent[0][1] == "12345"

    def test_handle_start(self, monkeypatch):
        sent = []
        monkeypatch.setattr(main.radar, "send_telegram", lambda msg, chat_id=None: sent.append((msg, chat_id)))
        main.handle_start("12345")
        assert len(sent) == 1
        assert "Crypto Radar" in sent[0][0]
        assert "/scan" in sent[0][0]

    def test_handle_help(self, monkeypatch):
        sent = []
        monkeypatch.setattr(main.radar, "send_telegram", lambda msg, chat_id=None: sent.append((msg, chat_id)))
        main.handle_help("12345")
        assert len(sent) == 1
        assert "PANDUAN" in sent[0][0]

    def test_handle_strategies(self, monkeypatch):
        sent = []
        monkeypatch.setattr(main.radar, "send_telegram", lambda msg, chat_id=None: sent.append((msg, chat_id)))
        main.handle_strategies("12345")
        assert len(sent) == 1
        assert "Reversal" in sent[0][0]
        assert "Breakout" in sent[0][0]
        assert "Trend Follow" in sent[0][0]

    def test_handle_status(self, monkeypatch):
        sent = []
        monkeypatch.setattr(main.radar, "send_telegram", lambda msg, chat_id=None: sent.append((msg, chat_id)))
        monkeypatch.setattr(main.radar, "load_memory", lambda: {"BTCUSDT": {"last_alert": 0}})
        main.handle_status("12345")
        assert len(sent) == 1
        assert "ONLINE" in sent[0][0]
        assert "Uptime" in sent[0][0]

    def test_handle_top_success(self, monkeypatch):
        sent = []
        monkeypatch.setattr(main.radar, "send_telegram", lambda msg, chat_id=None: sent.append((msg, chat_id)))
        monkeypatch.setattr(main.radar, "get_top_volume_coins", lambda limit=10: ["BTCUSDT", "ETHUSDT"])
        main.handle_top("12345")
        assert len(sent) >= 2  # loading message + result
        result_msg = sent[-1][0]
        assert "BTC" in result_msg
        assert "ETH" in result_msg

    def test_handle_top_failure(self, monkeypatch):
        sent = []
        monkeypatch.setattr(main.radar, "send_telegram", lambda msg, chat_id=None: sent.append((msg, chat_id)))
        monkeypatch.setattr(main.radar, "get_top_volume_coins", lambda limit=10: [])
        main.handle_top("12345")
        assert len(sent) >= 2
        assert "Gagal" in sent[-1][0]

    def test_handle_ai(self, monkeypatch):
        sent = []
        monkeypatch.setattr(main.radar, "send_telegram", lambda msg, chat_id=None: sent.append((msg, chat_id)))
        main.handle_ai("12345", "BTC")
        assert len(sent) >= 1
        assert "AI sedang menganalisis" in sent[0][0]
