# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/l28_option_a_selection_readiness_v0.1.json"
PROTOCOL = ROOT / "PROTOCOL.md"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_option_a_is_recommended_but_not_selected():
    data = load()

    assert data["status"] == "SELECTION_READINESS_ONLY"
    assert data["readiness"] == "READY_FOR_EXPLICIT_OPTION_A_POLICY_SELECTION"
    assert data["recommended_option"] == "OPTION_A_HALT_ON_CONFLICT"

    assert data["selected_option"] is None
    assert data["policy_selected"] is False
    assert data["policy_implementation_authorized"] is False


def test_option_a_candidate_does_not_invent_consensus_values():
    candidate = load()["candidate_semantics"]

    assert candidate["automatic_reorg_allowed"] is False
    assert candidate["peer_can_select_canonical_history"] is False
    assert candidate["operator_discretionary_fork_choice_allowed"] is False
    assert candidate["confirmation_claim_allowed"] is False
    assert candidate["confirmation_count"] is None
    assert candidate["max_reorg_depth"] is None
    assert candidate["fork_choice_rule"] is None
    assert candidate["finality_claim_created"] is False


def test_conflict_behavior_is_fail_closed():
    candidate = load()["candidate_semantics"]

    assert (
        candidate["conflict_action"]
        == "HALT_SYNC_AND_RETAIN_CURRENT_LOCAL_CANONICAL_STATE"
    )

    assert candidate["resume_rule"] == (
        "ONLY_AFTER_GOVERNED_DETERMINISTIC_RESOLUTION_RULE_IS_SELECTED_IMPLEMENTED_TESTED_REVIEWED_AND_AUTHORIZED"
    )


def test_protocol_compatibility_is_bounded_not_overclaimed():
    compat = load()["compatibility"]

    assert compat["protocol_version_reviewed"] == "1.0.0"
    assert compat["protocol_invariants_changed"] is False
    assert compat["economic_invariants_changed"] is False
    assert compat["transaction_validation_changed"] is False
    assert compat["canonical_height_rule_changed"] is False
    assert compat["historical_state_changed"] is False

    assert compat["non_normative_fail_closed_boundary_compatible"] is True
    assert compat["normative_protocol_adoption_automatically_v1_compatible"] is False
    assert compat["normative_adoption_requires_governed_compatibility_decision"] is True
    assert compat["breaking_change_requires_v2_0_0"] is True


def test_all_options_remain_unselected():
    options = load()["option_evaluation"]

    assert len(options) == 3
    assert all(item["selected"] is False for item in options)

    by_id = {item["id"]: item for item in options}

    assert by_id["OPTION_A_HALT_ON_CONFLICT"]["recommended"] is True
    assert by_id["OPTION_A_HALT_ON_CONFLICT"]["automatic_reorg"] is False

    assert by_id["OPTION_B_BOUNDED_REORG"]["recommended"] is False
    assert by_id["OPTION_C_FINALITY_FLOOR"]["recommended"] is False


def test_peer_and_operator_gain_no_consensus_authority():
    authority = load()["protected_authority"]

    assert all(value is False for value in authority.values())


def test_runtime_activation_remains_false():
    auth = load()["authorization"]

    assert all(value is False for value in auth.values())


def test_f37_11_remains_blocked_until_explicit_selection():
    gaps = load()["gap_reassessment"]

    assert gaps["F37-11"] == (
        "BLOCKED_REORG_POLICY_PENDING_EXPLICIT_OPTION_A_SELECTION"
    )


def test_protocol_frozen_versioning_language_still_exists():
    protocol = PROTOCOL.read_text(encoding="utf-8")

    assert "Protocol invariants** MUST NOT change within v1.x" in protocol
    assert "Any breaking change MUST be released as **v2.0.0**" in protocol
    assert "canonical consensus height" in protocol
    assert "fail closed" in protocol
