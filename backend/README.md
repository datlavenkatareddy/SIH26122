# SIH26122 — Backend

FastAPI + Python backend for the SIH26122 infrastructure progress tracking system.

## Prerequisites

- Python 3.11+
- Virtual environment created inside `backend/venv/`

## Setup

All commands below are run from the **`SIH26122/` directory** (the parent of `backend/`).
This is required so that `backend` is a proper Python package importable as `backend.main`.

```powershell
# 1. Activate the virtual environment (Windows PowerShell)
backend\venv\Scripts\Activate.ps1

# On Windows Command Prompt:
# backend\venv\Scripts\activate.bat

# On macOS/Linux:
# source backend/venv/bin/activate

# 2. Install dependencies (first time / after requirements changes)
pip install -r backend/requirements.txt

# 3. Configure environment
#    backend/.env already exists for local dev. If starting fresh:
copy backend\.env.example backend\.env
#    Then edit backend/.env and fill in your real values.

# 4. Start the backend
uvicorn backend.main:app --reload --port 8000
```

The API will be available at:
- **Swagger UI / interactive docs**: http://127.0.0.1:8000/docs
- **OpenAPI JSON**: http://127.0.0.1:8000/openapi.json
- **Health check**: http://127.0.0.1:8000/health

## Environment Variables

All secrets live in `backend/.env` — **never** in the parent `SIH26122/.env`.

The backend loads `backend/.env` using an explicit `__file__`-relative path, so it
works correctly regardless of the working directory uvicorn is launched from.
You do **not** need a duplicate `.env` at the `SIH26122/` level.

See [`backend/.env.example`](.env.example) for the full list of variables with explanations.

### Key variables for local dev (dev-mode, no live Supabase)

```ini
AUTH_DEV_MODE=true

# Leave these blank so the unsigned dev-token fallback is reached:
SUPABASE_JWT_SECRET=
SUPABASE_JWKS_URL=
SUPABASE_URL=
```

> **Both** conditions must be true for `AUTH_DEV_MODE` to activate:
> 1. `AUTH_DEV_MODE=true`
> 2. All Supabase verification variables (`SUPABASE_JWT_SECRET`, `SUPABASE_JWKS_URL`, `SUPABASE_URL`) must be absent or empty.

## CORS

By default the backend allows `http://localhost:5173` and `http://127.0.0.1:5173`
(the Vite dev server). Controlled by `CORS_ORIGINS` in `backend/.env`; no change
needed for standard local development.

## Troubleshooting — Stale/Zombie Process on Port 8000

Multiple `uvicorn --reload` restarts (or a crash without clean shutdown) can leave
an orphaned process bound to port 8000. Symptoms: the new terminal appears to start
but requests hit old code, wrong config, or silently fail.

**Diagnose and kill on Windows:**

```powershell
# Find the PID listening on 8000
netstat -ano | findstr :8000

# Kill it (replace <PID> with the number from the LISTENING row)
taskkill /PID <PID> /F
```

**On macOS/Linux:**

```bash
lsof -ti :8000 | xargs kill -9
```

Then restart uvicorn fresh.

## Running Tests

From `SIH26122/` with the venv active:

```powershell
pytest backend/
```
