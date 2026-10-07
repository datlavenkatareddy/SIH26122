# SIH26122 --- Product Requirements Document (PRD v6)

**Problem Statement:** SIH26122 --- Oil India Limited --- Smart
Automation\
**Version:** 6.0\
**Status:** Product Requirements Document — consolidated v6\
**Purpose:** Define the product, user experience, functional requirements, data, intelligence behavior, integrations, and release scope for SIH26122.


------------------------------------------------------------------------

# 1. Product Summary

SIH26122 is a controlled middle layer between messy field execution
evidence and a structured project schedule.

It:

1.  Ingests field progress from PDF, Excel, CSV, TXT, scanned diaries,
    typed text, browser voice transcription, audio-upload UI,
    photographs/evidence, and P6/MSP progress exports.
2.  Extracts structured execution claims.
3.  Detects the input language and supports English, Hindi and Telugu
    UI/localization.
4.  Optionally asks one targeted clarification question when required
    claim information is missing.
5.  Matches claims to schedule activities using a four-tier matching
    cascade.
6.  Bridges broad WBS-level claims to multiple schedule activities where
    appropriate.
7.  Runs deterministic physical, logical, sequencing, conflict and
    evidence checks.
8.  Fuses independent evidence channels into corroboration/contradiction
    relationships.
9.  Produces a risk-aware Supervisor review priority.
10. Presents provenance, evidence, validation reasons and investigation
    paths to a human Supervisor.
11. Requires human approval/edit/reject/hold before approved actuals are
    changed.
12. Reconciles start, finish, cumulative percentage and incremental
    quantity.
13. Produces CSV output and a production-shaped P6 EPPM REST payload
    against a local mock server.
14. Provides delay analytics, institutional memory, activity history,
    forecasting, impact preview, execution summaries and an execution
    knowledge graph.
15. Maintains a tamper-evident SHA-256 audit chain.

### Product principle

> **AI reads the mess. Rules check it. A human approves it. Everything
> is logged.**

------------------------------------------------------------------------

# 2. Product Scope

SIH26122 covers the complete flow from field execution reporting to approved project actuals and execution intelligence. The product combines the established project workflow with the v6 capabilities described in this document.

The product scope includes:

- Schedule ingestion from P6/MSP CSV/XLSX and native P6 `.xer` files.
- Multi-format field claim intake from documents, text, voice, scanned diaries, photographs/evidence, and structured progress exports.
- Structured claim extraction with language detection and field-level provenance.
- English, Hindi, and Telugu user-interface localization.
- Runtime translation for generated and user-facing content while preserving canonical source data.
- Four-tier schedule matching with candidate visibility and unmatched handling.
- WBS-level decomposition for claims that represent multiple sibling activities.
- Deterministic validation of quantities, percentages, units, dependencies, sequencing, evidence metadata, and execution history.
- Chronological conflict detection and cross-channel evidence fusion.
- Supervisor review with explainable priority, provenance, evidence, and investigation paths.
- Human approval, editing, rejection, and hold workflows.
- Reconciliation of approved starts, finishes, cumulative progress, and incremental quantities.
- Audit logging with a tamper-evident SHA-256 chain.
- CSV and P6-shaped downstream integration.
- Delay analytics, institutional memory, activity history, silent-activity monitoring, and lightweight forecasting.
- Schedule impact analysis using dependency relationships, lag/lead, float, execution state, and bounded downstream propagation.
- Execution knowledge graph, Ask Why investigation, and execution summaries.

The release is designed as a single React + FastAPI + Supabase application with deterministic business rules surrounding optional LLM capabilities.

------------------------------------------------------------------------

# 3. Product Principles

1.  A field report is a **claim, not a fact**.
2.  AI assists extraction, clarification and phrasing; it never makes
    the final approval decision.
3.  Only an authenticated `SUPERVISOR` can approve, edit, reject or hold
    a claim.
4.  Low-confidence, unmatched, conflicting, contradictory or invalid
    claims are surfaced.
5.  Every approved update remains traceable to its source.
6.  Every human action is attributable to an authenticated user.
7.  Machine matching and human selection remain separate concepts.
8.  Externally supplied `activity_id` values are preserved exactly.
9.  Approved cumulative percentage is replaced, not blindly accumulated.
10. Approved incremental quantities are recalculated from source
    decisions.
11. Adapter failures never roll back an already committed approval.
12. PostgreSQL/Supabase is the source of truth; FAISS is a retrieval
    structure.
13. No paid API is required in the default build.
14. The architecture remains a single React + FastAPI + Supabase
    application.
15. Dynamic translation is a presentation/runtime layer; canonical
    stored source text is never overwritten merely to translate it.
16. A WBS split and a normal single-activity match are mutually
    exclusive for one claim.
17. Same-channel conflicts and cross-channel evidence contradictions
    remain separate concepts.
18. The deterministic checks layer remains authoritative over LLM
    suggestions.
19. v6 algorithm enhancements must reduce false positives/false
    negatives rather than add decorative complexity.
20. The demo must retain a deterministic, pre-tested fallback path.

------------------------------------------------------------------------

# 4. Problem and Solution

## 4.1 Problem

P6/MSP schedules contain structured activities, dates, quantities, WBS
codes and dependencies. Field reality arrives through heterogeneous
sources using different terminology, identifiers, languages and levels
of granularity.

Typical reports include:

-   "Line 24 spool erected."
-   "Concrete pouring completed in Area C."
-   "Joint 3 of 10 welded."
-   scanned handwritten diary entries
-   voice notes
-   subcontractor P6/MSP progress exports
-   photographs and evidence

The same work may therefore appear as a broad WBS claim, a specific
activity claim, an incremental quantity claim or a cumulative percentage
claim.

## 4.2 Solution flow

``` text
FIELD REALITY
   |
   +-- PDF / XLSX / CSV / TXT
   +-- scanned diary
   +-- typed text
   +-- browser voice
   +-- evidence photo
   +-- P6/MSP progress export
   |
   v
INTAKE
   |
   v
EXTRACTION
   |
   +--> language detection
   +--> provenance
   +--> optional one-question clarification
   |
   v
MATCHING
   |
   +--> 4-tier candidate matching
   +--> WBS granularity bridge
   |
   v
CHECKS
   |
   +--> physical validation
   +--> dependency/sequence validation
   +--> directional conflict detection
   +--> evidence fusion
   +--> rollup/reconciliation
   +--> priority score
   |
   v
SUPERVISOR REVIEW
   |
   +--> provenance
   +--> evidence
   +--> Ask Why
   +--> priority queue
   |
   v
APPROVE / EDIT / REJECT / HOLD
   |
   v
APPROVED ACTUALS
   |
   +--> SHA-256 audit
   +--> CSV
   +--> P6 adapter
   +--> dashboards
   +--> history
   +--> forecast
   +--> impact preview
   +--> execution summary
```

------------------------------------------------------------------------

# 5. Architecture

## 5.1 Technology

  -----------------------------------------------------------------------
  Layer                               Technology
  ----------------------------------- -----------------------------------
  Frontend                            React + TypeScript + Vite

  Data fetching                       TanStack Query

  UI                                  Tailwind/Lucide/shadcn-style
                                      components already used by the product
                                      components as already used

  Backend                             Python + FastAPI + Pydantic v2

  Database                            Supabase PostgreSQL

  Authentication                      Supabase Auth

  Semantic matching                   sentence-transformers /
                                      `all-MiniLM-L6-v2`

  Vector retrieval                    FAISS in-memory

  Fuzzy matching                      RapidFuzz

  Tabular parsing                     pandas, openpyxl

  PDF                                 PyMuPDF

  P6 XER                              native parser already implemented

  OCR                                 pytesseract

  Voice default                       Browser Web Speech API

  Voice fallback                      local `faster-whisper` /
                                      `whisper.cpp`, optional

  Image metadata                      Pillow / exifread

  Audit                               SHA-256 / Python hashlib

  Charts                              Recharts

  LLM primary                         Groq free tier

  LLM fallback                        Gemini free tier

  P6 integration                      production-shaped REST adapter +
                                      local mock

  Demo                                local application; Docker
                                      Compose only if explicitly
                                      completed
  -----------------------------------------------------------------------

## 5.2 LLM architecture

All LLM calls must pass through:

``` text
backend/shared/llm_client.py
```

M2 owns this shared client.

It is used by:

-   Feature 3 extraction
-   Feature 29 clarification
-   Feature 35 execution-summary phrasing

No router may contain a second ad-hoc Groq/Gemini HTTP implementation.

Provider configuration:

``` text
LLM_PROVIDER
LLM_API_KEY
LLM_MODEL
```

Groq is the primary provider; Gemini is the documented fallback.

The configured provider and model shall support stable structured generation for the extraction workflow. Groq is the primary provider and Gemini is the documented fallback.

------------------------------------------------------------------------

# 6. Authentication and Roles

Exactly two application roles:

## `SITE_ENGINEER`

Can:

-   log in
-   access Claim Intake
-   submit files
-   submit typed text
-   submit browser-transcribed voice
-   submit scanned diary images
-   submit P6/MSP progress exports
-   answer clarification questions

Cannot:

-   approve/edit/reject/hold
-   access Supervisor review screens
-   access Supervisor-only reports

## `SUPERVISOR`

Can:

-   log in
-   land on Daily Digest
-   access Review Workspace
-   approve/edit/reject/hold
-   access Dashboard
-   access Activity History
-   access Impact Preview
-   access evidence/graph/Ask Why
-   access AI Execution Summary
-   adjust WBS split percentages

Authentication rules:

-   Supabase Auth email/password
-   no signup
-   no password reset
-   exactly two seeded demo accounts
-   `profiles.id = auth.users.id`
-   role stored in `profiles.role`
-   backend role enforcement through `shared/auth.py`
-   frontend route hiding is not the security boundary
-   `planner_id` comes from the authenticated Supervisor, never from
    free-form request input

------------------------------------------------------------------------

# 7. Core Pipeline and State Machine

## 7.1 Standard pipeline

1.  `POST /claims/file` or `POST /claims/text`
2.  extraction/provenance/clarification gate
3.  if clarification is pending, stop and wait for `/clarify`
4.  `POST /claims/{event_id}/match`
5.  `POST /claims/{event_id}/check`
6.  Supervisor review
7.  decision
8.  approved actual update
9.  CSV/P6 downstream output

P6/MSP schedule-export claims bypass LLM extraction and clarification
because the structured file already supplies activity IDs and progress
fields.

## 7.2 Status ownership

``` text
M2:
    EXTRACTED

M3:
    EXTRACTED -> MATCHED
              -> UNMATCHED

M4:
    MATCHED   -> VALIDATED
              -> REVIEW_REQUIRED

    UNMATCHED -> REVIEW_REQUIRED

M5:
    REVIEW_REQUIRED / VALIDATED / HOLD
       -> APPROVED / EDITED / REJECTED / HOLD
```

No stage silently overwrites another stage's status.

------------------------------------------------------------------------

# 8. Complete Feature Set --- Features 1--35

## Feature 1 --- Schedule Ingestion



Supported baseline sources:

-   P6/MSP CSV/XLSX
-   native P6 `.xer` parser

Canonical source mapping:

  Source              Canonical
  ------------------- --------------------
  `L6 Task ID`        `activity_id`
  `L5 Activity ID`    `wbs_code`
  `Activity`          `activity_name`
  `Discipline`        `discipline`
  `Unit`              `uom`
  `Planned Qty`       `planned_quantity`
  `Baseline Start`    `planned_start`
  `Baseline Finish`   `planned_finish`
  `L1 + L2`           `location`

`asset_tag` remains nullable because it is not present in the real
source file.

Validation includes:

-   required fields
-   duplicate IDs
-   empty IDs
-   date format
-   start \<= finish
-   non-negative quantity
-   baseline percentage 0--100
-   whitespace normalization
-   dependency existence
-   self-dependency rejection

Import is transactional.

Dependencies support:

``` text
FS
SS
FF
SF
```

The schedule model may include the following relationship attributes when supplied by the source:

``` text
lag_days
total_float
is_critical
```

When a source does not provide one of these attributes, the product uses an explicit documented fallback and does not fabricate schedule facts.

FAISS is used as an in-memory retrieval structure for the active schedule, while PostgreSQL remains the persistent source of truth. Historical schedule data is retained in PostgreSQL. Automatic rematching of historical claims after schedule replacement is outside the product boundary.

------------------------------------------------------------------------

## Feature 2 --- Multi-format Claim Ingestion



Accept:

-   PDF
-   XLSX
-   CSV
-   TXT
-   typed text
-   browser voice-transcribed text
-   evidence photos
-   scanned diary images/PDF
-   P6/MSP progress files
-   existing audio-upload UI where present

The system records source-document metadata and SHA-256 file hashes.

------------------------------------------------------------------------

## Feature 3 --- LLM Extraction



Extraction schema:

``` json
{
  "event_date": "YYYY-MM-DD",
  "reported_activity_id": "string or null",
  "discipline": "CIVIL | PIPING | STATIC_ROTATING_EQUIPMENT | ELECTRICAL | INSTRUMENTATION | HSE",
  "action": "string",
  "event_type": "ACTUAL_START | ACTUAL_FINISH | PROGRESS_UPDATE | DELAY | BLOCKER",
  "claim_mode": "CUMULATIVE_PCT | INCREMENTAL_QUANTITY",
  "asset_tag": "string or null",
  "location": "string or null",
  "claimed_quantity": "number or null",
  "claimed_uom": "string or null",
  "claimed_pct": "number or null",
  "delay_reason": "MATERIAL | EQUIPMENT | LABOUR | ACCESS | WEATHER | REWORK | OTHER | null"
}
```

Pydantic validation is mandatory.

Start and finish are distinct events.

`claim_mode` invariant:

-   cumulative percentage -\> `claimed_pct`
-   incremental quantity -\> `claimed_quantity + claimed_uom`

------------------------------------------------------------------------

## Feature 4 --- Conversational Typed Intake



Typed natural-language input enters the same extraction/matching/check
pipeline.

------------------------------------------------------------------------

## Feature 5 --- Voice Input



Default:

``` text
Browser Web Speech API -> text -> normal extraction
```

No paid Whisper API.

------------------------------------------------------------------------

## Feature 6 --- Multi-language Support and Translation



### Static UI localization

The UI already supports:

``` text
English
Hindi
Telugu
```

through client-side internationalization/translation dictionaries.

Telugu localization must be formally documented in v6.

### Dynamic translation

Dynamic/runtime-generated content must be translated without modifying
canonical source data.

Target content:

-   user-generated claim text when a translated display is requested
-   AI clarification questions
-   evidence explanations
-   validation explanations
-   Ask Why results
-   AI execution summaries
-   other runtime-generated assistant text

Rules:

1.  Detect/store the claim's `language_detected`.
2.  Feature 29 clarification questions must be phrased in the claim's
    detected language.
3.  Canonical `raw_claim_text` and normalized structured fields are not
    overwritten by display translation.
4.  Translation is a runtime/presentation layer.
5.  If a translation fails, show the canonical/original language rather
    than blocking the claim pipeline.
6.  Dynamic translation must use the shared LLM client if an LLM is
    used.
7.  The UI must allow switching static UI language without corrupting
    claim data.

------------------------------------------------------------------------

## Feature 7 --- Four-tier Matching



Tiers:

1.  `EXACT_ID` --- confidence 1.00
2.  `EXACT_ASSET` --- approximately 0.80--0.95
3.  `HYBRID_FALLBACK` --- semantic + fuzzy + contextual signals
4.  `HARD_MISMATCH` --- hard discipline/location conflict

The matching score combines the following signals:

``` text
50% semantic
25% fuzzy
15% location
10% discipline
```

The active weights are calibrated against the benchmark and may be tuned while preserving the relative importance of semantic, fuzzy, location, and discipline signals.

A hard location/discipline mismatch must remain a strong gate.

The matching threshold is calibrated against the synthetic benchmark and documented with the active configuration.

WBS-level/broad claims must be routed to Feature 30 rather than forced
into an arbitrary leaf task.

Top three candidates remain available.

------------------------------------------------------------------------

## Feature 8 --- Unmatched Claim Flagging



Low-confidence claims must become:

``` text
UNMATCHED
```

Candidates remain visible.

M4 moves unmatched claims to `REVIEW_REQUIRED`.

------------------------------------------------------------------------

## Feature 9 --- Conflict Detection



Conflict reasoning is directional and chronological, distinguishing same-date disagreement, normal progression, regression, and quantity anomalies.

The new engine must distinguish:

### Same-date disagreement

Two cumulative claims for the same activity on the same reporting
date/shift disagree beyond the configured tolerance:

``` text
SAME_DATE_DISAGREEMENT
```

### Normal chronological progress

If:

``` text
t2 > t1
pct(t2) >= pct(t1)
```

the increase is normal progression, not a conflict by itself.

### Progress regression

If a newer claim reports lower cumulative progress than an older
authoritative/approved claim:

``` text
PROGRESS_REGRESSION
```

flag it unless the claim explicitly contains an accepted rework/reset
explanation.

### Incremental quantities

Incremental quantity claims are not ignored. They must be checked for:

-   planned-quantity exceedance
-   invalid negative values
-   duplicate physical contribution where deterministic evidence exists
-   implausible/unsupported accumulation

For same-date cumulative claims, a configured 10-percentage-point difference is the baseline threshold for disagreement. Across different dates, chronological progression rules take precedence over a symmetric difference threshold.

------------------------------------------------------------------------

## Feature 10 --- Physical / Logic Validation



Retain:

-   `VAL_OVER_100`
-   `VAL_NEGATIVE`
-   `VAL_UOM_MISMATCH`
-   `VAL_OUT_OF_SEQUENCE`
-   `VAL_REOPENED_COMPLETED_ACTIVITY`
-   `VAL_EVIDENCE_MISMATCH`
-   low-confidence validation

### Sequence validation behavior

`VAL_OUT_OF_SEQUENCE` must evaluate:

-   `ACTUAL_START`
-   `PROGRESS_UPDATE` when the successor has not legitimately started

Dependency-specific rules:

  -----------------------------------------------------------------------
  Relationship                        Required condition
  ----------------------------------- -----------------------------------
  FS                                  predecessor must be complete before
                                      successor start/progress when
                                      successor is otherwise unstarted

  SS                                  predecessor must have started /
                                      have progress

  FF                                  successor finish must not precede
                                      predecessor finish

  SF                                  apply start-to-finish constraint
                                      where the available schedule data
                                      supports it
  -----------------------------------------------------------------------

An already in-progress successor must not repeatedly receive false
out-of-sequence flags for ordinary progress updates.

------------------------------------------------------------------------

## Feature 11 --- Evidence Metadata Checks



For evidence photos:

-   EXIF timestamp
-   GPS
-   deterministic date comparison
-   Haversine distance

EXIF timestamp comparison uses a 2-day tolerance for the supported evidence workflow.

The current single-site-radius limitation should not be expanded into a
large geospatial system in this sprint.

------------------------------------------------------------------------

## Feature 12 --- Human Review Workspace



Supervisor sees:

-   extracted claim
-   source
-   top candidates
-   confidence
-   supporting signals
-   disqualifying signals
-   conflicts
-   validation issues
-   evidence metadata
-   provenance
-   WBS split information
-   evidence links
-   priority score/reasons
-   history
-   Ask Why controls

Actions:

``` text
APPROVE
EDIT
REJECT
HOLD
```

Every decision requires justification.

------------------------------------------------------------------------

## Feature 13 --- SHA-256 Audit Log



Audit records include:

-   entity
-   entity ID
-   action
-   actor
-   before state
-   after state
-   payload hash
-   previous hash
-   current hash
-   timestamp

Hash chaining remains intact.

------------------------------------------------------------------------

## Feature 14 --- CSV Export



Canonical columns:

``` text
activity_id
actual_start
actual_finish
actual_pct_complete
actual_quantity
```

------------------------------------------------------------------------

## Feature 15 --- Delay-reason Dashboard



Endpoint:

``` http
GET /api/v1/dashboard/delay-reasons
```

The dashboard must use live backend/database data.

Hardcoded KPI cards are not acceptable in the final v6 demo.

------------------------------------------------------------------------

## Feature 16 --- Institutional Memory



Join approved actuals with schedule activities and provide
planned-vs-actual historical information grouped/filterable by
discipline.

------------------------------------------------------------------------

## Feature 17 --- Daily Digest / Bulk Review



Digest groups claims by date/discipline.

Bulk approval remains independent per claim.

The default date may use the most recently created claim when no date is
supplied, as implemented, but this behavior must be documented.

Bulk approval still uses the normal audit and approved-actual paths.

The review queue must use Feature 32 priority ordering by default in v6.

------------------------------------------------------------------------

## Feature 18 --- Activity History



Chronological timeline:

-   execution events
-   source references
-   planner decisions
-   relevant source information
-   approved actual state
-   audit context where available

------------------------------------------------------------------------

## Feature 19 --- Silent Activity Nudge



Detect activities with no recent updates.

This is a monitoring signal, not an automatic schedule change.

------------------------------------------------------------------------

## Feature 20 --- Schedule Impact Preview



Impact analysis models dependency relationships, schedule constraints, float, and execution state to explain the downstream effect of a hypothetical delay.

### Required behavior

1.  Inspect direct successors for all supported relationships:
    -   FS
    -   SS
    -   FF
    -   SF
2.  Apply `lag_days`, including negative lead if represented by the
    source.
3.  Consider all predecessors of a successor.
4.  Determine the controlling predecessor.
5.  Inspect approved execution state:
    -   completed
    -   in progress
    -   not started
6.  Consider total float.
7.  Propagate only net delay.
8.  Support bounded multi-hop propagation.
9.  Explain why an activity is classified as impacted.

### Classifications

Examples:

``` text
ABSORBED_BY_FLOAT
CRITICAL_PATH_SLIP
EXECUTION_IN_PROGRESS
NON_CONTROLLING_PREDECESSOR
ALREADY_COMPLETED
NO_IMPACT
```

### Core calculation

For a relationship constraint:

``` text
effective constraint
= predecessor schedule point
+ hypothetical delay
+ relationship lag/lead
```

For a successor:

``` text
controlling constraint = max(all applicable predecessor constraints)
slippage = max(0, controlling constraint - planned constraint)
net_delay = max(0, slippage - available float)
```

Only `net_delay` propagates downstream.

A completed successor is not shifted.

An in-progress successor is analyzed using remaining execution context
rather than blindly shifting its historical planned start.

A non-controlling predecessor delay must not be reported as a
controlling schedule slip.

------------------------------------------------------------------------

## Feature 21 --- Scanned Diary / OCR



Default:

``` text
pytesseract
```

Windows Tesseract installation/path must be documented or packaged
sufficiently for demo execution.

------------------------------------------------------------------------

## Feature 22 --- P6/MSP Schedule-export Claims



P6/MSP progress export is a claim source, not a new baseline.

Rows with actual progress become `SCHEDULE_EXPORT` execution events and
go directly to `EXACT_ID`.

No LLM extraction/clarification is required for structured
schedule-export rows.

They still pass checks and Supervisor review.

------------------------------------------------------------------------

## Feature 23 --- Start/Finish Event Capture and Reconciliation



Separate:

``` text
ACTUAL_START
ACTUAL_FINISH
```

One `(schedule_id, activity_id)` approved-actual row stores the combined
state.

Start cannot erase finish; finish cannot erase start.

------------------------------------------------------------------------

## Feature 24 --- Granularity Rollup



Incremental quantity rollup remains source-decision-based.

Only latest decisions with:

``` text
APPROVE
EDIT
```

contribute.

Never use:

``` python
actual_quantity += claimed_quantity
```

------------------------------------------------------------------------

## Feature 25 --- Lightweight Forecasting



Forecasting uses a deliberately explainable method:

``` text
actual_duration / planned_duration
```

aggregated historically by discipline.

It is not a trained ML model.

Feature 35 may use the forecast ratio to identify activities whose current pace trails historical expectation.

A more advanced ML/CPM forecast is not mandatory v6 work.

------------------------------------------------------------------------

## Feature 26 --- Auto-triggered CSV Export



After approved actual commit:

``` text
DB COMMIT
   |
   +--> CSV regeneration
   +--> P6 adapter
```

No distributed transaction.

------------------------------------------------------------------------

## Feature 27 --- P6 EPPM REST API Write-back



Canonical interface:

``` python
push_actual(
    activity_id,
    actual_start,
    actual_finish,
    actual_pct_complete,
    actual_quantity,
)
```

Canonical P6 payload:

``` json
{
  "Id": "A1000",
  "StartDate": "2026-09-05",
  "FinishDate": "2026-09-08",
  "PercentComplete": 75
}
```

`actual_quantity` is dropped from the P6 payload.

`ActualDuration` is not used.

Live OIL P6 access is not required; local mock is the demo target.

The default demo configuration should actively point to the local mock
P6 endpoint.

------------------------------------------------------------------------

## Feature 28 --- Login and Role-based Access



Screens:

1.  Login
2.  Claim Intake
3.  Daily Digest
4.  Review Workspace
5.  Dashboard
6.  Activity History
7.  Impact Preview
8.  AI Execution Summary
9.  Investigation content is inline, not a separate required screen

Role landing:

``` text
SITE_ENGINEER -> /intake
SUPERVISOR    -> /digest
```

------------------------------------------------------------------------

# 9. Feature 29 --- Adaptive Field Copilot



After extraction, check only required fields:

-   `event_type`
-   `discipline`
-   at least one of `claimed_pct` / `claimed_quantity`

If any required field is missing:

1.  Make exactly one additional LLM call.
2.  Generate one specific clarification question.
3.  Phrase it in `language_detected`.
4.  Set `clarification_status = PENDING`.
5.  Store `clarification_question`.
6.  Stop the pipeline before matching.

Do not ask because these are null:

-   `asset_tag`
-   `location`
-   `delay_reason`

`POST /claims/{event_id}/clarify`:

-   accepts free-text answer
-   preserves original raw claim
-   combines original claim + answer
-   reruns the same extraction schema/Pydantic validation
-   stores answer
-   sets `clarification_status = ANSWERED`
-   updates provenance for newly filled fields
-   returns the claim ready for matching

Never create an endless clarification loop.

------------------------------------------------------------------------

# 10. Feature 30 --- WBS Granularity Bridge



### M1

Add:

``` http
GET /api/v1/schedules/{schedule_id}/wbs-tree
```

Group activities by `wbs_code`.

A WBS group with 2+ child activities is a decomposition candidate.

### M3

During `/match`:

1.  run normal four-tier matching
2.  inspect top candidate's WBS
3.  if 2+ sibling activities exist
4.  if claim does not identify a specific asset/sub-location
5.  decompose instead of forcing a single match

Normal match and split are XOR:

``` text
normal:
matched_activity_id != null
splits = none

split:
matched_activity_id = null
splits >= 1
```

### Split allocation behavior

Do not blindly use `1/N` across every sibling.

Allocation must consider:

-   approved progress
-   completion state
-   planned start/finish
-   remaining headroom
-   sibling dependency order
-   temporal eligibility
-   planned quantity where dimensionally compatible
-   UOM compatibility
-   claim mode
-   claim wording/location/asset specificity

Completed activities receive zero new allocation.

Future/ineligible activities should not receive allocation.

Active, uncompleted siblings receive available progress in
dependency/topological order where sibling dependencies are known.

WBS-weighted allocation is prohibited across incompatible UOMs.

Generated shares must sum to:

``` text
1.0000 ± 0.0001
```

unless an explicitly supported partial-allocation mode is introduced.

### M4

For each split:

``` text
contribution = claim_value × split_pct
```

Run validation and reconciliation per child.

A split that allocates progress to an invalid/unstarted child must
surface sequence validation.

### M5

Show sibling rows and editable `split_pct`.

Edited rows become:

``` text
MANUAL
```

------------------------------------------------------------------------

# 11. Feature 31 --- Evidence Fusion Engine and Project Execution Knowledge Graph



## Evidence Fusion

Compare execution events:

-   same activity or split activity
-   within the configured comparison window
-   different `source_documents.document_type`

Classify:

``` text
CORROBORATES
CONTRADICTS
```

Store:

-   link ID
-   event A
-   event B
-   relation
-   confidence
-   rationale
-   timestamp

### Evidence fusion behavior

The evidence-fusion engine uses a configurable quantitative tolerance together with date, source-channel, and execution context. It:

1.  normalize the compared metric/date context
2.  distinguish same-date agreement/disagreement from normal time
    progression
3.  apply the configured deterministic threshold where applicable
4.  record source-channel context
5.  avoid treating a Day 1 report and Day 6 cumulative report as
    contradictory merely because the percentage increased
6.  surface authority metadata where available

A source-credibility hierarchy may be represented as configuration for
display/triage, but it must not silently overwrite a conflicting source
or auto-approve a claim.

`conflict_records` and `evidence_links` remain separate.

## Knowledge Graph

No materialized graph table.

At query time, join:

-   execution_events
-   source_documents
-   candidate_matches
-   conflict_records
-   validation_issues
-   planner_decisions
-   evidence_links
-   schedule_dependencies

Return nodes and edges.

------------------------------------------------------------------------

# 12. Feature 32 --- Smart Review Priority



The review queue assigns an explainable priority score based on issue severity, schedule criticality, and queue aging.

### Priority model

#### Base severity

  Condition                                                           Base
  ------------------------------------------ -----------------------------
  Critical physical/sequence error                                     100
  Conflict/evidence contradiction                                       70
  Unmatched or WBS decomposition ambiguity                              40
  Administrative warnings                      min(25, 10 × warning count)
  Routine/no flag                                                        5

Critical errors include:

-   `VAL_OUT_OF_SEQUENCE`
-   `VAL_OVER_100`
-   `VAL_REOPENED_COMPLETED_ACTIVITY`

#### Criticality multiplier

  Total Float           Multiplier
  ------------------- ------------
  \<= 0 days                   2.0
  \>0 and \<=5 days            1.5
  \>5 days                     1.0

If `is_critical` is authoritative from the source, it may be used
consistently with the float model.

#### Aging

``` text
aging = min(30, 6 × ln(1 + hours_in_queue))
```

#### Final

``` text
priority_score
= base_severity × criticality_multiplier + aging
```

The score gives greater weight to high-severity issues on schedule-critical activities while retaining bounded aging for older review items.

Reasons must explain:

-   severity
-   float/criticality
-   meaningful aging
-   conflict/contradiction/unmatched/split cause

Review queue:

``` http
GET /api/v1/review-queue?sort=priority
```

Statuses:

``` text
VALIDATED
REVIEW_REQUIRED
HOLD
```

Supervisor only.

------------------------------------------------------------------------

# 13. Feature 33 --- Field Provenance Tags



`execution_events.field_provenance`:

``` json
{
  "discipline": "AI_EXTRACTED",
  "claimed_pct": "AI_EXTRACTED",
  "location": "ENGINEER_ENTERED",
  "activity_id": "SCHEDULE_AUTO_FILLED"
}
```

Allowed values:

``` text
AI_EXTRACTED
SCHEDULE_AUTO_FILLED
ENGINEER_ENTERED
SUPERVISOR_EDITED
```

`ENGINEER_ENTERED` is reserved for structured values explicitly entered by the Site Engineer.

At intake:

-   LLM-filled -\> `AI_EXTRACTED`
-   schedule-export direct fields -\> `SCHEDULE_AUTO_FILLED`

On Supervisor `EDIT`:

-   only actually changed fields become `SUPERVISOR_EDITED`
-   untouched fields preserve stored provenance

Null fields need no provenance entry.

------------------------------------------------------------------------

# 14. Feature 34 --- Ask Why? Investigation Mode



Reuse the knowledge graph.

Endpoint:

``` http
GET /api/v1/graph/activity/{activity_id}?depth=N
```

Depth 1:

-   immediate claim
-   flags
-   conflicts
-   evidence links
-   direct dependency context

When a user selects a newly shown node:

-   root the traversal at the selected node
-   request deeper traversal

The UI is inline; no separate investigation screen is required.

The graph should expose enough identifiers for each node to support
drill-down.

A deterministic causal explanation layer may summarize an upstream
dependency chain using available:

-   predecessor activity
-   delay reason
-   actual/planned dates
-   float
-   validation flag

This should not invent facts that are not present in the data.

------------------------------------------------------------------------

# 15. Feature 35 --- AI Execution Summary



Endpoint:

``` http
GET /api/v1/reports/execution-summary?start=YYYY-MM-DD&end=YYYY-MM-DD&discipline=...
```

Inputs:

-   exact date range
-   optional discipline
-   `all`/omitted discipline = all

Aggregation must be deterministic.

Calculate:

1.  activities with execution events in range
2.  progress delta from approved actuals
3.  claim counts by status
4.  conflicts opened
5.  conflicts resolved
6.  activities whose current pace trails historical expected pace using
    Feature 25

Only aggregate numbers are passed to the LLM.

LLM instruction:

-   phrase the provided numbers
-   do not compute
-   do not estimate
-   do not add figures not provided

Optional cache:

``` text
(period_start, period_end, discipline)
```

Table:

``` text
execution_summaries
```

Supervisor only.

The summary must support dynamic translation/display in the selected UI
language without changing the canonical stored summary source.

------------------------------------------------------------------------

# 16. Data Model

Core product tables include:

``` text
profiles
schedules
schedule_activities
schedule_dependencies
source_documents
execution_events
source_references
candidate_matches
conflict_records
validation_issues
planner_decisions
approved_actuals
audit_logs
```

## 16.1 v6 additive fields

``` sql
execution_events:
    clarification_status
    clarification_question
    clarification_answer
    field_provenance JSONB
    priority_score REAL
    priority_reasons TEXT
```

## 16.2 WBS splits

``` sql
claim_activity_splits(
    split_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    split_basis TEXT,
    split_pct REAL NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
)
```

Allowed:

``` text
EQUAL
WBS_WEIGHTED
MANUAL
```

## 16.3 Evidence links

``` sql
evidence_links(
    link_id TEXT PRIMARY KEY,
    event_id_a TEXT NOT NULL,
    event_id_b TEXT NOT NULL,
    relation_type TEXT,
    confidence REAL,
    rationale TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
)
```

## 16.4 Execution summaries

``` sql
execution_summaries(
    summary_id TEXT PRIMARY KEY,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    discipline TEXT,
    summary_text TEXT NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT now()
)
```

## 16.5 Algorithm-supporting schedule fields

Required by the core intelligence capabilities where available:

``` sql
schedule_dependencies.lag_days
schedule_activities.total_float
schedule_activities.is_critical
```

If the actual source format cannot provide one of these values, document
the fallback and do not fabricate schedule facts.

`free_float` is optional and should only be added if the source/import
path can reliably support it.

------------------------------------------------------------------------

# 17. Existing Approved Actuals Contract

Exactly one row per:

``` text
(schedule_id, activity_id)
```

### Start/finish

-   start updates start only
-   finish updates finish only

### Cumulative percentage

Replace with newly approved value.

### Incremental quantity

Recalculate from source decisions:

``` text
latest decision per event
AND action in APPROVE / EDIT
```

using:

``` text
COALESCE(approved_qty, claimed_quantity)
```

Never blindly add to the stored actual.

------------------------------------------------------------------------

# 18. API Inventory

## Authentication

``` http
GET /api/v1/auth/me
```

## Schedule

``` http
POST /api/v1/schedules
GET /api/v1/schedules
GET /api/v1/schedules/{schedule_id}
GET /api/v1/schedules/{schedule_id}/activities
GET /api/v1/schedules/{schedule_id}/activities/{activity_id}
GET /api/v1/schedules/{schedule_id}/dependencies
GET /api/v1/schedules/{schedule_id}/wbs-tree
```

## Claims

``` http
POST /api/v1/claims/file
POST /api/v1/claims/text
POST /api/v1/claims/schedule-export
GET /api/v1/claims/{event_id}
GET /api/v1/claims
POST /api/v1/claims/{event_id}/clarify
POST /api/v1/claims/{event_id}/match
GET /api/v1/claims/{event_id}/candidates
POST /api/v1/claims/{event_id}/rematch
GET /api/v1/claims/{event_id}/splits
PATCH /api/v1/claims/{event_id}/splits
POST /api/v1/claims/{event_id}/check
GET /api/v1/claims/{event_id}/conflicts
GET /api/v1/claims/{event_id}/validation
GET /api/v1/claims/{event_id}/evidence
GET /api/v1/activities/{activity_id}/rollup
```

## Review / decisions

``` http
POST /api/v1/decisions
GET /api/v1/review-queue?sort=priority
GET /api/v1/digest?date=...
POST /api/v1/digest/bulk-approve
```

## Audit / alerts

``` http
GET /api/v1/audit/{entity_id}
GET /api/v1/alerts/silent-activities
```

## Reporting / integration

``` http
GET /api/v1/export/csv
GET /api/v1/dashboard/delay-reasons
GET /api/v1/dashboard/institutional-memory
GET /api/v1/dashboard/forecast?activity_id=...
GET /api/v1/dashboard/forecast?discipline=...
GET /api/v1/activities/{activity_id}/history
GET /api/v1/schedule/{activity_id}/impact-preview?delay_days=N
GET /api/v1/graph/activity/{activity_id}?depth=N
GET /api/v1/reports/execution-summary?start=...&end=...&discipline=...
POST /api/v1/mock-p6/activities/{activity_id}
```

------------------------------------------------------------------------

# 19. Frontend Requirements

M5 remains the sole frontend owner.

Application pages:

-   Login
-   Claim Intake
-   Daily Digest
-   Review Workspace
-   Dashboard
-   Activity History
-   Impact Preview

New/extended UI:

### Claim Intake

-   static language selector
-   dynamic-language-aware clarification
-   one-question clarification turn
-   voice/text flow
-   source/provenance context

### Review Workspace

-   priority-sorted queue
-   escalation badge
-   provenance chips
-   evidence corroboration/contradiction groups
-   WBS split editor
-   validation/conflict explanations
-   Ask Why inline drill-down

### Dashboard

-   live KPI data
-   delay reasons
-   institutional memory
-   forecast
-   no hardcoded operational counts

### New screen

``` text
AIExecutionSummary.tsx
```

Supervisor only.

### Theme

Dark/light theme behavior is supported across the application.

------------------------------------------------------------------------

# 20. Supporting Product Capabilities

The product includes the following supporting capabilities:

1.  Native P6 `.xer` stacked-table parser.
2.  Robust tabular extraction:
    -   banner-row skipping
    -   column auto-detection
    -   delimiter sniffing
    -   multi-sheet handling where applicable.
3.  Static multilingual UI:
    -   English
    -   Hindi
    -   Telugu.
4.  Telugu localization.
5.  Batch/multi-claim document extraction.
6.  Audio-upload option in Claim Intake where already present.
7.  Dark/light theme provider.
8.  45-activity synthetic benchmark fixtures with multi-date reports and
    ground-truth expectations.
9.  Local P6 mock integration.
10. Fallback frontend mocks controlled by `VITE_USE_MOCKS=true`.

These capabilities support the primary product workflow and are part of the documented product surface.

------------------------------------------------------------------------

# 21. Operational and Reliability Requirements

The product shall provide a predictable execution environment for the complete workflow.

- The configured LLM provider/model shall support the structured extraction path used by the application.
- Dashboard KPIs shall be derived from live application data rather than fixed demo values.
- Canonical XER fixtures shall be stable and deterministic for regression testing.
- Authentication and role-protected endpoints shall be covered by deterministic tests.
- OCR setup shall be documented so scanned-diary intake can be reproduced on the demo environment.
- The default hackathon configuration shall point P6 write-back to the local mock endpoint.
- The application shall retain a deterministic fallback/demo path when external services are unavailable.

------------------------------------------------------------------------

# 22. Core Intelligence Requirements

The product's intelligence layer consists of five core analytical capabilities. Each is deterministic, explainable, and driven by schedule and execution data.

| Capability | Product behavior |
|---|---|
| **Schedule Impact Preview** | Evaluates FS, SS, FF, and SF relationships; applies lag/lead; considers all predecessors, controlling constraints, float, execution state, and bounded downstream propagation. |
| **Out-of-Sequence Validation** | Evaluates actual starts and relevant progress updates against dependency semantics, distinguishing legitimate concurrent work from sequencing violations. |
| **WBS Granularity Bridge** | Decomposes broad claims across eligible sibling activities using progress, status, timing, remaining headroom, dependency order, claim context, planned quantity, and compatible UOMs. |
| **Conflict Detection** | Distinguishes same-date disagreement, normal chronological progress, progress regression, and deterministic incremental-quantity anomalies. |
| **Smart Review Priority** | Combines issue severity, activity criticality/float, and bounded queue aging into an explainable priority score. |

These capabilities form the deterministic decision-support layer between AI-assisted extraction and human approval.

------------------------------------------------------------------------

# 23. Intelligence Acceptance Criteria

## A1 --- Impact Preview

-   [ ] FS successor evaluated.
-   [ ] SS successor evaluated.
-   [ ] FF successor evaluated.
-   [ ] SF relationship handled where supported.
-   [ ] lag/lead applied.
-   [ ] delay within total float -\> `ABSORBED_BY_FLOAT`, net delay 0.
-   [ ] completed successor is not shifted.
-   [ ] in-progress successor uses remaining execution context.
-   [ ] non-controlling predecessor does not create false impact.
-   [ ] bounded multi-hop propagation works.
-   [ ] TC-IMP-01 through TC-IMP-05 pass.

## A2 --- Sequence

-   [ ] ACTUAL_START checked.
-   [ ] relevant PROGRESS_UPDATE checked.
-   [ ] incomplete FS predecessor flags unstarted successor.
-   [ ] SS with predecessor started permits legitimate successor start.
-   [ ] FF finish rule works.
-   [ ] already in-progress successor is not repeatedly flagged.
-   [ ] TC-SEQ-01 through TC-SEQ-04 pass.

## A3 --- WBS

-   [ ] completed sibling receives 0 new split.
-   [ ] future/ineligible sibling is excluded from allocation.
-   [ ] active siblings receive headroom-aware allocation.
-   [ ] dependency/topological order is respected where data exists.
-   [ ] incompatible UOMs cannot be raw-quantity weighted together.
-   [ ] split percentages sum to 1.0000 ± 0.0001.
-   [ ] each split is validated before approval.
-   [ ] TC-WBS-01 through TC-WBS-03 pass.

## A4 --- Conflict

-   [ ] increasing progress on later dates does not create a conflict
    merely because difference \>10.
-   [ ] same-date disagreement beyond tolerance creates
    `SAME_DATE_DISAGREEMENT`.
-   [ ] newer lower cumulative percentage creates `PROGRESS_REGRESSION`.
-   [ ] incremental quantity exceedance is detected.
-   [ ] TC-CONF-01 through TC-CONF-04 pass.

## A5 --- Priority

-   [ ] critical sequence error on critical path scores at least 200
    before aging.
-   [ ] administrative warnings are capped at 25 base points.
-   [ ] aging is capped at 30.
-   [ ] critical error cannot be outranked by minor-warning
    accumulation.
-   [ ] priority reasons are explainable.
-   [ ] TC-PRI-01 through TC-PRI-03 pass.

------------------------------------------------------------------------

# 24. Product Acceptance Criteria

-   [ ] PDF/Excel/CSV/TXT intake works.
-   [ ] typed intake works.
-   [ ] browser voice works.
-   [ ] OCR works on canonical scan.
-   [ ] P6/MSP progress export creates claims.
-   [ ] P6 `.xer` baseline ingestion works.
-   [ ] tabular extraction handles banner/delimiter cases.
-   [ ] batch extraction creates multiple claims where expected.
-   [ ] English/Hindi/Telugu static UI works.
-   [ ] dynamic translation falls back safely.
-   [ ] four-tier matching works.
-   [ ] top-3 candidates retained.
-   [ ] unmatched claims remain visible.
-   [ ] evidence EXIF/GPS checks work.
-   [ ] audit chain remains valid.
-   [ ] approved actuals reconciliation invariants pass.
-   [ ] start/finish merge works.
-   [ ] incremental quantity recalculation works.
-   [ ] CSV export works.
-   [ ] P6 adapter produces canonical payload.
-   [ ] adapter failure does not undo approval.
-   [ ] dashboards use live data.
-   [ ] history works.
-   [ ] forecast works.
-   [ ] role routing works.
-   [ ] backend authorization works.
-   [ ] guaranteed demo path works.

------------------------------------------------------------------------

# 25. Synthetic Demo / Benchmark Data

Canonical data must cover all six disciplines:

``` text
CIVIL
PIPING
STATIC_ROTATING_EQUIPMENT
ELECTRICAL
INSTRUMENTATION
HSE
```

The 45-activity benchmark provides the regression and intelligence-validation dataset for the supported scenarios.

Required cases:

1.  normal exact-ID claim
2.  fuzzy terminology claim
3.  location ambiguity
4.  unmatched claim
5.  broad WBS claim
6.  completed WBS sibling
7.  future WBS sibling
8.  same-date disagreement
9.  normal multi-day progress
10. progress regression
11. incremental quantity accumulation
12. FS sequence violation
13. SS legitimate start
14. FF sequence case
15. critical-path priority case
16. float-absorbed delay
17. controlling vs non-controlling predecessor
18. completed successor in impact preview
19. cross-channel corroboration
20. cross-channel contradiction
21. clarification-required claim
22. English clarification
23. Hindi clarification
24. Telugu clarification
25. OCR diary
26. P6/MSP progress export
27. P6 `.xer` baseline
28. multilingual runtime content
29. execution summary

------------------------------------------------------------------------

# 26. Primary Product Demonstration Flow

Target: approximately 3--5 minutes.

1.  Login as Site Engineer.
2.  Select language.
3.  Submit a field claim.
4.  Show extraction.
5.  If applicable, show one clarification question in the claim's
    language.
6.  Show matching/top candidates or WBS split.
7.  Show deterministic checks.
8.  Switch to Supervisor.
9.  Show priority-sorted review queue.
10. Open a claim.
11. Show provenance.
12. Show evidence/corroboration/contradiction.
13. Click Ask Why.
14. Approve/edit with justification.
15. Show audit chain.
16. Show approved actual.
17. Show CSV/P6 mock write-back.
18. Show live dashboard.
19. Show history/forecast.
20. Optionally show AI Execution Summary.

The demonstration follows the primary workflow and may use deterministic fallback data when an external dependency is unavailable.

------------------------------------------------------------------------

# 27. Release Scope and Future Extensions

## v6 Release Scope

The v6 product release includes:

- Features 1--35.
- Multiformat intake, extraction, matching, validation, approval, reconciliation, export, analytics, history, forecasting, and audit.
- English, Hindi, and Telugu static localization.
- Runtime/dynamic translation for supported generated content.
- Adaptive clarification for incomplete claims.
- WBS granularity bridging and context-aware split allocation.
- Cross-channel evidence fusion and execution knowledge graph.
- Explainable review prioritization.
- Field-level provenance.
- Ask Why investigation.
- AI Execution Summary.
- Dependency-aware impact preview and sequencing analysis.
- Chronological conflict reasoning.
- Regression and benchmark validation across the supported scenarios.

## Product Boundaries

The following are outside the v6 product boundary:

- Full production-grade speech recognition as a required service.
- Paid Whisper services.
- Full photo-content AI verification.
- Enterprise identity management.
- Self-registration and password reset.
- More than two application roles.
- Fine-grained per-activity permission management.
- Live OIL P6 credentials.
- Persistent per-schedule FAISS indexes.
- Automatic rematching of historical claims after schedule replacement.
- Kafka, Redis, Kubernetes, microservices, or distributed transaction infrastructure.
- A fully trained ML forecasting model.
- An unrestricted full-project CPM engine.

## Future Extensions

Potential extensions include a local Whisper fallback, broader CPM analysis, LLM-assisted supervisor justification suggestions, richer geospatial evidence, and one-command containerized deployment.

------------------------------------------------------------------------

# 28. Product Definition of Done

The product satisfies its v6 definition of done when the following end-to-end user journey is supported:

``` text
LOGIN
 ↓
ROLE ROUTING
 ↓
SITE ENGINEER INTAKE
 ↓
EXTRACTION
 ↓
LANGUAGE / PROVENANCE
 ↓
OPTIONAL ONE-QUESTION CLARIFICATION
 ↓
MATCH OR WBS SPLIT
 ↓
DIRECTIONAL CONFLICT + SEQUENCE + EVIDENCE CHECKS
 ↓
RISK-AWARE PRIORITY
 ↓
SUPERVISOR REVIEW
 ↓
APPROVE / EDIT
 ↓
AUDIT
 ↓
APPROVED ACTUALS
 ↓
CSV + P6 MOCK
 ↓
DASHBOARD / HISTORY / FORECAST
 ↓
IMPACT PREVIEW
 ↓
GRAPH / ASK WHY
 ↓
AI EXECUTION SUMMARY
```

The resulting product provides a continuous, auditable path from heterogeneous field evidence to approved project actuals and execution intelligence.

------------------------------------------------------------------------

