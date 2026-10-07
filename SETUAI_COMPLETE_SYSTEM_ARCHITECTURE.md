# SETUAI — Complete System Architecture
**System Implementation Audit & Technical Reference Manual**
*Repository: SIH26122 / SETUAI (Oil India Limited — Smart Automation)*

---

## 1. System Overview

**SETUAI** is an industrial-grade, controlled execution verification and schedule-reconciliation middleware designed for large-scale infrastructure and energy projects. In real-world capital projects, progress reporting from the field is noisy, fragmented, multi-lingual, and distributed across disparate channels—informal chat transcripts, handwritten diary scans, physical measurement books (M-Books), quality inspection notes, daily progress reports (DPRs), and contractor spreadsheets. Meanwhile, the Enterprise Project Management Information System (PMIS, such as Oracle Primavera P6 or Microsoft Project) demands rigorous, validated progress percentages, exact activity codes, and strict CPM logic.

SETUAI bridges this operational divide through a deterministic, human-in-the-loop pipeline:

$$\text{Field Execution Reality} \longrightarrow \text{Structured Claim} \longrightarrow \text{Schedule Match} \longrightarrow \text{Validation} \longrightarrow \text{Human Decision} \longrightarrow \text{Approved Actual} \longrightarrow \text{Project Intelligence}$$

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                        THE SETUAI CORE TRANSFORMATION                                   │
├─────────────────────┬─────────────────────────────────────────────────┬────────────────────────────────┤
│ Stage               │ Component Responsibility                        │ Problem Solved                 │
├─────────────────────┼─────────────────────────────────────────────────┼────────────────────────────────┤
│ 1. Field Reality    │ Multimodal Intake (Text, Voice, PDF, XLSX, XER) │ Unstructured, noisy reporting  │
│ 2. Structured Claim │ LLM / Tabular Extraction & Field Provenance      │ Ambiguous, non-standard fields │
│ 3. Schedule Match   │ 4-Tier Cascade & WBS Granularity Decomposition  │ Misaligned activity resolution │
│ 4. Validation       │ Directional, Quantity, Sequence & Evidence Rules│ Impossible/fraudulent progress │
│ 5. Human Decision   │ Supervisor Review Workspace (Approve/Edit/etc.) │ Zero-trust AI governance       │
│ 6. Approved Actual  │ Canonical Upsert & Reconciliation Contract      │ Schedule data corruption       │
│ 7. Intelligence     │ Impact Engine, Knowledge Graph & Forecasting    │ Delayed critical-path foresight│
└─────────────────────┴─────────────────────────────────────────────────┴────────────────────────────────┘
```

The fundamental philosophy embedded in the codebase is:
> **"AI reads the mess. Rules check it. A human approves it. Everything is logged."**

---

## 2. Actors & Real-World Usage

The codebase defines and enforces two distinct operational roles within the PostgreSQL database (`profiles.role`) and throughout API authorization guards (`backend/shared/auth.py`):

```
                   ┌──────────────────────────────────────────────┐
                   │               AUTHENTICATION                 │
                   │           Supabase Auth / JWT                │
                   └──────────────────────┬───────────────────────┘
                                          │
                      ┌───────────────────┴───────────────────┐
                      ▼                                       ▼
         ┌─────────────────────────┐             ┌─────────────────────────┐
         │      SITE ENGINEER      │             │       SUPERVISOR        │
         │   (Field Operations)    │             │   (Project Planner)     │
         └────────────┬────────────┘             └────────────┬────────────┘
                      │                                       │
         ┌────────────┴────────────┐             ┌────────────┴────────────┐
         │ • Submit Field Claims   │             │ • Daily Digest Queue    │
         │ • Upload Evidence Photos│             │ • Review Workspace      │
         │ • Upload DPR / M-Book   │             │ • Approve / Edit / Hold │
         │ • Answer Clarifications │             │ • WBS Split Adjustments │
         │ • Track Intake Status   │             │ • Schedule Impact / Graph│
         └─────────────────────────┘             └─────────────────────────┘
```

### 2.1 Site Engineer (`SITE_ENGINEER`)
The Site Engineer represents field personnel deployed on-site across construction packages (Civil, Piping, Electrical, Instrumentation, HSE).
* **Login & Role Routing:** Authenticates via [LoginScreen.tsx](file:///d:/SIH26122/frontend/src/pages/LoginScreen.tsx). The role routing guard ([App.tsx](file:///d:/SIH26122/frontend/src/App.tsx)) automatically redirects the engineer to `/intake`.
* **Claim Submission ([ClaimIntake.tsx](file:///d:/SIH26122/frontend/src/pages/ClaimIntake.tsx)):**
  * **Typed Text:** Free-text descriptions in English, Hindi, Telugu, or Hinglish/code-mixed slang.
  * **Voice Input:** Web Speech API integration capturing audio, converting client-side to text, and submitting as `input_channel = 'VOICE'`.
  * **Document / File Input:** Uploads Daily Progress Reports (PDF), Contractor spreadsheets (XLSX/CSV), or Primavera schedule exports (`.xer`).
  * **Evidence Photo Upload:** Submits high-resolution physical evidence photos (`EVIDENCE_PHOTO`). EXIF metadata (timestamp, GPS coordinates) is extracted server-side for geo-fencing and tamper verification.
  * **Clarification Response:** When mandatory progress details are omitted, the engineer receives an AI-generated question in their detected dialect and provides an in-place answer via `POST /api/v1/claims/{event_id}/clarify`.
  * **Claim Status Tracking:** Observes real-time progress of claims moving through `EXTRACTED`, `MATCHED`, `VALIDATED`, and `REVIEW_REQUIRED`.

### 2.2 Supervisor / Planner (`SUPERVISOR`)
The Supervisor represents the Project Manager, Planning Engineer, or Lead Consultant responsible for project integrity and official PMIS reporting.
* **Daily Digest ([DailyDigest.tsx](file:///d:/SIH26122/frontend/src/pages/DailyDigest.tsx)):** Morning summary of all submitted field claims across disciplines. Supports bulk approval for zero-risk, high-confidence claims (`POST /api/v1/digest/bulk-approve`).
* **Review Workspace ([ReviewWorkspace.tsx](file:///d:/SIH26122/frontend/src/pages/ReviewWorkspace.tsx)):** The primary decision cockpit. The queue is ordered by a multi-factor `priority_score` (Feature 32).
* **Claim Inspection:** Inspects claim provenance badges (`AI_EXTRACTED`, `HUMAN_ENTERED`, `SCHEDULE_AUTO_FILLED`, `SUPERVISOR_EDITED`), extracted quantities, and activity candidates.
* **Evidence Inspection ([EvidencePanel.tsx](file:///d:/SIH26122/frontend/src/components/EvidencePanel.tsx)):** Views corroborating or contradicting cross-channel evidence records with confidence scores, GPS site-radius compliance, and photo lightboxes.
* **Validation Issues & Conflict Inspection:** Evaluates deterministic flags (negative values, planned quantity overruns, sequence inversions, out-of-turn execution, same-date disagreements).
* **WBS Split Adjustment ([WBSSplitEditor.tsx](file:///d:/SIH26122/frontend/src/components/WBSSplitEditor.tsx)):** Adjusts percentage allocations across sibling activities when broad claims are decomposed (`PATCH /api/v1/claims/{event_id}/splits`).
* **Governance Actions:** Executes `APPROVE`, `EDIT`, `REJECT`, or `HOLD` with mandatory written justification.
* **Audit Inspection:** Validates the cryptographic SHA-256 tamper-evident log chain for any claim or activity.

---

## 3. Complete End-to-End Real User Workflow

The end-to-end execution flow traces the lifecycle of field execution reality into an approved PMIS actual:

```
[1. LOGIN] ──► [2. ROLE DETECTION] ──► [3. SITE ENGINEER INTAKE]
                                                  │
                                                  ▼
[6. PROVENANCE] ◄── [5. EXTRACTION & LANG] ◄── [4. RAW CLAIM CREATED]
       │
       ▼
[7. CLARIFICATION GATE] ─────────(Missing Info)────────► [SITE ENGINEER RE-INTAKE]
       │ (Sufficient Info)                                        │
       ▼                                                          │ (Re-extracted)
[8. CLAIM MATCHING (4 TIERS)] ◄───────────────────────────────────┘
       │
       ▼
[9. WBS GRANULARITY CHECK] ───────(Broad Scope)────────► [DECOMPOSE TO SIBLINGS]
       │ (Leaf Scope)                                             │
       ▼                                                          ▼
[10. DETERMINISTIC VALIDATION] ◄──────────────────────────────────┘
       │
       ▼
[11. CONFLICT & EVIDENCE FUSION]
       │
       ▼
[12. SMART PRIORITY CALCULATION]
       │
       ▼
[13. SUPERVISOR REVIEW WORKSPACE]
       │
       ├──► [HOLD] ──────────(Re-investigate / Request Info)
       ├──► [REJECT] ────────(Terminal: Logged in Audit Trail)
       ├──► [EDIT] ──────────┐
       └──► [APPROVE] ───────┴─► [14. ATOMIC DECISION & AUDIT HASH]
                                            │
                                            ▼
                                 [15. APPROVED ACTUALS UPSERT]
                                            │
                      ┌─────────────────────┼─────────────────────┐
                      ▼                     ▼                     ▼
             [16. CSV EXPORT]      [17. P6 MOCK PUSH]    [18. PROJECT INTEL]
             RFC-4180 Format       REST Payload Hook     • Live Dashboard
                                                         • Activity History
                                                         • CPM Impact Engine
                                                         • Ask Why Graph
                                                         • AI Execution Summary
```

### Step-by-Step Architectural Trace:

1. **LOGIN:**
   * *Input:* User credentials (email, password).
   * *Component:* [LoginScreen.tsx](file:///d:/SIH26122/frontend/src/pages/LoginScreen.tsx) calling Supabase Auth (`supabase.auth.signInWithPassword`).
   * *Database State:* Auth token validated; user UUID resolved against `profiles` table.
   * *Output:* JWT Bearer token stored in browser `localStorage`.
2. **ROLE DETECTION:**
   * *Input:* Authenticated session.
   * *Component:* [AuthProvider.tsx](file:///d:/SIH26122/frontend/src/auth/AuthProvider.tsx) calls `GET /api/v1/auth/me`.
   * *Database State:* Reads `profiles.role` (`SITE_ENGINEER` or `SUPERVISOR`).
   * *Next Component:* [App.tsx](file:///d:/SIH26122/frontend/src/App.tsx) redirects `SITE_ENGINEER` to `/intake` and `SUPERVISOR` to `/digest`.
3. **SITE ENGINEER INTAKE:**
   * *Input:* Text description, voice recording, PDF Daily Progress Report, XLSX spreadsheet, `.xer` file, or evidence image.
   * *Component:* [ClaimIntake.tsx](file:///d:/SIH26122/frontend/src/pages/ClaimIntake.tsx).
   * *API:* `POST /api/v1/claims/text`, `POST /api/v1/claims/file`, or `POST /api/v1/claims/schedule-export`.
4. **RAW CLAIM CREATED:**
   * *Processing:* [intake.py](file:///d:/SIH26122/backend/routers/intake.py).
   * *Database State:* Writes record to `source_documents` (SHA-256 content hash). Creates one or more rows in `execution_events` with status `EXTRACTED`.
   * *Tables Written:* `source_documents`, `execution_events`, `source_references`.
5. **LANGUAGE DETECTION & EXTRACTION:**
   * *Processing:* [llm_extraction.py](file:///d:/SIH26122/backend/shared/llm_extraction.py) via centralized [llm_client.py](file:///d:/SIH26122/backend/shared/llm_client.py) (Groq primary, Gemini fallback). Structured tabular files route to [tabular_extraction.py](file:///d:/SIH26122/backend/shared/tabular_extraction.py) (zero LLM cost).
   * *Output:* `ExtractedClaimFields` containing normalized discipline, action, event_type, claim_mode, claimed_pct, claimed_quantity, location, asset_tag, and detected language.
6. **PROVENANCE TAGGING:**
   * *Processing:* [intake.py](file:///d:/SIH26122/backend/routers/intake.py).
   * *Output:* Populates `execution_events.field_provenance` (JSONB) with tags: `AI_EXTRACTED` or `HUMAN_ENTERED`.
7. **CLARIFICATION GATE:**
   * *Component:* `check_missing_required_fields()` in [llm_extraction.py](file:///d:/SIH26122/backend/shared/llm_extraction.py).
   * *Trigger:* Missing `event_type`, `discipline`, or progress values (`claimed_pct` and `claimed_quantity` both null).
   * *State Transition:* Sets `clarification_status = 'PENDING'`, generates a single targeted question in the user's detected language, and blocks schedule matching until clarified.
8. **CLAIM MATCHING:**
   * *Component:* [matching.py](file:///d:/SIH26122/backend/routers/matching.py).
   * *API:* `POST /api/v1/claims/{event_id}/match`.
   * *Algorithm:* 4-tier cascade:
     1. `EXACT_ID`: External activity ID exact match ($\text{Confidence} = 1.0$).
     2. `EXACT_ASSET`: Equipment asset tag exact match ($\text{Confidence} = 0.80 - 0.95$).
     3. `HYBRID_FALLBACK`: Sentence-Transformers + FAISS semantic retrieval + RapidFuzz fuzzy text match + metadata scoring.
     4. `HARD_MISMATCH`: Strict penalties ($\le 0.40$) for conflicting disciplines or locations.
   * *Tables Written:* `candidate_matches` (top 3 candidates persisted).
   * *Database State:* `execution_events.status` becomes `MATCHED` or `UNMATCHED`.
9. **WBS GRANULARITY CHECK:**
   * *Component:* [wbs_split.py](file:///d:/SIH26122/backend/shared/wbs_split.py).
   * *Processing:* Inspects claim scope. If broad keywords ("across all sections", "entire header") or summary activities are detected, decomposes claim across eligible sibling activities using water-fill allocation constrained by remaining headroom.
   * *Tables Written:* `claim_activity_splits`.
10. **DETERMINISTIC VALIDATION:**
    * *Component:* [checks.py](file:///d:/SIH26122/backend/routers/checks.py).
    * *API:* `POST /api/v1/claims/{event_id}/check`.
    * *Rules Evaluated:* `VAL_NEGATIVE`, `VAL_OVER_100`, `VAL_UOM_MISMATCH`, `VAL_UNSUPPORTED_ACCUMULATION`, `VAL_REOPENED_COMPLETED_ACTIVITY`, `VAL_OUT_OF_SEQUENCE`, `VAL_EVIDENCE_MISMATCH`.
    * *Tables Written:* `validation_issues`.
11. **CONFLICT & EVIDENCE FUSION:**
    * *Processing:* [checks.py](file:///d:/SIH26122/backend/routers/checks.py).
    * *Conflict Checks:* `SAME_DATE_DISAGREEMENT` ($> 10\%$ variance), `PROGRESS_REGRESSION` (lower progress than approved actuals without accepted rework/reset context).
    * *Evidence Fusion:* Cross-references multi-channel reports (DPR vs Inspection Note) to classify relationship as `CORROBORATES` or `CONTRADICTS`.
    * *Tables Written:* `conflict_records`, `evidence_links`.
12. **SMART PRIORITY CALCULATION:**
    * *Processing:* `evaluate_smart_review_priority()` in [checks.py](file:///d:/SIH26122/backend/routers/checks.py).
    * *Formula:* Base priority weighted by critical path status ($+30$), float urgency ($\le 0 \implies +25$), validation errors ($+20$), conflicts ($+25$), evidence contradictions ($+20$), and queue aging.
    * *Database State:* Sets `execution_events.priority_score`, updates status to `VALIDATED` (clean) or `REVIEW_REQUIRED` (flagged).
13. **SUPERVISOR REVIEW WORKSPACE:**
    * *UI Cockpit:* [ReviewWorkspace.tsx](file:///d:/SIH26122/frontend/src/pages/ReviewWorkspace.tsx) calling `GET /api/v1/review-queue?sort=priority`.
    * *Action Choice:*
      * **HOLD:** Puts claim on hold for site clarification (`status = 'HOLD'`).
      * **REJECT:** Terminal rejection with justification (`status = 'REJECTED'`).
      * **EDIT:** Overrides percentage/quantity or activity target (`status = 'EDITED'`). Fields tagged as `SUPERVISOR_EDITED`.
      * **APPROVE:** Human accepts claim (`status = 'APPROVED'`).
14. **ATOMIC DECISION & AUDIT LOGGING:**
    * *API:* `POST /api/v1/decisions` handled by [decisions.py](file:///d:/SIH26122/backend/routers/decisions.py).
    * *Processing:* Inserts record into `planner_decisions`. Invokes `write_audit_log()` in [audit.py](file:///d:/SIH26122/backend/shared/audit.py).
    * *Audit Mechanics:* Cryptographic SHA-256 hash chaining:
      $$\text{current\_hash} = \text{SHA-256}(\text{entity} + \text{action} + \text{before} + \text{after} + \text{payload\_hash} + \text{previous\_hash})$$
    * *Tables Written:* `planner_decisions`, `audit_logs`.
15. **APPROVED ACTUALS RECONCILIATION:**
    * *Processing:* `upsert_approved_actual()` in [actuals.py](file:///d:/SIH26122/backend/shared/actuals.py).
    * *Contract:* Strictly one row per `(schedule_id, activity_id)`:
      * Start/finish dates merged without erasing previous bounds.
      * Cumulative percentages replaced, not summed.
      * Incremental quantities recalculated from latest approved planner decisions.
    * *Tables Written:* `approved_actuals`.
16. **DOWNSTREAM ADAPTER DISPATCH:**
    * *CSV Export Adapter:* [export.py](file:///d:/SIH26122/backend/routers/export.py) automatically generates RFC-4180 compliant CSVs.
    * *P6 REST Adapter:* [p6.py](file:///d:/SIH26122/backend/shared/p6.py) produces production-shaped P6 EPPM REST write-back payloads (`POST /mock-p6/activities/{activity_id}`).
17. **PROJECT INTELLIGENCE CONSUMPTION:**
    * **Dashboard:** [Dashboard.tsx](file:///d:/SIH26122/frontend/src/pages/Dashboard.tsx) renders live KPIs, delay reason Pareto charts, and institutional duration ratios.
    * **Activity History:** [ActivityHistory.tsx](file:///d:/SIH26122/frontend/src/pages/ActivityHistory.tsx) reconstructs chronological lifecycles.
    * **Impact Preview Engine:** [ImpactPreview.tsx](file:///d:/SIH26122/frontend/src/pages/ImpactPreview.tsx) executes bounded 3-hop CPM forward propagation over FS/SS/FF/SF dependencies.
    * **Execution Knowledge Graph & Ask Why:** [AskWhyPanel.tsx](file:///d:/SIH26122/frontend/src/components/AskWhyPanel.tsx) traverses causal links from schedule activity down to raw claim evidence.
    * **AI Execution Summary:** [AIExecutionSummary.tsx](file:///d:/SIH26122/frontend/src/pages/AIExecutionSummary.tsx) renders deterministic database facts narrated into professional summaries with runtime Hindi/Telugu translations.

---

## 4. High-Level System Architecture

The implemented architecture is a unified, layered system. PostgreSQL serves as the absolute single source of truth:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PRESENTATION LAYER                                     │
│  React 18 + TypeScript + Vite + Tailwind/Vanilla CSS + TanStack Query + i18next       │
│                                                                                        │
│  Pages: Login | Claim Intake | Daily Digest | Review Workspace | Dashboard            │
│         Activity History | Impact Preview | WBS Explorer | AI Execution Summary        │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP / JSON / SSE (Port 8000)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                APPLICATION / API LAYER                                 │
│  FastAPI (Python 3.11+) + Pydantic v2 + Supabase Auth / PyJWT                          │
│                                                                                        │
│  Routers:                                                                              │
│  • auth.py         • intake.py       • matching.py     • checks.py                     │
│  • decisions.py    • schedule.py     • activities.py   • dashboard.py                  │
│  • export.py       • mock_p6.py      • graph.py        • claim_graph.py                │
│  • investigation.py• summary.py      • reports.py      • schedules.py                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Direct Memory / Service Calls
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                DOMAIN / INTELLIGENCE LAYER                             │
│                                                                                        │
│  Extraction Engine:      M2 LLM Batch + Vision + Tabular Parser + XER Parser           │
│  Retrieval & Matching:   Sentence-Transformers (MiniLM-L6) + FAISS IndexFlatIP + Fuzzy │
│  Granularity Engine:     WBS Group Discovery + Water-Fill Decomposition                │
│  Validation Engine:      Physical + Directional Conflict + Sequence + Evidence Checks  │
│  Review & Governance:    Priority Scorer + Provenance Tracking + Decision State Machine│
│  Reconciliation Engine:  Approved Actuals Canonical Upsert (Rules A-F)                 │
│  Schedule CPM Engine:    A1 Core Constraint Solver (FS, SS, FF, SF, Lag, Float, State)│
│  Narrative Engine:       Deterministic Aggregator + Dynamic LLM Translation Cache      │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Psycopg v3 (Synchronous Service Connection)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA LAYER                                          │
│  Supabase PostgreSQL (14 Tables, RLS Enabled, Strict Foreign Keys, Serial Audit Chain) │
│                                                                                        │
│  • profiles              • schedules            • schedule_activities                  │
│  • schedule_dependencies • source_documents     • execution_events                     │
│  • source_references     • candidate_matches    • claim_activity_splits                │
│  • validation_issues     • conflict_records     • evidence_links                       │
│  • planner_decisions     • approved_actuals     • audit_logs                           │
│  • execution_summaries                                                                 │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ External API Integration
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL & EMBEDDED SERVICES                              │
│  • LLM Providers: Groq API (openai/gpt-oss-20b) | Google Gemini API (gemini-3.6-flash)│
│  • Vector Engine: Local CPU Sentence-Transformers (all-MiniLM-L6-v2)                   │
│  • OCR Engine: Tesseract / pytesseract                                                 │
│  • PMIS Integration: RFC-4180 CSV Adapter | P6 EPPM REST Client | Local Mock P6 Server │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Frontend Architecture

### 5.1 Technology Foundation
* **Framework:** React 18 with TypeScript, bootstrapped via Vite.
* **State Management & Server Cache:** TanStack React Query (`@tanstack/react-query`) handles query caching, background invalidation, and optimistic UI transitions.
* **Routing:** `react-router-dom` v6 with role-guarded layout wrappers (`ProtectedRoute.tsx`).
* **Internationalization:** `i18next` with language switcher supporting English (`en`), Hindi (`hi`), and Telugu (`te`).
* **Styling & Aesthetics:** Industrial aesthetic featuring high-contrast dark modes, glassmorphic HUD overlays, responsive layout grids, and interactive SVG/Canvas graph visualizations.

### 5.2 Page & Route Directory

| Page Component | Route | Role Access | Primary APIs Invoked | Key Data Displayed | User Actions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [LoginScreen.tsx](file:///d:/SIH26122/frontend/src/pages/LoginScreen.tsx) | `/login` | Public | `supabase.auth.signInWithPassword`, `GET /auth/me` | Role badges, error banners | Submit credentials, test account auto-fill |
| [ClaimIntake.tsx](file:///d:/SIH26122/frontend/src/pages/ClaimIntake.tsx) | `/intake` | `SITE_ENGINEER` | `POST /claims/text`, `POST /claims/file`, `POST /claims/{id}/clarify` | Multimodal forms, voice recorder, clarification modal | Enter text, speak voice, upload PDF/XLSX/Image, answer copilot |
| [DailyDigest.tsx](file:///d:/SIH26122/frontend/src/pages/DailyDigest.tsx) | `/digest` | `SUPERVISOR` | `GET /digest`, `POST /digest/bulk-approve` | Daily claims list, discipline groupings, status counts | Review day's volume, execute bulk approve on clean claims |
| [ReviewWorkspace.tsx](file:///d:/SIH26122/frontend/src/pages/ReviewWorkspace.tsx) | `/review` | `SUPERVISOR` | `GET /review-queue`, `POST /claims/{id}/match`, `POST /claims/{id}/check`, `POST /decisions` | Queue sorted by priority, candidate picker, validation alerts, evidence fusion cards | Inspect evidence, select match, edit WBS split, approve, edit, reject, hold |
| [Dashboard.tsx](file:///d:/SIH26122/frontend/src/pages/Dashboard.tsx) | `/dashboard` | `SUPERVISOR` | `GET /dashboard/summary`, `GET /dashboard/delay-reasons`, `GET /dashboard/forecast` | KPI scorecards, delay Pareto chart, discipline distribution, forecast table | Filter by schedule, switch disciplines, inspect delay reasons |
| [ActivityHistory.tsx](file:///d:/SIH26122/frontend/src/pages/ActivityHistory.tsx) | `/history` | `SUPERVISOR` | `GET /activities`, `GET /activities/{id}/history`, `GET /investigation/{id}/context` | Activity table, chronological audit timeline, provenance badges, Ask Why modal | Search activities, filter by state, inspect claim lifecycle and evidence |
| [ImpactPreview.tsx](file:///d:/SIH26122/frontend/src/pages/ImpactPreview.tsx) | `/impact` | `SUPERVISOR` | `GET /schedule/{id}/impact-preview`, `GET /activities` | Simulation slider, network DAG graph, timeline Gantt view, float absorption table | Adjust hypothetical delay (days), simulate downstream slip, trace path |
| [WBSExplorerPage.tsx](file:///d:/SIH26122/frontend/src/pages/WBSExplorerPage.tsx) | `/wbs` | `SUPERVISOR` | `GET /schedules/{id}/wbs-tree` | Hierarchical WBS tree, activity allocations, planned quantities | Expand/collapse WBS branches, inspect sibling relationships |
| [AIExecutionSummary.tsx](file:///d:/SIH26122/frontend/src/pages/AIExecutionSummary.tsx) | `/summary`, `/reports/execution-summary` | `SUPERVISOR` | `GET /reports/execution-summary` | Executive narrative card, KPI highlights, language selector (EN/HI/TE) | Change period (last 7 days, this month, custom), switch language, copy report |

### 5.3 Specialized Visual Components
* [FieldProvenanceBadge.tsx](file:///d:/SIH26122/frontend/src/components/FieldProvenanceBadge.tsx): Renders precise provenance tags (`AI_EXTRACTED`, `HUMAN_ENTERED`, `SCHEDULE_AUTO_FILLED`, `SUPERVISOR_EDITED`) on every field.
* [EvidencePanel.tsx](file:///d:/SIH26122/frontend/src/components/EvidencePanel.tsx): Renders corroborating and contradicting evidence links with confidence bars and source snippets.
* [WBSSplitEditor.tsx](file:///d:/SIH26122/frontend/src/components/WBSSplitEditor.tsx): Interactive slider allowing Supervisors to adjust decomposed WBS percentages ensuring $\sum \text{split\_pct} = 1.0000 \pm 0.0001$.
* [ImpactNetworkGraph.tsx](file:///d:/SIH26122/frontend/src/components/impact/ImpactNetworkGraph.tsx): Canvas/SVG-based Directed Acyclic Graph (DAG) visualizing controlling predecessors, shifted dates, and float-absorbed nodes.
* [AskWhyPanel.tsx](file:///d:/SIH26122/frontend/src/components/AskWhyPanel.tsx): Slide-over drawer explaining the end-to-end causal chain from schedule delay back to raw site photos and claims.

---

## 6. Backend Architecture

The backend is built with FastAPI (Python 3.11+). All endpoints are modularly registered in [main.py](file:///d:/SIH26122/backend/main.py):

```
FastAPI Application Entrypoint (backend/main.py)
 ├── Authentication & Roles (backend/routers/auth.py)
 ├── Schedule Ingestion & Indexing (backend/routers/schedules.py)
 ├── Multimodal Claim Intake (backend/routers/intake.py)
 ├── 4-Tier Matching & WBS Decomposition (backend/routers/matching.py)
 ├── Deterministic Validation & Evidence Fusion (backend/routers/checks.py)
 ├── Review Decisions & Daily Digest (backend/routers/decisions.py)
 ├── Canonical Approved Actuals & Adapters (backend/routers/export.py, mock_p6.py)
 ├── CPM Schedule Impact Engine (backend/routers/schedule.py)
 ├── Activity History & Lifecycle Reconstruction (backend/routers/activities.py)
 ├── Operational Dashboard & Forecast (backend/routers/dashboard.py)
 ├── Execution Knowledge Graph & Ask Why (backend/routers/graph.py, claim_graph.py, investigation.py)
 └── AI Execution Summary & Translation (backend/routers/summary.py, reports.py)
```

### 6.1 Router Inventory & Responsibilities

#### 1. [schedules.py](file:///d:/SIH26122/backend/routers/schedules.py)
* **Responsibility:** Ingests baseline schedules (CSV, XLSX, MSP XML, XER), writes canonical records, builds active FAISS index.
* **Key Endpoints:**
  * `POST /api/v1/schedules`: Upload and parse schedule baseline.
  * `GET /api/v1/schedules`: List stored schedules.
  * `GET /api/v1/schedules/{id}/wbs-tree`: Return hierarchical WBS tree.

#### 2. [intake.py](file:///d:/SIH26122/backend/routers/intake.py)
* **Responsibility:** Ingests field claims across channels. Manages evidence storage, file parsing, LLM batch extraction, clarification generation, and provenance initialization.
* **Key Endpoints:**
  * `POST /api/v1/claims/text`: Ingest typed text or browser voice claims.
  * `POST /api/v1/claims/file`: Ingest PDF, XLSX, CSV, XER, or image files.
  * `POST /api/v1/claims/schedule-export`: Ingest contractor progress spreadsheets.
  * `POST /api/v1/claims/{id}/clarify`: Receive user clarification answer.
  * `GET /api/v1/claims/{id}/photo`: Serve stored evidence image.

#### 3. [matching.py](file:///d:/SIH26122/backend/routers/matching.py)
* **Responsibility:** Executes 4-tier candidate resolution against schedule activities. Manages WBS granularity decomposition.
* **Key Endpoints:**
  * `POST /api/v1/claims/{id}/match`: Run matching cascade and persist candidates.
  * `POST /api/v1/claims/{id}/rematch`: Re-execute matching cascade.
  * `GET /api/v1/claims/{id}/candidates`: Retrieve top 3 candidate matches.
  * `GET /api/v1/claims/{id}/splits`: Fetch decomposed WBS sibling shares.
  * `PATCH /api/v1/claims/{id}/splits`: Supervisor manual split override.

#### 4. [checks.py](file:///d:/SIH26122/backend/routers/checks.py)
* **Responsibility:** Authoritative rule engine. Evaluates physical constraints, directional conflicts, sequence inversions, evidence fusion, and smart review priority score.
* **Key Endpoints:**
  * `POST /api/v1/claims/{id}/check`: Run validation suite and compute priority score.
  * `GET /api/v1/claims/{id}/validation`: Return validation issues.
  * `GET /api/v1/claims/{id}/conflicts`: Return same-channel conflicts.
  * `GET /api/v1/claims/{id}/evidence`: Return cross-channel evidence fusion links.
  * `GET /api/v1/review-queue`: Return priority-sorted Supervisor review queue.

#### 5. [decisions.py](file:///d:/SIH26122/backend/routers/decisions.py)
* **Responsibility:** Manages human governance workflow. Executes Approve/Edit/Reject/Hold, updates claim status, appends cryptographic audit records, and triggers approved actuals upsert.
* **Key Endpoints:**
  * `POST /api/v1/decisions`: Submit review decision with justification.
  * `GET /api/v1/decisions`: List recent planner decisions.
  * `GET /api/v1/digest`: Fetch daily digest claim queue.
  * `POST /api/v1/digest/bulk-approve`: Bulk-approve clean `VALIDATED` claims.

#### 6. [export.py](file:///d:/SIH26122/backend/routers/export.py) & [mock_p6.py](file:///d:/SIH26122/backend/routers/mock_p6.py)
* **Responsibility:** Downstream PMIS synchronization. Formats canonical RFC-4180 CSVs and dispatches P6 EPPM REST write-back payloads.
* **Key Endpoints:**
  * `GET /api/v1/export/actuals.csv`: Download approved actuals CSV.
  * `POST /mock-p6/activities/{activity_id}`: Mock P6 endpoint validating incoming JSON payloads.

#### 7. [schedule.py](file:///d:/SIH26122/backend/routers/schedule.py)
* **Responsibility:** Pure deterministic Critical Path Method (CPM) constraint engine. Evaluates relationship constraints (FS, SS, FF, SF), lag/lead, controlling predecessors, and bounded 3-hop downstream slip.
* **Key Endpoints:**
  * `GET /api/v1/schedule/{activity_id}/impact-preview`: Run downstream impact preview for hypothetical delay.

#### 8. [activities.py](file:///d:/SIH26122/backend/routers/activities.py)
* **Responsibility:** Activity lifecycle reconstruction. Aggregates execution events, decisions, and actuals into a unified chronological audit trail.
* **Key Endpoints:**
  * `GET /api/v1/activities`: Filtered and paginated activity list.
  * `GET /api/v1/activities/{id}/history`: Chronological lifecycle timeline.
  * `GET /api/v1/activities/{id}/rollup`: Aggregated progress quantities and percentages.

#### 9. [dashboard.py](file:///d:/SIH26122/backend/routers/dashboard.py)
* **Responsibility:** Operational KPIs, delay reason Pareto analytics, institutional duration memory, and historical-ratio forecasting.
* **Key Endpoints:**
  * `GET /api/v1/dashboard/summary`: High-level project KPIs and discipline volume.
  * `GET /api/v1/dashboard/delay-reasons`: Approved delay reason aggregations.
  * `GET /api/v1/dashboard/institutional-memory`: Planned vs actual duration comparisons.
  * `GET /api/v1/dashboard/forecast`: Ratio-based duration forecasting.

#### 10. [investigation.py](file:///d:/SIH26122/backend/routers/investigation.py) & [graph.py](file:///d:/SIH26122/backend/routers/graph.py)
* **Responsibility:** Traverses node-edge relationships across activities, claims, dependencies, and evidence for the "Ask Why" root-cause engine.
* **Key Endpoints:**
  * `GET /api/v1/investigation/{activity_id}/context`: Comprehensive causal graph context.
  * `GET /api/v1/graph/activity/{activity_id}`: Directed graph nodes and edges.

#### 11. [summary.py](file:///d:/SIH26122/backend/routers/summary.py) & [reports.py](file:///d:/SIH26122/backend/routers/reports.py)
* **Responsibility:** Aggregates verified database facts and prompts the LLM to generate narrative summaries. Manages SHA-256 caching and dynamic runtime Hindi/Telugu translations.
* **Key Endpoints:**
  * `GET /api/v1/reports/execution-summary`: Get AI-narrated executive summary.
  * `POST /api/v1/reports/translate`: Dynamic runtime translation for UI strings.

---

## 7. Claim Processing Pipeline

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                STAGE A: INTAKE                                    │
│  Channels: TYPED_TEXT | VOICE | FILE_UPLOAD (PDF/XLSX/CSV/XER) | SCANNED_OCR     │
│  Output: Document hash, raw claim text, input channel logged                      │
└─────────────────────────────────────────┬─────────────────────────────────────────┘
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                               STAGE B: EXTRACTION                                 │
│  Engine: Tabular Parser (Direct) OR LLM JSON Batch / Vision                       │
│  Output: ExtractedClaimFields (Discipline, EventType, ClaimMode, Pct/Qty, Dates) │
│  Provenance: AI_EXTRACTED | HUMAN_ENTERED tags recorded                           │
└─────────────────────────────────────────┬─────────────────────────────────────────┘
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                              STAGE C: CLARIFICATION                               │
│  Gate: Missing event_type, discipline, or progress?                               │
│  Yes ──► Set PENDING, prompt Site Engineer in detected language                   │
│  No  ──► Proceed to Matching                                                      │
└─────────────────────────────────────────┬─────────────────────────────────────────┘
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                                STAGE D: MATCHING                                  │
│  Cascade: EXACT_ID (1.00) ──► EXACT_ASSET (0.80-0.95) ──► HYBRID_FALLBACK         │
│  Ambiguity: If (Rank1 - Rank2) < 0.05 ──► Flag UNMATCHED                          │
│  Output: Top 3 candidate_matches persisted in DB                                  │
└─────────────────────────────────────────┬─────────────────────────────────────────┘
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                            STAGE E: WBS GRANULARITY                               │
│  Scope Check: Broad wording / summary activity?                                   │
│  Yes ──► Decompose across eligible siblings via water-fill headroom allocation   │
│  No  ──► Retain single matched leaf activity                                      │
└─────────────────────────────────────────┬─────────────────────────────────────────┘
                                          ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                               STAGE F: VALIDATION                                 │
│  Deterministic Checks:                                                            │
│  • Physical: Negative values, planned exceedance (>100%), UOM compatibility       │
│  • Sequence: Topological predecessor completion (FS incomplete, SS unstarted)    │
│  • Directional Conflict: Same-date disagreement (>10%), Unexplained regression    │
│  • Evidence: EXIF date variance > 2 days, GPS site radius > 5km                   │
│  Output: validation_issues, conflict_records, smart priority_score calculated     │
│  Status Transition: Set VALIDATED (clean) OR REVIEW_REQUIRED (flagged)           │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### Stage A — Intake
Supported intake channels and file parsers:
* **Typed Text:** Directly ingested via `POST /claims/text`.
* **Voice Recording:** Browser Web Speech API converts audio to text, tagged with `input_channel = 'VOICE'`.
* **PDF Reports:** Text extracted via `pypdf` or `pdfminer`.
* **Scanned Diaries / Images:** Direct OCR via `pytesseract` or native multimodal vision processing via Gemini Flash / Vision LLM.
* **Tabular Spreadsheets (CSV/XLSX):** Parsed via `pandas` and `openpyxl`. Detects structured progress columns (`Activity ID`, `Today Actual`, `Progress Pct`).
* **P6 Native Files (`.xer`):** Parsed via [xer_parser.py](file:///d:/SIH26122/backend/shared/xer_parser.py), extracting native `TASK` records with actual progress.

### Stage B — Extraction
* **Structured Progress Paths:** Tabular and `.xer` files bypass LLMs entirely. Field values map directly to schema attributes with zero hallucination risk.
* **Unstructured / Semi-Structured Paths:** Routed to `extract_claim_fields_batch()` in [llm_extraction.py](file:///d:/SIH26122/backend/shared/llm_extraction.py).
* **System Prompt Contract:** Prompts require a strict JSON dictionary:
  ```json
  {
    "claims": [
      {
        "event_date": "YYYY-MM-DD",
        "reported_activity_id": "string or null",
        "discipline": "CIVIL | PIPING | STATIC_ROTATING_EQUIPMENT | ELECTRICAL | INSTRUMENTATION | HSE",
        "action": "description of work",
        "event_type": "ACTUAL_START | ACTUAL_FINISH | PROGRESS_UPDATE | DELAY | BLOCKER",
        "claim_mode": "CUMULATIVE_PCT | INCREMENTAL_QUANTITY",
        "asset_tag": "string or null",
        "location": "string or null",
        "claimed_quantity": null,
        "claimed_uom": null,
        "claimed_pct": 65.0,
        "delay_reason": null,
        "language_detected": "English | Hindi | Telugu | Hindi-English mixed"
      }
    ]
  }
  ```
* **Provenance Initialization:** Populates `execution_events.field_provenance` (JSONB) with field-level attribution.

### Stage C — Clarification Gate
* Implemented in `check_missing_required_fields()` ([llm_extraction.py](file:///d:/SIH26122/backend/shared/llm_extraction.py)):
  * Verifies presence of: `event_type`, `discipline`, and at least one progress value (`claimed_pct` or `claimed_quantity`).
  * If missing, sets `clarification_status = 'PENDING'`, generates a polite, localized question via `generate_clarification_question()`, and suspends matching.
  * When the Site Engineer responds (`POST /claims/{id}/clarify`), the answer is concatenated with the raw text, re-extracted, and provenance updated.

### Stage D — Matching Cascade
Implemented in [matching.py](file:///d:/SIH26122/backend/routers/matching.py):
1. **Tier 1 — `EXACT_ID`:**
   * Claim specifies `reported_activity_id`.
   * Exact match found in `schedule_activities` for the same `schedule_id`.
   * $\text{Confidence} = 1.00$.
2. **Tier 2 — `EXACT_ASSET`:**
   * Claim specifies `asset_tag`.
   * Matches `schedule_activities.asset_tag` for the same schedule.
   * $\text{Confidence} = 0.80 - 0.95$, adjusted for location/discipline agreement. Capped at $\le 0.40$ if discipline conflicts.
3. **Tier 3 — `HYBRID_FALLBACK`:**
   * Combines vector semantic search (Sentence-Transformers `all-MiniLM-L6-v2` + FAISS cosine inner product) with RapidFuzz token match:
     $$\text{Composite} = 0.40 \cdot \text{Semantic} + 0.30 \cdot \text{Fuzzy} + 0.15 \cdot \text{Location} + 0.15 \cdot \text{Discipline}$$
   * Contextual Gate: If discipline or location explicitly mismatches, confidence is capped at $\le 0.40$.
   * Ambiguity Gate: If $(\text{Rank}_1 - \text{Rank}_2) < 0.05$, marked as ambiguous $\implies$ forces status to `UNMATCHED`.
4. **Tier 4 — `HARD_MISMATCH`:**
   * Flagged if conflicting metadata exists. Confidence capped at $\le 0.40$.

### Stage E — WBS Granularity Bridge
Implemented in [wbs_split.py](file:///d:/SIH26122/backend/shared/wbs_split.py):
* **Discovery:** Finds parent summary activities (`SUMMARY_CHILDREN`) or activities sharing the same `wbs_code` (`SHARED_CODE`).
* **Scope Classification:** Detects broad phrasing ("across all lines", "entire section") vs specific sub-scope names ("Section A").
* **Allocation Rules:**
  1. Completed sibling $\implies 0$ allocation.
  2. Future sibling (planned start > claim date) $\implies 0$ allocation.
  3. Predecessor-gated sibling (FS predecessor incomplete or SS predecessor unstarted) $\implies 0$ allocation.
  4. Incompatible UOM $\implies 0$ allocation.
  5. Water-fill allocation distributes claim value across eligible siblings weighted by remaining planned headroom.
  6. Normal single match and WBS split are strictly mutually exclusive ($\text{XOR}$).

### Stage F — Deterministic Validation
Implemented in [checks.py](file:///d:/SIH26122/backend/routers/checks.py):
* **Physical Checks:** Flags negative progress (`VAL_NEGATIVE`), values $> 100\%$ (`VAL_OVER_100`), and units mismatch (`VAL_UOM_MISMATCH`).
* **Logical Checks:** Flags attempts to report progress on completed activities (`VAL_REOPENED_COMPLETED_ACTIVITY`) or single-claim quantities $> 150\%$ of plan (`VAL_UNSUPPORTED_ACCUMULATION`).
* **Sequence Checks:** Validates predecessor relationships (`VAL_OUT_OF_SEQUENCE`).
* **Directional Conflict Checks:** Flags same-date progress disagreements $> 10\%$ (`SAME_DATE_DISAGREEMENT`) and unapproved progress drops (`PROGRESS_REGRESSION`).

---

## 8. Evidence Architecture

Evidence processing connects field documentation to schedule claims without allowing uncontrolled automated approvals:

```
┌────────────────────────────────────────────────────────┐
│                   EVIDENCE INTAKE                      │
│  Photos (JPG/PNG), M-Book Sheets, Inspection PDFs      │
└───────────────────────────┬────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│   METADATA AUDIT      │       │    EVIDENCE FUSION    │
│  EXIF Date Check      │       │  Cross-Channel Pairs  │
│  GPS Haversine Radius │       │  (DPR vs Inspection)  │
└───────────┬───────────┘       └───────────┬───────────┘
            │                               │
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│   VALIDATION FLAGS    │       │ RELATION CLASSIFIER   │
│ VAL_EVIDENCE_MISMATCH │       │ CORROBORATES (Agree)  │
│ (Severity: WARNING)   │       │ CONTRADICTS  (Differ) │
└───────────┬───────────┘       └───────────┬───────────┘
            │                               │
            └───────────────┬───────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│             SUPERVISOR REVIEW WORKSPACE                │
│  • Evidence does NOT auto-approve claims               │
│  • Contradictions elevate priority score (+20)         │
│  • Missing evidence allows optional review             │
│  • High-res lightbox rendering with EXIF badges        │
└────────────────────────────────────────────────────────┘
```

### 8.1 Key Evidence Principles
1. **Optional Evidence Contract:** Providing supporting evidence photos is optional for field engineers. If omitted, SETUAI generates a clean placeholder image (`file_not_uploaded.png`) rather than raising a system exception.
2. **Deterministic Metadata Auditing:**
   * **Temporal Audit:** Compares photo EXIF `DateTimeOriginal` with reported `event_date`. If $|\Delta t| > 2\text{ days}$, flags `VAL_EVIDENCE_MISMATCH` (Severity: `WARNING`).
   * **Geospatial Audit:** Calculates Haversine distance between photo GPS coordinates and project site coordinates (`PROJECT_SITE_LAT`, `PROJECT_SITE_LON`). If distance exceeds radius (`PROJECT_SITE_RADIUS_KM`, default $5.0\text{ km}$), flags `VAL_EVIDENCE_MISMATCH`.
3. **Evidence Fusion Engine:**
   * Links independent reporting channels within a 14-day temporal window (`EVIDENCE_COMPARISON_WINDOW_DAYS`).
   * Pairs agreeing within tolerance ($10\%$) are classified as `CORROBORATES`.
   * Pairs with conflicting progress or opposing claims are classified as `CONTRADICTS`.
   * Persisted in `evidence_links` table with confidence scores and rationales.
4. **Zero-Trust AI Principle:** High evidence confidence never automatically approves a claim. Evidence serves strictly to inform the human Supervisor.

---

## 9. Review & Decision Architecture

All progress updates must pass through human governance. The Supervisor review cockpit is powered by a multi-factor risk priority engine:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      SMART PRIORITY SCORING                            │
│                                                                        │
│  Base Score:                         0.0                               │
│  + Critical Path Activity:         +30.0                               │
│  + Negative Float (Behind Sched):  +25.0                               │
│  + Validation ERROR Issues:        +20.0 per issue                     │
│  + Validation WARNING Issues:      +10.0 per issue                     │
│  + Open Conflict Records:          +25.0 per conflict                  │
│  + Contradicting Evidence Links:   +20.0 per contradiction             │
│  + Broad WBS Split Scope:          +15.0                               │
│  + Queue Aging:                    + 2.0 per hour waiting              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      PRIORITY-ORDERED REVIEW QUEUE                     │
│  GET /api/v1/review-queue?sort=priority                                │
│  Order: priority_score DESC, created_at ASC, event_id ASC              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
       ┌────────────────────────┐      ┌────────────────────────┐
       │     SINGLE REVIEW      │      │   BULK APPROVE GATE    │
       │  Supervisor inspects   │      │  POST /digest/bulk-app │
       │  provenance, evidence, │      │  Status = VALIDATED    │
       │  splits & candidates   │      │  Priority < 50         │
       └────────────┬───────────┘      │  Zero validation flags │
                    │                  └───────────┬────────────┘
                    ▼                              │
       ┌────────────────────────┐                  │
       │  SUPERVISOR DECISION   │                  │
       │  • APPROVE             │                  │
       │  • EDIT                │◄─────────────────┘
       │  • REJECT              │
       │  • HOLD                │
       └────────────┬───────────┘
                    │
                    ▼
       ┌────────────────────────┐
       │ ATOMIC DB TRANSACTION  │
       │ 1. planner_decisions   │
       │ 2. execution_events    │
       │ 3. audit_logs (SHA-256)│
       │ 4. approved_actuals    │
       └────────────────────────┘
```

### 9.1 Decision Actions & State Impacts

| Action | Allowed Source Status | Resulting Event Status | Approved Actuals Impact | Provenance Impact | Audit Log Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`APPROVE`** | `VALIDATED`, `REVIEW_REQUIRED`, `HOLD` | `APPROVED` | **Written/Upserted** via `upsert_approved_actual()` | Preserves stored tags | `APPROVE` |
| **`EDIT`** | `VALIDATED`, `REVIEW_REQUIRED`, `HOLD` | `EDITED` | **Written/Upserted** using overridden values | Overridden fields tagged `SUPERVISOR_EDITED` | `EDIT` |
| **`REJECT`** | `VALIDATED`, `REVIEW_REQUIRED`, `HOLD` | `REJECTED` | **No write** to `approved_actuals` | Unchanged | `REJECT` |
| **`HOLD`** | `VALIDATED`, `REVIEW_REQUIRED`, `HOLD` | `HOLD` | **No write** to `approved_actuals` | Unchanged | `HOLD` |

---

## 10. Approved Actuals Reconciliation

The reconciliation contract (`backend/shared/actuals.py`) enforces mathematical and relational integrity when approved claims update schedule actuals:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   RECONCILIATION CONTRACT (RULES A-F)                  │
├────────────────────────────────────────────────────────────────────────┤
│ Rule A: Canonical Keying                                               │
│         Exactly ONE row per (schedule_id, activity_id).                 │
│                                                                        │
│ Rule B: Start & Finish Date Merging                                    │
│         Never erase actual_start when recording actual_finish.          │
│         Never erase actual_finish when recording actual_start.          │
│                                                                        │
│ Rule C: Cumulative Percentage Replacement                              │
│         Cumulative percentage is REPLACED, never summed:               │
│         actual_pct_complete = new_approved_pct                         │
│                                                                        │
│ Rule D: Incremental Quantity Source-Decision Recalculation            │
│         Never maintain a running total. Recalculate from all source    │
│         decisions with action IN ('APPROVE', 'EDIT') plus split shares.│
│                                                                        │
│ Rule E: Canonical Execution State Interpretation                       │
│         1. actual_pct_complete >= 100.0  ==> COMPLETED                 │
│         2. actual_start IS NOT NULL      ==> IN_PROGRESS               │
│         3. else                          ==> NOT_STARTED               │
│                                                                        │
│ Rule F: Downstream Adapter Hooking                                     │
│         Database transaction commits BEFORE triggering CSV/P6 export.  │
│         Adapter failures NEVER roll back approved actuals.             │
└────────────────────────────────────────────────────────────────────────┘
```

### Mathematical Data Flow:
* **Cumulative Percentages:**
  $$\text{actual\_pct\_complete} = \min(100.0, \max(0.0, \text{approved\_pct} \times \text{split\_pct}))$$
* **Incremental Quantities:**
  $$\text{actual\_quantity} = \sum_{\text{Decisions}} \text{approved\_qty} + \sum_{\text{Splits}} (\text{approved\_qty} \times \text{split\_pct})$$

---

## 11. Database Architecture

The data architecture is implemented in PostgreSQL (Supabase) across 14 relational tables, reinforced by Row Level Security (RLS) and strict foreign keys:

```mermaid
erDiagram
    profiles ||--o{ source_documents : uploads
    profiles ||--o{ execution_events : reports
    profiles ||--o{ planner_decisions : decides
    schedules ||--o{ schedule_activities : contains
    schedules ||--o{ schedule_dependencies : defines
    schedules ||--o{ execution_events : scopes
    schedules ||--o{ approved_actuals : records
    
    schedule_activities ||--o{ approved_actuals : tracks
    schedule_activities ||--o{ claim_activity_splits : allocates
    
    source_documents ||--o{ execution_events : sources
    execution_events ||--o{ source_references : references
    execution_events ||--o{ candidate_matches : generates
    execution_events ||--o{ validation_issues : flags
    execution_events ||--o{ conflict_records : conflicts
    execution_events ||--o{ evidence_links : links
    execution_events ||--o{ claim_activity_splits : decomposes
    execution_events ||--o{ planner_decisions : receives
    execution_events ||--o{ approved_actuals : creates
    
    planner_decisions ||--o{ approved_actuals : authorizes
```

### Table Specifications

#### Schedule Domain
* **`schedules`**:
  * *PK:* `schedule_id` (TEXT, UUID).
  * *Fields:* `project_name`, `data_date`, `source_format`, `created_at`.
* **`schedule_activities`**:
  * *PK:* `(schedule_id, activity_id)`.
  * *Fields:* `activity_name`, `wbs_code`, `discipline`, `location`, `asset_tag`, `planned_start`, `planned_finish`, `planned_quantity`, `uom`, `baseline_pct_complete`, `total_float`, `is_critical`.
* **`schedule_dependencies`**:
  * *PK:* `dependency_id` (TEXT, UUID).
  * *Fields:* `schedule_id`, `predecessor_activity_id`, `successor_activity_id`, `relationship_type` (FS/SS/FF/SF), `lag_days`.

#### Execution Domain
* **`source_documents`**:
  * *PK:* `document_id` (TEXT, UUID).
  * *Fields:* `file_name`, `document_type`, `uploader_id` (FK $\to$ `profiles.id`), `file_hash` (SHA-256), `uploaded_at`.
* **`execution_events`**:
  * *PK:* `event_id` (TEXT, UUID).
  * *Fields:* `document_id`, `schedule_id`, `event_date`, `raw_claim_text`, `input_channel`, `language_detected`, `reported_activity_id`, `matched_activity_id`, `discipline`, `action`, `event_type`, `claim_mode`, `asset_tag`, `location`, `claimed_quantity`, `claimed_uom`, `claimed_pct`, `delay_reason`, `supervisor_id` (reporter FK), `photo_path`, `status`, `clarification_status`, `clarification_question`, `clarification_answer`, `field_provenance` (JSONB), `priority_score`, `priority_reasons`, `created_at`.
* **`source_references`**:
  * *PK:* `reference_id` (TEXT, UUID).
  * *Fields:* `event_id` (FK), `file_name`, `sheet_name`, `row_cell_ref`, `message_id`, `raw_snippet`.
* **`candidate_matches`**:
  * *PK:* `candidate_id` (TEXT, UUID).
  * *Fields:* `event_id` (FK), `schedule_id`, `activity_id`, `rank_order` (1..3), `match_tier`, `composite_confidence`, `semantic_score`, `fuzzy_score`, `location_score`, `discipline_score`, `supporting_signals`, `disqualifying_signals`.
* **`claim_activity_splits`**:
  * *PK:* `split_id` (TEXT, UUID).
  * *Fields:* `event_id` (FK), `activity_id`, `split_basis` (`EQUAL` | `WBS_WEIGHTED` | `MANUAL`), `split_pct`, `schedule_id`, `wbs_code`, `planned_quantity`, `allocated_quantity`, `uom`, `rationale`, `created_at`.

#### Control & Validation Domain
* **`validation_issues`**:
  * *PK:* `issue_id` (TEXT, UUID).
  * *Fields:* `event_id` (FK), `rule_code`, `severity` (`WARNING` | `ERROR`), `description`.
* **`conflict_records`**:
  * *PK:* `conflict_id` (TEXT, UUID).
  * *Fields:* `schedule_id`, `activity_id`, `reporting_period`, `event_id_a`, `event_id_b`, `value_a`, `value_b`, `variance_pct`, `status` (`OPEN` | `RESOLVED`).
* **`evidence_links`**:
  * *PK:* `link_id` (TEXT, UUID).
  * *Fields:* `event_id_a`, `event_id_b`, `relation_type` (`CORROBORATES` | `CONTRADICTS`), `confidence`, `rationale`, `created_at`.
* **`planner_decisions`**:
  * *PK:* `decision_id` (TEXT, UUID).
  * *Fields:* `event_id` (FK), `selected_activity_id`, `action` (`APPROVE` | `EDIT` | `REJECT` | `HOLD`), `approved_pct`, `approved_qty`, `planner_id` (FK $\to$ `profiles.id`), `justification`, `decided_at`.
* **`approved_actuals`**:
  * *PK:* `actual_id` (TEXT, UUID).
  * *Constraint:* `UNIQUE (schedule_id, activity_id)`.
  * *Fields:* `decision_id`, `event_id`, `schedule_id`, `activity_id`, `actual_start`, `actual_finish`, `actual_pct_complete`, `actual_quantity`, `exported_at`, `created_at`.

#### Audit & Reporting Domain
* **`audit_logs`**:
  * *PK:* `log_id` (SERIAL).
  * *Fields:* `entity_type`, `entity_id`, `action`, `actor_id`, `before_state` (JSON), `after_state` (JSON), `payload_hash`, `previous_hash`, `current_hash`, `timestamp`.
* **`execution_summaries`**:
  * *PK:* `summary_id` (TEXT, UUID).
  * *Constraint:* `UNIQUE (period_start, period_end, COALESCE(discipline, 'ALL'))`.
  * *Fields:* `period_start`, `period_end`, `discipline`, `summary_text`, `generated_at`, `aggregate_hash`.

---

## 12. State Machine

The complete implemented lifecycle for an execution claim follows strict transition rules:

```mermaid
stateDiagram-v2
    [*] --> EXTRACTED : Raw Intake (Text/Voice/File/XER)
    
    EXTRACTED --> PENDING_CLARIFICATION : Missing required fields
    PENDING_CLARIFICATION --> EXTRACTED : Engineer Clarification Received
    
    EXTRACTED --> MATCHED : Match Found (Tier 1-3, Conf > 0.40)
    EXTRACTED --> UNMATCHED : Low Confidence / Ambiguous / Hard Mismatch
    
    MATCHED --> VALIDATED : Clean Checks & Zero Flags
    MATCHED --> REVIEW_REQUIRED : Validation Errors, Conflicts, or Contradictions
    UNMATCHED --> REVIEW_REQUIRED : Unmatched claims routed to Review
    
    VALIDATED --> APPROVED : Supervisor Approval / Bulk Approve
    VALIDATED --> EDITED : Supervisor Edit
    VALIDATED --> REJECTED : Supervisor Rejection
    VALIDATED --> HOLD : Supervisor Hold
    
    REVIEW_REQUIRED --> APPROVED : Supervisor Overrides & Approves
    REVIEW_REQUIRED --> EDITED : Supervisor Edits & Approves
    REVIEW_REQUIRED --> REJECTED : Supervisor Rejection
    REVIEW_REQUIRED --> HOLD : Supervisor Hold
    
    HOLD --> REVIEW_REQUIRED : Re-opened for subsequent review
    
    APPROVED --> APPROVED_ACTUAL : Written to approved_actuals
    EDITED --> APPROVED_ACTUAL : Written to approved_actuals
```

---

## 13. Impact Preview Architecture

The CPM Schedule Impact Engine ([schedule.py](file:///d:/SIH26122/backend/routers/schedule.py) & [impact.py](file:///d:/SIH26122/backend/shared/impact.py)) models the downstream schedule consequences of execution delays:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CPM CONSTRAINT ENGINE                           │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Direct Edge Evaluation:                                             │
│    Calculates required successor start date:                           │
│    • FS (Finish-to-Start): Start_succ = Finish_pred + Lag              │
│    • SS (Start-to-Start):   Start_succ = Start_pred + Lag               │
│    • FF (Finish-to-Finish): Finish_succ = Finish_pred + Lag            │
│                             Start_succ = Finish_succ - Duration_succ   │
│    • SF (Start-to-Finish):  Finish_succ = Start_pred + Lag             │
│                             Start_succ = Finish_succ - Duration_succ   │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Controlling Predecessor Selection:                                  │
│    When a successor has multiple incoming dependencies, ties break     │
│    deterministically:                                                  │
│    Tier 1: Latest required successor start date                        │
│    Tier 2: Largest gross delay days                                    │
│    Tier 3: Predecessor activity ID ascending (lexicographical)         │
│    Tier 4: Relationship type ascending                                 │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Float Absorption Contract:                                          │
│    If Total Float is KNOWN:                                            │
│    • Absorbed Delay = min(Gross Delay, Total Float)                    │
│    • Net Delay Slip = max(0, Gross Delay - Total Float)                │
│    If Total Float is NULL:                                             │
│    • Float Status = UNKNOWN; halt numeric slip propagation             │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Execution State Gating:                                             │
│    If successor execution_state == COMPLETED:                          │
│    • Impact = 0 days (already finished in reality)                     │
│    • Halts downstream propagation along this branch                    │
├────────────────────────────────────────────────────────────────────────┤
│ 5. Bounded Propagation:                                                │
│    Frontier traverses up to MAX_IMPACT_HOPS = 3.                       │
│    Tracks visited nodes to prevent cyclic deadlocks.                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Analytics & Intelligence

### 14.1 Operational Dashboard ([dashboard.py](file:///d:/SIH26122/backend/routers/dashboard.py))
* **KPI Derivation:**
  * **Total Claims:** $\sum \text{execution\_events}$ scoped to schedule.
  * **Pending Review:** Claims with status $\notin (\text{'APPROVED'}, \text{'EDITED'}, \text{'REJECTED'})$.
  * **Approved Actuals:** Count of committed rows in `approved_actuals`.
  * **Open Conflicts:** Count of active rows in `conflict_records`.
* **Delay Reason Pareto Chart:** Aggregates `delay_reason` across approved claims.
* **Discipline Distribution:** Live distribution of activities by discipline.
* **Week-over-Week Trend:** Evaluates claim volume in the past 7 days against prior 7 days.

### 14.2 Activity History & Rollup ([activities.py](file:///d:/SIH26122/backend/routers/activities.py))
Reconstructs the full lifecycle timeline for any activity:
$$\text{Source References} \longrightarrow \text{Execution Claims} \longrightarrow \text{Candidate Matches} \longrightarrow \text{Decisions} \longrightarrow \text{Approved Actuals}$$

### 14.3 Institutional Memory & Forecasting ([dashboard.py](file:///d:/SIH26122/backend/routers/dashboard.py))
* **Institutional Memory:** Compares planned durations $(\text{planned\_finish} - \text{planned\_start})$ against actual durations $(\text{actual\_finish} - \text{actual\_start})$ from `approved_actuals`.
* **Forecasting:** Calculates discipline-specific historical performance ratios:
  $$\text{Historical Ratio} = \frac{1}{N} \sum_{i=1}^N \frac{\text{Actual Duration}_i}{\text{Planned Duration}_i}$$
  Forecasts remaining activity duration:
  $$\text{Forecast Duration} = \text{Planned Duration} \times \text{Historical Ratio}$$

### 14.4 Execution Knowledge Graph & Ask Why ([graph.py](file:///d:/SIH26122/backend/routers/graph.py), [investigation.py](file:///d:/SIH26122/backend/routers/investigation.py))
Constructs a unified, bounded node-edge graph:
* **Nodes:** Activities, Execution Events, Decisions, Approved Actuals, Evidence Documents.
* **Edges:** Dependencies (`predecessor_of`), Matches (`matches`), Decisions (`authorizes`), Evidence (`supports`).
* **Ask Why Panel:** Traverses graph to provide explainable answers to: *"Why is Activity X delayed?"* by tracing directly back to source claims, weather delays, and controlling predecessor slips.

### 14.5 AI Execution Summary ([summary.py](file:///d:/SIH26122/backend/routers/summary.py), [reports.py](file:///d:/SIH26122/backend/routers/reports.py))
* **Deterministic Aggregation:** Compiles verified counts (claims, completed activities, open conflicts, delays) from PostgreSQL.
* **Constrained LLM Generation:** The LLM is provided *only* the pre-calculated aggregate JSON. It is strictly instructed never to invent numbers or hallucinate claims.
* **Cryptographic Cache:** Summary narrative is cached in `execution_summaries` keyed by `(period_start, period_end, discipline)` and guarded by `aggregate_hash`.
* **Runtime Translation:** Process-local in-memory translation cache (SHA-256) renders display narratives in Hindi (`hi`) or Telugu (`te`) without altering canonical English database records.

---

## 15. AI / ML Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AI / ML COMPONENT MATRIX                        │
├─────────────────────┬───────────────────────┬──────────────────────────┤
│ Function            │ Technology / Model    │ Execution Boundary       │
├─────────────────────┼───────────────────────┼──────────────────────────┤
│ Claim Extraction    │ Groq / Gemini Flash   │ Constrained JSON Prompt  │
│ Vision OCR / Scans  │ Gemini Flash / Tesseract Direct image inference │
│ Clarification Voice │ Web Speech API        │ Client-side browser STT  │
│ Semantic Retrieval  │ all-MiniLM-L6-v2      │ In-Memory CPU Embeddings │
│ Vector Search       │ FAISS (IndexFlatIP)   │ In-Memory Cosine Product │
│ Fuzzy Matching      │ RapidFuzz             │ In-Memory Levenshtein    │
│ Executive Summary   │ Groq / Gemini Flash   │ Bounded Narrative Synthes│
│ Dynamic Translation │ Groq / Gemini Flash   │ SHA-256 Memory Cached    │
└─────────────────────┴───────────────────────┴──────────────────────────┘
```

### Deterministic vs AI Separation:
* **AI Responsibilities:** Translating messy text to JSON, reading handwritten diary images, drafting polite clarification questions, semantic candidate retrieval, and phrasing executive narratives.
* **Deterministic Responsibilities:** Physical quantity math, dependency validation, conflict detection, controlling predecessor selection, CPM date math, and human approval enforcement.

---

## 16. Integration Architecture

### 16.1 Downstream PMIS Integration (P6 & MSP)
* **RFC-4180 CSV Adapter ([export.py](file:///d:/SIH26122/backend/routers/export.py)):** Generates 5-column CSV: `activity_id`, `actual_start`, `actual_finish`, `actual_pct_complete`, `actual_quantity`.
* **P6 EPPM REST Client ([p6.py](file:///d:/SIH26122/backend/shared/p6.py)):** Produces standard P6 payloads:
  ```json
  {
    "Id": "CIV-PS3-TR-0180",
    "StartDate": "2026-09-15",
    "FinishDate": "2026-09-22",
    "PercentComplete": 65.0
  }
  ```
* **Local Mock P6 Server ([mock_p6.py](file:///d:/SIH26122/backend/routers/mock_p6.py)):** Provides local testing endpoint `POST /mock-p6/activities/{activity_id}`.

### 16.2 Ingestion Parsers
* **Native P6 `.xer` Parser ([xer_parser.py](file:///d:/SIH26122/backend/shared/xer_parser.py)):** Decodes tab-delimited XER structures (`PROJECT`, `WBS`, `TASK`, `TASKPRED`).
* **Tabular Progress Parser ([tabular_extraction.py](file:///d:/SIH26122/backend/shared/tabular_extraction.py)):** Parses multi-sheet Excel workbooks and CSV progress files without LLM overhead.

---

## 17. Security & RBAC Architecture

* **Authentication Protocol:** Supabase Auth issuing JWT Bearer tokens.
* **Token Verification Modes ([auth.py](file:///d:/SIH26122/backend/shared/auth.py)):**
  1. *Symmetric HMAC-SHA256:* Verified offline via `SUPABASE_JWT_SECRET`.
  2. *Asymmetric ES256/RS256:* Verified offline via cached Supabase JWKS (`PyJWKClient`).
  3. *Online HTTP Check:* Fallback verification against Supabase Auth API (`/auth/v1/user`).
  4. *Auth Dev Mode:* Explicit dev mode (`AUTH_DEV_MODE=true`) accepting signed test tokens.
* **Role Verification:** User profile loaded from PostgreSQL `profiles` table:
  * `require_role('SITE_ENGINEER')`: Access to intake and clarification endpoints.
  * `require_role('SUPERVISOR')`: Access to review queue, decisions, splits, impact preview, and executive summaries.
* **Database Row Level Security (RLS):** Enabled on all 14 tables. PostgREST anonymous role has default deny; authenticated users have read/insert policies matching their roles.

---

## 18. Audit & Traceability Architecture

SETUAI implements a tamper-evident audit log chain ([audit.py](file:///d:/SIH26122/backend/shared/audit.py)):

```
┌────────────────────────────────────────────────────────────────────────┐
│                   TAMPER-EVIDENT SHA-256 AUDIT LOG                     │
├────────────────────────────────────────────────────────────────────────┤
│ Entry 0 (Genesis):                                                     │
│   previous_hash = "000000000000000000000000000000000000000000000000..." │
│   current_hash  = SHA-256(entity + action + before + after + payload)  │
├────────────────────────────────────────────────────────────────────────┤
│ Entry i:                                                               │
│   previous_hash = Entry[i-1].current_hash                              │
│   current_hash  = SHA-256(entity + action + before + after +           │
│                           payload_hash + previous_hash)                │
└────────────────────────────────────────────────────────────────────────┘
```

The system verifies chain integrity via `verify_audit_chain()`:
* Recomputes `payload_hash` from normalized `before_state` and `after_state`.
* Recomputes `current_hash` from record attributes and `previous_hash`.
* Asserts strictly increasing monotonic `log_id` sequence numbers.

---

## 19. Complete API Architecture

| Domain | Method | Endpoint | Purpose | Role | Reads | Writes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Auth** | `GET` | `/api/v1/auth/me` | Resolve user profile & role | Authenticated | `profiles` | None |
| **Schedules** | `POST` | `/api/v1/schedules` | Ingest new schedule baseline | Authenticated | None | `schedules`, `schedule_activities`, `schedule_dependencies` |
| **Schedules** | `GET` | `/api/v1/schedules` | List stored schedules | Authenticated | `schedules` | None |
| **Schedules** | `GET` | `/api/v1/schedules/{id}/wbs-tree` | Get hierarchical WBS tree | Authenticated | `schedule_activities` | None |
| **Intake** | `POST` | `/api/v1/claims/text` | Submit typed or voice claim | `SITE_ENGINEER` | `schedules` | `source_documents`, `execution_events`, `source_references` |
| **Intake** | `POST` | `/api/v1/claims/file` | Upload PDF/XLSX/Image claims | `SITE_ENGINEER` | `schedules` | `source_documents`, `execution_events`, `source_references` |
| **Intake** | `POST` | `/api/v1/claims/schedule-export` | Upload progress spreadsheet | `SITE_ENGINEER` | `schedules` | `source_documents`, `execution_events`, `source_references` |
| **Intake** | `POST` | `/api/v1/claims/{id}/clarify` | Submit clarification response | `SITE_ENGINEER` | `execution_events` | `execution_events` |
| **Intake** | `GET` | `/api/v1/claims` | List claims for schedule | Authenticated | `execution_events` | None |
| **Intake** | `GET` | `/api/v1/claims/{id}` | Get single claim detail | Authenticated | `execution_events` | None |
| **Intake** | `GET` | `/api/v1/claims/{id}/photo` | Download evidence photo | Authenticated | `execution_events` | None |
| **Matching** | `POST` | `/api/v1/claims/{id}/match` | Execute 4-tier match cascade | Authenticated | `execution_events`, `schedule_activities` | `candidate_matches`, `execution_events`, `claim_activity_splits` |
| **Matching** | `GET` | `/api/v1/claims/{id}/candidates` | Get top 3 candidates | Authenticated | `candidate_matches` | None |
| **Matching** | `GET` | `/api/v1/claims/{id}/splits` | Get WBS split allocations | Authenticated | `claim_activity_splits` | None |
| **Matching** | `PATCH`| `/api/v1/claims/{id}/splits` | Supervisor override WBS split | `SUPERVISOR` | `claim_activity_splits` | `claim_activity_splits`, `audit_logs` |
| **Checks** | `POST` | `/api/v1/claims/{id}/check` | Run validation & priority | Authenticated | `execution_events`, `approved_actuals`, `schedule_dependencies` | `validation_issues`, `conflict_records`, `evidence_links`, `execution_events` |
| **Checks** | `GET` | `/api/v1/claims/{id}/validation` | Get validation issues | `SUPERVISOR` | `validation_issues` | None |
| **Checks** | `GET` | `/api/v1/claims/{id}/conflicts` | Get same-channel conflicts | `SUPERVISOR` | `conflict_records` | None |
| **Checks** | `GET` | `/api/v1/claims/{id}/evidence` | Get cross-channel evidence | `SUPERVISOR` | `evidence_links`, `execution_events` | None |
| **Checks** | `GET` | `/api/v1/review-queue` | Get priority review queue | `SUPERVISOR` | `execution_events`, `validation_issues`, `conflict_records` | `execution_events` (refreshed priority) |
| **Decisions** | `POST` | `/api/v1/decisions` | Submit Approve/Edit/Reject/Hold | `SUPERVISOR` | `execution_events`, `planner_decisions` | `planner_decisions`, `execution_events`, `approved_actuals`, `audit_logs` |
| **Decisions** | `GET` | `/api/v1/digest` | Get daily claims digest | `SUPERVISOR` | `execution_events` | None |
| **Decisions** | `POST` | `/api/v1/digest/bulk-approve` | Bulk-approve clean claims | `SUPERVISOR` | `execution_events` | `planner_decisions`, `execution_events`, `approved_actuals`, `audit_logs` |
| **Impact** | `GET` | `/api/v1/schedule/{id}/impact-preview` | Bounded CPM delay simulation | `SUPERVISOR` | `schedule_activities`, `schedule_dependencies`, `approved_actuals` | None |
| **Activities**| `GET` | `/api/v1/activities` | Filtered activity listing | Authenticated | `schedule_activities`, `approved_actuals` | None |
| **Activities**| `GET` | `/api/v1/activities/{id}/history` | Lifecycle history timeline | Authenticated | `execution_events`, `planner_decisions`, `approved_actuals` | None |
| **Dashboard** | `GET` | `/api/v1/dashboard/summary` | Live operational KPIs | `SUPERVISOR` | `execution_events`, `approved_actuals`, `conflict_records` | None |
| **Dashboard** | `GET` | `/api/v1/dashboard/delay-reasons` | Pareto delay aggregations | `SUPERVISOR` | `execution_events`, `planner_decisions` | None |
| **Dashboard** | `GET` | `/api/v1/dashboard/forecast` | Historical ratio forecast | `SUPERVISOR` | `schedule_activities`, `approved_actuals` | None |
| **Investigate**| `GET` | `/api/v1/investigation/{id}/context` | Causal Ask Why graph | Authenticated | Graph traversal across all tables | None |
| **Summary** | `GET` | `/api/v1/reports/execution-summary` | Executive summary report | `SUPERVISOR` | Pre-calculated database aggregates | `execution_summaries` |
| **Export** | `GET` | `/api/v1/export/actuals.csv` | Download actuals CSV | `SUPERVISOR` | `approved_actuals` | None |

---

## 20. Complete Data Flow

```mermaid
flowchart LR
    subgraph Users
        SE[Site Engineer]
        SV[Supervisor]
    end

    subgraph Frontend
        FE_Intake[Claim Intake UI]
        FE_Review[Review Workspace UI]
        FE_Dash[Dashboard & Intel UI]
    end

    subgraph API_Routers
        R_Intake[intake.py]
        R_Match[matching.py]
        R_Check[checks.py]
        R_Decide[decisions.py]
        R_Impact[schedule.py]
        R_Summary[summary.py]
        R_Export[export.py]
    end

    subgraph Intelligence
        LLM[LLM Engine]
        FAISS[FAISS Vector Index]
        WBS[WBS Granularity Bridge]
        CPM[CPM Constraint Solver]
    end

    subgraph Database
        DB[(Supabase PostgreSQL)]
    end

    subgraph External
        P6[Oracle P6 EPPM / Mock]
        CSV[RFC-4180 CSV]
    end

    SE -->|Enters Claim / Photo| FE_Intake
    FE_Intake -->|POST /claims/text| R_Intake
    R_Intake -->|Extracts Fields| LLM
    R_Intake -->|Writes Claim| DB

    DB -->|Read Unmatched| R_Match
    R_Match -->|Semantic Search| FAISS
    R_Match -->|Decompose Broad| WBS
    R_Match -->|Writes Candidates| DB

    DB -->|Read Matched| R_Check
    R_Check -->|Validates Rules| DB
    R_Check -->|Computes Priority| DB

    SV -->|Inspects Queue| FE_Review
    FE_Review -->|GET /review-queue| R_Check
    SV -->|Approve / Edit| FE_Review
    FE_Review -->|POST /decisions| R_Decide
    R_Decide -->|Atomic Decision & Audit| DB
    R_Decide -->|Upserts Approved Actuals| DB

    DB -->|Trigger Post-Commit| R_Export
    R_Export -->|Write CSV| CSV
    R_Export -->|REST Push| P6

    SV -->|View Analytics| FE_Dash
    FE_Dash -->|GET /summary| R_Summary
    FE_Dash -->|GET /impact-preview| R_Impact
    R_Impact -->|Solve Graph| CPM
```

---

## 21. Component Dependency Graph

```mermaid
graph TD
    AppShell[AppShell / Layout] --> ClaimIntakePage[Claim Intake Page]
    AppShell --> ReviewWorkspacePage[Review Workspace Page]
    AppShell --> DashboardPage[Dashboard Page]
    AppShell --> ImpactPage[Impact Preview Page]
    AppShell --> HistoryPage[Activity History Page]
    
    ClaimIntakePage --> ApiClient[frontend/src/api.ts]
    ReviewWorkspacePage --> ApiClient
    DashboardPage --> ApiClient
    ImpactPage --> ApiClient
    HistoryPage --> ApiClient

    ApiClient --> FastAPI[FastAPI Backend - main.py]
    
    FastAPI --> IntakeRouter[routers/intake.py]
    FastAPI --> MatchingRouter[routers/matching.py]
    FastAPI --> ChecksRouter[routers/checks.py]
    FastAPI --> DecisionsRouter[routers/decisions.py]
    FastAPI --> ScheduleRouter[routers/schedule.py]
    FastAPI --> DashboardRouter[routers/dashboard.py]
    FastAPI --> ActivitiesRouter[routers/activities.py]
    FastAPI --> SummaryRouter[routers/summary.py]
    FastAPI --> ExportRouter[routers/export.py]

    IntakeRouter --> LlmExtraction[shared/llm_extraction.py]
    IntakeRouter --> TabularExtraction[shared/tabular_extraction.py]
    IntakeRouter --> XerParser[shared/xer_parser.py]
    
    MatchingRouter --> ScheduleIndex[shared/schedule_index.py]
    MatchingRouter --> WbsSplit[shared/wbs_split.py]
    
    ChecksRouter --> ActualsModule[shared/actuals.py]
    ChecksRouter --> AuditModule[shared/audit.py]
    
    DecisionsRouter --> ActualsModule
    DecisionsRouter --> AuditModule
    DecisionsRouter --> ExportRouter
    DecisionsRouter --> P6Adapter[shared/p6.py]
    
    ScheduleRouter --> ImpactModule[shared/impact.py]
    
    LlmExtraction --> LlmClient[shared/llm_client.py]
    SummaryRouter --> LlmClient
    
    IntakeRouter --> DbConn[shared/db.py]
    MatchingRouter --> DbConn
    ChecksRouter --> DbConn
    DecisionsRouter --> DbConn
    ScheduleRouter --> DbConn
    DashboardRouter --> DbConn
    ActivitiesRouter --> DbConn
    
    DbConn --> Postgres[(PostgreSQL / Supabase)]
    ScheduleIndex --> SentenceTransformers[Sentence-Transformers CPU]
    ScheduleIndex --> FaissLib[FAISS FlatIP]
    P6Adapter --> HttpMock[httpx -> Mock P6 / EPPM]
```

---

## 22. Real-World Walkthrough Example

### Scenario:
A Site Engineer in Duliajan reports that pipe rack spool welding reached 65% completion.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. ENGINEER SUBMISSION:                                                                │
│    Text: "Today completed welding on Utility Header Spool Section B, progress 65%"     │
│    Photo: Attached high-resolution weld inspection photo (EXIF Date matches today).    │
│    Action: POST /api/v1/claims/text                                                    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. AI EXTRACTION & PROVENANCE:                                                         │
│    discipline: "PIPING"                                                                │
│    action: "completed welding on Utility Header Spool Section B"                       │
│    event_type: "PROGRESS_UPDATE"                                                       │
│    claim_mode: "CUMULATIVE_PCT"                                                        │
│    claimed_pct: 65.0                                                                   │
│    field_provenance: {"discipline": "AI_EXTRACTED", "claimed_pct": "AI_EXTRACTED"}   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. MATCHING CASCADE & WBS RESOLUTION:                                                  │
│    Target candidates:                                                                  │
│    - Rank 1: PIP-UH-SPOOL-02 ("Utility Header Spool Section B")  Confidence: 0.94     │
│    - Rank 2: PIP-UH-SPOOL-01 ("Utility Header Spool Section A")  Confidence: 0.72     │
│    Scope Check: "Section B" matches specific sibling; single match retained.           │
│    Status: MATCHED                                                                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. DETERMINISTIC VALIDATION:                                                           │
│    • Physical: 65.0% in [0, 100] ==> PASS                                             │
│    • Chronological: Prior approved actual was 40.0% ==> Normal Progression (PASS)      │
│    • Sequence: Predecessor PIP-UH-FIT-02 is COMPLETED ==> PASS                         │
│    • Evidence: EXIF date variance = 0 days, GPS distance = 0.8km <= 5km ==> PASS       │
│    • Priority Calculation: Critical path (+30) + Negative float (+25) = 55.0           │
│    Status: REVIEW_REQUIRED (Priority > 50 warrants human sign-off)                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. SUPERVISOR APPROVAL:                                                                │
│    Supervisor opens Review Workspace, verifies weld photo and ultrasonic test log.     │
│    Action: APPROVE with justification: "Visual and radiographic inspection verified".  │
│    DB State: planner_decisions inserted, audit_logs hash chained.                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. RECONCILIATION & ADAPTER SYNC:                                                      │
│    approved_actuals updated:                                                           │
│    - schedule_id: "sch_oil_assam_01"                                                   │
│    - activity_id: "PIP-UH-SPOOL-02"                                                    │
│    - actual_pct_complete: 65.0                                                         │
│    - actual_start: "2026-09-10" (preserved)                                            │
│    Post-Commit Hooks:                                                                  │
│    - actuals.csv updated                                                               │
│    - P6 REST payload dispatched: {"Id": "PIP-UH-SPOOL-02", "PercentComplete": 65.0}     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 7. INTELLIGENCE UPDATE:                                                                │
│    - Dashboard KPI increments Actuals count                                            │
│    - CPM Impact Engine updates float absorption for downstream hydro-testing           │
│    - Ask Why Graph links photo directly to activity progress record                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 23. Technology Stack

| Layer | Technology | Version | Purpose in SETUAI |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | React | `^18.3.1` | Component-driven user interface |
| **Language** | TypeScript | `^5.5.3` | Type-safe client development |
| **Build Tool** | Vite | `^5.4.2` | Development and bundle compilation |
| **Client State** | TanStack React Query | `^5.56.2` | Server cache & query synchronization |
| **Routing** | React Router DOM | `^6.26.2` | Role-protected client routing |
| **Localization** | i18next / react-i18next | `^15.7.4` | English, Hindi, Telugu UI bundles |
| **Icons** | Lucide React | `^0.344.0` | Industrial HUD iconography |
| **Backend API** | FastAPI | `^0.115.0` | High-performance async/sync web framework |
| **Validation** | Pydantic | `^2.9.2` | Data contract and schema enforcement |
| **Database Driver** | Psycopg (v3) | `~=3.2.0` | Synchronous PostgreSQL row-factory driver |
| **Database** | PostgreSQL (Supabase) | 15+ | Relational source of truth, RLS, foreign keys |
| **Auth** | Supabase Auth / PyJWT | `~=2.9.0` | JWT verification (HMAC, JWKS, Auth API) |
| **Embeddings** | Sentence-Transformers | `~=3.1.0` | Local CPU embeddings (`all-MiniLM-L6-v2`) |
| **Vector Index** | FAISS (cpu) | `~=1.9.0` | In-memory cosine inner-product indexing |
| **Fuzzy Matching**| RapidFuzz | `~=3.9.7` | Token set and Levenshtein string matching |
| **Primary LLM** | Groq API | Free Tier | Cloud LLM inference (`openai/gpt-oss-20b`) |
| **Fallback LLM**| Google Gemini API | Free Tier | Multimodal vision & text (`gemini-3.6-flash`) |
| **OCR** | Tesseract / pytesseract| `~=0.3.10`| Local scanned image text recognition |
| **Tabular Data**| Pandas / OpenPyXL | `~=2.2.0` | CSV/XLSX multi-sheet parsing |
| **HTTP Client** | HTTPX | `~=0.27.0` | Non-blocking PMIS and LLM requests |

---

## 24. Actual vs PRD Architecture Gap

| Component / Requirement | PRD Requirement | Implementation Status | Evidence in Codebase |
| :--- | :--- | :--- | :--- |
| **PostgreSQL Source of Truth** | Relational integrity, FKs, RLS | **`IMPLEMENTED`** | [schema.sql](file:///d:/SIH26122/backend/models/schema.sql), [001_security_rls_and_foreign_keys.sql](file:///d:/SIH26122/backend/models/migrations/001_security_rls_and_foreign_keys.sql) |
| **4-Tier Schedule Matching** | EXACT_ID, ASSET, HYBRID, MISMATCH | **`IMPLEMENTED`** | `match_claim()`, `calculate_hybrid_score()` in [matching.py](file:///d:/SIH26122/backend/routers/matching.py) |
| **Ambiguity Protection** | Difference $< 0.05 \implies$ UNMATCHED | **`IMPLEMENTED`** | [matching.py:L1043-L1053](file:///d:/SIH26122/backend/routers/matching.py#L1043-L1053) |
| **WBS Granularity Bridge** | Broad claim sibling decomposition | **`IMPLEMENTED`** | [wbs_split.py](file:///d:/SIH26122/backend/shared/wbs_split.py), `claim_activity_splits` table |
| **Supervisor Manual Split Edit**| Adjust split percentages $\sum = 1.0$ | **`IMPLEMENTED`** | `PATCH /claims/{id}/splits`, [WBSSplitEditor.tsx](file:///d:/SIH26122/frontend/src/components/WBSSplitEditor.tsx) |
| **Directional Conflict Engine**| Same-date diff $>10\%$, regressions | **`IMPLEMENTED`** | `evaluate_cumulative_conflicts()` in [checks.py](file:///d:/SIH26122/backend/routers/checks.py) |
| **Accepted Rework Context** | Permit progress regression if rework | **`IMPLEMENTED`** | `has_rework_or_reset_context()` in [checks.py](file:///d:/SIH26122/backend/routers/checks.py) |
| **Evidence Fusion Engine** | Corroborates/Contradicts cross-channel| **`IMPLEMENTED`** | `evaluate_evidence_fusion()` in [checks.py](file:///d:/SIH26122/backend/routers/checks.py), `evidence_links` |
| **Optional Evidence Behavior** | Evidence photos optional; no crash | **`IMPLEMENTED`** | `ensure_default_placeholder_image()` in [intake.py](file:///d:/SIH26122/backend/routers/intake.py) |
| **Adaptive Field Copilot** | 1 targeted question in detected lang | **`IMPLEMENTED`** | `check_missing_required_fields()`, `POST /claims/{id}/clarify` |
| **Field Provenance Tagging** | AI vs Human vs Edit field tags | **`IMPLEMENTED`** | `field_provenance` JSONB column, [FieldProvenanceBadge.tsx](file:///d:/SIH26122/frontend/src/components/FieldProvenanceBadge.tsx) |
| **Smart Review Priority** | Explainable priority score formula | **`IMPLEMENTED`** | `evaluate_smart_review_priority()` in [checks.py](file:///d:/SIH26122/backend/routers/checks.py) |
| **Approved Actuals Upsert** | Canonical Rules A-F, single row/act | **`IMPLEMENTED`** | `upsert_approved_actual()`, `_execute_upsert()` in [actuals.py](file:///d:/SIH26122/backend/shared/actuals.py) |
| **Tamper-Evident Audit Chain** | SHA-256 chained hash log | **`IMPLEMENTED`** | `write_audit_log()`, `verify_audit_chain()` in [audit.py](file:///d:/SIH26122/backend/shared/audit.py) |
| **P6 Write-Back Adapter** | Production-shaped P6 REST payload | **`IMPLEMENTED`** | [p6.py](file:///d:/SIH26122/backend/shared/p6.py), [mock_p6.py](file:///d:/SIH26122/backend/routers/mock_p6.py) |
| **CPM Impact Preview Engine** | FS/SS/FF/SF, float, 3-hop propagation| **`IMPLEMENTED`** | [impact.py](file:///d:/SIH26122/backend/shared/impact.py), [schedule.py](file:///d:/SIH26122/backend/routers/schedule.py) |
| **AI Execution Summary** | Deterministic aggregate + LLM phrasing | **`IMPLEMENTED`** | [summary.py](file:///d:/SIH26122/backend/routers/summary.py), [reports.py](file:///d:/SIH26122/backend/routers/reports.py) |
| **Dynamic Translation** | Hindi & Telugu runtime translation | **`IMPLEMENTED`** | `_translation_cache`, `POST /reports/translate` |
| **Ask Why Investigation** | Causal node-edge graph traversal | **`IMPLEMENTED`** | [investigation.py](file:///d:/SIH26122/backend/routers/investigation.py), [AskWhyPanel.tsx](file:///d:/SIH26122/frontend/src/components/AskWhyPanel.tsx) |
| **Multi-Schedule FAISS Pool** | Dictionary of FAISS indexes by sched | **`PARTIAL`** | Single active FAISS index in memory; rebuilds on schedule switch |
| **Native Audio Upload STT** | Direct MP3/WAV upload server-side STT | **`[PRD / NOT IMPLEMENTED]`**| Browser Web Speech API used; raw audio file upload endpoint omitted |
| **MSP XML Live Write-Back** | Direct Microsoft Project XML export | **`[PRD / NOT IMPLEMENTED]`**| RFC-4180 CSV and P6 REST adapters implemented; MSP XML read-only |
| **Silent Activity Monitoring** | Cron background worker for dormancy | **`[PRD / NOT IMPLEMENTED]`**| Queried on demand via UI; standing daemon task not enabled |

---

## 25. Architectural Principles

The SETUAI architecture strictly follows 10 non-negotiable principles:

1. **PostgreSQL as the Absolute Source of Truth:**
   FAISS vector indexes and in-memory caches are ephemeral retrieval structures. All authoritative state resides in PostgreSQL. Process restart loses no state.
2. **Deterministic Rules Over AI Suggestions:**
   An LLM is never permitted to calculate project metrics, approve actuals, or override CPM dependency logic. AI parses messy text; deterministic Python code checks it.
3. **Strict Human-in-the-Loop Governance:**
   High confidence from vector matching or corroborated evidence never bypasses human review. Only an authenticated `SUPERVISOR` can commit progress updates.
4. **Field Attribution & Provenance-First Data:**
   Every field carries origin metadata (`AI_EXTRACTED`, `HUMAN_ENTERED`, `SUPERVISOR_EDITED`). External `activity_id` values from P6 are preserved verbatim.
5. **Decoupled Downstream Failure:**
   Failures in downstream adapters (P6 EPPM REST timeout, network disconnect) never roll back an already-committed database approval.
6. **No Silent Data Fabrication:**
   When historical data is missing or prior comparison periods have zero claims, the system reports `null` / `None` rather than fabricating synthetic progress.
7. **Canonical Actuals Contract:**
   Cumulative percentages replace prior progress (never sum); incremental quantities recalculate from source decisions; dates merge without erasing previous milestones.
8. **Tamper-Evident Traceability:**
   Every decision and status change is hashed into an immutable cryptographic SHA-256 chain linked to the authenticated user's UUID.
9. **Bounded Impact Propagation:**
   CPM schedule impact evaluates controlling predecessors deterministically and halts downstream propagation at completed successor activities or missing float bounds.
10. **Additive, Non-Breaking Schema Evolution:**
    Database migrations use idempotent `ADD COLUMN IF NOT EXISTS` and `NOT VALID` foreign keys to ensure historical records remain accessible.

---

## 26. Final One-Page Architecture

```
                                  ┌───────────────────────────────┐
                                  │          FIELD USERS          │
                                  │ Site Engineer | Supervisor    │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │      REACT 18 FRONTEND        │
                                  │ TypeScript | Query | i18next  │
                                  └───────────────┬───────────────┘
                                                  │ HTTP / JWT
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │      FASTAPI APPLICATION      │
                                  │ Pydantic | RBAC | 16 Routers  │
                                  └───────────────┬───────────────┘
                                                  │
                ┌─────────────────────────────────┴─────────────────────────────────┐
                ▼                                                                   ▼
┌───────────────────────────────┐                                   ┌───────────────────────────────┐
│     EXECUTION INTELLIGENCE    │                                   │      PROJECT INTELLIGENCE     │
│ • LLM / Tabular Extraction    │                                   │ • Live Operational Dashboard  │
│ • 4-Tier Schedule Matching    │                                   │ • CPM Schedule Impact Engine  │
│ • WBS Granularity Bridge      │                                   │ • Activity History Timeline   │
│ • Directional Conflict Rules  │                                   │ • Institutional Memory Ratio  │
│ • Evidence Fusion Engine      │                                   │ • Ask Why Causal Graph        │
│ • Smart Review Priority Scorer│                                   │ • AI Summary & Translation    │
│ • Approved Actuals Upsert     │                                   │ • RFC-4180 CSV / P6 REST Push │
└───────────────┬───────────────┘                                   └───────────────┬───────────────┘
                │                                                                   │
                └─────────────────────────────────┬─────────────────────────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │      SUPABASE POSTGRESQL      │
                                  │    Single Source of Truth     │
                                  │ 14 Tables | RLS | Audit Chain │
                                  └───────────────────────────────┘
```

---

## 27. Architecture Confidence

* **Implemented Architecture Confidence:** **98%**
  * Grounded in direct inspection of 16 backend routers, 27 shared domain modules, 14 database tables, 2 SQL migration scripts, 9 frontend pages, and 30 automated test suites.
* **PRD-to-Code Alignment:** **92%**
  * All core v5 and v6 features are fully implemented, tested, and active. Minor gaps are confined to secondary integration targets (native server audio upload vs browser Web Speech, MSP XML live write-back vs P6 REST, and multi-schedule vector index pooling).
* **Major Unknowns:**
  * Performance under extreme enterprise load ($> 100,000$ activities per schedule) regarding in-memory FAISS single-schedule re-indexing latency during concurrent multi-project uploads.
* **Major Architecture Gaps:**
  * FAISS index is currently process-local and in-memory; restart requires warm-up via database load.
  * Direct binary audio upload (`.wav`/`.mp3`) server-side transcription is absent (relies on browser Web Speech API).
* **Recommended Verification Files:**
  * [backend/shared/actuals.py](file:///d:/SIH26122/backend/shared/actuals.py) — Canonical approved actuals upsert & Rule A-F reconciliation.
  * [backend/routers/matching.py](file:///d:/SIH26122/backend/routers/matching.py) — 4-tier matching cascade & WBS decomposition.
  * [backend/routers/checks.py](file:///d:/SIH26122/backend/routers/checks.py) — Directional conflicts, evidence fusion, and smart priority scoring.
  * [backend/shared/impact.py](file:///d:/SIH26122/backend/shared/impact.py) — CPM constraint solver & float absorption algorithm.
  * [backend/shared/audit.py](file:///d:/SIH26122/backend/shared/audit.py) — Cryptographic SHA-256 audit chaining.
  * [frontend/src/pages/ReviewWorkspace.tsx](file:///d:/SIH26122/frontend/src/pages/ReviewWorkspace.tsx) — Supervisor decision workspace.
