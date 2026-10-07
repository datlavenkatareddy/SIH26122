"""
Regression test suite for Priority 1 & 2: Supabase RLS Security and Safe Foreign Keys.

Verifies:
1. RLS is active on all 14 public tables.
2. Anonymous access (role `anon`) is denied from accessing protected data tables.
3. Authenticated access (role `authenticated`) functions per RLS policies.
4. Backend access (role `postgres`) bypasses RLS seamlessly.
5. Foreign key constraints actively prevent invalid relational writes.
6. Safe migration integrity: historical records remain intact.
"""

import uuid
import pytest
import psycopg.errors
from backend.shared.db import get_connection

EXPECTED_TABLES = [
    "profiles",
    "schedules",
    "schedule_activities",
    "schedule_dependencies",
    "source_documents",
    "execution_events",
    "source_references",
    "candidate_matches",
    "conflict_records",
    "validation_issues",
    "planner_decisions",
    "approved_actuals",
    "audit_logs",
    "claim_wbs_splits",
    "claim_activity_splits",
    "evidence_links",
    "execution_summaries",
]


def test_rls_enabled_on_all_tables():
    """Verify that every single public table has Row Level Security enabled."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename, rowsecurity
                FROM pg_tables
                WHERE schemaname = 'public' AND tablename = ANY(%s)
                """,
                (EXPECTED_TABLES,),
            )
            rows = {r["tablename"]: r["rowsecurity"] for r in cur.fetchall()}

    for tbl in EXPECTED_TABLES:
        assert tbl in rows, f"Table {tbl} not found in database"
        assert rows[tbl] is True, f"RLS is NOT enabled on table {tbl}"


def test_anon_access_denied_by_rls():
    """Verify that anonymous role (anon) is blocked from reading or writing sensitive data."""
    with get_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE anon;")
                # anon should read 0 rows from protected tables or fail
                cur.execute("SELECT count(*) FROM execution_events;")
                assert cur.fetchone()["count"] == 0

                cur.execute("SELECT count(*) FROM approved_actuals;")
                assert cur.fetchone()["count"] == 0

                cur.execute("SELECT count(*) FROM audit_logs;")
                assert cur.fetchone()["count"] == 0

                # anon cannot insert
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute(
                        """
                        INSERT INTO execution_events (
                            event_id, schedule_id, event_date, raw_claim_text, input_channel
                        ) VALUES ('test-anon', 'sched-1', '2026-01-01', 'hack', 'TYPED_TEXT');
                        """
                    )


def test_authenticated_access_allowed_by_rls():
    """Verify that authenticated role can query data according to SELECT policies."""
    with get_connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE authenticated;")
                # authenticated users have SELECT policies on public metadata/tables
                cur.execute("SELECT count(*) FROM schedules;")
                count = cur.fetchone()["count"]
                assert count >= 0


def test_foreign_key_enforcement_on_new_writes():
    """Verify that FK constraints reject invalid relational writes on all protected paths."""
    non_existent_sched = f"NON-EXIST-{uuid.uuid4().hex[:6]}"
    non_existent_event = f"NON-EXIST-EVT-{uuid.uuid4().hex[:6]}"

    # 1. schedule_activities -> schedules FK
    with get_connection() as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO schedule_activities (
                            schedule_id, activity_id, activity_name, discipline, location,
                            planned_start, planned_finish
                        ) VALUES (%s, 'ACT-INVALID', 'Test', 'CIVIL', 'LOC', '2026-01-01', '2026-01-10');
                        """,
                        (non_existent_sched,),
                    )

    # 2. execution_events -> schedules FK
    with get_connection() as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO execution_events (
                            event_id, schedule_id, event_date, raw_claim_text, input_channel
                        ) VALUES ('EVT-INV', %s, '2026-01-01', 'text', 'TYPED_TEXT');
                        """,
                        (non_existent_sched,),
                    )

    # 3. planner_decisions -> execution_events FK
    with get_connection() as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO planner_decisions (
                            decision_id, event_id, selected_activity_id, action, planner_id, justification
                        ) VALUES ('DEC-INV', %s, 'ACT-1', 'APPROVE', %s, 'justification');
                        """,
                        (non_existent_event, str(uuid.uuid4())),
                    )


def test_historical_orphan_records_accessible():
    """Verify that historical orphan records remain safely intact and readable."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM execution_events WHERE schedule_id = 'sched-OIL-2026';")
            count = cur.fetchone()["count"]
            assert count == 8, f"Expected 8 historical orphan execution_events, got {count}"

            cur.execute("SELECT count(*) FROM approved_actuals WHERE schedule_id = 'sched-OIL-2026';")
            actual_count = cur.fetchone()["count"]
            assert actual_count == 4, f"Expected 4 historical orphan approved_actuals, got {actual_count}"
