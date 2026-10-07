# [Product Name] — Product Requirements Document (PRD v5)

**SIH Problem Statement 26122 | Oil India Limited | Theme: Smart Automation**  
**Status:** Final consolidated build PRD  
**Source of truth:** PRD v2 functional requirements + PRD v4 technology/authentication updates + the current `SIH26122_Full_Build_Context_And_Task_Division` implementation/build plan.

> **Important:** This v5 consolidates the two PRDs. The existing team build plan is authoritative for implementation-level contracts, ownership, schemas, API behavior, integration behavior, and merge rules. Where an older PRD statement conflicts with the build plan, the build plan wins. In particular, the P6 adapter uses `PercentComplete`; `ActualDuration` is not part of the canonical payload.

---

## 1. Executive Summary

Infrastructure projects operate from a master schedule maintained in Primavera P6 or Microsoft Project. The schedule is structured, but field reality is not. Progress arrives through daily reports, spreadsheets, scanned diaries, typed messages, voice input, photographs, and subcontractor P6/MSP progress exports. These inputs frequently use different terminology, different levels of granularity, and different identifiers from the master schedule.

**[Product Name]** is a controlled middle layer between field reality and the project schedule.

It:

1. Ingests heterogeneous field-progress inputs.
2. Extracts structured claims from those inputs.
3. Matches each claim to a schedule activity.
4. Runs deterministic conflict, physical, evidence, and sequencing checks.
5. Presents the complete evidence and red flags to a human planner.
6. Allows only an authenticated Supervisor to approve, edit, reject, or hold a claim.
7. Updates the system's approved actual-progress record only after human action.
8. Automatically generates a current CSV export after approval.
9. Sends the same approved actual to a production-shaped P6 REST adapter backed by a local mock server for the hackathon.
10. Provides delay analytics, institutional memory, activity history, impact preview, and lightweight forecasting.
11. Maintains an auditable history of decisions and source provenance.

### One-line pitch

> **AI reads the mess. Rules check it makes sense. A human approves it. Everything is logged.**

---

# 2. Product Principles

These principles are non-negotiable.

1. **A field report is a claim, not a fact.**
2. **AI assists; it never makes the final approval decision.**
3. **Only an authenticated Supervisor can approve or edit an update that becomes official.**
4. **Low-confidence, unmatched, conflicting, or invalid claims are surfaced rather than hidden or silently resolved.**
5. **Every approved update is traceable to its source.**
6. **Every action is attributable to an authenticated user.**
7. **Machine matching and human selection are distinct concepts.**
8. **Externally supplied `activity_id` values are preserved exactly.**
9. **Approved incremental quantities are recalculated from source decisions, never blindly accumulated.**
10. **Adapter failures never roll back a successful approval.**
11. **PostgreSQL/Supabase is the source of truth; the FAISS index is an in-memory retrieval structure only.**
12. **No paid API is required anywhere in the default build.**
13. **The hackathon implementation is deliberately a single-app architecture; distributed infrastructure is out of scope.**
14. **The demo must have a deterministic, pre-tested fallback path.**

---

# 3. Problem Definition

## 3.1 Current problem

The baseline schedule contains structured activities such as:

- Activity ID
- WBS code
- Activity name
- Discipline
- Location
- Planned dates
- Planned quantity
- Unit of measure

Field reports may instead say things such as:

- "Line 24 spool erected."
- "Concrete pouring completed in Area C."
- "Joint 3 of 10 welded."
- A scanned handwritten diary entry.
- A voice note.
- A subcontractor's P6/MSP progress file.

The same activity can therefore be referred to using different terminology or different granularity.

## 3.2 Required solution

The system must create a reliable bridge:

```text
FIELD REALITY
    |
    | files / scans / text / voice / schedule export
    v
INTAKE
    |
    v
EXTRACTION
    |
    v
MATCHING
    |
    v
CHECKS
    |
    v
HUMAN REVIEW
    |
    v
APPROVED ACTUALS
    |
    +----> AUDIT LOG
    +----> CSV EXPORT
    +----> P6 REST ADAPTER
    +----> DASHBOARDS
    +----> INSTITUTIONAL MEMORY
    +----> FORECAST
```

---

# 4. System Architecture

## 4.1 High-level architecture

```text
                       +---------------------------+
                       |       LOGIN               |
                       |     Supabase Auth         |
                       | SITE_ENGINEER / SUPERVISOR|
                       +-------------+-------------+
                                     |
                  +------------------+------------------+
                  |                                     |
          SITE_ENGINEER                           SUPERVISOR
                  |                                     |
                  v                                     v
       +--------------------+              +--------------------------+
       |   CLAIM INTAKE     |              | REVIEW / DIGEST /        |
       | file / scan / chat|              | DASHBOARD / HISTORY /    |
       | voice / P6 export  |              | IMPACT PREVIEW           |
       +---------+----------+              +------------+-------------+
                 |                                      |
                 +------------------+-------------------+
                                    |
                                    v
                       +--------------------------+
                       |     BASELINE SCHEDULE    |
                       | Primavera / MSP CSV/XLSX |
                       +------------+-------------+
                                    |
                                    v
                       +--------------------------+
                       | SYSTEM PIPELINE           |
                       | 1. Intake                 |
                       | 2. Extraction             |
                       | 3. Matching               |
                       | 4. Checks                 |
                       | 5. Review                 |
                       | 6. Output                 |
                       +------------+-------------+
                                    |
                   +----------------+----------------+
                   |                                 |
                   v                                 v
             CSV Export                         P6 REST Adapter
                   |                                 |
                   v                                 v
             Primavera/MSP                    Local Mock P6
```

## 4.2 Architecture characteristics

- One React/Vite frontend.
- One Python/FastAPI backend.
- Supabase PostgreSQL as the database.
- Supabase Auth for authentication.
- FAISS in memory for the active schedule's semantic index.
- No Kafka, Redis, Kubernetes, microservices, or distributed transaction layer.
- Local `docker-compose` deployment for the demo.
- Real P6 adapter request construction, but a local mock P6 server.
- Free/open-source or genuinely free-tier dependencies only.

---

# 5. Technology Stack

| Layer | Technology | Requirement |
|---|---|---|
| Frontend | React + TypeScript + Vite | Free |
| Data fetching | TanStack Query | Free |
| Backend | Python + FastAPI + Pydantic v2 | Free |
| Database | Supabase PostgreSQL | Free tier |
| Authentication | Supabase Auth | Free tier |
| Auth client | `@supabase/supabase-js` | Free |
| Backend Supabase client | `supabase-py` | Auth/database integration as specified |
| LLM extraction | Groq free tier | Default provider |
| LLM backup | Gemini free tier | Documented fallback |
| Embeddings | `sentence-transformers` / `all-MiniLM-L6-v2` | Local |
| Semantic search | FAISS | In-memory |
| Fuzzy matching | RapidFuzz | Local |
| Excel/CSV | pandas, openpyxl | Local |
| PDF | PyMuPDF | Local |
| OCR | pytesseract | Local |
| Voice | Browser Web Speech API | Default |
| Voice fallback | locally run `faster-whisper` / `whisper.cpp` | Optional |
| Image metadata | Pillow / exifread | Local |
| Audit | Python hashlib / SHA-256 | Local |
| HTTP adapter | Python HTTP client | Local |
| Demo deployment | docker-compose | Local |

### Cost rule

The default build must not require:

- OpenAI API billing
- Paid Whisper
- Paid vision LLM calls
- Paid cloud hosting
- Live enterprise P6 access

Groq is the default LLM provider. Gemini is the documented free-tier fallback.

---

# 6. Authentication and Roles

## 6.1 Roles

Exactly two application roles exist:

### `SITE_ENGINEER`

Can:

- Log in.
- Access Claim Intake.
- Submit files.
- Submit typed text.
- Submit voice-transcribed text.
- Submit scanned diary images.
- Submit P6/MSP progress exports.

Cannot:

- Access Supervisor review screens.
- Approve or edit claims.
- Access Supervisor-only dashboards/history/impact screens.

### `SUPERVISOR`

Can:

- Log in.
- Access Daily Digest.
- Access Review Workspace.
- Approve/edit/reject/hold claims.
- Access Dashboard.
- Access Activity History.
- Access Impact Preview.

The Supervisor does not use the Site Engineer intake screen in the intended UI flow.

## 6.2 Authentication rules

- Login uses Supabase Auth.
- There is no signup.
- There is no password-reset flow.
- Exactly two seeded demo accounts exist.
- `profiles.id` equals `auth.users.id`.
- Role is stored in `profiles.role`.
- Backend authorization is enforced by `shared/auth.py`.
- Frontend hiding/route gating is not the security boundary.
- Every frontend API request sends the Supabase JWT in the `Authorization` header.
- User identity must never be accepted as a free-form request-body field.

## 6.3 Auth API

```http
GET /api/v1/auth/me
```

Returns the authenticated user's identity/profile/role required by the frontend.

---

# 7. Core Processing Pipeline

A claim does not silently flow through every stage.

The frontend explicitly calls the stages in order.

## 7.1 Standard claim path

### Step 1 — Intake

```http
POST /api/v1/claims/file
```

or

```http
POST /api/v1/claims/text
```

Claim is created with status:

```text
EXTRACTED
```

### Step 2 — Matching

```http
POST /api/v1/claims/{event_id}/match
```

Status becomes:

```text
MATCHED
```

or

```text
UNMATCHED
```

### Step 3 — Checks

```http
POST /api/v1/claims/{event_id}/check
```

Accepts either `MATCHED` or `UNMATCHED`.

Possible result:

```text
VALIDATED
```

only for a matched claim with no flags, or:

```text
REVIEW_REQUIRED
```

for a flagged matched claim or any unmatched claim.

### Step 4 — Human decision

Supervisor chooses:

```text
APPROVE
EDIT
REJECT
HOLD
```

Every decision creates exactly one `planner_decisions` row.

### Step 5 — Approved actual update

For APPROVE/EDIT, M5's decision endpoint calls:

```python
upsert_approved_actual(...)
```

### Step 6 — Outputs

After the database write commits:

```text
approved_actuals
      |
      +--> CSV export
      |
      +--> P6RestAdapter
```

Adapter failures are logged and visible but do not roll back the approved actual.

---

# 8. Functional Features

## Feature 1 — Schedule Ingestion

**Owner:** M1

Upload a baseline schedule in supported P6/MSP CSV/XLSX form.

Canonical mapping:

| Source column | Canonical field |
|---|---|
| `L6 Task ID` | `activity_id` |
| `L5 Activity ID` | `wbs_code` |
| `Activity` | `activity_name` |
| `Discipline` | `discipline` |
| `Unit` | `uom` |
| `Planned Qty` | `planned_quantity` |
| `Baseline Start` | `planned_start` |
| `Baseline Finish` | `planned_finish` |
| `L1` + `L2` | `location` |

`asset_tag` is nullable because it is not present in the real source file.

The schedule import validates:

- required fields
- duplicate activity IDs
- empty IDs
- date format
- planned start <= planned finish
- non-negative quantity
- baseline percentage 0–100
- whitespace/empty-value normalization

The import is transactional.

Dependencies support:

```text
FS
SS
FF
SF
```

A dependency referencing a nonexistent activity or a self-dependency is rejected.

### Active FAISS index rule

Only one live FAISS index exists at a time.

Uploading a new schedule:

- Replaces the active in-memory FAISS index.
- Does not delete historical schedule rows from PostgreSQL.
- Makes older schedule versions unmatchable.
- Does not automatically rematch old claims.
- Keeps each claim's `schedule_id` immutable.

A future multi-project version may use one FAISS index per `schedule_id`; that is not part of this MVP.

---

## Feature 2 — Multi-format Claim Ingestion

**Owner:** M2

Accept:

- PDF
- XLSX
- CSV
- TXT
- optional evidence photo
- typed text
- voice-transcribed text

All routes are role-gated to `SITE_ENGINEER` in the intended production flow.

---

## Feature 3 — LLM Extraction

**Owner:** M2

Convert messy text into structured claim fields.

The extraction must identify, when available:

- activity
- discipline
- location
- asset tag
- quantity
- percentage complete
- event type
- event date
- claim mode
- action/description
- language

Supported event types:

```text
ACTUAL_START
ACTUAL_FINISH
PROGRESS_UPDATE
DELAY
BLOCKER
```

Start and finish are distinct events.

LLM responses are validated with Pydantic.

Malformed or missing optional values become `null`; the system should not crash because an extraction field is absent.

---

## Feature 4 — Conversational Typed Intake

**Owner:** M2 backend / M5 UI

Allow a Site Engineer to submit natural-language progress such as:

```text
Finished pouring concrete in Area C.
```

It must enter the same extraction/matching/check pipeline as other text claims.

---

## Feature 5 — Voice Input

**Owner:** M2 backend / M5 UI

Default:

```text
Browser Web Speech API
```

No paid Whisper API.

If needed, a local Whisper implementation may be used as a free fallback.

Voice ultimately becomes text and follows the same extraction pipeline.

---

## Feature 6 — Multi-language Support

**Owner:** M2

Input may be:

- English
- Hindi
- mixed English/Hindi

The model understands the input language but returns normalized structured fields in English where possible.

Detected language is stored when available.

---

## Feature 7 — Four-tier Matching

**Owner:** M3

### Tier 1 — EXACT_ID

If:

```text
reported_activity_id == schedule activity_id
```

confidence:

```text
1.00
```

P6/MSP schedule-export claims enter here because they already carry the real activity ID.

### Tier 2 — EXACT_ASSET

Exact asset-tag match.

Confidence range:

```text
0.80–0.95
```

depending on discipline/location agreement.

A hard discipline mismatch caps confidence at <= 0.40.

### Tier 3 — HYBRID_FALLBACK

Combine:

- semantic similarity from FAISS
- RapidFuzz text similarity

Approximately 50/50 composite weighting.

### Tier 4 — HARD_MISMATCH

Hard discipline or location conflicts override otherwise strong similarity.

Every candidate contains:

```text
supporting_signals[]
disqualifying_signals[]
```

The top three candidates are retained.

---

## Feature 8 — Unmatched Claim Flagging

**Owner:** M3

If the best candidate is below the recommended threshold of:

```text
0.50
```

the claim becomes:

```text
UNMATCHED
```

but candidate results are still retained.

An unmatched claim must never disappear.

M4 subsequently transitions an unmatched claim to:

```text
REVIEW_REQUIRED
```

so a Supervisor can resolve it.

---

## Feature 9 — Conflict Detection

**Owner:** M4

For cumulative percentage claims:

- Compare against recent claims for the same matched activity.
- Use a 7-day window.
- Flag if the difference exceeds 10 percentage points.
- The current claim is always included.
- Prior active assertions include:
  - APPROVED
  - EDITED
  - HOLD
  - VALIDATED
  - REVIEW_REQUIRED
- REJECTED claims are excluded.

Conflict checking does not apply to incremental quantity claims.

---

## Feature 10 — Physical / Logic Validation

**Owner:** M4

Check for:

- progress > 100%
- negative progress
- invalid quantities
- UOM mismatch
- out-of-sequence activity
- reopened completed activity
- other deterministic validation rules defined by the build plan

Validation flags do not hide the claim.

---

## Feature 11 — Evidence Metadata Checks

**Owner:** M4

For attached photos, inspect available metadata such as:

- timestamp
- GPS

Use:

- Pillow
- exifread
- deterministic GPS/time comparison

Full visual understanding of photo content is not required.

---

## Feature 12 — Human Review Workspace

**Owner:** M5

Supervisor-only.

Show:

- extracted claim
- source
- top-3 candidates
- confidence
- supporting signals
- disqualifying signals
- conflicts
- validation issues
- evidence metadata
- history needed for context

Actions:

```text
Approve
Edit
Reject
Hold
```

Every action requires a justification.

---

## Feature 13 — SHA-256 Audit Log

**Owner:** M4

Every planner decision produces a tamper-evident audit entry.

Audit fields include:

- entity
- entity ID
- action
- authenticated actor
- before state
- after state
- payload hash
- previous hash
- current hash
- timestamp

The current hash incorporates the previous hash, creating a chain.

---

## Feature 14 — CSV Export

**Owner:** M6 backend / M5 download UI

Endpoint:

```http
GET /api/v1/export/csv
```

Export columns:

```text
activity_id
actual_start
actual_finish
actual_pct_complete
actual_quantity
```

The export represents approved/edit decisions and approved actuals in a format suitable for downstream Primavera/MSP handling.

---

## Feature 15 — Delay-reason Dashboard

**Owner:** M6 backend / M5 UI

Endpoint:

```http
GET /api/v1/dashboard/delay-reasons
```

Aggregate:

```text
execution_events.delay_reason
```

across approved claims and return JSON suitable for frontend visualization.

---

## Feature 16 — Institutional Memory

**Owner:** M6 backend / M5 UI

Endpoint:

```http
GET /api/v1/dashboard/institutional-memory
```

Join:

```text
approved_actuals
+
schedule_activities
```

Provide planned vs. actual duration.

Filtering/grouping uses:

```text
discipline
```

There is no `activity_type` column.

This view provides reusable historical project knowledge.

---

## Feature 17 — Daily Digest / Bulk Review

**Owner:** M5

Endpoint:

```http
GET /api/v1/digest?date=...
```

Claims are grouped by day/discipline.

Bulk approval:

```http
POST /api/v1/digest/bulk-approve
```

Each bulk-approved claim creates its own decision and invokes the normal shared audit/upsert path.

Because `planner_decisions.justification` is required, bulk approval uses a standard justification such as:

```text
Bulk-approved: no open flags, confidence above threshold
```

Bulk processing is independent per claim.

Response:

```json
{
  "approved": ["event-id-1", "event-id-2"],
  "failed": [
    {
      "event_id": "event-id-3",
      "error": "..."
    }
  ]
}
```

A failed claim must not roll back successful claims.

---

## Feature 18 — Activity History

**Owner:** M6 backend / M5 UI

Endpoint:

```http
GET /api/v1/activities/{activity_id}/history
```

Return a chronological timeline containing:

- linked execution events
- source references
- planner decisions
- relevant claim/source information

---

## Feature 19 — Silent Activity Nudge

**Owner:** M4

Endpoint:

```http
GET /api/v1/alerts/silent-activities
```

Identify activities with no recent updates.

This is a review/monitoring signal, not an automatic schedule change.

---

## Feature 20 — Impact Preview

**Owner:** M6 backend / M5 UI

**Priority:** Stretch.

Endpoint:

```http
GET /api/v1/schedule/{activity_id}/impact-preview?delay_days=N
```

For an activity and hypothetical delay:

- inspect immediate successor dependencies
- use the `FS` relationship for the MVP ripple calculation
- return shifted earliest-start estimates

This is a one-level graph traversal, not a full CPM recalculation.

---

## Feature 21 — Scanned Diary / OCR Ingestion

**Owner:** M2

Use:

```text
pytesseract
```

as the default.

OCR is not required to be production-grade.

The OCR text then follows the same extraction pipeline.

---

## Feature 22 — P6/MSP Schedule-export Claims

**Owner:** M2 parsing / M3 direct matching

A subcontractor's P6/MSP progress export is treated as:

```text
claims
```

not as a new baseline schedule.

Because the file already carries real activity IDs, claims enter M3's EXACT_ID tier.

No LLM extraction is required for these structured rows.

They still pass through the checks stage.

---

## Feature 23 — Start/Finish Event Capture and Reconciliation

**Owner:** M2 extraction / M6 shared actuals

Start and finish are separate claims/events.

Example:

```text
START:
A1000 -> 2026-09-05

FINISH:
A1000 -> 2026-09-08
```

The approved actual record becomes:

```text
A1000
actual_start  = 2026-09-05
actual_finish = 2026-09-08
```

The second event updates the existing `(schedule_id, activity_id)` row instead of creating a disconnected actual record.

---

## Feature 24 — Granularity Rollup

**Owner:** M4

For:

```text
claim_mode = INCREMENTAL_QUANTITY
```

multiple small field reports contribute to the same activity.

Example:

```text
Joint 3 of 10 welded
Joint 4 of 10 welded
Joint 5 of 10 welded
```

Only claims whose latest decision is:

```text
APPROVE
EDIT
```

contribute to the approved quantity.

The quantity invariant is:

```text
approved_actuals.actual_quantity
=
sum(
  COALESCE(approved_qty, claimed_quantity)
)
for claims whose latest decision is APPROVE or EDIT
for the selected activity
```

The sum is divided by `planned_quantity` to derive activity-level percentage complete for the rollup view.

Rejected claims contribute zero.

Held/validated/review-required claims contribute zero until a later decision approves/edits them.

A HOLD-then-APPROVE sequence must count only the latest approved decision, not both decisions.

Duplicate incremental reports are not content-deduplicated; the decision/event identity controls contribution.

---

## Feature 25 — Lightweight Forecasting

**Owner:** M6 backend / M5 UI

Endpoint:

```http
GET /api/v1/dashboard/forecast?activity_id=...
```

or:

```http
GET /api/v1/dashboard/forecast?discipline=...
```

Calculate:

```text
actual duration / planned duration
```

for completed historical activities of the same discipline.

Take the average ratio and apply it to a current/upcoming activity.

This is intentionally:

- arithmetic
- explainable
- lightweight
- not a trained ML model

---

## Feature 26 — Auto-triggered CSV Export

**Owner:** M6 backend / M5 decision endpoint

Whenever an approval/edit causes an `approved_actuals` write:

```text
commit approved_actuals
        |
        +--> regenerate CSV
        |
        +--> invoke P6 adapter
```

CSV generation is not a scheduled background job.

It is triggered by the shared actual-upsert path.

---

## Feature 27 — P6 EPPM REST API Write-back Adapter

**Owner:** M6

The adapter is swappable.

### Canonical interface

```python
push_actual(
    activity_id: str,
    actual_start: date | None,
    actual_finish: date | None,
    actual_pct_complete: float | None,
    actual_quantity: float | None,
)
```

Both adapters receive these same five fields.

### CSVExportAdapter

Writes:

```text
activity_id
actual_start
actual_finish
actual_pct_complete
actual_quantity
```

### P6RestAdapter

Maps to the canonical P6 request:

```json
{
  "Id": "A1000",
  "StartDate": "2026-09-05",
  "FinishDate": "2026-09-08",
  "PercentComplete": 75
}
```

`actual_quantity` is intentionally dropped because P6 has no native equivalent field in this contract.

### Critical canonical rule

`ActualDuration` is **not** part of this v5 P6 payload.

The externally supplied:

```text
activity_id
```

is used directly as:

```text
P6 Id
```

No translation or UUID conversion occurs.

### Mock server

```http
POST /api/v1/mock-p6/activities/{activity_id}
```

The mock accepts the same request shape produced by `P6RestAdapter`.

The integration code must be production-shaped even though the live P6 endpoint and credentials are unavailable.

---

## Feature 28 — Login and Role-based Access

**Owner:** M5 UI + M6 shared auth

Seven intended screens:

1. Login
2. Claim Intake
3. Daily Digest
4. Review Workspace
5. Dashboard
6. Activity History
7. Impact Preview

Site Engineer:

```text
Login -> Claim Intake
```

Supervisor:

```text
Login -> Daily Digest
```

Unauthorized direct navigation redirects to the role's own landing page.

---

# 9. Data Model

PostgreSQL/Supabase is the source of truth.

## 9.1 `profiles`

```sql
profiles(
  id UUID PRIMARY KEY,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL
    CHECK (role IN ('SITE_ENGINEER', 'SUPERVISOR')),
  created_at TIMESTAMPTZ DEFAULT now()
)
```

`id` equals `auth.users.id`.

---

## 9.2 `schedules`

```sql
schedules(
  schedule_id TEXT PRIMARY KEY,
  project_name TEXT NOT NULL,
  data_date DATE,
  source_format TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
)
```

Allowed source-format examples:

```text
P6_CSV
MSP_XML
EXCEL
```

---

## 9.3 `schedule_activities`

```sql
schedule_activities(
  activity_id TEXT NOT NULL,
  schedule_id TEXT NOT NULL,
  activity_name TEXT NOT NULL,
  wbs_code TEXT,
  discipline TEXT NOT NULL,
  location TEXT NOT NULL,
  asset_tag TEXT,
  planned_start DATE NOT NULL,
  planned_finish DATE NOT NULL,
  planned_quantity REAL,
  uom TEXT,
  baseline_pct_complete REAL DEFAULT 0.0,
  PRIMARY KEY (schedule_id, activity_id)
)
```

---

## 9.4 `schedule_dependencies`

```sql
schedule_dependencies(
  dependency_id TEXT PRIMARY KEY,
  schedule_id TEXT NOT NULL,
  predecessor_activity_id TEXT NOT NULL,
  successor_activity_id TEXT NOT NULL,
  relationship_type TEXT DEFAULT 'FS'
)
```

Relationship types:

```text
FS
SS
FF
SF
```

---

## 9.5 `source_documents`

```sql
source_documents(
  document_id TEXT PRIMARY KEY,
  file_name TEXT NOT NULL,
  document_type TEXT,
  uploader_id UUID,
  file_hash TEXT NOT NULL,
  uploaded_at TIMESTAMPTZ DEFAULT now()
)
```

Document types include:

```text
DPR
MBOOK
CHAT_LOG
QC_INSPECTION
SUPERVISOR_NOTE
SCANNED_DIARY
SCHEDULE_EXPORT_PROGRESS
```

`uploader_id` refers to the authenticated Site Engineer in the current role model.

---

## 9.6 `execution_events`

Core fields:

```sql
execution_events(
  event_id TEXT PRIMARY KEY,
  document_id TEXT,
  schedule_id TEXT NOT NULL,
  event_date DATE NOT NULL,
  raw_claim_text TEXT NOT NULL,
  input_channel TEXT NOT NULL,
  language_detected TEXT,
  reported_activity_id TEXT,
  matched_activity_id TEXT,
  discipline TEXT,
  action TEXT,
  event_type TEXT,
  claim_mode TEXT,
  claimed_pct REAL,
  claimed_quantity REAL,
  claimed_uom TEXT,
  delay_reason TEXT,
  status TEXT
)
```

Input channels:

```text
FILE_UPLOAD
SCANNED_OCR
TYPED_TEXT
VOICE
SCHEDULE_EXPORT
```

Event types:

```text
ACTUAL_START
ACTUAL_FINISH
PROGRESS_UPDATE
DELAY
BLOCKER
```

Claim modes:

```text
CUMULATIVE_PCT
INCREMENTAL_QUANTITY
```

### Claim-mode invariant

`CUMULATIVE_PCT`:

```text
claimed_pct populated
claimed_quantity NULL
claimed_uom NULL
```

`INCREMENTAL_QUANTITY`:

```text
claimed_quantity populated
claimed_uom populated
claimed_pct NULL
```

---

# 10. Identifier Contract

All system-generated IDs are lowercase UUID4 strings generated in Python using:

```python
uuid.uuid4()
```

Do not switch system IDs to database-generated UUIDs.

System-generated IDs include:

```text
event_id
candidate_id
decision_id
actual_id
conflict_id
issue_id
dependency_id
document_id
reference_id
log_id
schedule_id
```

All of these are stored as `TEXT`.

## 10.1 `activity_id` exception

`activity_id` is externally supplied.

Example:

```text
A1000
```

It is:

- not generated
- not UUID-converted
- not hashed
- not renamed

The value remains identical through:

```text
P6/MSP source
  ->
schedule_activities.activity_id
  ->
execution_events.reported_activity_id
  ->
candidate_matches.activity_id
  ->
execution_events.matched_activity_id
  ->
planner_decisions.selected_activity_id
  ->
approved_actuals.activity_id
  ->
CSV/P6 export
```

This is essential to EXACT_ID matching and P6 interoperability.

## 10.2 Dates and timestamps

Dates:

```text
YYYY-MM-DD
```

Timestamps:

```text
ISO 8601 UTC
```

No Excel serial dates or locale-specific date strings remain in stored canonical fields.

---

# 11. Candidate Matching Data

```sql
candidate_matches(
  candidate_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  schedule_id TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  rank_order INTEGER CHECK (rank_order BETWEEN 1 AND 3),
  match_tier TEXT,
  composite_confidence REAL
    CHECK (composite_confidence BETWEEN 0.0 AND 1.0),
  semantic_score REAL,
  fuzzy_score REAL,
  location_score REAL,
  discipline_score REAL,
  supporting_signals TEXT,
  disqualifying_signals TEXT,
  UNIQUE (event_id, rank_order)
)
```

`supporting_signals` and `disqualifying_signals` are JSON arrays.

---

# 12. Conflict and Validation Data

## 12.1 `conflict_records`

```sql
conflict_records(
  conflict_id TEXT PRIMARY KEY,
  schedule_id TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  reporting_period DATE NOT NULL,
  event_id_a TEXT NOT NULL,
  event_id_b TEXT NOT NULL,
  value_a REAL NOT NULL,
  value_b REAL NOT NULL,
  variance_pct REAL NOT NULL,
  status TEXT DEFAULT 'OPEN'
)
```

Statuses:

```text
OPEN
RESOLVED
DISMISSED
```

## 12.2 `validation_issues`

```sql
validation_issues(
  issue_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  rule_code TEXT,
  severity TEXT,
  description TEXT NOT NULL
)
```

Rule codes include:

```text
VAL_OVER_100
VAL_NEGATIVE
VAL_UOM_MISMATCH
VAL_OUT_OF_SEQUENCE
VAL_EVIDENCE_MISMATCH
VAL_REOPENED_COMPLETED_ACTIVITY
VAL_LOW_MATCH_CONFIDENCE
```

Severity:

```text
WARNING
ERROR
```

---

# 13. Planner Decisions

```sql
planner_decisions(
  decision_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  selected_activity_id TEXT NOT NULL,
  action TEXT,
  approved_pct REAL,
  approved_qty REAL,
  planner_id UUID NOT NULL,
  justification TEXT NOT NULL,
  decided_at TIMESTAMPTZ DEFAULT now()
)
```

Actions:

```text
APPROVE
EDIT
REJECT
HOLD
```

`planner_id` references the authenticated Supervisor's profile.

Every submitted decision creates exactly one row.

Viewing, matching, or checking a claim does not create a planner decision.

---

# 14. Approved Actuals

```sql
approved_actuals(
  actual_id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  schedule_id TEXT NOT NULL,
  activity_id TEXT NOT NULL,
  actual_start DATE,
  actual_finish DATE,
  actual_pct_complete REAL
    CHECK (actual_pct_complete BETWEEN 0.0 AND 100.0),
  actual_quantity REAL,
  exported_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (schedule_id, activity_id)
)
```

There is exactly one approved-actual row per:

```text
(schedule_id, activity_id)
```

Start/finish/quantity events update that row.

---

# 15. `upsert_approved_actual()` Contract

M6 owns:

```python
upsert_approved_actual(
    schedule_id,
    activity_id,
    event_id,
    decision_id,
    **fields
)
```

## 15.1 Row behavior

If `(schedule_id, activity_id)` exists:

- update only fields supplied by the decision.

If it does not exist:

- insert a new row.

A finish decision must not erase an existing start date.

A start decision must not erase an existing finish date.

## 15.2 Cumulative percentage

For:

```text
CUMULATIVE_PCT
```

the approved percentage is replaced by the newly approved value.

It is not accumulated.

## 15.3 Incremental quantity

For:

```text
INCREMENTAL_QUANTITY
```

the quantity is recalculated from database source rows on every approval/edit.

It must never use:

```python
actual_quantity += claimed_quantity
```

The authoritative calculation uses the latest decision per event and counts only decisions whose action is:

```text
APPROVE
EDIT
```

The effective quantity is:

```text
COALESCE(planner_decisions.approved_qty,
         execution_events.claimed_quantity)
```

summed for the selected activity.

## 15.4 Post-commit behavior

After the `approved_actuals` database transaction commits:

```text
1. Generate/update CSV.
2. Call P6RestAdapter.
```

If either adapter fails:

- the approved actual remains committed
- the adapter failure is logged/visible
- no rollback occurs
- no distributed transaction is introduced
- no automatic retry queue is required

---

# 16. Decision and Review API Contracts

M5 owns the decision-writing endpoint:

```http
POST /api/v1/decisions
```

It records:

```text
APPROVE
EDIT
REJECT
HOLD
```

with justification.

For APPROVE/EDIT it calls:

```text
M4 audit function
+
M6 upsert_approved_actual()
```

M5 must use the shared functions rather than implementing duplicate versions.

---

# 17. M6 API Contract

M6 owns:

```http
GET /api/v1/export/csv

GET /api/v1/dashboard/delay-reasons

GET /api/v1/dashboard/institutional-memory

GET /api/v1/dashboard/forecast?activity_id=...

GET /api/v1/dashboard/forecast?discipline=...

GET /api/v1/activities/{activity_id}/history

GET /api/v1/schedule/{activity_id}/impact-preview?delay_days=N

POST /api/v1/mock-p6/activities/{activity_id}
```

M6 also owns the shared:

```text
backend/shared/actuals.py
backend/shared/auth.py
```

---

# 18. Complete API Inventory

## Authentication

```http
GET /api/v1/auth/me
```

## Schedule

```http
POST /api/v1/schedules
GET /api/v1/schedules
GET /api/v1/schedules/{schedule_id}
GET /api/v1/schedules/{schedule_id}/activities
GET /api/v1/schedules/{schedule_id}/activities/{activity_id}
GET /api/v1/schedules/{schedule_id}/dependencies
```

## Claims

```http
POST /api/v1/claims/file
POST /api/v1/claims/text
POST /api/v1/claims/schedule-export
GET /api/v1/claims/{event_id}
GET /api/v1/claims
POST /api/v1/claims/{event_id}/match
GET /api/v1/claims/{event_id}/candidates
POST /api/v1/claims/{event_id}/rematch
POST /api/v1/claims/{event_id}/check
GET /api/v1/claims/{event_id}/conflicts
GET /api/v1/claims/{event_id}/validation
GET /api/v1/activities/{activity_id}/rollup
```

## Decisions / digest

```http
POST /api/v1/decisions
GET /api/v1/digest?date=...
POST /api/v1/digest/bulk-approve
```

## Audit / alerts

```http
GET /api/v1/audit/{entity_id}
GET /api/v1/alerts/silent-activities
```

## M6 reporting/integration

```http
GET /api/v1/export/csv
GET /api/v1/dashboard/delay-reasons
GET /api/v1/dashboard/institutional-memory
GET /api/v1/dashboard/forecast?activity_id=...
GET /api/v1/dashboard/forecast?discipline=...
GET /api/v1/activities/{activity_id}/history
GET /api/v1/schedule/{activity_id}/impact-preview?delay_days=N
POST /api/v1/mock-p6/activities/{activity_id}
```

---

# 19. Status Ownership and State Machine

The claim status is owned by the pipeline stage responsible for that transition.

```text
M2:
        EXTRACTED

M3:
        EXTRACTED
            |
            +--> MATCHED
            |
            +--> UNMATCHED

M4:
        MATCHED
            |
            +--> VALIDATED
            |
            +--> REVIEW_REQUIRED

        UNMATCHED
            |
            +--> REVIEW_REQUIRED
```

Rules:

- M2 creates claims at `EXTRACTED`.
- M3 writes matching results.
- M4 writes validation/check results.
- Unmatched claims cannot become `VALIDATED`.
- A claim is eligible for the review queue only after the checks stage.
- No stage may silently overwrite another stage's status.

---

# 20. Source Provenance

Every claim must remain traceable to its source.

For files, source references may include:

- filename
- sheet
- row
- raw snippet

For typed/voice input:

- originating text
- input channel
- associated source/document metadata

For approved changes, the chain must remain navigable:

```text
source
  ->
execution_event
  ->
candidate match
  ->
validation/conflict
  ->
planner decision
  ->
approved_actual
  ->
CSV/P6 output
```

---

# 21. Synthetic Demo Data

Real OIL project data is not required/available.

The team must maintain canonical synthetic data.

## Required schedule

Must contain all six disciplines:

```text
CIVIL
PIPING
STATIC_ROTATING_EQUIPMENT
ELECTRICAL
INSTRUMENTATION
HSE
```

The source headers must follow the canonical schedule-source mapping.

## Required claims

At least 8–10 realistic field reports.

They must cover multiple disciplines.

## Required special cases

At least:

1. One scanned diary image.
2. One subcontractor P6/MSP progress export.
3. One activity with multiple incremental quantity claims.
4. Two conflicting reports for the same activity.
5. One guaranteed successful claim for the fallback demo.

---

# 22. Demo Flow

Target duration:

**3 minutes**

## Step 1 — Login as Site Engineer

Show:

- Login
- role-based routing
- Claim Intake only

## Step 2 — Submit field update

Type or speak a field update.

Show:

- extraction
- structured fields

## Step 3 — Matching

Show:

- top-3 candidates
- confidence
- supporting/disqualifying signals

## Step 4 — Conflict

Submit two conflicting reports.

Show:

- conflict detection
- review flag

## Step 5 — Switch role

Log out.

Log in as Supervisor.

Show:

- Daily Digest landing page
- Site Engineer-only screen is not in navigation

## Step 6 — Supervisor decision

Resolve the conflict and approve/edit.

Show:

```text
planner decision
     |
     +--> audit entry
     |
     +--> approved_actuals
     |
     +--> auto CSV regeneration
     |
     +--> P6 mock request
```

## Step 7 — Analytics

Show:

- delay-reason dashboard
- institutional-memory view
- lightweight forecast

## Step 8 — Optional

If time allows:

- scanned diary OCR
- P6/MSP progress export claim ingestion

The guaranteed path must always be prioritized over optional features.

---

# 23. Scope

## 23.1 MVP

Build:

```text
Features 1–19
Features 21–28
```

Feature 20 is stretch.

## 23.2 Stretch

```text
Feature 20 — Impact Preview
```

## 23.3 Explicitly out of scope

Do not build:

- full photo-content AI verification
- production-grade speech recognition
- full critical-path recalculation
- enterprise identity systems
- self-registration
- password reset
- more than two roles
- fine-grained per-activity permissions
- live P6/MSP server connection
- paid API integrations
- persistent per-schedule FAISS indexes
- automatic rematching of old claims after schedule replacement
- microservices
- Kafka
- Redis
- Kubernetes
- distributed transaction infrastructure

---

# 24. Performance Targets

## Schedule indexing

For a 500-activity schedule:

```text
parse -> embed -> FAISS index < 2 seconds
```

after the embedding model is already loaded.

The first cold model load may take longer and is excluded from this target.

---

# 25. M6 Responsibility — Detailed Execution Scope

M6 is backend-only and does not build UI.

## M6 owns

### Shared core

```text
backend/shared/auth.py
backend/shared/actuals.py
profiles schema addition
```

### Reporting/integration

```text
export.py
CSV export
delay-reason dashboard
institutional memory
activity history
impact preview
forecast
P6RestAdapter
CSVExportAdapter
mock P6 server
```

### Data

```text
canonical sample schedule
sample field reports
scanned diary sample
P6/MSP progress sample
six-discipline coverage
```

### Safety

```text
backend/smoke_test.py
.env.example
.gitignore verification
demo seed/fallback path
final integration pass
```

---

# 26. M6 Work Phases

## Phase 0 — PRD and contract freeze

- Use this PRD v5.
- Do not invent additional requirements.
- Treat the build plan as the implementation authority.

## Phase 1 — Repository inspection

Verify:

- current backend structure
- schema
- Supabase connection
- routers
- shared modules
- existing M1–M4 outputs
- current main branch state

No duplicate implementations.

## Phase 2 — First M6 PR

Implement:

```text
shared/auth.py
shared/actuals.py
profiles schema
```

This is the first M6 PR because M5 and M2 depend on these shared functions.

## Phase 3 — Export

Implement:

```text
export.py
GET /api/v1/export/csv
CSVExportAdapter
auto-trigger from actuals
```

## Phase 4 — Analytics

Implement:

```text
delay reasons
institutional memory
forecast
```

## Phase 5 — History

Implement:

```text
activity history
```

## Phase 6 — Impact Preview

Implement the one-level FS successor traversal.

## Phase 7 — P6 integration

Implement:

```text
PMISAdapter
P6RestAdapter
mock P6 endpoint
```

## Phase 8 — Synthetic data

Create/maintain:

```text
sample_data/schedule.csv
sample reports
sample scanned diary
sample P6/MSP export
```

## Phase 9 — Smoke test

Implement:

```text
backend/smoke_test.py
```

Minimum:

1. backend boots
2. router health checks pass
3. canonical schedule upload works
4. canonical claim submission works
5. claim reaches `MATCHED`

## Phase 10 — Demo safety net

Pre-seed and rehearse one complete known-good path.

The seed process must invoke the real schedule upload endpoint so the in-memory FAISS index is rebuilt.

Do not seed `schedule_activities` directly and assume matching will work.

---

# 27. Team Ownership Matrix

| # | Feature | Owner |
|---|---|---|
| 1 | Schedule ingestion | M1 |
| 2 | Multi-format claim ingestion | M2 |
| 3 | LLM extraction | M2 |
| 4 | Conversational typed intake | M2 backend / M5 UI |
| 5 | Voice input | M2 backend / M5 UI |
| 6 | Multi-language | M2 |
| 7 | 4-tier matching | M3 |
| 8 | Unmatched flagging | M3 |
| 9 | Conflict detection | M4 |
| 10 | Physical validation | M4 |
| 11 | Metadata evidence checks | M4 |
| 12 | Review workspace | M5 |
| 13 | SHA-256 audit | M4 |
| 14 | CSV export | M6 backend / M5 UI |
| 15 | Delay dashboard | M6 backend / M5 UI |
| 16 | Institutional memory | M6 backend / M5 UI |
| 17 | Daily digest / bulk review | M5 |
| 18 | Activity history | M6 backend / M5 UI |
| 19 | Silent activity nudge | M4 |
| 20 | Impact preview | M6 backend / M5 UI |
| 21 | Scanned diary/OCR | M2 |
| 22 | P6/MSP progress claims | M2 parsing / M3 matching |
| 23 | Start/finish reconciliation | M2 extraction / M6 shared upsert |
| 24 | Granularity rollup | M4 |
| 25 | Forecasting | M6 backend / M5 UI |
| 26 | Auto CSV on approval | M6 backend / M5 decision endpoint |
| 27 | P6 REST adapter | M6 |
| 28 | Login/RBAC | M5 UI / M6 shared auth |

---

# 28. Git and Branching Rules

## Branch naming

```text
feature/m1-schedule-ingestion
feature/m2-intake-extraction
feature/m3-matching
feature/m4-validation-audit
feature/m5-frontend
feature/m6-export-integration
```

## Rules

1. Never push directly to `main`.
2. Every change goes through a PR.
3. At least one other member reviews the PR.
4. Review is especially focused on schema/API contract drift.
5. Commit frequently in small units.
6. Do not create shared feature branches.
7. Do not edit another member's router.
8. M6 does not build frontend files.
9. Do not modify `main.py` or `models/schema.sql` during normal feature work except through agreed integration syncs.
10. Do not change existing shared schema shapes without flagging the team.
11. Run the smoke test after every merge to `main`.

---

# 29. Required Merge Order

The intended order is:

```text
M1 core PR
       +
M2 core PR
       |
       v
M3 PR
       |
       v
M4 PR
       |
       v
M6 FIRST PR
(shared/actuals.py
 + shared/auth.py
 + profiles)
       |
       +------------------+
       |                  |
       v                  v
M2 auth-gated final      M5 PR
       |                  |
       +--------+---------+
                |
                v
        M6 SECOND PR
        (export/dashboards/
         forecast/P6/etc.)
                |
                v
        Final integration
```

M5 does not need to wait for M6's second PR to merge.

---

# 30. Integration Syncs

## Sync 1

After M1 and M2 core PRs:

- M3 replaces mocks with real inputs.
- Verify contract compatibility.

## Sync 2

After M3:

- M4 replaces matching mocks with real M3 output.

## Sync 3

After M4 + M6 first PR:

- M5 wires:
  - audit
  - actuals
  - auth
- M2 replaces mocked auth with real role gate.

## Sync 4 — Final

After M5 + M6 second PR:

- M5 connects dashboard/history/impact screens.
- Entire team runs the demo on `main`.
- Use M6's pre-seeded safety-net path.

---

# 31. Secrets and Environment

M6 owns `.env.example`.

Never commit:

- real LLM API keys
- Supabase service secrets
- JWT secrets
- seeded passwords
- private credentials

Every secret is read from environment variables.

Example concept:

```text
LLM_API_KEY
SUPABASE_URL
SUPABASE_KEY
P6_MOCK_URL
```

Exact environment names must match the implemented repository contract.

`.env` must be in `.gitignore`.

The shared LLM key is distributed privately, never through GitHub.

No paid key is added without team approval.

---

# 32. FAISS Reliability Rule

FAISS is intentionally:

```text
in-memory
single active schedule
non-persistent
```

It is rebuilt whenever a schedule is uploaded.

It is not restored automatically from a persisted FAISS file.

Therefore:

- restarting the process destroys the index
- the database remains intact
- the demo seed process must re-upload the schedule through the real schedule endpoint
- the seed process must not bypass indexing by inserting schedule rows directly

This is a deliberate MVP architecture choice.

---

# 33. Error and Failure Semantics

## Intake failure

The claim remains at the last successful pipeline status.

The frontend must surface the failure.

## Matching failure

The claim does not silently advance.

## Check failure

The claim remains available for review.

## Unmatched claim

Becomes:

```text
REVIEW_REQUIRED
```

after M4's check stage.

## Decision failure

The decision is not treated as successful unless its transaction completes.

## Adapter failure

If `approved_actuals` has already committed:

```text
approval remains successful
adapter failure is logged
no rollback
```

## Bulk approval failure

Each claim is independent.

One failure does not roll back successful approvals.

---

# 34. Security Boundaries

The frontend is not the security boundary.

Backend enforcement is mandatory.

Examples:

- Site Engineer cannot call Supervisor-only decision endpoints.
- Supervisor identity comes from JWT/session.
- Planner identity cannot be supplied arbitrarily by the client.
- Intake identity comes from authenticated user context.
- Secrets never live in source code.
- Audit records store authenticated actor identity.
- Approved data is generated only through human decision flow.

---

# 35. Observability and Explainability

Every machine match should be explainable.

Candidates expose:

```text
match_tier
composite_confidence
semantic_score
fuzzy_score
location_score
discipline_score
supporting_signals
disqualifying_signals
```

The system should prefer:

```text
"why this matched"
```

over a bare confidence number.

The Supervisor must be able to understand why the system suggested an activity.

---

# 36. Problem Statement Traceability

| Problem requirement | Feature(s) |
|---|---|
| Ingest free-text daily reports | #2, #4 |
| Ingest spreadsheets | #2 |
| Ingest scanned diaries | #21 |
| Ingest P6/MSP exports as progress input | #22 |
| Extract actual start events | #3, #23 |
| Extract actual finish events | #3, #23 |
| Conversational/voice interface | #4, #5 |
| Handle terminology differences | #7 |
| Handle granularity differences | #7, #24 |
| Flag unmatched/new activities | #8 |
| Human approval before official update | #12, #28 |
| Auto-update internal approved actuals | #23, #26 |
| CSV feedback to PMIS | #14, #26 |
| P6 write-back integration | #27 |
| Confidence scoring | #7 |
| Audit trail | #13 |
| Clean discipline-tagged dataset | #3 and schema |
| All six disciplines | sample-data requirement |
| Live analytics | #15, #16 |
| Delay/risk discovery | #15, #16 |
| Forecasting | #25 |
| Institutional memory | #16 |
| Multiple input formats | #2, #21, #22 |
| Production-grade OCR/ASR | explicitly not required |

---

# 37. Acceptance Criteria

The system is considered MVP-complete when all of the following are true.

## Intake

- [ ] PDF/Excel/CSV/TXT claims can be ingested.
- [ ] Typed text can be ingested.
- [ ] Voice can be converted through browser-native Web Speech API.
- [ ] Scanned diary can pass through pytesseract.
- [ ] P6/MSP progress export can be parsed as claims.

## Extraction

- [ ] Structured extraction is validated by Pydantic.
- [ ] Start and finish events are separate.
- [ ] English/Hindi/mixed input is supported.
- [ ] Source provenance is stored.

## Matching

- [ ] EXACT_ID works.
- [ ] EXACT_ASSET works when asset tags exist.
- [ ] Hybrid semantic/fuzzy fallback works.
- [ ] Hard mismatches are respected.
- [ ] Top 3 candidates are retained.
- [ ] Supporting/disqualifying signals are returned.
- [ ] Low-confidence claims become UNMATCHED rather than disappearing.

## Checks

- [ ] Conflicts are detected for cumulative percentages.
- [ ] Rejected claims do not generate future conflicts.
- [ ] Physical/logic validation works.
- [ ] Evidence metadata checks work.
- [ ] Incremental quantity rollup works.
- [ ] Unmatched claims reach REVIEW_REQUIRED.

## Review

- [ ] Only authenticated Supervisor can approve/edit/reject/hold.
- [ ] Every decision creates one planner decision.
- [ ] Every decision has a justification.
- [ ] Audit chain is updated.

## Approved actuals

- [ ] Start and finish reconcile to one activity record.
- [ ] Cumulative percentage is replaced, not added.
- [ ] Incremental quantity is recalculated from source decisions.
- [ ] Latest decision per event is counted correctly.
- [ ] Approved actuals are unique by `(schedule_id, activity_id)`.

## Output

- [ ] CSV export works.
- [ ] CSV regenerates after approval.
- [ ] P6 adapter produces the canonical payload.
- [ ] P6 mock receives the request.
- [ ] Adapter failures do not undo approvals.

## Analytics

- [ ] Delay dashboard returns grouped data.
- [ ] Institutional-memory view returns planned vs actual duration.
- [ ] Forecast returns a historical-ratio estimate.
- [ ] Activity history returns a chronological evidence/decision trail.
- [ ] Impact preview works if included in the stretch build.

## Authentication

- [ ] Site Engineer login routes to Claim Intake.
- [ ] Supervisor login routes to Daily Digest.
- [ ] Backend role checks enforce permissions.
- [ ] No user can spoof planner identity.
- [ ] Exactly two seeded accounts are available for the demo.

## Demo safety

- [ ] Canonical sample schedule covers all six disciplines.
- [ ] Canonical claims cover multiple input types.
- [ ] Conflict example works.
- [ ] Granularity example works.
- [ ] Scan/OCR sample exists.
- [ ] P6/MSP progress sample exists.
- [ ] Guaranteed end-to-end demo path works.
- [ ] Smoke test passes after merges.

---

# 38. Definition of Done for the Entire Team

The project is ready for demonstration when:

```text
LOGIN
  ↓
ROLE ROUTING
  ↓
SITE ENGINEER INTAKE
  ↓
EXTRACTION
  ↓
MATCHING
  ↓
CHECKS
  ↓
SUPERVISOR REVIEW
  ↓
APPROVE / EDIT
  ↓
AUDIT
  ↓
APPROVED ACTUAL
  ↓
AUTO CSV
  ↓
P6 MOCK WRITE-BACK
  ↓
DASHBOARD
  ↓
HISTORY / FORECAST
```

can be demonstrated from a clean `main` branch using the canonical seeded data.

---

# 39. Final Product Positioning

The system is not positioned as an autonomous planner.

It is a **controlled intelligence layer** between unstructured field reality and structured project controls.

Its differentiators are:

1. **Multi-format field reality ingestion**
2. **Explainable schedule matching**
3. **Deterministic validation around probabilistic AI**
4. **Human-controlled approval**
5. **Start/finish reconciliation**
6. **Granularity-aware progress aggregation**
7. **Tamper-evident auditability**
8. **Automatic downstream export**
9. **Production-shaped P6 integration**
10. **Institutional memory and lightweight forecasting**
11. **Role-based accountability**
12. **Zero-cost hackathon implementation**

The system's fundamental promise remains:

> **No field report becomes an official schedule fact merely because AI understood it. AI extracts and proposes; deterministic rules challenge it; a human Supervisor decides; the system records exactly what happened.**

---

# Appendix A — Canonical M6 Deliverables

```text
backend/
├── shared/
│   ├── auth.py
│   └── actuals.py
│
├── export.py
├── smoke_test.py
└── mock_p6/            # implementation may use project structure
```

Additional:

```text
.env.example
sample_data/
├── schedule.csv
├── daily_reports/
├── scanned_diary/
└── p6_progress_export/
```

The exact repository layout may follow the existing project structure; the ownership and API contracts above must remain stable.

---

# Appendix B — Canonical M6 Adapter Contract

```python
class PMISAdapter:
    def push_actual(
        self,
        activity_id: str,
        actual_start: date | None,
        actual_finish: date | None,
        actual_pct_complete: float | None,
        actual_quantity: float | None,
    ):
        ...
```

Implementations:

```text
CSVExportAdapter
P6RestAdapter
```

Canonical P6 request:

```json
{
  "Id": "A1000",
  "StartDate": "2026-09-05",
  "FinishDate": "2026-09-08",
  "PercentComplete": 75
}
```

No `ActualDuration`.

---

# Appendix C — Canonical M6 Execution Order

```text
1. Freeze v5 PRD
2. Inspect repository
3. Inspect current schema and shared contracts
4. Implement shared/auth.py
5. Implement shared/actuals.py
6. Integrate profiles
7. Test first PR
8. Push first PR
9. Merge after M4 according to team order
10. Run smoke test
11. Build CSV export
12. Build auto-export
13. Build dashboards
14. Build institutional memory
15. Build forecast
16. Build history
17. Build impact preview
18. Build PMIS adapter interface
19. Build CSVExportAdapter
20. Build P6RestAdapter
21. Build mock P6 endpoint
22. Build/validate sample data
23. Build smoke test
24. Seed guaranteed demo path
25. Run final integration
26. Rehearse complete demo on main
```

---

# Appendix D — Authoritative Contradiction Resolutions

These decisions prevent the two PRDs from producing conflicting implementations.

| Topic | Final v5 rule |
|---|---|
| Database | Supabase PostgreSQL |
| Auth | Supabase Auth |
| Roles | SITE_ENGINEER, SUPERVISOR |
| LLM | Groq free tier by default |
| LLM backup | Gemini free tier |
| Voice | Browser Web Speech API |
| OCR | pytesseract |
| FAISS | single in-memory active index |
| Multi-project FAISS | future roadmap, not MVP |
| P6 live server | unavailable; local mock |
| P6 adapter | real request-building code |
| P6 canonical fields | Id, StartDate, FinishDate, PercentComplete |
| P6 quantity | dropped from P6 payload |
| P6 ActualDuration | **not used** |
| Activity ID | source-provided string, unchanged |
| System IDs | Python UUID4 strings stored as TEXT |
| Approved actuals | one row per `(schedule_id, activity_id)` |
| Cumulative percentage | overwrite |
| Incremental quantity | recalculate from source decisions |
| Adapter failure | non-blocking, no rollback |
| UI ownership | M5 owns all UI |
| M6 UI | none |
| Impact preview | stretch |
| Paid APIs | prohibited in default build |
| Live P6 credentials | not required |
| Demo deployment | local docker-compose |

---

## End of PRD v5
