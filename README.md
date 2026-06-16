# 🎯 Crypto Radar — Multi-Strategy Sniper (v6.0)

> *"Tired of staring at charts at 2 AM with your eyes half-shut, terrified you'll miss the one good entry? Yeah, been there."*

Crypto Radar was born out of a very real frustration: **the crypto market never sleeps, but we're humans who need rest.** This bot isn't here to replace your trading instincts — think of it more as a tireless assistant that watches the charts while you sleep, grab coffee, or binge Netflix guilt-free.

The idea is simple: **when there's a high-quality opportunity, it whistles. When there isn't, it stays quiet.** No spam, no drama.

---

## 🆕 What's New in v6.0 (Multi-Strategy + Backtest + Validation)

- 🎯 **Multi-strategy support** — 3 strategies now built-in:
  - `reversal` (default, bottom fishing: 4H support + 1H oversold + 5m pinbar)
  - `breakout` (momentum continuation: 4H trend + 1H resistance break + 5m volume breakout)
  - `trend_follow` (pullback in trend: 4H EMA200 + 1H MACD + 5m engulfing at EMA20)
- 📊 **Backtest engine** (`backtest.py`) — replay historical data, simulate entry/SL/TP, compute win rate, profit factor, max drawdown, expectancy per trade
- 🧪 **Unit tests** (`tests/` with pytest) — 54 tests covering filter logic, strategy evaluation, backtest math, anti-spam memory, stablecoin filtering
- 🤖 **CI/CD pipeline** (`.github/workflows/tests.yml`) — auto-run pytest + ruff lint on every push/PR; auto-run backtest validation on main
- 🏗️ **Strategy registry** (`strategies/`) — add new strategies by subclassing `BaseStrategy` and registering in `strategies/__init__.py`
- 🔧 **Environment-controlled strategy selection** — `STRATEGIES=reversal,breakout` env var picks which strategies run
- 📝 **Pure vs Live filter variants** — `check_X(symbol)` (live, fetches data) vs `_check_X_df(df)` (pure, accepts DataFrame) for backtest reuse

---

## 🆕 What's New in v5.1 (Hardened Edition)

- 🌐 **Binance geo-restriction workaround** — multi-endpoint failover + `data-api.binance.vision` mirror (no more HTTP 451 on GitHub Actions US runners)
- 📊 **Volume spike threshold raised to 1.5x** (was 1.2x — too noisy, too many false positives)
- 🕯️ **Pinbar candle selection fixed** — uses `close_time` verification, no longer blindly picks `iloc[-2]`
- 💾 **Memory leak fix** — matplotlib figures now explicitly closed after each chart generation
- 🔒 **File locking** on `alerted_coins.json` (POSIX `fcntl`) — safe concurrent writes
- 🪙 **Expanded stablecoin blacklist** — USDS, USDD, USDE, USDE, PAXG, XAUT, leveraged tokens, etc.
- 📰 **News/listing anti-spam persisted** — `posted_news.json` + `posted_listings.json` survive bot restarts (no more spam after restart)
- ⏰ **Timezone-aware datetimes** everywhere (no more naive `datetime.fromtimestamp`)
- 🚦 **CoinGecko caching** — 60s TTL cache for `/search` and `/info` slash commands
- 📝 **Logging module** replaces `print()` for structured logs
- 🩺 **`/health` endpoint** on keep-alive server (uptime + last scan time)
- 🔐 **`.env` no longer committed** — proper `.gitignore`, `.env.example` template

---

## 🧠 How It Works — Reversal Sniper

This bot uses a **3-filter bottom-fishing strategy** to catch reversal entries at support.

| Step | Timeframe | What it looks for | Analogy |
|------|-----------|-------------------|---------|
| 1️⃣ | **4H** | Strong support bounce + volume spike (smart money stepping in) | Checking if there's a concrete foundation under price |
| 2️⃣ | **1H** | Stochastic (5,3,3) oversold (K ≤ 20) — momentum exhausted to downside | The bow is drawn back, ready to release |
| 3️⃣ | **5m** | Bullish Pinbar (close > open + lower wick ≥ 1.5× body) — rejection candle | Finger's on the trigger, ready to squeeze |

**A coin must pass all 3 filters sequentially.** Fail one? Instantly dropped — no mercy. This isn't a bot that fires signals every 5 minutes — it only sends the ones that are **truly worth your attention**.

The bot **dynamically scans the top N coins by 24h quote volume** (default 120, configurable via `SCAN_LIMIT`). Stablecoins and leveraged tokens are filtered out automatically.

---

## 🔫 Key Features

### 📡 Telegram Alerts + Inline Keyboard + Chart
Every signal that passes all filters gets sent straight to your Telegram with:
- **5m candlestick chart** (PNG, generated via `mplfinance`)
- **Checklist report** showing exactly which filter passed/failed
- **Inline keyboard** with shortcut buttons to Binance Chart, TradingView, and CoinGecko — one tap and you're ready to execute

### 💰 Auto Risk:Reward Calculator (1:2)
Every signal comes with:
- **Entry Price** — the suggested entry (5m pinbar close)
- **Stop Loss** — 1.5% below the 4H support level
- **Take Profit** — automatically calculated at 1:2 R:R ratio

### 🧠 Anti-Spam Memory System
- **Telegram mode**: 4-hour cooldown per coin, persisted in `alerted_coins.json` (auto-committed back to repo by GitHub Actions)
- **Discord mode**: news + listing IDs persisted in `posted_news.json` + `posted_listings.json` — no duplicate posts after restart

### ⚡ Automatic Retry + Failover
- HTTP retries (3× with exponential backoff on 429/5xx)
- **Multiple Binance endpoints** — automatically falls back to `data-api.binance.vision` when `api.binance.com` returns 451

### 🤖 Optional Discord Bot Mode
Beyond Telegram sniper, you also get a full Discord "Command Center":
- `/search <coin>` — real-time price, market cap, 24h change, rank (with 60s cache)
- `/info <coin>` — project description, website, GitHub (with 60s cache)
- **News radar** — top 3 breaking news every hour (CryptoCompare API)
- **Listing radar** — new Binance listings detected every 5 minutes
- **Sniper signal** — runs `radar.run_scanner` every 15 minutes (same logic as Telegram mode, but inside the bot)

---

## 🛠️ Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| **Python** | 3.10+ | 3.12 recommended |
| **discord.py** | 2.3+ | For Discord bot mode |
| **requests** | 2.31+ | Binance & Telegram API calls |
| **pandas** | 2.1+ | Candlestick data processing |
| **pandas-ta** | 0.3.14b1+ | Technical indicators (Stochastic, etc.) |
| **mplfinance** | 0.12.10b0+ | Chart generation |
| **flask** | 3.0+ | Keep-alive HTTP server (for Discord bot mode) |
| **python-dotenv** | 1.0+ | Load `.env` file |
| **Telegram Bot** | — | Create one via [@BotFather](https://t.me/BotFather) (for Telegram mode) |
| **Discord Bot** | — | Create at [Discord Developer Portal](https://discord.com/developers/applications) (for Discord mode) |

---

## 🚀 Two Deployment Modes — Pick What You Need

| Mode | What it does | Best for | Server needed? |
|------|--------------|----------|----------------|
| **A. Telegram Sniper** | Standalone scanner, sends alerts to Telegram | Solo traders who only want Telegram signals | ❌ **NO** — runs on GitHub Actions (free, 24/7) |
| **B. Discord Command Center** | Full Discord bot with `/search`, `/info`, news, listing, sniper | Teams / communities who want an all-in-one bot | ✅ **YES** — needs always-on process (HF Spaces free / Render / VPS) |

> 💡 You can run **both modes simultaneously** if you want both Telegram alerts AND Discord commands.

---

## 🅰️ Mode A — Telegram Sniper (No Server, GitHub Actions)

This is the **simplest path**: zero cost, zero server, runs on GitHub's free CI runners every 15 minutes.

### 1. Fork / clone the repo

```bash
git clone https://github.com/<your-username>/crypto-radar.git
cd crypto-radar
```

### 2. Create `.env` locally (for testing)

```bash
cp .env.example .env
# Edit .env and fill in your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

### 3. Test locally

```bash
pip install -r requirements.txt
python radar.py
```

You should see the scanner iterate over the top 120 coins, applying the 3-filter pipeline.

### 4. Push to GitHub + add Secrets

```bash
git add .
git commit -m "🚀 Deploy Telegram sniper"
git push origin main
```

Then on GitHub → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|-------------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Your group/channel chat ID |

(Optional) Under **Settings → Secrets and variables → Actions → Variables**, you can also tune:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SCAN_LIMIT` | `120` | Number of top coins to scan |
| `VOL_SPIKE_THRESHOLD` | `1.5` | Volume spike ratio |
| `STOCH_OVERSOLD` | `20` | Stochastic %K oversold threshold |
| `COOLDOWN_HOURS` | `4` | Anti-spam cooldown per coin |

### 5. Enable the Workflow

Go to **Actions** tab → click **"I understand my workflows, go ahead and enable them"**.

Your bot now runs **automatically every 15 minutes, 24/7, for free**. On each run:
1. Scans all monitored coins through the 3-layer filter
2. Sends a Telegram alert (with chart) if a sniper signal is found
3. Auto-commits the `alerted_coins.json` memory file back to the repo (so cooldown persists across runs)

> 💡 **Manual test**: Actions tab → select workflow → **"Run workflow"**.

---

## 🅱️ Mode B — Discord Command Center (Free hosting via Hugging Face Spaces)

Discord bots need a **persistent WebSocket connection**, which means they can't run on serverless cron like GitHub Actions. They need an always-on process. Here are your **free** options ranked by reliability:

| Platform | Free tier | Sleeps? | Setup difficulty | Recommended? |
|----------|-----------|---------|------------------|--------------|
| **Hugging Face Spaces** | Unlimited (CPU basic) | ❌ No sleep | Easy | ✅ **Best free option** |
| **Oracle Cloud Always Free** | 1-4 ARM VMs forever | ❌ No sleep | Medium | ✅ Most reliable (more setup) |
| **Render** | Free web service | 😴 Sleeps after 15 min idle | Easy | ⚠️ Use with UptimeRobot ping |
| **Replit + UptimeRobot** | Free tier | 😴 Sleeps without pings | Easy | ⚠️ Unreliable |
| **Railway.app** | $5 free credit/month | ❌ No sleep | Easy | ⚠️ Credit runs out in ~3 weeks |

### Recommended: Hugging Face Spaces (Free, No Sleep, No Credit Card)

#### Step 1 — Create a Space
1. Go to https://huggingface.co/login (sign up if needed)
2. Click your avatar → **New Space**
3. Name: `crypto-radar` (or whatever)
4. License: MIT
5. SDK: **Docker** (we need full control)
6. Visibility: **Private** (recommended — your bot tokens are stored as secrets)

#### Step 2 — Upload the code
Two options:
- **Push via Git** (recommended for ongoing development):
  ```bash
  git clone https://huggingface.co/spaces/<your-username>/crypto-radar
  cp -r /path/to/crypto-radar/* /path/to/crypto-radar/.env.example crypto-radar/
  cd crypto-radar
  git add .
  git commit -m "Initial deploy"
  git push
  ```
- **Upload files via web UI**: drag-and-drop all files (except `.env`!) into the Space file browser.

#### Step 3 — Create `Dockerfile` in the Space root

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps for matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# HF Spaces expects the app on port 7860 by default
ENV PORT=7860
EXPOSE 7860

CMD ["python", "main.py"]
```

#### Step 4 — Add Secrets
On the Space page → **Settings → Repository secrets → New secret**:

| Secret name | Value |
|-------------|-------|
| `DISCORD_TOKEN` | Your Discord bot token |
| `DISCORD_NEWS_CHANNEL_ID` | Channel ID for news broadcast |
| `DISCORD_ALERT_CHANNEL_ID` | Channel ID for listing alerts |
| `TELEGRAM_BOT_TOKEN` | (Optional, if you also want Telegram from the same bot) |
| `TELEGRAM_CHAT_ID` | (Optional) |

#### Step 5 — Start the Space
Click **Restart this Space** (or it auto-builds on file upload). Watch the logs — you should see:
```
🤖 Logged in as YourBot#1234 (ID: ...)
📡 News channel : ...
🚨 Alert channel: ...
✅ N slash commands berhasil disinkronisasi!
```

Your Discord bot is now live 24/7, free, no sleep.

> 💡 **Verify the keep-alive is working**: visit `https://<your-username>-crypto-radar.hf.space/health` — should return JSON with uptime + last scan time.

### Alternative: Oracle Cloud Always Free VM

If you want maximum reliability (and you're OK with a slightly more involved setup):

1. Sign up at https://www.oracle.com/cloud/free/
2. Create an **Always Free** ARM VM (Ampere A1, 4 OCPU / 24GB RAM — free forever)
3. SSH in, install Python 3.12 + git
4. Clone your repo, set up `systemd` service:
   ```bash
   sudo nano /etc/systemd/system/crypto-radar.service
   ```
   ```ini
   [Unit]
   Description=Crypto Radar Discord Bot
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/crypto-radar
   EnvironmentFile=/home/ubuntu/crypto-radar/.env
   ExecStart=/home/ubuntu/crypto-radar/venv/bin/python main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
5. Enable + start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable crypto-radar
   sudo systemctl start crypto-radar
   sudo systemctl status crypto-radar
   ```

---

## 📂 Project Structure

```
crypto-radar/
├── .github/
│   └── workflows/
│       ├── main.yml              # GitHub Actions: Telegram sniper every 15 min
│       └── tests.yml             # CI: pytest + lint + backtest validation
├── cogs/
│   ├── __init__.py
│   ├── crypto_commands.py        # /search, /info slash commands (Discord)
│   └── background_tasks.py       # News radar, listing radar, sniper loop (Discord)
├── strategies/
│   ├── __init__.py               # Registry: get_strategies() + STRATEGIES env var
│   ├── base.py                   # BaseStrategy ABC + SignalResult dataclass
│   ├── reversal.py               # 4H support + 1H oversold + 5m pinbar
│   ├── breakout.py               # 4H EMA50 + 1H resistance break + 5m vol breakout
│   └── trend_follow.py           # 4H EMA200 + 1H MACD + 5m engulfing at EMA20
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures (synthetic 4H/1H/5m DataFrames)
│   ├── test_radar.py             # Filter logic + R:R + anti-spam tests
│   ├── test_strategies.py        # Strategy evaluation tests
│   └── test_backtest.py          # Trade simulation + metrics tests
├── .env.example                  # Template for env vars (DO NOT commit .env)
├── .gitignore                    # Properly ignores .env, __pycache__, runtime memory
├── README.md                     # You're reading this right now
├── alerted_coins.json            # Anti-spam memory (auto-committed by GH Actions)
├── backtest.py                   # Backtest engine (walk-forward + metrics)
├── keep_alive.py                 # Flask HTTP server with /health endpoint
├── main.py                       # Discord bot entry point
├── radar.py                      # Scanner engine: filters + multi-strategy orchestrator
├── requirements.txt              # Pinned runtime dependencies
└── requirements-dev.txt          # Pinned dev dependencies (pytest, ruff)
```

---

## 🧪 Local Development

```bash
# 1. Clone
git clone https://github.com/<your-username>/crypto-radar.git
cd crypto-radar

# 2. Virtualenv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Install
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your tokens

# 5. Run
python radar.py    # Telegram sniper mode
python main.py     # Discord bot mode
```

---

## 🎯 Multi-Strategy System

Crypto Radar v6.0 supports multiple trading strategies that run in parallel. Each strategy is a Python class subclassing `BaseStrategy` and registered in `strategies/__init__.py`.

### Built-in Strategies

| Strategy | Direction | Description | Lookback (4H/1H/5m) |
|----------|-----------|-------------|---------------------|
| `reversal` | Long | **Bottom fishing**: 4H support bounce + volume spike → 1H Stochastic oversold → 5m bullish pinbar | 30 / 50 / 25 |
| `breakout` | Long | **Momentum continuation**: 4H EMA50 uptrend → 1H 20-candle resistance break → 5m volume breakout above prev high | 60 / 50 / 30 |
| `trend_follow` | Long | **Pullback in trend**: 4H price > EMA200 → 1H MACD histogram bullish → 5m bullish engulfing at EMA20 | 220 / 100 / 50 |

### Selecting Strategies (env var)

```bash
# Default: ALL strategies active
STRATEGIES=              # uses all 3

# Run only reversal (v5.1 behavior)
STRATEGIES=reversal

# Run breakout + trend_follow (skip reversal)
STRATEGIES=breakout,trend_follow
```

In GitHub Actions, set this as a **Variable** (not Secret) under Settings → Secrets and variables → Actions → Variables.

### Adding a Custom Strategy

1. Create `strategies/my_strategy.py`:

```python
from .base import BaseStrategy, SignalResult
import radar

class MyStrategy(BaseStrategy):
    name = "my_strategy"
    risk_reward_ratio = 2.0
    stop_loss_pct = 1.5

    def required_lookback(self) -> dict:
        return {"4h": 50, "1h": 50, "5m": 25}

    def check_signal(self, symbol: str) -> SignalResult:
        # Live mode: fetch fresh data
        df = radar.fetch_klines(symbol, "4h", limit=50)
        return self._evaluate(df)

    def check_signal_at(self, dfs, current_time) -> SignalResult:
        # Backtest mode: use pre-fetched data
        df = dfs["4h"].loc[dfs["4h"]["close_time"] <= current_time]
        return self._evaluate(df)

    def _evaluate(self, df) -> SignalResult:
        # Your filter logic here
        if some_condition:
            return SignalResult(
                strategy_name=self.name, passed=True,
                entry=..., stop_loss=..., take_profit=...,
                details={...}, chart_df=df.tail(25),
            )
        return SignalResult(strategy_name=self.name, passed=False, reason="...")
```

2. Register in `strategies/__init__.py`:

```python
from .my_strategy import MyStrategy
STRATEGY_REGISTRY["my_strategy"] = MyStrategy
```

3. Add tests in `tests/test_strategies.py`.

4. Activate via `STRATEGIES=my_strategy` env var.

---

## 📊 Backtest Engine

Validate strategy profitability BEFORE live trading. Replays historical klines, walks forward per 5m candle close, simulates entry/SL/TP outcomes.

### Quick Start

```bash
# Backtest BTC for 30 days with all strategies
python backtest.py --symbol BTCUSDT --days 30 --strategy all

# Backtest BTC + ETH for 14 days with reversal only
python backtest.py --symbol BTCUSDT,ETHUSDT --days 14 --strategy reversal

# Backtest BTC for 90 days with breakout (longer = more reliable stats)
python backtest.py --symbol BTCUSDT --days 90 --strategy breakout
```

### Output Metrics

| Metric | Meaning | Healthy Range |
|--------|---------|---------------|
| **Signals** | Total trade signals generated | Depends on strategy aggressiveness |
| **WinRate** | % of trades that hit TP before SL | > 50% for trend-follow, > 40% for reversal |
| **PF** (Profit Factor) | gross_profit / gross_loss | > 1.5 = good, > 2.0 = excellent |
| **AvgWin / AvgLoss** | Average PnL % per winning/losing trade | Should align with R:R (1:2 → +3%/-1.5%) |
| **MaxDD** | Peak-to-trough drawdown on cumulative PnL | < 10% = acceptable |
| **Expectancy** | Average PnL per trade | > 0% = profitable |

### Example Output

```
==============================================================================================================
  📊 BACKTEST RESULTS — BTCUSDT — 7 days
==============================================================================================================
  Strategy        Signals   Win  Loss    TO  WinRate       PF   AvgWin  AvgLoss    MaxDD   Expect
--------------------------------------------------------------------------------------------------------------
  breakout              2     0     1     1     0.0%     0.67    0.00%   -1.14%    1.14%   -0.19%
==============================================================================================================
```

This shows breakout strategy had 2 signals in 7 days for BTC; 1 hit SL (-1.14%), 1 timed out. **PF=0.67 means it's losing money** — you'd tune the parameters (e.g. raise volume threshold) before deploying live.

### Trade Simulation Logic

- **Entry**: at close of the 5m signal candle
- **SL priority**: if a candle's `low <= SL` AND `high >= TP` in the same candle, **SL wins** (conservative assumption — worst-case fills)
- **Timeout**: if neither SL nor TP hit within `MAX_HOLD_CANDLES` (288 × 5m = 24h), close at last candle's close
- **Cooldown**: 4-hour cooldown between signals of the same strategy on the same symbol (matches live mode)

### Reports

JSON reports saved to `./backtest_reports/<SYMBOL>_<timestamp>.json` with full trade list for further analysis.

---

## 🧪 Testing & Validation

### Run Tests Locally

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Test Coverage

| File | Tests | What's Covered |
|------|-------|----------------|
| `tests/test_radar.py` | 19 | Filter logic (4H/1H/5m), R:R calculator, anti-spam memory, stablecoin filtering |
| `tests/test_strategies.py` | 20 | Strategy registry, base R:R, all 3 strategies' filter helpers + end-to-end signal evaluation |
| `tests/test_backtest.py` | 15 | Trade simulation (win/loss/timeout/SL-priority), metrics computation (PF, win rate, max DD, expectancy) |

All tests use **synthetic data** (no network) — they run in ~2 seconds and are safe to execute in CI.

### CI Pipeline (`.github/workflows/tests.yml`)

On every push/PR to `main`:
1. Install `requirements-dev.txt`
2. Run `ruff` lint (non-blocking)
3. Run `pytest` with verbose output
4. Generate coverage report (uploaded as artifact, 7-day retention)

On push to `main` (after tests pass):
5. Run live backtest on BTCUSDT (7 days, all strategies)
6. Run live backtest on ETHUSDT (7 days, reversal)

If backtests fail (network error, etc.), the job still passes — backtest is informational, not blocking.

---

## ⚠️ SECURITY — Token Hygiene

This repo previously leaked tokens via a committed `.env` file. The leak has been fixed (`.env` is now gitignored, history purged), but **if you forked or cloned before this fix, your tokens may be compromised**.

**Action required if you had tokens in the old `.env`:**

1. **Discord**: https://discord.com/developers/applications → your bot → **Bot → Reset Token**
2. **Telegram**: chat [@BotFather](https://t.me/BotFather) → `/revoke` → pick your bot → save new token
3. **GitHub PAT** (if shared anywhere): https://github.com/settings/tokens → delete + create new
4. **Update your GitHub Secrets** with the new tokens (Settings → Secrets and variables → Actions)
5. **Update your HF Space secrets** (or whichever hosting you use) with the new tokens

**Going forward**:
- `.env` is now in `.gitignore` — never commit it
- Use `.env.example` as the template
- Store real secrets only in GitHub Secrets (for Actions) or platform-specific secret stores (HF Spaces, Render, etc.)

---

## ⚠️ Disclaimer — A Friendly Word from a Fellow Trader

I built this bot for myself, and I'm sharing it because I genuinely think it can be useful to other traders who take a similar approach.

But hear me out:

> **This bot is an ASSISTANT, not an ORACLE.**

It can help you filter out noise and highlight interesting moments. But the final call is always yours. The crypto market is wild — it can make you rich in a week or leave you staring at the ceiling wondering what went wrong. No bot, indicator, or "trading guru" can predict the future with 100% accuracy.

**🔑 Principles I live by:**
- **DYOR** (Do Your Own Research) — always. Never blindly follow any signal.
- **Risk management** — never put in money you can't afford to lose.
- **Discipline** — your stop loss isn't a suggestion, it's your portfolio's life insurance.
- **Patience** — a sniper doesn't fire every 5 seconds. Sometimes there are no signals all day, and that's NORMAL.

> **⚖️ Not Financial Advice.** This is an educational project and a personal tool. Any profits or losses resulting from the use of this bot are entirely your own responsibility.

---

<p align="center">
  <b>Built with ☕, 🎯, and countless sleepless nights staring at charts.</b><br>
  <i>— from one trader to another</i>
</p>
