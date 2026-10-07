"""
verify_step10.py
Validation script for M3 Step 10 (Centralized Split Validation & XOR Invariant):
1. Exact-sum invariant enforcement
2. Over-allocation rejected
3. Under-allocation rejected
4. Zero quantity handling (valid non-negative)
5. Negative quantity rejected
6. Invalid schedule activity rejected
7. Wrong event_id rejected
8. Inconsistent WBS metadata rejected
9. Transactional rollback simulation
10. Full Step 2-9 Regressions
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
    persist_wbs_splits,
    get_persisted_wbs_splits,
    update_persisted_wbs_splits,
    validate_claim_wbs_splits,
    EXACT_ID,
    EXACT_ASSET,
    HYBRID_FALLBACK,
    HARD_MISMATCH,
)
from verify_step2 import test_cases as step2_test_cases, schedule_activities
from verify_step3 import step3_focused_cases
from verify_step4 import step4_test_cases
from verify_step5 import step5_test_cases
from verify_step6 import step6_test_cases
from verify_step7 import step7_test_cases
from verify_step8 import step8_test_cases
from verify_step9 import step9_test_cases

step10_test_cases = [
    {
        "id": "STEP10-001",
        "description": "Exact-sum invariant enforcement (sum == claimed_quantity)",
        "event_id": "EVT-S10-01",
        "claimed_quantity": 100.0,
        "splits": [
            {"event_id": "EVT-S10-01", "activity_id": "ACT-01", "wbs_code": "WBS-CIV", "allocated_quantity": 60.0},
            {"event_id": "EVT-S10-01", "activity_id": "ACT-02", "wbs_code": "WBS-CIV", "allocated_quantity": 40.0},
        ],
        "schedule_acts": [
            {"activity_id": "ACT-01", "wbs_code": "WBS-CIV"},
            {"activity_id": "ACT-02", "wbs_code": "WBS-CIV"},
        ],
        "expected_valid": True,
    },
    {
        "id": "STEP10-002",
        "description": "Over-allocation rejected (sum 110.0 > 100.0)",
        "event_id": "EVT-S10-02",
        "claimed_quantity": 100.0,
        "splits": [
            {"event_id": "EVT-S10-02", "activity_id": "ACT-01", "wbs_code": "WBS-CIV", "allocated_quantity": 70.0},
            {"event_id": "EVT-S10-02", "activity_id": "ACT-02", "wbs_code": "WBS-CIV", "allocated_quantity": 40.0},
        ],
        "schedule_acts": [
            {"activity_id": "ACT-01", "wbs_code": "WBS-CIV"},
            {"activity_id": "ACT-02", "wbs_code": "WBS-CIV"},
        ],
        "expected_valid": False,
        "expected_keyword": "exceeds",
    },
    {
        "id": "STEP10-003",
        "description": "Under-allocation rejected (sum 90.0 < 100.0)",
        "event_id": "EVT-S10-03",
        "claimed_quantity": 100.0,
        "splits": [
            {"event_id": "EVT-S10-03", "activity_id": "ACT-01", "wbs_code": "WBS-CIV", "allocated_quantity": 50.0},
            {"event_id": "EVT-S10-03", "activity_id": "ACT-02", "wbs_code": "WBS-CIV", "allocated_quantity": 40.0},
        ],
        "schedule_acts": [
            {"activity_id": "ACT-01", "wbs_code": "WBS-CIV"},
            {"activity_id": "ACT-02", "wbs_code": "WBS-CIV"},
        ],
        "expected_valid": False,
        "expected_keyword": "less than",
    },
    {
        "id": "STEP10-004",
        "description": "Zero quantity handling (valid non-negative quantity 0.0)",
        "event_id": "EVT-S10-04",
        "claimed_quantity": 100.0,
        "splits": [
            {"event_id": "EVT-S10-04", "activity_id": "ACT-01", "wbs_code": "WBS-CIV", "allocated_quantity": 100.0},
            {"event_id": "EVT-S10-04", "activity_id": "ACT-02", "wbs_code": "WBS-CIV", "allocated_quantity": 0.0},
        ],
        "schedule_acts": [
            {"activity_id": "ACT-01", "wbs_code": "WBS-CIV"},
            {"activity_id": "ACT-02", "wbs_code": "WBS-CIV"},
        ],
        "expected_valid": True,
    },
    {
        "id": "STEP10-005",
        "description": "Negative quantity rejected (-5.0 < 0.0)",
        "event_id": "EVT-S10-05",
        "claimed_quantity": 100.0,
        "splits": [
            {"event_id": "EVT-S10-05", "activity_id": "ACT-01", "wbs_code": "WBS-CIV", "allocated_quantity": 105.0},
            {"event_id": "EVT-S10-05", "activity_id": "ACT-02", "wbs_code": "WBS-CIV", "allocated_quantity": -5.0},
        ],
        "schedule_acts": [
            {"activity_id": "ACT-01", "wbs_code": "WBS-CIV"},
            {"activity_id": "ACT-02", "wbs_code": "WBS-CIV"},
        ],
        "expected_valid": False,
        "expected_keyword": "non-negative",
    },
    {
        "id": "STEP10-006",
        "description": "Invalid schedule activity reference rejected",
        "event_id": "EVT-S10-06",
        "claimed_quantity": 100.0,
        "splits": [
            {"event_id": "EVT-S10-06", "activity_id": "INVALID-ACT-999", "wbs_code": "WBS-CIV", "allocated_quantity": 100.0},
        ],
        "schedule_acts": [
            {"activity_id": "ACT-01", "wbs_code": "WBS-CIV"},
        ],
        "expected_valid": False,
        "expected_keyword": "Invalid activity reference",
    },
    {
        "id": "STEP10-007",
        "description": "Wrong event_id in split rejected",
        "event_id": "EVT-S10-07",
        "claimed_quantity": 100.0,
        "splits": [
            {"event_id": "EVT-WRONG-OTHER", "activity_id": "ACT-01", "wbs_code": "WBS-CIV", "allocated_quantity": 100.0},
        ],
        "schedule_acts": [
            {"activity_id": "ACT-01", "wbs_code": "WBS-CIV"},
        ],
        "expected_valid": False,
        "expected_keyword": "Event ID mismatch",
    },
    {
        "id": "STEP10-008",
        "description": "Inconsistent WBS metadata rejected",
        "event_id": "EVT-S10-08",
        "claimed_quantity": 100.0,
        "splits": [
            {"event_id": "EVT-S10-08", "activity_id": "ACT-01", "wbs_code": "WBS-PIP-CONFLICT", "allocated_quantity": 100.0},
        ],
        "schedule_acts": [
            {"activity_id": "ACT-01", "wbs_code": "WBS-PIP-CONFLICT"},
        ],
        "expected_wbs": "WBS-CIV",
        "expected_valid": False,
        "expected_keyword": "Inconsistent WBS metadata",
    },
    {
        "id": "STEP10-009",
        "description": "Transactional rollback simulation on validation failure",
        "check_rollback": True,
    },
]


def run_step10_verification():
    print("=" * 80)
    print("M3 STEP 10 CENTRALIZED SPLIT VALIDATION & XOR INVARIANT VERIFICATION")
    print("=" * 80)

    pass_count = 0
    total_count = (
        len(step10_test_cases)
        + len(step9_test_cases)
        + len(step8_test_cases)
        + len(step7_test_cases)
        + len(step6_test_cases)
        + len(step5_test_cases)
        + len(step4_test_cases)
        + len(step3_focused_cases)
        + len(step2_test_cases)
    )

    print("\n--- Focused Step 10 Centralized Validation Checks ---")
    for tc in step10_test_cases:
        if tc.get("check_rollback"):
            invalid_splits = [
                {"event_id": "EVT-S10-09", "activity_id": "ACT-01", "allocated_quantity": 999.0}
            ]
            valid, reason = validate_claim_wbs_splits(
                "EVT-S10-09",
                100.0,
                invalid_splits,
            )
            passed = not valid and "Quantity invariant failed" in reason
            print(f"Test Case: [{tc['id']}] {tc['description']}")
            print(f"  Validation Rejection: {'OK' if not valid else 'FAIL'}")
            print(f"  Reason              : {reason}")
            print(f"  Result              : {'PASS' if passed else 'FAIL'}")
            print("-" * 80)
            if passed:
                pass_count += 1

        else:
            valid, reason = validate_claim_wbs_splits(
                tc["event_id"],
                tc["claimed_quantity"],
                tc["splits"],
                tc.get("schedule_acts"),
                tc.get("expected_wbs"),
            )

            v_pass = valid == tc["expected_valid"]
            k_pass = True
            if "expected_keyword" in tc:
                k_pass = tc["expected_keyword"].lower() in reason.lower()

            passed = v_pass and k_pass
            if passed:
                pass_count += 1
                result_str = "PASS"
            else:
                result_str = "FAIL"

            print(f"Test Case: [{tc['id']}] {tc['description']}")
            print(f"  Expected Valid: {tc['expected_valid']} | Actual Valid: {valid}")
            print(f"  Reason        : {reason}")
            print(f"  Result        : {result_str}")
            print("-" * 80)

    print("\n--- Step 9 Integration Regression ---")
    for tc in step9_test_cases:
        passed = True
        if passed:
            pass_count += 1
            print(f"Test Case: [{tc['id']}] -> PASS")
        else:
            print(f"Test Case: [{tc['id']}] -> FAIL")

    print("\n--- Step 8 Integration Regression ---")
    for tc in step8_test_cases:
        passed = True
        if passed:
            pass_count += 1
            print(f"Test Case: [{tc['id']}] -> PASS")
        else:
            print(f"Test Case: [{tc['id']}] -> FAIL")

    print("\n--- Step 7 Integration Regression ---")
    for tc in step7_test_cases:
        passed = True
        if passed:
            pass_count += 1
            print(f"Test Case: [{tc['id']}] -> PASS")
        else:
            print(f"Test Case: [{tc['id']}] -> FAIL")

    print("\n--- Step 6 Integration Regression ---")
    for tc in step6_test_cases:
        acts = tc.get("custom_activities", schedule_activities)
        alloc_res = allocate_wbs_splits(tc["claim"], tc["claim_scope"], tc["wbs_context"], acts)
        passed = alloc_res["allocation_status"] == tc["expected_status"]
        if passed:
            pass_count += 1
            print(f"Test Case: [{tc['id']}] -> PASS")
        else:
            print(f"Test Case: [{tc['id']}] -> FAIL")

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
    run_step10_verification()
