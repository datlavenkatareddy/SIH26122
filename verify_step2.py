"""
verify_step2.py
Manual evaluation script for M3 matching against the 45-activity canonical benchmark
and challenge scenarios (identical activity names in different locations, discipline mismatch,
location aliases, WBS-level/broad claims, terminology variation).
"""

import csv
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load project's .env file before importing backend modules
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

# 1. Load canonical 45-activity schedule
SCHEDULE_PATH = Path("sample_data/canonical/schedule.csv")
schedule_activities = []

if SCHEDULE_PATH.exists():
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            schedule_activities.append(
                {
                    "schedule_id": "SIH26122_NFU",
                    "activity_id": row["Activity_ID"],
                    "activity_name": row["Activity_Name"],
                    "wbs_code": row.get("WBS"),
                    "parent_id": row.get("Parent_ID"),
                    "discipline": row["Discipline"],
                    "location": row["Location"],
                    "asset_tag": row.get("Asset_Tag"),
                    "planned_quantity": float(row["Planned_Quantity"]) if row.get("Planned_Quantity") and str(row.get("Planned_Quantity")).strip() else None,
                }
            )

# 2. Define benchmark and challenge test cases
test_cases = [
    # --- 5 Canonical Benchmark Cases ---
    {
        "id": "MATCH-001",
        "description": "Exact ID Match",
        "claim": {
            "event_id": "EVT-TEST-M01",
            "schedule_id": "SIH26122_NFU",
            "reported_activity_id": "PIP-PS3-WLD-024",
            "raw_claim_text": "PIP-PS3-WLD-024: Two field weld joints completed on utility header",
            "discipline": "Piping",
        },
        "expected_tier": EXACT_ID,
        "expected_act": "PIP-PS3-WLD-024",
        "expected_status": "MATCHED",
    },
    {
        "id": "MATCH-002",
        "description": "Asset Tag Match (P-102 with Piping discipline)",
        "claim": {
            "event_id": "EVT-TEST-M02",
            "schedule_id": "SIH26122_NFU",
            "asset_tag": "P-102",
            "raw_claim_text": "P-102 discharge line welding completed.",
            "discipline": "Piping",
        },
        "expected_tier": EXACT_ASSET,
        "expected_act": "PIP-PS3-WLD-024",
        "expected_status": "MATCHED",
    },
    {
        "id": "MATCH-003",
        "description": "Semantic / Description Match",
        "claim": {
            "event_id": "EVT-TEST-M03",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Two field weld joints completed on utility header.",
            "discipline": "Piping",
        },
        "expected_tier": HYBRID_FALLBACK,
        "expected_act": "PIP-PS3-WLD-024",
        "expected_status": "MATCHED",
    },
    {
        "id": "MATCH-004",
        "description": "Ambiguous Claim (Overlapping Trench Sections)",
        "claim": {
            "event_id": "EVT-TEST-M04",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Utility trench excavation from approximately CH 0+200 to CH 0+240 completed.",
            "discipline": "Civil",
            "location": "Pump Station 3",
        },
        "expected_tier": HYBRID_FALLBACK,
        "expected_act": None,
        "expected_status": "UNMATCHED",
    },
    {
        "id": "MATCH-005",
        "description": "Unmatched Out-of-Scope Claim",
        "claim": {
            "event_id": "EVT-TEST-M05",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Temporary rain shelter installed at laydown area.",
            "discipline": "General Works",
        },
        "expected_tier": HYBRID_FALLBACK,
        "expected_act": None,
        "expected_status": "UNMATCHED",
    },
    # --- 5 Specific Challenge Scenarios ---
    {
        "id": "CHALLENGE-001",
        "description": "Identical Activity Names in Different Locations (MCC-02 vs MCC-01)",
        "claim": {
            "event_id": "EVT-CH-01",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Place sieved sand bedding in electrical cable trench at MCC-02",
            "discipline": "Electrical",
            "location": "MCC-02",
        },
        "expected_tier": HYBRID_FALLBACK,
        "expected_act": "ELE-PS3-CT-011",
        "expected_status": "MATCHED",
    },
    {
        "id": "CHALLENGE-002",
        "description": "Discipline Mismatch (Claim Piping vs Activity Civil)",
        "claim": {
            "event_id": "EVT-CH-02",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Utility Trench Excavation CH 0+180 to CH 0+220",
            "discipline": "Piping",
            "location": "Pump Station 3",
        },
        "expected_tier": HARD_MISMATCH,
        "expected_act": None,
        "expected_status": "UNMATCHED",
    },
    {
        "id": "CHALLENGE-003",
        "description": "Location Alias (PS3 -> Pump Station 3)",
        "claim": {
            "event_id": "EVT-CH-03",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Submersible dewatering pump relocation after water ingress",
            "discipline": "Static/Rotating Equipment",
            "location": "PS3",
        },
        "expected_tier": HYBRID_FALLBACK,
        "expected_act": "MECH-PS3-DWP-003",
        "expected_status": "MATCHED",
    },
    {
        "id": "CHALLENGE-004",
        "description": "Broad / WBS-Level Claim",
        "claim": {
            "event_id": "EVT-CH-04",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "General civil works in progress across pump station area",
            "discipline": "Civil",
            "location": "Pump Station 3",
        },
        "expected_tier": HYBRID_FALLBACK,
        "expected_act": None,
        "expected_status": "UNMATCHED",
    },
    {
        "id": "CHALLENGE-005",
        "description": "Terminology Variation (rebar & formwork vs reinforcement)",
        "claim": {
            "event_id": "EVT-CH-05",
            "schedule_id": "SIH26122_NFU",
            "raw_claim_text": "Reinforcement steel fixing and shuttering for crude pump foundation",
            "discipline": "Civil",
            "location": "Pump Station 3",
        },
        "expected_tier": HYBRID_FALLBACK,
        "expected_act": "CIV-PS3-FND-002",
        "expected_status": "MATCHED",
    },
]


def run_evaluation():
    print("=" * 80)
    print(
        "M3 MATCHING CONTRACT BENCHMARK & CALIBRATION EVALUATION (45 Activities)"
    )
    print("=" * 80)

    pass_count = 0
    total_count = len(test_cases)

    for tc in test_cases:
        cands = match_claim(tc["claim"], schedule_activities)
        top = cands[0] if cands else None

        actual_tier = top.match_tier if top else "NONE"
        confidence = top.composite_confidence if top else 0.0

        is_ambiguous = False
        if (
            cands
            and cands[0].match_tier == HYBRID_FALLBACK
            and len(cands) >= 2
        ):
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

        tier_pass = actual_tier == tc["expected_tier"]
        status_pass = actual_status == tc["expected_status"]
        act_pass = actual_act == tc["expected_act"]

        passed = status_pass and act_pass
        if passed:
            pass_count += 1
            result_str = "PASS"
        else:
            result_str = "FAIL"

        print(f"Test Case: [{tc['id']}] {tc['description']}")
        print(
            f"  Expected Tier   : {tc['expected_tier']} | Actual Tier   : {actual_tier}"
        )
        print(
            f"  Expected Status : {tc['expected_status']} | Actual Status : {actual_status}"
        )
        print(
            f"  Expected Act ID : {tc['expected_act']} | Actual Act ID : {actual_act}"
        )
        print(f"  Confidence Score: {confidence:.4f}")
        print(f"  Result          : {result_str}")
        print("-" * 80)

    print(f"\nFINAL SUMMARY: {pass_count} / {total_count} PASSED")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()
