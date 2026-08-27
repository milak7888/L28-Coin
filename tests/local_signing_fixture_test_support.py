# SPDX-License-Identifier: Apache-2.0
"""Test-local support for Foundation115 offline fixture conformance.

This module reads committed public JSON fixtures only. It is not a signer,
wallet, validator, network client, ledger, settlement service, or runtime.
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
FIXTURE_DIR = (
    REPO_ROOT
    / "conformance"
    / "local_signing_economic_control"
    / "v0.1"
    / "fixtures"
)
DOMAIN = b"L28-LSEC-CONFORMANCE-V0.1\x00"
BLOCKED = "BLOCKED_REQUIRES_FUTURE_SECURITY_DECISION"
DISPOSABLE_MARKER = "DISPOSABLE-FORBIDDEN-MARKER-NOT-A-KEY"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CASE_ID_RE = re.compile(
    r"^LSEC-CONF-v0\.1-(ISO|AUT|VAL|KEY|LIM|APR|RPL|EXP|AUD|OPR|EXT|ECO)-"
    r"(POS|NEG|BND|FCL)-\d{3}$"
)
FIXTURE_ID_RE = re.compile(
    r"^fx-lsec-v01-(iso|aut|val|key|lim|apr|rpl|exp|aud|opr|ext|eco)-"
    r"(pos|neg|bnd|fcl)-\d{3}$"
)

_INVENTORY_TEXT = """
LSEC-CONF-v0.1-ISO-POS-001 fx-lsec-v01-iso-pos-001 POS isolated_boundary_ok
LSEC-CONF-v0.1-ISO-NEG-001 fx-lsec-v01-iso-neg-001 NEG signer_authority_forbidden
LSEC-CONF-v0.1-ISO-BND-001 fx-lsec-v01-iso-bnd-001 BND public_metadata_ok
LSEC-CONF-v0.1-ISO-FCL-001 fx-lsec-v01-iso-fcl-001 FCL signer_not_authorized
LSEC-CONF-v0.1-AUT-POS-001 fx-lsec-v01-aut-pos-001 POS authorization_validation_separated
LSEC-CONF-v0.1-AUT-NEG-001 fx-lsec-v01-aut-neg-001 NEG protocol_validation_rejected
LSEC-CONF-v0.1-AUT-BND-001 fx-lsec-v01-aut-bnd-001 BND protocol_validation_pending
LSEC-CONF-v0.1-AUT-FCL-001 fx-lsec-v01-aut-fcl-001 FCL authority_binding_invalid
LSEC-CONF-v0.1-VAL-POS-001 fx-lsec-v01-val-pos-001 POS protocol_validation_accepted
LSEC-CONF-v0.1-VAL-NEG-001 fx-lsec-v01-val-neg-001 NEG validation_override_forbidden
LSEC-CONF-v0.1-VAL-BND-001 fx-lsec-v01-val-bnd-001 BND protocol_validation_accepted
LSEC-CONF-v0.1-VAL-FCL-001 fx-lsec-v01-val-fcl-001 FCL protocol_validation_unavailable
LSEC-CONF-v0.1-KEY-POS-001 fx-lsec-v01-key-pos-001 POS public_custody_boundary_ok
LSEC-CONF-v0.1-KEY-NEG-001 fx-lsec-v01-key-neg-001 NEG secret_material_forbidden
LSEC-CONF-v0.1-KEY-BND-001 fx-lsec-v01-key-bnd-001 BND public_metadata_ok
LSEC-CONF-v0.1-KEY-FCL-001 fx-lsec-v01-key-fcl-001 FCL custody_boundary_violation
LSEC-CONF-v0.1-LIM-POS-001 fx-lsec-v01-lim-pos-001 POS spending_limits_ok
LSEC-CONF-v0.1-LIM-NEG-001 fx-lsec-v01-lim-neg-001 NEG per_transaction_limit_exceeded
LSEC-CONF-v0.1-LIM-NEG-002 fx-lsec-v01-lim-neg-002 NEG cumulative_limit_exceeded
LSEC-CONF-v0.1-LIM-BND-001 fx-lsec-v01-lim-bnd-001 BND spending_limits_ok
LSEC-CONF-v0.1-LIM-BND-002 fx-lsec-v01-lim-bnd-002 BND spending_limits_ok
LSEC-CONF-v0.1-LIM-FCL-001 fx-lsec-v01-lim-fcl-001 FCL spending_policy_unavailable
LSEC-CONF-v0.1-APR-POS-001 fx-lsec-v01-apr-pos-001 POS approval_threshold_met
LSEC-CONF-v0.1-APR-NEG-001 fx-lsec-v01-apr-neg-001 NEG approval_threshold_not_met
LSEC-CONF-v0.1-APR-NEG-002 fx-lsec-v01-apr-neg-002 NEG duplicate_approval
LSEC-CONF-v0.1-APR-BND-001 fx-lsec-v01-apr-bnd-001 BND approval_threshold_met
LSEC-CONF-v0.1-APR-FCL-001 fx-lsec-v01-apr-fcl-001 FCL approval_policy_unavailable
LSEC-CONF-v0.1-RPL-POS-001 fx-lsec-v01-rpl-pos-001 POS replay_fresh
LSEC-CONF-v0.1-RPL-NEG-001 fx-lsec-v01-rpl-neg-001 NEG replay_detected
LSEC-CONF-v0.1-RPL-BND-001 fx-lsec-v01-rpl-bnd-001 BND replay_detected
LSEC-CONF-v0.1-RPL-FCL-001 fx-lsec-v01-rpl-fcl-001 FCL replay_state_unavailable
LSEC-CONF-v0.1-EXP-POS-001 fx-lsec-v01-exp-pos-001 POS expiration_active
LSEC-CONF-v0.1-EXP-NEG-001 fx-lsec-v01-exp-neg-001 NEG artifact_expired
LSEC-CONF-v0.1-EXP-NEG-002 fx-lsec-v01-exp-neg-002 NEG not_yet_valid
LSEC-CONF-v0.1-EXP-BND-001 fx-lsec-v01-exp-bnd-001 BND artifact_expired
LSEC-CONF-v0.1-EXP-FCL-001 fx-lsec-v01-exp-fcl-001 FCL evaluation_time_unavailable
LSEC-CONF-v0.1-AUD-POS-001 fx-lsec-v01-aud-pos-001 POS audit_evidence_ok
LSEC-CONF-v0.1-AUD-NEG-001 fx-lsec-v01-aud-neg-001 NEG settlement_claim_unverified
LSEC-CONF-v0.1-AUD-NEG-002 fx-lsec-v01-aud-neg-002 NEG audit_authority_forbidden
LSEC-CONF-v0.1-AUD-BND-001 fx-lsec-v01-aud-bnd-001 BND audit_evidence_ok
LSEC-CONF-v0.1-AUD-FCL-001 fx-lsec-v01-aud-fcl-001 FCL audit_lineage_invalid
LSEC-CONF-v0.1-OPR-POS-001 fx-lsec-v01-opr-pos-001 POS operator_gate_satisfied
LSEC-CONF-v0.1-OPR-NEG-001 fx-lsec-v01-opr-neg-001 NEG operator_authorization_denied
LSEC-CONF-v0.1-OPR-NEG-002 fx-lsec-v01-opr-neg-002 NEG operator_authorization_mismatch
LSEC-CONF-v0.1-OPR-BND-001 fx-lsec-v01-opr-bnd-001 BND operator_gate_satisfied
LSEC-CONF-v0.1-OPR-FCL-001 fx-lsec-v01-opr-fcl-001 FCL operator_gate_unavailable
LSEC-CONF-v0.1-EXT-POS-001 fx-lsec-v01-ext-pos-001 POS external_evidence_advisory
LSEC-CONF-v0.1-EXT-NEG-001 fx-lsec-v01-ext-neg-001 NEG advisory_authority_forbidden
LSEC-CONF-v0.1-EXT-NEG-002 fx-lsec-v01-ext-neg-002 NEG external_evidence_authority_forbidden
LSEC-CONF-v0.1-EXT-BND-001 fx-lsec-v01-ext-bnd-001 BND external_evidence_advisory
LSEC-CONF-v0.1-EXT-FCL-001 fx-lsec-v01-ext-fcl-001 FCL future_security_decision_required
LSEC-CONF-v0.1-ECO-POS-001 fx-lsec-v01-eco-pos-001 POS protected_economics_preserved
LSEC-CONF-v0.1-ECO-NEG-001 fx-lsec-v01-eco-neg-001 NEG protocol_override_forbidden
LSEC-CONF-v0.1-ECO-NEG-002 fx-lsec-v01-eco-neg-002 NEG protocol_validation_rejected
LSEC-CONF-v0.1-ECO-BND-001 fx-lsec-v01-eco-bnd-001 BND spending_limits_ok
LSEC-CONF-v0.1-ECO-FCL-001 fx-lsec-v01-eco-fcl-001 FCL ledger_state_unavailable
"""
PLANNED = tuple(tuple(line.split()) for line in _INVENTORY_TEXT.strip().splitlines())
PLANNED_BY_CASE = {case_id: (fixture_id, cls, code) for case_id, fixture_id, cls, code in PLANNED}
PLANNED_BY_FIXTURE = {fixture_id: (case_id, cls, code) for case_id, fixture_id, cls, code in PLANNED}
CLASS_NAME = {"POS": "positive", "NEG": "negative", "BND": "boundary", "FCL": "fail_closed"}
EXPECTED_CLASS_COUNTS = Counter({"POS": 12, "NEG": 19, "BND": 13, "FCL": 12})

ORDERS = {
    "top": ("fixture_schema","fixture_spec_version","plan_version","fixture_id","case_id","family","class","description","fixed_clock","public_identities","input","expected","authority_assertions","safety_assertions","canonical"),
    "fixed_clock": ("evaluation_time","created_at","not_before","expires_at","replay_retention_until"),
    "public_identities": ("payer_id","payee_id","operator_id","approver_ids","signer_public_key_id"),
    "input": ("intent","policy","approvals","replay_view","expiration_view","operator_authorization","protocol_validation","advisory_evidence","receipt_audit_evidence","case_probe"),
    "intent": ("intent_profile","intent_id","request_id","payer_id","payee_id","asset_id","amount","purpose","created_at","not_before","expires_at","nonce","proposed_transaction"),
    "proposed_transaction": ("sender","receiver","amount","timestamp","nonce","type","coinbase"),
    "policy": ("available","policy_id","asset_id","per_transaction_limit","cumulative_limit","prior_authorized_total","window_start","window_end","approval_threshold","authorized_approver_ids","operator_authorization_required","signer_boundary_authorized","protocol_override_allowed","unlimited_spend_allowed"),
    "approval": ("approval_id","approver_id","intent_id","policy_id","approved_amount","decision","created_at","expires_at","public_evidence_id"),
    "replay_view": ("available","view_id","intent_id","request_id","status","first_seen_at","retention_until","read_only"),
    "expiration_view": ("evaluation_time","intent_not_before","intent_expires_at","quote_expires_at","payment_expires_at","approvals_expire_at","operator_evidence_expires_at","clock_source","system_clock_read","network_clock_read"),
    "operator_authorization": ("available","evidence_id","operator_id","decision","intent_id","policy_id","payer_id","payee_id","asset_id","maximum_amount","created_at","expires_at","independent_security_review_id","scope_matches"),
    "protocol_validation": ("delegate","available","invocation_required","invoked","transaction_input_sha256","status","reason","alternate_validator_supplied","override_requested","ledger_context_available","consensus_context_available","issued_supply_context_available","read_only"),
    "advisory_evidence": ("harness_evals_present","harness_evals_report_id","harness_evals_effect","bitcoin_evidence_present","bitcoin_evidence_id","bitcoin_effect","authority_claimed","removal_changes_core_result"),
    "receipt_audit_evidence": ("available","audit_profile","audit_id","intent_id","policy_id","authorization_status","validation_status","replay_status","expiration_status","approval_status","operator_status","settlement_evidence_status","public_receipt_id","lineage_id","claims_signature_created","claims_broadcast","claims_ledger_mutation","claims_consensus_change"),
    "case_probe": ("probe_kind","target_path","operation","public_value","public_marker"),
    "expected": ("ok","outcome","code","case_id","family","authorization_status","validation_status","signer_edge_status","limit_status","approval_status","replay_status","expiration_status","operator_status","audit_status","protocol_reason","detail","report_id","non_execution"),
    "non_execution": ("signing_attempted","signature_created","wallet_accessed","transaction_submitted","broadcast_attempted","rpc_connected","network_connected","replay_state_mutated","ledger_mutated","settlement_finalized","consensus_modified","execution_authorized"),
    "authority_assertions": ("l28_consensus_authority","l28_settlement_authority","validate_transaction_mandatory","authorization_equals_validation","signer_isolated_future_only","signer_may_override_protocol","harness_evals_advisory_only","bitcoin_external_evidence_only","adapter_transport_only","issuance_override_allowed","supply_override_allowed","height_override_allowed","history_override_allowed","validation_override_allowed","consensus_override_allowed","historical_evidence_mutable","protected_economic_facts","blocked_security_decision_status"),
    "protected_economic_facts": ("hard_cap_l28","emission_ceiling_l28","historically_mined_l28","treasury_locked_l28","circulating_snapshot_l28","halving_interval","reward_schedule","historical_mined_through_entry","next_canonical_height_after_bootstrap"),
    "safety_assertions": ("contains_private_keys","contains_seed_phrases","contains_mnemonics","contains_xprv","contains_wallet_secrets","contains_credentials","contains_rpc_credentials","contains_production_addresses","contains_real_balances_or_transactions","contains_environment_values","generates_or_imports_keys","creates_or_imports_wallets","signs","broadcasts","connects_network","mutates_replay_state","mutates_ledger","activates_settlement","changes_protocol_or_economics","public_fictional_data_only"),
    "canonical": ("algorithm","field_order_enforced","input_sha256","expected_report_id","fixture_sha256"),
}

PROTECTED_ECONOMICS = {
    "hard_cap_l28": 28000000,
    "emission_ceiling_l28": 11130000,
    "historically_mined_l28": 2824584,
    "treasury_locked_l28": 500000,
    "circulating_snapshot_l28": 2324584,
    "halving_interval": 210000,
    "reward_schedule": [28, 14, 7, 3, 1, 0],
    "historical_mined_through_entry": 100877,
    "next_canonical_height_after_bootstrap": 100878,
}
AUTHORITY_ASSERTIONS = {
    "l28_consensus_authority": True,
    "l28_settlement_authority": True,
    "validate_transaction_mandatory": True,
    "authorization_equals_validation": False,
    "signer_isolated_future_only": True,
    "signer_may_override_protocol": False,
    "harness_evals_advisory_only": True,
    "bitcoin_external_evidence_only": True,
    "adapter_transport_only": True,
    "issuance_override_allowed": False,
    "supply_override_allowed": False,
    "height_override_allowed": False,
    "history_override_allowed": False,
    "validation_override_allowed": False,
    "consensus_override_allowed": False,
    "historical_evidence_mutable": False,
    "protected_economic_facts": PROTECTED_ECONOMICS,
    "blocked_security_decision_status": BLOCKED,
}
NON_EXECUTION = {key: False for key in ORDERS["non_execution"]}
SAFETY_ASSERTIONS = {
    **{key: False for key in ORDERS["safety_assertions"][:-1]},
    "public_fictional_data_only": True,
}
OVERRIDE_FLAGS = (
    "issuance_override_allowed",
    "supply_override_allowed",
    "height_override_allowed",
    "history_override_allowed",
    "validation_override_allowed",
    "consensus_override_allowed",
)


class DuplicateKeyError(ValueError):
    pass


def _pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(key)
        out[key] = value
    return out


def strict_loads(text: str) -> Any:
    return json.loads(
        text,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        object_pairs_hook=_pairs_hook,
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
        text = raw.decode("utf-8")
        if "\t" in text:
            raise AssertionError(f"tabs forbidden: {path}")
        fixture = strict_loads(text)
        if not isinstance(fixture, dict):
            raise AssertionError(f"fixture root must be object: {path}")
        fixtures.append(fixture)
    return fixtures


def by_case(fixtures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {fixture["case_id"]: fixture for fixture in fixtures}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def recompute_digests(fixture: dict[str, Any]) -> tuple[str, str, str]:
    input_digest = sha256(fixture["input"])
    expected_without_report = copy.deepcopy(fixture["expected"])
    expected_without_report.pop("report_id")
    report_id = sha256(DOMAIN + canonical_bytes(expected_without_report))
    fixture_for_digest = copy.deepcopy(fixture)
    fixture_for_digest["canonical"]["fixture_sha256"] = ""
    fixture_digest = sha256(fixture_for_digest)
    return input_digest, report_id, fixture_digest


def assert_order(value: dict[str, Any], schema_name: str) -> None:
    if tuple(value) != ORDERS[schema_name]:
        raise AssertionError(
            f"{schema_name} property order mismatch: {tuple(value)!r}"
        )


def assert_exact_schema(fixture: dict[str, Any]) -> None:
    assert_order(fixture, "top")
    assert_order(fixture["fixed_clock"], "fixed_clock")
    assert_order(fixture["public_identities"], "public_identities")
    value = fixture["input"]
    assert_order(value, "input")
    assert_order(value["intent"], "intent")
    assert_order(value["intent"]["proposed_transaction"], "proposed_transaction")
    assert_order(value["policy"], "policy")
    for approval in value["approvals"]:
        assert_order(approval, "approval")
    for name in (
        "replay_view",
        "expiration_view",
        "operator_authorization",
        "protocol_validation",
        "advisory_evidence",
        "receipt_audit_evidence",
        "case_probe",
    ):
        assert_order(value[name], name)
    assert_order(fixture["expected"], "expected")
    assert_order(fixture["expected"]["non_execution"], "non_execution")
    assert_order(fixture["authority_assertions"], "authority_assertions")
    assert_order(
        fixture["authority_assertions"]["protected_economic_facts"],
        "protected_economic_facts",
    )
    assert_order(fixture["safety_assertions"], "safety_assertions")
    assert_order(fixture["canonical"], "canonical")


def structural_code(candidate: dict[str, Any]) -> str:
    try:
        assert_exact_schema(candidate)
    except (AssertionError, KeyError, TypeError):
        return "schema_invalid"
    actual = recompute_digests(candidate)
    declared = (
        candidate["canonical"]["input_sha256"],
        candidate["canonical"]["expected_report_id"],
        candidate["canonical"]["fixture_sha256"],
    )
    if actual != declared or candidate["expected"]["report_id"] != actual[1]:
        return "canonical_digest_mismatch"
    if candidate["authority_assertions"] != AUTHORITY_ASSERTIONS:
        return "authority_assertion_invalid"
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
