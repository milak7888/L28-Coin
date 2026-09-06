# SPDX-License-Identifier: Apache-2.0
"""Deterministic offline evaluator for future live-adapter review readiness."""


READY = "READY_FOR_FUTURE_LIVE_ADAPTER_IMPLEMENTATION_REVIEW"
NOT_READY = "NOT_READY"
BLOCKED = "BLOCKED"
RESOURCE_CONTRACT_READY = "RESOURCE_CONTRACT_READY_FOR_IMPLEMENTATION_REVIEW"

LIFECYCLE_PHASES = (
    "PROCESS_OBJECT_CONSTRUCTION",
    "PROCESS_START_SUPERVISION",
    "CHILD_BOOTSTRAP_WINDOW",
    "ACTIVE_EXECUTION",
    "CLEANUP_UNTIL_ALL_CHILDREN_TERMINAL",
    "RELEASED",
)
DEADLINE_COVERAGE = (
    "RESOURCE_CONSTRUCTION",
    "STARTUP_SUPERVISION",
    "CHILD_BOOTSTRAP",
    "ACTIVE_WORK",
    "CLEANUP_INITIATION",
)
DEADLINE_DESCRIPTOR = (
    "SINGLE_BOUNDED_DEADLINE_DATA_ONLY",
    DEADLINE_COVERAGE,
    ("bounded", True),
    ("timer_implemented", False),
)
TERMINAL_STATES = (
    "SUCCESS",
    "EXECUTION_ABORT",
    "CLEANUP_FAILURE",
    "TERMINALIZATION_FAILURE",
)
DIMENSIONS = (
    "A_RESOURCE_PROVENANCE",
    "B_PARENT_OWNERSHIP",
    "C_LIFECYCLE_ORDERING",
    "D_STARTUP_PRECONDITIONS",
    "E_BOOTSTRAP_RETENTION",
    "F_DEADLINE_COVERAGE",
    "G_FAILURE_PROPAGATION",
    "H_CLEANUP_TERMINALIZATION",
    "I_AUTHORIZATION_SEPARATION",
    "J_PROTOCOL_AUTHORITY_FIREWALL",
    "K_CAPABILITY_FIREWALL",
    "L_HISTORICAL_PRESERVATION",
    "M_LIVE_IMPLEMENTATION_REVIEW_READINESS",
)

REQUIRED_AUTHORITY = {
    "NEW_AUTHORIZATION_REQUIRED": True,
    "SEPARATE_SECURITY_REVIEW_REQUIRED": True,
    "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
    "F159_RETRY_FORBIDDEN": True,
    "F157_F158_F159_CONSUMPTION_STATE_REUSABLE": False,
    "F161_EXECUTION_AUTHORIZED": False,
    "F162_EXECUTION_AUTHORIZED": False,
    "F163_EXECUTION_AUTHORIZED": False,
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

F163_EXECUTION_AUTHORIZED = False


def _dimension(result, evidence):
    return {"result": result, "evidence": evidence}


def evaluate_live_adapter_readiness(state):
    """Evaluate design-review readiness without creating executable authority."""

    if not isinstance(state, dict):
        state = {}
    dimensions = {}
    contract = state.get("resource_contract")
    resource_ready = (
        contract is not None
        and getattr(contract, "frozen", False) is True
        and getattr(contract, "provenance_verified", False) is True
        and getattr(contract, "execution_authorized", True) is False
        and getattr(contract, "readiness_code", None) == RESOURCE_CONTRACT_READY
        and state.get("resource_provenance_valid") is True
    )
    dimensions[DIMENSIONS[0]] = _dimension(
        "PASS" if resource_ready else NOT_READY,
        "COMPLETE_FROZEN_EXACT_RESOURCE_CONTRACT"
        if resource_ready
        else "RESOURCE_PROVENANCE_INCOMPLETE_OR_INVALID",
    )

    ownership_ready = (
        resource_ready
        and state.get("parent_ownership_valid") is True
        and getattr(contract, "lifecycle_owner", None) is not None
        and getattr(contract, "boundary", None) is not None
        and getattr(contract.boundary, "lifecycle_helper", None)
        is contract.lifecycle_owner
    )
    dimensions[DIMENSIONS[1]] = _dimension(
        "PASS" if ownership_ready else NOT_READY,
        "F161_PARENT_OWNERSHIP_BOUND_TO_F162"
        if ownership_ready
        else "PARENT_OWNERSHIP_NOT_PROVEN",
    )

    lifecycle_ready = state.get("lifecycle_phases") == LIFECYCLE_PHASES
    dimensions[DIMENSIONS[2]] = _dimension(
        "PASS" if lifecycle_ready else NOT_READY,
        "EXACT_ORDERED_F160_F161_F162_PHASES"
        if lifecycle_ready
        else "LIFECYCLE_ORDERING_INVALID",
    )

    startup_ready = (
        resource_ready
        and ownership_ready
        and state.get("startup_preconditions_valid") is True
        and getattr(contract.boundary, "hypothetical_start_eligible", False) is True
        and getattr(contract.boundary, "execution_authorized", True) is False
    )
    dimensions[DIMENSIONS[3]] = _dimension(
        "PASS" if startup_ready else NOT_READY,
        "HYPOTHETICAL_ELIGIBILITY_DATA_ONLY"
        if startup_ready
        else "STARTUP_PRECONDITIONS_INCOMPLETE",
    )

    retention_ready = state.get("bootstrap_retention_valid") is True
    dimensions[DIMENSIONS[4]] = _dimension(
        "PASS" if retention_ready else NOT_READY,
        "READY_RESULT_CHILD_SUPERVISOR_RETENTION_REQUIRED"
        if retention_ready
        else "BOOTSTRAP_RETENTION_NOT_PROVEN",
    )

    deadline_ready = (
        state.get("single_deadline_required") is True
        and state.get("deadline_coverage") == DEADLINE_COVERAGE
        and contract is not None
        and getattr(contract, "deadline_descriptor", None) == DEADLINE_DESCRIPTOR
    )
    dimensions[DIMENSIONS[5]] = _dimension(
        "PASS" if deadline_ready else NOT_READY,
        "SINGLE_BOUNDED_DEADLINE_CONSTRUCTION_THROUGH_CLEANUP_INITIATION"
        if deadline_ready
        else "DEADLINE_COVERAGE_INCOMPLETE",
    )

    failure_ready = state.get("failure_preserves_parent_ownership") is True
    dimensions[DIMENSIONS[6]] = _dimension(
        "PASS" if failure_ready else NOT_READY,
        "FAIL_CLOSED_AND_RETAIN_FOR_CLEANUP"
        if failure_ready
        else "FAILURE_PROPAGATION_CONTRACT_INCOMPLETE",
    )

    terminal_states = state.get("terminal_states")
    cleanup_ready = (
        state.get("cleanup_contract_valid") is True
        and terminal_states == TERMINAL_STATES
        and len(set(terminal_states or ())) == len(TERMINAL_STATES)
    )
    dimensions[DIMENSIONS[7]] = _dimension(
        "PASS" if cleanup_ready else NOT_READY,
        "F161_RELEASE_PREDICATES_AND_DISTINCT_TERMINAL_STATES"
        if cleanup_ready
        else "CLEANUP_OR_TERMINALIZATION_INCOMPLETE",
    )

    authority = state.get("authority", {})
    authority_ready = authority == REQUIRED_AUTHORITY
    dimensions[DIMENSIONS[8]] = _dimension(
        "PASS" if authority_ready else BLOCKED,
        "ALL_EXECUTION_AUTHORITY_FALSE_AND_NEW_REVIEW_REQUIRED"
        if authority_ready
        else "AUTHORIZATION_FIREWALL_CONTRADICTION",
    )

    protected = state.get("protected_authority", {})
    protected_authority_ready = (
        isinstance(protected, dict)
        and
        set(protected) == set(PROTECTED_AUTHORITY_KEYS)
        and all(protected[key] is False for key in PROTECTED_AUTHORITY_KEYS)
    )
    protocol_ready = (
        state.get("protocol_hash_valid") is True
        and state.get("validator_hash_valid") is True
        and protected_authority_ready
    )
    dimensions[DIMENSIONS[9]] = _dimension(
        "PASS" if protocol_ready else BLOCKED,
        "PROTOCOL_VALIDATOR_AND_ECONOMIC_AUTHORITY_PRESERVED"
        if protocol_ready
        else "PROTECTED_PROTOCOL_OR_AUTHORITY_MISMATCH",
    )

    capability_ready = state.get("capability_firewall_valid") is True
    dimensions[DIMENSIONS[10]] = _dimension(
        "PASS" if capability_ready else BLOCKED,
        "NO_RUNTIME_PROCESS_THREAD_SOCKET_OR_NETWORK_CAPABILITY"
        if capability_ready
        else "CAPABILITY_FIREWALL_VIOLATION",
    )

    bindings = state.get("source_bindings", {})
    binding_keys_present = isinstance(bindings, dict) and all(
        key in bindings for key in ("F160", "F161", "F162")
    )
    bindings_valid = binding_keys_present and all(
        bindings[key] is True for key in ("F160", "F161", "F162")
    )
    historical_ready = (
        bindings_valid
        and state.get("f158_hashes_valid") is True
        and state.get("historical_state_valid") is True
    )
    if not binding_keys_present:
        historical_result = NOT_READY
        historical_evidence = "REQUIRED_SOURCE_BINDING_MISSING"
    elif not historical_ready:
        historical_result = BLOCKED
        historical_evidence = "SOURCE_OR_HISTORICAL_HASH_MISMATCH"
    else:
        historical_result = "PASS"
        historical_evidence = "F158_THROUGH_F162_HISTORY_HASH_BOUND"
    dimensions[DIMENSIONS[11]] = _dimension(
        historical_result,
        historical_evidence,
    )

    prior_results = [dimensions[name]["result"] for name in DIMENSIONS[:-1]]
    if BLOCKED in prior_results:
        overall = BLOCKED
        overall_evidence = "ONE_OR_MORE_SECURITY_BOUNDARIES_BLOCKED"
    elif any(result != "PASS" for result in prior_results):
        overall = NOT_READY
        overall_evidence = "ONE_OR_MORE_DESIGN_DIMENSIONS_NOT_READY"
    else:
        overall = READY
        overall_evidence = "ALL_REQUIRED_OFFLINE_DESIGN_DIMENSIONS_PASS"
    dimensions[DIMENSIONS[12]] = _dimension(
        "PASS" if overall == READY else overall,
        overall_evidence,
    )

    return {
        "status": overall,
        "dimensions": dimensions,
        "implementation_review_ready": overall == READY,
        "execution_authorized": False,
        "runtime_authorized": False,
        "testnet_authorized": False,
        "production_ready": False,
    }
