# SIH26122 — Intelligent Data Capture & Schedule-Linking Layer

A system that ingests messy infrastructure field progress reports, extracts structured
execution claims, matches them to project baseline schedule activities, performs
validation and conflict checks, and requires human planner approval before anything
becomes final.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · FastAPI · Pydantic v2 · Supabase PostgreSQL |
| Frontend | React · TypeScript · Vite · TanStack Query |
| AI / Matching | OpenAI-compatible LLM API · sentence-transformers · FAISS · RapidFuzz |

## Project Structure

```
SIH26122/
├── backend/          # FastAPI app — entry point: backend/main.py
│   ├── routers/
│   ├── models/
│   ├── shared/       # db.py, auth.py, schemas.py, ...
│   ├── .env          # gitignored — real secrets live here
│   └── .env.example  # template — copy to .env and fill in
└── frontend/         # React + Vite app
    ├── src/
    ├── .env          # gitignored
    └── .env.example  # template
```

---

## Quickstart — Local Development

### 1. Backend

All backend commands are run from **`SIH26122/`** (this directory), so that
`backend` resolves as a Python package (`backend.main:app`).

```powershell
# Activate virtual environment (Windows PowerShell)
backend\venv\Scripts\Activate.ps1

# Install / update dependencies
pip install -r backend/requirements.txt

# Start the server
uvicorn backend.main:app --reload --port 8000
```

> **backend/.env is self-loading.** The backend finds its own `.env` using a
> `__file__`-relative path — you do NOT need to copy or symlink it to `SIH26122/.env`.
> Secrets live exclusively in `backend/.env`.

Verify it started cleanly:
- **Swagger docs**: http://127.0.0.1:8000/docs
- **Health**: http://127.0.0.1:8000/health

### 2. Frontend

```powershell
cd frontend
npm install          # first time only
npm run dev
```

Frontend runs at **http://localhost:5173**.

> **CORS** is pre-configured: `backend/main.py` defaults `CORS_ORIGINS` to
> `http://localhost:5173,http://127.0.0.1:5173` — no configuration needed for
> standard local dev.

---

## Environment Configuration

### Backend — `backend/.env`

Copy `backend/.env.example` → `backend/.env` and fill in your values.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Supabase Postgres direct connection string |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Publishable/anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Service-role key (bypasses RLS — keep secret) |
| `AUTH_DEV_MODE` | `true` to accept unsigned dev tokens (local dev only — see below) |
| `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL` | LLM configuration (Groq or Gemini) |
| `CORS_ORIGINS` | Comma-separated allowed origins (default covers Vite dev server) |

### Frontend — `frontend/.env`

```ini
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_USE_MOCKS=false     # false = real backend; true = local mock data only
```

> If `VITE_USE_MOCKS` is missing or anything other than `false`, the app
> silently serves fake data for every screen. A loud `console.warn` fires in
> the browser DevTools to make this impossible to miss.

---

## Demo Login Accounts (Dev Mode)

Used when `AUTH_DEV_MODE=true` in `backend/.env` and no live Supabase project
is configured in `frontend/.env`.

| Email | Password | Role | Landing page |
|-------|----------|------|-------------|
| `site.engineer@sih26122.internal` | `Demo123456!` | SITE_ENGINEER | `/intake` |
| `supervisor@sih26122.internal` | `Demo123456!` | SUPERVISOR | `/digest` |
| `engineer@setu.ai` | `Demo123456!` | SITE_ENGINEER | `/intake` |
| `planner@setu.ai` | `Demo123456!` | SUPERVISOR | `/digest` |

> Roles are resolved by the **backend** from the `profiles` database table —
> never from client-side storage. A login that succeeds but has no matching
> `profiles` row will 401 on `/api/v1/auth/me`.

---

## Troubleshooting

### Stale / zombie backend process on port 8000

Multiple `uvicorn --reload` restarts can leave an orphaned process still bound
to 8000, silently serving old code. If you see unexpected behavior after a restart:

```powershell
# Windows — find the PID on port 8000
netstat -ano | findstr :8000

# Kill it (use the PID from the LISTENING row)
taskkill /PID <PID> /F
```

```bash
# macOS / Linux
lsof -ti :8000 | xargs kill -9
```

### App looks like it works but makes no real API calls

Check the browser DevTools console. If you see:

```
[SetuAI] 🚧 Running in MOCK MODE — no backend calls are being made.
```

Set `VITE_USE_MOCKS=false` in `frontend/.env` and restart `npm run dev`.

### Backend 401 "Invalid token: Unable to find a signing key"

If you are using the dev-mode login accounts, the error message will include:

> "This looks like an unsigned dev token (alg: none)..."

Fix: set `AUTH_DEV_MODE=true` in `backend/.env` **and** leave
`SUPABASE_JWT_SECRET`, `SUPABASE_JWKS_URL`, and `SUPABASE_URL` blank.

---

## Security Notes

> [!CAUTION]
> `backend/.env` contains a live database password, a Supabase service-role key
> (which bypasses Row Level Security), and an LLM API key.
>
> - `backend/.env` and `frontend/.env` are in `.gitignore` and must **never** be committed.
> - If this repository is ever made public or shared outside the team, **immediately
>   rotate** the `SUPABASE_SERVICE_ROLE_KEY` and `LLM_API_KEY`. The service-role key
>   grants full unrestricted database access.

---

## Git Workflow

- `main` is protected from direct development pushes.
- Each member works on their assigned feature branch.
- Changes are merged through Pull Requests with at least one reviewer.
