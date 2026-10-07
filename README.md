# SIH26122 — Intelligent Data Capture & Schedule-Linking Layer

A controlled middle layer between messy field evidence and a structured project schedule:

> **AI reads the mess. Rules check it. A human approves it. Everything is logged.**

Field reports (typed text, voice transcript, PDF/XLSX/CSV/TXT, scanned diaries, P6 exports) become *claims*.
Claims are extracted, matched to schedule activities (or decomposed across WBS siblings), checked by deterministic
rules, prioritised, and only become approved actuals after a Supervisor decision — with a SHA-256 audit chain,
CSV export and a P6 write-back (local mock).

**Stack:** React + TypeScript + Vite · FastAPI + Pydantic v2 · Supabase (Postgres + Auth) · sentence-transformers + FAISS + RapidFuzz · Groq (primary) / Gemini (fallback) via one shared client.

## Run it locally

Prerequisites: Python 3.13, Node 20+, Tesseract (`brew install tesseract`) for scanned-diary OCR, a filled-in `.env`
(copy `backend/.env.example`; needs Supabase URL/keys/`DATABASE_URL` and an LLM key).

```bash
# backend  (applies backend/models/schema.sql on startup; warms the FAISS index in the background)
python -m venv backend/.venv && source backend/.venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --port 8000

# load the v6 benchmark schedule (45 activities, 34 dependencies, float) — becomes the active schedule
python scripts/load_demo_schedule.py

# frontend  (frontend/.env: VITE_API_BASE_URL=http://localhost:8000, VITE_USE_MOCKS=false)
cd frontend && npm ci && npm run dev          # http://localhost:5173
```

Demo logins (seeded Supabase users; the password is the one shown on the login screen):
`site.engineer@sih26122.internal` → lands on **/intake**, `supervisor@sih26122.internal` → lands on **/digest**.

Scripted end-to-end walkthrough of the PRD demo flow (creates its own claims): `python scripts/demo_walkthrough.py`

Tests: `python -m pytest -q` (some tests call the live LLM and the live database — see *Caveats*).

## What is built (PRD v6 features)

| Area | Status |
|---|---|
| F1 schedule ingestion (CSV/XLSX/XER), transactional import, FS/SS/FF/SF, lag, float, criticality | ✅ (CSV accepts several predecessors per row, `;`-separated) |
| F2–F5 multi-format / typed / voice-text intake, hashing, provenance | ✅ |
| F6 static En/Hi/Te UI + runtime translation with safe fallback | ✅ (`POST /api/v1/reports/translate`, summary, Ask Why) |
| F7–F8 four-tier matching, top-3, unmatched | ✅ |
| F9 directional conflicts, F10 sequence/physical validation, F11 EXIF/GPS | ✅ (tests TC-SEQ/CONF) |
| F12–F13 review workspace, SHA-256 audit chain | ✅ (`chain_valid` verified in the walkthrough) |
| F14/F26 CSV export, F27 P6 write-back to the local mock | ✅ (`GET /api/v1/mock-p6/received` shows payloads) |
| F15–F19 dashboard (live), memory, digest, history, silent nudge | ✅ |
| F20 impact preview (FS/SS/FF/SF, lag, float, controlling predecessor, multi-hop) | ✅ |
| F21–F22 OCR diary, P6 schedule-export claims | ✅ |
| F23–F25 start/finish merge, rollup, forecast | ✅ |
| F29 adaptive clarification (one question, in the claim's language) | ✅ |
| F30 WBS Granularity Bridge (v6 allocation, XOR with normal match, editable split) | ✅ rebuilt this pass |
| F31 evidence fusion + knowledge graph | ✅ (`/claims/{id}/knowledge-graph`) |
| F32 smart review priority (severity × float multiplier + capped aging) | ✅ (TC-PRI) |
| F33 field provenance (AI / schedule / engineer / supervisor-edited) | ✅ (EDIT tags only changed fields) |
| F34 Ask Why (depth N, re-root, deterministic causal chain) | ✅ (`/graph/explain/{activity_id}`) |
| F35 AI execution summary (`/api/v1/reports/execution-summary`, cached per exact period) | ✅ |

### Notes on how the WBS bridge works
* A **WBS group** is a summary activity plus its direct children (`1.02.02` → `.01/.02/.03`) or 2+ activities sharing a `wbs_code`.
* A claim is **broad** when it names no sub-scope/asset/ID (or references the summary activity). Broad claims are split;
  everything else is a normal match. A claim has a `matched_activity_id` **or** split rows, never both.
* Completed siblings, not-yet-eligible siblings (planned to start after the claim date), siblings gated behind an incomplete
  FS/SS predecessor, and siblings in an incompatible UOM receive 0. The rest share the claim, capped by remaining headroom and
  weighted by remaining planned quantity when UOMs are compatible. Shares sum to 1.0000.
* Approval writes **one approved actual per child** (`claim value × split_pct`); quantities are always recalculated from the
  latest APPROVE/EDIT decisions, never accumulated.
* Table: `claim_activity_splits` (PRD §16.2, plus `allocated_quantity`, `uom`, `rationale`). The legacy `claim_wbs_splits` table is unused.

## Deliberate behaviours & deviations (read before the demo)

* **Digest default date:** `GET /api/v1/digest` with no `date` returns every claim (the Digest page picks the most recent date).
* **Execution state** follows the canonical rule *started ⇔ actual_start exists*. A quantity-only approval (no start event) therefore
  still reads "Not Started" in the execution summary and in sequence checks, although rollup shows the derived %.
* **P6 payload:** quantity is dropped (per PRD); for quantity-progressed activities `PercentComplete` is derived as approved qty ÷ planned qty.
* **Cumulative claim on a split:** each child receives `claimed_pct × split_pct` (PRD Feature 30 M4 contract).
* **Deterministic extraction fallback:** `EXTRACTION_FALLBACK=rules` (set in the demo `.env`) uses conservative regex extraction when the
  LLM is unavailable or over quota; gaps still trigger the one-question clarification. Unset it to fail with a 502 instead.
* **Execution summary** is also served at the older `/api/v1/execution-summary?period=` path (kept for compatibility).

## Caveats / known issues

* **Free-tier LLM quota:** the test suite makes live LLM calls (`backend/test_m2_intake.py`, `backend/shared/test_llm_extraction.py`).
  A full run can exhaust Groq's daily limit; the shared client fails fast on daily-quota errors and the fallback above takes over.
* **Tests use the live Supabase database** (as before), so runs leave claims behind. Use a separate project for CI.
* `POST /api/v1/digest/bulk-approve` **without `event_ids` approves every VALIDATED claim** (documented behaviour; the UI always sends ids).
* `POST /api/v1/schedules` is unauthenticated (existing behaviour, flagged in the plan's audit notes). Because the newest schedule is the
  active one, protect this route before exposing the API beyond localhost.
* The root-level `verify_step*.py` / `verify_m3_*.py` scripts are stale (they read a CSV layout that no longer exists); use `pytest`.
* The UI was type-checked and built (`npm run build`) and every endpoint it calls was exercised against the live backend, but the pages
  were not visually verified in a browser in this pass.

## Repository map

```
backend/routers/      one router per PRD area (schedules, intake, matching, checks, decisions, export, dashboard, graph, claim_graph, reports, …)
backend/shared/       llm_client (the only LLM implementation), wbs_split, rule_extraction, actuals, audit, auth, schedule parsing, FAISS index
backend/models/       schema.sql (idempotent, applied on startup) + migrations
frontend/src/         pages, components, api.ts (single API layer), i18n (en/hi/te)
sample_data/          45-activity benchmark (canonical/schedule.csv = single source of truth), demo inputs, expected results
scripts/              load_demo_schedule.py, demo_walkthrough.py
tests/                phase tests + tests/test_v6_*.py (WBS split, M4 algorithms, extraction fallback)
```

## Git workflow

`main` is protected; develop on feature branches and merge through reviewed PRs. Never commit `.env` or API keys.
