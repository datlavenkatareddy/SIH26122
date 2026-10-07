"""
Unit tests for shared/llm_extraction.py: error-handling contract (a genuine
failure raises LLMExtractionError, never silently degrades to a null
claim), batch-response parsing, and vision-model configuration. Tests that
need a real model response make real calls against the configured
LLM_PROVIDER (this project's dev key), matching the rest of the test suite's
existing approach (see test_m2_intake.py) rather than mocking the provider.
"""
import pytest

from backend.shared import llm_extraction
from backend.shared.llm_extraction import (
    LLMExtractionError,
    _parse_batch_response,
    extract_claim_fields,
    extract_claim_fields_batch,
    extract_claim_fields_from_image_batch,
)


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


def test_parse_batch_response_wrapped_array():
    resp = _parse_batch_response('{"claims": [{"action": "did a thing"}, {"action": "did another"}]}')
    assert len(resp) == 2
    assert resp[0].action == "did a thing"


def test_parse_batch_response_empty_array_is_not_an_error():
    """A model that ran successfully and found nothing returns an empty
    list -- that's a legitimate outcome, not a parse failure."""
    resp = _parse_batch_response('{"claims": []}')
    assert resp == []


def test_parse_batch_response_bare_object_tolerated_as_one_item_batch():
    """Some models omit the {"claims": [...]} wrapper for a single result
    despite the prompt -- tolerate it as a 1-item batch rather than
    raising, since that's strictly more useful."""
    resp = _parse_batch_response('{"action": "did a thing"}')
    assert len(resp) == 1
    assert resp[0].action == "did a thing"


def test_parse_batch_response_empty_string_raises():
    with pytest.raises(LLMExtractionError):
        _parse_batch_response("")


def test_parse_batch_response_invalid_json_raises():
    with pytest.raises(LLMExtractionError):
        _parse_batch_response("not json at all {{{")


def test_parse_batch_response_claims_not_a_list_raises():
    with pytest.raises(LLMExtractionError):
        _parse_batch_response('{"claims": "not a list"}')


def test_parse_batch_response_invalid_claim_shape_raises():
    """A claim with a field value outside its enum (e.g. an invalid
    discipline) is a genuine malformed-response failure, not something to
    silently drop or null out."""
    with pytest.raises(LLMExtractionError):
        _parse_batch_response('{"claims": [{"discipline": "NOT_A_REAL_DISCIPLINE"}]}')


def test_extract_claim_fields_raises_on_client_failure(monkeypatch):
    """A genuine failure building the LLM client (bad/missing config,
    network error) must raise LLMExtractionError -- the original bug being
    fixed here is this silently returning ExtractedClaimFields() instead."""
    def _broken(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(llm_extraction, "_get_client", _broken)
    with pytest.raises(LLMExtractionError):
        extract_claim_fields("Excavation completed 100%")


def test_extract_claim_fields_batch_raises_on_client_failure(monkeypatch):
    def _broken(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(llm_extraction, "_get_client", _broken)
    with pytest.raises(LLMExtractionError):
        extract_claim_fields_batch("Excavation completed 100%")


def test_extract_claim_fields_raises_on_empty_response(monkeypatch):
    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return _FakeResponse("")

    monkeypatch.setattr(llm_extraction, "_get_client", lambda: _FakeClient())
    with pytest.raises(LLMExtractionError):
        extract_claim_fields("some text")


def test_extract_claim_fields_raises_on_malformed_json(monkeypatch):
    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return _FakeResponse("{not valid json")

    monkeypatch.setattr(llm_extraction, "_get_client", lambda: _FakeClient())
    with pytest.raises(LLMExtractionError):
        extract_claim_fields("some text")


def test_missing_api_key_raises_clearly(monkeypatch):
    """Missing configuration must fail visibly and specifically -- not as
    a generic exception, and not as a silently-empty claim."""
    from backend.shared import llm_client

    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(llm_client, "_client", None)
    # Prevent the shared client from reloading a real key from .env for this test.
    monkeypatch.setattr(llm_client, "_load_env_if_needed", lambda: None)
    with pytest.raises(LLMExtractionError, match="LLM_API_KEY"):
        extract_claim_fields("some text")


def test_unknown_provider_raises_clearly(monkeypatch):
    from backend.shared import llm_client

    monkeypatch.setattr(llm_client, "_client", None)
    monkeypatch.setenv("LLM_PROVIDER", "not-a-real-provider")
    monkeypatch.setenv("LLM_API_KEY", "dummy-key-for-this-test")
    try:
        with pytest.raises(LLMExtractionError, match="Unknown LLM_PROVIDER"):
            extract_claim_fields("some text")
    finally:
        monkeypatch.setattr(llm_client, "_client", None)


def test_vision_extraction_raises_clearly_when_no_vision_model_configured(monkeypatch):
    """Groq (this project's default configured provider) has no
    vision-capable model on the configured key at the time this was
    written -- calling the vision path without LLM_VISION_MODEL set must
    fail with an actionable message, not silently return an empty/null
    result or crash with an unrelated error."""
    monkeypatch.delenv("LLM_VISION_MODEL", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    with pytest.raises(LLMExtractionError, match="vision"):
        extract_claim_fields_from_image_batch(b"fake image bytes", mime_type="image/png")


def _skip_on_quota_exhaustion(exc: LLMExtractionError):
    """
    These two tests make real calls against the configured LLM provider
    (this project's free-tier Groq key, shared across the whole test
    suite/session). A provider-side rate/quota limit is an infrastructure
    condition of the moment, not a defect in this code -- skip rather than
    fail so a temporarily-exhausted free-tier quota doesn't look like a
    regression. Anything else (bad response shape, config error) still
    fails normally.
    """
    msg = str(exc).lower()
    if "rate_limit" in msg or "rate limit" in msg or "429" in msg:
        pytest.skip(f"LLM provider quota/rate limit hit (infra, not a code issue): {exc}")
    raise exc


@pytest.mark.live_llm
def test_batch_extraction_real_multi_activity_text():
    """Real-model smoke test: a genuinely multi-activity report must
    produce one claim per activity, not collapse them into one (the
    core bug this batch contract exists to fix)."""
    text = (
        "Daily Progress Report - 14 Aug 2026\n"
        "CIV-PS3-TR-0180 | Civil | Excavate utility trench | 100.0% | Complete\n"
        "PIP-PS3-WLD-024 | Piping | Complete field weld joints | 91.7% | Ongoing\n"
    )
    try:
        claims = extract_claim_fields_batch(text)
    except LLMExtractionError as e:
        _skip_on_quota_exhaustion(e)
        return
    assert len(claims) == 2
    ids = {c.reported_activity_id for c in claims}
    assert ids == {"CIV-PS3-TR-0180", "PIP-PS3-WLD-024"}


@pytest.mark.live_llm
def test_batch_extraction_real_irrelevant_text_returns_empty():
    """Genuinely content-free/irrelevant text should come back as an empty
    list (model ran fine, nothing to extract) rather than an error or a
    fabricated claim."""
    try:
        claims = extract_claim_fields_batch("asdkjfh qwerty lorem ipsum nothing relevant here")
    except LLMExtractionError as e:
        _skip_on_quota_exhaustion(e)
        return
    assert claims == []
