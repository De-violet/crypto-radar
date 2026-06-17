# 🎯 Crypto Radar v7.0 — Multi-Strategy Sniper (Discord + Web Edition)

> *Multi-strategy crypto signal bot with Discord alerts + Web dashboard.*

Crypto Radar watches the crypto market 24/7 using a 3-filter multi-timeframe
strategy pipeline. When high-conviction entries appear, it broadcasts signals
to your Discord server and (in Phase 1) a live web dashboard.

**v7.0 is a major pivot**: Telegram mode has been removed. The project now
targets **Discord + Web** as the primary surfaces. The legacy Telegram code is
preserved on the `legacy-telegram` branch (tag `v6.0-telegram-final`).

---

## 🆕 What's New in v7.0

- 🔥 **Telegram mode removed** — see `legacy-telegram` branch for backup
- 🐍 **FastAPI backend** (`apps/api/main.py`) — REST + WebSocket API for the web frontend
- 🎨 **Next.js 16 web frontend** (`web` branch) — violet luxury theme, deployed to Vercel
- 🤖 **Discord bot embedded in FastAPI** — 1 container, 1 process, runs on Fly.io free tier
- 🚀 **Auto-deploy from GitHub**:
  - Push to `main` → Fly.io (Python backend + Discord bot)
  - Push to `web` → Vercel (Next.js frontend)
- 🔌 **Pluggable signal emitter** — `radar.register_signal_sink(fn)` lets Discord & Web register their own sinks
- 🏗 **Modular architecture** — `main.py` exposes `bot` singleton importable by FastAPI

---

## 🏗 Architecture (v7.0)

```
                  GitHub repo (De-violet/crypto-radar)
                  ├── branch: main   → Python backend + Discord bot
                  └── branch: web    → Next.js frontend
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
         Fly.io (free 256MB)      Vercel (free)
         • FastAPI /health        • Next.js 16 dashboard
         • FastAPI /api/v1/*      • Violet theme
         • Discord.py bot         • Supabase Auth (Phase 1)
         • 1 container            • Auto-deploy from `web`
         • Auto-deploy from `main`
              │                       │
              └─────── HTTPS ─────────┘
                     ↕
                Supabase (free)
                • Postgres 500MB
                • Auth (Google/GitHub OAuth)
                • Storage (for chart images)
```

---

## 📂 Project Structure (v7.0)

```
crypto-radar/  (branch: main)
├── apps/
│   └── api/
│       ├── __init__.py
│       ├── main.py              # FastAPI app + lifespan hook (starts Discord bot)
│       └── routers/
│           └── __init__.py
├── cogs/                       # Discord.py cogs (existing)
│   ├── background_tasks.py
│   └── crypto_commands.py
├── strategies/                 # Trading strategies (existing)
│   ├── base.py
│   ├── reversal.py
│   ├── breakout.py
│   └── trend_follow.py
├── tests/                      # pytest tests (existing)
├── .github/workflows/
│   ├── tests.yml               # Lint + tests + backtest validation
│   └── fly-deploy.yml          # Auto-deploy main → Fly.io
├── .env.example                # Updated: no Telegram, added Supabase + API
├── Dockerfile                  # Fly.io: 256MB, 1 process, FastAPI + Discord
├── fly.toml                    # Fly.io config
├── backtest.py                 # Backtest engine (existing)
├── keep_alive.py               # Legacy Flask keep-alive (still used by main.py standalone)
├── main.py                     # Discord bot entry — exposes `bot` singleton
├── radar.py                    # Scanner engine + signal emitter (refactored v7.0)
├── pyproject.toml              # ruff + pytest + mypy config
├── requirements.txt            # + fastapi, uvicorn, supabase
└── README.md                   # This file
```

Branch `web` contains the Next.js frontend (separate deploy pipeline).

---

## 🚀 Quick Start

### Local development

```bash
# 1. Clone
git clone https://github.com/De-violet/crypto-radar.git
cd crypto-radar

# 2. Virtualenv
python -m venv venv && source venv/bin/activate

# 3. Install deps
pip install -r requirements-dev.txt

# 4. Configure
cp .env.example .env
# Edit .env — set at minimum DISCORD_TOKEN + DISCORD_NEWS_CHANNEL_ID + DISCORD_ALERT_CHANNEL_ID

# 5. Run FastAPI (Discord bot akan start otomatis di background)
python -m uvicorn apps.api.main:app --reload --port 8000

# Verify
curl http://localhost:8000/health
# {"status":"ok","version":"7.0.0",...}
```

### Run Discord bot standalone (without FastAPI)

```bash
python main.py
# Starts Flask keep_alive + Discord bot (legacy mode from v6.0)
```

### Run backtest

```bash
python backtest.py --symbol BTCUSDT --days 30 --strategy all
```

---

## 🌐 Deployment

See **[DEPLOY.md](./DEPLOY.md)** for the complete step-by-step guide.

**TL;DR:**

| Component | Branch | Hosting | Auto-deploy trigger |
|---|---|---|---|
| Python backend + Discord bot | `main` | Fly.io (free 256MB) | Push to `main` |
| Next.js web frontend | `web` | Vercel (free) | Push to `web` |
| Database + Auth | – | Supabase (free 500MB) | – |
| Domain DNS | – | Cloudflare (free) | – |

---

## 🎯 Multi-Strategy System

Crypto Radar v7.0 supports multiple trading strategies that run in parallel.
Each strategy is a Python class subclassing `BaseStrategy` and registered in
`strategies/__init__.py`.

### Built-in Strategies

| Strategy | Direction | Description | Lookback (4H/1H/5m) |
|---|---|---|---|
| `reversal` | Long | **Bottom fishing**: 4H support bounce + volume spike → 1H Stochastic oversold → 5m bullish pinbar | 30 / 50 / 25 |
| `breakout` | Long | **Momentum continuation**: 4H EMA50 uptrend → 1H 20-candle resistance break → 5m volume breakout | 60 / 50 / 30 |
| `trend_follow` | Long | **Pullback in trend**: 4H price > EMA200 → 1H MACD bullish → 5m bullish engulfing at EMA20 | 220 / 100 / 50 |

### Selecting Strategies (env var)

```bash
# Default: ALL strategies active
STRATEGIES=

# Run only reversal
STRATEGIES=reversal

# Run breakout + trend_follow
STRATEGIES=breakout,trend_follow
```

### Adding a Custom Strategy

1. Create `strategies/my_strategy.py` subclassing `BaseStrategy`
2. Register in `strategies/__init__.py`: `STRATEGY_REGISTRY["my_strategy"] = MyStrategy`
3. Add tests in `tests/test_strategies.py`
4. Activate via `STRATEGIES=my_strategy` env var

See the [Strategy Development Guide](./STRATEGIES.md) for details.

---

## 🔌 Signal Emitter (new in v7.0)

The scanner engine now emits signals via a pluggable sink system. Discord bot
and Web API each register their own sink:

```python
import radar

def my_custom_sink(symbol, signal_result, report, chart_buf=None):
    """Custom sink — write to file, send to Slack, push to webhook, etc."""
    print(f"Signal for {symbol}: {report}")

radar.register_signal_sink(my_custom_sink)
```

Default behavior (no sinks registered): signals are logged only.

---

## 🧪 Testing & Validation

```bash
# Run all tests
pytest tests/ -v

# Lint
ruff check .

# Coverage
pytest tests/ --cov=. --cov-report=term-missing
```

CI pipeline (`.github/workflows/tests.yml`) runs on every push to `main` and `web`:
- ruff lint (blocking)
- pytest (blocking)
- coverage report (artifact, 7-day retention)
- backtest validation on BTC + ETH (main only)

---

## ⚠️ Disclaimer

This bot is an **assistant, not an oracle**. It can help filter noise and
highlight interesting moments — but the final call is always yours.

> **⚖️ Not Financial Advice.** Any profits or losses resulting from the use
> of this bot are entirely your own responsibility. Always DYOR.

---

## 📝 License

MIT — see [LICENSE](./LICENSE).
