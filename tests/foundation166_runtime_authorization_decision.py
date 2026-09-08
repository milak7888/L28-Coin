# SPDX-License-Identifier: Apache-2.0
"""Pure-data F166 operator-decision boundary; no authority is granted here."""


PENDING = "PENDING_OPERATOR_DECISION"
AUTHORIZE = "AUTHORIZE_ONE_NEW_BOUNDED_EXPERIMENT"
DEFER = "DEFER"
DECISION_STATES = (PENDING, AUTHORIZE, DEFER)

PROPOSED_EXPERIMENT_ID = "L28-F165-PROPOSED-BOUNDED-RUNTIME-001"
F165_GATE_SHA256 = "a9e1c6b791eb7031bcd81024a163c4ddafddb9bb844ab9f24324bc5dfc80d942"

REQUIRED_F165_STATE = {
    "decision_result": "READY_FOR_OPERATOR_AUTHORIZATION_DECISION",
    "new_authorization_required": True,
    "f159_retry_forbidden": True,
    "old_authorization_reusable": False,
    "authorization_granted": False,
    "execution_authorized": False,
    "execution_invocation_present": False,
}

FUTURE_OPERATOR_EVIDENCE_KEYS = (
    "evidence_kind",
    "separate_future_step",
    "proposed_experiment_id",
    "decision",
    "operator_decision_id",
    "security_review_id",
    "separate_explicit_execution_invocation_required",
)


class DecisionBoundaryError(ValueError):
    """Raised for malformed, stale, contradictory, or implicit decisions."""


def required_f165_input():
    value = dict(REQUIRED_F165_STATE)
    value["f165_gate_sha256"] = F165_GATE_SHA256
    value["proposed_experiment_id"] = PROPOSED_EXPERIMENT_ID
    return value


def committed_decision_state():
    """Return the non-authorizing state committed by F166."""

    return {
        "decision": PENDING,
        "decision_valid": True,
        "authorization_granted": False,
        "execution_authorized": False,
        "execution_invocation_present": False,
        "future_operator_evidence_present": False,
    }


def _validate_f165(f165_input):
    if not isinstance(f165_input, dict) or f165_input != required_f165_input():
        raise DecisionBoundaryError("F165_BINDING_OR_STATE_INVALID")


def _validate_future_operator_evidence(evidence):
    if not isinstance(evidence, dict) or tuple(evidence) != FUTURE_OPERATOR_EVIDENCE_KEYS:
        raise DecisionBoundaryError("EXPLICIT_FUTURE_OPERATOR_EVIDENCE_REQUIRED")
    if (
        evidence["evidence_kind"] != "EXPLICIT_OPERATOR_AUTHORIZATION_DECISION"
        or evidence["separate_future_step"] is not True
        or evidence["proposed_experiment_id"] != PROPOSED_EXPERIMENT_ID
        or evidence["decision"] != AUTHORIZE
        or not isinstance(evidence["operator_decision_id"], str)
        or not evidence["operator_decision_id"].startswith("FUTURE-")
        or not isinstance(evidence["security_review_id"], str)
        or not evidence["security_review_id"].startswith("FUTURE-")
        or evidence["separate_explicit_execution_invocation_required"] is not True
    ):
        raise DecisionBoundaryError("EXPLICIT_FUTURE_OPERATOR_EVIDENCE_INVALID")


def assess_operator_decision(f165_input, requested_decision=PENDING, operator_evidence=None):
    """Assess decision-record structure without creating an authorization grant."""

    _validate_f165(f165_input)
    if requested_decision not in DECISION_STATES:
        raise DecisionBoundaryError("UNKNOWN_OPERATOR_DECISION")
    if requested_decision == AUTHORIZE:
        _validate_future_operator_evidence(operator_evidence)
        return {
            "decision": AUTHORIZE,
            "decision_valid": True,
            "authorization_granted": True,
            "execution_authorized": False,
            "execution_invocation_present": False,
            "future_operator_evidence_present": True,
            "new_authorization_only": True,
            "f159_retry_forbidden": True,
            "old_authorization_reusable": False,
        }
    if operator_evidence is not None:
        raise DecisionBoundaryError("OPERATOR_EVIDENCE_NOT_ALLOWED_FOR_NON_AUTHORIZE")
    result = committed_decision_state()
    result["decision"] = requested_decision
    return result
