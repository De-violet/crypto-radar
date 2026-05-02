# 🎯 Crypto Radar — The Ultimate Sniper

> *"Tired of staring at charts at 2 AM with your eyes half-shut, terrified you'll miss the one good entry? Yeah, been there."*

Crypto Radar was born out of a very real frustration: **the crypto market never sleeps, but we're humans who need rest.** This bot isn't here to replace your trading instincts — think of it more as a tireless assistant that watches the charts while you sleep, grab coffee, or binge Netflix guilt-free.

The idea is simple: **when there's a high-quality opportunity, it whistles. When there isn't, it stays quiet.** No spam, no drama.

---

## 🧠 How It Works — Sniper, Not Rambo

If Rambo walks into the market and shoots in every direction (buying every green candle in sight), **the Sniper sits patiently, observes, and only pulls the trigger when every single condition lines up perfectly.**

This bot uses a **Multi-Timeframe Top-Down Analysis** approach — the same technique used by professional traders and institutional desk analysts. Here's the analogy:

| Step | Timeframe | What it looks for | Analogy |
|------|-----------|-------------------|---------|
| 1️⃣ | **1D (Daily)** | Is the macro trend Bullish or Bearish? (Close > EMA 50) | Reading the wind direction from a mountaintop |
| 2️⃣ | **4H** | Strong support bounce + volume spike (smart money stepping in) | Checking if there's a concrete foundation under price |
| 3️⃣ | **1H** | Stochastic oversold + golden cross (momentum ready to flip) | The bow is drawn back, ready to release |
| 4️⃣ | **5m** | Bullish Pinbar (a "rejection" candle — price tried to drop but got slapped back hard) | Finger's on the trigger, ready to squeeze |

**A coin must pass all 4 filters sequentially.** Fail one? Instantly dropped — no mercy. This isn't a bot that fires signals every 5 minutes — it only sends the ones that are **truly worth your attention.**

---

## 🔫 Key Features — Your Secret Weapons

### 📡 Telegram Alerts + Inline Keyboard
Every signal that passes all filters gets sent straight to your Telegram with a professional report. Complete with shortcut buttons to **Binance Chart**, **TradingView**, and **CoinGecko** — one tap and you're ready to execute.

### 💰 Auto Risk:Reward Calculator (1:2)
No need to open a separate calculator. Every signal comes with:
- **Entry Price** — the suggested entry point
- **Stop Loss** — 1.5% below support (tight enough to avoid wicks)
- **Take Profit** — automatically calculated at a 1:2 R:R ratio

Just copy-paste to your exchange. Done.

### 🧠 Anti-Spam Memory System
Ever gotten the same alert 10 times in an hour? Annoying, right? This bot has a "brain" — a JSON file that tracks when it last sent an alert for each coin. **4-hour cooldown** — once it fires a signal for BTC, it won't bother you about BTC again for the next 4 hours.

### ⚡ Automatic Retry
Connection dropped mid-request? Binance servers being sluggish? Relax. This bot has **automatic retry** (3 attempts with exponential back-off) on all HTTP requests. It doesn't go down easy.

---

## 🛠️ Prerequisites — Gear Up

Before you deploy, make sure you've got these:

| Tool | Version | Notes |
|------|---------|-------|
| **Python** | 3.12+ | Core runtime |
| **requests** | latest | For calling Binance & Telegram APIs |
| **pandas** | latest | Candlestick data processing |
| **pandas-ta** | latest | Technical indicators library (EMA, Stochastic, etc.) |
| **Telegram Bot** | — | Create one via [@BotFather](https://t.me/BotFather) |

---

## 🚀 Local Installation & Testing

Want to try it on your own machine first? Easy.

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/crypto-radar.git
cd crypto-radar
```

### 2. Install dependencies

```bash
pip install requests pandas pandas-ta
```

### 3. Set environment variables

Linux / macOS:
```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF_your_bot_token_here"
export TELEGRAM_CHAT_ID="-100xxxxxxx"
```

Windows (PowerShell):
```powershell
$env:TELEGRAM_BOT_TOKEN = "123456:ABC-DEF_your_bot_token_here"
$env:TELEGRAM_CHAT_ID = "-100xxxxxxx"
```

> 💡 **Tip:** Don't have a Telegram bot yet? Open [@BotFather](https://t.me/BotFather), type `/newbot`, follow the steps. Grab your token, invite the bot to your group/channel, and get the chat ID.

### 4. Run it!

```bash
python radar.py
```

If everything's set up correctly, you'll see something like this in your terminal:

```
============================================================
  🎯 CRYPTO RADAR v4.0 — Multi-Timeframe Sniper Edition
============================================================
  Coins  : BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT
  Time   : 2026-05-02 12:00 UTC
  Memory : alerted_coins.json (cooldown 4h)
============================================================

──────────────────────────────────────────────────
  🔍 Scanning: BTC/USDT
──────────────────────────────────────────────────
  [1/4] 1D Trend ... ✅ BULLISH
  [2/4] 4H Support+Vol ... ❌ FILTER 4H FAILED
        ⛔ BTC ❌ Support Zone (2.14%)  ✅ Bounce  ❌ Vol 0.8x. DROP.
```

Coins that fail any filter get dropped immediately. Brutal, but effective.

---

## ☁️ Deploy on GitHub Actions — 24/7 Autopilot

This is the best part: **make your bot run autonomously in GitHub's cloud, FOR FREE, no VPS needed.**

### 1. Push the repo to GitHub

```bash
git add .
git commit -m "🚀 Initial deploy"
git push origin main
```

### 2. Add Secrets

Go to your repo on GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 2 secrets:

| Name | Value |
|------|-------|
| `TELEGRAM_BOT_TOKEN` | Your token from BotFather |
| `TELEGRAM_CHAT_ID` | Your group/channel chat ID |

### 3. Enable the Workflow

Go to the **Actions** tab in your repo. If the workflow isn't running yet, click **"I understand my workflows, go ahead and enable them"**.

Your bot now runs **automatically every 15 minutes**, 24/7. On each run it will:
1. Scan all monitored coins through the 4-layer filter
2. Send a Telegram alert if a sniper signal is found
3. Auto-commit the memory file (so the cooldown system persists across runs)

> 💡 **Want to test manually?** Go to the Actions tab → select the workflow → click **"Run workflow"**. It runs instantly without waiting for the cron schedule.

---

## 📂 Project Structure

```
crypto-radar/
├── .github/
│   └── workflows/
│       └── main.yml          # GitHub Actions: autopilot every 15 minutes
├── radar.py                  # The brain: scanner + filters + notifier
├── alerted_coins.json        # Anti-spam memory (auto-generated at runtime)
└── README.md                 # You're reading this right now
```

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
