# 🚀 Deployment Guide — Crypto Radar v7.0

Step-by-step guide to deploy Crypto Radar v7.0 to production.

## 📋 Prerequisites

| Item | Cost | Notes |
|---|---|---|
| GitHub repo | Free | `De-violet/crypto-radar` (already exists) |
| Fly.io account | Free (256MB) | https://fly.io — sign up with GitHub |
| Vercel account | Free | https://vercel.com — sign up with GitHub |
| Supabase project | Free (500MB DB) | https://supabase.com |
| Cloudflare account | Free | https://cloudflare.com — for DNS |
| Your domain | – | Already purchased |
| Discord bot token | – | From https://discord.com/developers/applications |

---

## 🐍 Backend (Python + Discord bot) → Fly.io

### Step 1 — Install Fly.io CLI

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh
export PATH="$HOME/.fly/bin:$PATH"

# Verify
flyctl version
```

### Step 2 — Login & create app

```bash
flyctl auth login

# Dari folder repo (branch main)
cd /path/to/crypto-radar
git checkout main

# Create app (kalau belum ada)
flyctl launch --no-deploy --name crypto-radar --region sin
# Answer: "Would you like to copy configuration to the new app?" → Yes
# Answer: "Create .dockerignore from 1 .gitignore file?" → No (already exists)
```

### Step 3 — Set secrets

```bash
# Discord
flyctl secrets set DISCORD_TOKEN=your_discord_bot_token
flyctl secrets set DISCORD_NEWS_CHANNEL_ID=your_news_channel_id
flyctl secrets set DISCORD_ALERT_CHANNEL_ID=your_alert_channel_id

# Supabase (dari Supabase dashboard → Settings → API)
flyctl secrets set SUPABASE_URL=https://your-project.supabase.co
flyctl secrets set SUPABASE_ANON_KEY=your_anon_key
flyctl secrets set SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# API
flyctl secrets set API_INTERNAL_TOKEN=$(openssl rand -hex 32)
flyctl secrets set API_CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### Step 4 — Deploy

```bash
flyctl deploy
```

Setelah deploy, verifikasi:

```bash
curl https://crypto-radar.fly.dev/health
# {"status":"ok","version":"7.0.0",...}
```

### Step 5 — Setup auto-deploy from GitHub

1. Dapatkan Fly API token: `flyctl tokens create deploy -a crypto-radar`
2. Di GitHub repo → Settings → Secrets and variables → Actions → New secret:
   - Name: `FLY_API_TOKEN`
   - Value: token dari step 1
3. Workflow `.github/workflows/fly-deploy.yml` otomatis jalan tiap push ke `main`

---

## 🌐 Frontend (Next.js) → Vercel

### Step 1 — Import project ke Vercel

1. Buka https://vercel.com/new
2. Import `De-violet/crypto-radar` dari GitHub
3. **Penting**: di "Configure Project", set:
   - **Framework Preset**: Next.js
   - **Root Directory**: `./` (default — repo root)
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
4. **Production Branch**: `web` (BUKAN `main`)
5. **Environment Variables**:
   - `NEXT_PUBLIC_API_BASE_URL` = `https://crypto-radar.fly.dev`
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://your-project.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = `your_anon_key`
6. Click **Deploy**

### Step 2 — Setup custom domain di Vercel

1. Vercel dashboard → your project → Settings → Domains
2. Add domain: `your-domain.com` (atau `app.your-domain.com`)
3. Vercel akan kasih CNAME record — copy ini
4. Lanjut ke Cloudflare (Step 3 di bawah)

---

## 🗄 Database & Auth → Supabase

### Step 1 — Create project

1. Buka https://supabase.com → New Project
2. Name: `crypto-radar`
3. Database password: generate strong password, simpan di password manager
4. Region: Southeast Asia (Singapore) — paling dekat ke Fly.io `sin`
5. Plan: Free

### Step 2 — Get API keys

Project settings → API:

| Key | Untuk apa |
|---|---|
| Project URL | `SUPABASE_URL` di Fly.io, `NEXT_PUBLIC_SUPABASE_URL` di Vercel |
| anon public | `SUPABASE_ANON_KEY` di Fly.io, `NEXT_PUBLIC_SUPABASE_ANON_KEY` di Vercel |
| service_role | `SUPABASE_SERVICE_ROLE_KEY` di Fly.io **SAJA** (jangan di Vercel!) |

### Step 3 — Setup Auth providers

Authentication → Providers:

1. **Google**: enable, isi Client ID + Secret dari Google Cloud Console
   - Buat OAuth credential di https://console.cloud.google.com/apis/credentials
   - Authorized redirect URI: `https://your-project.supabase.co/auth/v1/callback`
2. **GitHub**: enable, isi Client ID + Secret dari GitHub OAuth Apps
   - Buat di https://github.com/settings/developers
   - Callback URL: `https://your-project.supabase.co/auth/v1/callback`

### Step 4 — Create DB schema (Phase 1)

Untuk Phase 0, belum ada tabel. Di Phase 1 akan dijalankan:

```sql
-- Run di Supabase SQL Editor
-- Schema lengkap akan dibuat di Phase 1
```

---

## 🌍 Domain → Cloudflare DNS

### Step 1 — Add domain ke Cloudflare (kalau belum)

1. Cloudflare dashboard → Add site → masukkan domain Anda
2. Update nameserver di registrar Anda sesuai instruksi Cloudflare

### Step 2 — Setup DNS records

Cloudflare → DNS → Records:

| Type | Name | Content | Proxy status | Notes |
|---|---|---|---|---|
| CNAME | `@` atau `app` | `cname.vercel-dns.com` | Proxied (orange cloud) | Untuk Vercel web |
| CNAME | `api` | `crypto-radar.fly.dev` | Proxied | Untuk FastAPI |
| MX | `@` | (sesuai email provider) | DNS only | Kalau pakai email domain |

**Catatan SSL**: Cloudflare proxy otomatis kasih SSL. Set SSL mode ke "Full" di SSL/TLS settings.

### Step 3 — Update CORS origins di Fly.io

Setelah domain live:

```bash
flyctl secrets set API_CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

Dan update Vercel env var:

```
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com
```

---

## 🔍 Verify Everything Works

### Backend

```bash
# Health check
curl https://api.your-domain.com/health
# Expected: {"status":"ok","version":"7.0.0",...}

# Strategies
curl https://api.your-domain.com/api/v1/strategies
# Expected: [{"name":"reversal",...},{"name":"breakout",...},{"name":"trend_follow",...}]

# Docs
open https://api.your-domain.com/docs
```

### Frontend

```bash
# Web dashboard
open https://your-domain.com
# Expected: landing page dengan violet theme

# Health check via Next.js API route
curl https://your-domain.com/api/health
# Expected: {"status":"ok","backend":{...}}
```

### Discord bot

Bot harus online di Discord server Anda. Cek log Fly.io:

```bash
flyctl logs
# Look for: "🤖 Logged in as YourBot#1234"
```

---

## 🆘 Troubleshooting

### Bot tidak online di Discord

1. Cek `flyctl logs` — cari "Discord bot failed"
2. Verify `DISCORD_TOKEN` valid: `flyctl secrets list`
3. Pastikan bot di-invite ke server Anda dengan permission `applications.commands` + `bot`

### Web tidak bisa connect ke API

1. Cek CORS: `flyctl secrets get API_CORS_ORIGINS`
2. Pastikan domain web ada di CORS whitelist
3. Cek network tab di browser — error "CORS policy" = masalah CORS
4. Cek `NEXT_PUBLIC_API_BASE_URL` di Vercel — harus `https://api.your-domain.com` atau `https://crypto-radar.fly.dev`

### Fly.io container OOM (256MB limit)

1. Cek memory: `flyctl status`
2. Kalau sering OOM, naikkan ke 512MB (still free tier):
   ```toml
   # fly.toml
   [vm]
     memory_mb = 512
   ```
3. Atau disable chart generation (paling berat):
   ```python
   # Di radar.py, line ~780
   # photo_buf = generate_chart(symbol, result.chart_df)
   # ↑ comment out untuk hemat RAM
   ```

### Vercel deploy fail

1. Cek build log di Vercel dashboard
2. Pastikan `npm install` sukses — cek `package.json` valid
3. Cek TypeScript errors: jalankan `npx tsc --noEmit` di lokal

---

## 📊 Cost Estimation (free tier limits)

| Service | Free tier | Estimated usage (1 user) | Status |
|---|---|---|---|
| Fly.io | 256MB shared VM | ~100MB used | ✅ Well within |
| Vercel | 100GB bandwidth, 100h build | <1GB, <10min build | ✅ Well within |
| Supabase | 500MB DB, 50K MAU | <10MB, 1 user | ✅ Well within |
| Cloudflare | unlimited DNS | – | ✅ Free forever |
| GitHub Actions | 2000 min/month | ~30 min/month | ✅ Well within |

**Total monthly cost: $0** untuk personal use.

Kalau sudah 100+ users:
- Fly.io: upgrade ke $2-5/month (more RAM)
- Supabase: $25/month Pro (8GB DB, 100K MAU)
- Vercel: tetap free (Pro $20/month hanya kalau butuh more bandwidth)

---

## 🎯 Next Steps (Phase 1+)

Setelah Phase 0 berhasil deploy:

1. **Phase 1** — Wire real Supabase Auth di Next.js + buat schema DB + implement `/api/v1/signals` baca dari Supabase
2. **Phase 2** — Chart per coin (pakai lightweight chart lib seperti `lightweight-charts`)
3. **Phase 3** — Settings page (read-write) + manual trigger scan
4. **Phase 4** — Backtest UI
5. **Phase 5** — Multi-user workspace + billing (Stripe)

Detail lihat di `README.md` bagian "Roadmap".
