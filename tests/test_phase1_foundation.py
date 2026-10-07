import re
import sqlite3
import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.actuals import (
    _dispatch_adapters,
    get_approved_actual,
    get_approved_pct,
    upsert_approved_actual,
)
from backend.shared.auth import VALID_ROLES, UserProfile, get_current_user, require_role


class SQLitePsycopgAdapter:
    """
    Lightweight DB connection adapter for deterministic in-memory testing.
    Translates Postgres-specific query patterns (%s, FOR UPDATE) to SQLite syntax.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def execute(self, query: str, params=None):
        clean_q = query.replace("FOR UPDATE", "")
        clean_q = re.sub(r"%s", "?", clean_q)
        cur = self.conn.cursor()
        if params is not None:
            cur.execute(clean_q, params)
        else:
            cur.execute(clean_q)
        return cur

    def commit(self):
        self.conn.commit()


def create_test_db() -> SQLitePsycopgAdapter:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE profiles (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('SITE_ENGINEER', 'SUPERVISOR')),
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE execution_events (
            event_id TEXT PRIMARY KEY,
            schedule_id TEXT NOT NULL,
            event_date TEXT,
            claim_mode TEXT DEFAULT 'CUMULATIVE_PCT',
            event_type TEXT,
            claimed_quantity REAL,
            claimed_pct REAL,
            matched_activity_id TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE planner_decisions (
            decision_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            selected_activity_id TEXT NOT NULL,
            action TEXT,
            approved_pct REAL,
            approved_qty REAL,
            decided_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE claim_activity_splits (
            split_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            activity_id TEXT NOT NULL,
            split_basis TEXT,
            split_pct REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE approved_actuals (
            actual_id TEXT PRIMARY KEY,
            decision_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            schedule_id TEXT NOT NULL,
            activity_id TEXT NOT NULL,
            actual_start TEXT,
            actual_finish TEXT,
            actual_pct_complete REAL,
            actual_quantity REAL,
            exported_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE (schedule_id, activity_id)
        )
        """
    )
    return SQLitePsycopgAdapter(conn)


# =========================================================================
# 1. Auth & RBAC Tests
# =========================================================================

def test_auth_roles():
    assert VALID_ROLES == {"SITE_ENGINEER", "SUPERVISOR"}

    # Supported roles pass dependency creation
    dep_eng = require_role("SITE_ENGINEER")
    dep_sup = require_role("SUPERVISOR")
    assert callable(dep_eng)
    assert callable(dep_sup)

    # Unsupported role raises ValueError
    try:
        require_role("ADMIN")
        assert False, "require_role('ADMIN') should fail"
    except ValueError:
        pass


def test_role_dependency_enforcement():
    dep_engineer = require_role("SITE_ENGINEER")
    dep_supervisor = require_role("SUPERVISOR")

    engineer_user = UserProfile(
        id="11111111-1111-1111-1111-111111111111",
        full_name="Alice Engineer",
        role="SITE_ENGINEER",
    )
    supervisor_user = UserProfile(
        id="22222222-2222-2222-2222-222222222222",
        full_name="Bob Supervisor",
        role="SUPERVISOR",
    )

    # Valid roles return user
    assert dep_engineer(engineer_user) == engineer_user
    assert dep_supervisor(supervisor_user) == supervisor_user

    # Mismatched roles raise HTTP 403
    try:
        dep_engineer(supervisor_user)
        assert False, "Should raise 403"
    except HTTPException as e:
        assert e.status_code == 403

    try:
        dep_supervisor(engineer_user)
        assert False, "Should raise 403"
    except HTTPException as e:
        assert e.status_code == 403


def test_auth_me_endpoint_with_client():
    client = TestClient(app)

    # Unauthenticated request -> 401
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    # Invalid token -> 401
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert resp.status_code == 401

    # Override dependency for authenticated testing
    mock_user = UserProfile(
        id="33333333-3333-3333-3333-333333333333",
        full_name="Test Planner",
        role="SITE_ENGINEER",
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer mocked-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == mock_user.id
        assert data["full_name"] == mock_user.full_name
        assert data["role"] == mock_user.role
    finally:
        app.dependency_overrides.clear()


# =========================================================================
# 2. Approved-Actual Calculations (8 Canonical Scenarios)
# =========================================================================

def test_cumulative_percentage_replacement():
    """
    Scenario 1: Cumulative percentage replacement.
    A newly effective APPROVE percentage replaces previous actual_pct_complete.
    Do not add percentages together (40% then 60% must be 60%, not 100%).
    """
    db = create_test_db()
    sch_id = "SCH-CUM-1"
    act_id = "ACT-01"

    # Step 1: Initial claim 40%
    res1 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-1",
        decision_id="DEC-1",
        action="APPROVE",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=40.0,
        conn=db,
    )
    assert res1 is not None
    assert res1["actual_pct_complete"] == 40.0

    # Step 2: Second claim 60%
    res2 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-2",
        decision_id="DEC-2",
        action="APPROVE",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=60.0,
        conn=db,
    )
    assert res2 is not None
    # Must replace, NOT accumulate (60.0 != 100.0)
    assert res2["actual_pct_complete"] == 60.0


def test_start_then_finish_merging():
    """
    Scenario 2: Start then finish.
    A finish event must never erase an existing actual_start date.
    """
    db = create_test_db()
    sch_id = "SCH-DATES-1"
    act_id = "ACT-02"

    # Start claim
    res_start = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-START",
        decision_id="DEC-START",
        action="APPROVE",
        event_type="ACTUAL_START",
        actual_start="2026-08-01",
        conn=db,
    )
    assert res_start["actual_start"] == "2026-08-01"
    assert res_start["actual_finish"] is None

    # Finish claim
    res_finish = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-FINISH",
        decision_id="DEC-FINISH",
        action="APPROVE",
        event_type="ACTUAL_FINISH",
        actual_finish="2026-08-15",
        conn=db,
    )
    assert res_finish["actual_start"] == "2026-08-01", "actual_start was erased by finish event!"
    assert res_finish["actual_finish"] == "2026-08-15"


def test_finish_then_start_merging():
    """
    Scenario 3: Finish then start.
    A start event must never erase an existing actual_finish date.
    """
    db = create_test_db()
    sch_id = "SCH-DATES-2"
    act_id = "ACT-03"

    # Finish claim first
    res_finish = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-F",
        decision_id="DEC-F",
        action="APPROVE",
        event_type="ACTUAL_FINISH",
        actual_finish="2026-08-20",
        conn=db,
    )
    assert res_finish["actual_finish"] == "2026-08-20"
    assert res_finish["actual_start"] is None

    # Start claim arrives second
    res_start = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-S",
        decision_id="DEC-S",
        action="APPROVE",
        event_type="ACTUAL_START",
        actual_start="2026-08-10",
        conn=db,
    )
    assert res_start["actual_finish"] == "2026-08-20", "actual_finish was erased by start event!"
    assert res_start["actual_start"] == "2026-08-10"


def test_multiple_incremental_quantities_and_recalculation():
    """
    Scenarios 4-8:
    - Multiple incremental quantities
    - REJECT (contributes zero, does not write approved_actuals)
    - HOLD (contributes zero, does not write approved_actuals)
    - HOLD followed by APPROVE (counted once)
    - EDIT replacing an earlier decision
    - No double counting
    """
    db = create_test_db()
    sch_id = "SCH-QTY-1"
    act_id = "CIV-01"

    # --- Scenario 4: Multiple incremental quantities ---
    # Event 1: claimed 25.0 m
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-Q1", sch_id, "INCREMENTAL_QUANTITY", 25.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-Q1", "EV-Q1", act_id, "APPROVE", "2026-08-01 10:00:00"),
    )
    res_q1 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-Q1",
        decision_id="DEC-Q1",
        action="APPROVE",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    assert res_q1["actual_quantity"] == 25.0

    # Event 2: claimed 35.0 m (APPROVE)
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-Q2", sch_id, "INCREMENTAL_QUANTITY", 35.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-Q2", "EV-Q2", act_id, "APPROVE", "2026-08-02 10:00:00"),
    )
    res_q2 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-Q2",
        decision_id="DEC-Q2",
        action="APPROVE",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    assert res_q2["actual_quantity"] == 60.0  # 25.0 + 35.0

    # Event 3: claimed 10.0 m, but planner EDITs with approved_qty = 15.0 m
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-Q3", sch_id, "INCREMENTAL_QUANTITY", 10.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_qty, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-Q3", "EV-Q3", act_id, "EDIT", 15.0, "2026-08-03 10:00:00"),
    )
    res_q3 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-Q3",
        decision_id="DEC-Q3",
        action="EDIT",
        claim_mode="INCREMENTAL_QUANTITY",
        approved_qty=15.0,
        conn=db,
    )
    # COALESCE uses approved_qty (15.0) instead of claimed (10.0): 25 + 35 + 15 = 75.0
    assert res_q3["actual_quantity"] == 75.0

    # --- Scenario 5: REJECT ---
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-Q4", sch_id, "INCREMENTAL_QUANTITY", 50.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-Q4", "EV-Q4", act_id, "REJECT", "2026-08-04 10:00:00"),
    )
    res_q4 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-Q4",
        decision_id="DEC-Q4",
        action="REJECT",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    # REJECT must return None and NOT touch approved_actuals
    assert res_q4 is None
    # Current approved actual remains 75.0
    cur_actual = db.execute(
        "SELECT actual_quantity FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()
    assert cur_actual["actual_quantity"] == 75.0

    # --- Scenario 6: HOLD ---
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-Q5", sch_id, "INCREMENTAL_QUANTITY", 30.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-Q5-HOLD", "EV-Q5", act_id, "HOLD", "2026-08-05 10:00:00"),
    )
    res_q5_hold = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-Q5",
        decision_id="DEC-Q5-HOLD",
        action="HOLD",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    # HOLD must return None and NOT touch approved_actuals
    assert res_q5_hold is None
    cur_actual = db.execute(
        "SELECT actual_quantity FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()
    assert cur_actual["actual_quantity"] == 75.0

    # --- Scenario 7: HOLD followed by APPROVE ---
    # Planner later opens EV-Q5 and approves it
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-Q5-APP", "EV-Q5", act_id, "APPROVE", "2026-08-06 10:00:00"),
    )
    res_q5_app = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-Q5",
        decision_id="DEC-Q5-APP",
        action="APPROVE",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    # Total: 75.0 + 30.0 = 105.0
    assert res_q5_app["actual_quantity"] == 105.0

    # --- Scenario 8: EDIT replacing an earlier effective decision ---
    # Planner modifies DEC-Q1 (was 25.0) to have approved_qty = 20.0
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_qty, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-Q1-EDIT", "EV-Q1", act_id, "EDIT", 20.0, "2026-08-07 10:00:00"),
    )
    res_q1_edit = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-Q1",
        decision_id="DEC-Q1-EDIT",
        action="EDIT",
        claim_mode="INCREMENTAL_QUANTITY",
        approved_qty=20.0,
        conn=db,
    )
    # Total: 20 (Q1) + 35 (Q2) + 15 (Q3) + 30 (Q5) = 100.0 (NOT 120.0)
    assert res_q1_edit["actual_quantity"] == 100.0

    # --- No double counting verification ---
    # Exactly one row exists in approved_actuals
    rows = db.execute(
        "SELECT * FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["actual_quantity"] == 100.0


def test_planner_decision_authority():
    """
    Scenario: Selected activity in planner_decisions is authoritative over machine matching.
    """
    db = create_test_db()
    sch_id = "SCH-AUTH-1"
    machine_act = "ACT-MACHINE"
    planner_act = "ACT-HUMAN-OVERRIDE"

    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, matched_activity_id) VALUES (?, ?, ?)",
        ("EV-AUTH", sch_id, machine_act),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-AUTH", "EV-AUTH", planner_act, "APPROVE", 80.0, "2026-08-01 10:00:00"),
    )

    # Calling upsert_approved_actual with decision_id
    res = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=machine_act,  # Even if machine activity is passed
        event_id="EV-AUTH",
        decision_id="DEC-AUTH",
        action="APPROVE",
        approved_pct=80.0,
        conn=db,
    )
    assert res["activity_id"] == planner_act, "Must write to authoritative selected_activity_id"


def test_adapter_boundary_isolation():
    """
    Ensures _dispatch_adapters returns valid non-blocking status.
    """
    status = _dispatch_adapters({"actual_id": "test", "activity_id": "act-1"})
    assert isinstance(status, dict)
    assert status.get("csv_export") == "not_implemented_phase1"
    assert status.get("p6_rest") == "not_implemented_phase1"
