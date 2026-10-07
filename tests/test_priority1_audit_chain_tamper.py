import copy
import hashlib
import pytest
from backend.shared.audit import (
    GENESIS_HASH,
    compute_hash,
    payload_hash,
    verify_audit_chain,
    canonical_json,
)


def _build_audit_sequence():
    """
    Construct a real 3-entry audit sequence with authentic cryptographic linkage.
    ENTRY 1 (Genesis linked) -> ENTRY 2 -> ENTRY 3.
    """
    entries = []

    # Entry 1
    before_1 = None
    after_1 = {"status": "EXTRACTED", "pct": 10.0}
    p_hash_1 = payload_hash(before_1, after_1)
    prev_1 = GENESIS_HASH
    curr_1 = compute_hash(
        entity_type="execution_event",
        entity_id="EVT-001",
        action="CREATE",
        actor_id="USER-1",
        before_state=before_1,
        after_state=after_1,
        payload_hash=p_hash_1,
        previous_hash=prev_1,
    )
    entries.append({
        "log_id": 1,
        "entity_type": "execution_event",
        "entity_id": "EVT-001",
        "action": "CREATE",
        "actor_id": "USER-1",
        "before_state": None,
        "after_state": canonical_json(after_1),
        "payload_hash": p_hash_1,
        "previous_hash": prev_1,
        "current_hash": curr_1,
    })

    # Entry 2
    before_2 = after_1
    after_2 = {"status": "VALIDATED", "pct": 10.0}
    p_hash_2 = payload_hash(before_2, after_2)
    prev_2 = curr_1
    curr_2 = compute_hash(
        entity_type="execution_event",
        entity_id="EVT-001",
        action="VALIDATE",
        actor_id="SYSTEM",
        before_state=before_2,
        after_state=after_2,
        payload_hash=p_hash_2,
        previous_hash=prev_2,
    )
    entries.append({
        "log_id": 2,
        "entity_type": "execution_event",
        "entity_id": "EVT-001",
        "action": "VALIDATE",
        "actor_id": "SYSTEM",
        "before_state": canonical_json(before_2),
        "after_state": canonical_json(after_2),
        "payload_hash": p_hash_2,
        "previous_hash": prev_2,
        "current_hash": curr_2,
    })

    # Entry 3
    before_3 = after_2
    after_3 = {"status": "APPROVED", "pct": 10.0, "decision": "APPROVE"}
    p_hash_3 = payload_hash(before_3, after_3)
    prev_3 = curr_2
    curr_3 = compute_hash(
        entity_type="execution_event",
        entity_id="EVT-001",
        action="APPROVE",
        actor_id="SUPERVISOR-9",
        before_state=before_3,
        after_state=after_3,
        payload_hash=p_hash_3,
        previous_hash=prev_3,
    )
    entries.append({
        "log_id": 3,
        "entity_type": "execution_event",
        "entity_id": "EVT-001",
        "action": "APPROVE",
        "actor_id": "SUPERVISOR-9",
        "before_state": canonical_json(before_3),
        "after_state": canonical_json(after_3),
        "payload_hash": p_hash_3,
        "previous_hash": prev_3,
        "current_hash": curr_3,
    })

    return entries


def test_audit_01_valid_sequence_passes():
    """Authentic, untampered sequence passes full verification."""
    logs = _build_audit_sequence()
    is_valid, reason = verify_audit_chain(logs)
    assert is_valid is True
    assert reason is None


def test_audit_02_payload_tamper_detected():
    """Tampering with before_state or after_state fails verification."""
    logs = _build_audit_sequence()
    # Maliciously alter after_state in Entry 2
    logs[1]["after_state"] = '{"status":"VALIDATED","pct":999.0}'
    is_valid, reason = verify_audit_chain(logs)
    assert is_valid is False
    assert "Payload hash mismatch" in reason


def test_audit_03_payload_hash_tamper_detected():
    """Tampering with payload_hash fails verification."""
    logs = _build_audit_sequence()
    logs[1]["payload_hash"] = "deadbeef" * 8
    is_valid, reason = verify_audit_chain(logs)
    assert is_valid is False
    assert "Payload hash mismatch" in reason


def test_audit_04_current_hash_tamper_detected():
    """Tampering with current_hash fails verification."""
    logs = _build_audit_sequence()
    logs[1]["current_hash"] = "baadc0de" * 8
    is_valid, reason = verify_audit_chain(logs)
    assert is_valid is False
    assert "Current hash mismatch" in reason


def test_audit_05_previous_hash_tamper_detected():
    """Tampering with previous_hash breaks chain linkage and is detected."""
    logs = _build_audit_sequence()
    logs[2]["previous_hash"] = "0" * 64
    is_valid, reason = verify_audit_chain(logs)
    assert is_valid is False
    assert "Chain linkage violation" in reason


def test_audit_06_genesis_tamper_detected():
    """Tampering with the root genesis hash is detected."""
    logs = _build_audit_sequence()
    logs[0]["previous_hash"] = "1" * 64
    is_valid, reason = verify_audit_chain(logs)
    assert is_valid is False
    assert "Genesis/start linkage violation" in reason


def test_audit_07_chain_ordering_tamper_detected():
    """Swapping the order of entries in the chain violates sequence ordering and is detected."""
    logs = _build_audit_sequence()
    # Swap Entry 2 and Entry 3
    swapped = [logs[0], logs[2], logs[1]]
    is_valid, reason = verify_audit_chain(swapped)
    assert is_valid is False
    # Linkage or sequence violation is detected
    assert "Chain linkage violation" in reason or "Sequence order violation" in reason


def test_audit_08_metadata_tamper_detected():
    """Tampering with action or actor_id is detected via current_hash recomputation."""
    logs = _build_audit_sequence()
    logs[2]["actor_id"] = "IMPOSTOR-42"
    is_valid, reason = verify_audit_chain(logs)
    assert is_valid is False
    assert "Current hash mismatch" in reason
