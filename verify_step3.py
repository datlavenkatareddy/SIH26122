"""
verify_step3.py
Validation script for M3 Contextual Matching Gates:
1. High semantic/fuzzy + wrong discipline -> capped/rejected (UNMATCHED)
2. High semantic/fuzzy + wrong location -> capped/rejected (UNMATCHED)
3. Correct discipline + correct location -> matched (MATCHED)
4. Full Step 2 Benchmark Suite Validation
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
    EXACT_ID,
    EXACT_ASSET,
    HYBRID_FALLBACK,
    HARD_MISMATCH,
)
from verify_step2 import test_cases as step2_test_cases, schedule_activities

step3_focused_cases = [
    {
        "id": "STEP3-001",
        "description": "High Fuzzy/Semantic Text + Wrong Discipline -> Capped at <= 0.40 / Rejected",
        "claim": {
            "event_id": "EVT-S3-01",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Utility Trench Excavation CH 0+180 to CH 0+220",
            "discipline": "Piping",  # Wrong discipline for Civil activity
            "location": "Pump Station 3",
        },
        "expected_status": "UNMATCHED",
        "expected_max_confidence": 0.40,
    },
    {
        "id": "STEP3-002",
        "description": "High Fuzzy/Semantic Text + Wrong Location -> Capped at <= 0.40 / Rejected",
        "claim": {
            "event_id": "EVT-S3-02",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Place sieved sand bedding in electrical cable trench at MCC-02",
            "discipline": "Electrical",
            "location": "Substation Yard",  # Wrong location for MCC Building activity
        },
        "expected_status": "UNMATCHED",
        "expected_max_confidence": 0.40,
    },
    {
        "id": "STEP3-003",
        "description": "Correct Discipline + Correct Location -> Matched",
        "claim": {
            "event_id": "EVT-S3-03",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Place sieved sand bedding in electrical cable trench at MCC-02",
            "discipline": "Electrical",
            "location": "MCC-02",  # Correct location
        },
        "expected_status": "MATCHED",
        "expected_act": "ELE-PS3-CT-011",
    },
]


def run_step3_verification():
    print("=" * 80)
    print("M3 CONTEXTUAL MATCHING GATES VERIFICATION (Step 3)")
    print("=" * 80)

    pass_count = 0
    total_count = len(step3_focused_cases) + len(step2_test_cases)

    print("\n--- Focused Step 3 Contextual Gate Checks ---")
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

        status_pass = actual_status == tc["expected_status"]
        conf_pass = True
        if "expected_max_confidence" in tc:
            conf_pass = confidence <= tc["expected_max_confidence"]

        act_pass = True
        if "expected_act" in tc:
            act_pass = actual_act == tc["expected_act"]

        # Explicit assertions for STEP3-001 and STEP3-002
        if tc["id"] in ["STEP3-001", "STEP3-002"]:
            assert actual_status == "UNMATCHED", f"{tc['id']} failed: expected status UNMATCHED, got {actual_status}"
            assert confidence <= 0.40, f"{tc['id']} failed: expected confidence <= 0.40, got {confidence}"

        passed = status_pass and conf_pass and act_pass
        if passed:
            pass_count += 1
            result_str = "PASS"
        else:
            result_str = "FAIL"

        print(f"Test Case: [{tc['id']}] {tc['description']}")
        print(
            f"  Expected Status : {tc['expected_status']} | Actual Status : {actual_status}"
        )
        print(f"  Confidence Score: {confidence:.4f} (<= 0.40 Capped Assert: {'OK' if confidence <= 0.40 else 'FAIL'})")
        print(f"  Result          : {result_str}")
        print("-" * 80)

    print("\n--- Step 2 Benchmark Suite Validation ---")
    for tc in step2_test_cases:
        cands = match_claim(tc["claim"], schedule_activities)
        top = cands[0] if cands else None

        actual_tier = top.match_tier if top else "NONE"
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

        status_pass = actual_status == tc["expected_status"]
        act_pass = actual_act == tc["expected_act"]

        passed = status_pass and act_pass
        if passed:
            pass_count += 1
            result_str = "PASS"
        else:
            result_str = "FAIL"

        print(
            f"Test Case: [{tc['id']}] {tc['description']} -> {result_str} (Conf: {confidence:.4f})"
        )

    print(f"\nFINAL SUMMARY: {pass_count} / {total_count} PASSED")
    print("=" * 80)


if __name__ == "__main__":
    run_step3_verification()
