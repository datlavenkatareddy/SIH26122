"""
verify_step6.py
Validation script for M3 Step 6 (Deterministic WBS Split Allocation):
1. Proportional allocation for BROAD_WBS claims
2. Exact sum invariant & rounding/remainder handling
3. NULL planned quantity exclusion
4. Zero / invalid planned quantities handling (allocation failure)
5. No eligible activities handling (allocation failure)
6. Non-BROAD_WBS claim skips allocation (allocation_status == SKIPPED)
7. Full Step 2-5 Regressions
"""

import csv
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load project environment variables
load_dotenv()

# Ensure backend can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.routers.matching import (
    match_claim,
    get_wbs_context,
    detect_claim_scope,
    allocate_wbs_splits,
    EXACT_ID,
    EXACT_ASSET,
    HYBRID_FALLBACK,
    HARD_MISMATCH,
)
from verify_step2 import test_cases as step2_test_cases, schedule_activities
from verify_step3 import step3_focused_cases
from verify_step4 import step4_test_cases
from verify_step5 import step5_test_cases

step6_test_cases = [
    {
        "id": "STEP6-001",
        "description": "Proportional allocation across eligible activities for BROAD_WBS claim",
        "claim": {
            "event_id": "EVT-S6-01",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 100.0,
        },
        "claim_scope": "BROAD_WBS",
        "wbs_context": {
            "wbs_code": "WBS-CIV",
            "wbs_group_activities": ["ACT-01", "ACT-02"],
            "sibling_activity_ids": ["ACT-02"],
        },
        "custom_activities": [
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "ACT-01",
                "wbs_code": "WBS-CIV",
                "planned_quantity": 60.0,
            },
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "ACT-02",
                "wbs_code": "WBS-CIV",
                "planned_quantity": 40.0,
            },
        ],
        "expected_status": "SUCCESS",
        "expected_split_count": 2,
        "expected_allocations": {"ACT-01": 60.0, "ACT-02": 40.0},
    },
    {
        "id": "STEP6-002",
        "description": "Exact sum invariant & rounding remainder handling",
        "claim": {
            "event_id": "EVT-S6-02",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 100.0,
        },
        "claim_scope": "BROAD_WBS",
        "wbs_context": {
            "wbs_code": "WBS-CIV",
            "wbs_group_activities": ["ACT-01", "ACT-02", "ACT-03"],
            "sibling_activity_ids": ["ACT-02", "ACT-03"],
        },
        "custom_activities": [
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "ACT-01",
                "wbs_code": "WBS-CIV",
                "planned_quantity": 30.0,
            },
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "ACT-02",
                "wbs_code": "WBS-CIV",
                "planned_quantity": 30.0,
            },
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "ACT-03",
                "wbs_code": "WBS-CIV",
                "planned_quantity": 30.0,
            },
        ],
        "expected_status": "SUCCESS",
        "expected_split_count": 3,
        "check_exact_sum": True,
    },
    {
        "id": "STEP6-003",
        "description": "Exclusion of NULL planned quantity activity",
        "claim": {
            "event_id": "EVT-S6-03",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 50.0,
        },
        "claim_scope": "BROAD_WBS",
        "wbs_context": {
            "wbs_code": "WBS-CIV",
            "wbs_group_activities": ["ACT-VALID", "ACT-NULL"],
            "sibling_activity_ids": ["ACT-NULL"],
        },
        "custom_activities": [
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "ACT-VALID",
                "wbs_code": "WBS-CIV",
                "planned_quantity": 50.0,
            },
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "ACT-NULL",
                "wbs_code": "WBS-CIV",
                "planned_quantity": None,
            },
        ],
        "expected_status": "SUCCESS",
        "expected_split_count": 1,
        "expected_allocations": {"ACT-VALID": 50.0},
    },
    {
        "id": "STEP6-004",
        "description": "Zero / invalid planned quantities -> FAILED allocation",
        "claim": {
            "event_id": "EVT-S6-04",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 50.0,
        },
        "claim_scope": "BROAD_WBS",
        "wbs_context": {
            "wbs_code": "WBS-CIV",
            "wbs_group_activities": ["ACT-ZERO-1", "ACT-ZERO-2"],
            "sibling_activity_ids": ["ACT-ZERO-2"],
        },
        "custom_activities": [
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "ACT-ZERO-1",
                "wbs_code": "WBS-CIV",
                "planned_quantity": 0.0,
            },
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "ACT-ZERO-2",
                "wbs_code": "WBS-CIV",
                "planned_quantity": 0.0,
            },
        ],
        "expected_status": "FAILED",
        "expected_split_count": 0,
    },
    {
        "id": "STEP6-005",
        "description": "No eligible activities in WBS group -> FAILED allocation",
        "claim": {
            "event_id": "EVT-S6-05",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 50.0,
        },
        "claim_scope": "BROAD_WBS",
        "wbs_context": {
            "wbs_code": "WBS-EMPTY",
            "wbs_group_activities": [],
            "sibling_activity_ids": [],
        },
        "custom_activities": [],
        "expected_status": "FAILED",
        "expected_split_count": 0,
    },
    {
        "id": "STEP6-006",
        "description": "Non-BROAD_WBS claim (SPECIFIC) -> SKIPPED allocation",
        "claim": {
            "event_id": "EVT-S6-06",
            "schedule_id": "SIH26122_NFU",
            "reported_activity_id": "PIP-PS3-WLD-024",
            "raw_claim_text": "PIP-PS3-WLD-024: Two field weld joints completed",
            "claimed_quantity": 2.0,
        },
        "claim_scope": "SPECIFIC",
        "wbs_context": {
            "wbs_code": "WBS-PIP",
            "wbs_group_activities": ["PIP-PS3-WLD-024"],
            "sibling_activity_ids": [],
        },
        "custom_activities": [
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "PIP-PS3-WLD-024",
                "wbs_code": "WBS-PIP",
                "planned_quantity": 24.0,
            }
        ],
        "expected_status": "SKIPPED",
        "expected_split_count": 0,
    },
]


def run_step6_verification():
    print("=" * 80)
    print("M3 STEP 6 DETERMINISTIC WBS SPLIT ALLOCATION VERIFICATION")
    print("=" * 80)

    pass_count = 0
    total_count = (
        len(step6_test_cases)
        + len(step5_test_cases)
        + len(step4_test_cases)
        + len(step3_focused_cases)
        + len(step2_test_cases)
    )

    print("\n--- Focused Step 6 Split Allocation Checks ---")
    for tc in step6_test_cases:
        acts = tc.get("custom_activities", schedule_activities)
        alloc_res = allocate_wbs_splits(
            tc["claim"], tc["claim_scope"], tc["wbs_context"], acts
        )

        actual_status = alloc_res["allocation_status"]
        reason = alloc_res["allocation_reason"]
        splits = alloc_res["wbs_splits"]

        status_pass = actual_status == tc["expected_status"]
        count_pass = True
        if tc["expected_split_count"] > 0:
            count_pass = splits is not None and len(splits) == tc["expected_split_count"]
        else:
            count_pass = splits is None or len(splits) == 0

        alloc_pass = True
        if "expected_allocations" in tc and splits:
            actual_map = {s["activity_id"]: s["allocated_quantity"] for s in splits}
            alloc_pass = actual_map == tc["expected_allocations"]

        sum_pass = True
        if tc.get("check_exact_sum") and splits:
            claimed_qty = float(tc["claim"]["claimed_quantity"])
            allocated_sum = sum(s["allocated_quantity"] for s in splits)
            sum_pass = round(allocated_sum, 4) == round(claimed_qty, 4)

        passed = status_pass and count_pass and alloc_pass and sum_pass
        if passed:
            pass_count += 1
            result_str = "PASS"
        else:
            result_str = "FAIL"

        print(f"Test Case: [{tc['id']}] {tc['description']}")
        print(f"  Expected Status: {tc['expected_status']} | Actual Status: {actual_status}")
        print(f"  Split Count    : {len(splits) if splits else 0}")
        print(f"  Reason         : {reason}")
        if tc.get("check_exact_sum") and splits:
            allocated_sum = sum(s["allocated_quantity"] for s in splits)
            print(f"  Exact Sum Check: {allocated_sum} == {tc['claim']['claimed_quantity']} ({'OK' if sum_pass else 'FAIL'})")
        print(f"  Result         : {result_str}")
        print("-" * 80)

    print("\n--- Step 5 Integration Regression ---")
    for tc in step5_test_cases:
        acts = tc.get("custom_activities", schedule_activities)
        cands = match_claim(tc["claim"], acts)
        wbs_ctx = get_wbs_context(tc["claim"]["schedule_id"], tc["target_act"], acts)
        scope_res = detect_claim_scope(tc["claim"], wbs_ctx, cands)
        passed = scope_res["claim_scope"] == tc["expected_scope"]

        if passed:
            pass_count += 1
            print(f"Test Case: [{tc['id']}] -> PASS")
        else:
            print(f"Test Case: [{tc['id']}] -> FAIL")

    print("\n--- Step 4 Integration Regression ---")
    for tc in step4_test_cases:
        if tc.get("check_wbs"):
            cands = match_claim(tc["claim"], schedule_activities)
            top = cands[0] if cands else None
            wbs_ctx = get_wbs_context(tc["claim"]["schedule_id"], top.activity_id, schedule_activities)
            scope_res = detect_claim_scope(tc["claim"], wbs_ctx, cands)
            passed = top is not None and wbs_ctx is not None and scope_res["claim_scope"] == "SPECIFIC"
        elif tc.get("check_null_wbs"):
            wbs_ctx = get_wbs_context(tc["schedule_id"], tc["activity_id"], tc["custom_activities"])
            scope_res = detect_claim_scope({"raw_claim_text": "Test"}, wbs_ctx)
            passed = wbs_ctx is not None and scope_res["claim_scope"] == "SPECIFIC"
        elif tc.get("check_invalid"):
            wbs_ctx = get_wbs_context(tc["schedule_id"], tc["activity_id"], schedule_activities)
            scope_res = detect_claim_scope({"raw_claim_text": "Test"}, wbs_ctx)
            passed = wbs_ctx is None and scope_res["claim_scope"] == "SPECIFIC"
        else:
            passed = True

        if passed:
            pass_count += 1
            print(f"Test Case: [{tc['id']}] -> PASS")
        else:
            print(f"Test Case: [{tc['id']}] -> FAIL")

    print("\n--- Step 3 Focused Checks Regression ---")
    for tc in step3_focused_cases:
        cands = match_claim(tc["claim"], schedule_activities)
        top = cands[0] if cands else None
        confidence = top.composite_confidence if top else 0.0

        is_ambiguous = False
        if cands and cands[0].match_tier == HYBRID_FALLBACK and len(cands) >= 2:
            diff = cands[0].composite_confidence - cands[1].composite_confidence
            if diff < 0.05:
                is_ambiguous = True

        if (
            top
            and top.match_tier in [EXACT_ID, EXACT_ASSET, HYBRID_FALLBACK]
            and top.composite_confidence > 0.40
            and not is_ambiguous
        ):
            actual_status = "MATCHED"
            actual_act = top.activity_id
        else:
            actual_status = "UNMATCHED"
            actual_act = None

        passed = actual_status == tc["expected_status"]
        if "expected_max_confidence" in tc:
            passed = passed and confidence <= tc["expected_max_confidence"]
        if "expected_act" in tc:
            passed = passed and actual_act == tc["expected_act"]

        if passed:
            pass_count += 1
            print(f"Test Case: [{tc['id']}] -> PASS")
        else:
            print(f"Test Case: [{tc['id']}] -> FAIL")

    print("\n--- Step 2 Benchmark Suite Regression ---")
    for tc in step2_test_cases:
        cands = match_claim(tc["claim"], schedule_activities)
        top = cands[0] if cands else None

        is_ambiguous = False
        if cands and cands[0].match_tier == HYBRID_FALLBACK and len(cands) >= 2:
            diff = cands[0].composite_confidence - cands[1].composite_confidence
            if diff < 0.05:
                is_ambiguous = True

        if (
            top
            and top.match_tier in [EXACT_ID, EXACT_ASSET, HYBRID_FALLBACK]
            and top.composite_confidence > 0.40
            and not is_ambiguous
        ):
            actual_status = "MATCHED"
            actual_act = top.activity_id
        else:
            actual_status = "UNMATCHED"
            actual_act = None

        passed = (actual_status == tc["expected_status"]) and (actual_act == tc["expected_act"])
        if passed:
            pass_count += 1
            print(f"Test Case: [{tc['id']}] -> PASS")
        else:
            print(f"Test Case: [{tc['id']}] -> FAIL")

    print(f"\nFINAL SUMMARY: {pass_count} / {total_count} PASSED")
    print("=" * 80)


if __name__ == "__main__":
    run_step6_verification()
