"""
Phase 2 A1 Core Constraint Engine & Impact Preview Tests.

Covers:
- IMP-01: FS relationship
- IMP-02: SS relationship
- IMP-03: FF relationship
- IMP-04: SF relationship
- IMP-05: positive lag
- IMP-06: negative lead
- IMP-07: mixed FS + FF predecessors
- IMP-08: controlling predecessor selection (non-target controlling)
- IMP-09: deterministic tie-break
- IMP-10: known float absorbs delay
- IMP-11: delay exceeds float
- IMP-12: NULL float produces float_status=UNKNOWN, net_delay_days=null
- IMP-13: NOT_STARTED execution state
- IMP-14: IN_PROGRESS execution state
- IMP-15: COMPLETED execution state (affected successor completed -> 0 shift; target completed still propagates)
- IMP-16: missing duration produces explicit uncertainty
- IMP-17: batched query / endpoint behavior
"""

import sqlite3
from datetime import date
from typing import Any

import pytest

from backend.routers.schedule import query_impact_preview
from backend.shared.impact import (
    ConstraintEvaluation,
    evaluate_constraint,
    evaluate_successor_impact,
    select_controlling_constraint,
)
from backend.shared.schemas import ExecutionState


class SQLitePsycopgAdapter:
    """Lightweight DB adapter for deterministic in-memory tests."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def execute(self, query: str, params=None):
        clean_q = query.replace("%s", "?")
        cur = self.conn.cursor()
        if params is not None:
            cur.execute(clean_q, params)
        else:
            cur.execute(clean_q)
        return cur

    def commit(self):
        self.conn.commit()


def create_test_db() -> SQLitePsycopgAdapter:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

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
            planned_finish TEXT,
            planned_quantity REAL,
            uom TEXT,
            baseline_pct_complete REAL DEFAULT 0.0,
            total_float REAL,
            is_critical BOOLEAN,
            PRIMARY KEY (schedule_id, activity_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE schedule_dependencies (
            dependency_id TEXT PRIMARY KEY,
            schedule_id TEXT NOT NULL,
            predecessor_activity_id TEXT NOT NULL,
            successor_activity_id TEXT NOT NULL,
            relationship_type TEXT DEFAULT 'FS',
            lag_days REAL DEFAULT 0.0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE approved_actuals (
            actual_id TEXT PRIMARY KEY,
            decision_id TEXT,
            event_id TEXT,
            schedule_id TEXT,
            activity_id TEXT,
            actual_start TEXT,
            actual_finish TEXT,
            actual_pct_complete REAL,
            actual_quantity REAL,
            exported_at TEXT,
            created_at TEXT
        )
        """
    )
    return SQLitePsycopgAdapter(conn)


# ==============================================================================
# IMP-01: FS Relationship
# ==============================================================================

def test_imp_01_fs_relationship():
    c = evaluate_constraint(
        predecessor_id="A",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 10),
        successor_id="B",
        successor_planned_start=date(2026, 8, 10),
        successor_planned_finish=date(2026, 8, 15),
        relationship_type="FS",
        lag_days=0.0,
        is_target_predecessor=True,
        simulated_delay_days=5,
    )
    assert c.constraint_dimension == "START"
    assert c.required_successor_start == date(2026, 8, 15)
    assert c.gross_delay_days == 5
    assert not c.uncertainty


# ==============================================================================
# IMP-02: SS Relationship
# ==============================================================================

def test_imp_02_ss_relationship():
    c = evaluate_constraint(
        predecessor_id="A",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 10),
        successor_id="B",
        successor_planned_start=date(2026, 8, 1),
        successor_planned_finish=date(2026, 8, 8),
        relationship_type="SS",
        lag_days=0.0,
        is_target_predecessor=True,
        simulated_delay_days=3,
    )
    assert c.constraint_dimension == "START"
    assert c.required_successor_start == date(2026, 8, 4)
    assert c.gross_delay_days == 3
    assert not c.uncertainty


# ==============================================================================
# IMP-03: FF Relationship
# ==============================================================================

def test_imp_03_ff_relationship():
    # Successor duration = 2026-08-10 - 2026-08-05 = 5 days
    c = evaluate_constraint(
        predecessor_id="A",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 10),
        successor_id="B",
        successor_planned_start=date(2026, 8, 5),
        successor_planned_finish=date(2026, 8, 10),
        relationship_type="FF",
        lag_days=0.0,
        is_target_predecessor=True,
        simulated_delay_days=4,
    )
    assert c.constraint_dimension == "FINISH"
    assert c.required_successor_finish == date(2026, 8, 14)
    # Required start = 2026-08-14 - 5 days = 2026-08-09
    assert c.required_successor_start == date(2026, 8, 9)
    assert c.gross_delay_days == 4
    assert not c.uncertainty


# ==============================================================================
# IMP-04: SF Relationship
# ==============================================================================

def test_imp_04_sf_relationship():
    # Successor duration = 2026-08-01 - 2026-07-25 = 7 days
    c = evaluate_constraint(
        predecessor_id="A",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 10),
        successor_id="B",
        successor_planned_start=date(2026, 7, 25),
        successor_planned_finish=date(2026, 8, 1),
        relationship_type="SF",
        lag_days=0.0,
        is_target_predecessor=True,
        simulated_delay_days=5,
    )
    assert c.constraint_dimension == "FINISH"
    # A simulated start = 2026-08-06
    assert c.required_successor_finish == date(2026, 8, 6)
    # Required start = 2026-08-06 - 7 days = 2026-07-30
    assert c.required_successor_start == date(2026, 7, 30)
    assert c.gross_delay_days == 5
    assert not c.uncertainty


# ==============================================================================
# IMP-05: Positive Lag
# ==============================================================================

def test_imp_05_positive_lag():
    c = evaluate_constraint(
        predecessor_id="A",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 10),
        successor_id="B",
        successor_planned_start=date(2026, 8, 10),
        successor_planned_finish=date(2026, 8, 15),
        relationship_type="FS",
        lag_days=2.0,
        is_target_predecessor=True,
        simulated_delay_days=3,
    )
    # Finish 2026-08-10 + 3 delay + 2 lag = 2026-08-15
    assert c.required_successor_start == date(2026, 8, 15)
    assert c.gross_delay_days == 5


# ==============================================================================
# IMP-06: Negative Lead
# ==============================================================================

def test_imp_06_negative_lead():
    c = evaluate_constraint(
        predecessor_id="A",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 10),
        successor_id="B",
        successor_planned_start=date(2026, 8, 10),
        successor_planned_finish=date(2026, 8, 15),
        relationship_type="FS",
        lag_days=-2.0,
        is_target_predecessor=True,
        simulated_delay_days=4,
    )
    # Finish 2026-08-10 + 4 delay - 2 lead = 2026-08-12
    assert c.required_successor_start == date(2026, 8, 12)
    assert c.gross_delay_days == 2


# ==============================================================================
# IMP-07: Mixed FS + FF Predecessors Reconciled
# ==============================================================================

def test_imp_07_mixed_fs_ff_reconciled():
    # Successor C: planned_start=2026-08-10, planned_finish=2026-08-20 (dur=10)
    # Pred A (target): FS, finish=2026-08-10, delay=3 -> finish=2026-08-13 -> req_start=2026-08-13
    cA = evaluate_constraint(
        predecessor_id="A",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 10),
        successor_id="C",
        successor_planned_start=date(2026, 8, 10),
        successor_planned_finish=date(2026, 8, 20),
        relationship_type="FS",
        lag_days=0.0,
        is_target_predecessor=True,
        simulated_delay_days=3,
    )
    # Pred B (non-target): FF, finish=2026-08-12, no delay -> req_finish=2026-08-12 -> req_start=2026-08-02
    cB = evaluate_constraint(
        predecessor_id="B",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 12),
        successor_id="C",
        successor_planned_start=date(2026, 8, 10),
        successor_planned_finish=date(2026, 8, 20),
        relationship_type="FF",
        lag_days=0.0,
        is_target_predecessor=False,
    )
    controlling = select_controlling_constraint([cA, cB])
    assert controlling is not None
    assert controlling.predecessor_activity_id == "A"
    assert controlling.required_successor_start == date(2026, 8, 13)


# ==============================================================================
# IMP-08: Controlling Predecessor Selection (Non-Target Controlling)
# ==============================================================================

def test_imp_08_non_target_controlling():
    # Target A delays by 2 days: finish becomes 2026-08-12
    cA = evaluate_constraint(
        predecessor_id="A",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 10),
        successor_id="C",
        successor_planned_start=date(2026, 8, 10),
        successor_planned_finish=date(2026, 8, 20),
        relationship_type="FS",
        lag_days=0.0,
        is_target_predecessor=True,
        simulated_delay_days=2,
    )
    # Pred B is already later: finish 2026-08-15
    cB = evaluate_constraint(
        predecessor_id="B",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 15),
        successor_id="C",
        successor_planned_start=date(2026, 8, 10),
        successor_planned_finish=date(2026, 8, 20),
        relationship_type="FS",
        lag_days=0.0,
        is_target_predecessor=False,
    )
    controlling = select_controlling_constraint([cA, cB])
    assert controlling is not None
    assert controlling.predecessor_activity_id == "B"
    assert controlling.required_successor_start == date(2026, 8, 15)

    res = evaluate_successor_impact(
        successor={"activity_id": "C", "planned_start": "2026-08-10", "planned_finish": "2026-08-20", "total_float": 5.0},
        execution_state="NOT_STARTED",
        constraints=[cA, cB],
        target_activity_id="A",
    )
    assert res["controlling_predecessor"] == "B"


# ==============================================================================
# IMP-09: Deterministic Tie-Break
# ==============================================================================

def test_imp_09_deterministic_tie_break():
    # Case A: Same required start, different gross delays -> larger gross delay wins
    c1 = ConstraintEvaluation(
        predecessor_activity_id="P1",
        successor_activity_id="S",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 15),
        gross_delay_days=5,
    )
    c2 = ConstraintEvaluation(
        predecessor_activity_id="P2",
        successor_activity_id="S",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 15),
        gross_delay_days=3,
    )
    controlling = select_controlling_constraint([c1, c2])
    assert controlling is not None
    assert controlling.predecessor_activity_id == "P1"

    # Case B: Same required start, same gross delay -> activity_id ascending wins
    c_b = ConstraintEvaluation(
        predecessor_activity_id="B_ACT",
        successor_activity_id="S",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 15),
        gross_delay_days=4,
    )
    c_a = ConstraintEvaluation(
        predecessor_activity_id="A_ACT",
        successor_activity_id="S",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 15),
        gross_delay_days=4,
    )
    controlling_ab = select_controlling_constraint([c_b, c_a])
    assert controlling_ab is not None
    assert controlling_ab.predecessor_activity_id == "A_ACT"


# ==============================================================================
# IMP-10: Known Float Absorbs Delay Completely
# ==============================================================================

def test_imp_10_known_float_absorbs_delay():
    c = ConstraintEvaluation(
        predecessor_activity_id="A",
        successor_activity_id="B",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 13),
        gross_delay_days=3,
    )
    res = evaluate_successor_impact(
        successor={"activity_id": "B", "planned_start": "2026-08-10", "planned_finish": "2026-08-15", "total_float": 5.0},
        execution_state="NOT_STARTED",
        constraints=[c],
        target_activity_id="A",
    )
    assert res["gross_delay_days"] == 3
    assert res["float_status"] == "KNOWN"
    assert res["absorbed_delay_days"] == 3
    assert res["net_delay_days"] == 0
    assert res["classification"] == "ABSORBED_BY_FLOAT"


# ==============================================================================
# IMP-11: Delay Exceeds Float
# ==============================================================================

def test_imp_11_delay_exceeds_float():
    c = ConstraintEvaluation(
        predecessor_activity_id="A",
        successor_activity_id="B",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 16),
        gross_delay_days=6,
    )
    res = evaluate_successor_impact(
        successor={"activity_id": "B", "planned_start": "2026-08-10", "planned_finish": "2026-08-15", "total_float": 2.0},
        execution_state="NOT_STARTED",
        constraints=[c],
        target_activity_id="A",
    )
    assert res["gross_delay_days"] == 6
    assert res["float_status"] == "KNOWN"
    assert res["absorbed_delay_days"] == 2
    assert res["net_delay_days"] == 4
    assert res["classification"] == "CRITICAL_PATH_SLIP"


# ==============================================================================
# IMP-12: NULL Float Produces UNKNOWN and None Net Delay
# ==============================================================================

def test_imp_12_null_float_handling():
    c = ConstraintEvaluation(
        predecessor_activity_id="A",
        successor_activity_id="B",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 14),
        gross_delay_days=4,
    )
    res = evaluate_successor_impact(
        successor={"activity_id": "B", "planned_start": "2026-08-10", "planned_finish": "2026-08-15", "total_float": None},
        execution_state="NOT_STARTED",
        constraints=[c],
        target_activity_id="A",
    )
    assert res["gross_delay_days"] == 4
    assert res["total_float"] is None
    assert res["float_status"] == "UNKNOWN"
    assert res["absorbed_delay_days"] is None
    assert res["net_delay_days"] is None
    assert res["uncertainty"] is True
    # Explicitly verify no silent zero coercion
    assert res["net_delay_days"] != 0
    assert res["absorbed_delay_days"] != 0


# ==============================================================================
# IMP-13: NOT_STARTED Execution State
# ==============================================================================

def test_imp_13_not_started_state():
    c = ConstraintEvaluation(
        predecessor_activity_id="A",
        successor_activity_id="B",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 13),
        gross_delay_days=3,
    )
    res = evaluate_successor_impact(
        successor={"activity_id": "B", "planned_start": "2026-08-10", "planned_finish": "2026-08-15", "total_float": 0.0},
        execution_state=ExecutionState.NOT_STARTED.value,
        constraints=[c],
        target_activity_id="A",
    )
    assert res["execution_state"] == "NOT_STARTED"
    assert res["gross_delay_days"] == 3
    assert res["net_delay_days"] == 3


# ==============================================================================
# IMP-14: IN_PROGRESS Execution State
# ==============================================================================

def test_imp_14_in_progress_state():
    c = ConstraintEvaluation(
        predecessor_activity_id="A",
        successor_activity_id="B",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 13),
        gross_delay_days=3,
    )
    res = evaluate_successor_impact(
        successor={"activity_id": "B", "planned_start": "2026-08-10", "planned_finish": "2026-08-15", "total_float": 5.0},
        execution_state=ExecutionState.IN_PROGRESS.value,
        constraints=[c],
        target_activity_id="A",
    )
    assert res["execution_state"] == "IN_PROGRESS"
    assert res["gross_delay_days"] == 3
    assert res["float_status"] == "KNOWN"


# ==============================================================================
# IMP-15: COMPLETED Execution State
# ==============================================================================

def test_imp_15_completed_state():
    # Rule: If the affected successor is already COMPLETED, impact is 0 and it is not shifted.
    c = ConstraintEvaluation(
        predecessor_activity_id="A",
        successor_activity_id="B",
        relationship_type="FS",
        lag_days=0.0,
        constraint_dimension="START",
        required_successor_start=date(2026, 8, 15),
        gross_delay_days=5,
    )
    res = evaluate_successor_impact(
        successor={"activity_id": "B", "planned_start": "2026-08-10", "planned_finish": "2026-08-15", "total_float": 0.0},
        execution_state=ExecutionState.COMPLETED.value,
        constraints=[c],
        target_activity_id="A",
    )
    assert res["execution_state"] == "COMPLETED"
    assert res["gross_delay_days"] == 0
    assert res["net_delay_days"] == 0
    assert res["shifted_earliest_start"] == "2026-08-10"
    assert res["classification"] == "ALREADY_COMPLETED"

    # Target A COMPLETED must still propagate to evaluate downstream NOT_STARTED successor B
    db = create_test_db()
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish)
        VALUES ('TARGET_COMP', 'SCHED-01', 'Done Task', 'CIVIL', 'Site A', '2026-08-01', '2026-08-10'),
               ('SUCC_UNSTARTED', 'SCHED-01', 'Future Task', 'CIVIL', 'Site A', '2026-08-10', '2026-08-15')
        """
    )
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, schedule_id, activity_id, actual_pct_complete)
        VALUES ('ACT-01', 'SCHED-01', 'TARGET_COMP', 100.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-01', 'SCHED-01', 'TARGET_COMP', 'SUCC_UNSTARTED', 'FS')
        """
    )
    result = query_impact_preview("TARGET_COMP", delay_days=5, conn=db)
    assert len(result["impacts"]) == 1
    assert result["impacts"][0]["successor_activity_id"] == "SUCC_UNSTARTED"
    assert result["impacts"][0]["gross_delay_days"] == 5


# ==============================================================================
# IMP-16: Missing Duration Produces Uncertainty
# ==============================================================================

def test_imp_16_missing_duration_produces_uncertainty():
    # Successor missing planned_finish -> cannot convert FF finish constraint to start
    c = evaluate_constraint(
        predecessor_id="A",
        predecessor_start=date(2026, 8, 1),
        predecessor_finish=date(2026, 8, 10),
        successor_id="B",
        successor_planned_start=date(2026, 8, 5),
        successor_planned_finish=None,
        relationship_type="FF",
        lag_days=0.0,
        is_target_predecessor=True,
        simulated_delay_days=3,
    )
    assert c.uncertainty is True
    assert c.required_successor_start is None
    assert "missing planned duration" in c.uncertainty_reason.lower()

    res = evaluate_successor_impact(
        successor={"activity_id": "B", "planned_start": "2026-08-05", "planned_finish": None, "total_float": 2.0},
        execution_state="NOT_STARTED",
        constraints=[c],
        target_activity_id="A",
    )
    assert res["uncertainty"] is True


# ==============================================================================
# IMP-17: Batched Query Traversal Pipeline (End-to-End)
# ==============================================================================

def test_imp_17_batched_traversal_e2e():
    db = create_test_db()
    # Complex schedule topology:
    # A (target, delay=4)
    # B (other predecessor)
    # S1 has incoming: A (FS)
    # S2 has incoming: A (SS, lag=1) and B (FF)
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'S-01', 'Target Act', 'CIVIL', 'L1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'S-01', 'Other Pred', 'CIVIL', 'L1', '2026-08-01', '2026-08-07', 2.0),
               ('S1', 'S-01', 'Successor 1', 'CIVIL', 'L1', '2026-08-05', '2026-08-10', 3.0),
               ('S2', 'S-01', 'Successor 2', 'CIVIL', 'L1', '2026-08-05', '2026-08-15', NULL)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type, lag_days)
        VALUES ('D1', 'S-01', 'A', 'S1', 'FS', 0.0),
               ('D2', 'S-01', 'A', 'S2', 'SS', 1.0),
               ('D3', 'S-01', 'B', 'S2', 'FF', 0.0)
        """
    )

    result = query_impact_preview("A", delay_days=4, conn=db)
    assert result["activity_id"] == "A"
    assert result["delay_days"] == 4
    assert len(result["impacts"]) == 2

    # S1 evaluation:
    # A planned_finish=2026-08-05 + 4 delay = 2026-08-09.
    # S1 planned_start=2026-08-05 -> gross delay = 4 days.
    # Total float = 3.0 -> absorbed=3, net=1.
    s1 = result["impacts"][0]
    assert s1["successor_activity_id"] == "S1"
    assert s1["gross_delay_days"] == 4
    assert s1["float_status"] == "KNOWN"
    assert s1["absorbed_delay_days"] == 3
    assert s1["net_delay_days"] == 1

    # S2 evaluation:
    # A SS with lag 1: A planned_start=2026-08-01 + 4 delay + 1 lag = 2026-08-06.
    # B FF: B finish=2026-08-07. S2 duration = 10. Req finish = 2026-08-07 -> Req start = 2026-07-28.
    # Controlling constraint is A SS (req start 2026-08-06 > 2026-07-28).
    # S2 planned_start=2026-08-05 -> gross delay = 1 day.
    # S2 total_float is NULL -> float_status=UNKNOWN, absorbed=None, net=None.
    s2 = result["impacts"][1]
    assert s2["successor_activity_id"] == "S2"
    assert s2["controlling_predecessor"] == "A"
    assert s2["controlling_relationship"] == "SS"
    assert s2["gross_delay_days"] == 1
    assert s2["float_status"] == "UNKNOWN"
    assert s2["absorbed_delay_days"] is None
    assert s2["net_delay_days"] is None
    assert s2["uncertainty"] is True
