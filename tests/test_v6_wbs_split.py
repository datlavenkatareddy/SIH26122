"""
PRD v6 Feature 30 / acceptance group A3 -- WBS Granularity Bridge.
Pure-logic tests (no database): TC-WBS-01 .. TC-WBS-03 plus the XOR / sum /
UOM / manual-edit invariants.
"""
import pytest

from backend.shared.wbs_split import (
    SplitEditError,
    allocate_split,
    apply_manual_split_edit,
    classify_claim_scope,
    find_wbs_group,
)


def _act(aid, name, wbs, qty, uom, start, finish, **kw):
    return {"activity_id": aid, "activity_name": name, "wbs_code": wbs, "planned_quantity": qty,
            "uom": uom, "planned_start": start, "planned_finish": finish, **kw}


# Mirrors the benchmark's Utility Header group (1.02.02 + spool sections A/B/C).
ACTS = [
    _act("HDR", "Above Ground Utility Header Fabrication", "1.02.02", 100, "m", "2026-08-12", "2026-08-22"),
    _act("HDR-A", "Utility Header Spool Section A", "1.02.02.01", 40, "m", "2026-08-12", "2026-08-16"),
    _act("HDR-B", "Utility Header Spool Section B", "1.02.02.02", 30, "m", "2026-08-15", "2026-08-19"),
    _act("HDR-C", "Utility Header Spool Section C", "1.02.02.03", 30, "m", "2026-08-18", "2026-08-22"),
    _act("OTHER", "Unrelated", "1.03.01", 1, "ea", "2026-08-12", "2026-08-13"),
]
MEMBERS = ACTS[1:4]
CLAIM = {"claim_mode": "INCREMENTAL_QUANTITY", "claimed_quantity": 12.0, "claimed_uom": "m",
         "raw_claim_text": "Utility header fabrication 12 m done today", "event_date": "2026-08-17"}


def _sum(res):
    return round(sum(r["split_pct"] for r in res["splits"]), 4)


def test_group_discovery_from_summary_and_from_child():
    g = find_wbs_group("HDR", ACTS)
    assert g["kind"] == "SUMMARY_CHILDREN" and [m["activity_id"] for m in g["members"]] == ["HDR-A", "HDR-B", "HDR-C"]
    g2 = find_wbs_group("HDR-B", ACTS)
    assert g2["summary_activity_id"] == "HDR" and len(g2["members"]) == 3
    assert find_wbs_group("OTHER", ACTS) is None


def test_single_child_wbs_is_not_a_group():
    assert find_wbs_group("X", [_act("X", "x", "1.01.01", 1, "ea", "2026-08-01", "2026-08-02")]) is None


def test_tc_wbs_01_completed_sibling_gets_zero_and_split_sums_to_one():
    actuals = {"HDR-A": {"actual_pct_complete": 100, "actual_finish": "2026-08-16"}}
    res = allocate_split(CLAIM, MEMBERS, actuals, claim_date="2026-08-19")
    assert res["status"] == "SUCCESS"
    ids = {r["activity_id"] for r in res["splits"]}
    assert "HDR-A" not in ids and ids == {"HDR-B", "HDR-C"}
    assert any(e["activity_id"] == "HDR-A" and "completed" in e["reason"] for e in res["excluded"])
    assert abs(_sum(res) - 1.0) <= 0.0001


def test_tc_wbs_02_future_sibling_excluded():
    res = allocate_split(CLAIM, MEMBERS, {}, claim_date="2026-08-16")  # C starts 08-18
    ids = {r["activity_id"] for r in res["splits"]}
    assert "HDR-C" not in ids and {"HDR-A", "HDR-B"} == ids
    assert any(e["activity_id"] == "HDR-C" and "future" in e["reason"] for e in res["excluded"])
    assert abs(_sum(res) - 1.0) <= 0.0001


def test_active_siblings_share_by_remaining_quantity_and_contributions_add_up():
    actuals = {"HDR-B": {"actual_start": "2026-08-15", "actual_pct_complete": 50, "actual_quantity": 15}}
    res = allocate_split(CLAIM, MEMBERS, actuals, claim_date="2026-08-19")
    assert res["status"] == "SUCCESS"
    by = {r["activity_id"]: r for r in res["splits"]}
    assert all(r["split_basis"] == "WBS_WEIGHTED" for r in by.values())
    # A has 40 m to go, B 15 m, C 30 m -> weights follow remaining planned quantity.
    assert by["HDR-A"]["split_pct"] > by["HDR-C"]["split_pct"] > by["HDR-B"]["split_pct"]
    assert abs(sum(r["allocated_quantity"] for r in by.values()) - 12.0) < 0.01
    assert abs(_sum(res) - 1.0) <= 0.0001


def test_headroom_cap_is_respected():
    # B has only 2 m left; a 12 m claim cannot put more than 2 m on it.
    actuals = {"HDR-B": {"actual_start": "2026-08-15", "actual_pct_complete": 93, "actual_quantity": 28}}
    res = allocate_split(CLAIM, MEMBERS, actuals, claim_date="2026-08-19")
    b = next(r for r in res["splits"] if r["activity_id"] == "HDR-B")
    assert b["allocated_quantity"] <= 2.0 + 0.01
    assert abs(_sum(res) - 1.0) <= 0.0001


def test_tc_wbs_03_incompatible_uom_is_never_quantity_weighted():
    members = [
        _act("S1", "Spool 1", "2.1.1", 40, "m", "2026-08-01", "2026-08-05"),
        _act("S2", "Joint weld", "2.1.2", 24, "joints", "2026-08-01", "2026-08-05"),
    ]
    res = allocate_split({**CLAIM, "claimed_uom": "m"}, members, {}, claim_date="2026-08-03")
    assert {r["activity_id"] for r in res["splits"]} == {"S1"}
    assert any(e["activity_id"] == "S2" and "UOM" in e["reason"] for e in res["excluded"])
    # Cumulative claim across mixed UOMs: allowed, but never weighted by raw quantities.
    res2 = allocate_split({"claim_mode": "CUMULATIVE_PCT", "claimed_pct": 40}, members, {}, claim_date="2026-08-03")
    assert {r["split_basis"] for r in res2["splits"]} == {"EQUAL"}
    assert abs(_sum(res2) - 1.0) <= 0.0001


def test_fs_predecessor_gates_unstarted_successor():
    deps = [{"predecessor_activity_id": "HDR-A", "successor_activity_id": "HDR-B", "relationship_type": "FS"}]
    res = allocate_split(CLAIM, MEMBERS, {}, deps, claim_date="2026-08-19")
    ids = {r["activity_id"] for r in res["splits"]}
    assert "HDR-B" not in ids  # A incomplete, B unstarted -> gated
    # Once B has started it is no longer gated.
    started = {"HDR-B": {"actual_start": "2026-08-15", "actual_pct_complete": 10}}
    res2 = allocate_split(CLAIM, MEMBERS, started, deps, claim_date="2026-08-19")
    assert "HDR-B" in {r["activity_id"] for r in res2["splits"]}


def test_no_eligible_sibling_fails_instead_of_forcing_a_match():
    done = {a["activity_id"]: {"actual_pct_complete": 100, "actual_finish": "2026-08-19"} for a in MEMBERS}
    res = allocate_split(CLAIM, MEMBERS, done, claim_date="2026-08-19")
    assert res["status"] == "FAILED" and res["splits"] == []


def test_claim_exceeding_headroom_still_sums_to_one():
    big = {**CLAIM, "claimed_quantity": 500.0}
    res = allocate_split(big, MEMBERS, {}, claim_date="2026-08-19")
    assert res["status"] == "SUCCESS" and abs(_sum(res) - 1.0) <= 0.0001


def test_scope_classification():
    g = find_wbs_group("HDR", ACTS)
    top_summary = {"activity_id": "HDR", "match_tier": "HYBRID_FALLBACK"}
    assert classify_claim_scope({"raw_claim_text": "utility header fabrication progressing"}, g, top_summary)["claim_scope"] == "BROAD_WBS"
    assert classify_claim_scope({"raw_claim_text": "Spool Section B welded"}, g, {"activity_id": "HDR-B"})["claim_scope"] == "SPECIFIC"
    assert classify_claim_scope({"reported_activity_id": "HDR-C", "raw_claim_text": "x"}, g)["claim_scope"] == "SPECIFIC"
    assert classify_claim_scope({"reported_activity_id": "HDR", "raw_claim_text": "x"}, g)["claim_scope"] == "BROAD_WBS"
    assert classify_claim_scope({"raw_claim_text": "x"}, None)["claim_scope"] == "SPECIFIC"


def test_manual_edit_marks_only_changed_rows_and_enforces_sum():
    existing = [
        {"activity_id": "A", "split_pct": 0.5, "split_basis": "EQUAL"},
        {"activity_id": "B", "split_pct": 0.5, "split_basis": "EQUAL"},
    ]
    out = apply_manual_split_edit(existing, [{"activity_id": "A", "split_pct": 0.5}, {"activity_id": "B", "split_pct": 0.5}])
    assert {r["split_basis"] for r in out} == {"EQUAL"}  # untouched values stay as generated
    out = apply_manual_split_edit(existing, [{"activity_id": "A", "split_pct": 0.7}, {"activity_id": "B", "split_pct": 0.3}])
    assert {r["activity_id"]: r["split_basis"] for r in out} == {"A": "MANUAL", "B": "MANUAL"}
    with pytest.raises(SplitEditError):
        apply_manual_split_edit(existing, [{"activity_id": "A", "split_pct": 0.7}, {"activity_id": "B", "split_pct": 0.2}])
    with pytest.raises(SplitEditError):
        apply_manual_split_edit(existing, [{"activity_id": "ZZZ", "split_pct": 1.0}])
    out = apply_manual_split_edit(existing, [{"activity_id": "A", "split_pct": 1.0}, {"activity_id": "B", "split_pct": 0}])
    assert [r["activity_id"] for r in out] == ["A"]
