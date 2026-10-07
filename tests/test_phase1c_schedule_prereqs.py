"""
Phase 1C — Schedule Data Prerequisites Test Suite

Covers schema, parser, repository, and execution-state requirements:
- SCHEMA-01: Existing schedule activity rows survive with existing fields intact.
- SCHEMA-02: Existing dependency rows survive and missing lag defaults to 0.0.
- SCHEMA-03: Missing total_float remains NULL; explicitly prove NULL != 0.
- SCHEMA-04: Missing is_critical remains NULL when both is_critical and total_float missing.
- SCHEMA-05: Missing lag_days becomes 0.0.
- SCHEMA-06: NULL total_float is not interpreted as zero (does not imply critical or zero float).
- SCHEMA-07: Source-provided is_critical=false is preserved even when total_float=0.
- SCHEMA-08: Source-provided total_float=4.5 is preserved exactly.
- SCHEMA-09: FS/SS/FF/SF remain valid relationship types.
- STATE-01: No actual_start + 0% -> NOT_STARTED.
- STATE-02: actual_start + 25% -> IN_PROGRESS.
- STATE-03: actual_start + 99% -> IN_PROGRESS.
- STATE-04: 100% -> COMPLETED.
- STATE-05: 110% -> COMPLETED.
- STATE-NULL-01: actual_start present + percentage NULL -> IN_PROGRESS.
- STATE-NULL-02: actual_start absent + percentage NULL -> NOT_STARTED.
"""

from datetime import date
import uuid

import pytest

from backend.shared.actuals import get_execution_state
from backend.shared.schedule import parse_schedule_csv
from backend.shared.schedule_repository import (
    get_schedule_activity,
    list_schedule_activities,
    list_schedule_dependencies,
    save_schedule,
)
from backend.shared.schemas import (
    ExecutionState,
    Schedule,
    ScheduleActivity,
    ScheduleDependency,
)


_BASE_CSV = (
    "L6 Task ID,L5 Activity ID,Activity,Discipline,Unit,Planned Qty,Baseline Start,Baseline Finish,L1,L2\n"
    "ACT-001,WBS-1,Earthwork Prep,Civil,m3,100.0,2026-08-01,2026-08-10,Zone A,Sub 1\n"
    "ACT-002,WBS-1,Foundation Pour,Civil,m3,50.0,2026-08-11,2026-08-20,Zone A,Sub 1\n"
)


# ===========================================================================
# Schema & Parsing Tests (SCHEMA-01 through SCHEMA-09)
# ===========================================================================

def test_schema_01_existing_activity_fields_intact():
    """Existing schedule activity rows survive with existing fields intact."""
    result = parse_schedule_csv(_BASE_CSV, schedule_id="SCHED-S01")
    assert result.is_valid
    assert len(result.activities) == 2

    act1 = result.activities[0]
    assert act1.activity_id == "ACT-001"
    assert act1.activity_name == "Earthwork Prep"
    assert act1.discipline == "Civil"
    assert act1.location == "Zone A / Sub 1"
    assert act1.planned_start == date(2026, 8, 1)
    assert act1.planned_finish == date(2026, 8, 10)
    assert act1.planned_quantity == 100.0
    assert act1.uom == "m3"
    assert act1.baseline_pct_complete == 0.0


def test_schema_02_and_05_dependency_defaults_lag_to_zero():
    """Existing dependency rows survive migration and missing lag defaults to 0.0."""
    csv_text = (
        "L6 Task ID,L5 Activity ID,Activity,Discipline,Unit,Planned Qty,Baseline Start,Baseline Finish,L1,L2,Predecessor Activity ID,Relationship Type\n"
        "ACT-001,WBS-1,Earthwork Prep,Civil,m3,100.0,2026-08-01,2026-08-10,Zone A,Sub 1,,\n"
        "ACT-002,WBS-1,Foundation Pour,Civil,m3,50.0,2026-08-11,2026-08-20,Zone A,Sub 1,ACT-001,FS\n"
    )
    result = parse_schedule_csv(csv_text, schedule_id="SCHED-S02")
    assert result.is_valid
    assert len(result.dependencies) == 1

    dep = result.dependencies[0]
    assert dep.predecessor_activity_id == "ACT-001"
    assert dep.successor_activity_id == "ACT-002"
    assert dep.relationship_type == "FS"
    assert dep.lag_days == 0.0


def test_schema_03_and_06_missing_total_float_remains_null():
    """Missing total_float remains NULL. NULL != 0.0."""
    result = parse_schedule_csv(_BASE_CSV, schedule_id="SCHED-S03")
    act = result.activities[0]

    assert act.total_float is None
    # Explicitly prove NULL is not zero
    assert act.total_float != 0.0
    assert act.total_float != 0


def test_schema_04_missing_is_critical_remains_null():
    """Missing is_critical remains NULL when both is_critical and total_float are missing."""
    result = parse_schedule_csv(_BASE_CSV, schedule_id="SCHED-S04")
    act = result.activities[0]

    assert act.is_critical is None
    assert act.total_float is None


def test_schema_07_source_provided_is_critical_false_preserved_with_zero_float():
    """Source-provided is_critical=false is preserved even when total_float=0.0."""
    csv_text = (
        "L6 Task ID,L5 Activity ID,Activity,Discipline,Unit,Planned Qty,Baseline Start,Baseline Finish,L1,L2,Total Float,Is Critical\n"
        "ACT-001,WBS-1,Earthwork Prep,Civil,m3,100.0,2026-08-01,2026-08-10,Zone A,Sub 1,0.0,false\n"
        "ACT-002,WBS-1,Foundation Pour,Civil,m3,50.0,2026-08-11,2026-08-20,Zone A,Sub 1,5.0,true\n"
    )
    result = parse_schedule_csv(csv_text, schedule_id="SCHED-S07")
    assert result.is_valid
    assert len(result.activities) == 2

    # Case 1: source false + float 0 -> stays false
    act1 = result.activities[0]
    assert act1.total_float == 0.0
    assert act1.is_critical is False
    assert act1.is_critical is not None

    # Case 2: source true + float 5 -> stays true
    act2 = result.activities[1]
    assert act2.total_float == 5.0
    assert act2.is_critical is True


def test_schema_08_source_provided_total_float_preserved():
    """Source-provided total_float=4.5 is preserved exactly."""
    csv_text = (
        "L6 Task ID,L5 Activity ID,Activity,Discipline,Unit,Planned Qty,Baseline Start,Baseline Finish,L1,L2,Total Float\n"
        "ACT-001,WBS-1,Earthwork Prep,Civil,m3,100.0,2026-08-01,2026-08-10,Zone A,Sub 1,4.5\n"
        "ACT-002,WBS-1,Foundation Pour,Civil,m3,50.0,2026-08-11,2026-08-20,Zone A,Sub 1,-2.0\n"
    )
    result = parse_schedule_csv(csv_text, schedule_id="SCHED-S08")
    assert result.is_valid

    act1 = result.activities[0]
    assert act1.total_float == 4.5
    # Fallback derivation: 4.5 <= 0 is False
    assert act1.is_critical is False

    act2 = result.activities[1]
    assert act2.total_float == -2.0
    # Fallback derivation: -2.0 <= 0 is True
    assert act2.is_critical is True


def test_schema_09_all_relationship_types_valid():
    """FS, SS, FF, SF remain valid relationship types with positive and negative lag."""
    csv_text = (
        "L6 Task ID,L5 Activity ID,Activity,Discipline,Unit,Planned Qty,Baseline Start,Baseline Finish,L1,L2,Predecessor Activity ID,Relationship Type,Lag Days\n"
        "ACT-001,WBS-1,Task 1,Civil,m3,10,2026-08-01,2026-08-05,Zone A,Sub 1,,,\n"
        "ACT-002,WBS-1,Task 2,Civil,m3,10,2026-08-06,2026-08-10,Zone A,Sub 1,ACT-001,FS,2.5\n"
        "ACT-003,WBS-1,Task 3,Civil,m3,10,2026-08-06,2026-08-10,Zone A,Sub 1,ACT-001,SS,0\n"
        "ACT-004,WBS-1,Task 4,Civil,m3,10,2026-08-06,2026-08-10,Zone A,Sub 1,ACT-001,FF,-1.0\n"
        "ACT-005,WBS-1,Task 5,Civil,m3,10,2026-08-06,2026-08-10,Zone A,Sub 1,ACT-001,SF,3.0\n"
    )
    result = parse_schedule_csv(csv_text, schedule_id="SCHED-S09")
    assert result.is_valid
    assert len(result.dependencies) == 4

    deps = {d.successor_activity_id: d for d in result.dependencies}

    assert deps["ACT-002"].relationship_type == "FS"
    assert deps["ACT-002"].lag_days == 2.5

    assert deps["ACT-003"].relationship_type == "SS"
    assert deps["ACT-003"].lag_days == 0.0

    assert deps["ACT-004"].relationship_type == "FF"
    assert deps["ACT-004"].lag_days == -1.0  # Lead represented by negative lag

    assert deps["ACT-005"].relationship_type == "SF"
    assert deps["ACT-005"].lag_days == 3.0


def test_schema_repository_persistence_and_retrieval_e2e():
    """
    End-to-end repository test proving that total_float, is_critical,
    and lag_days are persisted into PostgreSQL and retrieved without data loss.
    """
    sched_id = f"test-p1c-{uuid.uuid4()}"
    csv_text = (
        "L6 Task ID,L5 Activity ID,Activity,Discipline,Unit,Planned Qty,Baseline Start,Baseline Finish,L1,L2,Total Float,Is Critical,Predecessor Activity ID,Relationship Type,Lag Days\n"
        f"ACT-PERSIST-1,WBS-1,Task 1,Civil,m3,10,2026-08-01,2026-08-05,Zone A,Sub 1,,,\n"
        f"ACT-PERSIST-2,WBS-1,Task 2,Civil,m3,10,2026-08-06,2026-08-10,Zone A,Sub 1,4.5,false,ACT-PERSIST-1,SS,-2.5\n"
        f"ACT-PERSIST-3,WBS-1,Task 3,Civil,m3,10,2026-08-06,2026-08-10,Zone A,Sub 1,0.0,true,ACT-PERSIST-1,FS,3.0\n"
    )

    parse_result = parse_schedule_csv(csv_text, schedule_id=sched_id)
    assert parse_result.is_valid

    schedule = Schedule(
        schedule_id=sched_id,
        project_name="Phase 1C E2E Test",
        data_date=date(2026, 8, 1),
        source_format="csv",
    )

    try:
        count = save_schedule(schedule, parse_result)
        assert count == 3

        # Read back activities
        activities = list_schedule_activities(sched_id)
        assert len(activities) == 3
        act_map = {a.activity_id: a for a in activities}

        # ACT-PERSIST-1: missing total_float remains None, missing is_critical remains None
        assert act_map["ACT-PERSIST-1"].total_float is None
        assert act_map["ACT-PERSIST-1"].total_float != 0.0
        assert act_map["ACT-PERSIST-1"].is_critical is None

        # ACT-PERSIST-2: total_float=4.5, is_critical=False
        assert act_map["ACT-PERSIST-2"].total_float == 4.5
        assert act_map["ACT-PERSIST-2"].is_critical is False

        # ACT-PERSIST-3: total_float=0.0, is_critical=True
        assert act_map["ACT-PERSIST-3"].total_float == 0.0
        assert act_map["ACT-PERSIST-3"].is_critical is True

        # Read back dependencies
        dependencies = list_schedule_dependencies(sched_id)
        assert len(dependencies) == 2
        dep_map = {d.successor_activity_id: d for d in dependencies}

        assert dep_map["ACT-PERSIST-2"].relationship_type == "SS"
        assert dep_map["ACT-PERSIST-2"].lag_days == -2.5

        assert dep_map["ACT-PERSIST-3"].relationship_type == "FS"
        assert dep_map["ACT-PERSIST-3"].lag_days == 3.0

    finally:
        # Cleanup
        from backend.shared.db import get_connection
        try:
            with get_connection() as conn:
                conn.execute("DELETE FROM schedule_dependencies WHERE schedule_id = %s", (sched_id,))
                conn.execute("DELETE FROM schedule_activities WHERE schedule_id = %s", (sched_id,))
                conn.execute("DELETE FROM schedules WHERE schedule_id = %s", (sched_id,))
                conn.commit()
        except Exception:
            pass


# ===========================================================================
# Execution State Tests (STATE-01 through STATE-05, STATE-NULL-01/02)
# ===========================================================================

def test_state_01_no_start_zero_percent_is_not_started():
    """STATE-01: No actual_start + 0% -> NOT_STARTED."""
    state = get_execution_state(actual_start=None, actual_pct_complete=0.0)
    assert state == ExecutionState.NOT_STARTED.value
    assert state == "NOT_STARTED"


def test_state_02_start_exists_25_percent_is_in_progress():
    """STATE-02: actual_start exists + 25% -> IN_PROGRESS."""
    state = get_execution_state(actual_start=date(2026, 8, 1), actual_pct_complete=25.0)
    assert state == ExecutionState.IN_PROGRESS.value
    assert state == "IN_PROGRESS"


def test_state_03_start_exists_99_percent_is_in_progress():
    """STATE-03: actual_start exists + 99% -> IN_PROGRESS."""
    state = get_execution_state(actual_start="2026-08-01", actual_pct_complete=99.0)
    assert state == ExecutionState.IN_PROGRESS.value
    assert state == "IN_PROGRESS"


def test_state_04_100_percent_is_completed():
    """STATE-04: 100% -> COMPLETED (with or without start date)."""
    # 100% without start date
    state1 = get_execution_state(actual_start=None, actual_pct_complete=100.0)
    assert state1 == ExecutionState.COMPLETED.value
    assert state1 == "COMPLETED"

    # 100% with start date
    state2 = get_execution_state(actual_start=date(2026, 8, 1), actual_pct_complete=100.0)
    assert state2 == ExecutionState.COMPLETED.value
    assert state2 == "COMPLETED"


def test_state_05_greater_than_100_percent_is_completed():
    """STATE-05: >100% -> COMPLETED."""
    state = get_execution_state(actual_start=date(2026, 8, 1), actual_pct_complete=110.0)
    assert state == ExecutionState.COMPLETED.value
    assert state == "COMPLETED"


def test_state_null_01_start_present_percentage_null_is_in_progress():
    """STATE-NULL-01: actual_start present + percentage NULL -> IN_PROGRESS."""
    state = get_execution_state(actual_start="2026-08-01", actual_pct_complete=None)
    assert state == ExecutionState.IN_PROGRESS.value
    assert state == "IN_PROGRESS"


def test_state_null_02_start_absent_percentage_null_is_not_started():
    """STATE-NULL-02: actual_start absent + percentage NULL -> NOT_STARTED."""
    state = get_execution_state(actual_start=None, actual_pct_complete=None)
    assert state == ExecutionState.NOT_STARTED.value
    assert state == "NOT_STARTED"


def test_state_with_dict_and_objects():
    """Verify get_execution_state inspects approved_actual dicts and objects correctly."""
    # From approved_actual dictionary
    aa_in_progress = {"actual_start": "2026-08-01", "actual_pct_complete": 40.0}
    assert get_execution_state(approved_actual=aa_in_progress) == "IN_PROGRESS"

    aa_completed = {"actual_start": "2026-08-01", "actual_pct_complete": 100.0}
    assert get_execution_state(approved_actual=aa_completed) == "COMPLETED"

    aa_not_started = {"actual_start": None, "actual_pct_complete": 0.0}
    assert get_execution_state(approved_actual=aa_not_started) == "NOT_STARTED"

    # Direct keyword override takes precedence over object
    assert get_execution_state(approved_actual=aa_in_progress, actual_pct_complete=100.0) == "COMPLETED"
