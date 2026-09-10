# SPDX-License-Identifier: Apache-2.0
"""F171 fail-closed signer/economic-control eligibility gate.

Evaluates public evidence only. Importing this module is inert. It never
signs, broadcasts, settles, mints, loads keys, or calls
coin.tx_validation.validate_transaction.
"""

from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path


def _load_f170():
    path = Path(__file__).resolve().parent / "foundation170_forward_path_decision.py"
    spec = importlib.util.spec_from_file_location("foundation170_forward_path_decision", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_F170 = _load_f170()
OPTION_B = _F170.OPTION_B
ForwardPathDecisionError = _F170.ForwardPathDecisionError
assess_forward_path = _F170.assess_forward_path
required_proof = _F170.required_proof


ELIGIBLE = "ELIGIBLE_FOR_FUTURE_SIGNER_AUTHORIZATION_REVIEW"
NOT_ELIGIBLE = "NOT_ELIGIBLE"
BLOCKED = "BLOCKED"

CANONICAL_VALIDATOR = "coin.tx_validation.validate_transaction"
TRUSTED_TIME_SOURCE = "caller_supplied_fixture_clock"
AUDIT_PROFILE = "l28-local-signer-eligibility-audit/v0.1"

PROTECTED_ECONOMICS = {
    "hard_cap_l28": 28000000,
    "emission_ceiling_l28": 11130000,
    "historically_mined_l28": 2824584,
    "treasury_locked_l28": 500000,
    "circulating_snapshot_l28": 2324584,
    "halving_interval": 210000,
    "reward_schedule": (28, 14, 7, 3, 1, 0),
    "historical_mined_through_entry": 100877,
    "next_canonical_height_after_bootstrap": 100878,
    "issuance_mechanism": "coinbase_only",
    "canonical_height_authority": "consensus_derived",
}

PROTECTED_AUTHORITY = (
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
    "bitcoin",
)

NON_EXECUTION_FLAGS = (
    "signer_invoked",
    "signing_attempted",
    "signature_created",
    "wallet_accessed",
    "broadcast_attempted",
    "transaction_submitted",
    "ledger_mutated",
    "settlement_finalized",
    "execution_authorized",
    "spend_authorized",
    "signing_authorized",
)

SECRET_KEYS = frozenset(
    {
        "private_key",
        "seed",
        "seed_phrase",
        "mnemonic",
        "xprv",
        "wallet_credential",
        "rpc_user",
        "rpc_password",
        "rpc_cookie",
    }
)


def _is_natural_int(value):
    return type(value) is int and value >= 0


def empty_accept_state():
    return {
        "request_ids": (),
        "idempotency_keys": (),
        "authorized_total": 0,
    }


def committed_evidence():
    """Production-unresolved F171 evidence. Eligibility is blocked."""

    return {
        "F170_OPERATOR_SELECTION": OPTION_B,
        "production_time_backend": "UNRESOLVED",
        "production_audit_backend": "UNRESOLVED",
        "caller_identity_evidence": None,
        "operator_authorization_evidence": None,
        "authorization_evidence": None,
        "economic_policy": None,
        "approvals": None,
        "replay_evidence": None,
        "time_evidence": None,
        "audit_evidence": None,
        "proposed_transaction": None,
        "custody_readiness_evidence": {"status": "unresolved", "keys_loaded": False},
        "runtime_hardening_evidence": {"status": "unresolved"},
        "fault_recovery_evidence": {"status": "unresolved"},
        "prior_accept_state": empty_accept_state(),
        "protected_economics": dict(PROTECTED_ECONOMICS),
        "authority_assertions": {name: False for name in PROTECTED_AUTHORITY},
        "non_execution": {name: False for name in NON_EXECUTION_FLAGS},
    }


def committed_gate_result():
    result, _state = evaluate_signer_eligibility(committed_evidence())
    return result


def _reject(code, reason, field="", next_state=None):
    return (
        {
            "F171_SIGNER_ELIGIBILITY_RESULT": code,
            "reason": reason,
            "field": field,
            "F170_OPERATOR_SELECTION": OPTION_B,
            "F171_SIGNER_RUNTIME_ACTIVE": False,
            "F171_SIGNING": False,
            "F171_BROADCAST": False,
            "F171_SETTLEMENT": False,
            "F171_PROTOCOL_AUTHORITY": False,
            "canonical_validator": CANONICAL_VALIDATOR,
            "eligibility_equals_validation": False,
            "authorization_equals_validation": False,
            "signer_invoked": False,
        },
        deepcopy(next_state) if next_state is not None else empty_accept_state(),
    )


def _contains_secret(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in SECRET_KEYS:
                return True
            if _contains_secret(value):
                return True
    elif isinstance(node, (list, tuple)):
        return any(_contains_secret(item) for item in node)
    return False


def _as_dict(value):
    return value if isinstance(value, dict) else None


def _accept_state(value):
    state = _as_dict(value)
    if state is None:
        return None
    request_ids = tuple(state.get("request_ids") or ())
    idempotency_keys = tuple(state.get("idempotency_keys") or ())
    total = state.get("authorized_total", 0)
    if not _is_natural_int(total):
        return None
    if any(not isinstance(item, str) or not item for item in request_ids + idempotency_keys):
        return None
    return {
        "request_ids": request_ids,
        "idempotency_keys": idempotency_keys,
        "authorized_total": total,
    }


def _record_accept(state, request_id, idempotency_key, amount):
    return {
        "request_ids": state["request_ids"] + (request_id,),
        "idempotency_keys": state["idempotency_keys"] + (idempotency_key,),
        "authorized_total": state["authorized_total"] + amount,
    }


def evaluate_signer_eligibility(evidence):
    """Return (result, next_accept_state). Never mutates caller evidence."""

    if not isinstance(evidence, dict):
        return _reject(NOT_ELIGIBLE, "schema_invalid", "evidence")
    snapshot = deepcopy(evidence)
    if _contains_secret(snapshot):
        return _reject(NOT_ELIGIBLE, "secret_material_forbidden", "evidence")

    try:
        selection = assess_forward_path(required_proof(), snapshot.get("F170_OPERATOR_SELECTION"))
    except ForwardPathDecisionError:
        return _reject(BLOCKED, "f170_operator_selection_unavailable", "F170_OPERATOR_SELECTION")
    if selection.get("F170_DECISION") != OPTION_B:
        return _reject(BLOCKED, "f170_option_b_required", "F170_OPERATOR_SELECTION")

    economics = snapshot.get("protected_economics")
    if economics is not None:
        expected = dict(PROTECTED_ECONOMICS)
        expected["reward_schedule"] = list(PROTECTED_ECONOMICS["reward_schedule"])
        provided = dict(economics)
        if provided.get("reward_schedule") is not None:
            provided["reward_schedule"] = list(provided["reward_schedule"])
        if provided != expected:
            return _reject(NOT_ELIGIBLE, "protocol_override_forbidden", "protected_economics")

    authority = snapshot.get("authority_assertions")
    if isinstance(authority, dict):
        if any(authority.get(name) for name in PROTECTED_AUTHORITY):
            return _reject(NOT_ELIGIBLE, "protocol_override_forbidden", "authority_assertions")
        if any(
            value is True
            for key, value in authority.items()
            if isinstance(key, str)
            and (
                key.endswith("_override_allowed")
                or key in {"authorization_equals_validation", "eligibility_equals_invocation"}
            )
        ):
            return _reject(NOT_ELIGIBLE, "protocol_override_forbidden", "authority_assertions")

    non_execution = snapshot.get("non_execution")
    if isinstance(non_execution, dict) and any(non_execution.get(name) for name in NON_EXECUTION_FLAGS):
        return _reject(NOT_ELIGIBLE, "execution_forbidden", "non_execution")

    time_backend = snapshot.get("production_time_backend")
    audit_backend = snapshot.get("production_audit_backend")
    if time_backend == "UNRESOLVED":
        return _reject(BLOCKED, "production_time_backend_unresolved", "production_time_backend")
    if audit_backend == "UNRESOLVED":
        return _reject(BLOCKED, "production_audit_backend_unresolved", "production_audit_backend")
    if time_backend != "TEST_LOCAL_EVIDENCE_CONTRACT_ONLY":
        return _reject(BLOCKED, "future_security_decision_required", "production_time_backend")
    if audit_backend != "TEST_LOCAL_EVIDENCE_CONTRACT_ONLY":
        return _reject(BLOCKED, "future_security_decision_required", "production_audit_backend")

    caller = _as_dict(snapshot.get("caller_identity_evidence"))
    if caller is None:
        return _reject(NOT_ELIGIBLE, "identity_evidence_unavailable", "caller_identity_evidence")
    if caller.get("authentication_status") != "verified" or not caller.get("caller_id"):
        return _reject(NOT_ELIGIBLE, "identity_evidence_unauthenticated", "caller_identity_evidence")

    operator = _as_dict(snapshot.get("operator_authorization_evidence"))
    if operator is None:
        return _reject(NOT_ELIGIBLE, "operator_gate_unavailable", "operator_authorization_evidence")
    if operator.get("authentication_status") != "verified" or operator.get("decision") != "approved":
        return _reject(NOT_ELIGIBLE, "operator_authorization_denied", "operator_authorization_evidence")
    if operator.get("scope_matches") is not True:
        return _reject(NOT_ELIGIBLE, "operator_authorization_mismatch", "operator_authorization_evidence")

    authorization = _as_dict(snapshot.get("authorization_evidence"))
    if authorization is None or authorization.get("authorization_status") != "allowed":
        return _reject(NOT_ELIGIBLE, "authorization_unavailable", "authorization_evidence")
    intent_id = authorization.get("intent_id")
    request_id = authorization.get("request_id")
    if not intent_id or not request_id:
        return _reject(NOT_ELIGIBLE, "authorization_unavailable", "authorization_evidence")
    if operator.get("request_id") != request_id or operator.get("intent_id") != intent_id:
        return _reject(NOT_ELIGIBLE, "authority_binding_invalid", "operator_authorization_evidence")
    caller_scope = caller.get("scope_request_id")
    if caller_scope is not None and caller_scope != request_id:
        return _reject(NOT_ELIGIBLE, "authority_binding_invalid", "caller_identity_evidence")

    policy = _as_dict(snapshot.get("economic_policy"))
    if policy is None:
        return _reject(NOT_ELIGIBLE, "spending_policy_unavailable", "economic_policy")
    per_limit = policy.get("per_transaction_limit")
    cumulative_limit = policy.get("cumulative_limit")
    if not _is_natural_int(per_limit) or not _is_natural_int(cumulative_limit):
        return _reject(NOT_ELIGIBLE, "schema_invalid", "economic_policy")
    if policy.get("protocol_override_allowed") is True or policy.get("unlimited_spend_allowed") is True:
        return _reject(NOT_ELIGIBLE, "protocol_override_forbidden", "economic_policy")
    if policy.get("policy_status") != "active" or policy.get("authentication_status") != "verified":
        return _reject(NOT_ELIGIBLE, "spending_policy_unavailable", "economic_policy")
    if policy.get("asset_id") != "L28":
        return _reject(NOT_ELIGIBLE, "spending_policy_unavailable", "economic_policy.asset_id")

    approvals = snapshot.get("approvals")
    if not isinstance(approvals, list) or not approvals:
        return _reject(NOT_ELIGIBLE, "approval_policy_unavailable", "approvals")
    threshold = policy.get("approval_threshold", 1)
    authorized_approvers = set(policy.get("authorized_approver_ids") or ())
    seen = set()
    accepted = 0
    for approval in approvals:
        if not isinstance(approval, dict):
            return _reject(NOT_ELIGIBLE, "approval_policy_unavailable", "approvals")
        approver = approval.get("approver_id")
        if approver in seen:
            return _reject(NOT_ELIGIBLE, "duplicate_approval", "approvals")
        seen.add(approver)
        if (
            approval.get("authentication_status") == "verified"
            and approval.get("decision") == "approved"
            and approval.get("request_id") == request_id
            and approval.get("intent_id") == intent_id
            and approver in authorized_approvers
        ):
            accepted += 1
    if accepted < threshold:
        return _reject(NOT_ELIGIBLE, "approval_threshold_not_met", "approvals")

    replay = _as_dict(snapshot.get("replay_evidence"))
    if replay is None or replay.get("available") is not True:
        return _reject(NOT_ELIGIBLE, "replay_state_unavailable", "replay_evidence")
    idempotency_key = replay.get("idempotency_key")
    if not idempotency_key or replay.get("request_id") != request_id or replay.get("intent_id") != intent_id:
        return _reject(NOT_ELIGIBLE, "replay_state_unavailable", "replay_evidence")
    if replay.get("status") != "fresh" or replay.get("atomic_transition_status") != "ready":
        return _reject(NOT_ELIGIBLE, "replay_detected", "replay_evidence")

    prior = _accept_state(snapshot.get("prior_accept_state"))
    if prior is None:
        return _reject(NOT_ELIGIBLE, "replay_state_unavailable", "prior_accept_state")
    if request_id in prior["request_ids"] or idempotency_key in prior["idempotency_keys"]:
        return _reject(NOT_ELIGIBLE, "replay_detected", "replay_evidence", prior)

    tx = _as_dict(snapshot.get("proposed_transaction"))
    if tx is None:
        return _reject(NOT_ELIGIBLE, "schema_invalid", "proposed_transaction", prior)
    amount = tx.get("amount")
    if type(amount) is not int or amount <= 0:
        return _reject(NOT_ELIGIBLE, "schema_invalid", "proposed_transaction.amount", prior)
    if tx.get("coinbase") is True or tx.get("type") == "coinbase":
        return _reject(NOT_ELIGIBLE, "protocol_override_forbidden", "proposed_transaction", prior)
    if amount > per_limit:
        return _reject(NOT_ELIGIBLE, "per_transaction_limit_exceeded", "proposed_transaction.amount", prior)
    if prior["authorized_total"] + amount > cumulative_limit:
        return _reject(NOT_ELIGIBLE, "cumulative_limit_exceeded", "economic_policy.cumulative_limit", prior)

    time_evidence = _as_dict(snapshot.get("time_evidence"))
    if time_evidence is None:
        return _reject(NOT_ELIGIBLE, "evaluation_time_unavailable", "time_evidence", prior)
    if (
        time_evidence.get("source") != TRUSTED_TIME_SOURCE
        or time_evidence.get("authentication_status") != "verified"
        or time_evidence.get("system_clock_read") is True
        or time_evidence.get("network_clock_read") is True
        or type(time_evidence.get("evaluation_time")) is not int
    ):
        return _reject(NOT_ELIGIBLE, "evaluation_time_unavailable", "time_evidence", prior)

    audit = _as_dict(snapshot.get("audit_evidence"))
    if audit is None or audit.get("available") is not True:
        return _reject(NOT_ELIGIBLE, "audit_lineage_invalid", "audit_evidence", prior)
    if audit.get("evidence_profile") != AUDIT_PROFILE or audit.get("public_evidence_only") is not True:
        return _reject(NOT_ELIGIBLE, "audit_lineage_invalid", "audit_evidence", prior)
    if not audit.get("audit_id"):
        return _reject(NOT_ELIGIBLE, "audit_lineage_invalid", "audit_evidence", prior)

    custody = _as_dict(snapshot.get("custody_readiness_evidence")) or {}
    if custody.get("keys_loaded") is True:
        return _reject(NOT_ELIGIBLE, "secret_material_forbidden", "custody_readiness_evidence", prior)
    if custody.get("status") != "resolved":
        return _reject(BLOCKED, "custody_readiness_unresolved", "custody_readiness_evidence", prior)

    hardening = _as_dict(snapshot.get("runtime_hardening_evidence")) or {}
    if hardening.get("status") != "resolved":
        return _reject(BLOCKED, "runtime_hardening_unresolved", "runtime_hardening_evidence", prior)

    recovery = _as_dict(snapshot.get("fault_recovery_evidence")) or {}
    if recovery.get("status") != "resolved":
        return _reject(BLOCKED, "fault_recovery_unresolved", "fault_recovery_evidence", prior)

    next_state = _record_accept(prior, request_id, idempotency_key, amount)
    return (
        {
            "F171_SIGNER_ELIGIBILITY_RESULT": ELIGIBLE,
            "reason": "signer_eligible_public_projection",
            "field": "",
            "F170_OPERATOR_SELECTION": OPTION_B,
            "F171_SIGNER_RUNTIME_ACTIVE": False,
            "F171_SIGNING": False,
            "F171_BROADCAST": False,
            "F171_SETTLEMENT": False,
            "F171_PROTOCOL_AUTHORITY": False,
            "canonical_validator": CANONICAL_VALIDATOR,
            "eligibility_equals_validation": False,
            "authorization_equals_validation": False,
            "signer_invoked": False,
        },
        next_state,
    )
