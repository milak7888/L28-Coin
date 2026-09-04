# SPDX-License-Identifier: Apache-2.0

import hashlib
import json
from pathlib import Path

from coin import tx_validation


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "docs/l28_foundation151_option_a_gate_closure_v0.1.json"
RECORD = (
    ROOT
    / "docs/foundation151_option_a_gate_closure_f37_reassessment_v0.1.md"
)
F143 = ROOT / "docs/foundation143_isolated_loopback_experiment_evidence_v0.1.json"
F149 = ROOT / "docs/l28_option_a_independent_review_checklist_v0.1.json"


def load(path=STATUS):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f149_and_f150_review_outcomes_are_closed_only_offline():
    data = load()
    outcome = data["review_outcome"]

    assert data["status"] == "PASS"
    assert outcome["foundation149_independent_security_review"] == "PASS"
    assert outcome["foundation150_remediation"] == "PASS"
    assert outcome["original_f149_findings_fully_remediated"] is True
    assert outcome["review_disposition"] == {
        "BLOCKED": 0,
        "GAP": 0,
        "PASS": 15,
    }
    assert outcome["further_independent_review_required_before_runtime"] is True
    assert data["scope"]["offline_only"] is True
    assert data["scope"]["normative_protocol_adoption"] is False
    assert data["scope"]["network_runtime"] is False


def test_f37_reassessment_preserves_prior_loopback_boundaries():
    gaps = load()["f37_reassessment"]

    assert gaps == {
        "F37-07": "PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE",
        "F37-10": "PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE",
        "F37-11": "OFFLINE_OPTION_A_REVIEWED_NON_NORMATIVE",
    }

    historical = load(F143)["gap_reassessment"]
    assert historical["F37-07"] == gaps["F37-07"]
    assert historical["F37-10"] == gaps["F37-10"]


def test_f37_11_historical_pending_record_is_preserved_not_rewritten():
    historical = load(F149)

    assert historical["independent_review_performed"] is False
    assert historical["independent_review_passed"] is False
    assert historical["gap_reassessment"]["F37-11"] == (
        "PARTIAL_OFFLINE_OPTION_A_IMPLEMENTED_PENDING_INDEPENDENT_REVIEW"
    )
    assert load()["f37_reassessment"]["F37-11"] == (
        "OFFLINE_OPTION_A_REVIEWED_NON_NORMATIVE"
    )


def test_next_gate_is_decision_ready_but_not_authorized():
    gate = load()["next_possible_gate"]

    assert gate["name"] == (
        "EXPLICIT_BOUNDED_RUNTIME_NETWORK_AUTHORIZATION_DECISION"
    )
    assert gate["status"] == "READY_FOR_EXPLICIT_DECISION"
    assert gate["decision_only"] is True
    assert gate["implementation_authorized"] is False
    assert gate["activation_authorized"] is False
    assert gate["required_before_any_implementation"]


def test_all_runtime_network_testnet_and_value_authority_is_false():
    data = load()
    authorization = data["authorization"]

    assert set(authorization) == {
        "broadcast_authorized",
        "deployment_authorized",
        "filesystem_runtime_authorized",
        "key_creation_authorized",
        "mining_authorized",
        "network_authorized",
        "persistent_p2p_runtime_authorized",
        "process_runtime_authorized",
        "public_testnet_authorized",
        "rpc_authorized",
        "settlement_authorized",
        "signing_authorized",
        "socket_authorized",
        "wallet_creation_authorized",
    }
    assert all(value is False for value in authorization.values())
    assert set(data["option_a_authority"]) == {
        "automatic_reorg_authorized",
        "canonical_height_override_authorized",
        "confirmation_claim_authorized",
        "fork_winner_selected",
        "history_authority",
        "issuance_authority",
        "ledger_mutation_authorized",
        "settlement_authority",
        "supply_authority",
        "validation_authority",
    }
    assert all(value is False for value in data["option_a_authority"].values())


def test_protocol_economics_history_and_validator_are_exact():
    protected = load()["protected_invariants"]

    assert protected["protocol_version"] == "1.0.0"
    assert protected["coinbase_only_issuance"] is True
    assert protected["hard_cap"] == 28000000
    assert protected["emission_ceiling"] == 11130000
    assert protected["historically_mined"] == 2824584
    assert protected["treasury_locked"] == 500000
    assert protected["circulating_snapshot"] == 2324584
    assert protected["halving_interval"] == 210000
    assert protected["reward_schedule"] == [28, 14, 7, 3, 1, 0]
    assert protected["historical_mined_through_entry"] == 100877
    assert protected["next_canonical_height"] == 100878
    assert protected["historical_evidence_immutable"] is True
    assert protected["canonical_height_authority"] == "CONSENSUS_DERIVED_ONLY"
    assert protected["canonical_validator"] == (
        "coin.tx_validation.validate_transaction"
    )
    assert protected["protocol_invariants_changed"] is False
    assert protected["economic_invariants_changed"] is False
    assert protected["historical_state_changed"] is False
    assert protected["transaction_validation_changed"] is False
    assert protected["signer_runtime_authorized"] is False
    assert protected["bitcoin_authority"] == (
        "EXTERNAL_EVIDENCE_ONLY_ZERO_L28_AUTHORITY"
    )

    assert tx_validation.L28_MAX_SUPPLY == 28000000
    assert tx_validation.L28_EMISSION_CEILING == 11130000
    assert tx_validation.L28_HISTORICAL_MINED == 2824584
    assert tx_validation.L28_HALVING_INTERVAL == 210000
    assert tx_validation.L28_REWARD_SCHEDULE == (28, 14, 7, 3, 1)
    assert tx_validation.L28_HISTORICAL_LAST_ENTRY == 100877
    assert tx_validation.L28_NEXT_HEIGHT_AFTER_CHECKPOINT == 100878
    assert callable(tx_validation.validate_transaction)


def test_protocol_and_validator_hashes_match_the_foundation151_baseline():
    baseline = load()["baseline"]

    assert baseline["commit"] == (
        "7958995612e8fdf8e8609efa581f35b7e3bfdd18"
    )
    assert sha256(ROOT / "PROTOCOL.md") == baseline["protocol_sha256"]
    assert sha256(ROOT / "coin/tx_validation.py") == (
        baseline["tx_validation_sha256"]
    )


def test_record_is_explicitly_non_activating_and_non_normative():
    text = RECORD.read_text(encoding="utf-8")

    assert "OFFLINE_OPTION_A_REVIEWED_NON_NORMATIVE" in text
    assert "PASS 15 / GAP 0 / BLOCKED 0" in text
    assert "READY_FOR_EXPLICIT_DECISION" in text
    assert "This is decision readiness only." in text
    assert "No persistent networking" in text
    assert "coin.tx_validation.validate_transaction" in text
    assert "Bitcoin remains external evidence only" in text
