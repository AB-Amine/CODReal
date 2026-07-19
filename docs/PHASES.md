# CODReal — Phases (source of truth for progress)

Detailed CDC: `Cahier_des_Charges_CODReal_v2.md`  
Day-to-day Phase 1: **`docs/PHASE1_GUIDE.md`**  
Setup audit: **`docs/STATUS.md`**

---

## Phase 1 — MVP Puissant 🟡 IN PROGRESS (~80% code / ~40% go-to-market)

### Done (code)
- [x] Foundations (monorepo, FastAPI, Next.js, Supabase schema)
- [x] Matching engine + calculation engine + tests (19)
- [x] CSV upload + validation
- [x] Dashboard UI + campaigns + alerts (rule-based API)
- [x] Auth UI + JWT + persistence layer
- [x] Supabase project keys configured (local)
- [x] Meta integration code + mock
- [x] TikTok integration code + mock
- [x] Cron sync endpoint + scripts
- [x] ngrok HTTPS for OAuth redirects (when running)

### Blocked / waiting (external)
- [ ] TikTok app **verification approved**
- [ ] TikTok App ID + Secret filled in `.env`
- [ ] Meta Developer App created + secrets filled

### Remaining Phase 1 work
- [ ] Daily demo path validated by team (mock + CSV)
- [ ] Deploy Vercel + Render
- [ ] Production secrets (`TOKEN_ENCRYPTION_KEY`, `CRON_SECRET`)
- [ ] Dashboard filters (period / platform)
- [ ] Alert thresholds editable in UI
- [ ] Landing / beta recruitment (5–10 testers)
- [ ] Optional: first real Meta or TikTok account connected

### Phase 1 exit criteria
1. Stranger can open a **public URL**, sign up, import CSV, see real ROAS  
2. Ads connected via **mock or real OAuth**  
3. Feedback from several COD sellers  

---

## Phase 2 — Intelligence & Alertes (not started)

- Advanced rules + campaign scoring  
- WhatsApp / Email notifications  
- Report export (PDF/CSV)  

---

## Phase 3 — IA légère (not started)

- MCP natural language Q&A on user data  
- Light return-rate prediction  
- Optimization suggestions  

---

## Architecture rule (all phases)

**Ingestion → Matching → Calculation → Presentation**
