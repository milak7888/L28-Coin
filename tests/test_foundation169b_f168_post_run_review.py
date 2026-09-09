# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path

from coin.foundation168_execution_evidence import evidence_is_hash_valid
from coin.foundation168_post_run_review import PASS, evaluate_post_run


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "docs/foundation169b_f168_execution_evidence_v1.0.json"
GATE_PATH = ROOT / "docs/l28_foundation169b_f168_post_run_gate_v0.1.json"
REVIEW_PATH = ROOT / "docs/foundation169b_f168_post_run_review_v1.0.md"
EXPECTED_FILE_SHA256 = "9d61a79a8761102384202c8b9700ce0e93cbfab8be7a916f5829418e55cc3c01"
EXPECTED_LIFECYCLE = [
    "AUTHORIZATION_CONSUMED",
    "PROCESS_OBJECT_CONSTRUCTION",
    "PROCESS_START_SUPERVISION",
    "CHILD_BOOTSTRAP_WINDOW",
    "ACTIVE_EXECUTION",
    "RECONNECT",
    "CLEANUP_INITIATION",
]


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, key
        result[key] = value
    return result


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_imported_evidence_file_and_embedded_hashes_are_exact():
    evidence = load_json(EVIDENCE_PATH)
    gate = load_json(GATE_PATH)
    assert sha256(EVIDENCE_PATH) == EXPECTED_FILE_SHA256
    assert gate["source_evidence"]["file_sha256"] == EXPECTED_FILE_SHA256
    assert gate["source_evidence"]["embedded_evidence_sha256"] == (
        evidence["evidence_sha256"]
    )
    assert gate["source_evidence"]["copied_without_modification"] is True
    assert evidence_is_hash_valid(evidence)


def test_unchanged_f168_post_run_evaluator_returns_pass():
    assert evaluate_post_run(load_json(EVIDENCE_PATH)) == PASS


def test_success_scope_ports_sessions_and_reconnect_are_exact():
    evidence = load_json(EVIDENCE_PATH)
    assert evidence["terminal_state"] == "SUCCESS"
    assert evidence["agent_a_effective_listener"] == ["127.0.0.1", 28428]
    ports = evidence["agent_b_effective_source_ports"]
    assert ports == [54875, 54876]
    assert all(port not in (0, 28429) for port in ports)
    assert len(set(ports)) == 2
    assert evidence["session_count"] == 2
    assert evidence["reconnect_count"] == 1
    assert evidence["maximum_duration_seconds"] == 60
    assert evidence["end_monotonic"] <= evidence["deadline_monotonic"]


def test_one_shot_consumption_no_retry_and_terminal_cleanup_are_proven():
    evidence = load_json(EVIDENCE_PATH)
    assert evidence["authorization_consumed"] is True
    assert evidence["authorization_claim_count"] == 1
    assert evidence["retry_occurred"] is False
    assert len(evidence["child_lifecycle_states"]) == 2
    assert all(child["terminal"] is True for child in evidence["child_lifecycle_states"])
    assert evidence["all_children_terminal"] is True
    assert evidence["supervisors_quiescent"] is True
    assert evidence["cleanup_complete"] is True
    assert evidence["cleanup_result"] == "PASS"
    assert evidence["terminalization_complete"] is True
    assert evidence["terminalization_result"] == "COMPLETE"


def test_lifecycle_is_complete_and_ordered():
    evidence = load_json(EVIDENCE_PATH)
    assert evidence["lifecycle_phases"] == EXPECTED_LIFECYCLE
    assert evidence["phase_reached"] == "CLEANUP_INITIATION"


def test_authority_and_external_network_firewalls_are_preserved():
    evidence = load_json(EVIDENCE_PATH)
    assert evidence["external_network"] is False
    assert evidence["protocol_authority"] is False
    assert evidence["economic_authority"] is False
    assert evidence["signing"] is False
    assert evidence["protected_hashes"]["protocol_sha256"] == sha256(
        ROOT / "PROTOCOL.md"
    )
    assert evidence["protected_hashes"]["tx_validation_sha256"] == sha256(
        ROOT / "coin/tx_validation.py"
    )


def test_gate_records_pass_consumed_non_retry_state_and_no_new_activity():
    gate = load_json(GATE_PATH)
    assert gate["post_run_state"] == {
        "F168_POST_RUN_RESULT": "PASS",
        "F168_AUTHORIZATION_CONSUMED": True,
        "F168_EXECUTION_OCCURRED": True,
        "F168_RETRY_ALLOWED": False,
        "F159_RETRY_FORBIDDEN": True,
        "authorization_claim_count": 1,
        "retry_occurred": False,
    }
    activity = gate["offline_review_activity"]
    assert not any(activity.values())
    assert gate["authority"]["settlement"] is False


def test_gate_bindings_review_and_candidate_scope_are_exact():
    gate = load_json(GATE_PATH)
    decision = gate["operator_decision_binding"]
    assert sha256(ROOT / decision["path"]) == decision["sha256"]
    assert gate["lifecycle"] == EXPECTED_LIFECYCLE
    assert gate["security_review"] == {
        "PASS": 10, "GAP": 0, "BLOCKED": 0, "COMMIT_READY": True
    }
    assert set(gate["candidate_scope"]) == {
        "docs/foundation169b_f168_execution_evidence_v1.0.json",
        "docs/foundation169b_f168_post_run_review_v1.0.md",
        "docs/l28_foundation169b_f168_post_run_gate_v0.1.json",
        "tests/test_foundation169b_f168_post_run_review.py",
    }
    review = REVIEW_PATH.read_text(encoding="utf-8")
    assert "PASS 10 / GAP 0 / BLOCKED 0" in review
