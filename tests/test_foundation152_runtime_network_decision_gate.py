# SPDX-License-Identifier: Apache-2.0

import ast
import hashlib
import json
from pathlib import Path

from coin import tx_validation


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/l28_foundation152_runtime_network_decision_gate_v0.1.json"
RECORD = (
    ROOT
    / "docs/foundation152_bounded_runtime_network_authorization_decision_package_v0.1.md"
)
TEST_FILE = Path(__file__)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def load_gate():
    return json.loads(
        GATE.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gate_records_selected_one_shot_authorization_without_execution():
    data = load_gate()
    gate = data["decision_gate"]

    assert data["status"] == (
        "ONE_SHOT_RUNTIME_NETWORK_AUTHORIZATION_GRANTED_NOT_CONSUMED"
    )
    assert gate["decision_ready"] is True
    assert gate["authorized_to_execute"] is True
    assert gate["selected_option"] == (
        "AUTHORIZE_ONE_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT"
    )
    assert gate["authorization_artifact_present"] is True
    assert gate["separate_explicit_operator_decision_required"] is False
    assert gate["authorization_granted"] is True
    assert gate["authorization_consumed"] is False
    assert gate["consumed_for_reuse"] is False
    assert gate["valid_for_active_execution"] is False
    assert gate["experiment_executed"] is False

    assert gate["options"] == [
        {
            "id": "A",
            "value": "AUTHORIZE_ONE_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT",
            "selected": True,
        },
        {"id": "B", "value": "DEFER", "selected": False},
        {"id": "C", "value": "REJECT_AND_REVISE", "selected": False},
    ]


def test_current_f37_evidence_is_preserved_without_overstatement():
    evidence = load_gate()["evidence_boundary"]

    assert evidence["F37-07"] == (
        "PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE"
    )
    assert evidence["F37-10"] == (
        "PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE"
    )
    assert evidence["F37-11"] == "OFFLINE_OPTION_A_REVIEWED_NON_NORMATIVE"
    assert evidence["foundation143_authorization_persistent"] is False
    assert evidence["foundation151_next_gate"] == (
        "EXPLICIT_BOUNDED_RUNTIME_NETWORK_AUTHORIZATION_DECISION"
    )


def test_proposed_experiment_is_exactly_two_processes_and_loopback_only():
    proposal = load_gate()["proposed_experiment"]
    topology = proposal["topology"]

    assert proposal["proposal_only"] is True
    assert proposal["agent_count"] == 2
    assert proposal["process_count"] == 2
    assert proposal["same_local_machine_required"] is True
    assert proposal["external_connectivity_permitted"] is False
    assert topology == {
        "agent_a": {
            "id": "agent-a",
            "role": "DESIGNATED_LOCAL_CORE_WRITER",
            "address": "127.0.0.1",
            "port": 28428,
            "process": "process-a",
        },
        "agent_b": {
            "id": "agent-b",
            "role": "PEER_EVIDENCE_ONLY",
            "address": "127.0.0.1",
            "port": 28429,
            "process": "process-b",
        },
    }
    assert proposal["permitted_message_types"] == [
        "HELLO",
        "TIP_EVIDENCE",
        "CANDIDATE_EVIDENCE",
    ]
    assert proposal["transport_limits"] == {
        "max_frame_bytes": 4096,
        "max_payload_bytes": 2048,
        "max_messages_per_session": 32,
        "max_sessions": 2,
        "max_reconnects": 1,
        "maximum_wall_duration_seconds": 60,
    }


def test_lifecycle_data_and_replay_state_are_disposable_and_isolated():
    proposal = load_gate()["proposed_experiment"]
    lifecycle = proposal["lifecycle"]
    data = proposal["data_isolation"]
    replay = proposal["message_replay_isolation"]

    assert lifecycle["restart_after_stop_permitted"] is False
    assert lifecycle["persistent_service_permitted"] is False
    assert lifecycle["reset_scope"] == "ONLY_CURRENT_AUTHORIZATION_DISPOSABLE_STATE"
    assert lifecycle["startup_order"] == [
        "VALIDATE_UNCONSUMED_UNEXPIRED_ONE_SHOT_AUTHORIZATION",
        "CREATE_TWO_ISOLATED_DISPOSABLE_DATA_DIRECTORIES",
        "VERIFY_ALL_EXECUTION_PREREQUISITES",
        "ATOMIC_SUCCESSFUL_EXECUTION_START_CONSUMES_FOR_REUSE",
        "START_PROCESS_A",
        "START_PROCESS_B",
        "OPEN_ONLY_DECLARED_LOOPBACK_ENDPOINTS",
    ]
    assert len(lifecycle["stop_order"]) == 6

    assert data["shared_data_directory_permitted"] is False
    assert data["preexisting_directory_permitted"] is False
    assert data["historical_state_import_permitted"] is False
    assert data["real_value_state_permitted"] is False
    assert data["agent_a_relative_data_dir"] != data["agent_b_relative_data_dir"]

    assert replay["message_ids_persist_across_allowed_reconnect"] is True
    assert replay["peer_nonce_keys_persist_across_allowed_reconnect"] is True
    assert replay["state_reuse_across_authorizations_permitted"] is False
    assert replay["duplicate_message_action"] == "ABORT_AND_HALT_FAIL_CLOSED"


def test_future_authorization_is_explicit_bounded_one_shot_and_fail_closed():
    auth = load_gate()["future_one_shot_authorization"]

    assert auth["option_a_selected"] is True
    assert auth["separate_artifact_required"] is True
    assert auth["must_bind_exact_foundation152_profile"] is True
    assert auth["must_bind_exact_baseline_commit"] is True
    assert auth["must_bind_exact_experiment_scope"] is True
    assert auth["must_bind_operator_identity_and_decision_record"] is True
    assert auth["maximum_execution_window_seconds"] == 60
    assert auth["consume_atomically_on_successful_execution_start"] is True
    assert auth["maximum_execution_count"] == 1
    assert auth["reuse_permitted"] is False
    assert auth["authorization_granted"] is True
    assert auth["authorization_consumed"] is False
    assert auth["consumed_for_reuse"] is False
    assert auth["valid_for_active_execution"] is False
    assert auth["experiment_executed"] is False
    assert auth["lifecycle_states"] == {
        "pre_start": {
            "authorization_consumed": False,
            "consumed_for_reuse": False,
            "valid_for_active_execution": False,
            "first_start_consumption_available": True,
        },
        "active_execution": {
            "authorization_consumed": True,
            "consumed_for_reuse": True,
            "valid_for_active_execution": True,
            "first_start_consumption_available": False,
        },
        "terminated_execution": {
            "authorization_consumed": True,
            "consumed_for_reuse": True,
            "valid_for_active_execution": False,
            "first_start_consumption_available": False,
        },
    }
    assert auth["active_execution_validity_ends_at_earliest_of"] == [
        "EXPERIMENT_COMPLETED",
        "EXPERIMENT_ABORTED",
        "SIXTY_SECOND_MAXIMUM_DEADLINE",
    ]
    assert auth["consumption_does_not_invalidate_active_execution"] is True
    assert auth["consumed_authorization_restart_action"] == (
        "REJECT_RESTART_FAIL_CLOSED"
    )
    assert auth["missing_invalid_or_previously_consumed_start_action"] == (
        "DO_NOT_START_FAIL_CLOSED"
    )


def test_option_a_conflict_halt_is_required_and_resume_is_not_permitted():
    policy = load_gate()["option_a_integration"]
    scenarios = load_gate()["proposed_experiment"]["required_scenarios"]

    assert "PEER_EQUIVOCATION_HALTS_SYNC_AND_RETAINS_LOCAL_CANONICAL_STATE" in scenarios
    assert policy["policy"] == "HALT_ON_CONFLICT_RETAIN_CURRENT_LOCAL_CANONICAL_STATE"
    assert policy["scope"] == "REVIEWED_NON_NORMATIVE_SAFETY_BOUNDARY_ONLY"
    assert policy["peer_equivocation_assessment_required"] is True
    assert policy["required_transition"] == "SYNCING_TO_HALTED_CONFLICT"
    assert policy["retain_current_local_canonical_state"] is True
    assert policy["halt_is_sticky"] is True
    assert policy["resume_during_experiment_permitted"] is False
    assert policy["governed_deterministic_resolution_required_for_any_future_resume"] is True


def test_abort_evidence_and_cleanup_requirements_are_fail_closed():
    data = load_gate()

    assert len(data["abort_criteria"]) == 13
    assert "PEER_EQUIVOCATION_OR_CONFLICT" in data["abort_criteria"]
    assert "ANY_AUTHORITY_OVERRIDE_CLAIM" in data["abort_criteria"]
    assert data["evidence_capture"]["required"] is True
    assert data["evidence_capture"]["private_or_secret_evidence_permitted"] is False
    assert data["evidence_capture"]["pass_requires_complete_evidence"] is True
    assert len(data["evidence_capture"]["capture"]) == 8

    cleanup = data["cleanup_requirements"]
    assert cleanup["both_endpoints_closed"] is True
    assert cleanup["both_processes_stopped"] is True
    assert cleanup["disposable_data_directories_removed"] is True
    assert cleanup["authorization_irreversibly_consumed"] is True
    assert cleanup["persistent_listener_or_peer_session_permitted"] is False
    assert cleanup["cleanup_failure_result"] == (
        "EXPERIMENT_FAILED_CLEANUP_INCOMPLETE"
    )


def test_all_execution_and_override_authority_remains_false():
    data = load_gate()
    execution = data["current_task_execution_authority"]
    bounded = data["authorized_future_bounded_capabilities"]
    firewall = data["authority_firewall"]

    assert set(execution) == {
        "network_authorized",
        "socket_authorized",
        "persistent_p2p_runtime_authorized",
        "filesystem_runtime_authorized",
        "process_runtime_authorized",
        "rpc_authorized",
        "wallet_creation_authorized",
        "key_creation_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "settlement_authorized",
        "deployment_authorized",
        "public_testnet_authorized",
    }
    assert all(value is False for value in execution.values())

    assert bounded == {
        "scope": "ONE_FOUNDATION152_EXPERIMENT_ONLY",
        "network_authorized": True,
        "socket_authorized": True,
        "filesystem_runtime_authorized": True,
        "process_runtime_authorized": True,
        "persistent_authority": False,
        "transferable": False,
        "reusable": False,
    }

    assert set(firewall) == {
        "ledger_mutation_authorized",
        "canonical_height_override_authorized",
        "issuance_authority",
        "supply_authority",
        "validation_authority",
        "consensus_authority",
        "history_authority",
        "settlement_authority",
        "confirmation_claim_authorized",
        "automatic_reorg_authorized",
        "fork_winner_selected",
    }
    assert all(value is False for value in firewall.values())


def test_protocol_economics_history_validator_bitcoin_and_signer_are_preserved():
    protected = load_gate()["protected_invariants"]

    assert protected["protocol_version"] == "1.0.0"
    assert protected["protocol_invariants_changed"] is False
    assert protected["canonical_validator"] == "coin.tx_validation.validate_transaction"
    assert protected["transaction_validation_changed"] is False
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
    assert protected["canonical_height_authority"] == "CONSENSUS_DERIVED_ONLY"
    assert protected["historical_evidence_immutable"] is True
    assert protected["historical_state_changed"] is False
    assert protected["bitcoin_authority"] == "EXTERNAL_EVIDENCE_ONLY_ZERO_L28_AUTHORITY"
    assert protected["signer_runtime_authorized"] is False
    assert protected["option_a_normative_protocol_adoption"] is False

    assert tx_validation.L28_MAX_SUPPLY == 28000000
    assert tx_validation.L28_EMISSION_CEILING == 11130000
    assert tx_validation.L28_HISTORICAL_MINED == 2824584
    assert tx_validation.L28_HALVING_INTERVAL == 210000
    assert tx_validation.L28_REWARD_SCHEDULE == (28, 14, 7, 3, 1)
    assert tx_validation.L28_HISTORICAL_LAST_ENTRY == 100877
    assert tx_validation.L28_NEXT_HEIGHT_AFTER_CHECKPOINT == 100878
    assert callable(tx_validation.validate_transaction)


def test_protocol_and_validator_hashes_match_the_foundation152_baseline():
    baseline = load_gate()["baseline"]

    assert baseline["commit"] == "84f7b05ecf10f91dbfcdd5d8909b0df4a673f1f2"
    assert sha256(ROOT / "PROTOCOL.md") == baseline["protocol_sha256"]
    assert sha256(ROOT / "coin/tx_validation.py") == baseline["tx_validation_sha256"]


def test_new_artifacts_are_data_documentation_and_tests_without_runtime_imports():
    tree = ast.parse(TEST_FILE.read_text(encoding="utf-8"))
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    forbidden = {
        "socket",
        "subprocess",
        "multiprocessing",
        "asyncio",
        "requests",
        "urllib",
        "http",
        "wallet",
    }
    assert forbidden.isdisjoint(imports)

    assert GATE.suffix == ".json"
    assert RECORD.suffix == ".md"
    record = RECORD.read_text(encoding="utf-8")
    assert "AUTHORIZED_TO_EXECUTE=true" in record
    assert "AUTHORIZATION_CONSUMED=false" in record
    assert "CONSUMED_FOR_REUSE=false" in record
    assert "VALID_FOR_ACTIVE_EXECUTION=false" in record
    assert "EXPERIMENT_EXECUTED=false" in record


def test_duplicate_key_json_is_rejected_by_the_gate_loader():
    malformed = '{"status":"ready","status":"authorized"}'

    try:
        json.loads(malformed, object_pairs_hook=reject_duplicate_keys)
    except ValueError as error:
        assert str(error) == "duplicate key: status"
    else:
        raise AssertionError("duplicate JSON key accepted")
