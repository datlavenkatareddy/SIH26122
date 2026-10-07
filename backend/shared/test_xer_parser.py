"""
Unit tests for the Primavera P6 .xer parser (shared/xer_parser.py).
Includes both hand-built fixtures (exercising specific edge cases) and the
real sample_data/input/schedule-xer/sih26122_schedule.xer export.
"""
from pathlib import Path

import pytest

from backend.shared.xer_parser import (
    XERParseError,
    activities_with_progress,
    build_claim_from_activity,
    extract_activities,
    parse_xer_tables,
)

_REAL_XER = (
    Path(__file__).resolve().parents[2]
    / "sample_data" / "input" / "schedule-xer" / "sih26122_schedule.xer"
)

_MINIMAL_XER = (
    "ERMHDR\t19.12\t2026-08-10\tProject\tadmin\tPlanner\tPROJ\tUSD\tDD/MM/YYYY\t1\t0\t0\n"
    "%T\tPROJWBS\n"
    "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name\n"
    "%R\t100\t1\t\t1\tCivil Works\n"
    "%R\t101\t1\t100\t1.01\tSubcivil\n"
    "%T\tTASK\n"
    "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\tstatus_code\ttarget_start_date\ttarget_end_date\n"
    "%R\t2001\t1\t101\tCIV-A\tExcavate trench\tTT_Task\tTK_Complete\t2026-08-14 08:00\t2026-08-14 18:00\n"
    "%R\t2002\t1\t101\tCIV-B\tPour foundation\tTT_Task\tTK_Active\t2026-08-15 08:00\t2026-08-16 18:00\n"
    "%R\t2003\t1\t101\tCIV-C\tNot started yet\tTT_Task\tTK_NotStart\t2026-08-20 08:00\t2026-08-21 18:00\n"
).encode("utf-8")


def test_parse_xer_tables_extracts_stacked_tables():
    tables = parse_xer_tables(_MINIMAL_XER)
    assert set(tables) == {"PROJWBS", "TASK"}
    assert tables["TASK"].fields == [
        "task_id", "proj_id", "wbs_id", "task_code", "task_name", "task_type",
        "status_code", "target_start_date", "target_end_date",
    ]
    assert len(tables["TASK"].rows) == 3
    assert tables["TASK"].rows[0]["task_code"] == "CIV-A"


def test_xer_is_not_treated_as_csv():
    """A real XER's raw bytes would misparse badly as CSV (tab-delimited,
    variable column counts per table, %T/%F/%R control lines mixed with
    data) -- this just documents that parse_xer_tables produces the CORRECT
    structured result rather than garbage, as the strongest evidence this
    isn't reusing a generic delimited-text parser."""
    tables = parse_xer_tables(_MINIMAL_XER)
    # A CSV reader would see the %T/%F/%R prefix as just another column;
    # the real parser must not treat those lines as TASK data rows.
    task_codes = [row.get("task_code") for row in tables["TASK"].rows]
    assert "%F" not in task_codes and "%T" not in task_codes
    assert all(code in ("CIV-A", "CIV-B", "CIV-C") for code in task_codes)


def test_missing_ermhdr_raises():
    with pytest.raises(XERParseError):
        parse_xer_tables(b"not an xer file\njust some text\n")


def test_missing_task_table_raises():
    no_task = (
        "ERMHDR\t19.12\t2026-08-10\tProject\tadmin\tPlanner\tPROJ\tUSD\tDD/MM/YYYY\t1\t0\t0\n"
        "%T\tPROJECT\n"
        "%F\tproj_id\tproj_short_name\n"
        "%R\t1\tPROJ\n"
    ).encode("utf-8")
    with pytest.raises(XERParseError):
        parse_xer_tables(no_task)


def test_activities_with_progress_excludes_not_started():
    activities = extract_activities(_MINIMAL_XER)
    assert len(activities) == 3
    progressed = activities_with_progress(activities)
    assert {a.activity_id for a in progressed} == {"CIV-A", "CIV-B"}
    assert "CIV-C" not in {a.activity_id for a in progressed}


def test_discipline_resolved_from_wbs_hierarchy():
    """CIV-A/CIV-B sit under wbs_id=101 ("Subcivil"), whose PARENT
    (wbs_id=100, "Civil Works") is what actually names a discipline --
    verifies the resolver walks up the WBS chain rather than only checking
    the activity's immediate parent."""
    activities = extract_activities(_MINIMAL_XER)
    assert all(a.discipline == "CIVIL" for a in activities)


def test_build_claim_from_activity_complete():
    activities = extract_activities(_MINIMAL_XER)
    by_id = {a.activity_id: a for a in activities}
    raw_text, extracted = build_claim_from_activity(by_id["CIV-A"])
    assert extracted.reported_activity_id == "CIV-A"
    assert extracted.claimed_pct == 100.0
    assert extracted.discipline.value == "CIVIL"
    assert extracted.event_type.value == "ACTUAL_FINISH"
    assert "CIV-A" in raw_text


def test_build_claim_from_activity_active_no_pct():
    """An active-but-not-yet-complete activity with no phys_complete_pct
    field in this export legitimately has no percentage to report -- must
    stay null, not be guessed at."""
    activities = extract_activities(_MINIMAL_XER)
    by_id = {a.activity_id: a for a in activities}
    _, extracted = build_claim_from_activity(by_id["CIV-B"])
    assert extracted.claimed_pct is None
    assert extracted.event_type.value == "PROGRESS_UPDATE"


def test_encoding_fallback_cp1252():
    """A byte sequence that isn't valid UTF-8 but IS valid cp1252 (common
    for P6 exports from non-English Windows locales) must still parse."""
    xer_with_latin1_byte = (
        "ERMHDR\t19.12\t2026-08-10\tProject\tadmin\tPlanner\tPROJ\tUSD\tDD/MM/YYYY\t1\t0\t0\n"
        "%T\tTASK\n"
        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\tstatus_code\n"
        "%R\t2001\t1\t100\tCIV-A\tCaf\xe9 site office\tTK_Complete\n"
    ).encode("cp1252")
    activities = extract_activities(xer_with_latin1_byte)
    assert activities[0].activity_name == "Café site office"


@pytest.mark.skipif(not _REAL_XER.exists(), reason="real sample XER not present")
def test_real_sample_xer_end_to_end():
    contents = _REAL_XER.read_bytes()
    activities = extract_activities(contents)
    assert len(activities) == 45
    progressed = activities_with_progress(activities)
    assert len(progressed) == 44  # one TK_NotStart activity excluded
    assert all(a.discipline is not None for a in progressed), "every real activity should resolve a discipline via WBS"

    ids = {a.activity_id for a in activities}
    assert "CIV-PS3-TR-0180" in ids
    assert "PIP-PS3-WLD-024" in ids

    by_id = {a.activity_id: a for a in progressed}
    raw_text, extracted = build_claim_from_activity(by_id["CIV-PS3-TR-0180"])
    assert extracted.reported_activity_id == "CIV-PS3-TR-0180"
    assert extracted.claimed_pct == 100.0
    assert extracted.discipline.value == "CIVIL"
