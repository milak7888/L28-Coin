# SPDX-License-Identifier: Apache-2.0
"""Pure-data F170 forward-path decision boundary; importing is inert."""


PENDING = "PENDING_OPERATOR_SELECTION"
OPTION_A = "OPTION_A"
OPTION_B = "OPTION_B"
OPTION_C = "OPTION_C"
OPTION_D = "OPTION_D"

FORWARD_OPTIONS = {
    OPTION_A: "broader isolated two-agent testnet",
    OPTION_B: "signer and economic-control security gates",
    OPTION_C: "interoperability preparation",
    OPTION_D: "bounded public testnet planning",
}

F169B_EVIDENCE_SHA256 = "9d61a79a8761102384202c8b9700ce0e93cbfab8be7a916f5829418e55cc3c01"
F169B_GATE_SHA256 = "5fb4ee72a28ab69809d62f1d490098e278d41335a0fe623dd28d30720b9168e1"

REQUIRED_PROOF = {
    "f169b_evidence_sha256": F169B_EVIDENCE_SHA256,
    "f169b_gate_sha256": F169B_GATE_SHA256,
    "F168_POST_RUN_RESULT": "PASS",
    "F168_EXECUTION_OCCURRED": True,
    "F168_AUTHORIZATION_CONSUMED": True,
    "F168_RETRY_ALLOWED": False,
    "F159_RETRY_FORBIDDEN": True,
    "authorization_claim_count": 1,
}


class ForwardPathDecisionError(ValueError):
    """Raised for missing proof, unknown directions, or implicit advancement."""


def required_proof():
    return dict(REQUIRED_PROOF)


def committed_decision_state():
    return {
        "F170_DECISION": PENDING,
        "OPERATOR_SELECTION_RECORDED": False,
        "SELECTED_DIRECTION": None,
        "NO_AUTOMATIC_ADVANCEMENT": True,
        "SEPARATE_FUTURE_REVIEW_REQUIRED": True,
        "SEPARATE_FUTURE_AUTHORIZATION_REQUIRED": True,
        "RUNTIME_ACTIVITY": False,
        "SIGNER_ACTIVATION": False,
        "TESTNET_ACTIVITY": False,
        "PUBLIC_TESTNET_ACTIVATION": False,
        "DEPLOYMENT": False,
        "PROTOCOL_AUTHORITY": False,
        "ECONOMIC_AUTHORITY": False,
        "SETTLEMENT_AUTHORITY": False,
    }


def assess_forward_path(proof, requested_selection=PENDING):
    """Record a direction only; never activate or authorize that direction."""

    if not isinstance(proof, dict) or proof != required_proof():
        raise ForwardPathDecisionError("F168_PASS_PROOF_MISSING_OR_INVALID")
    if requested_selection != PENDING and requested_selection not in FORWARD_OPTIONS:
        raise ForwardPathDecisionError("UNKNOWN_FORWARD_PATH_SELECTION")
    result = committed_decision_state()
    if requested_selection != PENDING:
        result["F170_DECISION"] = requested_selection
        result["OPERATOR_SELECTION_RECORDED"] = True
        result["SELECTED_DIRECTION"] = FORWARD_OPTIONS[requested_selection]
    return result
