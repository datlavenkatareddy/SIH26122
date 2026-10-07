"""
verify_step4.py
Validation script for M3 Step 4 (M1 WBS-Tree Integration):
1. Matched activity with WBS code -> correct WBS code, group activities, and sibling activity IDs
2. Matched activity with NULL/missing WBS code -> safe fallback response
3. Invalid / non-existent activity or schedule ID -> returns None safely without error
4. Full Step 2 Benchmark Suite & Step 3 Contextual Gate Validation
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
    EXACT_ID,
    EXACT_ASSET,
    HYBRID_FALLBACK,
    HARD_MISMATCH,
)
from verify_step2 import test_cases as step2_test_cases, schedule_activities
from verify_step3 import step3_focused_cases

step4_test_cases = [
    {
        "id": "STEP4-001",
        "description": "Matched activity with WBS code -> returns correct WBS code and sibling IDs",
        "claim": {
            "event_id": "EVT-S4-01",
            "schedule_id": "SIH26122_NFU",
            "reported_activity_id": "PIP-PS3-WLD-024",
            "raw_claim_text": "PIP-PS3-WLD-024: Two field weld joints completed",
            "discipline": "Piping",
        },
        "expected_act": "PIP-PS3-WLD-024",
        "check_wbs": True,
    },
    {
        "id": "STEP4-002",
        "description": "Activity with NULL/missing WBS code -> safe fallback wbs_context",
        "schedule_id": "SIH26122_NFU",
        "activity_id": "NO_WBS_ACT_TEST",
        "custom_activities": [
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "NO_WBS_ACT_TEST",
                "activity_name": "Test Activity without WBS",
                "wbs_code": None,
                "discipline": "Civil",
                "location": "Pump Station 3",
            }
        ],
        "check_null_wbs": True,
    },
    {
        "id": "STEP4-003",
        "description": "Invalid / Non-existent activity ID -> returns None safely",
        "schedule_id": "SIH26122_NFU",
        "activity_id": "NON_EXISTENT_ACTIVITY_999",
        "check_invalid": True,
    },
]


def run_step4_verification():
    print("=" * 80)
    print("M3 STEP 4 WBS-TREE INTEGRATION VERIFICATION")
    print("=" * 80)

    pass_count = 0
    total_count = len(step4_test_cases) + len(step3_focused_cases) + len(step2_test_cases)

    print("\n--- Focused Step 4 WBS Integration Checks ---")
    for tc in step4_test_cases:
        if tc.get("check_wbs"):
            cands = match_claim(tc["claim"], schedule_activities)
            top = cands[0] if cands else None
            assert top is not None and top.activity_id == tc["expected_act"]

            wbs_ctx = get_wbs_context(
                tc["claim"]["schedule_id"], top.activity_id, schedule_activities
            )
            assert wbs_ctx is not None, f"{tc['id']} failed: wbs_context is None"
            assert "wbs_code" in wbs_ctx, f"{tc['id']} failed: missing wbs_code key"
            assert "wbs_group_activities" in wbs_ctx, f"{tc['id']} failed: missing wbs_group_activities"
            assert "sibling_activity_ids" in wbs_ctx, f"{tc['id']} failed: missing sibling_activity_ids"
            assert top.activity_id in wbs_ctx["wbs_group_activities"], f"{tc['id']} failed: target activity missing from group"
            assert top.activity_id not in wbs_ctx["sibling_activity_ids"], f"{tc['id']} failed: target activity found in siblings"

            print(f"Test Case: [{tc['id']}] {tc['description']}")
            print(f"  Matched Activity: {top.activity_id}")
            print(f"  WBS Code        : {wbs_ctx['wbs_code']}")
            print(f"  Group Count     : {len(wbs_ctx['wbs_group_activities'])}")
            print(f"  Sibling Count   : {len(wbs_ctx['sibling_activity_ids'])}")
            print(f"  Result          : PASS")
            print("-" * 80)
            pass_count += 1

        elif tc.get("check_null_wbs"):
            wbs_ctx = get_wbs_context(
                tc["schedule_id"], tc["activity_id"], tc["custom_activities"]
            )
            assert wbs_ctx is not None, f"{tc['id']} failed: wbs_context is None"
            assert wbs_ctx["wbs_code"] is None, f"{tc['id']} failed: wbs_code should be None"
            assert wbs_ctx["wbs_group_activities"] == [tc["activity_id"]], f"{tc['id']} failed: unexpected group activities"
            assert wbs_ctx["sibling_activity_ids"] == [], f"{tc['id']} failed: sibling_activity_ids should be empty"

            print(f"Test Case: [{tc['id']}] {tc['description']}")
            print(f"  WBS Context     : {wbs_ctx}")
            print(f"  Result          : PASS")
            print("-" * 80)
            pass_count += 1

        elif tc.get("check_invalid"):
            wbs_ctx = get_wbs_context(
                tc["schedule_id"], tc["activity_id"], schedule_activities
            )
            assert wbs_ctx is None, f"{tc['id']} failed: expected None for invalid activity, got {wbs_ctx}"

            print(f"Test Case: [{tc['id']}] {tc['description']}")
            print(f"  WBS Context     : None (Safe handling)")
            print(f"  Result          : PASS")
            print("-" * 80)
            pass_count += 1

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
            res_str = "PASS"
        else:
            res_str = "FAIL"

        print(f"Test Case: [{tc['id']}] -> {res_str}")

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
            res_str = "PASS"
        else:
            res_str = "FAIL"

        print(f"Test Case: [{tc['id']}] -> {res_str}")

    print(f"\nFINAL SUMMARY: {pass_count} / {total_count} PASSED")
    print("=" * 80)


if __name__ == "__main__":
    run_step4_verification()
