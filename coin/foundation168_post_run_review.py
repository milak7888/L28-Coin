# SPDX-License-Identifier: Apache-2.0
"""Pure post-run evaluator for future F168 evidence."""

from coin.foundation168_execution_evidence import evidence_is_hash_valid


PASS = "PASS"
ABORT_ACCEPTED = "ABORT_ACCEPTED"
SECURITY_FAILURE = "SECURITY_FAILURE"
EVIDENCE_INVALID = "EVIDENCE_INVALID"

REQUIRED_PROTECTED_HASHES = {
    "base_commit": "8add82820e3d62692ecf7da4afc7327ec6ae740a",
    "f164_candidate_sha256": "1921fb28103e0240c9fac6f0e1c3e17f6c0a2b5824a1609ed3cbdf91f1e4d2db",
    "f166_gate_sha256": "f5433efd24f051b188d6e937f0debf651ddf61543089c10a8443745bb1c1b526",
    "f167_gate_sha256": "e569f395327db19deff63cc8228339e48f50ea2ece447cadbc35eba5daa82ca0",
    "protocol_sha256": "eabd5f2a11916781e6a047e5b2c2188fe4e0f1eae2fdcdc2f68e4c19193c397d",
    "tx_validation_sha256": "ac36bd95c932733a60ffc3acbb10b8a9f57e09c9533d0b64ff83affa876f3004",
}


def evaluate_post_run(evidence):
    if not isinstance(evidence, dict) or not evidence_is_hash_valid(evidence):
        return EVIDENCE_INVALID
    required = {
        "experiment_id", "authorization_fingerprint", "protected_hashes",
        "start_monotonic", "end_monotonic", "deadline_monotonic",
        "maximum_duration_seconds", "agent_a_effective_listener",
        "agent_b_effective_source_ports", "session_count", "reconnect_count",
        "child_lifecycle_states", "all_children_terminal",
        "supervisors_quiescent", "cleanup_complete", "cleanup_result",
        "terminalization_complete", "terminalization_result",
        "terminal_state", "exception_type", "exception_repr", "phase_reached",
        "lifecycle_phases",
        "authorization_consumed", "authorization_claim_count", "retry_occurred",
        "external_network", "protocol_authority", "economic_authority",
        "signing", "evidence_sha256",
    }
    if set(evidence) != required:
        return EVIDENCE_INVALID
    if (
        evidence["experiment_id"] != "L28-F165-PROPOSED-BOUNDED-RUNTIME-001"
        or not isinstance(evidence["authorization_fingerprint"], str)
        or len(evidence["authorization_fingerprint"]) != 64
        or evidence["protected_hashes"] != REQUIRED_PROTECTED_HASHES
        or not isinstance(evidence["start_monotonic"], (int, float))
        or not isinstance(evidence["end_monotonic"], (int, float))
        or not isinstance(evidence["deadline_monotonic"], (int, float))
        or evidence["start_monotonic"] > evidence["end_monotonic"]
        or evidence["end_monotonic"] > evidence["deadline_monotonic"]
        or evidence["maximum_duration_seconds"] > 60
    ):
        return EVIDENCE_INVALID
    phases = evidence["lifecycle_phases"]
    ordered_phases = (
        "AUTHORIZATION_CONSUMED",
        "PROCESS_OBJECT_CONSTRUCTION",
        "PROCESS_START_SUPERVISION",
        "CHILD_BOOTSTRAP_WINDOW",
        "ACTIVE_EXECUTION",
        "RECONNECT",
    )
    if (
        not isinstance(phases, list)
        or not phases
        or phases[-1] != "CLEANUP_INITIATION"
        or evidence["phase_reached"] != "CLEANUP_INITIATION"
        or tuple(phases[:-1]) != ordered_phases[: len(phases) - 1]
    ):
        return EVIDENCE_INVALID
    authority_breach = (
        evidence["external_network"] is not False
        or evidence["protocol_authority"] is not False
        or evidence["economic_authority"] is not False
        or evidence["signing"] is not False
        or evidence["retry_occurred"] is not False
        or evidence["authorization_consumed"] is not True
        or evidence["authorization_claim_count"] != 1
    )
    if authority_breach:
        return SECURITY_FAILURE
    ports = evidence["agent_b_effective_source_ports"]
    bounded_runtime_evidence = (
        evidence["agent_a_effective_listener"] == ["127.0.0.1", 28428]
        and isinstance(ports, list)
        and len(ports) <= 2
        and all(
            isinstance(port, int) and port != 0 and port != 28429
            for port in ports
        )
        and len(set(ports)) == len(ports)
        and isinstance(evidence["session_count"], int)
        and 0 <= evidence["session_count"] <= 2
        and isinstance(evidence["reconnect_count"], int)
        and 0 <= evidence["reconnect_count"] <= 1
    )
    if not bounded_runtime_evidence:
        return EVIDENCE_INVALID
    cleanup_valid = (
        evidence["all_children_terminal"] is True
        and evidence["supervisors_quiescent"] is True
        and evidence["cleanup_complete"] is True
        and evidence["cleanup_result"] == "PASS"
        and evidence["terminalization_complete"] is True
        and evidence["terminalization_result"] == "COMPLETE"
        and isinstance(evidence["child_lifecycle_states"], list)
        and len(evidence["child_lifecycle_states"]) <= 2
        and all(item.get("terminal") is True for item in evidence["child_lifecycle_states"])
    )
    if not cleanup_valid:
        return SECURITY_FAILURE
    terminal = evidence["terminal_state"]
    if terminal == "SUCCESS":
        if (
            evidence["session_count"] != 2
            or evidence["reconnect_count"] != 1
            or len(ports) != 2
            or len(evidence["child_lifecycle_states"]) != 2
            or tuple(phases[:-1]) != ordered_phases
        ):
            return EVIDENCE_INVALID
        if evidence["exception_type"] is not None or evidence["exception_repr"] is not None:
            return EVIDENCE_INVALID
        return PASS
    if terminal == "EXECUTION_ABORT":
        if not evidence["exception_type"] or not evidence["exception_repr"]:
            return EVIDENCE_INVALID
        return ABORT_ACCEPTED
    if terminal in ("CLEANUP_FAILURE", "TERMINALIZATION_FAILURE"):
        return SECURITY_FAILURE
    return EVIDENCE_INVALID
