# Meta Ads (optional for Phase 1 demo)

Use **Mock Meta** on `/integrations` until you create a real app.

## When you want live spend

1. [developers.facebook.com](https://developers.facebook.com/) → Create app (Business)  
2. Add **Marketing API** + **Facebook Login**  
3. Valid OAuth redirect URI (must match `.env`):

```text
https://YOUR-NGROK-OR-API-HOST/api/v1/integrations/meta/callback
```

Local without HTTPS (if Meta allows):

```text
http://127.0.0.1:8000/api/v1/integrations/meta/callback
```

4. Put in `backend/.env`:

```env
META_APP_ID=...
META_APP_SECRET=...
META_REDIRECT_URI=https://.../api/v1/integrations/meta/callback
```

5. Restart API → `/integrations` → Connect OAuth Meta → Sync  

Scopes (read-only): `ads_read`, `business_management`  

Full product flow: `docs/PHASE1_GUIDE.md`
