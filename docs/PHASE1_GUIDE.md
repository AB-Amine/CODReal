# Phase 1 — Complete guide (what to do, in order)

This is the **only guide you need** to understand and run Phase 1 of CODReal.

---

## A. Phase 1 goal (from the CDC)

**Prove** that Moroccan COD sellers can see **true profit** after ads + returns.

Must include:

| Feature | Status in code |
|---------|----------------|
| Auth (email/password) | ✅ |
| CSV delivery upload | ✅ |
| Phone + order matching | ✅ |
| Real ROAS / CPA / net profit | ✅ |
| Dashboard + campaign table + basic alerts | ✅ |
| Meta ads read-only (OAuth or mock) | ✅ code / mock; real app optional |
| TikTok ads read-only (OAuth or mock) | ✅ code / mock; **real app pending review** |
| Sync job (manual / cron-ready) | ✅ code |

**Not Phase 1:** WhatsApp alerts, report export, MCP/AI → Phase 2–3.

**Success criteria:** 5–10 beta users try it and understand the dashboard.

---

## B. How to run the app (every day)

### Terminal 1 — API (must be in `backend`)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
cd D:\CODREAL\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Or from repo root:

```powershell
cd D:\CODREAL
powershell -ExecutionPolicy Bypass -File .\run_api.ps1
```

- Docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/api/v1/health  

### Terminal 2 — Frontend

```powershell
cd D:\CODREAL\frontend
npm run dev
```

- App: http://localhost:3000  

### Terminal 3 — only when testing real OAuth (TikTok/Meta HTTPS)

```powershell
ngrok http 8000
```

Then set redirect URLs in TikTok/Meta console **and** `backend/.env` to:

```text
https://YOUR-NGROK-SUBDOMAIN.ngrok-free.app/api/v1/integrations/tiktok/callback
```

Restart API after changing `.env`.

---

## C. User journey (product process)

```
1. Signup / Login          → Supabase Auth
2. Connect ads             → Mock now | Real OAuth when apps approved
3. Import deliveries CSV   → phone, status, amount, date
4. System matches          → phone (+ order_ref)
5. Dashboard               → spend vs delivered revenue vs returns
6. Act                     → kill losing campaigns, scale winners
```

### Happy path for demo (recommended now)

| Step | Where | Action |
|------|--------|--------|
| 1 | `/signup` | Create account |
| 2 | `/integrations` | **Mock Meta** + **Mock TikTok** |
| 3 | `/upload` | Upload `samples/codreal_delivery_template.csv` with “persist” checked |
| 4 | `/dashboard` | “Mes données” — read KPIs + alerts |
| 5 | `/campaigns` | See per-campaign real ROAS |

---

## D. Phase 1 process — roadmap for the team

### Step 0 — Foundations ✅ DONE

- Repo structure, stack, engines, UI shell, Supabase wired, tests green  

### Step 1 — Local product demo ✅ READY NOW

- [ ] You run API + frontend every session  
- [ ] Signup works  
- [ ] Mock ads + CSV → dashboard shows real ROAS  
- [ ] Team trains on this flow  

### Step 2 — Wait for external approvals (parallel, no code block)

| External | Status | Action while waiting |
|----------|--------|----------------------|
| TikTok verification | Pending | Use mock; don’t block beta |
| Meta Developer App | Not created | Optional; mock is fine for beta |

When approved: fill App ID/Secret → OAuth → real spend.

### Step 3 — Harden MVP (next engineering work)

Priority order:

1. **Deploy** (Vercel + Render free tiers) so testers don’t need your PC  
2. Fix production env (HTTPS API URL, `CRON_SECRET`, `TOKEN_ENCRYPTION_KEY`)  
3. Dashboard filters (period, platform)  
4. Alert threshold settings (min ROAS, max return rate)  
5. Onboarding copy on landing (“import CSV in 2 minutes”)  

### Step 4 — Beta (week 7–8 of original plan)

1. Landing + clear signup  
2. Recruit 5–10 COD sellers (FB groups Maroc)  
3. Collect feedback on matching accuracy & UX  
4. Improve phone matching / CSV aliases if needed  

### Step 5 — Close Phase 1

Phase 1 is “done” when:

- [ ] Deployed URL works for a stranger  
- [ ] Signup + mock (or real) ads + CSV → clear profit view  
- [ ] ≥ 5 people tested and you know what to fix  
- [ ] Real Meta and/or TikTok connected for at least 1 account (if APIs approved)  

Then start **Phase 2** (email/WhatsApp alerts, exports, advanced rules).

---

## E. What you still need to set up (manual only)

| # | Item | Required for |
|---|------|----------------|
| 1 | Nothing else for **local mock demo** | Demo today |
| 2 | TikTok approval + App ID/Secret | Live TikTok spend |
| 3 | Meta App + App ID/Secret | Live Meta spend |
| 4 | Stable HTTPS (ngrok fixed domain or Render) | Reliable OAuth |
| 5 | Vercel + Render accounts | Public beta |
| 6 | Strong `TOKEN_ENCRYPTION_KEY` + `CRON_SECRET` | Production security |

Details: `docs/STATUS.md`

---

## F. API map (for developers)

| Area | Endpoints |
|------|-----------|
| Health | `GET /api/v1/health` |
| Auth | `GET /auth/status`, `GET /auth/me` |
| Orders | `POST /orders/upload?persist=true`, `GET /orders` |
| Campaigns | `GET/POST /campaigns` |
| Dashboard | `POST /dashboard/pipeline`, `GET /dashboard/me`, `POST /dashboard/seed-demo` |
| Meta | `/integrations/meta/*` (connect, callback, sync, mock) |
| TikTok | `/integrations/tiktok/*` |
| Cron | `POST /jobs/sync-ads` + `Authorization: Bearer CRON_SECRET` |

Interactive: http://127.0.0.1:8000/docs  

---

## G. CSV columns (delivery import)

**Required:** `phone`, `status`, `amount_collected`, `delivery_date`  
**Optional:** `order_ref`, `carrier`, `campaign_name`, `campaign_id`  

Status: `delivered` | `returned` | `refused` | `pending` (FR aliases accepted: livré, retour, …)  

Template: `samples/codreal_delivery_template.csv`

---

## H. Formulas (product truth)

- **Net profit** = delivered revenue − ad spend − (return fee × returned/refused)  
- **Real CPA** = spend ÷ delivered orders  
- **Real ROAS** = delivered revenue ÷ spend  

Default return fee: **25 MAD** (`DEFAULT_RETURN_FEE`).

---

## I. If something breaks

| Problem | Fix |
|---------|-----|
| `No module named 'app'` | `cd D:\CODREAL\backend` before uvicorn |
| `supabase_configured: false` | Check `backend/.env`; restart API from `backend/` |
| Login fails | Check frontend Supabase anon key; disable email confirm in Supabase if testing |
| TikTok OAuth fails | App pending or wrong redirect / empty App ID |
| ngrok URL changed | Update TikTok console + `.env` + restart API |

Check setup:

```powershell
powershell -File D:\CODREAL\scripts\check_setup.ps1
```
