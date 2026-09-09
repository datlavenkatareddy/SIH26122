/**
 * Setu AI (SIH26122) — Typed API Client & PRD Contracts
 *
 * Fully compliant with PRD v5 specification.
 * USE_MOCKS=true  → returns realistic mock data (demo mode)
 * USE_MOCKS=false → calls real FastAPI endpoints at VITE_API_BASE_URL
 */

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false';
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Fires at module load — fires before any component renders so it's the
// first thing visible in DevTools console. Cannot be silenced by app code.
if (USE_MOCKS) {
  console.warn(
    '[SetuAI] 🚧 Running in MOCK MODE — no backend calls are being made.\n' +
    'Set VITE_USE_MOCKS=false in frontend/.env to connect to the real backend.'
  );
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('supabase_access_token') || localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorText = await res.text().catch(() => 'Unknown network error');
    throw new Error(`API ${res.status}: ${errorText}`);
  }
  return res.json();
}

// ─── Canonical PRD Enums & Types ──────────────────────────────────────────────

export type UserRole = 'SITE_ENGINEER' | 'SUPERVISOR';

export type InputChannel =
  | 'FILE_UPLOAD'
  | 'SCANNED_OCR'
  | 'TYPED_TEXT'
  | 'VOICE'
  | 'SCHEDULE_EXPORT';

export type EventType =
  | 'ACTUAL_START'
  | 'ACTUAL_FINISH'
  | 'PROGRESS_UPDATE'
  | 'DELAY'
  | 'BLOCKER';

export type ClaimMode = 'CUMULATIVE_PCT' | 'INCREMENTAL_QUANTITY';

export type DecisionAction = 'APPROVE' | 'EDIT' | 'REJECT' | 'HOLD';

export type ClaimStatus =
  | 'EXTRACTED'
  | 'MATCHED'
  | 'UNMATCHED'
  | 'VALIDATED'
  | 'REVIEW_REQUIRED'
  | 'APPROVED'
  | 'EDITED'
  | 'REJECTED'
  | 'HOLD';

export type Discipline =
  | 'CIVIL'
  | 'PIPING'
  | 'STATIC_ROTATING_EQUIPMENT'
  | 'ELECTRICAL'
  | 'INSTRUMENTATION'
  | 'HSE';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface ExecutionEvent {
  event_id: string;
  document_id: string | null;
  schedule_id: string;
  event_date: string; // YYYY-MM-DD
  raw_claim_text: string;
  input_channel: InputChannel;
  language_detected: string | null;
  reported_activity_id: string | null;
  matched_activity_id: string | null;
  discipline: Discipline | null;
  action: string | null;
  event_type: EventType | null;
  claim_mode: ClaimMode;
  asset_tag: string | null;
  location: string | null;
  claimed_quantity: number | null;
  claimed_uom: string | null;
  claimed_pct: number | null;
  delay_reason: string | null;
  supervisor_id: string | null;
  photo_path: string | null;
  status: ClaimStatus;
  created_at: string;
}

export interface SourceReference {
  reference_id: string;
  event_id: string;
  file_name: string | null;
  sheet_name: string | null;
  row_cell_ref: string | null;
  message_id: string | null;
  raw_snippet: string;
}

export interface CandidateMatch {
  candidate_id: string;
  event_id: string;
  schedule_id: string;
  activity_id: string;
  rank_order: 1 | 2 | 3;
  match_tier: 'EXACT' | 'SEMANTIC' | 'FUZZY' | 'DISCIPLINE_LOCATION' | string | null;
  composite_confidence: number;
  semantic_score: number | null;
  fuzzy_score: number | null;
  location_score: number | null;
  discipline_score: number | null;
  supporting_signals: string | null;
  disqualifying_signals: string | null;
}

export interface ConflictRecord {
  conflict_id: string;
  schedule_id: string;
  activity_id: string;
  reporting_period: string;
  event_id_a: string;
  event_id_b: string;
  value_a: number;
  value_b: number;
  variance_pct: number;
  status: 'OPEN' | 'RESOLVED';
}

export interface ValidationIssue {
  issue_id: string;
  event_id: string;
  rule_code: string | null;
  severity: 'WARNING' | 'ERROR' | null;
  description: string;
}

export interface PlannerDecision {
  decision_id: string;
  event_id: string;
  selected_activity_id: string;
  action: DecisionAction;
  approved_pct: number | null;
  approved_qty: number | null;
  planner_id: string;
  justification: string;
  decided_at: string;
}

export interface ScheduleActivity {
  activity_id: string;
  schedule_id: string;
  activity_name: string;
  wbs_code: string | null;
  discipline: Discipline;
  location: string;
  asset_tag: string | null;
  planned_start: string;
  planned_finish: string;
  planned_quantity: number | null;
  uom: string | null;
  baseline_pct_complete: number;
}

export interface ScheduleDependency {
  dependency_id: string;
  schedule_id: string;
  predecessor_activity_id: string;
  successor_activity_id: string;
  relationship_type: 'FS' | 'SS' | 'FF' | 'SF';
}

export interface ImpactPreviewResult {
  activity_id: string;
  delay_days: number;
  disclaimer: string;
  successors: {
    successor_activity_id: string;
    activity_name: string;
    relationship_type: string;
    original_start: string;
    original_finish: string;
    shifted_start: string;
    shifted_finish: string;
    lag_days: number;
  }[];
}

export interface AuditLogEntry {
  log_id: number;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id: string;
  before_state: string | null;
  after_state: string | null;
  payload_hash: string;
  previous_hash: string;
  current_hash: string;
  timestamp: string;
}

export interface ActivityListItem extends ScheduleActivity {
  approved_pct: number;
  approved_quantity: number | null;
  actual_start: string | null;
  actual_finish: string | null;
  status: 'NOT STARTED' | 'IN PROGRESS' | 'COMPLETED' | string;
}

export interface ActivityHistoryItem {
  timestamp: string;
  event_id: string;
  event_date?: string | null;
  raw_claim_text: string;
  input_channel: InputChannel;
  claimed_pct: number | null;
  claimed_qty: number | null;
  claimed_uom?: string | null;
  reported_activity_id?: string | null;
  matched_activity_id?: string | null;
  discipline?: string | null;
  location?: string | null;
  asset_tag?: string | null;
  delay_reason?: string | null;
  status: ClaimStatus;
  supervisor_action: string | null;
  approved_pct?: number | null;
  approved_qty?: number | null;
  justification?: string | null;
  decision?: {
    decision_id: string;
    action: string;
    approved_pct: number | null;
    approved_qty: number | null;
    planner_id: string;
    justification: string;
    decided_at: string | null;
  } | null;
  source_references?: SourceReference[];
  actor: string;
}

// ─── Realistic Demo Dataset ──────────────────────────────────────────────────

const TODAY = new Date().toISOString().split('T')[0];

const MOCK_EVENTS: ExecutionEvent[] = [
  {
    event_id: 'EVT-20260814-001',
    document_id: 'DOC-FLD-001',
    schedule_id: 'SIH26122_NFU',
    event_date: '2026-08-14',
    raw_claim_text: 'Two field weld joints completed on utility header at Pump Station 3.',
    input_channel: 'FILE_UPLOAD',
    language_detected: 'en',
    reported_activity_id: 'PIP-PS3-WLD-024',
    matched_activity_id: 'PIP-PS3-WLD-024',
    discipline: 'PIPING',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: 'WLD-024',
    location: 'Pump Station 3',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 40,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'APPROVED',
    created_at: '2026-08-14T09:00:00Z',
  },
  {
    event_id: 'EVT-20260814-002',
    document_id: 'DOC-DIA-001',
    schedule_id: 'SIH26122_NFU',
    event_date: '2026-08-14',
    raw_claim_text: 'Utility Trench Excavation CH 0+180 to CH 0+220 completed per site diary log.',
    input_channel: 'SCANNED_OCR',
    language_detected: 'en',
    reported_activity_id: 'CIV-PS3-TR-0180',
    matched_activity_id: 'CIV-PS3-TR-0180',
    discipline: 'CIVIL',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: null,
    location: 'North Field Corridor',
    claimed_quantity: 40,
    claimed_uom: 'm',
    claimed_pct: 100,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'APPROVED',
    created_at: '2026-08-14T11:00:00Z',
  },
  {
    event_id: 'EVT-20260815-001',
    document_id: 'DOC-XER-001',
    schedule_id: 'SIH26122_NFU',
    event_date: '2026-08-15',
    raw_claim_text: 'Utility Header Field Weld Joints status updated: 60% cumulative progress reached.',
    input_channel: 'SCHEDULE_EXPORT',
    language_detected: 'en',
    reported_activity_id: 'PIP-PS3-WLD-024',
    matched_activity_id: 'PIP-PS3-WLD-024',
    discipline: 'PIPING',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: 'WLD-024',
    location: 'Pump Station 3',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 60,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'APPROVED',
    created_at: '2026-08-15T10:00:00Z',
  },
  {
    event_id: 'EVT-CONF-001A',
    document_id: 'DOC-FLD-001',
    schedule_id: 'SIH26122_NFU',
    event_date: '2026-08-18',
    raw_claim_text: 'Dewatering Pump Relocation Sector 4 reported at 75% progress. Spare hose delivery delayed.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'MECH-PS3-DWP-003',
    matched_activity_id: 'MECH-PS3-DWP-003',
    discipline: 'STATIC_ROTATING_EQUIPMENT',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: null,
    location: 'Sector 4',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 75,
    delay_reason: 'MATERIAL',
    supervisor_id: null,
    photo_path: null,
    status: 'REVIEW_REQUIRED',
    created_at: '2026-08-18T08:30:00Z',
  },
  {
    event_id: 'EVT-CONF-001B',
    document_id: 'DOC-FLD-001',
    schedule_id: 'SIH26122_NFU',
    event_date: '2026-08-18',
    raw_claim_text: 'Dewatering Pump Relocation Sector 4 reported at 30% progress. Rain flooded pump pit.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'MECH-PS3-DWP-003',
    matched_activity_id: 'MECH-PS3-DWP-003',
    discipline: 'STATIC_ROTATING_EQUIPMENT',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: null,
    location: 'Sector 4',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 30,
    delay_reason: 'WEATHER',
    supervisor_id: null,
    photo_path: null,
    status: 'REVIEW_REQUIRED',
    created_at: '2026-08-18T14:30:00Z',
  },
  {
    event_id: 'EVT-20260819-001',
    document_id: 'DOC-FLD-001',
    schedule_id: 'SIH26122_NFU',
    event_date: '2026-08-19',
    raw_claim_text: 'Junction Box JB-101 Field Mounting completed and inspected.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'INS-PS3-JB-001',
    matched_activity_id: 'INS-PS3-JB-001',
    discipline: 'INSTRUMENTATION',
    action: 'ACTUAL_FINISH',
    event_type: 'ACTUAL_FINISH',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: 'JB-101',
    location: 'Pump Station 3',
    claimed_quantity: 1,
    claimed_uom: 'ea',
    claimed_pct: 100,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'APPROVED',
    created_at: '2026-08-19T16:00:00Z',
  },
  {
    event_id: 'EVT-20260814-003',
    document_id: 'DOC-FLD-001',
    schedule_id: 'SIH26122_NFU',
    event_date: '2026-08-14',
    raw_claim_text: 'Daily Site Safety Induction and Toolbox Talk conducted for 45 subcontractor workers.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'HSE-PS3-IND-001',
    matched_activity_id: 'HSE-PS3-IND-001',
    discipline: 'HSE',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: null,
    location: 'Site Main Gate',
    claimed_quantity: 45,
    claimed_uom: 'man',
    claimed_pct: 100,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'APPROVED',
    created_at: '2026-08-14T07:30:00Z',
  },
  {
    event_id: 'evt-101',
    document_id: 'doc-001',
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'Completed foundation pour F-4 in Block-4 North, 50 cu.m poured today.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'ACT-201',
    matched_activity_id: 'ACT-201',
    discipline: 'CIVIL',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'INCREMENTAL_QUANTITY',
    asset_tag: 'FND-B4',
    location: 'Block-4 North',
    claimed_quantity: 50,
    claimed_uom: 'cu.m',
    claimed_pct: 100,
    delay_reason: null,
    supervisor_id: null,
    photo_path: '/uploads/f4_pour.jpg',
    status: 'VALIDATED',
    created_at: new Date().toISOString(),
  },
  {
    event_id: 'evt-102',
    document_id: 'doc-002',
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'Rebar placement for column C4, level B2 finished. 75% total progress claimed.',
    input_channel: 'VOICE',
    language_detected: 'en',
    reported_activity_id: 'ACT-202',
    matched_activity_id: 'ACT-202',
    discipline: 'CIVIL',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: 'COL-C4',
    location: 'Block-2',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 75,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'REVIEW_REQUIRED',
    created_at: new Date().toISOString(),
  },
  {
    event_id: 'evt-103',
    document_id: null,
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'Completed 8 weld joints on 6" crude pipeline near Pump Skid PS-02.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'ACT-301',
    matched_activity_id: 'ACT-301',
    discipline: 'PIPING',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'INCREMENTAL_QUANTITY',
    asset_tag: 'PUMP-002',
    location: 'Pump Station 2',
    claimed_quantity: 8,
    claimed_uom: 'joints',
    claimed_pct: 40,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'VALIDATED',
    created_at: new Date().toISOString(),
  },
  {
    event_id: 'evt-104',
    document_id: 'doc-004',
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'SCADA Panel E3 installation complete and powered up in control room.',
    input_channel: 'FILE_UPLOAD',
    language_detected: 'en',
    reported_activity_id: 'ACT-401',
    matched_activity_id: 'ACT-401',
    discipline: 'ELECTRICAL',
    action: 'ACTUAL_FINISH',
    event_type: 'ACTUAL_FINISH',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: 'PANEL-E3',
    location: 'Unit E3 Control Room',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 100,
    delay_reason: null,
    supervisor_id: null,
    photo_path: '/uploads/panel_e3.jpg',
    status: 'APPROVED',
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    event_id: 'evt-105',
    document_id: null,
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'Loop testing for pressure transmitter IT-201 delayed due to missing calibration cert.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'ACT-501',
    matched_activity_id: 'ACT-501',
    discipline: 'INSTRUMENTATION',
    action: 'DELAY',
    event_type: 'DELAY',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: 'IT-201',
    location: 'Main Process Area',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 10,
    delay_reason: 'Vendor missing calibration certificates for test bench',
    supervisor_id: null,
    photo_path: null,
    status: 'HOLD',
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    event_id: 'evt-106',
    document_id: null,
    schedule_id: 'sched-OIL-2026',
    event_date: TODAY,
    raw_claim_text: 'HSE Safety Audit in Zone A completed. 3 housekeeping non-conformances cleared.',
    input_channel: 'TYPED_TEXT',
    language_detected: 'en',
    reported_activity_id: 'ACT-601',
    matched_activity_id: 'ACT-601',
    discipline: 'HSE',
    action: 'PROGRESS_UPDATE',
    event_type: 'PROGRESS_UPDATE',
    claim_mode: 'CUMULATIVE_PCT',
    asset_tag: null,
    location: 'Zone A',
    claimed_quantity: null,
    claimed_uom: null,
    claimed_pct: 100,
    delay_reason: null,
    supervisor_id: null,
    photo_path: null,
    status: 'APPROVED',
    created_at: new Date(Date.now() - 5400000).toISOString(),
  },
];

const MOCK_CANDIDATES: CandidateMatch[] = [
  {
    candidate_id: 'cand-101',
    event_id: 'evt-102',
    schedule_id: 'sched-OIL-2026',
    activity_id: 'ACT-202',
    rank_order: 1,
    match_tier: 'EXACT',
    composite_confidence: 0.88,
    semantic_score: 0.92,
    fuzzy_score: 0.84,
    location_score: 0.95,
    discipline_score: 1.0,
    supporting_signals: 'Exact match on activity tag "C4"; matched discipline CIVIL; matching location Block-2',
    disqualifying_signals: null,
  },
  {
    candidate_id: 'cand-102',
    event_id: 'evt-102',
    schedule_id: 'sched-OIL-2026',
    activity_id: 'ACT-203',
    rank_order: 2,
    match_tier: 'SEMANTIC',
    composite_confidence: 0.54,
    semantic_score: 0.61,
    fuzzy_score: 0.50,
    location_score: 0.40,
    discipline_score: 1.0,
    supporting_signals: 'Semantic overlap on rebar reinforcement tokens',
    disqualifying_signals: 'Location mismatch (Block-3 instead of Block-2)',
  },
  {
    candidate_id: 'cand-103',
    event_id: 'evt-102',
    schedule_id: 'sched-OIL-2026',
    activity_id: 'ACT-204',
    rank_order: 3,
    match_tier: 'FUZZY',
    composite_confidence: 0.32,
    semantic_score: 0.35,
    fuzzy_score: 0.42,
    location_score: 0.30,
    discipline_score: 0.8,
    supporting_signals: 'Partial token match on "column"',
    disqualifying_signals: 'Low composite score below threshold',
  },
];

const MOCK_FLAGS: ValidationIssue[] = [
  {
    issue_id: 'flag-101',
    event_id: 'evt-102',
    rule_code: 'CONFIDENCE_THRESHOLD_UNMET',
    severity: 'WARNING',
    description: 'Top candidate confidence (0.88) is below automated auto-approval threshold (0.90). Supervisor review required.',
  },
  {
    issue_id: 'flag-102',
    event_id: 'evt-102',
    rule_code: 'QUANTITY_VARIANCE',
    severity: 'WARNING',
    description: 'Claimed progress (+15%) exceeds baseline planned daily rate of 8% for Column C4.',
  },
];

const MOCK_DECISIONS: PlannerDecision[] = [
  {
    decision_id: 'dec-wld-01',
    event_id: 'EVT-20260814-001',
    selected_activity_id: 'PIP-PS3-WLD-024',
    action: 'APPROVE',
    approved_pct: 40,
    approved_qty: null,
    planner_id: 'usr-supervisor-01',
    justification: 'Welding inspection verified initial 40% joints.',
    decided_at: '2026-08-14T12:00:00Z',
  },
  {
    decision_id: 'dec-wld-02',
    event_id: 'EVT-20260815-001',
    selected_activity_id: 'PIP-PS3-WLD-024',
    action: 'APPROVE',
    approved_pct: 60,
    approved_qty: null,
    planner_id: 'usr-supervisor-01',
    justification: 'XER progress sync verified: cumulative 60% confirmed.',
    decided_at: '2026-08-15T15:00:00Z',
  },
  {
    decision_id: 'dec-tr-01',
    event_id: 'EVT-20260814-002',
    selected_activity_id: 'CIV-PS3-TR-0180',
    action: 'APPROVE',
    approved_pct: 100,
    approved_qty: 40,
    planner_id: 'usr-supervisor-01',
    justification: 'Trench excavation signed off by civil foreman per site diary.',
    decided_at: '2026-08-14T16:00:00Z',
  },
  {
    decision_id: 'dec-ins-01',
    event_id: 'EVT-20260819-001',
    selected_activity_id: 'INS-PS3-JB-001',
    action: 'APPROVE',
    approved_pct: 100,
    approved_qty: 1,
    planner_id: 'usr-supervisor-01',
    justification: 'Junction box installation verified against QA checklist.',
    decided_at: '2026-08-19T17:00:00Z',
  },
  {
    decision_id: 'dec-hse-01',
    event_id: 'EVT-20260814-003',
    selected_activity_id: 'HSE-PS3-IND-001',
    action: 'APPROVE',
    approved_pct: 100,
    approved_qty: 45,
    planner_id: 'usr-supervisor-01',
    justification: 'Toolbox talk roster confirmed 45 attendees.',
    decided_at: '2026-08-14T08:00:00Z',
  },
  {
    decision_id: 'dec-101',
    event_id: 'evt-104',
    selected_activity_id: 'ACT-401',
    action: 'APPROVE',
    approved_pct: 100,
    approved_qty: null,
    planner_id: 'usr-supervisor-01',
    justification: 'Verified physical installation and pre-commissioning signoff certificate.',
    decided_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    decision_id: 'dec-102',
    event_id: 'evt-106',
    selected_activity_id: 'ACT-601',
    action: 'APPROVE',
    approved_pct: 100,
    approved_qty: null,
    planner_id: 'usr-supervisor-01',
    justification: 'HSE walkthrough report attached and validated by Lead HSE Inspector.',
    decided_at: new Date(Date.now() - 5400000).toISOString(),
  },
];

const MOCK_ACTIVITIES: ScheduleActivity[] = [
  {
    activity_id: 'CIV-PS3-TR-0180',
    schedule_id: 'SIH26122_NFU',
    activity_name: 'Utility Trench Excavation CH 0+180 to CH 0+220',
    wbs_code: '1.01.01',
    discipline: 'CIVIL',
    location: 'Pump Station 3',
    asset_tag: 'TR-0180',
    planned_start: '2026-08-14',
    planned_finish: '2026-08-14',
    planned_quantity: 40.0,
    uom: 'm',
    baseline_pct_complete: 100,
  },
  {
    activity_id: 'PIP-PS3-WLD-024',
    schedule_id: 'SIH26122_NFU',
    activity_name: 'Utility Header Field Weld Joints',
    wbs_code: '1.02.01',
    discipline: 'PIPING',
    location: 'Pump Station 3',
    asset_tag: 'WLD-024',
    planned_start: '2026-08-11',
    planned_finish: '2026-08-15',
    planned_quantity: 24.0,
    uom: 'joints',
    baseline_pct_complete: 60,
  },
  {
    activity_id: 'MECH-PS3-DWP-003',
    schedule_id: 'SIH26122_NFU',
    activity_name: 'Dewatering Pump Relocation',
    wbs_code: '1.03.01',
    discipline: 'STATIC_ROTATING_EQUIPMENT',
    location: 'Pump Station 3',
    asset_tag: 'DWP-003',
    planned_start: '2026-08-14',
    planned_finish: '2026-08-14',
    planned_quantity: 1.0,
    uom: 'ea',
    baseline_pct_complete: 0,
  },
  {
    activity_id: 'ELE-PS3-CBL-001',
    schedule_id: 'SIH26122_NFU',
    activity_name: '11kV Medium Voltage Cable Pulling',
    wbs_code: '1.04.03',
    discipline: 'ELECTRICAL',
    location: 'Substation',
    asset_tag: 'CBL-001',
    planned_start: '2026-08-12',
    planned_finish: '2026-08-18',
    planned_quantity: 500.0,
    uom: 'm',
    baseline_pct_complete: 60,
  },
  {
    activity_id: 'INS-PS3-JB-001',
    schedule_id: 'SIH26122_NFU',
    activity_name: 'Junction Box JB-101 Field Mounting',
    wbs_code: '1.05.01',
    discipline: 'INSTRUMENTATION',
    location: 'Pump Station 3',
    asset_tag: 'JB-101',
    planned_start: '2026-08-19',
    planned_finish: '2026-08-20',
    planned_quantity: 1.0,
    uom: 'ea',
    baseline_pct_complete: 100,
  },
  {
    activity_id: 'HSE-PS3-IND-001',
    schedule_id: 'SIH26122_NFU',
    activity_name: 'Daily Site Safety Induction and Toolbox Talk',
    wbs_code: '1.06.01',
    discipline: 'HSE',
    location: 'Site Main Gate',
    asset_tag: 'HSE-IND',
    planned_start: '2026-08-14',
    planned_finish: '2026-08-14',
    planned_quantity: 45.0,
    uom: 'man',
    baseline_pct_complete: 100,
  },
  {
    activity_id: 'ACT-201',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'Foundation Concrete Pouring — Block 4',
    wbs_code: 'WBS-1.1.2',
    discipline: 'CIVIL',
    location: 'Block-4 North',
    asset_tag: 'FND-B4',
    planned_start: '2026-09-01',
    planned_finish: '2026-09-10',
    planned_quantity: 200,
    uom: 'cu.m',
    baseline_pct_complete: 40,
  },
  {
    activity_id: 'ACT-202',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'Rebar Placement — Column C4',
    wbs_code: 'WBS-1.1.3',
    discipline: 'CIVIL',
    location: 'Block-2',
    asset_tag: 'COL-C4',
    planned_start: '2026-09-05',
    planned_finish: '2026-09-12',
    planned_quantity: 12,
    uom: 'MT',
    baseline_pct_complete: 60,
  },
  {
    activity_id: 'ACT-301',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'Field Welding — 6" Crude Line L-1',
    wbs_code: 'WBS-2.1.1',
    discipline: 'PIPING',
    location: 'Pump Station 2',
    asset_tag: 'PUMP-002',
    planned_start: '2026-09-02',
    planned_finish: '2026-09-15',
    planned_quantity: 60,
    uom: 'joints',
    baseline_pct_complete: 30,
  },
  {
    activity_id: 'ACT-401',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'SCADA Panel E3 Installation & Power Up',
    wbs_code: 'WBS-3.2.1',
    discipline: 'ELECTRICAL',
    location: 'Unit E3 Control Room',
    asset_tag: 'PANEL-E3',
    planned_start: '2026-09-01',
    planned_finish: '2026-09-08',
    planned_quantity: 1,
    uom: 'unit',
    baseline_pct_complete: 100,
  },
  {
    activity_id: 'ACT-501',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'Loop Testing — Transmitter IT-201',
    wbs_code: 'WBS-4.1.2',
    discipline: 'INSTRUMENTATION',
    location: 'Main Process Area',
    asset_tag: 'IT-201',
    planned_start: '2026-09-08',
    planned_finish: '2026-09-14',
    planned_quantity: 10,
    uom: 'loops',
    baseline_pct_complete: 10,
  },
  {
    activity_id: 'ACT-601',
    schedule_id: 'sched-OIL-2026',
    activity_name: 'HSE Field Safety Compliance Walkthrough',
    wbs_code: 'WBS-5.1.1',
    discipline: 'HSE',
    location: 'Zone A',
    asset_tag: null,
    planned_start: '2026-09-08',
    planned_finish: '2026-09-08',
    planned_quantity: 1,
    uom: 'report',
    baseline_pct_complete: 100,
  },
];

const MOCK_AUDIT_LOGS: AuditLogEntry[] = [
  {
    log_id: 102,
    entity_type: 'execution_event',
    entity_id: 'evt-104',
    action: 'DECISION_APPROVE',
    actor_id: 'usr-supervisor-01',
    before_state: '{"status":"VALIDATED","claimed_pct":100}',
    after_state: '{"status":"APPROVED","approved_pct":100}',
    payload_hash: 'e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7',
    previous_hash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
    current_hash: 'f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    log_id: 101,
    entity_type: 'execution_event',
    entity_id: 'evt-106',
    action: 'DECISION_APPROVE',
    actor_id: 'usr-supervisor-01',
    before_state: '{"status":"VALIDATED","claimed_pct":100}',
    after_state: '{"status":"APPROVED","approved_pct":100}',
    payload_hash: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2',
    previous_hash: '0000000000000000000000000000000000000000000000000000000000000000',
    current_hash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
    timestamp: new Date(Date.now() - 5400000).toISOString(),
  },
];

// ─── API Methods ─────────────────────────────────────────────────────────────

export const authApi = {
  getMe: async (): Promise<UserProfile> => {
    if (USE_MOCKS) {
      await sleep(200);
      const rawUser = localStorage.getItem('user');
      if (rawUser) return JSON.parse(rawUser);
      return {
        id: 'usr-supervisor-01',
        email: 'planner@setu.ai',
        full_name: 'Rajesh Kumar (Lead Planner)',
        role: 'SUPERVISOR',
      };
    }
    const data: any = await apiFetch('/api/v1/auth/me');
    return { ...data, email: data.email || '' };
  },
};

export const claimsApi = {
  submitText: async (text: string, scheduleId: string = 'sched-OIL-2026'): Promise<{ event: ExecutionEvent }> => {
    if (USE_MOCKS) {
      await sleep(1000);
      const ev: ExecutionEvent = {
        event_id: `evt-${Date.now()}`,
        document_id: null,
        schedule_id: scheduleId,
        event_date: TODAY,
        raw_claim_text: text,
        input_channel: 'TYPED_TEXT',
        language_detected: 'en',
        reported_activity_id: null,
        matched_activity_id: null,
        discipline: 'CIVIL',
        action: 'PROGRESS_UPDATE',
        event_type: 'PROGRESS_UPDATE',
        claim_mode: 'CUMULATIVE_PCT',
        asset_tag: null,
        location: null,
        claimed_quantity: null,
        claimed_uom: null,
        claimed_pct: 50,
        delay_reason: null,
        supervisor_id: null,
        photo_path: null,
        status: 'EXTRACTED',
        created_at: new Date().toISOString(),
      };
      return { event: ev };
    }
    const data = await apiFetch('/api/v1/claims/text', {
      method: 'POST',
      body: JSON.stringify({ raw_claim_text: text, input_channel: 'TYPED_TEXT', schedule_id: scheduleId }),
    });
    return { event: data as any };
  },

  submitFile: async (file: File, scheduleId: string = 'sched-OIL-2026'): Promise<{ event: ExecutionEvent }> => {
    if (USE_MOCKS) {
      await sleep(1500);
      const ev: ExecutionEvent = {
        event_id: `evt-${Date.now()}`,
        document_id: `doc-${Date.now()}`,
        schedule_id: scheduleId,
        event_date: TODAY,
        raw_claim_text: `Ingested update from file: ${file.name}`,
        input_channel: 'FILE_UPLOAD',
        language_detected: 'en',
        reported_activity_id: null,
        matched_activity_id: null,
        discipline: 'CIVIL',
        action: 'PROGRESS_UPDATE',
        event_type: 'PROGRESS_UPDATE',
        claim_mode: 'CUMULATIVE_PCT',
        asset_tag: null,
        location: null,
        claimed_quantity: null,
        claimed_uom: null,
        claimed_pct: null,
        delay_reason: null,
        supervisor_id: null,
        photo_path: null,
        status: 'EXTRACTED',
        created_at: new Date().toISOString(),
      };
      return { event: ev };
    }
    const form = new FormData();
    form.append('file', file);
    const token = localStorage.getItem('supabase_access_token') || localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${BASE_URL}/api/v1/claims/file`, {
      method: 'POST',
      headers,
      body: form,
    });
    if (!res.ok) throw new Error(await res.text().catch(() => 'File submit failed'));
    const data = await res.json();
    return { event: data as any };
  },

  match: async (eventId: string): Promise<{ status: ClaimStatus; matches: CandidateMatch[] }> => {
    if (USE_MOCKS) {
      await sleep(1000);
      return { status: 'MATCHED', matches: MOCK_CANDIDATES };
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/match`, { method: 'POST' });
    return { status: data.status, matches: data.candidates || [] };
  },

  check: async (eventId: string): Promise<{ status: ClaimStatus; issues: ValidationIssue[] }> => {
    if (USE_MOCKS) {
      await sleep(800);
      return { status: 'REVIEW_REQUIRED', issues: MOCK_FLAGS };
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/check`, { method: 'POST' });
    return { status: data.status, issues: data.validation_issues || [] };
  },

  getCandidates: async (eventId: string): Promise<CandidateMatch[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_CANDIDATES.filter((c) => c.event_id === eventId || eventId === 'evt-102');
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/candidates`);
    return data.candidates || [];
  },

  getConflicts: async (eventId: string): Promise<ConflictRecord[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return [
        {
          conflict_id: 'cnf-001',
          schedule_id: 'sched-OIL-2026',
          activity_id: 'ACT-202',
          reporting_period: TODAY,
          event_id_a: eventId,
          event_id_b: 'evt-previous-09',
          value_a: 75,
          value_b: 60,
          variance_pct: 25,
          status: 'OPEN',
        },
      ];
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/conflicts`);
    return data.conflicts || [];
  },

  getValidation: async (eventId: string): Promise<ValidationIssue[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_FLAGS;
    }
    const data: any = await apiFetch(`/api/v1/claims/${eventId}/validation`);
    return data.validation_issues || [];
  },

  getEvent: async (eventId: string): Promise<ExecutionEvent> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_EVENTS.find((e) => e.event_id === eventId) || MOCK_EVENTS[1];
    }
    return apiFetch(`/api/v1/claims/${eventId}`);
  },
};

export const digestApi = {
  getByDate: async (dateStr: string): Promise<ExecutionEvent[]> => {
    if (USE_MOCKS) {
      await sleep(500);
      return MOCK_EVENTS;
    }
    return apiFetch(`/api/v1/digest?date=${dateStr}`);
  },

  bulkApprove: async (eventIds: string[]): Promise<{ approved: string[]; failed: string[] }> => {
    if (USE_MOCKS) {
      await sleep(900);
      return { approved: eventIds, failed: [] };
    }
    const data: any = await apiFetch('/api/v1/digest/bulk-approve', {
      method: 'POST',
      body: JSON.stringify({ event_ids: eventIds }),
    });
    return { approved: data.approved || [], failed: (data.failed || []).map((f: any) => typeof f === 'string' ? f : f.event_id) };
  },
};

export const decisionsApi = {
  submit: async (payload: {
    event_id: string;
    selected_activity_id: string;
    action: DecisionAction;
    approved_pct?: number | null;
    approved_qty?: number | null;
    justification: string;
  }): Promise<PlannerDecision> => {
    if (USE_MOCKS) {
      await sleep(800);
      return {
        decision_id: `dec-${Date.now()}`,
        event_id: payload.event_id,
        selected_activity_id: payload.selected_activity_id,
        action: payload.action,
        approved_pct: payload.approved_pct ?? null,
        approved_qty: payload.approved_qty ?? null,
        planner_id: 'usr-supervisor-01',
        justification: payload.justification,
        decided_at: new Date().toISOString(),
      };
    }
    const data: any = await apiFetch('/api/v1/decisions', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return {
      decision_id: data.decision_id,
      event_id: data.event_id,
      selected_activity_id: data.selected_activity_id,
      action: data.action as DecisionAction,
      approved_pct: payload.approved_pct ?? null,
      approved_qty: payload.approved_qty ?? null,
      planner_id: '',
      justification: payload.justification,
      decided_at: new Date().toISOString(),
    };
  },

  getRecent: async (): Promise<PlannerDecision[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_DECISIONS;
    }
    return apiFetch('/api/v1/decisions?limit=10');
  },
};

export const dashboardApi = {
  getDelayReasons: async (): Promise<{ reason: string; count: number }[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return [
        { reason: 'Material / Equipment Delivery Delay', count: 14 },
        { reason: 'Adverse Weather / Rain Shutdown', count: 8 },
        { reason: 'Subcontractor Manpower Shortage', count: 6 },
        { reason: 'Missing Engineering Drawings / RFC', count: 4 },
        { reason: 'Inspection Clearance Bottleneck', count: 3 },
      ];
    }
    const data: any = await apiFetch('/api/v1/dashboard/delay-reasons');
    return (data.delay_reasons || []).map((d: any) => ({ reason: d.delay_reason, count: d.count }));
  },

  getInstitutionalMemory: async (): Promise<{ topic: string; resolution: string; count: number }[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return [
        { topic: 'Block-4 Concrete Curing Time', resolution: 'Accelerate with rapid-hardening admixture when temperature drops below 15°C', count: 12 },
        { topic: 'Pump Station Skid Alignment', resolution: 'Require dual-laser alignment signoff before line welding', count: 9 },
        { topic: 'SCADA Panel Power-Up Protocol', resolution: 'Perform secondary ground check prior to energization', count: 5 },
      ];
    }
    const data: any = await apiFetch('/api/v1/dashboard/institutional-memory');
    return (data.activities || []).map((a: any) => ({ topic: a.activity_id + ' (' + a.discipline + ')', resolution: a.variance_days !== null ? (a.variance_days > 0 ? a.variance_days + ' days delayed' : Math.abs(a.variance_days) + ' days ahead') : 'No actuals yet', count: a.planned_duration || 0 }));
  },

  getForecast: async (): Promise<{ milestone: string; target_date: string; forecast_date: string; slippage_days: number }[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return [
        { milestone: 'MS-02 Foundation Completion', target_date: '2026-09-15', forecast_date: '2026-09-18', slippage_days: 3 },
        { milestone: 'MS-03 Piping Hydrotest Clearance', target_date: '2026-10-01', forecast_date: '2026-10-05', slippage_days: 4 },
        { milestone: 'MS-04 Overall Substation Energization', target_date: '2026-11-15', forecast_date: '2026-11-20', slippage_days: 5 },
      ];
    }
    const data: any = await apiFetch('/api/v1/dashboard/forecast?discipline=CIVIL');
    return (data.activities || [data]).map((a: any) => ({ milestone: a.activity_id || a.discipline || 'Unknown', target_date: a.planned_duration ? a.planned_duration + ' days planned' : 'N/A', forecast_date: a.forecast_duration ? a.forecast_duration + ' days forecast' : 'N/A', slippage_days: a.forecast_duration && a.planned_duration ? a.forecast_duration - a.planned_duration : 0 }));
  },

  getSilentActivities: async (): Promise<ScheduleActivity[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return [
        {
          activity_id: 'ACT-301',
          schedule_id: 'sched-OIL-2026',
          activity_name: 'Field Welding — 6" Crude Line L-1',
          wbs_code: 'WBS-2.1.1',
          discipline: 'PIPING',
          location: 'Pump Station 2',
          asset_tag: 'PUMP-002',
          planned_start: '2026-09-02',
          planned_finish: '2026-09-15',
          planned_quantity: 60,
          uom: 'joints',
          baseline_pct_complete: 30,
        },
      ];
    }
    const data: any = await apiFetch('/api/v1/alerts/silent-activities');
    return (data.silent_activities || []).map((a: any) => ({ ...a, asset_tag: a.asset_tag || null, uom: a.uom || null, baseline_pct_complete: a.baseline_pct_complete || 0 }));
  },

  getExportCsvUrl: (): string => {
    return `${BASE_URL}/api/v1/export/csv`;
  },
};

export const activitiesApi = {
  list: async (scheduleId?: string, discipline?: string): Promise<{
    schedule_id: string | null;
    schedules: { schedule_id: string; project_name: string; data_date?: string | null }[];
    activities: ActivityListItem[];
  }> => {
    if (USE_MOCKS) {
      await sleep(300);
      let list = MOCK_ACTIVITIES.map((act) => {
        let approved_pct = 0;
        if (act.activity_id === 'CIV-PS3-TR-0180' || act.activity_id === 'INS-PS3-JB-001' || act.activity_id === 'HSE-PS3-IND-001') {
          approved_pct = 100;
        } else if (act.activity_id === 'PIP-PS3-WLD-024') {
          approved_pct = 60;
        } else if (act.activity_id === 'ELE-PS3-CBL-001') {
          approved_pct = 60;
        } else if (act.activity_id === 'ACT-202') {
          approved_pct = 75;
        } else if (act.activity_id === 'ACT-401') {
          approved_pct = 100;
        }

        let status = 'NOT STARTED';
        if (approved_pct >= 100) status = 'COMPLETED';
        else if (approved_pct > 0) status = 'IN PROGRESS';

        return {
          ...act,
          approved_pct,
          approved_quantity: null,
          actual_start: null,
          actual_finish: null,
          status,
        };
      });

      if (discipline && discipline !== 'ALL') {
        list = list.filter((a) => a.discipline === discipline);
      }

      return {
        schedule_id: 'SIH26122_NFU',
        schedules: [
          { schedule_id: 'SIH26122_NFU', project_name: 'SIH26122 Canonical Demo Schedule', data_date: '2026-08-14' },
        ],
        activities: list,
      };
    }

    const params = new URLSearchParams();
    if (scheduleId) params.append('schedule_id', scheduleId);
    if (discipline && discipline !== 'ALL') params.append('discipline', discipline);
    const queryStr = params.toString() ? `?${params.toString()}` : '';
    const data: any = await apiFetch(`/api/v1/activities${queryStr}`);
    return {
      schedule_id: data.schedule_id || null,
      schedules: data.schedules || [],
      activities: (data.activities || []).map((a: any) => ({
        ...a,
        approved_pct: a.approved_pct ?? 0,
        status: a.status || (a.approved_pct >= 100 ? 'COMPLETED' : a.approved_pct > 0 ? 'IN PROGRESS' : 'NOT STARTED'),
      })),
    };
  },

  getHistory: async (activityId: string): Promise<{
    activity: ActivityListItem;
    history: ActivityHistoryItem[];
  }> => {
    if (USE_MOCKS) {
      await sleep(400);
      const mockAct = MOCK_ACTIVITIES.find((a) => a.activity_id === activityId) || {
        activity_id: activityId,
        schedule_id: 'SIH26122_NFU',
        activity_name: activityId,
        wbs_code: null,
        discipline: 'CIVIL' as Discipline,
        location: 'Pump Station 3',
        asset_tag: null,
        planned_start: '2026-08-14',
        planned_finish: '2026-08-18',
        planned_quantity: 40,
        uom: 'm',
        baseline_pct_complete: 0,
      };

      let approved_pct = 0;
      if (activityId === 'CIV-PS3-TR-0180' || activityId === 'INS-PS3-JB-001' || activityId === 'HSE-PS3-IND-001') {
        approved_pct = 100;
      } else if (activityId === 'PIP-PS3-WLD-024') {
        approved_pct = 60;
      } else if (activityId === 'ELE-PS3-CBL-001') {
        approved_pct = 60;
      } else if (activityId === 'ACT-202') {
        approved_pct = 75;
      }

      const status = approved_pct >= 100 ? 'COMPLETED' : approved_pct > 0 ? 'IN PROGRESS' : 'NOT STARTED';

      const fullAct: ActivityListItem = {
        ...mockAct,
        approved_pct,
        approved_quantity: null,
        actual_start: null,
        actual_finish: null,
        status,
      };

      const matchingEvents = MOCK_EVENTS.filter(
        (e) => e.matched_activity_id === activityId || e.reported_activity_id === activityId
      );

      const historyItems: ActivityHistoryItem[] = matchingEvents.map((ev) => {
        const dec = MOCK_DECISIONS.find((d) => d.event_id === ev.event_id);
        return {
          timestamp: ev.created_at,
          event_id: ev.event_id,
          event_date: ev.event_date,
          raw_claim_text: ev.raw_claim_text,
          input_channel: ev.input_channel,
          claimed_pct: ev.claimed_pct,
          claimed_qty: ev.claimed_quantity,
          claimed_uom: ev.claimed_uom,
          reported_activity_id: ev.reported_activity_id,
          matched_activity_id: ev.matched_activity_id,
          discipline: ev.discipline,
          location: ev.location,
          asset_tag: ev.asset_tag,
          delay_reason: ev.delay_reason,
          status: ev.status,
          supervisor_action: dec ? dec.action : (ev.status === 'APPROVED' ? 'APPROVE' : null),
          approved_pct: dec ? dec.approved_pct : (ev.status === 'APPROVED' ? ev.claimed_pct : null),
          approved_qty: dec ? dec.approved_qty : null,
          justification: dec ? dec.justification : (ev.status === 'APPROVED' ? 'Verified by Supervisor inspection' : null),
          decision: dec ? {
            decision_id: dec.decision_id,
            action: dec.action,
            approved_pct: dec.approved_pct,
            approved_qty: dec.approved_qty,
            planner_id: dec.planner_id,
            justification: dec.justification,
            decided_at: dec.decided_at,
          } : null,
          actor: ev.input_channel === 'VOICE' ? 'Site Engineer (Voice Log)' : (ev.input_channel === 'FILE_UPLOAD' ? 'Site Engineer (Document Ingestion)' : 'Site Engineer (Field Claim)'),
          source_references: [
            {
              reference_id: `ref-${ev.event_id}`,
              event_id: ev.event_id,
              file_name: ev.document_id ? `${ev.document_id}.pdf` : null,
              sheet_name: null,
              row_cell_ref: null,
              message_id: null,
              raw_snippet: ev.raw_claim_text,
            },
          ],
        };
      });

      return {
        activity: fullAct,
        history: historyItems,
      };
    }

    const data: any = await apiFetch(`/api/v1/activities/${activityId}/history`);
    const timeline = data.timeline || [];
    const eventItems = timeline.filter((t: any) => t.type === 'execution_event');

    let activityMeta: ActivityListItem;
    if (data.activity) {
      activityMeta = {
        ...data.activity,
        approved_pct: data.activity.approved_pct ?? 0,
        status: data.activity.status || (data.activity.approved_pct >= 100 ? 'COMPLETED' : data.activity.approved_pct > 0 ? 'IN PROGRESS' : 'NOT STARTED'),
      };
    } else {
      activityMeta = {
        activity_id: activityId,
        schedule_id: eventItems[0]?.schedule_id || '',
        activity_name: activityId,
        wbs_code: null,
        discipline: (eventItems[0]?.discipline || 'CIVIL') as Discipline,
        location: eventItems[0]?.location || '',
        asset_tag: eventItems[0]?.asset_tag || null,
        planned_start: '',
        planned_finish: '',
        planned_quantity: null,
        uom: null,
        baseline_pct_complete: 0,
        approved_pct: 0,
        approved_quantity: null,
        actual_start: null,
        actual_finish: null,
        status: 'NOT STARTED',
      };
    }

    return {
      activity: activityMeta,
      history: eventItems.map((ev: any) => ({
        timestamp: ev.timestamp || ev.event_date || '',
        event_id: ev.event_id || '',
        event_date: ev.event_date || null,
        raw_claim_text: ev.raw_claim_text || '',
        input_channel: (ev.input_channel || 'TYPED_TEXT') as InputChannel,
        claimed_pct: ev.claimed_pct ?? null,
        claimed_qty: ev.claimed_quantity ?? null,
        claimed_uom: ev.claimed_uom ?? null,
        reported_activity_id: ev.reported_activity_id ?? null,
        matched_activity_id: ev.matched_activity_id ?? null,
        discipline: ev.discipline ?? null,
        location: ev.location ?? null,
        asset_tag: ev.asset_tag ?? null,
        delay_reason: ev.delay_reason ?? null,
        status: ev.status || 'EXTRACTED',
        supervisor_action: ev.supervisor_action || ev.decision?.action || null,
        approved_pct: ev.approved_pct ?? ev.decision?.approved_pct ?? null,
        approved_qty: ev.approved_qty ?? ev.decision?.approved_qty ?? null,
        justification: ev.justification || ev.decision?.justification || null,
        decision: ev.decision || null,
        source_references: ev.source_references || [],
        actor: ev.supervisor_action ? 'Supervisor Review' : (ev.input_channel === 'VOICE' ? 'Site Engineer (Voice Log)' : 'Site Engineer (Field Claim)'),
      })),
    };
  },
};

export const schedulesApi = {
  getActivities: async (scheduleId: string = 'sched-OIL-2026'): Promise<ScheduleActivity[]> => {
    if (USE_MOCKS) {
      await sleep(300);
      return MOCK_ACTIVITIES;
    }
    return apiFetch(`/api/v1/schedules/${scheduleId}/activities`);
  },

  getImpactPreview: async (activityId: string, delayDays: number): Promise<ImpactPreviewResult> => {
    if (USE_MOCKS) {
      await sleep(500);
      const activity = MOCK_ACTIVITIES.find((a) => a.activity_id === activityId) || MOCK_ACTIVITIES[0];
      return {
        activity_id: activity.activity_id,
        delay_days: delayDays,
        disclaimer: 'Preview only · Immediate FS successors · Not full CPM recalculation',
        successors: [
          {
            successor_activity_id: 'ACT-202',
            activity_name: 'Rebar Placement — Column C4',
            relationship_type: 'FS',
            original_start: '2026-09-05',
            original_finish: '2026-09-12',
            shifted_start: '2026-09-10',
            shifted_finish: '2026-09-17',
            lag_days: 0,
          },
          {
            successor_activity_id: 'ACT-301',
            activity_name: 'Field Welding — 6" Crude Line L-1',
            relationship_type: 'FS',
            original_start: '2026-09-12',
            original_finish: '2026-09-25',
            shifted_start: '2026-09-17',
            shifted_finish: '2026-09-30',
            lag_days: 0,
          },
        ],
      };
    }
    const data: any = await apiFetch(`/api/v1/schedule/${activityId}/impact-preview?delay_days=${delayDays}`);
    return {
      activity_id: data.activity_id,
      delay_days: data.delay_days,
      disclaimer: 'Preview only · Immediate FS successors · Not full CPM recalculation',
      successors: (data.impacts || []).map((imp: any) => ({
        successor_activity_id: imp.successor_activity_id,
        activity_name: imp.successor_activity_id,
        relationship_type: imp.dependency_type || 'FS',
        original_start: imp.original_earliest_start || '',
        original_finish: '',
        shifted_start: imp.shifted_earliest_start || '',
        shifted_finish: '',
        lag_days: 0,
      })),
    };
  },
};

export const auditApi = {
  getLogs: async (): Promise<AuditLogEntry[]> => {
    if (USE_MOCKS) {
      await sleep(400);
      return MOCK_AUDIT_LOGS;
    }
    return apiFetch('/api/v1/audit');
  },
};

export { MOCK_EVENTS, MOCK_ACTIVITIES, MOCK_DECISIONS };
