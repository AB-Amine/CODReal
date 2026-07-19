# CODReal — Project status (re-analysis)

**Last audited:** 2026-07-19  
**Phase:** 1 — MVP (in progress)

---

## 1. What CODReal is

Dashboard for Moroccan **COD** e-commerce:

1. **Ingestion** — ad spend (Meta/TikTok) + delivery CSV  
2. **Matching** — phone (MA formats) + order_ref  
3. **Calculation** — net profit, real CPA, real ROAS, return rate  
4. **Presentation** — dashboard + alerts  

Spec: `Cahier_des_Charges_CODReal_v2.md`

---

## 2. Setup matrix (honest)

### ✅ Done & working (code + config)

| Item | Status |
|------|--------|
| Monorepo (`frontend` / `backend` / `supabase` / `samples` / `scripts`) | ✅ |
| FastAPI API (matching, calc, CSV, dashboard, integrations, jobs) | ✅ |
| Next.js UI (landing, login, signup, dashboard, upload, campaigns, integrations) | ✅ |
| Matching engine (phone + order_ref) | ✅ |
| Calculation engine (profit / CPA / ROAS) | ✅ |
| CSV/Excel parser + validation | ✅ |
| Supabase **keys** (backend + frontend) | ✅ configured |
| DB tables (profiles, campaigns, orders, matches, ad_accounts, …) | ✅ query OK earlier |
| Auth UI + JWT backend | ✅ code ready |
| Meta OAuth + mock (code) | ✅ |
| TikTok OAuth + mock (code) | ✅ |
| Cron job endpoint `POST /jobs/sync-ads` | ✅ code |
| Backend unit tests | ✅ **19 passed** |
| ngrok installed + token saved | ✅ |
| TikTok/Meta redirect URIs in `.env` (ngrok HTTPS) | ✅ set |

### ⚠️ Partial / external (not fully live yet)

| Item | Status | What you do |
|------|--------|-------------|
| **TikTok app verification** | ⏳ Pending | Wait for approval; use **Mock TikTok** until then |
| **TikTok App ID / Secret** | ❌ Empty in `.env` | Paste when TikTok gives them / after approval |
| **Meta Developer App** | ❌ Not created / empty IDs | Optional; use **Mock Meta** or create Meta app |
| **Meta App ID / Secret** | ❌ Empty | Same |
| **Real OAuth end-to-end** | ⏸️ Blocked by above | Works in code once apps approved + secrets set |
| **TOKEN_ENCRYPTION_KEY** | ⚠️ Placeholder | Change for production |
| **CRON_SECRET** | ⚠️ Dev default | Change for production |

### ❌ Not done yet (Phase 1 remaining product work)

| Item | Priority |
|------|----------|
| Dashboard **date / platform filters** (UI) | Medium |
| **Alert rules UI** (user-editable thresholds) | Medium |
| **Deploy** (Vercel frontend + Render backend) | High for beta |
| **Scheduled cron** on a host (Render Cron every 4–6h) | Medium |
| **Landing** polish + beta signup funnel | Medium |
| 5–10 **beta testers** + real COD data | High for validation |
| Google / Facebook login | Phase 1 optional / later |
| WhatsApp / email notifications | **Phase 2** |
| MCP / AI | **Phase 3** |

### Runtime note (machines)

| Process | Typical state |
|---------|----------------|
| Backend API (`:8000`) | Start yourself from `backend/` |
| Frontend (`:3000`) | Start yourself from `frontend/` |
| ngrok | Start when you need public HTTPS OAuth |

---

## 3. Environment checklist

### Backend `backend/.env`

| Variable | Status |
|----------|--------|
| `SUPABASE_URL` | ✅ |
| `SUPABASE_KEY` (service_role) | ✅ |
| `SUPABASE_JWT_SECRET` | ✅ |
| `TIKTOK_REDIRECT_URI` | ✅ (ngrok HTTPS) |
| `META_REDIRECT_URI` | ✅ (ngrok HTTPS) |
| `TIKTOK_APP_ID` / `TIKTOK_APP_SECRET` | ❌ empty |
| `META_APP_ID` / `META_APP_SECRET` | ❌ empty |
| `TOKEN_ENCRYPTION_KEY` | ⚠️ change-me |
| `CRON_SECRET` | ⚠️ dev default |

### Frontend `frontend/.env.local`

| Variable | Status |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | ✅ |
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ |

---

## 4. Architecture (as built)

```
Browser (Next.js :3000)
    │  Supabase Auth (email/password)
    │  Bearer JWT → API
    ▼
FastAPI (:8000)
    ├── CSV upload → parse → (optional) persist
    ├── Matching engine
    ├── Calculation engine
    ├── Meta / TikTok OAuth + sync (or mock)
    └── Jobs (cron secret)
    ▼
Supabase PostgreSQL (+ RLS)
```

Flow always: **Ingestion → Matching → Calculation → Presentation**

---

## 5. How to demo today (no TikTok approval needed)

1. Start API + frontend (see `docs/PHASE1_GUIDE.md`)  
2. Open http://localhost:3000/signup → create account  
3. `/integrations` → **Mock Meta** + **Mock TikTok**  
4. `/upload` → `samples/codreal_delivery_template.csv` (persist on)  
5. `/dashboard` → **Mes données** → see real ROAS / alerts  

That is a full Phase‑1 product demo for beta users.

---

## 6. When TikTok verification is approved

1. Put `TIKTOK_APP_ID` + `TIKTOK_APP_SECRET` in `backend/.env`  
2. Ensure ngrok (or production HTTPS) matches TikTok redirect URL  
3. Restart API  
4. `/integrations` → Connect OAuth TikTok → Sync  
5. Upload deliveries → dashboard  

Same pattern for Meta when you create the Meta app.
