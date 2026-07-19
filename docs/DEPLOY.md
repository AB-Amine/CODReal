# Deploy CODReal — you + partner (laptop can be off)

## Architecture (production)

```
You / Partner browser
        │
        ▼
  Vercel (Next.js)  ──HTTPS──►  Render (FastAPI)
        │                              │
        └──────── Supabase Auth/DB ────┘
```

Both of you open the **same Vercel URL**. No need for your PC to stay on.

---

## What YOU configure (checklist)

### A. GitHub (code)

Already prepared in this repo. After first push:

- Repo: `https://github.com/Adilchagri/CODReal` (or the URL printed after push)

### B. Render — Backend API

1. Go to https://dashboard.render.com → sign up (GitHub login)
2. **New** → **Web Service** → connect repo `CODReal`
3. Settings:

| Field | Value |
|-------|--------|
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance | **Free** |

4. **Environment** variables (copy from your local `backend/.env`, no quotes):

| Key | Value |
|-----|--------|
| `SUPABASE_URL` | your Supabase project URL |
| `SUPABASE_KEY` | **service_role** key (secret) |
| `SUPABASE_JWT_SECRET` | JWT secret from Supabase |
| `CORS_ORIGINS` | `https://YOUR-VERCEL-APP.vercel.app` (add after Vercel exists; can update later) |
| `FRONTEND_URL` | `https://YOUR-VERCEL-APP.vercel.app` |
| `TOKEN_ENCRYPTION_KEY` | long random string |
| `CRON_SECRET` | long random string |
| `DEBUG` | `false` |
| `META_APP_ID` | (if configured) |
| `META_APP_SECRET` | (if configured) |
| `META_REDIRECT_URI` | `https://YOUR-RENDER-API.onrender.com/api/v1/integrations/meta/callback` |
| `TIKTOK_APP_ID` | optional |
| `TIKTOK_APP_SECRET` | optional |
| `TIKTOK_REDIRECT_URI` | `https://YOUR-RENDER-API.onrender.com/api/v1/integrations/tiktok/callback` |

5. Deploy → copy public URL, e.g.  
   `https://codreal-api.onrender.com`

6. Test: `https://codreal-api.onrender.com/api/v1/health`

### C. Vercel — Frontend

1. Go to https://vercel.com → sign up (GitHub)
2. **Add New Project** → import `CODReal`
3. Settings:

| Field | Value |
|-------|--------|
| Root Directory | `frontend` |
| Framework | Next.js |

4. **Environment variables**:

| Key | Value |
|-----|--------|
| `NEXT_PUBLIC_API_URL` | `https://codreal-api.onrender.com` (your Render URL, no trailing slash) |
| `NEXT_PUBLIC_SUPABASE_URL` | same as Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **anon** public key (not service_role) |

5. Deploy → copy URL, e.g.  
   `https://codreal.vercel.app`

6. Go back to **Render** and set:

- `CORS_ORIGINS=https://codreal.vercel.app`
- `FRONTEND_URL=https://codreal.vercel.app`

Redeploy API if needed.

### D. Meta (if using real OAuth)

In Meta Developer Console, add redirect:

```text
https://YOUR-RENDER-API.onrender.com/api/v1/integrations/meta/callback
```

Same value as `META_REDIRECT_URI` on Render.

### E. Partner access

Send them only:

```text
https://YOUR-APP.vercel.app
```

They:

1. Open the link  
2. **Sign up** with their email  
3. Use dashboard / mock Meta / upload CSV  

Same Supabase project → shared product, separate user data (RLS by user).

---

## Free tier notes

| Service | Note |
|---------|------|
| Render free | Sleeps after ~15 min idle → first request can take 30–60s |
| Vercel free | Fine for demo |
| Supabase free | Already in use |

---

## Local still works

Unchanged:

```powershell
cd backend → uvicorn ...
cd frontend → npm run dev
```

---

## Security

- Never commit `.env` / `.env.local`
- Only **anon** key on Vercel
- **service_role** only on Render
