"""Deterministic extraction fallback (PRD v6 Section 21) -- no network, no database."""
import pytest

from backend.shared import llm_extraction
from backend.shared.rule_extraction import extract_with_rules


def test_rules_extract_quantity_claim():
    c = extract_with_rules("Utility header fabrication progressing, 12 m completed across the header sections at Pump Station 3")
    assert c.discipline.value == "PIPING"
    assert c.claim_mode.value == "INCREMENTAL_QUANTITY" and c.claimed_quantity == 12 and c.claimed_uom == "m"
    assert c.event_type.value == "PROGRESS_UPDATE" and c.language_detected == "English"


def test_rules_extract_percentage_and_id():
    c = extract_with_rules("CIV-PS3-FND-002 rebar and formwork 60% complete")
    assert c.claimed_pct == 60 and c.reported_activity_id == "CIV-PS3-FND-002" and c.discipline.value == "CIVIL"


def test_rules_leave_gaps_instead_of_guessing():
    c = extract_with_rules("some work happened today")
    assert c.discipline is None and c.claimed_pct is None and c.claimed_quantity is None


def test_script_language_detection():
    assert extract_with_rules("పైపింగ్ 40% పూర్తి").language_detected == "Telugu"
    assert extract_with_rules("पाइपिंग 40% पूर्ण").language_detected == "Hindi"


def test_fallback_is_opt_in(monkeypatch):
    def boom():
        raise llm_extraction.LLMExtractionError("provider down")
    monkeypatch.setattr(llm_extraction, "_get_client", boom)
    monkeypatch.delenv("EXTRACTION_FALLBACK", raising=False)
    with pytest.raises(llm_extraction.LLMExtractionError):
        llm_extraction.extract_claim_fields("pump 50% done")
    monkeypatch.setenv("EXTRACTION_FALLBACK", "rules")
    assert llm_extraction.extract_claim_fields("pump 50% done").claimed_pct == 50
    assert len(llm_extraction.extract_claim_fields_batch("pump 50% done")) == 1
