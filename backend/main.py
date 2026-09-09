import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Explicit path: main.py lives at backend/main.py, so .parent → backend/.env.
# This MUST run before any backend module import below — shared/db.py and
# others read DATABASE_URL/SUPABASE_*/LLM_* at import time (module-level
# os.getenv calls), so loading .env afterwards leaves them permanently unset.
# Using __file__-relative path instead of bare load_dotenv() ensures the
# correct backend/.env is found regardless of which directory uvicorn is
# launched from (the project is always launched from SIH26122/, one level up).
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import (
    schedules,
    intake,
    matching,
    checks,
    decisions,
    export,
    auth,
    dashboard,
    activities,
    schedule,
    mock_p6,
)
from backend.shared.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Database initialization skipped on startup ({e})")
    yield


app = FastAPI(
    title="SIH26122 Infrastructure Progress Tracking API",
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(schedules.router)
app.include_router(intake.router)
app.include_router(matching.router)
app.include_router(checks.router)
app.include_router(decisions.router)
app.include_router(export.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(activities.router)
app.include_router(schedule.router)
app.include_router(mock_p6.router)