# SIH26122 --- Full Build Plan & Team Task Division v6

**Problem Statement:** SIH26122 --- Oil India Limited --- Smart
Automation\
**Version:** 6.0\
**Purpose:** Implementation plan combining the previous 28-feature team
build plan, the current codebase state, Features 29--35, stabilization
fixes, multilingual static/dynamic translation, and the five mandatory
algorithm corrections.

> **Ownership rule:** Each member keeps the work they already owned
> wherever possible. New work is assigned to the member who owns the
> closest existing module/domain so the team does not create
> cross-module ownership conflicts.

------------------------------------------------------------------------

# 1. Shared Context

## Product

The system ingests messy field-progress evidence, extracts structured
claims, matches claims to the baseline schedule, checks them, requires
human Supervisor approval, and produces auditable approved actuals plus
analytics and downstream outputs.

## Core principle

``` text
Field report = CLAIM
AI = ASSISTANT
Rules = VALIDATION
Supervisor = AUTHORITY
Audit = TRACEABILITY
```

Nothing becomes official project progress until a Supervisor decision is
recorded.

------------------------------------------------------------------------

# 2. Existing Architecture --- Preserve

``` text
Frontend
  React + TypeScript + Vite
  TanStack Query
  i18n
  role-based routing

Backend
  Python + FastAPI
  Pydantic v2

Database
  Supabase PostgreSQL

Auth
  Supabase Auth

Matching
  sentence-transformers
  FAISS
  RapidFuzz

Parsing
  pandas
  openpyxl
  PyMuPDF
  native P6 XER parser
  tabular extraction
  pytesseract

LLM
  shared provider client
  Groq primary
  Gemini fallback

Outputs
  CSV
  P6 REST adapter
  local P6 mock
```

Do not replace this architecture with microservices, Kafka, Redis or
Kubernetes.

------------------------------------------------------------------------

# 3. Existing Ownership --- Retain

  ---------------------------------------------------------------------
  Member                             Existing responsibility
  ---------------------------------- ----------------------------------
  M1                                 Schedule ingestion, dependency
                                     parsing, schedule indexing

  M2                                 Claim ingestion, LLM extraction,
                                     typed/voice intake backend,
                                     language support, OCR,
                                     schedule-export parsing

  M3                                 Four-tier matching, unmatched
                                     handling, direct matching for
                                     schedule exports

  M4                                 Conflict detection, physical/logic
                                     validation, metadata evidence,
                                     audit, silent-activity logic,
                                     granularity rollup

  M5                                 Entire frontend, login UI, review
                                     UI, digest UI, dashboard UI,
                                     history UI, impact UI, decision
                                     endpoint

  M6                                 Actuals shared function, auth
                                     shared function, exports,
                                     dashboards, history backend,
                                     forecasting, impact backend, P6
                                     adapter, smoke test, demo
                                     safety/data
  ---------------------------------------------------------------------

This is the ownership to follow for v6. New work is assigned to the closest existing owner rather than creating a new ownership boundary.

------------------------------------------------------------------------

# 4. Member 1 --- Schedule Ingestion, Dependencies & WBS Data

## Previous work --- retain

### A. Schedule ingestion

Continue owning:

-   P6/MSP CSV/XLSX parsing
-   native `.xer` parsing integration
-   canonical field mapping
-   date normalization
-   required-field validation
-   duplicate activity detection
-   quantity validation
-   baseline percentage validation
-   transactional schedule import
-   schedule dependency import
-   FAISS index construction

### B. Dependency parsing

Retain:

``` text
FS
SS
FF
SF
```

validation.

Reject:

-   nonexistent predecessor
-   nonexistent successor
-   self-dependency

### C. Active FAISS rule

Retain the existing single active in-memory index.

Do not implement persistent per-schedule indexes in v6.

Do not automatically rematch old claims after schedule upload.

------------------------------------------------------------------------

## New v6 work

### Task M1-1 --- Add schedule support for algorithm metadata

Coordinate schema changes for:

``` text
schedule_dependencies.lag_days
schedule_activities.total_float
schedule_activities.is_critical
```

Requirements:

-   import values if reliably available in the source
-   normalize values
-   do not invent missing schedule facts
-   document fallback when unavailable

If `free_float` is not available reliably, do not add it merely for
appearance.

### Task M1-2 --- WBS tree endpoint

Implement:

``` http
GET /api/v1/schedules/{schedule_id}/wbs-tree
```

Return:

``` text
wbs_code
children[]
    activity_id
    activity_name
    planned_quantity
    uom
    planned_start
    planned_finish
```

A WBS code with only one child is not a decomposition candidate.

### Task M1-3 --- WBS data support

Ensure M3 can determine:

-   sibling activities
-   child WBS membership
-   planned quantity
-   UOM
-   planned dates
-   dependency relationships
-   criticality/float where available

### Task M1-4 --- Benchmark schedule

Maintain the canonical 45-activity benchmark.

Ensure all six disciplines exist:

``` text
CIVIL
PIPING
STATIC_ROTATING_EQUIPMENT
ELECTRICAL
INSTRUMENTATION
HSE
```

Add/retain WBS/dependency cases required by the v6 tests.

------------------------------------------------------------------------

## M1 APIs

``` http
POST /api/v1/schedules
GET /api/v1/schedules
GET /api/v1/schedules/{schedule_id}
GET /api/v1/schedules/{schedule_id}/activities
GET /api/v1/schedules/{schedule_id}/activities/{activity_id}
GET /api/v1/schedules/{schedule_id}/dependencies
GET /api/v1/schedules/{schedule_id}/wbs-tree
```

------------------------------------------------------------------------

## M1 Definition of Done

-   [ ] Existing schedule ingestion regression tests pass.
-   [ ] XER parser still works.
-   [ ] Transactional import still works.
-   [ ] All four dependency types remain supported.
-   [ ] lag/float/criticality values are available when source supports
    them.
-   [ ] WBS tree endpoint works.
-   [ ] 45-activity benchmark remains valid.
-   [ ] No matching logic is moved into M1.

------------------------------------------------------------------------

# 5. Member 2 --- Intake, Extraction, Language, Translation & Copilot

## Previous work --- retain

Continue owning:

-   PDF/XLSX/CSV/TXT intake
-   typed text
-   browser voice-transcribed text
-   evidence photo handling
-   scanned diary/OCR
-   P6/MSP progress-file parsing
-   LLM extraction
-   Pydantic extraction schema
-   language detection
-   source references
-   batch claim extraction
-   source document hashing

------------------------------------------------------------------------

## New v6 work

### Task M2-1 --- Fix LLM provider configuration

Current audit issue:

``` text
llama-3.3-70b-versatile -> 404
```

Required:

-   replace with active Groq model or documented Gemini fallback
-   test live extraction
-   keep provider configurable
-   do not hardcode a provider in multiple routers

### Task M2-2 --- Create shared LLM client

New file:

``` text
backend/shared/llm_client.py
```

Stable interface, for example:

``` python
call_llm(messages: list[dict]) -> str
```

The exact signature must be agreed once and then treated as a shared
contract.

It reads:

``` text
LLM_PROVIDER
LLM_API_KEY
LLM_MODEL
```

M2 uses it for:

-   extraction
-   clarification
-   future dynamic translation

M6 imports it for Feature 35.

No second Groq/Gemini implementation is allowed.

------------------------------------------------------------------------

## Task M2-3 --- Adaptive Field Copilot

Feature 29.

After extraction check only:

``` text
event_type
discipline
claimed_pct OR claimed_quantity
```

If missing:

``` text
clarification_status = PENDING
clarification_question = one question
```

Question must be:

-   specific
-   single
-   in detected claim language
-   not a generic "provide more information"

Do not trigger on missing:

``` text
asset_tag
location
delay_reason
```

### New endpoint

``` http
POST /api/v1/claims/{event_id}/clarify
```

Behavior:

1.  read original raw claim
2.  append/merge free-text answer
3.  rerun same extraction schema
4.  validate with Pydantic
5.  set `ANSWERED`
6.  update provenance
7.  return claim ready for `/match`

Never loop indefinitely.

------------------------------------------------------------------------

## Task M2-4 --- Field provenance at intake

For each populated field:

``` text
LLM extraction -> AI_EXTRACTED
schedule export -> SCHEDULE_AUTO_FILLED
```

Do not invent provenance for null values.

Do not set `SUPERVISOR_EDITED`; M5 owns that.

------------------------------------------------------------------------

## Task M2-5 --- Static multilingual support documentation

Confirm and preserve:

``` text
English
Hindi
Telugu
```

through existing i18n dictionaries.

Do not replace the existing i18n system.

------------------------------------------------------------------------

## Task M2-6 --- Dynamic translation foundation

Build runtime translation support through the shared LLM client.

Target:

-   clarification questions
-   AI summaries
-   Ask Why explanations
-   validation/evidence explanations when runtime translation is
    requested
-   selected dynamic content

Rules:

-   preserve canonical source text
-   translate for display
-   cache only if useful
-   fallback to original text on failure
-   never block approval solely because translation failed

------------------------------------------------------------------------

## Task M2-7 --- Tesseract setup

Document/package the Windows Tesseract binary path so Feature 21 works
reliably on the demo machine.

------------------------------------------------------------------------

## M2 APIs

``` http
POST /api/v1/claims/file
POST /api/v1/claims/text
POST /api/v1/claims/schedule-export
GET /api/v1/claims/{event_id}
GET /api/v1/claims
POST /api/v1/claims/{event_id}/clarify
```

------------------------------------------------------------------------

## M2 Definition of Done

-   [ ] Groq/Gemini live extraction works.
-   [ ] Shared LLM client is used everywhere.
-   [ ] No ad-hoc LLM calls remain.
-   [ ] Batch extraction remains working.
-   [ ] XER/tabular ingestion remains working.
-   [ ] English/Hindi/Telugu static UI contract is preserved.
-   [ ] Dynamic translation has a safe fallback.
-   [ ] Clarification asks exactly one question.
-   [ ] Clarification uses `language_detected`.
-   [ ] Provenance is written correctly.
-   [ ] OCR works on canonical sample.

------------------------------------------------------------------------

# 6. Member 3 --- Matching & WBS Decomposition

## Previous work --- retain

Continue owning:

-   EXACT_ID
-   EXACT_ASSET
-   HYBRID_FALLBACK
-   HARD_MISMATCH
-   top-3 candidate retention
-   confidence calculation
-   supporting/disqualifying signals
-   unmatched handling
-   schedule-export direct matching
-   `/match`
-   `/rematch`

------------------------------------------------------------------------

## New v6 work

### Task M3-1 --- Matching calibration review

Current implementation:

``` text
semantic 50%
fuzzy 25%
location 15%
discipline 10%
```

and current code cutoff:

``` text
> 0.40
```

Do not change these blindly.

Use the 45-activity benchmark to evaluate:

-   false positives
-   false negatives
-   identical activity names in different locations
-   discipline mismatches
-   WBS-level claims
-   location aliases

Then agree the v6 threshold and weights with M1/M4.

### Task M3-2 --- Strong contextual gating

Location and discipline conflicts must not be diluted by a strong
semantic score.

Where possible:

``` text
hard contextual mismatch
    -> disqualify/cap
```

rather than simply adding a fractional score.

### Task M3-3 --- WBS Granularity Bridge

During `/match`:

1.  run normal matching
2.  inspect top candidate WBS
3.  get siblings from M1's WBS tree
4.  detect whether claim is broad
5.  if broad and WBS has 2+ eligible children, split instead of forcing
    one activity

------------------------------------------------------------------------

## v6 WBS split algorithm

Inputs:

-   sibling activities
-   planned quantity
-   UOM
-   planned dates
-   approved actuals
-   dependency order
-   claim mode
-   claim value
-   claim wording
-   asset/location specificity

Rules:

1.  completed activity -\> 0 allocation
2.  future/ineligible activity -\> 0 allocation
3.  active uncompleted sibling -\> eligible
4.  dependency order controls waterfall when sibling dependencies exist
5.  use quantity weighting only when UOM is compatible
6.  otherwise use context-aware equal/headroom allocation
7.  preserve sum:

``` text
sum(split_pct) = 1.0 ± 0.0001
```

8.  write one split row per sibling
9.  set:

``` text
matched_activity_id = NULL
status = MATCHED
```

------------------------------------------------------------------------

## M3 APIs

``` http
POST /api/v1/claims/{event_id}/match
GET /api/v1/claims/{event_id}/candidates
POST /api/v1/claims/{event_id}/rematch
GET /api/v1/claims/{event_id}/splits
PATCH /api/v1/claims/{event_id}/splits
```

PATCH is Supervisor-only.

------------------------------------------------------------------------

## M3 Definition of Done

-   [ ] Existing four-tier matching passes.
-   [ ] Threshold is benchmark-calibrated.
-   [ ] hard mismatches remain hard guards.
-   [ ] top-3 candidates remain available for normal matches.
-   [ ] WBS split and normal match are XOR.
-   [ ] completed/future siblings do not receive invalid allocation.
-   [ ] UOM mismatch cannot create meaningless WBS quantity weights.
-   [ ] WBS tests pass.

------------------------------------------------------------------------

# 7. Member 4 --- Checks, Algorithms, Evidence, Priority & Audit

## Previous work --- retain

Continue owning:

-   conflict detection
-   physical validation
-   logical validation
-   evidence metadata
-   silent activity nudge
-   granularity reconciliation
-   audit log
-   validation issue records

------------------------------------------------------------------------

# 7A. Mandatory Algorithm Fix A2 --- Out-of-Sequence

### Current bug

The old implementation mainly checks `ACTUAL_START` and assumes FS-style
completion.

### New task

Refactor the sequence validator so it understands:

``` text
FS
SS
FF
SF where supported
```

and checks both:

``` text
ACTUAL_START
PROGRESS_UPDATE when successor is unstarted
```

Rules:

### FS

Unstarted successor cannot legitimately start/progress before
predecessor completion.

### SS

Successor may start once predecessor has started/progressed.

### FF

Successor finish cannot precede predecessor finish.

### Established in-progress successor

Do not re-trigger a sequence warning for every ordinary progress update.

### Tests

``` text
TC-SEQ-01
TC-SEQ-02
TC-SEQ-03
TC-SEQ-04
```

------------------------------------------------------------------------

# 7B. Mandatory Algorithm Fix A4 --- Directional Conflict Detection

Replace:

``` text
abs(valueA - valueB) > 10
```

over every claim in a symmetric 7-day window.

Use:

### Same date

Different cumulative claims on same date/shift:

``` text
SAME_DATE_DISAGREEMENT
```

if beyond tolerance.

### Later date

Higher/equal cumulative percentage:

``` text
normal progression
```

Lower percentage:

``` text
PROGRESS_REGRESSION
```

unless justified by rework/reset context.

### Incremental quantity

Check:

-   negative

-   planned quantity

-   implausible accumulation

-   deterministic duplicate physical contribution where identifiable

Do not blindly treat all 7-day differences as conflicts.

Tests:

``` text
TC-CONF-01 ... TC-CONF-04
```

------------------------------------------------------------------------

# 7C. Feature 30 --- WBS Reconciliation

For every split:

``` text
contribution = claimed_pct × split_pct
```

or:

``` text
contribution = claimed_quantity × split_pct
```

Run the same validation and approved-actual invariants per child.

A split child that violates sequence eligibility must surface a
validation issue.

------------------------------------------------------------------------

# 7D. Feature 31 --- Evidence Fusion

During `/check`:

1.  find related events
2.  use same activity or split activity
3.  compare different document types
4.  normalize time/metric context
5.  classify:
    -   `CORROBORATES`
    -   `CONTRADICTS`
6.  write `evidence_links`

Keep:

``` text
conflict_records != evidence_links
```

The two mechanisms answer different questions.

Evidence links should carry:

``` text
confidence
rationale
```

Do not auto-approve based on corroboration.

------------------------------------------------------------------------

# 7E. Mandatory Algorithm Fix A5 --- Smart Review Priority

Replace old additive score.

### Base severity

``` text
critical physical/sequence = 100
conflict/contradiction      = 70
unmatched/WBS ambiguity     = 40
administrative warnings     = min(25, 10*n)
routine                      = 5
```

### Criticality

``` text
float <= 0   -> 2.0x
float <= 5   -> 1.5x
else         -> 1.0x
```

### Aging

``` text
min(30, 6*ln(1+hours))
```

### Final

``` text
score = base * multiplier + aging
```

Critical sequence error on critical path:

``` text
100 * 2 = 200
```

before aging.

Minor warnings cannot exceed:

``` text
25 * 2 + 30 = 80
```

even at maximum criticality/aging.

Write:

``` text
priority_score
priority_reasons
```

------------------------------------------------------------------------

# 7F. Audit

Retain SHA-256 chain.

Ensure new decision/review metadata remains auditable where appropriate.

------------------------------------------------------------------------

## M4 APIs

``` http
POST /api/v1/claims/{event_id}/check
GET /api/v1/claims/{event_id}/conflicts
GET /api/v1/claims/{event_id}/validation
GET /api/v1/claims/{event_id}/evidence
GET /api/v1/review-queue?sort=priority
GET /api/v1/alerts/silent-activities
GET /api/v1/audit/{entity_id}
GET /api/v1/activities/{activity_id}/rollup
```

------------------------------------------------------------------------

## M4 Definition of Done

-   [ ] Sequence tests pass.
-   [ ] Conflict directional tests pass.
-   [ ] WBS child reconciliation works.
-   [ ] Evidence fusion works.
-   [ ] conflict/evidence remain separate.
-   [ ] priority inversion tests pass.
-   [ ] audit chain remains valid.
-   [ ] unmatched claims still reach REVIEW_REQUIRED.
-   [ ] existing physical validation tests still pass.

------------------------------------------------------------------------

# 8. Member 5 --- Sole Frontend Owner + Decision Endpoint

## Previous work --- retain

Continue owning all frontend code:

``` text
Login
Claim Intake
Review Workspace
Daily Digest
Dashboard
Activity History
Impact Preview
```

and:

``` text
frontend/src/api.ts
auth/session
routing
layout
shared UI
```

Continue owning:

``` http
POST /api/v1/decisions
```

and call:

``` text
write_audit_log()
upsert_approved_actual()
```

------------------------------------------------------------------------

# 8A. Feature 29 UI --- Clarification

After intake:

``` text
clarification_status == PENDING
```

UI must:

1.  show the single question
2.  keep the original claim in the thread
3.  collect the answer
4.  call `/clarify`
5.  do not call `/match` before clarification is answered
6.  resume normal `/match` -\> `/check`

No duplicate claim should be created merely to answer a clarification.

------------------------------------------------------------------------

# 8B. Feature 33 UI --- Provenance

Each extracted field shows a chip:

``` text
AI Extracted
Schedule Auto-Filled
Engineer Entered
Supervisor Edited
```

Only display values actually present.

------------------------------------------------------------------------

# 8C. Feature 30 UI --- Split Editor

If:

``` text
matched_activity_id == null
AND split rows exist
```

show sibling activities instead of top-3 radio candidates.

Allow Supervisor to edit:

``` text
split_pct
```

and call:

``` http
PATCH /claims/{event_id}/splits
```

Touched rows become:

``` text
MANUAL
```

------------------------------------------------------------------------

# 8D. Feature 31 UI --- Evidence Panel

Separate:

``` text
CORROBORATES
CONTRADICTS
```

Show:

-   source/channel
-   confidence
-   rationale
-   relevant claim values/dates

Do not mix evidence links with same-channel conflict records.

------------------------------------------------------------------------

# 8E. Feature 32 UI --- Priority Queue

Default:

``` http
GET /review-queue?sort=priority
```

Show:

-   priority score
-   reasons
-   critical/near-critical indication
-   escalation badge when applicable

Do not expose raw mathematical clutter to the user unless useful; show
concise explanations.

------------------------------------------------------------------------

# 8F. Feature 34 UI --- Ask Why

Add a `Why?` button next to:

-   validation issue
-   conflict
-   evidence contradiction
-   relevant impact flag

Call:

``` http
GET /graph/activity/{activity_id}?depth=1
```

On clicking a newly revealed node:

``` text
depth = N+1
root = selected node
```

Render inline.

------------------------------------------------------------------------

# 8G. Feature 35 UI

Create:

``` text
frontend/src/screens/AIExecutionSummary.tsx
```

Provide:

-   Last 7 Days
-   This Month
-   custom date range if easy
-   six-discipline selector
-   All Disciplines
-   generated paragraph
-   language/display translation

Supervisor only.

------------------------------------------------------------------------

# 8H. Dynamic Translation UI

The existing static i18n selector remains.

For dynamic text:

``` text
canonical content
    |
    v
runtime translation
    |
    v
display language
```

Never replace the stored canonical claim.

If translation fails:

``` text
show original
```

Do not block review.

------------------------------------------------------------------------

# 8I. Dashboard KPI Fix

Replace hardcoded:

``` text
Total Claims
Pending Review
Actuals Committed
Open Conflicts
```

with live backend/database counts.

The discipline chart must also be live.

------------------------------------------------------------------------

# 8J. Decision endpoint provenance behavior

When Supervisor chooses `EDIT`:

-   identify fields actually changed
-   set only those fields to `SUPERVISOR_EDITED`
-   preserve provenance on untouched fields

For `APPROVE` with no field changes, do not mark fields as edited.

------------------------------------------------------------------------

## M5 Definition of Done

-   [ ] Existing pages still work.
-   [ ] Role routing works.
-   [ ] Clarification flow works.
-   [ ] Provenance chips work.
-   [ ] WBS split editor works.
-   [ ] Evidence groups work.
-   [ ] Priority queue works.
-   [ ] Ask Why drill-down works.
-   [ ] Execution Summary screen works.
-   [ ] Dashboard KPIs are live.
-   [ ] static En/Hi/Te selector works.
-   [ ] dynamic content translation works/falls back safely.
-   [ ] decision endpoint preserves audit/actuals contracts.

------------------------------------------------------------------------

# 9. Member 6 --- Shared Core, Outputs, Analytics, Impact, Graph & Summary

## Previous work --- retain

Continue owning:

-   `shared/actuals.py`
-   `shared/auth.py`
-   `routers/auth.py`
-   `export.py`
-   CSV export
-   dashboards
-   institutional memory
-   history
-   forecasting
-   impact preview
-   P6 adapter
-   local mock P6
-   smoke test
-   demo safety net
-   canonical synthetic data support

------------------------------------------------------------------------

# 9A. Shared actuals

Do not break:

``` text
one approved_actual row per schedule/activity
```

Maintain:

-   start/finish merging
-   cumulative percentage replacement
-   incremental quantity recalculation
-   latest decision per event
-   APPROVE/EDIT-only contribution

------------------------------------------------------------------------

# 9B. Auth

Retain:

``` text
get_current_user()
require_role()
GET /auth/me
```

Verify Supabase JWT and profile role.

Also coordinate with the audit finding that schedule creation and
intermediate pipeline routes need appropriate network/security
treatment.

The original product flow may still trigger `/match` and `/check`
automatically, but the team should ensure those routes cannot be exposed
as uncontrolled unauthenticated mutation endpoints in the deployed demo.

------------------------------------------------------------------------

# 9C. Mandatory Algorithm Fix A1 --- Impact Preview

Replace the old:

``` text
one-hop FS-only
```

logic.

### Inputs

-   target activity
-   hypothetical delay
-   dependencies
-   relationship type
-   lag/lead
-   planned dates
-   total float
-   criticality
-   approved actual state

### Stage 1 --- successor discovery

Find direct successors across:

``` text
FS
SS
FF
SF
```

### Stage 2 --- predecessor control

For each successor:

-   gather all predecessors
-   calculate relationship-specific constraints
-   determine controlling predecessor

### Stage 3 --- execution-state gating

``` text
completed -> no shift
in progress -> remaining-duration-aware
not started -> normal constraint analysis
```

### Stage 4 --- float absorption

``` text
slippage = max(0, constrained_date - planned_date)
net_delay = max(0, slippage - total_float)
```

### Stage 5 --- bounded propagation

Propagate only positive net delay.

Stop when:

-   no net delay
-   maximum configured depth
-   milestone/output boundary reached

### Classifications

``` text
ABSORBED_BY_FLOAT
CRITICAL_PATH_SLIP
EXECUTION_IN_PROGRESS
NON_CONTROLLING_PREDECESSOR
ALREADY_COMPLETED
NO_IMPACT
```

### Endpoint

Keep:

``` http
GET /api/v1/schedule/{activity_id}/impact-preview?delay_days=N
```

------------------------------------------------------------------------

# 9D. Feature 31 --- Graph API

New:

``` text
routers/graph.py
```

Endpoint:

``` http
GET /api/v1/graph/activity/{activity_id}?depth=N
```

Join at query time:

``` text
execution_events
source_documents
candidate_matches
conflict_records
validation_issues
planner_decisions
evidence_links
schedule_dependencies
```

Return:

``` json
{
  "nodes": [],
  "edges": []
}
```

No materialized graph table.

------------------------------------------------------------------------

# 9E. Feature 34 --- Ask Why backend

Reuse graph traversal.

Depth 1:

``` text
immediate cause/context
```

Deeper levels:

``` text
root = selected node
depth = N+1
```

Where data supports it, include deterministic causal context:

-   predecessor
-   delay reason
-   date
-   float
-   sequence issue
-   evidence relationship

Do not invent root causes.

------------------------------------------------------------------------

# 9F. Feature 35 --- AI Execution Summary

New:

``` text
routers/reports.py
```

Endpoint:

``` http
GET /api/v1/reports/execution-summary?start=...&end=...&discipline=...
```

Aggregate deterministically:

1.  activities with events
2.  approved progress delta
3.  claim counts by status
4.  conflicts opened
5.  conflicts resolved
6.  activities trailing historical pace

Then import:

``` python
from shared.llm_client import call_llm
```

Send aggregate numbers only.

LLM must not calculate or introduce new numbers.

Optional cache:

``` text
execution_summaries
```

Key:

``` text
period_start
period_end
discipline
```

------------------------------------------------------------------------

# 9G. Dashboard live-data fix

Replace hardcoded KPI constants with queries.

Minimum live KPIs:

``` text
total claims
pending/review claims
approved actuals
open conflicts
```

Discipline chart must be live.

Keep existing delay dashboard/institutional memory/forecast.

------------------------------------------------------------------------

# 9H. P6 adapter completion

Keep canonical:

``` python
push_actual(
    activity_id,
    actual_start,
    actual_finish,
    actual_pct_complete,
    actual_quantity,
)
```

P6 request:

``` json
{
  "Id": "A1000",
  "StartDate": "2026-09-05",
  "FinishDate": "2026-09-08",
  "PercentComplete": 75
}
```

Do not add:

``` text
ActualDuration
```

Enable the local mock URL in demo configuration.

------------------------------------------------------------------------

# 9I. Test/demo safety

Current test baseline from audit:

``` text
262 total
250 passed
12 failed
```

Known failures:

``` text
10 -> Groq model 404
1  -> XER sample byte expectation
1  -> JWKS mock key mismatch
```

M6 owns the integration/smoke layer; coordinate with M2/M5 for the root
fixes.

After stabilization, run:

-   full existing regression suite
-   five algorithm targeted tests
-   complete demo smoke test

------------------------------------------------------------------------

## M6 Definition of Done

-   [ ] actuals regression suite passes.
-   [ ] auth shared core passes.
-   [ ] live dashboards work.
-   [ ] impact algorithm passes TC-IMP tests.
-   [ ] graph endpoint works.
-   [ ] Ask Why drill-down data works.
-   [ ] execution summary works.
-   [ ] shared LLM client is imported, not duplicated.
-   [ ] P6 mock receives canonical payload.
-   [ ] adapter failure is non-blocking.
-   [ ] smoke test works from clean main.

------------------------------------------------------------------------

# 10. Shared Schema Changes

All schema changes require team notification before merge.

## Existing `execution_events` additions

``` sql
clarification_status TEXT DEFAULT 'NONE'
clarification_question TEXT
clarification_answer TEXT
field_provenance JSONB DEFAULT '{}'
priority_score REAL DEFAULT 0.0
priority_reasons TEXT
```

## New tables

``` sql
claim_activity_splits(...)
evidence_links(...)
execution_summaries(...)
```

## Algorithm support

``` sql
schedule_dependencies.lag_days
schedule_activities.total_float
schedule_activities.is_critical
```

Do not add free-float or other fields unless the source/import path can
support them.

------------------------------------------------------------------------

# 11. File Ownership

  File                           Owner
  ------------------------------ -----------------------
  `routers/schedules.py`         M1
  `routers/intake.py`            M2
  `routers/matching.py`          M3
  `routers/checks.py`            M4
  `routers/decisions.py`         M5
  `routers/export.py`            M6
  `routers/auth.py`              M6
  `routers/graph.py`             M6
  `routers/reports.py`           M6
  `shared/llm_client.py`         M2
  `shared/audit.py`              M4
  `shared/actuals.py`            M6
  `shared/auth.py`               M6
  `shared/schemas.py`            shared/additive
  `models/schema.sql`            shared/announce-first
  `requirements.txt`             shared/additive
  `frontend/*`                   M5
  `sample_data/schedule*`        M1 + M6
  `sample_data/field_reports*`   M2 + M6
  `smoke_test.py`                M6
  `.env.example`                 M6

No one edits another member's router.

------------------------------------------------------------------------

# 12. Feature 29--35 Dependency Map

``` text
M1 WBS TREE
     |
     v
M3 WBS SPLITS
     |
     v
M4 RECONCILIATION + EVIDENCE + PRIORITY
     |
     +----------+
                |
                v
M6 GRAPH + ASK WHY
                |
M2 LLM CLIENT --+--> M6 EXECUTION SUMMARY

M2 CLARIFICATION
     |
     v
M5 INTAKE UI

M2 PROVENANCE
     |
     v
M5 REVIEW UI

M4 PRIORITY
     |
     v
M5 REVIEW QUEUE

M4 EVIDENCE
     |
     v
M5 EVIDENCE PANEL
```

------------------------------------------------------------------------

# 13. Five Algorithm Dependency Map

``` text
M1:
lag + float + criticality
        |
        +--------------------+
        |                    |
        v                    v
M4 sequence             M6 impact
        |                    |
        +---------+----------+
                  |
                  v
            M4 priority

M1 WBS
   |
   v
M3 decomposition
   |
   v
M4 validation/reconciliation
   |
   v
M4 conflict
   |
   v
M4 priority
```

------------------------------------------------------------------------

# 14. Implementation Order

## Phase 0 --- Stabilization

1.  M2 fixes LLM provider/model.
2.  M6 fixes/validates P6 mock configuration.
3.  M6 coordinates XER test expectation.
4.  M6 coordinates JWKS mock test.
5.  M2 completes Tesseract setup.
6.  M5 confirms Dashboard KPI sources.

Do not start broad UI polish before the live pipeline is stable.

------------------------------------------------------------------------

## Phase 1 --- Schema

Together:

``` text
lag_days
total_float
is_critical

clarification fields
field_provenance
priority fields
claim_activity_splits
evidence_links
execution_summaries
```

Run migration once.

------------------------------------------------------------------------

## Phase 2 --- M1 + M2 foundation

M1:

``` text
WBS tree
schedule metadata
benchmark support
```

M2:

``` text
shared LLM client
clarification
provenance
dynamic translation foundation
```

These can be developed in parallel.

------------------------------------------------------------------------

## Phase 3 --- M3 + M4 correctness

M3:

``` text
matching calibration
WBS decomposition
```

M4:

``` text
out-of-sequence
directional conflict
```

M3 can use mocked WBS data before M1 integration.

M4 can use fixture events before M3 integration.

------------------------------------------------------------------------

## Phase 4 --- WBS/evidence/priority

M4:

``` text
WBS reconciliation
evidence fusion
priority scorer
review queue
```

Run targeted tests.

------------------------------------------------------------------------

## Phase 5 --- M6 algorithm and intelligence

M6:

``` text
float-aware impact preview
graph
Ask Why
execution summary
```

Use M2's shared LLM client.

------------------------------------------------------------------------

## Phase 6 --- M5 integration

M5:

``` text
clarification UI
provenance chips
WBS split editor
evidence groups
priority queue
Ask Why
execution summary
live dashboard KPIs
dynamic translation
```

------------------------------------------------------------------------

## Phase 7 --- Regression

Run:

``` text
existing test suite
+
18 targeted algorithm cases
+
Feature 29–35 tests
+
full smoke test
```

------------------------------------------------------------------------

# 15. Merge Order

Recommended v6 merge sequence:

1.  Stabilization fixes that are isolated and agreed.
2.  M1 WBS/schema support.
3.  M2 shared LLM client + clarification + provenance.
4.  M3 matching calibration + WBS decomposition.
5.  M4 sequence + conflict + WBS reconciliation + evidence + priority.
6.  M6 graph + reports + impact enhancements.
7.  M5 full UI integration.
8.  final shared integration.

If a schema migration is required before a member's code, merge the
migration first as a coordinated integration commit.

------------------------------------------------------------------------

# 16. Integration Syncs

  Sync     Trigger              Required checks
  -------- -------------------- -------------------------------------------------------
  Sync 1   M1 + M2 foundation   schedule -\> intake -\> extraction
  Sync 2   M3                   extraction -\> matching -\> WBS XOR
  Sync 3   M4                   match/split -\> check -\> conflicts/evidence/priority
  Sync 4   M6                   approved actual -\> export/P6/impact/graph/summary
  Sync 5   M5                   complete UI -\> all backend features
  Final    all merged           full demo + regression

After every merge:

``` text
health check
core intake smoke test
matching
check
```

must pass.

------------------------------------------------------------------------

# 17. Shared Restrictions

1.  No direct push to `main`.
2.  No member edits another member's router.
3.  M5 is the only frontend editor.
4.  No one writes another pipeline stage's status.
5.  No ad-hoc LLM calls.
6.  Normal match and WBS split are XOR.
7.  `conflict_records` and `evidence_links` remain separate.
8.  Schema changes require team notification.
9.  `shared/schemas.py` is additive.
10. Real API keys never enter Git.
11. Paid APIs are not added without team agreement.
12. Old claims are not automatically rematched after schedule
    replacement.
13. No persistent per-schedule FAISS implementation in this sprint.
14. Do not rewrite stable audit/actuals invariants without a failing
    test proving the need.
15. Do not replace the explainable Feature 25 forecast with a large ML
    model during this sprint.

------------------------------------------------------------------------

# 18. Testing Plan

## Existing regression

Retain all existing tests for:

-   schedule ingestion
-   extraction
-   matching
-   audit
-   actuals
-   export
-   auth
-   dashboards
-   OCR
-   XER
-   tabular extraction

## Mandatory targeted tests

### Impact

``` text
TC-IMP-01
TC-IMP-02
TC-IMP-03
TC-IMP-04
TC-IMP-05
```

### Sequence

``` text
TC-SEQ-01
TC-SEQ-02
TC-SEQ-03
TC-SEQ-04
```

### WBS

``` text
TC-WBS-01
TC-WBS-02
TC-WBS-03
```

### Conflict

``` text
TC-CONF-01
TC-CONF-02
TC-CONF-03
TC-CONF-04
```

### Priority

``` text
TC-PRI-01
TC-PRI-02
TC-PRI-03
```

### Feature 29

-   missing event type -\> one question
-   missing discipline -\> one question
-   missing pct/qty -\> one question
-   optional nulls do not trigger
-   answer reruns extraction
-   no second question loop
-   language-specific clarification

### Feature 30

-   broad WBS claim
-   completed sibling excluded
-   future sibling excluded
-   UOM incompatibility
-   manual split update
-   split XOR match

### Feature 31

-   cross-channel corroboration
-   cross-channel contradiction
-   conflict/evidence separation
-   graph node/edge generation

### Feature 32

-   priority inversion prevention
-   critical-path multiplier
-   warning ceiling
-   aging ceiling

### Feature 33

-   AI provenance
-   schedule provenance
-   Supervisor-edited provenance

### Feature 34

-   depth 1
-   depth 2 root changes
-   causal context uses only existing data

### Feature 35

-   deterministic aggregation
-   LLM receives only aggregate values
-   no invented numbers
-   exact-period cache behavior if enabled
-   dynamic translation fallback

------------------------------------------------------------------------

# 19. Demo Safety Net

M6 owns one guaranteed path:

``` text
known schedule
known claim
known validation/conflict
known review item
known Supervisor decision
known approved actual
known CSV
known P6 mock request
```

This path must work without relying on:

-   live voice recognition
-   live dynamic translation
-   a fragile untested claim
-   live external P6
-   a new random schedule

Optional features are attempted only after the guaranteed path works.

------------------------------------------------------------------------

# 20. Final Team Definition of Done

The team is complete when:

``` text
SCHEDULE
  ↓
CLAIM INTAKE
  ↓
EXTRACTION
  ↓
STATIC + DYNAMIC LANGUAGE SUPPORT
  ↓
OPTIONAL CLARIFICATION
  ↓
4-TIER MATCH OR WBS SPLIT
  ↓
SEQUENCE
  ↓
DIRECTIONAL CONFLICT
  ↓
EVIDENCE FUSION
  ↓
RISK-AWARE PRIORITY
  ↓
SUPERVISOR REVIEW
  ↓
APPROVE / EDIT / REJECT / HOLD
  ↓
AUDIT + APPROVED ACTUALS
  ↓
CSV + P6 MOCK
  ↓
DASHBOARD + HISTORY + FORECAST
  ↓
IMPACT PREVIEW
  ↓
GRAPH + ASK WHY
  ↓
AI EXECUTION SUMMARY
```

All six members must be able to demonstrate their owned area from the
integrated branch.

------------------------------------------------------------------------

# Appendix A --- Member-by-Member Work Checklist

## M1

### Existing

-   [ ] Schedule ingestion
-   [ ] Dependency parser
-   [ ] FAISS index
-   [ ] validation
-   [ ] XER support

### Next

-   [ ] lag/float/criticality import
-   [ ] WBS tree
-   [ ] benchmark/WBS data

## M2

### Existing

-   [ ] PDF/Excel/CSV/TXT
-   [ ] typed intake
-   [ ] browser voice path
-   [ ] OCR
-   [ ] schedule-export parser
-   [ ] extraction
-   [ ] language
-   [ ] batch extraction
-   [ ] source references

### Next

-   [ ] provider fix
-   [ ] shared LLM client
-   [ ] clarification
-   [ ] provenance
-   [ ] dynamic translation
-   [ ] Tesseract setup

## M3

### Existing

-   [ ] four-tier matching
-   [ ] candidates
-   [ ] unmatched
-   [ ] direct P6 matching

### Next

-   [ ] threshold/weight calibration
-   [ ] contextual gates
-   [ ] WBS decomposition
-   [ ] split endpoint

## M4

### Existing

-   [ ] conflict
-   [ ] physical validation
-   [ ] sequence validation
-   [ ] evidence metadata
-   [ ] audit
-   [ ] silent activity
-   [ ] rollup

### Next

-   [ ] sequence fix
-   [ ] directional conflict
-   [ ] WBS reconciliation
-   [ ] evidence fusion
-   [ ] priority scorer
-   [ ] review queue

## M5

### Existing

-   [ ] all frontend
-   [ ] auth UI
-   [ ] review
-   [ ] digest
-   [ ] dashboard
-   [ ] history
-   [ ] impact UI
-   [ ] decision endpoint

### Next

-   [ ] clarification UI
-   [ ] provenance chips
-   [ ] WBS split editor
-   [ ] evidence panel
-   [ ] priority queue
-   [ ] Ask Why
-   [ ] execution summary
-   [ ] live KPIs
-   [ ] dynamic translation UI

## M6

### Existing

-   [ ] actuals
-   [ ] auth shared core
-   [ ] export
-   [ ] dashboards
-   [ ] history
-   [ ] forecast
-   [ ] impact
-   [ ] P6 adapter
-   [ ] mock P6
-   [ ] smoke test
-   [ ] demo safety

### Next

-   [ ] impact algorithm
-   [ ] graph API
-   [ ] Ask Why backend
-   [ ] execution summary
-   [ ] live KPI backend
-   [ ] P6 mock default config
-   [ ] final integration

------------------------------------------------------------------------

# Appendix B --- Current Audit Facts That Must Not Be Lost

The current codebase audit identified:

-   core pipeline is implemented end-to-end
-   native P6 `.xer` parsing exists
-   robust tabular extraction exists
-   static English/Hindi/Telugu UI translation exists
-   benchmark data exists
-   batch extraction exists
-   audio-upload UI exists
-   dark/light theme exists
-   P6 is backed by a local mock
-   frontend mock mode exists
-   Groq model configuration currently fails with 404
-   Dashboard KPI cards are currently hardcoded
-   XER sample-byte test has an expectation mismatch
-   JWKS mock test has a key-ID mismatch
-   FAISS is in-memory and disappears on backend restart until a
    schedule is indexed
-   automatic old-claim rematching after schedule replacement is
    deliberately out of scope

These are audit facts, not reasons to rebuild stable components
unnecessarily.

------------------------------------------------------------------------

# Appendix C --- v6 Work Classification

## Must fix before final demo

``` text
S1 Groq/provider configuration
S2 Dashboard live KPIs
S3 XER test expectation
S4 JWKS test mock
S5 Tesseract setup
S6 P6 mock default
A1 Impact Preview
A2 Out-of-Sequence
A3 WBS Granularity
A4 Conflict Detection
A5 Smart Review Priority
```

## Must implement as v6 new functionality

``` text
29 Adaptive Field Copilot
30 WBS Granularity Bridge
31 Evidence Fusion + Knowledge Graph
32 Smart Review Priority
33 Field Provenance
34 Ask Why
35 AI Execution Summary
Dynamic translation
```

## Must retain/document

``` text
P6 XER parser
tabular extraction
batch extraction
static En/Hi/Te translation
Telugu localization
audio-upload capability
dark/light theme
45-activity benchmark
local P6 mock
frontend mock mode
```

## Explicitly future/optional

``` text
local Whisper fallback
full CPM engine
LLM justification suggestions
Docker Compose if not already present
persistent per-schedule FAISS
automatic rematching
large-scale distributed architecture
```
