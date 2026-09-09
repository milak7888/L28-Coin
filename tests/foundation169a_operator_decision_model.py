# SPDX-License-Identifier: Apache-2.0
"""Pure-data F169A operator decision record; no runtime invocation is present."""


EXPERIMENT_ID = "L28-F165-PROPOSED-BOUNDED-RUNTIME-001"
AUTHORIZE = "AUTHORIZE_ONE_NEW_BOUNDED_EXPERIMENT"
AUTHORIZATION_ID = "L28-F168-BOUND-RUNTIME-001-AUTH-001"
BASE_COMMIT = "8add82820e3d62692ecf7da4afc7327ec6ae740a"
F164_CANDIDATE_SHA256 = "1921fb28103e0240c9fac6f0e1c3e17f6c0a2b5824a1609ed3cbdf91f1e4d2db"
F166_GATE_SHA256 = "f5433efd24f051b188d6e937f0debf651ddf61543089c10a8443745bb1c1b526"
F167_GATE_SHA256 = "e569f395327db19deff63cc8228339e48f50ea2ece447cadbc35eba5daa82ca0"

DECISION_KEYS = (
    "experiment_id",
    "decision",
    "authorization_id",
    "base_commit",
    "f164_candidate_sha256",
    "f166_gate_sha256",
    "f167_gate_sha256",
    "one_shot",
    "f159_retry_forbidden",
    "old_authorization_reusable",
)

DECISION_EVIDENCE = {
    "experiment_id": EXPERIMENT_ID,
    "decision": AUTHORIZE,
    "authorization_id": AUTHORIZATION_ID,
    "base_commit": BASE_COMMIT,
    "f164_candidate_sha256": F164_CANDIDATE_SHA256,
    "f166_gate_sha256": F166_GATE_SHA256,
    "f167_gate_sha256": F167_GATE_SHA256,
    "one_shot": True,
    "f159_retry_forbidden": True,
    "old_authorization_reusable": False,
}

CURRENT_STATE = {
    "F169A_DECISION": AUTHORIZE,
    "F169A_OPERATOR_DECISION_RECORDED": True,
    "F169A_AUTHORIZATION_GRANTED": True,
    "F168_INVOCATION_PRESENT": False,
    "F168_EXECUTION_AUTHORIZED": False,
    "F168_AUTHORIZATION_CONSUMED": False,
    "F168_EXECUTION_OCCURRED": False,
    "F159_RETRY_FORBIDDEN": True,
}


class DecisionBoundaryError(ValueError):
    """Raised when the exact operator decision evidence is altered."""


def committed_decision_evidence():
    return dict(DECISION_EVIDENCE)


def committed_state():
    return dict(CURRENT_STATE)


def validate_decision_evidence(evidence):
    """Validate the exact one-shot decision record without invoking execution."""

    if not isinstance(evidence, dict) or tuple(evidence) != DECISION_KEYS:
        raise DecisionBoundaryError("EXPLICIT_OPERATOR_DECISION_MISSING_OR_MALFORMED")
    if evidence != DECISION_EVIDENCE:
        raise DecisionBoundaryError("OPERATOR_DECISION_BINDING_INVALID")
    return committed_state()
