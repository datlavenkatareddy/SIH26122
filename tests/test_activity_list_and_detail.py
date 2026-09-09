import re
import sqlite3
from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend.shared.auth import UserProfile, get_current_user


class SQLitePsycopgAdapter:
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


def create_full_test_db() -> SQLitePsycopgAdapter:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE schedules (
            schedule_id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            data_date TEXT,
            source_format TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE schedule_activities (
            activity_id TEXT NOT NULL,
            schedule_id TEXT NOT NULL,
            activity_name TEXT NOT NULL,
            wbs_code TEXT,
            discipline TEXT NOT NULL,
            location TEXT NOT NULL,
            asset_tag TEXT,
            planned_start TEXT NOT NULL,
            planned_finish TEXT NOT NULL,
            planned_quantity REAL,
            uom TEXT,
            baseline_pct_complete REAL DEFAULT 0.0,
            PRIMARY KEY (schedule_id, activity_id)
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (schedule_id, activity_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE execution_events (
            event_id TEXT PRIMARY KEY,
            document_id TEXT,
            schedule_id TEXT NOT NULL,
            event_date TEXT NOT NULL,
            raw_claim_text TEXT NOT NULL,
            input_channel TEXT NOT NULL,
            language_detected TEXT,
            reported_activity_id TEXT,
            matched_activity_id TEXT,
            discipline TEXT,
            action TEXT,
            event_type TEXT,
            claim_mode TEXT DEFAULT 'CUMULATIVE_PCT',
            asset_tag TEXT,
            location TEXT,
            claimed_quantity REAL,
            claimed_uom TEXT,
            claimed_pct REAL,
            delay_reason TEXT,
            supervisor_id TEXT,
            photo_path TEXT,
            status TEXT DEFAULT 'EXTRACTED',
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE source_references (
            reference_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            file_name TEXT,
            sheet_name TEXT,
            row_cell_ref TEXT,
            message_id TEXT,
            raw_snippet TEXT NOT NULL
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
            planner_id TEXT NOT NULL,
            justification TEXT NOT NULL,
            decided_at TEXT
        )
        """
    )
    return SQLitePsycopgAdapter(conn)


def test_list_activities_endpoint_registered():
    routes = list(app.openapi()["paths"].keys())
    assert "/api/v1/activities" in routes, "GET /api/v1/activities not registered on app"


def test_list_activities_authorization():
    client = TestClient(app)

    # 1. Unauthenticated -> 401
    resp = client.get("/api/v1/activities")
    assert resp.status_code == 401

    # 2. SITE_ENGINEER -> 403
    engineer = UserProfile(id="11111111-1111-1111-1111-111111111111", full_name="Alice", role="SITE_ENGINEER")
    app.dependency_overrides[get_current_user] = lambda: engineer
    try:
        resp = client.get(
            "/api/v1/activities",
            headers={"Authorization": "Bearer mock-token"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()

    # 3. SUPERVISOR -> 200
    supervisor = UserProfile(id="22222222-2222-2222-2222-222222222222", full_name="Bob", role="SUPERVISOR")
    app.dependency_overrides[get_current_user] = lambda: supervisor
    try:
        resp = client.get(
            "/api/v1/activities",
            headers={"Authorization": "Bearer mock-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "activities" in data
        assert "schedules" in data
    finally:
        app.dependency_overrides.clear()


def test_status_derivation_from_approved_actuals(monkeypatch):
    db = create_full_test_db()
    # 1. Insert schedule
    db.execute(
        "INSERT INTO schedules (schedule_id, project_name) VALUES ('SCHED-TEST', 'Test Schedule')"
    )
    # 2. Insert 3 activities
    # Act 1: 0% approved actual -> NOT STARTED
    db.execute(
        """
        INSERT INTO schedule_activities (schedule_id, activity_id, activity_name, discipline, location, planned_start, planned_finish, planned_quantity, uom, baseline_pct_complete)
        VALUES ('SCHED-TEST', 'ACT-NOT-STARTED', 'Trench Excavation', 'CIVIL', 'Sector 1', '2026-08-01', '2026-08-10', 100.0, 'm', 0.0)
        """
    )
    # Act 2: 50% approved actual -> IN PROGRESS
    db.execute(
        """
        INSERT INTO schedule_activities (schedule_id, activity_id, activity_name, discipline, location, planned_start, planned_finish, planned_quantity, uom, baseline_pct_complete)
        VALUES ('SCHED-TEST', 'ACT-IN-PROGRESS', 'Field Welding', 'PIPING', 'Sector 2', '2026-08-02', '2026-08-12', 50.0, 'joints', 20.0)
        """
    )
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, decision_id, event_id, schedule_id, activity_id, actual_pct_complete)
        VALUES ('ACTUAL-1', 'DEC-1', 'EV-1', 'SCHED-TEST', 'ACT-IN-PROGRESS', 50.0)
        """
    )
    # Act 3: 100% approved actual -> COMPLETED
    db.execute(
        """
        INSERT INTO schedule_activities (schedule_id, activity_id, activity_name, discipline, location, planned_start, planned_finish, planned_quantity, uom, baseline_pct_complete)
        VALUES ('SCHED-TEST', 'ACT-COMPLETED', 'Loop Testing', 'ELECTRICAL', 'Sector 3', '2026-08-03', '2026-08-15', 10.0, 'loops', 100.0)
        """
    )
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, decision_id, event_id, schedule_id, activity_id, actual_pct_complete)
        VALUES ('ACTUAL-2', 'DEC-2', 'EV-2', 'SCHED-TEST', 'ACT-COMPLETED', 100.0)
        """
    )

    from backend.routers.activities import list_activities
    from contextlib import contextmanager

    @contextmanager
    def mock_get_conn():
        yield db

    monkeypatch.setattr("backend.routers.activities.get_connection", mock_get_conn)

    client = TestClient(app)
    supervisor = UserProfile(id="22222222-2222-2222-2222-222222222222", full_name="Bob", role="SUPERVISOR")
    app.dependency_overrides[get_current_user] = lambda: supervisor
    try:
        resp = client.get("/api/v1/activities?schedule_id=SCHED-TEST")
        assert resp.status_code == 200
        acts = {a["activity_id"]: a for a in resp.json()["activities"]}
        
        # ACT-NOT-STARTED: 0% -> NOT STARTED
        assert acts["ACT-NOT-STARTED"]["approved_pct"] == 0.0
        assert acts["ACT-NOT-STARTED"]["status"] == "NOT STARTED"
        assert acts["ACT-NOT-STARTED"]["activity_name"] == "Trench Excavation"
        assert acts["ACT-NOT-STARTED"]["discipline"] == "CIVIL"

        # ACT-IN-PROGRESS: 50% -> IN PROGRESS
        assert acts["ACT-IN-PROGRESS"]["approved_pct"] == 50.0
        assert acts["ACT-IN-PROGRESS"]["status"] == "IN PROGRESS"
        assert acts["ACT-IN-PROGRESS"]["activity_name"] == "Field Welding"
        assert acts["ACT-IN-PROGRESS"]["discipline"] == "PIPING"

        # ACT-COMPLETED: 100% -> COMPLETED
        assert acts["ACT-COMPLETED"]["approved_pct"] == 100.0
        assert acts["ACT-COMPLETED"]["status"] == "COMPLETED"
        assert acts["ACT-COMPLETED"]["activity_name"] == "Loop Testing"
        assert acts["ACT-COMPLETED"]["discipline"] == "ELECTRICAL"
    finally:
        app.dependency_overrides.clear()


def test_activity_detail_metadata_and_per_event_decision(monkeypatch):
    db = create_full_test_db()
    db.execute(
        """
        INSERT INTO schedule_activities (schedule_id, activity_id, activity_name, discipline, location, planned_start, planned_finish, planned_quantity, uom, baseline_pct_complete)
        VALUES ('SCHED-TEST', 'CIV-PS3-TR-0180', 'Utility Trench Excavation CH 0+180 to CH 0+220', 'CIVIL', 'Pump Station 3', '2026-08-14', '2026-08-14', 40.0, 'm', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, decision_id, event_id, schedule_id, activity_id, actual_pct_complete)
        VALUES ('ACTUAL-TR', 'DEC-TR-2', 'EV-TR-2', 'SCHED-TEST', 'CIV-PS3-TR-0180', 70.0)
        """
    )

    # Event 1: 40% claimed, approved 40%
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, claimed_pct, created_at)
        VALUES ('EV-TR-1', 'SCHED-TEST', '2026-08-14', 'Started trenching 40%', 'TYPED_TEXT', 'CIV-PS3-TR-0180', 40.0, '2026-08-14 09:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, planner_id, justification, decided_at)
        VALUES ('DEC-TR-1', 'EV-TR-1', 'CIV-PS3-TR-0180', 'APPROVE', 40.0, 'P-01', 'Approved 40% excavation', '2026-08-14 11:00:00')
        """
    )

    # Event 2: 70% cumulative claimed, approved 70%
    db.execute(
        """
        INSERT INTO execution_events (event_id, schedule_id, event_date, raw_claim_text, input_channel, matched_activity_id, claimed_pct, created_at)
        VALUES ('EV-TR-2', 'SCHED-TEST', '2026-08-15', 'Trenching now at 70%', 'VOICE', 'CIV-PS3-TR-0180', 70.0, '2026-08-15 09:00:00')
        """
    )
    db.execute(
        """
        INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_pct, planner_id, justification, decided_at)
        VALUES ('DEC-TR-2', 'EV-TR-2', 'CIV-PS3-TR-0180', 'APPROVE', 70.0, 'P-01', 'Approved cumulative 70%', '2026-08-15 12:00:00')
        """
    )

    from contextlib import contextmanager

    @contextmanager
    def mock_get_conn():
        yield db

    monkeypatch.setattr("backend.routers.activities.get_connection", mock_get_conn)

    client = TestClient(app)
    supervisor = UserProfile(id="22222222-2222-2222-2222-222222222222", full_name="Bob", role="SUPERVISOR")
    app.dependency_overrides[get_current_user] = lambda: supervisor
    try:
        resp = client.get("/api/v1/activities/CIV-PS3-TR-0180/history")
        assert resp.status_code == 200
        data = resp.json()

        # Metadata checks
        assert "activity" in data
        act_meta = data["activity"]
        assert act_meta["activity_id"] == "CIV-PS3-TR-0180"
        assert act_meta["activity_name"] == "Utility Trench Excavation CH 0+180 to CH 0+220"
        assert act_meta["discipline"] == "CIVIL"
        assert act_meta["approved_pct"] == 70.0
        assert act_meta["status"] == "IN PROGRESS"

        # Events check: each event has its own supervisor decision!
        events = [t for t in data["timeline"] if t["type"] == "execution_event"]
        assert len(events) == 2

        # Event 1
        assert events[0]["event_id"] == "EV-TR-1"
        assert events[0]["claimed_pct"] == 40.0
        assert events[0]["input_channel"] == "TYPED_TEXT"
        assert events[0]["supervisor_action"] == "APPROVE"
        assert events[0]["approved_pct"] == 40.0
        assert events[0]["justification"] == "Approved 40% excavation"

        # Event 2
        assert events[1]["event_id"] == "EV-TR-2"
        assert events[1]["claimed_pct"] == 70.0
        assert events[1]["input_channel"] == "VOICE"
        assert events[1]["supervisor_action"] == "APPROVE"
        assert events[1]["approved_pct"] == 70.0
        assert events[1]["justification"] == "Approved cumulative 70%"
    finally:
        app.dependency_overrides.clear()
