"""
verify_step5.py
Validation script for M3 Step 5 (Broad/WBS-Level Claim Detection):
1. Broad WBS-level claim with multiple siblings -> BROAD_WBS
2. Activity-specific claim -> SPECIFIC
3. Broad-looking claim with only one activity -> SPECIFIC (safe behavior)
4. No-WBS claim -> SPECIFIC (safe behavior)
5. Full Step 2 Benchmark, Step 3 Gate, and Step 4 WBS Integration Regressions
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
    EXACT_ID,
    EXACT_ASSET,
    HYBRID_FALLBACK,
    HARD_MISMATCH,
)
from verify_step2 import test_cases as step2_test_cases, schedule_activities
from verify_step3 import step3_focused_cases
from verify_step4 import step4_test_cases

step5_test_cases = [
    {
        "id": "STEP5-001",
        "description": "Broad WBS-level claim with multiple siblings -> BROAD_WBS",
        "claim": {
            "event_id": "EVT-S5-01",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "discipline": "Civil",
            "location": "Pump Station 3",
        },
        "target_act": "CIV-PS3-FND-001",
        "expected_scope": "BROAD_WBS",
    },
    {
        "id": "STEP5-002",
        "description": "Activity-specific claim -> SPECIFIC",
        "claim": {
            "event_id": "EVT-S5-02",
            "schedule_id": "SIH26122_NFU",
            "reported_activity_id": "PIP-PS3-WLD-024",
            "raw_claim_text": "PIP-PS3-WLD-024: Two field weld joints completed on utility header",
            "discipline": "Piping",
        },
        "target_act": "PIP-PS3-WLD-024",
        "expected_scope": "SPECIFIC",
    },
    {
        "id": "STEP5-003",
        "description": "Broad-looking claim with only one activity in WBS group -> SPECIFIC",
        "claim": {
            "event_id": "EVT-S5-03",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
        },
        "target_act": "SOLO_ACT_01",
        "custom_activities": [
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "SOLO_ACT_01",
                "activity_name": "Solo Civil Activity",
                "wbs_code": "SOLO_WBS_100",
                "discipline": "Civil",
                "location": "Pump Station 3",
            }
        ],
        "expected_scope": "SPECIFIC",
    },
    {
        "id": "STEP5-004",
        "description": "No-WBS claim -> SPECIFIC (safe behavior)",
        "claim": {
            "event_id": "EVT-S5-04",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
        },
        "target_act": "NO_WBS_ACT_01",
        "custom_activities": [
            {
                "schedule_id": "SIH26122_NFU",
                "activity_id": "NO_WBS_ACT_01",
                "activity_name": "Activity without WBS",
                "wbs_code": None,
                "discipline": "Civil",
                "location": "Pump Station 3",
            }
        ],
        "expected_scope": "SPECIFIC",
    },
]


def run_step5_verification():
    print("=" * 80)
    print("M3 STEP 5 BROAD/WBS-LEVEL CLAIM DETECTION VERIFICATION")
    print("=" * 80)

    pass_count = 0
    total_count = (
        len(step5_test_cases)
        + len(step4_test_cases)
        + len(step3_focused_cases)
        + len(step2_test_cases)
    )

    print("\n--- Focused Step 5 Broad Scope Detection Checks ---")
    for tc in step5_test_cases:
        acts = tc.get("custom_activities", schedule_activities)
        cands = match_claim(tc["claim"], acts)

        wbs_ctx = get_wbs_context(
            tc["claim"]["schedule_id"], tc["target_act"], acts
        )
        scope_res = detect_claim_scope(tc["claim"], wbs_ctx, cands)

        actual_scope = scope_res["claim_scope"]
        reason = scope_res["scope_reason"]

        passed = actual_scope == tc["expected_scope"]
        if passed:
            pass_count += 1
            result_str = "PASS"
        else:
            result_str = "FAIL"

        print(f"Test Case: [{tc['id']}] {tc['description']}")
        print(f"  Expected Scope: {tc['expected_scope']} | Actual Scope: {actual_scope}")
        print(f"  Scope Reason  : {reason}")
        print(f"  Result        : {result_str}")
        print("-" * 80)

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
    run_step5_verification()
