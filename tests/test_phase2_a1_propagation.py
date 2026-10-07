"""
Phase 2 Impact Preview Algorithm A1 — Bounded Multi-Hop Propagation Tests.

Covers:
- PROP-01: 2-hop propagation (A -> B -> C)
- PROP-02: 3-hop propagation (A -> B -> C -> D)
- PROP-03: Bounded stop at MAX_IMPACT_HOPS = 3 (hop 4 excluded)
- PROP-04: Cycle protection (A -> B -> C -> A terminates safely)
- PROP-05: Completed successor does not shift (impact = 0)
- PROP-06: Completed successor does not propagate delay downstream
- PROP-07: In-progress successor uses planned duration semantics
- PROP-08: NOT_STARTED successor propagates normally
- PROP-09: Float absorption reduces propagated delay (A delay=5, B float=3 => C receives 2)
- PROP-10: NULL float does not become zero during propagation
- PROP-11: NULL float produces null net delay and halts numeric delay propagation
- PROP-12: Multiple paths converge on same successor without duplicate output
- PROP-13: Multiple predecessors reconciled at downstream hop
- PROP-14: Non-target predecessor controlling downstream
- PROP-15: Mixed relationship types across hops (FS -> SS -> FF)
- PROP-16: Positive lag & negative lead across hops
- PROP-17: Database immutability (schedule dates unchanged after preview)
- PROP-18: Batched query execution verification (zero N+1 queries)
- PROP-19: Structured path / explanation trace returned
- PROP-20: Backward compatibility of legacy response fields
"""

import sqlite3
from typing import Any, List, Optional
import pytest

from backend.routers.schedule import MAX_IMPACT_HOPS, query_impact_preview
from backend.shared.schemas import ExecutionState


class CountingSQLiteAdapter:
    """
    In-memory SQLite adapter that logs query count and translates %s to ?.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.query_count = 0
        self.query_log: List[str] = []

    def execute(self, query: str, params=None):
        self.query_count += 1
        self.query_log.append(query)
        clean_q = query.replace("%s", "?")
        cur = self.conn.cursor()
        if params is not None:
            cur.execute(clean_q, params)
        else:
            cur.execute(clean_q)
        return cur

    def commit(self):
        self.conn.commit()


def create_propagation_test_db() -> CountingSQLiteAdapter:
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
    return CountingSQLiteAdapter(conn)


# ==============================================================================
# PROP-01: 2-Hop Propagation (A -> B -> C)
# ==============================================================================

def test_prop_01_two_hop_propagation():
    db = create_propagation_test_db()
    # A -> B -> C, total_float=0
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Activity A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Activity B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Activity C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS')
        """
    )

    result = query_impact_preview("A", delay_days=5, conn=db)
    impacts = {imp["successor_activity_id"]: imp for imp in result["impacts"]}

    assert "B" in impacts
    assert impacts["B"]["propagation_depth"] == 1
    assert impacts["B"]["gross_delay_days"] == 5
    assert impacts["B"]["net_delay_days"] == 5
    assert impacts["B"]["shifted_earliest_start"] == "2026-08-10"
    assert impacts["B"]["target_path"] == ["A", "B"]

    assert "C" in impacts
    assert impacts["C"]["propagation_depth"] == 2
    assert impacts["C"]["gross_delay_days"] == 5
    assert impacts["C"]["net_delay_days"] == 5
    assert impacts["C"]["shifted_earliest_start"] == "2026-08-15"
    assert impacts["C"]["target_path"] == ["A", "B", "C"]


# ==============================================================================
# PROP-02: 3-Hop Propagation (A -> B -> C -> D)
# ==============================================================================

def test_prop_02_three_hop_propagation():
    db = create_propagation_test_db()
    # A -> B -> C -> D, total_float=0
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0),
               ('D', 'SCHED-1', 'Act D', 'CIVIL', 'Site 1', '2026-08-15', '2026-08-20', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS'),
               ('DEP-CD', 'SCHED-1', 'C', 'D', 'FS')
        """
    )

    result = query_impact_preview("A", delay_days=4, conn=db)
    impacts = {imp["successor_activity_id"]: imp for imp in result["impacts"]}

    assert len(impacts) == 3
    assert impacts["B"]["propagation_depth"] == 1
    assert impacts["B"]["net_delay_days"] == 4
    assert impacts["B"]["target_path"] == ["A", "B"]

    assert impacts["C"]["propagation_depth"] == 2
    assert impacts["C"]["net_delay_days"] == 4
    assert impacts["C"]["target_path"] == ["A", "B", "C"]

    assert impacts["D"]["propagation_depth"] == 3
    assert impacts["D"]["net_delay_days"] == 4
    assert impacts["D"]["target_path"] == ["A", "B", "C", "D"]


# ==============================================================================
# PROP-03: Bounded Stop at MAX_IMPACT_HOPS = 3
# ==============================================================================

def test_prop_03_bounded_stop_at_max_hops():
    db = create_propagation_test_db()
    # A -> B -> C -> D -> E (5 activities in series, E is at hop 4)
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0),
               ('D', 'SCHED-1', 'Act D', 'CIVIL', 'Site 1', '2026-08-15', '2026-08-20', 0.0),
               ('E', 'SCHED-1', 'Act E', 'CIVIL', 'Site 1', '2026-08-20', '2026-08-25', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS'),
               ('DEP-CD', 'SCHED-1', 'C', 'D', 'FS'),
               ('DEP-DE', 'SCHED-1', 'D', 'E', 'FS')
        """
    )

    result = query_impact_preview("A", delay_days=3, conn=db)
    impact_ids = [imp["successor_activity_id"] for imp in result["impacts"]]

    assert result["propagation_depth_limit"] == 3
    assert "B" in impact_ids
    assert "C" in impact_ids
    assert "D" in impact_ids
    # E is at hop 4 -> strictly excluded
    assert "E" not in impact_ids
    assert len(result["impacts"]) == 3


# ==============================================================================
# PROP-04: Cycle Protection
# ==============================================================================

def test_prop_04_cycle_protection():
    db = create_propagation_test_db()
    # Cycle: A -> B -> C -> A, plus internal C -> B
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS'),
               ('DEP-CA', 'SCHED-1', 'C', 'A', 'FS'),
               ('DEP-CB', 'SCHED-1', 'C', 'B', 'FS')
        """
    )

    # Must terminate cleanly and without infinite loop or duplicate activity records
    result = query_impact_preview("A", delay_days=5, conn=db)
    impact_ids = [imp["successor_activity_id"] for imp in result["impacts"]]

    assert "B" in impact_ids
    assert "C" in impact_ids
    # Target A is never reported as its own downstream successor
    assert "A" not in impact_ids
    # Exactly one record per unique successor
    assert len(impact_ids) == len(set(impact_ids))


# ==============================================================================
# PROP-05: Completed Successor Does Not Shift (impact = 0)
# ==============================================================================

def test_prop_05_completed_successor_zero_shift():
    db = create_propagation_test_db()
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS')
        """
    )
    # B is marked COMPLETED
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, schedule_id, activity_id, actual_start, actual_finish, actual_pct_complete)
        VALUES ('ACT-B', 'SCHED-1', 'B', '2026-08-05', '2026-08-09', 100.0)
        """
    )

    result = query_impact_preview("A", delay_days=5, conn=db)
    assert len(result["impacts"]) == 1
    b_impact = result["impacts"][0]
    assert b_impact["successor_activity_id"] == "B"
    assert b_impact["execution_state"] == "COMPLETED"
    assert b_impact["gross_delay_days"] == 0
    assert b_impact["net_delay_days"] == 0
    assert b_impact["shifted_earliest_start"] == b_impact["original_earliest_start"]
    assert b_impact["classification"] == "ALREADY_COMPLETED"


# ==============================================================================
# PROP-06: Completed Successor Does Not Propagate Delay Downstream
# ==============================================================================

def test_prop_06_completed_successor_no_downstream_propagation():
    db = create_propagation_test_db()
    # A -> B -> C
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS')
        """
    )
    # B is completed
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, schedule_id, activity_id, actual_start, actual_finish, actual_pct_complete)
        VALUES ('ACT-B', 'SCHED-1', 'B', '2026-08-05', '2026-08-09', 100.0)
        """
    )

    result = query_impact_preview("A", delay_days=5, conn=db)
    impact_ids = [imp["successor_activity_id"] for imp in result["impacts"]]

    # B is evaluated at depth 1 with 0 shift
    assert "B" in impact_ids
    # C must NOT receive propagated delay from completed B
    assert "C" not in impact_ids


# ==============================================================================
# PROP-07: In-Progress Successor Uses Planned Duration Semantics
# ==============================================================================

def test_prop_07_in_progress_successor_planned_duration():
    db = create_propagation_test_db()
    # A -> B -> C
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS')
        """
    )
    # B is IN_PROGRESS (actual_start recorded, 40% complete)
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, schedule_id, activity_id, actual_start, actual_pct_complete)
        VALUES ('ACT-B', 'SCHED-1', 'B', '2026-08-05', 40.0)
        """
    )

    result = query_impact_preview("A", delay_days=3, conn=db)
    impacts = {imp["successor_activity_id"]: imp for imp in result["impacts"]}

    assert impacts["B"]["execution_state"] == "IN_PROGRESS"
    assert impacts["B"]["classification"] == "EXECUTION_IN_PROGRESS"
    assert impacts["B"]["gross_delay_days"] == 3
    assert impacts["B"]["net_delay_days"] == 3

    # C receives the 3-day net delay based on B's simulated finish
    assert impacts["C"]["propagation_depth"] == 2
    assert impacts["C"]["gross_delay_days"] == 3
    assert impacts["C"]["net_delay_days"] == 3
    assert impacts["C"]["shifted_earliest_start"] == "2026-08-13"


# ==============================================================================
# PROP-08: NOT_STARTED Successor Propagates Normally
# ==============================================================================

def test_prop_08_not_started_successor_propagation():
    db = create_propagation_test_db()
    # A -> B -> C with B NOT_STARTED
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS')
        """
    )
    db.execute(
        """
        INSERT INTO approved_actuals (actual_id, schedule_id, activity_id, actual_pct_complete)
        VALUES ('ACT-B', 'SCHED-1', 'B', 0.0)
        """
    )

    result = query_impact_preview("A", delay_days=4, conn=db)
    impacts = {imp["successor_activity_id"]: imp for imp in result["impacts"]}

    assert impacts["B"]["execution_state"] == "NOT_STARTED"
    assert impacts["B"]["net_delay_days"] == 4
    assert impacts["C"]["net_delay_days"] == 4


# ==============================================================================
# PROP-09: Float Absorption Reduces Propagated Delay (A delay=5, B float=3 => C receives 2)
# ==============================================================================

def test_prop_09_float_absorption_reduces_propagated_delay():
    db = create_propagation_test_db()
    # A (delay=5) -> B (total_float=3) -> C (total_float=0)
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 3.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS')
        """
    )

    result = query_impact_preview("A", delay_days=5, conn=db)
    impacts = {imp["successor_activity_id"]: imp for imp in result["impacts"]}

    # B absorbs 3 days of float, leaving net delay of 2 days
    assert impacts["B"]["gross_delay_days"] == 5
    assert impacts["B"]["total_float"] == 3.0
    assert impacts["B"]["absorbed_delay_days"] == 3
    assert impacts["B"]["net_delay_days"] == 2
    assert impacts["B"]["classification"] == "CRITICAL_PATH_SLIP"

    # C receives ONLY B's net delay (2 days), NOT 5 days, NOT 5+2=7 days!
    assert impacts["C"]["propagation_depth"] == 2
    assert impacts["C"]["gross_delay_days"] == 2
    assert impacts["C"]["net_delay_days"] == 2
    assert impacts["C"]["shifted_earliest_start"] == "2026-08-12"


# ==============================================================================
# PROP-10: NULL Float Does Not Become Zero During Propagation
# ==============================================================================

def test_prop_10_null_float_does_not_become_zero():
    db = create_propagation_test_db()
    # B has total_float NULL
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', NULL)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS')
        """
    )

    result = query_impact_preview("A", delay_days=4, conn=db)
    impacts = {imp["successor_activity_id"]: imp for imp in result["impacts"]}

    assert impacts["B"]["float_status"] == "UNKNOWN"
    assert impacts["B"]["total_float"] is None
    assert impacts["B"]["absorbed_delay_days"] is None
    assert impacts["B"]["net_delay_days"] is None
    assert impacts["B"]["uncertainty"] is True


# ==============================================================================
# PROP-11: NULL Float Produces Null Net Delay and Halts Numeric Propagation
# ==============================================================================

def test_prop_11_null_float_halts_numeric_propagation():
    db = create_propagation_test_db()
    # A -> B (NULL float) -> C (0 float)
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', NULL),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS')
        """
    )

    result = query_impact_preview("A", delay_days=5, conn=db)
    impact_ids = [imp["successor_activity_id"] for imp in result["impacts"]]

    # B is in impacts with UNKNOWN float and NULL net delay
    assert "B" in impact_ids
    assert result["impacts"][0]["net_delay_days"] is None
    assert result["impacts"][0]["uncertainty"] is True

    # Numeric propagation ceases along this branch; C is NOT included
    assert "C" not in impact_ids


# ==============================================================================
# PROP-12: Multiple Paths Converge on Same Successor Without Duplicate Output
# ==============================================================================

def test_prop_12_converging_paths_no_duplicate_output():
    db = create_propagation_test_db()
    # Diamond: A -> B -> D and A -> C -> D
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-12', 0.0),
               ('D', 'SCHED-1', 'Act D', 'CIVIL', 'Site 1', '2026-08-12', '2026-08-18', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-AC', 'SCHED-1', 'A', 'C', 'FS'),
               ('DEP-BD', 'SCHED-1', 'B', 'D', 'FS'),
               ('DEP-CD', 'SCHED-1', 'C', 'D', 'FS')
        """
    )

    result = query_impact_preview("A", delay_days=5, conn=db)
    impact_ids = [imp["successor_activity_id"] for imp in result["impacts"]]

    # D must appear EXACTLY ONCE in output
    assert impact_ids.count("D") == 1
    d_impact = next(imp for imp in result["impacts"] if imp["successor_activity_id"] == "D")
    assert d_impact["propagation_depth"] == 2
    # C finished Aug 12, with 5 days delay finishes Aug 17 -> D start pushed to Aug 17 (gross delay 5)
    assert d_impact["gross_delay_days"] == 5
    assert d_impact["shifted_earliest_start"] == "2026-08-17"


# ==============================================================================
# PROP-13: Multiple Predecessors Reconciled at Downstream Hop
# ==============================================================================

def test_prop_13_multiple_predecessors_reconciled_downstream():
    db = create_propagation_test_db()
    # At hop 2: D has predecessor B (delayed) and independent E (baseline)
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('E', 'SCHED-1', 'Act E', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-11', 0.0),
               ('D', 'SCHED-1', 'Act D', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-18', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BD', 'SCHED-1', 'B', 'D', 'FS'),
               ('DEP-ED', 'SCHED-1', 'E', 'D', 'FS')
        """
    )

    # Delay A by 4 days -> B simulated finish pushed from Aug 10 to Aug 14
    # E finish is Aug 11 (unaffected)
    # D requires max(14, 11) = Aug 14 -> B is controlling
    result = query_impact_preview("A", delay_days=4, conn=db)
    d_impact = next(imp for imp in result["impacts"] if imp["successor_activity_id"] == "D")

    assert d_impact["controlling_predecessor"] == "B"
    assert d_impact["shifted_earliest_start"] == "2026-08-14"
    assert d_impact["gross_delay_days"] == 4


# ==============================================================================
# PROP-14: Non-Target Predecessor Controlling Downstream
# ==============================================================================

def test_prop_14_non_target_predecessor_controlling_downstream():
    db = create_propagation_test_db()
    # D has predecessor B (delayed 2 days, finish Aug 12) and E (independent, finish Aug 16)
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('E', 'SCHED-1', 'Act E', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-16', 0.0),
               ('D', 'SCHED-1', 'Act D', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-20', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BD', 'SCHED-1', 'B', 'D', 'FS'),
               ('DEP-ED', 'SCHED-1', 'E', 'D', 'FS')
        """
    )

    # Delay A by 2 days -> B simulated finish = Aug 12
    # E finish = Aug 16
    # E imposes required start Aug 16, which is later than B's Aug 12
    result = query_impact_preview("A", delay_days=2, conn=db)
    d_impact = next(imp for imp in result["impacts"] if imp["successor_activity_id"] == "D")

    assert d_impact["controlling_predecessor"] == "E"
    assert d_impact["shifted_earliest_start"] == "2026-08-16"
    assert d_impact["gross_delay_days"] == 6


# ==============================================================================
# PROP-15: Mixed Relationship Types Across Hops (FS -> SS -> FF)
# ==============================================================================

def test_prop_15_mixed_relationship_types_across_hops():
    db = create_propagation_test_db()
    # Chain: A -[FS]-> B -[SS]-> C -[FF]-> D
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-12', 0.0),
               ('D', 'SCHED-1', 'Act D', 'CIVIL', 'Site 1', '2026-08-08', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'SS'),
               ('DEP-CD', 'SCHED-1', 'C', 'D', 'FF')
        """
    )

    # Delay A by 4 days:
    # B: FS from A -> B simulated start Aug 9, finish Aug 14 (net delay 4)
    # C: SS from B -> C required start = B simulated start = Aug 9. Gross delay = (Aug 9 - Aug 5) = 4.
    #    C planned finish Aug 12, duration 7 days -> C simulated finish = Aug 12 + 4 = Aug 16.
    # D: FF from C -> D required finish = C simulated finish = Aug 16.
    #    D planned duration = (Aug 15 - Aug 8) = 7 days.
    #    D required start = Aug 16 - 7 days = Aug 9.
    #    D planned start = Aug 8 -> D gross delay = 1 day (Aug 9 - Aug 8).
    result = query_impact_preview("A", delay_days=4, conn=db)
    impacts = {imp["successor_activity_id"]: imp for imp in result["impacts"]}

    assert impacts["B"]["dependency_type"] == "FS"
    assert impacts["B"]["gross_delay_days"] == 4

    assert impacts["C"]["dependency_type"] == "SS"
    assert impacts["C"]["gross_delay_days"] == 4
    assert impacts["C"]["shifted_earliest_start"] == "2026-08-09"

    assert impacts["D"]["dependency_type"] == "FF"
    assert impacts["D"]["gross_delay_days"] == 1
    assert impacts["D"]["shifted_earliest_start"] == "2026-08-09"


# ==============================================================================
# PROP-16: Positive Lag & Negative Lead Across Hops
# ==============================================================================

def test_prop_16_lag_and_lead_across_hops():
    db = create_propagation_test_db()
    # A -[FS, lag=2]-> B -[FS, lag=-1]-> C
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-07', '2026-08-12', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-11', '2026-08-16', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type, lag_days)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS', 2.0),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS', -1.0)
        """
    )

    # Delay A by 3 days:
    # A finish shifted: Aug 5 + 3 = Aug 8.
    # B required start: Aug 8 + 2 (lag) = Aug 10.
    # B planned start: Aug 7 -> B gross delay = 3 days (Aug 10 - Aug 7).
    # B simulated finish: Aug 12 + 3 = Aug 15.
    # C required start: Aug 15 + (-1 lead) = Aug 14.
    # C planned start: Aug 11 -> C gross delay = 3 days (Aug 14 - Aug 11).
    result = query_impact_preview("A", delay_days=3, conn=db)
    impacts = {imp["successor_activity_id"]: imp for imp in result["impacts"]}

    assert impacts["B"]["shifted_earliest_start"] == "2026-08-10"
    assert impacts["B"]["gross_delay_days"] == 3

    assert impacts["C"]["shifted_earliest_start"] == "2026-08-14"
    assert impacts["C"]["gross_delay_days"] == 3


# ==============================================================================
# PROP-17: Database Immutability (Schedule Dates Unchanged)
# ==============================================================================

def test_prop_17_database_immutability():
    db = create_propagation_test_db()
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS')
        """
    )

    # Capture state before preview
    before_rows = db.execute("SELECT activity_id, planned_start, planned_finish FROM schedule_activities ORDER BY activity_id").fetchall()
    before_data = [dict(r) for r in before_rows]

    # Execute preview
    query_impact_preview("A", delay_days=7, conn=db)

    # Capture state after preview
    after_rows = db.execute("SELECT activity_id, planned_start, planned_finish FROM schedule_activities ORDER BY activity_id").fetchall()
    after_data = [dict(r) for r in after_rows]

    assert before_data == after_data, "Impact preview must NOT mutate persistent schedule data in DB!"


# ==============================================================================
# PROP-18: Batched Query Execution Verification (Zero N+1 Queries)
# ==============================================================================

def test_prop_18_batched_query_execution_zero_n_plus_one():
    db = create_propagation_test_db()
    # Create a wider graph with 8 activities across 3 hops
    # Hop 1: B1, B2
    # Hop 2: C1, C2, C3
    # Hop 3: D1, D2
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A',  'SCHED-1', 'Act A',  'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B1', 'SCHED-1', 'Act B1', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('B2', 'SCHED-1', 'Act B2', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C1', 'SCHED-1', 'Act C1', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0),
               ('C2', 'SCHED-1', 'Act C2', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0),
               ('C3', 'SCHED-1', 'Act C3', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0),
               ('D1', 'SCHED-1', 'Act D1', 'CIVIL', 'Site 1', '2026-08-15', '2026-08-20', 0.0),
               ('D2', 'SCHED-1', 'Act D2', 'CIVIL', 'Site 1', '2026-08-15', '2026-08-20', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB1', 'SCHED-1', 'A', 'B1', 'FS'),
               ('DEP-AB2', 'SCHED-1', 'A', 'B2', 'FS'),
               ('DEP-B1C1', 'SCHED-1', 'B1', 'C1', 'FS'),
               ('DEP-B1C2', 'SCHED-1', 'B1', 'C2', 'FS'),
               ('DEP-B2C3', 'SCHED-1', 'B2', 'C3', 'FS'),
               ('DEP-C1D1', 'SCHED-1', 'C1', 'D1', 'FS'),
               ('DEP-C2D2', 'SCHED-1', 'C2', 'D2', 'FS'),
               ('DEP-C3D2', 'SCHED-1', 'C3', 'D2', 'FS')
        """
    )

    db.query_count = 0  # reset counter before preview
    result = query_impact_preview("A", delay_days=5, conn=db)

    assert len(result["impacts"]) == 7  # B1, B2, C1, C2, C3, D1, D2
    # Verification of query bounding:
    # 1 target query + (at most 4 queries per hop * 3 hops = 12 queries) -> total <= 13 queries
    # In an unbatched N+1 system, 7+ nodes would result in 25-35+ queries.
    assert db.query_count <= 14, f"Expected batched traversal queries <= 14, got {db.query_count}"


# ==============================================================================
# PROP-19: Structured Path / Explanation Trace Returned
# ==============================================================================

def test_prop_19_structured_path_trace_returned():
    db = create_propagation_test_db()
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0),
               ('C', 'SCHED-1', 'Act C', 'CIVIL', 'Site 1', '2026-08-10', '2026-08-15', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS'),
               ('DEP-BC', 'SCHED-1', 'B', 'C', 'FS')
        """
    )

    result = query_impact_preview("A", delay_days=2, conn=db)
    for impact in result["impacts"]:
        assert "propagation_depth" in impact
        assert isinstance(impact["propagation_depth"], int)
        assert "target_path" in impact
        assert isinstance(impact["target_path"], list)
        assert impact["target_path"][0] == "A"
        assert impact["target_path"][-1] == impact["successor_activity_id"]
        assert "controlling_predecessor" in impact
        assert "controlling_relationship" in impact
        assert "constraints_evaluated" in impact


# ==============================================================================
# PROP-20: Backward Compatibility of Legacy Response Fields
# ==============================================================================

def test_prop_20_backward_compatibility():
    db = create_propagation_test_db()
    db.execute(
        """
        INSERT INTO schedule_activities (activity_id, schedule_id, activity_name, discipline, location, planned_start, planned_finish, total_float)
        VALUES ('A', 'SCHED-1', 'Act A', 'CIVIL', 'Site 1', '2026-08-01', '2026-08-05', 0.0),
               ('B', 'SCHED-1', 'Act B', 'CIVIL', 'Site 1', '2026-08-05', '2026-08-10', 0.0)
        """
    )
    db.execute(
        """
        INSERT INTO schedule_dependencies (dependency_id, schedule_id, predecessor_activity_id, successor_activity_id, relationship_type)
        VALUES ('DEP-AB', 'SCHED-1', 'A', 'B', 'FS')
        """
    )

    result = query_impact_preview("A", delay_days=3, conn=db)

    # Legacy top-level keys
    assert "activity_id" in result
    assert "delay_days" in result
    assert "impacts" in result
    assert isinstance(result["impacts"], list)

    # Legacy impact item keys
    for impact in result["impacts"]:
        assert "successor_activity_id" in impact
        assert "dependency_type" in impact
        assert "original_earliest_start" in impact
        assert "shifted_earliest_start" in impact
