# Crypto Radar — Web Frontend

Next.js 16 frontend for the **Crypto Radar** trading-signal dashboard. This is the
`web` branch, deployed independently to Vercel. The backend lives on the
`main` branch (Python FastAPI + Discord bot).

> **Status: Phase 0 (skeleton).** UI scaffolding + theme + Supabase placeholder
> only. Real auth, API integration, and charts land in Phase 1+.

---

## Tech stack

| Layer        | Choice                                           |
| ------------ | ------------------------------------------------ |
| Framework    | Next.js 16 (App Router, TypeScript)              |
| Runtime      | React 19                                         |
| Styling      | Tailwind CSS 4 (CSS-based config, no JS config)  |
| Components   | shadcn/ui (New York style) + lucide-react        |
| Theming      | next-themes (class strategy, dark default)       |
| Fonts        | `next/font/google` — Inter + JetBrains Mono      |
| Auth (soon)  | @supabase/supabase-js (installed, not wired yet) |
| Backend      | Python FastAPI (separate repo / branch)          |
| Deploy       | Vercel                                           |

### Color palette — Violet Luxury

Defined as HSL CSS variables in `src/app/globals.css`:

- **Primary** — violet-600 `#7C3AED` (light) / `hsl(263 70% 65%)` (dark)
- **Accent** — soft lavender `#C4B5FD` (light) / deep violet (dark)
- Full light + dark palettes per the Phase 0 spec.

---

## Project structure

```
src/
├── app/
│   ├── layout.tsx              # root layout (fonts + ThemeProvider + Toaster)
│   ├── page.tsx                # landing page
│   ├── globals.css             # Tailwind 4 + violet CSS vars
│   ├── login/page.tsx          # Supabase auth placeholder
│   ├── dashboard/
│   │   ├── layout.tsx          # sidebar + topbar shell
│   │   └── page.tsx            # overview (skeleton stat cards + table)
│   └── api/health/route.ts     # proxies Python backend /health
├── components/
│   ├── ui/                     # shadcn/ui (button, card, input, badge, skeleton, sonner)
│   ├── site-header.tsx
│   ├── site-footer.tsx
│   ├── theme-provider.tsx
│   ├── theme-toggle.tsx
│   └── feature-card.tsx
├── lib/
│   ├── utils.ts                # cn() helper
│   ├── api-client.ts           # fetch wrapper for Python API
│   └── supabase-client.ts      # placeholder (throws "Not implemented in Phase 0")
└── middleware.ts               # protects /dashboard/* (cookie placeholder)
```

---

## Getting started (local)

### Prerequisites

- Node.js 18.18+ (or 20+ recommended)
- npm 10+ (or bun / pnpm — adjust commands accordingly)

### Install & run

```bash
# 1. Install dependencies
npm install

# 2. Copy env vars (Phase 0 values are fine as placeholders)
cp .env.example .env.local

# 3. Start the dev server
npm run dev
# → http://localhost:3000
```

### Verify the build

```bash
npm run build
npm run start
```

### Lint

```bash
npm run lint
```

---

## Environment variables

Copy `.env.example` → `.env.local` and fill in:

| Variable                          | Required | Description                                   |
| --------------------------------- | -------- | --------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`        | yes      | Python FastAPI base URL (e.g. `http://localhost:8000`) |
| `NEXT_PUBLIC_SUPABASE_URL`        | Phase 1  | Supabase project URL                          |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`   | Phase 1  | Supabase anon/public key                      |
| `API_BASE_URL`                    | optional | Server-only override (used by `/api/health`)  |

> Phase 0 does not make any real auth or API calls — the placeholders are
> enough to boot the UI.

---

## Routes

| Path            | Auth | Description                                  |
| --------------- | ---- | -------------------------------------------- |
| `/`             | no   | Landing page (hero, features, stats)         |
| `/login`        | no   | Placeholder Supabase auth (Google/GitHub/email) |
| `/dashboard`    | yes  | Overview — 4 stat cards + signals table (skeletons) |
| `/api/health`   | no   | Proxies backend `/health`, returns 200/503/502 |

### Auth middleware

`src/middleware.ts` guards `/dashboard/*`. In Phase 0 it only checks for an
`sb-session` cookie (existence, not validity). Real Supabase session
verification lands in Phase 1.

To preview the dashboard locally without real auth, set a cookie:

```bash
# in your browser console on localhost:3000
document.cookie = "sb-session=phase0-placeholder; path=/";
```

---

## Deploy to Vercel

This branch is configured for zero-config Vercel deploys:

1. Push the `web` branch to GitHub.
2. In Vercel, import the repo and set:
   - **Build Command:** `next build` (auto-detected)
   - **Output Directory:** `.next` (auto-detected)
   - **Install Command:** `npm install` (auto-detected)
3. Add the environment variables from `.env.example` in the Vercel dashboard.
4. Set the **Production Branch** to `web`.
5. Every push to `web` auto-deploys.

---

## Roadmap

- **Phase 0** ✅ — Skeleton: landing, login, dashboard, `/api/health`, violet theme.
- **Phase 1** — Supabase auth (OAuth + magic-link), real API client, signals feed.
- **Phase 2** — Charts (price + equity curve), backtest viewer.
- **Phase 3** — Strategy editor, alert preferences, billing.

---

## License

Private project. See the `main` branch for full licensing.
