# SPDX-License-Identifier: Apache-2.0
"""Fail-closed offline evaluator for the F165 operator decision package."""


READY = "READY_FOR_OPERATOR_AUTHORIZATION_DECISION"
NOT_READY = "NOT_READY"
BLOCKED = "BLOCKED"

PROPOSED_EXPERIMENT_ID = "L28-F165-PROPOSED-BOUNDED-RUNTIME-001"
REQUIRED_SOURCE_BINDINGS = {
    "F160": "408fe4264253a2940b93a051cdace49fda325019c8178def003ff695632e23d5",
    "F161": "24e839fc0707c64ea4c0d957730368bb404e1f45b16d842cd383d1ba76de0e8c",
    "F162": "112008e5b4fc2d14b0b7239038f21006493f668ffff21f224e2633377bc8c8fc",
    "F163": "6322cbfca6260e36e445c8f110f420be2b161168e2e234ebcecbac50e56b4985",
    "F164": "a05dd02527b2cd20ca1636ec2a6b48c62719957a32140f55a83ceb3f6ab788e6",
}
DEADLINE_COVERAGE = (
    "PROCESS_OBJECT_CONSTRUCTION",
    "PROCESS_START_SUPERVISION",
    "CHILD_BOOTSTRAP_WINDOW",
    "ACTIVE_EXECUTION",
    "CLEANUP_INITIATION",
)
TERMINAL_STATES = (
    "SUCCESS",
    "EXECUTION_ABORT",
    "CLEANUP_FAILURE",
    "TERMINALIZATION_FAILURE",
)
EXPECTED_SCOPE = {
    "disposable": True,
    "isolated": True,
    "agent_count": 2,
    "child_process_count": 2,
    "network_family": "IPv4_LOOPBACK_ONLY",
    "external_network_allowed": False,
    "agent_a_listener": ("127.0.0.1", 28428),
    "agent_b_bind": ("127.0.0.1", 0),
    "fixed_client_source_port_28429_forbidden": True,
    "session_count": 2,
    "reconnect_count": 1,
    "maximum_duration_seconds": 60,
    "deadline_kind": "ONE_SINGLE_BOUNDED_DEADLINE",
    "deadline_coverage": DEADLINE_COVERAGE,
    "strong_parent_resource_ownership_required": True,
    "parent_ownership_contracts": ("F160", "F161"),
    "provenance_freeze_security_contracts": ("F162", "F163"),
    "f164_candidate_required": True,
    "f164_candidate_activating": False,
    "cleanup_requires_all_children_terminal": True,
    "cleanup_requires_all_supervisors_quiescent": True,
    "terminal_states": TERMINAL_STATES,
}

EXPECTED_AUTHORITY = {
    "NEW_AUTHORIZATION_REQUIRED": True,
    "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
    "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
    "F159_RETRY_FORBIDDEN": True,
    "OLD_AUTHORIZATION_REUSABLE": False,
    "F165_AUTHORIZATION_GRANTED": False,
    "F165_EXECUTION_AUTHORIZED": False,
}

PROTECTED_AUTHORITY_KEYS = (
    "issuance",
    "supply",
    "height",
    "validation",
    "consensus",
    "history",
    "ledger",
    "settlement",
    "signing",
    "wallet",
    "bitcoin_authority",
)


def _result(status, reasons):
    return {
        "status": status,
        "reasons": tuple(reasons),
        "ready_for_operator_authorization_decision": status == READY,
        "authorization_granted": False,
        "execution_authorized": False,
        "execution_invocation_present": False,
    }


def evaluate_runtime_authorization_decision(package_snapshot, evidence):
    """Evaluate consideration readiness without granting any authority."""

    if not isinstance(package_snapshot, dict) or not isinstance(evidence, dict):
        return _result(BLOCKED, ("MALFORMED_DECISION_INPUT",))

    blocked = []
    not_ready = []
    required_snapshot_false = (
        "authorization_granted",
        "execution_authorized",
        "execution_invocation_present",
        "consumed",
        "reusable",
        "f159_authorization_reusable",
    )
    if package_snapshot.get("package_configured") is not True:
        not_ready.append("PACKAGE_NOT_CONFIGURED")
    if package_snapshot.get("proposed_experiment_id") != PROPOSED_EXPERIMENT_ID:
        blocked.append("PROPOSED_EXPERIMENT_ID_MISMATCH")
    if package_snapshot.get("scope") != EXPECTED_SCOPE:
        blocked.append("RUNTIME_SCOPE_NOT_EXACT")
    if any(package_snapshot.get(key) is not False for key in required_snapshot_false):
        blocked.append("PACKAGE_AUTHORITY_CONTRADICTION")

    bindings = package_snapshot.get("source_bindings")
    if not isinstance(bindings, dict):
        blocked.append("SOURCE_BINDINGS_MALFORMED")
    else:
        for foundation in ("F160", "F161", "F162", "F163", "F164"):
            if foundation not in bindings:
                blocked.append("MISSING_" + foundation + "_BINDING")
            elif bindings[foundation] != REQUIRED_SOURCE_BINDINGS[foundation]:
                blocked.append(foundation + "_BINDING_MISMATCH")

    if evidence.get("f164_security_review") != {
        "PASS": 13,
        "GAP": 0,
        "BLOCKED": 0,
    }:
        blocked.append("F164_SECURITY_REVIEW_NOT_PASS")
    if evidence.get("authority") != EXPECTED_AUTHORITY:
        blocked.append("AUTHORIZATION_FIREWALL_CONTRADICTION")
    if evidence.get("single_deadline_contract_complete") is not True:
        blocked.append("DEADLINE_CONTRACT_INCOMPLETE")
    if evidence.get("cleanup_contract_complete") is not True:
        blocked.append("CLEANUP_CONTRACT_INCOMPLETE")
    if evidence.get("terminalization_contract_complete") is not True:
        blocked.append("TERMINALIZATION_CONTRACT_INCOMPLETE")
    protected = evidence.get("protected_authority")
    if (
        not isinstance(protected, dict)
        or set(protected) != set(PROTECTED_AUTHORITY_KEYS)
        or any(protected.get(key) is not False for key in PROTECTED_AUTHORITY_KEYS)
    ):
        blocked.append("PROTECTED_AUTHORITY_FIREWALL_BROKEN")
    if evidence.get("protocol_hash_valid") is not True:
        blocked.append("PROTOCOL_BINDING_INVALID")
    if evidence.get("validator_hash_valid") is not True:
        blocked.append("VALIDATOR_BINDING_INVALID")
    if evidence.get("capability_firewall_valid") is not True:
        blocked.append("CAPABILITY_FIREWALL_BROKEN")
    if evidence.get("historical_f159_state_valid") is not True:
        blocked.append("F159_HISTORY_OR_NON_REUSE_INVALID")

    if blocked:
        return _result(BLOCKED, blocked)
    if not_ready:
        return _result(NOT_READY, not_ready)
    return _result(READY, ("OFFLINE_PACKAGE_READY_FOR_OPERATOR_CONSIDERATION_ONLY",))
