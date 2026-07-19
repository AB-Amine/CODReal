# Local demo — step by step

You do **not** need Meta/TikTok App IDs or TikTok verification for this demo.

---

## Important truth about “fixing APIs”

| API type | Needed for local demo? | Status |
|----------|------------------------|--------|
| Health, demo, pipeline, matching, CSV parse | **Yes** | Built-in, no external keys |
| Supabase auth + save data | Nice (full account demo) | Already configured on your PC |
| **Real** Meta OAuth | No | Empty `META_APP_*` — use **Mock** |
| **Real** TikTok OAuth | No | Pending verification — use **Mock** |

“Fixing” real Meta/TikTok means creating/approving apps outside CODReal.  
For the demo we make sure **CODReal’s own APIs** all work.

---

## Step 1 — Start the API

Open PowerShell:

```powershell
cd D:\CODREAL\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Leave this window open.

Check: http://127.0.0.1:8000/api/v1/health  
Should show `"status":"ok"`.

Demo readiness: http://127.0.0.1:8000/api/v1/demo/ready  

---

## Step 2 — Smoke-test demo APIs (optional)

New PowerShell window:

```powershell
powershell -ExecutionPolicy Bypass -File D:\CODREAL\scripts\smoke_demo_apis.ps1
```

You want: **ALL DEMO APIs OK**.

---

## Step 3 — Start the frontend

```powershell
cd D:\CODREAL\frontend
npm run dev
```

Open: **http://localhost:3000**

---

## Step 4 — Demo path A (fastest, no account)

1. Go to **http://localhost:3000/dashboard**  
2. Click **Démo locale** / **Charger données démo**  
3. You should see:
   - Dépense pub, CA livré, Bénéfice net, ROAS réel, Taux de retour  
   - Table of campaigns with scores  
   - Alerts on losing campaigns  

This uses `POST /api/v1/dashboard/pipeline` (or `/api/v1/demo/run`).

**No login. No Supabase. No Meta/TikTok apps.**

---

## Step 5 — Demo path B (full product, with account)

Needs Supabase (already set on your machine).

1. **http://localhost:3000/signup** → create account  
2. Login if needed  
3. **http://localhost:3000/integrations**  
   - Click **Mock Meta**  
   - Click **Mock TikTok**  
4. **http://localhost:3000/upload**  
   - Enable “Enregistrer en base”  
   - Upload: `D:\CODREAL\samples\codreal_delivery_template.csv`  
5. **http://localhost:3000/dashboard** → **Mes données**  

You now have: ads (mock) + deliveries + matching + real ROAS **in DB**.

---

## Step 6 — API docs (see everything)

http://127.0.0.1:8000/docs  

Try:

| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/demo/ready` | What works for demo |
| POST | `/api/v1/demo/run` | Full match + KPIs sample |
| POST | `/api/v1/dashboard/pipeline` | Same with custom JSON |
| POST | `/api/v1/orders/upload` | Parse CSV |
| GET | `/api/v1/integrations/meta/status` | Meta config (mock always available) |
| GET | `/api/v1/integrations/tiktok/status` | TikTok config |

---

## If something fails

| Symptom | Fix |
|---------|-----|
| `No module named 'app'` | You are not in `D:\CODREAL\backend` |
| Connection refused | API not started |
| Dashboard “API hors ligne” | Start backend first |
| Signup error | Supabase email confirm — disable in Supabase Auth settings for tests |
| Mock connect fails | Must be logged in + Supabase configured |
| Real Meta/TikTok Connect disabled | Normal without App ID — use Mock |

---

## What “success” looks like

- Dashboard shows **3 campaigns**, some **critical** alerts, one **good** (retargeting)  
- Match rate near **100%** on sample data  
- You can explain: *“Meta shows good ROAS; CODReal shows real profit after returns.”*

That is enough to demo Phase 1 to a seller or teammate.
