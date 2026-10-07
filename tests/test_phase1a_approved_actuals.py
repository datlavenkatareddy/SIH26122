import re
import sqlite3
from unittest.mock import patch

import pytest

from backend.shared.actuals import (
    get_approved_actual,
    get_approved_pct,
    upsert_approved_actual,
)


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


# ==============================================================================
# ACT-01: START_DATE update preserves existing FINISH_DATE
# ==============================================================================
def test_act_01_start_date_preserves_finish_date():
    """
    ACT-01: Updating actual_start must preserve existing actual_finish.
    It must not automatically set actual_pct_complete.
    """
    db = create_test_db()
    sch_id = "SCH-ACT-01"
    act_id = "ACT-PIPE-100"

    # Step 1: Establish existing approved_actuals row with both start and finish
    db.execute(
        """
        INSERT INTO approved_actuals (
            actual_id, decision_id, event_id, schedule_id, activity_id,
            actual_start, actual_finish, actual_pct_complete, actual_quantity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("ACT-01-INIT", "DEC-INIT", "EV-INIT", sch_id, act_id, "2026-09-01", "2026-09-10", None, None),
    )
    db.commit()

    # Step 2: New approval with updated START_DATE
    res = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-START-NEW",
        decision_id="DEC-START-NEW",
        action="APPROVE",
        event_type="ACTUAL_START",
        actual_start="2026-09-03",
        conn=db,
    )

    assert res is not None
    assert res["actual_start"] == "2026-09-03", "actual_start was not updated to 2026-09-03"
    assert res["actual_finish"] == "2026-09-10", "existing actual_finish was erased by START_DATE update"
    assert res["actual_pct_complete"] is None, "actual_pct_complete was wrongly populated automatically"

    # Direct database verification
    row = db.execute(
        "SELECT * FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()
    assert row["actual_start"] == "2026-09-03"
    assert row["actual_finish"] == "2026-09-10"
    assert row["actual_pct_complete"] is None


# ==============================================================================
# ACT-02: FINISH_DATE update preserves existing START_DATE
# ==============================================================================
def test_act_02_finish_date_preserves_start_date():
    """
    ACT-02: Updating actual_finish must preserve existing actual_start.
    It must not automatically set actual_pct_complete = 100, and must not
    auto-populate actual_start if actual_start was NULL.
    """
    db = create_test_db()
    sch_id = "SCH-ACT-02"
    act_id = "ACT-CIVIL-200"

    # Scenario A: Existing start date, update finish date
    db.execute(
        """
        INSERT INTO approved_actuals (
            actual_id, decision_id, event_id, schedule_id, activity_id,
            actual_start, actual_finish, actual_pct_complete, actual_quantity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("ACT-02-INIT", "DEC-INIT", "EV-INIT", sch_id, act_id, "2026-09-01", None, None, None),
    )
    db.commit()

    res = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-FINISH",
        decision_id="DEC-FINISH",
        action="APPROVE",
        event_type="ACTUAL_FINISH",
        actual_finish="2026-09-10",
        conn=db,
    )

    assert res is not None
    assert res["actual_start"] == "2026-09-01", "existing actual_start was erased by FINISH_DATE update"
    assert res["actual_finish"] == "2026-09-10", "actual_finish was not updated to 2026-09-10"
    assert res["actual_pct_complete"] is None, "actual_pct_complete was wrongly set to 100 automatically"

    # Scenario B: Target activity has NULL actual_start; finish update arrives
    act_id_nostart = "ACT-ELEC-201"
    res_b = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id_nostart,
        event_id="EV-FINISH-ONLY",
        decision_id="DEC-FINISH-ONLY",
        action="APPROVE",
        event_type="ACTUAL_FINISH",
        actual_finish="2026-09-15",
        conn=db,
    )
    assert res_b["actual_start"] is None, "actual_start was wrongly auto-populated from finish date"
    assert res_b["actual_finish"] == "2026-09-15"
    assert res_b["actual_pct_complete"] is None, "actual_pct_complete was wrongly set to 100 on finish"


# ==============================================================================
# ACT-03: CUMULATIVE_PCT replaces previous percentage rather than accumulating
# ==============================================================================
def test_act_03_cumulative_pct_replaces_not_accumulates():
    """
    ACT-03: For CUMULATIVE_PCT, actual_pct_complete must be replaced, not added.
    Example: 75% followed by 80% must become 80%, not 155%.
    Must also respect 0 <= actual_pct_complete <= 100 clamping.
    """
    db = create_test_db()
    sch_id = "SCH-ACT-03"
    act_id = "ACT-PUMP-300"

    # Initial approval at 75%
    res1 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-PCT-1",
        decision_id="DEC-PCT-1",
        action="APPROVE",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=75.0,
        conn=db,
    )
    assert res1["actual_pct_complete"] == 75.0

    # Second approval at 80%
    res2 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-PCT-2",
        decision_id="DEC-PCT-2",
        action="APPROVE",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=80.0,
        conn=db,
    )
    # Must be 80.0, NOT 155.0
    assert res2["actual_pct_complete"] == 80.0
    assert res2["actual_pct_complete"] != 155.0

    # Verify boundary clamping
    res_overflow = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-PCT-3",
        decision_id="DEC-PCT-3",
        action="APPROVE",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=120.0,
        conn=db,
    )
    assert res_overflow["actual_pct_complete"] == 100.0

    res_underflow = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-PCT-4",
        decision_id="DEC-PCT-4",
        action="APPROVE",
        claim_mode="CUMULATIVE_PCT",
        approved_pct=-10.0,
        conn=db,
    )
    assert res_underflow["actual_pct_complete"] == 0.0


# ==============================================================================
# ACT-04: INCREMENTAL_QUANTITY recalculates from source rows rather than +=
# ==============================================================================
def test_act_04_incremental_quantity_recalculates_not_adds():
    """
    ACT-04: Multi-event scenario where += produces an incorrect number:
      Event A: claimed = 10, latest APPROVE = no override (use claimed_quantity = 10)
      Event B: claimed = 20, latest EDIT approved_qty = 12 (use approved_qty = 12)
      Event C: claimed = 30, latest REJECT (excluded = 0)
      Event D: claimed = 40, latest HOLD (excluded = 0)
    Expected total: 10 + 12 = 22.
    An additive += logic would produce 100 (10 + 20 + 30 + 40) or 72.
    """
    db = create_test_db()
    sch_id = "SCH-ACT-04"
    act_id = "ACT-TRENCH-400"

    # Event A: claimed 10, approved with no override
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-A", sch_id, "INCREMENTAL_QUANTITY", 10.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-A", "EV-A", act_id, "APPROVE", "2026-08-01 10:00:00"),
    )

    # Event B: claimed 20, edited with approved_qty = 12
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-B", sch_id, "INCREMENTAL_QUANTITY", 20.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_qty, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-B", "EV-B", act_id, "EDIT", 12.0, "2026-08-02 10:00:00"),
    )

    # Event C: claimed 30, rejected
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-C", sch_id, "INCREMENTAL_QUANTITY", 30.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-C", "EV-C", act_id, "REJECT", "2026-08-03 10:00:00"),
    )

    # Event D: claimed 40, held
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-D", sch_id, "INCREMENTAL_QUANTITY", 40.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-D", "EV-D", act_id, "HOLD", "2026-08-04 10:00:00"),
    )

    # Trigger recalculation via upsert on the latest valid approved decision (DEC-B)
    res = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-B",
        decision_id="DEC-B",
        action="EDIT",
        claim_mode="INCREMENTAL_QUANTITY",
        approved_qty=12.0,
        conn=db,
    )

    assert res is not None
    assert res["actual_quantity"] == 22.0, f"Expected 22.0 (10 + 12), got {res['actual_quantity']}"

    # Verify directly from database
    row = db.execute(
        "SELECT actual_quantity FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()
    assert row["actual_quantity"] == 22.0


# ==============================================================================
# ACT-05: REJECTED/HOLD decisions are excluded from approved quantity
# ==============================================================================
def test_act_05_rejected_and_hold_excluded():
    """
    ACT-05: REJECTED and HOLD decisions must not contribute to approved quantity
    and must not write to approved_actuals.
    """
    db = create_test_db()
    sch_id = "SCH-ACT-05"
    act_id = "ACT-GATE-500"

    # Event 1: REJECT
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-REJ", sch_id, "INCREMENTAL_QUANTITY", 50.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-REJ", "EV-REJ", act_id, "REJECT", "2026-08-01 10:00:00"),
    )
    res_rej = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-REJ",
        decision_id="DEC-REJ",
        action="REJECT",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    assert res_rej is None, "REJECT must return None and not write approved_actuals"

    # Event 2: HOLD
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-HLD", sch_id, "INCREMENTAL_QUANTITY", 40.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-HLD", "EV-HLD", act_id, "HOLD", "2026-08-02 10:00:00"),
    )
    res_hld = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-HLD",
        decision_id="DEC-HLD",
        action="HOLD",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    assert res_hld is None, "HOLD must return None and not write approved_actuals"

    # Verify no row created in approved_actuals
    count = db.execute(
        "SELECT COUNT(*) AS cnt FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()["cnt"]
    assert count == 0


# ==============================================================================
# ACT-06: Only the latest decision per event_id contributes
# ==============================================================================
def test_act_06_latest_decision_per_event_contributes():
    """
    ACT-06: For an event with multiple historical decisions, only the single latest
    decision contributes to the total.
    Event E1: initial APPROVE = 10, later EDIT = 7 -> contribution = 7 (not 17).
    Event E2: initial APPROVE = 15, later EDIT = 12, latest REJECT -> contribution = 0.
    Total: 7 + 0 = 7.
    """
    db = create_test_db()
    sch_id = "SCH-ACT-06"
    act_id = "ACT-WELD-600"

    # Event E1: claimed 10
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-E1", sch_id, "INCREMENTAL_QUANTITY", 10.0),
    )
    # E1 Decision 1: APPROVE 10
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_qty, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-E1-1", "EV-E1", act_id, "APPROVE", 10.0, "2026-08-01 10:00:00"),
    )
    # E1 Decision 2 (LATER): EDIT 7
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_qty, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-E1-2", "EV-E1", act_id, "EDIT", 7.0, "2026-08-02 10:00:00"),
    )

    # Event E2: claimed 15
    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-E2", sch_id, "INCREMENTAL_QUANTITY", 15.0),
    )
    # E2 Decision 1: APPROVE 15
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_qty, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-E2-1", "EV-E2", act_id, "APPROVE", 15.0, "2026-08-01 11:00:00"),
    )
    # E2 Decision 2: EDIT 12
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_qty, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-E2-2", "EV-E2", act_id, "EDIT", 12.0, "2026-08-02 11:00:00"),
    )
    # E2 Decision 3 (LATEST): REJECT
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_qty, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-E2-3", "EV-E2", act_id, "REJECT", None, "2026-08-03 11:00:00"),
    )

    # Recalculate approved actuals
    res = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-E1",
        decision_id="DEC-E1-2",
        action="EDIT",
        claim_mode="INCREMENTAL_QUANTITY",
        approved_qty=7.0,
        conn=db,
    )

    assert res is not None
    # E1 contributes 7 (not 10 + 7); E2 contributes 0 (latest is REJECT) -> Total = 7.0
    assert res["actual_quantity"] == 7.0, f"Expected 7.0, got {res['actual_quantity']}"

    row = db.execute(
        "SELECT actual_quantity FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()
    assert row["actual_quantity"] == 7.0


# ==============================================================================
# ACT-07: EDIT approved_qty overrides execution_events.claimed_quantity
# ==============================================================================
def test_act_07_edit_approved_qty_overrides_claimed_quantity():
    """
    ACT-07: If an EDIT decision contains approved_qty, approved_qty overrides claimed_quantity.
    Example: claimed = 100, approved_qty = 65 -> approved quantity = 65 (not 100).
    """
    db = create_test_db()
    sch_id = "SCH-ACT-07"
    act_id = "ACT-CABLE-700"

    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-CABLE", sch_id, "INCREMENTAL_QUANTITY", 100.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, approved_qty, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("DEC-CABLE-EDIT", "EV-CABLE", act_id, "EDIT", 65.0, "2026-08-01 10:00:00"),
    )

    res = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-CABLE",
        decision_id="DEC-CABLE-EDIT",
        action="EDIT",
        claim_mode="INCREMENTAL_QUANTITY",
        approved_qty=65.0,
        conn=db,
    )

    assert res is not None
    assert res["actual_quantity"] == 65.0, f"Expected 65.0, got {res['actual_quantity']}"
    assert res["actual_quantity"] != 100.0

    row = db.execute(
        "SELECT actual_quantity FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchone()
    assert row["actual_quantity"] == 65.0


# ==============================================================================
# ACT-08: Repeated invocation is idempotent and does not double-count
# ==============================================================================
def test_act_08_repeated_invocation_is_idempotent():
    """
    ACT-08: Calling actuals persistence/recalculation multiple times must NOT
    double-count quantities.
    Example: Authoritative quantity = 20.
    First call -> 20. Second call -> 20 (not 40).
    Exactly 1 row per (schedule_id, activity_id).
    """
    db = create_test_db()
    sch_id = "SCH-ACT-08"
    act_id = "ACT-FOUND-800"

    db.execute(
        "INSERT INTO execution_events (event_id, schedule_id, claim_mode, claimed_quantity) VALUES (?, ?, ?, ?)",
        ("EV-IDEMP", sch_id, "INCREMENTAL_QUANTITY", 20.0),
    )
    db.execute(
        "INSERT INTO planner_decisions (decision_id, event_id, selected_activity_id, action, decided_at) VALUES (?, ?, ?, ?, ?)",
        ("DEC-IDEMP", "EV-IDEMP", act_id, "APPROVE", "2026-08-01 10:00:00"),
    )

    # First invocation
    res1 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-IDEMP",
        decision_id="DEC-IDEMP",
        action="APPROVE",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    assert res1["actual_quantity"] == 20.0

    # Second identical invocation
    res2 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-IDEMP",
        decision_id="DEC-IDEMP",
        action="APPROVE",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    assert res2["actual_quantity"] == 20.0, f"Expected 20.0 on repeat, got {res2['actual_quantity']} (double counting!)"

    # Third invocation
    res3 = upsert_approved_actual(
        schedule_id=sch_id,
        activity_id=act_id,
        event_id="EV-IDEMP",
        decision_id="DEC-IDEMP",
        action="APPROVE",
        claim_mode="INCREMENTAL_QUANTITY",
        conn=db,
    )
    assert res3["actual_quantity"] == 20.0

    # Exactly one row exists in approved_actuals
    rows = db.execute(
        "SELECT * FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
        (sch_id, act_id),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["actual_quantity"] == 20.0


# ==============================================================================
# ACT-09: Post-commit CSV/P6 failure does not remove already committed actual
# ==============================================================================
def test_act_09_post_commit_adapter_failure_does_not_rollback_actual():
    """
    ACT-09: If an export adapter or P6 push throws an exception post-commit,
    the approved_actuals row must remain committed and uncorrupted.
    """
    db = create_test_db()
    sch_id = "SCH-ACT-09"
    act_id = "ACT-ISO-900"

    with patch("backend.routers.export.trigger_auto_export", side_effect=RuntimeError("Simulated CSV disk failure")), \
         patch("backend.shared.p6.trigger_p6_actual_push", side_effect=ConnectionError("Simulated P6 network outage")):

        res = upsert_approved_actual(
            schedule_id=sch_id,
            activity_id=act_id,
            event_id="EV-ADAPT-FAIL",
            decision_id="DEC-ADAPT-FAIL",
            action="APPROVE",
            claim_mode="CUMULATIVE_PCT",
            approved_pct=85.0,
            actual_start="2026-09-01",
            conn=db,
        )

        # Function returns successfully despite post-commit hook failures
        assert res is not None
        assert res["actual_pct_complete"] == 85.0
        assert res["actual_start"] == "2026-09-01"

        # Direct database query verifies the row is committed and intact
        row = db.execute(
            "SELECT * FROM approved_actuals WHERE schedule_id = ? AND activity_id = ?",
            (sch_id, act_id),
        ).fetchone()
        assert row is not None
        assert row["actual_pct_complete"] == 85.0
        assert row["actual_start"] == "2026-09-01"
