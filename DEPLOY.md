# 🚀 Deployment Guide — Crypto Radar v7.0

Step-by-step guide to deploy Crypto Radar v7.0 to production using
**HuggingFace Spaces** (Python backend) + **Vercel** (Next.js frontend) +
**Supabase** (DB & Auth) + **Cloudflare** (DNS).

## 📋 Prerequisites

| Item | Cost | Notes |
|---|---|---|
| GitHub repo | Free | `De-violet/crypto-radar` (already exists) |
| HuggingFace account | Free (16GB RAM, 2 vCPU) | https://huggingface.co/join — sign up |
| Vercel account | Free | https://vercel.com — sign up with GitHub |
| Supabase project | Free (500MB DB) | https://supabase.com |
| Cloudflare account | Free | https://cloudflare.com — for DNS |
| Your domain | – | Already purchased |
| Discord bot token | – | From https://discord.com/developers/applications |

**Tidak butuh kartu kredit** untuk semua layanan di atas! HF Spaces free
tier memberi 16GB RAM + 2 vCPU shared (jauh lebih besar dari Fly.io 256MB).

---

## 🤗 Backend (Python + Discord bot) → HuggingFace Spaces

### Step 1 — Create HuggingFace account & Space

1. Daftar di https://huggingface.co/join (gratis, bisa pakai GitHub login)
2. Klik avatar Anda (kanan atas) → **New Space**
3. Isi:
   - **Space name**: `crypto-radar`
   - **License**: MIT
   - **SDK**: **Docker** (pilih Docker — bukan Gradio/Streamlit)
   - **Visibility**: **Private** (recommended — secrets aman)
4. Klik **Create Space**

Setelah create, Space Anda URL-nya:
```
https://huggingface.co/spaces/<YOUR_HF_USERNAME>/crypto-radar
```

### Step 2 — Create HF Token (untuk auto-sync dari GitHub)

1. Buka https://huggingface.co/settings/tokens
2. Klik **New token**
3. Isi:
   - **Name**: `github-sync`
   - **Type**: **Write** (scope: write ke repo)
4. Klik **Create**
5. **Copy token** (mulai dengan `hf_...`) — simpan, hanya muncul sekali

### Step 3 — Set secrets di GitHub repo (untuk auto-sync)

Di https://github.com/De-violet/crypto-radar → Settings → Secrets and variables → Actions → **New repository secret**:

| Secret name | Value |
|---|---|
| `HF_TOKEN` | Token dari Step 2 (`hf_...`) |
| `HF_USERNAME` | Username HuggingFace Anda (case-sensitive, misal `De-violet`) |

Setelah ini diset, **setiap push ke branch `main`** akan otomatis sync ke HF Space via workflow `.github/workflows/hf-sync.yml`.

### Step 4 — Set secrets di HF Space

Buka Space Anda → Settings → **Repository secrets** → **New secret**:

| Secret name | Value |
|---|---|
| `DISCORD_TOKEN` | Token bot Discord Anda |
| `DISCORD_NEWS_CHANNEL_ID` | Channel ID untuk berita crypto |
| `DISCORD_ALERT_CHANNEL_ID` | Channel ID untuk alert listing |
| `SUPABASE_URL` | `https://your-project.supabase.co` |
| `SUPABASE_ANON_KEY` | Anon key dari Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key dari Supabase |
| `API_INTERNAL_TOKEN` | Random string (`openssl rand -hex 32`) |
| `API_CORS_ORIGINS` | `https://your-domain.com,https://your-username-crypto-radar.hf.space` |

> ⚠️ Jangan commit `.env` ke git — semua secrets diatur via HF Settings.

### Step 5 — Trigger deploy pertama

Ada 2 cara:

**Cara A — Auto-sync (recommended)**: Push commit apapun ke branch `main` di GitHub. Workflow akan auto-sync ke HF Space.

**Cara B — Manual**: Di HF Space Anda, klik tab "Files" → drag-anddrop semua file dari repo GitHub Anda (kecuali `.env`, `tests/`, `__pycache__/`).

Setelah deploy pertama, tunggu 5-10 menit untuk build Docker image. Cek log di tab "Logs".

### Step 6 — Verify deployment

Setelah status Space = "Running", health check:

```bash
curl https://your-username-crypto-radar.hf.space/health
# Expected: {"status":"ok","version":"7.0.0","uptime_seconds":...,"active_strategies":[...]}
```

Cek Discord bot online di server Anda. Logs di HF → tab "Logs" akan tampil:
```
🤖 Discord bot started in background task
🤖 Logged in as YourBot#1234 (ID: ...)
```

### Step 7 (Opsional) — Enable persistent storage

Default HF Spaces: file system read-only kecuali `/data`. Untuk persist
`alerted_coins.json` (memory anti-spam) lewat restart:

1. HF Space → Settings → **Persistent storage** → Upgrade (gratis 20GB small disk)
2. Set env var: `MEMORY_FILE=/data/alerted_coins.json`
3. Restart Space

Atau alternatif: pakai Supabase DB (akan dibahas di Phase 1).

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
4. **Production Branch**: `web` (BUKAN `main`!)
5. **Environment Variables**:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://your-username-crypto-radar.hf.space` |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://your-project.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Anon key dari Supabase |

6. Click **Deploy**

### Step 2 — Setup custom domain di Vercel

1. Vercel dashboard → your project → Settings → Domains
2. Add domain: `your-domain.com` (atau `app.your-domain.com`)
3. Vercel akan kasih CNAME record — copy ini

---

## 🗄 Database & Auth → Supabase

### Step 1 — Create project

1. Buka https://supabase.com → New Project
2. Name: `crypto-radar`
3. Database password: generate strong password, simpan di password manager
4. Region: Southeast Asia (Singapore) — paling dekat dengan HF Spaces
5. Plan: Free

### Step 2 — Get API keys

Project settings → API:

| Key | Untuk apa |
|---|---|
| Project URL | `SUPABASE_URL` di HF Space, `NEXT_PUBLIC_SUPABASE_URL` di Vercel |
| anon public | `SUPABASE_ANON_KEY` di HF Space, `NEXT_PUBLIC_SUPABASE_ANON_KEY` di Vercel |
| service_role | `SUPABASE_SERVICE_ROLE_KEY` di HF Space **SAJA** (jangan di Vercel!) |

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
| CNAME | `api` | `your-username-crypto-radar.hf.space` | Proxied | Untuk FastAPI HF Space |
| MX | `@` | (sesuai email provider) | DNS only | Kalau pakai email domain |

**Catatan SSL**: Cloudflare proxy otomatis kasih SSL. Set SSL mode ke "Full" di SSL/TLS settings.

### Step 3 — Update CORS origins di HF Space

Setelah domain live, update secret di HF Space:

```
API_CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com,https://your-username-crypto-radar.hf.space
```

Dan update Vercel env var:

```
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com
```

---

## 🔍 Verify Everything Works

### Backend (HF Spaces)

```bash
# Health check
curl https://api.your-domain.com/health
# Expected: {"status":"ok","version":"7.0.0",...}

# Strategies
curl https://api.your-domain.com/api/v1/strategies
# Expected: [{"name":"reversal",...},{"name":"breakout",...},{"name":"trend_follow",...}]

# Docs (Swagger UI)
open https://api.your-domain.com/docs
```

### Frontend (Vercel)

```bash
# Web dashboard
open https://your-domain.com
# Expected: landing page dengan violet theme

# Health check via Next.js API route
curl https://your-domain.com/api/health
# Expected: {"status":"ok","backend":{...}}
```

### Discord bot

Bot harus online di Discord server Anda. Cek log di HF Space:

1. Buka https://huggingface.co/spaces/your-username/crypto-radar
2. Tab "Logs"
3. Look for: `🤖 Logged in as YourBot#1234`

---

## 🆘 Troubleshooting

### Bot tidak online di Discord

1. Cek tab "Logs" di HF Space — cari "Discord bot failed"
2. Verify `DISCORD_TOKEN` secret valid di HF Space Settings
3. Pastikan bot di-invite ke server Anda dengan permission `applications.commands` + `bot`
4. HF Space status harus "Running", bukan "Building" atau "Error"

### Web tidak bisa connect ke API

1. Cek CORS: verify `API_CORS_ORIGINS` di HF Space Settings includes domain Vercel Anda
2. Cek `NEXT_PUBLIC_API_BASE_URL` di Vercel — harus `https://your-username-crypto-radar.hf.space` atau `https://api.your-domain.com`
3. Cek network tab di browser — error "CORS policy" = masalah CORS
4. HF Spaces free tier bisa sleep kalau tidak ada traffic — solusi: pakai UptimeRobot ping `/health` tiap 5 menit

### HF Space status "Building" terus

1. Cek tab "Logs" selama build
2. Umumnya: dependency conflict di `requirements.txt` → fix & push ulang
3. Build timeout 30 menit (free tier) — kalau sering timeout, simplify deps

### HF Space status "Error" / "App failed to start"

1. Cek log startup — biasanya:
   - Port salah (harus 7860, sudah fix di Dockerfile)
   - Permission denied (user `user` UID 1000 harus own /app)
   - Import error Python (cek ruff/pytest lokal dulu)

### Auto-sync dari GitHub tidak jalan

1. Cek tab "Actions" di GitHub repo — workflow `Sync to HuggingFace Spaces`
2. Verifikasi `HF_TOKEN` valid (buka https://huggingface.co/settings/tokens)
3. Verifikasi `HF_USERNAME` benar (case-sensitive)
4. Verifikasi Space sudah dibuat di HF dulu (workflow tidak bisa create Space otomatis)

### Vercel deploy fail

1. Cek build log di Vercel dashboard
2. Pastikan `npm install` sukses — cek `package.json` valid
3. Cek TypeScript errors: jalankan `npx tsc --noEmit` di lokal

---

## 📊 Cost Estimation (free tier limits)

| Service | Free tier | Estimated usage (1 user) | Status |
|---|---|---|---|
| HuggingFace Spaces | 16GB RAM, 2 vCPU shared | ~500MB used | ✅ Well within |
| Vercel | 100GB bandwidth, 100h build | <1GB, <10min build | ✅ Well within |
| Supabase | 500MB DB, 50K MAU | <10MB, 1 user | ✅ Well within |
| Cloudflare | unlimited DNS | – | ✅ Free forever |
| GitHub Actions | 2000 min/month | ~30 min/month | ✅ Well within |

**Total monthly cost: $0** untuk personal use.

Kalau sudah 100+ users:
- HuggingFace: tetap free untuk Spaces basic (atau upgrade ke Spaces Pro $9/month untuk GPU/persistent disk)
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
