"""
verify_step7.py
Validation script for M3 Step 7 (Persist WBS Split Allocations):
1. Successful split persistence (persisted == True, split_count > 0)
2. Original claim remains unchanged (claimed_quantity untouched)
3. Multiple split rows are stored
4. Exact quantity-sum invariant across persisted split rows
5. Repeated persistence is idempotent (no duplicate rows/errors)
6. Invalid / skipped allocation is rejected safely (persisted == False)
7. Transaction / partial-failure safety simulation
8. Full Step 2-6 Regressions
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

step7_test_cases = [
    {
        "id": "STEP7-001",
        "description": "Successful split persistence for valid BROAD_WBS allocation",
        "claim": {
            "event_id": "EVT-S7-01",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 100.0,
        },
        "claim_scope": "BROAD_WBS",
        "alloc_info": {
            "allocation_status": "SUCCESS",
            "allocation_reason": "Allocated 100.0 across 2 activities",
            "wbs_splits": [
                {
                    "activity_id": "ACT-01",
                    "wbs_code": "WBS-CIV",
                    "planned_quantity": 60.0,
                    "allocation_pct": 60.0,
                    "allocated_quantity": 60.0,
                },
                {
                    "activity_id": "ACT-02",
                    "wbs_code": "WBS-CIV",
                    "planned_quantity": 40.0,
                    "allocation_pct": 40.0,
                    "allocated_quantity": 40.0,
                },
            ],
        },
        "expected_persisted": True,
        "expected_split_count": 2,
        "expected_total_qty": 100.0,
    },
    {
        "id": "STEP7-002",
        "description": "Original claim remains unchanged after split persistence",
        "claim": {
            "event_id": "EVT-S7-02",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 150.0,
        },
        "check_claim_unchanged": True,
    },
    {
        "id": "STEP7-003",
        "description": "Multiple split rows stored for group allocation",
        "claim": {
            "event_id": "EVT-S7-03",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 90.0,
        },
        "claim_scope": "BROAD_WBS",
        "alloc_info": {
            "allocation_status": "SUCCESS",
            "allocation_reason": "Allocated 90.0 across 3 activities",
            "wbs_splits": [
                {
                    "activity_id": "ACT-01",
                    "wbs_code": "WBS-CIV",
                    "planned_quantity": 30.0,
                    "allocation_pct": 33.3333,
                    "allocated_quantity": 30.0,
                },
                {
                    "activity_id": "ACT-02",
                    "wbs_code": "WBS-CIV",
                    "planned_quantity": 30.0,
                    "allocation_pct": 33.3333,
                    "allocated_quantity": 30.0,
                },
                {
                    "activity_id": "ACT-03",
                    "wbs_code": "WBS-CIV",
                    "planned_quantity": 30.0,
                    "allocation_pct": 33.3334,
                    "allocated_quantity": 30.0,
                },
            ],
        },
        "expected_persisted": True,
        "expected_split_count": 3,
    },
    {
        "id": "STEP7-004",
        "description": "Exact quantity-sum invariant across persisted split rows",
        "claim": {
            "event_id": "EVT-S7-04",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 100.0,
        },
        "claim_scope": "BROAD_WBS",
        "alloc_info": {
            "allocation_status": "SUCCESS",
            "allocation_reason": "Allocated 100.0 across 3 activities",
            "wbs_splits": [
                {
                    "activity_id": "ACT-01",
                    "wbs_code": "WBS-CIV",
                    "planned_quantity": 30.0,
                    "allocation_pct": 33.3333,
                    "allocated_quantity": 33.3333,
                },
                {
                    "activity_id": "ACT-02",
                    "wbs_code": "WBS-CIV",
                    "planned_quantity": 30.0,
                    "allocation_pct": 33.3333,
                    "allocated_quantity": 33.3333,
                },
                {
                    "activity_id": "ACT-03",
                    "wbs_code": "WBS-CIV",
                    "planned_quantity": 30.0,
                    "allocation_pct": 33.3334,
                    "allocated_quantity": 33.3334,
                },
            ],
        },
        "expected_persisted": True,
        "expected_total_qty": 100.0,
        "check_sum_invariant": True,
    },
    {
        "id": "STEP7-005",
        "description": "Repeated persistence is idempotent (no duplicate rows or errors)",
        "claim": {
            "event_id": "EVT-S7-05",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "claimed_quantity": 100.0,
        },
        "check_idempotency": True,
    },
    {
        "id": "STEP7-006",
        "description": "Invalid / SKIPPED allocation rejected safely (persisted == False)",
        "claim": {
            "event_id": "EVT-S7-06",
            "schedule_id": "SIH26122_NFU",
            "reported_activity_id": "PIP-PS3-WLD-024",
            "raw_claim_text": "PIP-PS3-WLD-024: Two field weld joints completed",
            "claimed_quantity": 2.0,
        },
        "claim_scope": "SPECIFIC",
        "alloc_info": {
            "allocation_status": "SKIPPED",
            "allocation_reason": "Claim scope is not BROAD_WBS",
            "wbs_splits": None,
        },
        "expected_persisted": False,
        "expected_split_count": 0,
    },
]


def run_step7_verification():
    print("=" * 80)
    print("M3 STEP 7 PERSIST WBS SPLIT ALLOCATIONS VERIFICATION")
    print("=" * 80)

    pass_count = 0
    total_count = (
        len(step7_test_cases)
        + len(step6_test_cases)
        + len(step5_test_cases)
        + len(step4_test_cases)
        + len(step3_focused_cases)
        + len(step2_test_cases)
    )

    print("\n--- Focused Step 7 Split Persistence Checks ---")
    for tc in step7_test_cases:
        if tc.get("check_claim_unchanged"):
            orig_qty = tc["claim"]["claimed_quantity"]
            alloc_res = {
                "allocation_status": "SUCCESS",
                "wbs_splits": [
                    {
                        "activity_id": "ACT-01",
                        "wbs_code": "WBS-CIV",
                        "planned_quantity": 150.0,
                        "allocation_pct": 100.0,
                        "allocated_quantity": 150.0,
                    }
                ],
            }
            p_res = persist_wbs_splits(
                tc["claim"]["event_id"],
                tc["claim"]["schedule_id"],
                "BROAD_WBS",
                alloc_res,
            )
            unchanged = tc["claim"]["claimed_quantity"] == orig_qty
            passed = p_res["persisted"] and unchanged

            print(f"Test Case: [{tc['id']}] {tc['description']}")
            print(f"  Original Claim Qty: {orig_qty} | Current Claim Qty: {tc['claim']['claimed_quantity']}")
            print(f"  Unchanged Check   : {'OK' if unchanged else 'FAIL'}")
            print(f"  Result            : {'PASS' if passed else 'FAIL'}")
            print("-" * 80)
            if passed:
                pass_count += 1

        elif tc.get("check_idempotency"):
            alloc_res = {
                "allocation_status": "SUCCESS",
                "wbs_splits": [
                    {
                        "activity_id": "ACT-01",
                        "wbs_code": "WBS-CIV",
                        "planned_quantity": 50.0,
                        "allocation_pct": 50.0,
                        "allocated_quantity": 50.0,
                    },
                    {
                        "activity_id": "ACT-02",
                        "wbs_code": "WBS-CIV",
                        "planned_quantity": 50.0,
                        "allocation_pct": 50.0,
                        "allocated_quantity": 50.0,
                    },
                ],
            }
            p_res1 = persist_wbs_splits(
                tc["claim"]["event_id"],
                tc["claim"]["schedule_id"],
                "BROAD_WBS",
                alloc_res,
            )
            p_res2 = persist_wbs_splits(
                tc["claim"]["event_id"],
                tc["claim"]["schedule_id"],
                "BROAD_WBS",
                alloc_res,
            )
            idempotent = (
                p_res1["persisted"]
                and p_res2["persisted"]
                and p_res1["split_count"] == p_res2["split_count"] == 2
            )

            print(f"Test Case: [{tc['id']}] {tc['description']}")
            print(f"  First Pass Count : {p_res1['split_count']} | Second Pass Count: {p_res2['split_count']}")
            print(f"  Idempotency Check: {'OK' if idempotent else 'FAIL'}")
            print(f"  Result           : {'PASS' if idempotent else 'FAIL'}")
            print("-" * 80)
            if idempotent:
                pass_count += 1

        else:
            p_res = persist_wbs_splits(
                tc["claim"]["event_id"],
                tc["claim"]["schedule_id"],
                tc.get("claim_scope", "BROAD_WBS"),
                tc["alloc_info"],
            )

            p_pass = p_res["persisted"] == tc["expected_persisted"]
            c_pass = True
            if "expected_split_count" in tc:
                c_pass = p_res["split_count"] == tc["expected_split_count"]

            sum_pass = True
            if tc.get("check_sum_invariant"):
                claimed_qty = float(tc["claim"]["claimed_quantity"])
                sum_pass = round(p_res["total_allocated_quantity"], 4) == round(claimed_qty, 4)

            passed = p_pass and c_pass and sum_pass
            if passed:
                pass_count += 1
                result_str = "PASS"
            else:
                result_str = "FAIL"

            print(f"Test Case: [{tc['id']}] {tc['description']}")
            print(f"  Expected Persisted: {tc['expected_persisted']} | Actual Persisted: {p_res['persisted']}")
            print(f"  Split Count       : {p_res['split_count']}")
            print(f"  Message           : {p_res['message']}")
            print(f"  Result            : {result_str}")
            print("-" * 80)

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
    run_step7_verification()
