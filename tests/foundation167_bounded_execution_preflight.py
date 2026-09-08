# SPDX-License-Identifier: Apache-2.0
"""Offline-only F167 bounded execution-preflight contract."""


PENDING = "PENDING_OPERATOR_DECISION"
AUTHORIZE = "AUTHORIZE_ONE_NEW_BOUNDED_EXPERIMENT"
DEFER = "DEFER"
PROPOSED_EXPERIMENT_ID = "L28-F165-PROPOSED-BOUNDED-RUNTIME-001"

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
    "f164_candidate_sha256": "1921fb28103e0240c9fac6f0e1c3e17f6c0a2b5824a1609ed3cbdf91f1e4d2db",
    "cleanup_requires_all_children_terminal": True,
    "cleanup_requires_all_supervisors_quiescent": True,
    "terminal_states": TERMINAL_STATES,
}
REQUIRED_SOURCE_BINDINGS = {
    "F160": "408fe4264253a2940b93a051cdace49fda325019c8178def003ff695632e23d5",
    "F161": "24e839fc0707c64ea4c0d957730368bb404e1f45b16d842cd383d1ba76de0e8c",
    "F162": "112008e5b4fc2d14b0b7239038f21006493f668ffff21f224e2633377bc8c8fc",
    "F163": "6322cbfca6260e36e445c8f110f420be2b161168e2e234ebcecbac50e56b4985",
    "F164": "a05dd02527b2cd20ca1636ec2a6b48c62719957a32140f55a83ceb3f6ab788e6",
    "F165": "a9e1c6b791eb7031bcd81024a163c4ddafddb9bb844ab9f24324bc5dfc80d942",
    "F166": "f5430f65d9907a0e12942a53aa652518989d91445da78131212dc7983fc43131",
}


class PreflightContractError(ValueError):
    """Raised when preflight evidence is incomplete, expanded, or contradictory."""


def exact_scope():
    return dict(EXPECTED_SCOPE)


def required_source_bindings():
    return dict(REQUIRED_SOURCE_BINDINGS)


def pending_f166_record():
    return {
        "decision": PENDING,
        "decision_valid": True,
        "authorization_granted": False,
        "execution_authorized": False,
        "execution_invocation_present": False,
        "future_operator_evidence_present": False,
        "f159_retry_forbidden": True,
        "old_authorization_reusable": False,
    }


def _validate_scope_and_bindings(scope, source_bindings):
    if not isinstance(scope, dict) or scope != EXPECTED_SCOPE:
        raise PreflightContractError("BOUNDED_SCOPE_NOT_EXACT")
    if (
        not isinstance(source_bindings, dict)
        or source_bindings != REQUIRED_SOURCE_BINDINGS
    ):
        raise PreflightContractError("F160_F166_BINDINGS_NOT_EXACT")


def _future_authorize_record_valid(record):
    return (
        isinstance(record, dict)
        and record.get("decision") == AUTHORIZE
        and record.get("decision_valid") is True
        and record.get("future_operator_evidence_present") is True
        and record.get("new_authorization_only") is True
        and record.get("f159_retry_forbidden") is True
        and record.get("old_authorization_reusable") is False
        and record.get("authorization_granted") is True
        and record.get("execution_authorized") is False
        and record.get("execution_invocation_present") is False
    )


def _future_invocation_template_valid(invocation):
    return (
        isinstance(invocation, dict)
        and invocation.get("invocation_kind")
        == "SEPARATE_EXPLICIT_F168_INVOCATION_TEMPLATE"
        and invocation.get("separate_future_step") is True
        and invocation.get("proposed_experiment_id") == PROPOSED_EXPERIMENT_ID
        and invocation.get("execution_occurred") is False
    )


def assess_bounded_execution_preflight(
    scope,
    source_bindings,
    f166_record,
    future_f168_invocation_template=None,
):
    """Prove necessary future prerequisites while keeping the actual gate closed."""

    _validate_scope_and_bindings(scope, source_bindings)
    if not isinstance(f166_record, dict):
        raise PreflightContractError("F166_DECISION_RECORD_INVALID")
    decision = f166_record.get("decision")
    if decision not in (PENDING, AUTHORIZE, DEFER):
        raise PreflightContractError("F166_DECISION_RECORD_INVALID")

    if decision == PENDING and f166_record != pending_f166_record():
        raise PreflightContractError("PENDING_F166_STATE_CONTRADICTION")
    if decision == DEFER and (
        f166_record.get("authorization_granted") is not False
        or f166_record.get("execution_authorized") is not False
    ):
        raise PreflightContractError("DEFER_F166_STATE_CONTRADICTION")

    authorize_record_valid = _future_authorize_record_valid(f166_record)
    invocation_template_valid = _future_invocation_template_valid(
        future_f168_invocation_template
    )
    eligibility_requirements_satisfied = (
        authorize_record_valid and invocation_template_valid
    )
    return {
        "F166_DECISION": decision,
        "FUTURE_AUTHORIZE_RECORD_STRUCTURALLY_VALID": authorize_record_valid,
        "SEPARATE_F168_INVOCATION_TEMPLATE_PRESENT": invocation_template_valid,
        "FUTURE_ELIGIBILITY_REQUIREMENTS_SATISFIED": eligibility_requirements_satisfied,
        "READY_FOR_EXECUTION": eligibility_requirements_satisfied,
        "EXECUTION_GATE_OPEN": eligibility_requirements_satisfied,
        "EXECUTION_AUTHORIZED": eligibility_requirements_satisfied,
        "EXECUTION_OCCURRED": False,
    }
