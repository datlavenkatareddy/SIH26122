"""
PRD v6 acceptance groups A2 (sequence), A4 (conflict), A5 (priority): TC-SEQ, TC-CONF, TC-PRI.
Pure-function tests -- no database, no network.
"""
import math
from datetime import date, datetime, timedelta, timezone

from backend.routers.checks import (
    compare_chronological_claims,
    compute_priority_aging,
    evaluate_dependency_rule,
    evaluate_smart_review_priority,
)

D = date


def _state(started=False, finished=False, start=None, finish=None, pct=0.0):
    return {"is_started": started, "is_finished": finished, "actual_start": start,
            "actual_finish": finish, "actual_pct_complete": pct, "actual_quantity": None}


def _seq(rel, pred, *, succ_started=False, event="ACTUAL_START", finish_claim=False, when=D(2026, 8, 20)):
    return evaluate_dependency_rule(
        relationship_type=rel, pred_id="PRED", pred_state=pred, succ_id="SUCC",
        succ_is_already_started=succ_started, event_type=event, is_finish_claim=finish_claim, event_date=when,
    )


# ---------------- A2: sequence ----------------

def test_tc_seq_01_fs_incomplete_predecessor_flags_unstarted_successor():
    assert _seq("FS", _state(started=True, pct=40)) is not None
    assert _seq("FS", _state(started=True, finished=True, start=D(2026, 8, 10), finish=D(2026, 8, 15), pct=100)) is None


def test_tc_seq_02_ss_started_predecessor_permits_successor_start():
    assert _seq("SS", _state(started=True, start=D(2026, 8, 12), pct=10)) is None
    assert _seq("SS", _state()) is not None  # predecessor not started


def test_tc_seq_03_ff_successor_finish_must_not_precede_predecessor_finish():
    incomplete = _state(started=True, pct=60)
    assert _seq("FF", incomplete, event="ACTUAL_FINISH", finish_claim=True, succ_started=True) is not None
    done = _state(started=True, finished=True, start=D(2026, 8, 10), finish=D(2026, 8, 18), pct=100)
    assert _seq("FF", done, event="ACTUAL_FINISH", finish_claim=True, succ_started=True, when=D(2026, 8, 19)) is None


def test_tc_seq_04_in_progress_successor_is_not_repeatedly_flagged():
    incomplete = _state(started=True, pct=40)
    assert _seq("FS", incomplete, event="PROGRESS_UPDATE", succ_started=True) is None


# ---------------- A4: conflict ----------------

def test_tc_conf_01_later_date_progress_is_not_a_conflict():
    r = compare_chronological_claims(D(2026, 8, 11), 20, D(2026, 8, 17), 80)
    assert r["relationship"] == "NORMAL_PROGRESSION" and not r.get("is_conflict")


def test_tc_conf_02_same_date_disagreement_beyond_tolerance():
    r = compare_chronological_claims(D(2026, 8, 14), 75, D(2026, 8, 14), 30)
    assert r["relationship"] == "SAME_DATE_DISAGREEMENT" and r["is_conflict"]
    assert compare_chronological_claims(D(2026, 8, 14), 50, D(2026, 8, 14), 55)["relationship"] == "SAME_DATE_AGREEMENT"


def test_tc_conf_03_newer_lower_is_regression_unless_rework():
    r = compare_chronological_claims(D(2026, 8, 12), 80, D(2026, 8, 18), 40)
    assert r["relationship"] == "PROGRESS_REGRESSION" and r["is_conflict"]
    r2 = compare_chronological_claims(D(2026, 8, 12), 80, D(2026, 8, 18), 40, has_rework_b=True)
    assert r2["relationship"] == "ACCEPTED_REWORK" and not r2["is_conflict"]


# ---------------- A5: priority ----------------

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _prio(issues=None, conflicts=None, links=None, *, activity_float=None, critical=None, hours=0.0, matched="ACT-1", status="REVIEW_REQUIRED"):
    ev = {"event_id": "E1", "schedule_id": "S1", "matched_activity_id": matched, "status": status,
          "created_at": NOW - timedelta(hours=hours)}
    info = {"total_float": activity_float, "is_critical": critical}
    return evaluate_smart_review_priority(ev, issues or [], conflicts or [], links or [], [], [{"match_tier": "EXACT_ID"}],
                                          activity_info=info, current_time=NOW)


SEQ_ERR = {"rule_code": "VAL_OUT_OF_SEQUENCE", "severity": "ERROR", "description": "x"}
WARN = {"rule_code": "VAL_EVIDENCE_MISMATCH", "severity": "WARNING", "description": "w"}


def test_tc_pri_01_critical_sequence_error_on_critical_path_is_at_least_200():
    r = _prio([SEQ_ERR], activity_float=0)
    assert r["base_severity"] == 100 and r["criticality_multiplier"] == 2.0
    assert r["priority_score"] >= 200


def test_tc_pri_02_warning_accumulation_is_capped_at_25_base_and_never_outranks_critical_error():
    many = _prio([WARN] * 12, activity_float=0, hours=10_000)
    assert many["base_severity"] == 25
    assert many["priority_score"] <= 25 * 2 + 30 + 1e-6            # 80 ceiling
    critical_unaged = _prio([SEQ_ERR], activity_float=20, hours=0)   # 100 x 1.0
    assert critical_unaged["priority_score"] > many["priority_score"]


def test_tc_pri_03_aging_is_capped_at_30_and_reasons_explain_the_score():
    assert compute_priority_aging(10_000_000) == 30.0
    assert math.isclose(compute_priority_aging(math.e - 1), 6.0, abs_tol=0.01)
    r = _prio([SEQ_ERR], activity_float=3, hours=48)
    assert r["criticality_multiplier"] == 1.5
    for tag in ("[Severity]", "[Cause]", "[Criticality]", "[Aging]"):
        assert tag in r["priority_reasons"]


def test_priority_bands():
    assert _prio([], conflicts=[{"status": "OPEN", "variance_pct": 40}], activity_float=20)["base_severity"] == 70
    assert _prio([], activity_float=20)["base_severity"] == 5
    assert _prio([], activity_float=20, matched=None, status="UNMATCHED")["base_severity"] == 40
