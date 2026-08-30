# SPDX-License-Identifier: Apache-2.0
"""Test-local support for Foundation121 offline fixture conformance.

This module reads committed public fixtures and normative documentation only.
It does not import or invoke protocol validation, signer, wallet, network,
ledger, settlement, or other production runtime code.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "conformance" / "local_signer_interface" / "v0.1" / "fixtures"
FIXTURE_SPEC = REPO_ROOT / "docs" / "local_signer_interface_fixture_spec_v0.1.md"

BLOCKED = "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION"
DISPOSABLE_MARKER = "DISPOSABLE-FORBIDDEN-MARKER-NOT-A-KEY"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(
    r"^LSI-CONF-v0\.1-(CMP|SCH|IDN|AUT|VAL|ELG|LIM|APR|RPL|EXP|OPR|ATH|CAN|PRE|AUD|FWL|NEX|GAT)-"
    r"(POS|NEG|BND|FCL)-(\d{3})$"
)
FIXTURE_ID_RE = re.compile(
    r"^fx-lsi-v01-(cmp|sch|idn|aut|val|elg|lim|apr|rpl|exp|opr|ath|can|pre|aud|fwl|nex|gat)-"
    r"(pos|neg|bnd|fcl)-(\d{3})$"
)
INVENTORY_ROW_RE = re.compile(
    r"^\| `(?P<case>LSI-CONF-v0\.1-[A-Z]{3}-(?:POS|NEG|BND|FCL)-\d{3})` "
    r"\| `(?P<fixture>fx-lsi-v01-[a-z]{3}-(?:pos|neg|bnd|fcl)-\d{3})` "
    r"\| (?P<class>POS|NEG|BND|FCL) \| `(?P<status>[a-z_]+)` "
    r"\| `(?P<code>[a-z_]+)` \|$",
    re.MULTILINE,
)
INVENTORY_SHA256 = "677995be0c718fe4d14547c889ef43cc45464f592054555b8b22bd10fa048adf"

FAMILIES = (
    "CMP", "SCH", "IDN", "AUT", "VAL", "ELG", "LIM", "APR", "RPL",
    "EXP", "OPR", "ATH", "CAN", "PRE", "AUD", "FWL", "NEX", "GAT",
)
CLASS_NAME = {"POS": "positive", "NEG": "negative", "BND": "boundary", "FCL": "fail_closed"}
EXPECTED_CLASS_COUNTS = Counter({"POS": 19, "NEG": 49, "BND": 14, "FCL": 18})

ORDERS = {
    "top": ("fixture_schema", "fixture_spec_version", "plan_version", "interface_profile", "fixture_id", "case_id", "family", "class", "description", "fixed_clock", "public_identities", "input", "expected", "authority_assertions", "protected_economic_facts", "safety_assertions", "canonical"),
    "fixed_clock": ("evaluation_time", "created_at", "not_before", "expires_at", "policy_window_start", "policy_window_end", "replay_retention_until"),
    "public_identities": ("caller_id", "caller_public_identity", "payer_id", "payee_id", "operator_id", "operator_public_identity", "approver_ids", "signer_public_key_id"),
    "input": ("request", "case_probe"),
    "request": ("interface_profile", "interface_version", "operation", "request_id", "idempotency_key", "created_at", "expires_at", "nonce", "caller_identity_evidence", "operator_authorization_evidence", "authorization_evidence", "economic_policy", "approvals", "replay_evidence", "time_evidence", "proposed_transaction", "protocol_validation_binding", "authority_assertions", "non_execution", "request_digest"),
    "caller_identity_evidence": ("evidence_profile", "evidence_id", "caller_id", "caller_public_identity", "caller_public_key_id", "authentication_status", "scope_request_id", "issued_at", "expires_at", "public_evidence_only"),
    "operator_authorization_evidence": ("evidence_profile", "evidence_id", "operator_id", "operator_public_identity", "authentication_status", "decision", "request_id", "intent_id", "policy_id", "payer_id", "payee_id", "asset_id", "maximum_amount", "created_at", "expires_at", "independent_security_review_id", "scope_matches", "public_evidence_only"),
    "authorization_evidence": ("evidence_profile", "authorization_id", "authorization_status", "intent_id", "request_id", "policy_id", "payer_id", "payee_id", "asset_id", "amount", "evaluator_id", "authentication_status", "created_at", "expires_at", "public_evidence_only"),
    "economic_policy": ("policy_profile", "policy_id", "policy_status", "authentication_status", "asset_id", "per_transaction_limit", "cumulative_limit", "prior_authorized_total", "window_start", "window_end", "approval_threshold", "authorized_approver_ids", "operator_authorization_required", "unlimited_spend_allowed", "protocol_override_allowed", "runtime_authorized"),
    "approval": ("approval_id", "approver_id", "approver_public_identity", "authentication_status", "decision", "request_id", "intent_id", "policy_id", "approved_amount", "created_at", "expires_at", "public_evidence_only"),
    "replay_evidence": ("evidence_profile", "evidence_id", "available", "request_id", "intent_id", "idempotency_key", "status", "first_seen_at", "retention_until", "state_version", "atomicity_evidence_id", "atomic_transition_status", "read_only"),
    "time_evidence": ("evidence_profile", "evidence_id", "evaluation_time", "source", "authentication_status", "intent_not_before", "intent_expires_at", "authorization_expires_at", "approvals_expire_at", "operator_evidence_expires_at", "policy_window_start", "policy_window_end", "system_clock_read", "network_clock_read"),
    "proposed_transaction": ("sender", "receiver", "amount", "timestamp", "nonce", "type", "coinbase"),
    "protocol_validation_binding": ("binding_profile", "delegate", "invocation_required", "available", "invoked", "status", "reason", "transaction_input_sha256", "validation_report_id", "ledger_context_id", "consensus_context_id", "issued_supply_context_id", "alternate_validator_supplied", "override_requested", "read_only", "binding_digest"),
    "case_probe": ("probe_kind", "target_path", "operation", "public_value", "expected_precedence_rank", "public_marker"),
    "expected": ("status", "code", "response"),
    "response": ("interface_profile", "interface_version", "operation", "request_id", "ok", "design_status", "code", "eligibility", "validation_binding", "public_audit_evidence", "authority_assertions", "non_execution", "error", "report_id"),
    "eligibility": ("authorization_status", "validation_status", "identity_status", "policy_status", "limit_status", "approval_status", "replay_status", "expiration_status", "operator_status", "eligibility_status", "signer_invocation_status", "signing_authorized", "spend_authorized", "settlement_authorized", "execution_authorized"),
    "response_validation_binding": ("delegate", "transaction_input_sha256", "validation_report_id", "validation_status", "protocol_reason", "binding_digest", "binding_preserved"),
    "public_audit_evidence": ("evidence_profile", "audit_id", "eligibility_receipt_id", "request_id", "request_digest", "intent_id", "transaction_input_sha256", "caller_evidence_id", "operator_evidence_id", "authorization_id", "policy_id", "approval_ids", "replay_evidence_id", "time_evidence_id", "validation_report_id", "decision_code", "evaluation_time", "settlement_evidence_status", "signature_evidence_status", "public_evidence_only"),
    "error": ("code", "message", "field", "evidence_id"),
    "authority_assertions": ("protocol_version", "l28_consensus_authority", "l28_settlement_authority", "validate_transaction_mandatory", "authorization_equals_validation", "eligibility_equals_invocation", "signer_isolated_future_only", "signer_may_override_protocol", "issuance_override_allowed", "supply_override_allowed", "height_override_allowed", "validation_override_allowed", "consensus_override_allowed", "history_override_allowed", "settlement_override_allowed", "historical_evidence_mutable", "adapter_transport_only", "harness_evals_advisory_only", "bitcoin_external_evidence_only", "blocked_security_decision_status"),
    "non_execution": ("signer_invocation_requested", "signer_invoked", "signing_attempted", "signature_created", "wallet_access_requested", "wallet_accessed", "transaction_submitted", "broadcast_attempted", "rpc_connected", "network_connected", "replay_state_mutated", "economic_control_state_mutated", "ledger_mutated", "settlement_attempted", "settlement_finalized", "consensus_modified", "execution_authorized"),
    "protected_economic_facts": ("hard_cap_l28", "emission_ceiling_l28", "historically_mined_l28", "treasury_locked_l28", "circulating_snapshot_l28", "halving_interval", "reward_schedule", "historical_mined_through_entry", "next_canonical_height_after_bootstrap", "issuance_mechanism", "canonical_height_authority", "historical_evidence_mutable"),
    "safety_assertions": ("public_fictional_data_only", "contains_private_keys", "contains_seeds_or_mnemonics", "contains_xprv_or_keystore", "contains_wallet_or_rpc_credentials", "contains_production_secrets", "contains_real_balances_or_transactions", "reads_keys_or_wallets", "reads_environment_or_system_clock", "invokes_validate_transaction", "implements_or_invokes_signer", "connects_rpc_or_network", "submits_or_broadcasts", "mutates_state_or_ledger", "settles_or_activates_runtime", "changes_protocol_or_economics"),
    "canonical": ("algorithm", "field_order_enforced", "fixture_input_sha256", "request_digest", "transaction_input_sha256", "validation_binding_digest", "expected_audit_id", "expected_eligibility_receipt_id", "expected_report_id", "expected_response_sha256", "fixture_sha256"),
}

FIXED_CLOCK = {
    "evaluation_time": 1700000100, "created_at": 1700000000,
    "not_before": 1700000000, "expires_at": 1700000300,
    "policy_window_start": 1699999900, "policy_window_end": 1700000400,
    "replay_retention_until": 1700000500,
}
PUBLIC_IDENTITIES = {
    "caller_id": "caller-fixture-public-001",
    "caller_public_identity": "agent-caller-public-001",
    "payer_id": "agent-payer-public-001",
    "payee_id": "agent-payee-public-001",
    "operator_id": "operator-fixture-public-001",
    "operator_public_identity": "operator-public-identity-001",
    "approver_ids": ["approver-public-001", "approver-public-002", "approver-public-003"],
    "signer_public_key_id": "signer-public-key-id-disposable-001",
}
AUTHORITY_ASSERTIONS = {
    "protocol_version": "1.0.0", "l28_consensus_authority": True,
    "l28_settlement_authority": True, "validate_transaction_mandatory": True,
    "authorization_equals_validation": False, "eligibility_equals_invocation": False,
    "signer_isolated_future_only": True, "signer_may_override_protocol": False,
    "issuance_override_allowed": False, "supply_override_allowed": False,
    "height_override_allowed": False, "validation_override_allowed": False,
    "consensus_override_allowed": False, "history_override_allowed": False,
    "settlement_override_allowed": False, "historical_evidence_mutable": False,
    "adapter_transport_only": True, "harness_evals_advisory_only": True,
    "bitcoin_external_evidence_only": True,
    "blocked_security_decision_status": BLOCKED,
}
PROTECTED_ECONOMICS = {
    "hard_cap_l28": 28000000, "emission_ceiling_l28": 11130000,
    "historically_mined_l28": 2824584, "treasury_locked_l28": 500000,
    "circulating_snapshot_l28": 2324584, "halving_interval": 210000,
    "reward_schedule": [28, 14, 7, 3, 1, 0],
    "historical_mined_through_entry": 100877,
    "next_canonical_height_after_bootstrap": 100878,
    "issuance_mechanism": "coinbase_only",
    "canonical_height_authority": "consensus_derived",
    "historical_evidence_mutable": False,
}
NON_EXECUTION = {name: False for name in ORDERS["non_execution"]}
SAFETY_ASSERTIONS = {
    "public_fictional_data_only": True,
    **{name: False for name in ORDERS["safety_assertions"][1:]},
}
OVERRIDE_FLAGS = tuple(name for name in ORDERS["authority_assertions"] if name.endswith("override_allowed"))

ID_DOMAIN = b"L28-LOCAL-SIGNER-INTERFACE-FIXTURE-V0.1-ID\x00"
TX_DOMAIN = b"L28-LOCAL-SIGNER-INTERFACE-V0.1-TRANSACTION\x00"
VALIDATION_DOMAIN = b"L28-LOCAL-SIGNER-INTERFACE-V0.1-VALIDATION\x00"
REQUEST_DOMAIN = b"L28-LOCAL-SIGNER-INTERFACE-V0.1-REQUEST\x00"
AUDIT_DOMAIN = b"L28-LOCAL-SIGNER-INTERFACE-V0.1-AUDIT\x00"
REPORT_DOMAIN = b"L28-LOCAL-SIGNER-INTERFACE-V0.1-REPORT\x00"
FIXTURE_INPUT_DOMAIN = b"L28-LOCAL-SIGNER-INTERFACE-FIXTURE-V0.1-INPUT\x00"
EXPECTED_RESPONSE_DOMAIN = b"L28-LOCAL-SIGNER-INTERFACE-FIXTURE-V0.1-EXPECTED-RESPONSE\x00"
FIXTURE_DOMAIN = b"L28-LOCAL-SIGNER-INTERFACE-FIXTURE-V0.1-FIXTURE\x00"


class DuplicateKeyError(ValueError):
    pass


def _pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def strict_loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_pairs_hook,
        parse_float=lambda value: (_ for _ in ()).throw(ValueError(value)),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def fixture_paths() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("*.json"))


def load_fixtures() -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for path in fixture_paths():
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise AssertionError(f"UTF-8 BOM forbidden: {path}")
        if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
            raise AssertionError(f"fixture must end with exactly one LF: {path}")
        fixture = strict_loads(raw.decode("utf-8"))
        if not isinstance(fixture, dict):
            raise AssertionError(f"fixture root must be object: {path}")
        fixtures.append(fixture)
    return fixtures


def inventory() -> tuple[tuple[str, str, str, str, str], ...]:
    text = FIXTURE_SPEC.read_text(encoding="utf-8")
    rows = tuple(tuple(match.groups()) for match in INVENTORY_ROW_RE.finditer(text))
    payload = "\n".join(" ".join(row) for row in rows).encode("utf-8")
    if hashlib.sha256(payload).hexdigest() != INVENTORY_SHA256:
        raise AssertionError("Foundation119 inventory changed")
    return rows


def by_case(fixtures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {fixture["case_id"]: fixture for fixture in fixtures}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=False, allow_nan=False).encode("utf-8")


def digest(domain: bytes, value: Any) -> str:
    return hashlib.sha256(domain + canonical_bytes(value)).hexdigest()


def public_id(fixture_id: str, role: str) -> str:
    return hashlib.sha256(ID_DOMAIN + fixture_id.encode() + b"\x00" + role.encode()).hexdigest()


def recompute_digests(fixture: dict[str, Any]) -> dict[str, str]:
    request = fixture["input"]["request"]
    response = fixture["expected"]["response"]
    transaction_sha = digest(TX_DOMAIN, request["proposed_transaction"])

    validation = copy.deepcopy(request["protocol_validation_binding"])
    validation["binding_digest"] = ""
    validation_sha = digest(VALIDATION_DOMAIN, validation)

    request_blank = copy.deepcopy(request)
    request_blank["request_digest"] = ""
    request_sha = digest(REQUEST_DOMAIN, request_blank)

    audit_blank = copy.deepcopy(response["public_audit_evidence"])
    audit_blank["audit_id"] = ""
    audit_blank["eligibility_receipt_id"] = ""
    audit_id = digest(AUDIT_DOMAIN, audit_blank)
    receipt_blank = copy.deepcopy(response["public_audit_evidence"])
    receipt_blank["eligibility_receipt_id"] = ""
    receipt_id = hashlib.sha256(AUDIT_DOMAIN + b"receipt\x00" + canonical_bytes(receipt_blank)).hexdigest()

    response_blank = copy.deepcopy(response)
    response_blank["report_id"] = ""
    report_id = digest(REPORT_DOMAIN, response_blank)

    fixture_blank = copy.deepcopy(fixture)
    fixture_blank["canonical"]["fixture_sha256"] = ""
    return {
        "fixture_input_sha256": digest(FIXTURE_INPUT_DOMAIN, fixture["input"]),
        "request_digest": request_sha,
        "transaction_input_sha256": transaction_sha,
        "validation_binding_digest": validation_sha,
        "expected_audit_id": audit_id,
        "expected_eligibility_receipt_id": receipt_id,
        "expected_report_id": report_id,
        "expected_response_sha256": digest(EXPECTED_RESPONSE_DOMAIN, response),
        "fixture_sha256": digest(FIXTURE_DOMAIN, fixture_blank),
    }


def assert_order(value: dict[str, Any], name: str) -> None:
    if tuple(value) != ORDERS[name]:
        raise AssertionError(f"{name} property order mismatch: {tuple(value)!r}")


def assert_exact_schema(fixture: dict[str, Any]) -> None:
    assert_order(fixture, "top")
    assert_order(fixture["fixed_clock"], "fixed_clock")
    assert_order(fixture["public_identities"], "public_identities")
    assert_order(fixture["input"], "input")
    request = fixture["input"]["request"]
    assert_order(request, "request")
    for name in ("caller_identity_evidence", "operator_authorization_evidence", "authorization_evidence", "economic_policy", "replay_evidence", "time_evidence", "proposed_transaction", "protocol_validation_binding"):
        assert_order(request[name], name)
    for approval in request["approvals"]:
        assert_order(approval, "approval")
    assert_order(request["authority_assertions"], "authority_assertions")
    assert_order(request["non_execution"], "non_execution")
    assert_order(fixture["input"]["case_probe"], "case_probe")
    assert_order(fixture["expected"], "expected")
    response = fixture["expected"]["response"]
    assert_order(response, "response")
    assert_order(response["eligibility"], "eligibility")
    assert_order(response["validation_binding"], "response_validation_binding")
    assert_order(response["public_audit_evidence"], "public_audit_evidence")
    assert_order(response["authority_assertions"], "authority_assertions")
    assert_order(response["non_execution"], "non_execution")
    assert_order(response["error"], "error")
    assert_order(fixture["authority_assertions"], "authority_assertions")
    assert_order(fixture["protected_economic_facts"], "protected_economic_facts")
    assert_order(fixture["safety_assertions"], "safety_assertions")
    assert_order(fixture["canonical"], "canonical")


def structural_code(candidate: dict[str, Any]) -> str:
    try:
        assert_exact_schema(candidate)
    except (AssertionError, KeyError, TypeError):
        return "schema_invalid"
    if candidate["canonical"] != {
        "algorithm": "sha256-utf8-exact-order-json",
        "field_order_enforced": True,
        **recompute_digests(candidate),
    }:
        return "canonical_digest_mismatch"
    if candidate["authority_assertions"] != AUTHORITY_ASSERTIONS:
        return "authority_assertion_invalid"
    if candidate["protected_economic_facts"] != PROTECTED_ECONOMICS:
        return "protocol_override_forbidden"
    return "ok"


def walk(value: Any):
    yield value
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)
