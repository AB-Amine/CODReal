# Supabase

On this machine Supabase is **already configured** (backend service_role + frontend anon).

## If you need to re-do it

1. Create project at [supabase.com](https://supabase.com)  
2. SQL Editor → run `supabase/migrations/001_initial_schema.sql`  
3. Project Settings → API:

| Key | File |
|-----|------|
| URL | `backend/.env` `SUPABASE_URL` + `frontend/.env.local` `NEXT_PUBLIC_SUPABASE_URL` |
| service_role | `backend/.env` `SUPABASE_KEY` only |
| anon | `frontend/.env.local` `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| JWT Secret | `backend/.env` `SUPABASE_JWT_SECRET` |

4. Auth → Email ON; for local tests you may disable “Confirm email”  

5. Restart API + frontend  

Verify: `GET /api/v1/health` → `"supabase_configured": true`
