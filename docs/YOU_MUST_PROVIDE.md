# What only you can provide (manual)

Code cannot create third-party accounts for you.

## Already done on your machine

- Supabase URL + service_role + JWT (backend)  
- Supabase URL + anon key (frontend)  
- ngrok auth configured  
- Redirect URIs pointing at your current ngrok host (when set)  

## Still optional / waiting

| You provide | When | Where |
|-------------|------|--------|
| TikTok App ID + Secret | After verification approved | `backend/.env` → `TIKTOK_APP_ID`, `TIKTOK_APP_SECRET` |
| Meta App ID + Secret | When you create Meta app | `backend/.env` → `META_APP_ID`, `META_APP_SECRET` |
| New ngrok public URL | Every time free ngrok restarts | TikTok/Meta console + `TIKTOK_REDIRECT_URI` / `META_REDIRECT_URI` |
| Vercel / Render accounts | Before public beta | Deploy |
| Strong secrets | Before production | `TOKEN_ENCRYPTION_KEY`, `CRON_SECRET` |

## Not required for demo

You can complete a full product demo with **Mock Meta + Mock TikTok + CSV** without any ads app approval.
