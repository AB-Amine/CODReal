# TikTok Ads

## Current status

- **App verification:** pending (your case)  
- **Code:** OAuth + sync + mock ready  
- **Until approved:** use **Mock TikTok** on `/integrations`  

## Redirect URL (HTTPS required by TikTok web)

When ngrok is running, use the **current** public URL:

```text
https://YOUR-SUBDOMAIN.ngrok-free.app/api/v1/integrations/tiktok/callback
```

Must match exactly:

- TikTok console → Advertiser redirect URL  
- `backend/.env` → `TIKTOK_REDIRECT_URI`  

Free ngrok URLs **change** when you restart ngrok → update both places.

## After verification approved

```env
TIKTOK_APP_ID=...
TIKTOK_APP_SECRET=...
TIKTOK_REDIRECT_URI=https://.../api/v1/integrations/tiktok/callback
```

1. Restart API  
2. API + `ngrok http 8000` running  
3. `/integrations` → Connect OAuth → Sync  
4. Upload CSV → dashboard  

## Endpoints

| Method | Path |
|--------|------|
| GET | `/api/v1/integrations/tiktok/status` |
| GET | `/api/v1/integrations/tiktok/connect` |
| GET | `/api/v1/integrations/tiktok/callback` |
| POST | `/api/v1/integrations/tiktok/sync` |
| POST | `/api/v1/integrations/tiktok/mock-connect` |

See also: `docs/PHASE1_GUIDE.md`, `docs/STATUS.md`
