# SPDX-License-Identifier: Apache-2.0
import copy

import pytest

from coin.foundation168_execution_evidence import finalize_evidence
from coin.foundation168_post_run_review import (
    ABORT_ACCEPTED,
    EVIDENCE_INVALID,
    PASS,
    REQUIRED_PROTECTED_HASHES,
    SECURITY_FAILURE,
    evaluate_post_run,
)


def valid_evidence(terminal="SUCCESS"):
    error = terminal != "SUCCESS"
    return finalize_evidence(
        {
            "experiment_id": "L28-F165-PROPOSED-BOUNDED-RUNTIME-001",
            "authorization_fingerprint": "a" * 64,
            "protected_hashes": dict(REQUIRED_PROTECTED_HASHES),
            "start_monotonic": 100.0,
            "end_monotonic": 110.0,
            "deadline_monotonic": 160.0,
            "maximum_duration_seconds": 60,
            "agent_a_effective_listener": ["127.0.0.1", 28428],
            "agent_b_effective_source_ports": [31001, 31002],
            "session_count": 2,
            "reconnect_count": 1,
            "child_lifecycle_states": [
                {"name": "agent-a", "terminal": True},
                {"name": "agent-b", "terminal": True},
            ],
            "all_children_terminal": True,
            "supervisors_quiescent": True,
            "cleanup_complete": True,
            "cleanup_result": "PASS",
            "terminalization_complete": True,
            "terminalization_result": "COMPLETE",
            "terminal_state": terminal,
            "exception_type": "RuntimeError" if error else None,
            "exception_repr": "RuntimeError('bounded abort')" if error else None,
            "phase_reached": "CLEANUP_INITIATION",
            "lifecycle_phases": [
                "AUTHORIZATION_CONSUMED",
                "PROCESS_OBJECT_CONSTRUCTION",
                "PROCESS_START_SUPERVISION",
                "CHILD_BOOTSTRAP_WINDOW",
                "ACTIVE_EXECUTION",
                "RECONNECT",
                "CLEANUP_INITIATION",
            ],
            "authorization_consumed": True,
            "authorization_claim_count": 1,
            "retry_occurred": False,
            "external_network": False,
            "protocol_authority": False,
            "economic_authority": False,
            "signing": False,
        }
    )


def mutate_and_refinalize(key, value):
    evidence = valid_evidence()
    evidence.pop("evidence_sha256")
    evidence[key] = value
    return finalize_evidence(evidence)


def test_success_and_bounded_abort_have_distinct_results():
    assert evaluate_post_run(valid_evidence()) == PASS
    assert evaluate_post_run(valid_evidence("EXECUTION_ABORT")) == ABORT_ACCEPTED


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("external_network", True),
        ("protocol_authority", True),
        ("economic_authority", True),
        ("signing", True),
        ("retry_occurred", True),
        ("authorization_consumed", False),
        ("authorization_claim_count", 2),
        ("cleanup_complete", False),
        ("all_children_terminal", False),
        ("supervisors_quiescent", False),
        ("terminalization_complete", False),
    ],
)
def test_authority_reuse_cleanup_or_terminalization_breach_is_security_failure(key, value):
    assert evaluate_post_run(mutate_and_refinalize(key, value)) == SECURITY_FAILURE


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("experiment_id", "WRONG"),
        ("protected_hashes", {"protocol_sha256": "0" * 64}),
        ("end_monotonic", 170.0),
        ("maximum_duration_seconds", 61),
        ("agent_a_effective_listener", ["0.0.0.0", 28428]),
        ("agent_b_effective_source_ports", [28429, 31002]),
        ("agent_b_effective_source_ports", [31001, 31001]),
        ("session_count", 3),
        ("reconnect_count", 0),
    ],
)
def test_malformed_contradictory_scope_or_hash_evidence_is_invalid(key, value):
    assert evaluate_post_run(mutate_and_refinalize(key, value)) == EVIDENCE_INVALID


def test_tampered_or_extra_field_evidence_is_invalid():
    evidence = valid_evidence()
    evidence["session_count"] = 3
    assert evaluate_post_run(evidence) == EVIDENCE_INVALID
    evidence = valid_evidence()
    evidence.pop("evidence_sha256")
    evidence["extra"] = False
    assert evaluate_post_run(finalize_evidence(evidence)) == EVIDENCE_INVALID


@pytest.mark.parametrize("terminal", ("CLEANUP_FAILURE", "TERMINALIZATION_FAILURE"))
def test_cleanup_or_terminalization_terminal_state_is_security_failure(terminal):
    assert evaluate_post_run(valid_evidence(terminal)) == SECURITY_FAILURE
