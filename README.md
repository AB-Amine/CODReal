# CODReal

**Real ROAS & Profit for COD e-commerce (Morocco / North Africa)**

Cross Meta/TikTok ad spend with real deliveries → **net profit, real CPA, real ROAS** after returns.

---

## Start here (read in this order)

| Doc | Purpose |
|-----|---------|
| **[`docs/DEPLOY.md`](docs/DEPLOY.md)** | **Deploy for you + partner (Vercel + Render)** |
| **[`docs/LOCAL_DEMO.md`](docs/LOCAL_DEMO.md)** | Local demo on one PC |
| **[`docs/PHASE1_GUIDE.md`](docs/PHASE1_GUIDE.md)** | Phase 1 process |
| **[`docs/STATUS.md`](docs/STATUS.md)** | What’s done vs missing |
| **[`docs/PHASES.md`](docs/PHASES.md)** | Phase 1/2/3 checklist |
| [`Cahier_des_Charges_CODReal_v2.md`](Cahier_des_Charges_CODReal_v2.md) | Full product spec (CDC) |

---

## Run locally

### API (folder must be `backend`)

```powershell
cd D:\CODREAL\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Or: `powershell -File D:\CODREAL\run_api.ps1`

- http://127.0.0.1:8000/docs  

### Frontend

```powershell
cd D:\CODREAL\frontend
npm run dev
```

- http://localhost:3000  

### Optional HTTPS tunnel (OAuth)

```powershell
ngrok http 8000
```

---

## Local demo (start here)

Full guide: **[`docs/LOCAL_DEMO.md`](docs/LOCAL_DEMO.md)**

```powershell
# Terminal 1
cd D:\CODREAL\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — test APIs
powershell -File D:\CODREAL\scripts\smoke_demo_apis.ps1

# Terminal 3
cd D:\CODREAL\frontend
npm run dev
```

Then open http://localhost:3000/dashboard → **Démo locale**  

(No Meta/TikTok App IDs needed. Real OAuth is optional.)

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14 + Tailwind (Vercel later) |
| Backend | FastAPI (Render later) |
| DB / Auth | Supabase |
| Ads | Meta + TikTok Marketing APIs (read-only) or mock |

**Pipeline:** Ingestion → Matching → Calculation → Presentation  

---

## Project layout

```
CODREAL/
├── backend/          # FastAPI
├── frontend/         # Next.js
├── supabase/         # SQL migrations
├── samples/          # CSV + demo JSON
├── scripts/          # setup helpers
└── docs/             # guides
```

---

## Phase status (short)

- **Phase 1 MVP:** code ~ready; demo with mock; TikTok real OAuth waiting for verification; deploy + beta still open  
- **Phase 2:** advanced alerts / WhatsApp / exports  
- **Phase 3:** MCP / light AI  

See `docs/PHASES.md` and `docs/STATUS.md`.

---

## Team

Backend & Architecture · Adil (Frontend) · Chouaib (DB & Security)  
Budget: free tiers (0 MAD) for MVP.
