# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/l28_confirmation_reorg_policy_decision_gate_v0.1.json"
PACKAGE = ROOT / "docs/foundation144_confirmation_reorg_security_decision_package_v0.1.md"
GAP = ROOT / "docs/foundation144_f37_confirmation_reorg_gap_reassessment_v0.1.md"


def load_gate():
    return json.loads(GATE.read_text(encoding="utf-8"))


def test_decision_gate_is_ready_but_selects_no_policy():
    data = load_gate()

    assert data["status"] == "DECISION_PACKAGE_ONLY"
    assert data["readiness"] == "READY_FOR_EXPLICIT_CONFIRMATION_REORG_POLICY_DECISION"

    current = data["current_state"]

    assert current["selected_policy_option"] is None
    assert current["confirmation_policy_defined"] is False
    assert current["confirmation_count_defined"] is False
    assert current["fork_choice_rule_defined"] is False
    assert current["reorg_policy_defined"] is False
    assert current["max_reorg_depth_defined"] is False
    assert current["finality_rule_defined"] is False
    assert current["confirmation_claim_allowed"] is False
    assert current["automatic_reorg_allowed"] is False


def test_all_policy_options_are_unselected_and_unparameterized():
    data = load_gate()
    options = data["policy_options"]

    assert len(options) == 3
    assert len({item["id"] for item in options}) == 3

    for item in options:
        assert item["selected"] is False
        assert item["confirmation_count"] is None
        assert item["fork_choice_rule"] is None
        assert item["max_reorg_depth"] is None
        assert item["finality_rule"] is None
        assert item["required_decisions"]


def test_decision_fields_contain_no_hidden_policy_values():
    data = load_gate()

    for value in data["decision_requirements"].values():
        assert value is None


def test_conflict_behavior_fails_closed_without_policy():
    current = load_gate()["current_state"]

    assert (
        current["on_conflict_without_selected_policy"]
        == "REJECT_CANONICAL_TRANSITION_AND_RETAIN_CURRENT_LOCAL_STATE"
    )
    assert current["automatic_reorg_allowed"] is False
    assert current["confirmation_claim_allowed"] is False


def test_required_protocol_invariants_are_preserved():
    invariants = set(load_gate()["protected_invariants"])

    required = {
        "CANONICAL_HEIGHT_FROM_CONSENSUS_STATE_ONLY",
        "MISSING_REQUIRED_STATE_FAILS_CLOSED",
        "PEER_EVIDENCE_HAS_NO_LEDGER_MUTATION_AUTHORITY",
        "PEER_EVIDENCE_HAS_NO_CANONICAL_HEIGHT_OVERRIDE_AUTHORITY",
        "PEER_EVIDENCE_HAS_NO_ISSUANCE_OR_SUPPLY_AUTHORITY",
        "CANONICAL_TRANSACTION_VALIDATION_REMAINS_COIN_TX_VALIDATION_VALIDATE_TRANSACTION",
        "HISTORICAL_RECORDS_REMAIN_IMMUTABLE",
        "SAME_PUBLIC_VALIDATION_RULES_FOR_ALL",
        "NO_OPERATOR_OR_SUBSYSTEM_CONSENSUS_OVERRIDE",
        "NO_SETTLEMENT_CLAIM_WITH_UNDEFINED_CONFIRMATION_REORG_POLICY",
    }

    assert required.issubset(invariants)


def test_threat_model_is_complete_and_unique():
    threats = load_gate()["threat_models"]
    ids = {item["id"] for item in threats}

    assert len(threats) == len(ids)

    assert ids == {
        "THREAT_STALE_PEER",
        "THREAT_CONFLICTING_TIPS",
        "THREAT_EQUIVOCATION",
        "THREAT_PARTITION",
        "THREAT_DEEP_REORG_ATTEMPT",
        "THREAT_OSCILLATING_TIPS",
        "THREAT_MISSING_LEDGER_STATE",
        "THREAT_INVALID_CANDIDATE",
    }


def test_future_evidence_requirements_are_explicit():
    evidence = set(load_gate()["required_future_evidence"])

    assert {
        "DETERMINISTIC_POLICY_UNIT_TESTS",
        "CONFLICTING_TIP_ADVERSARIAL_TESTS",
        "PARTITION_AND_RECONNECT_TESTS",
        "EQUIVOCATION_TESTS",
        "DEEP_REORG_BOUNDARY_TESTS",
        "OSCILLATION_RESISTANCE_TESTS",
        "MISSING_STATE_FAIL_CLOSED_TESTS",
        "PROTECTED_ECONOMIC_FACT_PRESERVATION",
        "CANONICAL_VALIDATOR_PRESERVATION",
        "INDEPENDENT_SECURITY_REVIEW",
    }.issubset(evidence)


def test_f37_statuses_remain_bounded():
    gaps = load_gate()["gap_reassessment"]

    assert gaps["F37-07"] == "PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE"
    assert gaps["F37-10"] == "PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE"
    assert gaps["F37-11"] == "BLOCKED_REORG_POLICY"


def test_all_runtime_and_economic_activation_remains_false():
    auth = load_gate()["authorization"]

    for value in auth.values():
        assert value is False


def test_docs_do_not_claim_policy_selection_or_activation():
    package = PACKAGE.read_text(encoding="utf-8")
    gap = GAP.read_text(encoding="utf-8")

    assert "selects none of these options" in package
    assert "No confirmation count is selected." in gap
    assert "F37-11 remains BLOCKED_REORG_POLICY" in gap
    assert "does not authorize implementation" in package
