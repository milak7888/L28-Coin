# SPDX-License-Identifier: Apache-2.0

import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from coin import tx_validation


ROOT = Path(__file__).resolve().parents[1]
AUTHORIZATION = (
    ROOT
    / "docs/l28_foundation153_option_a_one_shot_runtime_authorization_v1.0.json"
)
RECORD = ROOT / "docs/foundation153_option_a_one_shot_runtime_authorization_v1.0.md"
F152_RECORD = (
    ROOT
    / "docs/foundation152_bounded_runtime_network_authorization_decision_package_v0.1.md"
)
F152_GATE = ROOT / "docs/l28_foundation152_runtime_network_decision_gate_v0.1.json"
TEST_FILE = Path(__file__)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def load_authorization():
    return json.loads(
        AUTHORIZATION.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transition_lifecycle(state, event):
    next_state = deepcopy(state)

    if event == "SUCCESSFUL_START":
        if state["consumed_for_reuse"] or not state["first_start_consumption_available"]:
            return "REJECT_RESTART_FAIL_CLOSED", state
        next_state.update(
            authorization_consumed=True,
            consumed_for_reuse=True,
            valid_for_active_execution=True,
            experiment_executed=True,
            first_start_consumption_available=False,
        )
        return "ACTIVE_EXECUTION", next_state

    if event in {"NORMAL_COMPLETION", "ABORT", "SIXTY_SECOND_MAXIMUM_DEADLINE"}:
        if not state["valid_for_active_execution"]:
            return "REJECT_INVALID_TERMINATION_FAIL_CLOSED", state
        next_state["valid_for_active_execution"] = False
        return "TERMINATED_EXECUTION", next_state

    return "REJECT_UNKNOWN_EVENT_FAIL_CLOSED", state


def test_operator_selected_exactly_one_foundation152_decision_option():
    data = load_authorization()
    decision = data["operator_decision"]

    assert data["status"] == (
        "AUTHORIZATION_GRANTED_EXECUTION_GATE_CLOSED_NOT_CONSUMED"
    )
    assert data["authorization_id"] == "L28-F153-OPTION-A-ONE-SHOT-001"
    assert decision["selected_option"] == (
        "AUTHORIZE_ONE_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT"
    )
    assert decision["decision_explicit"] is True
    assert decision["accountable_authority"] == "L28_REPOSITORY_OPERATOR"
    assert decision["human_signature_claimed"] is False


def test_authorization_is_granted_not_consumed_and_not_executed():
    state = load_authorization()["authorization_state"]

    assert state == {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": False,
        "CONSUMED_FOR_REUSE": False,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXPERIMENT_EXECUTED": False,
        "execution_gate_open": False,
        "execution_prerequisites_satisfied": False,
    }


def test_authorization_is_one_shot_specific_nontransferable_and_nonpersistent():
    characteristics = load_authorization()["authorization_characteristics"]

    assert characteristics == {
        "explicit": True,
        "one_shot": True,
        "experiment_specific": True,
        "non_transferable": True,
        "reusable": False,
        "persistent_networking_authority": False,
        "scope_expansion_permitted": False,
    }


def test_foundation152_source_artifacts_are_bound_by_exact_digest():
    binding = load_authorization()["source_binding"]

    assert binding["parent_commit"] == (
        "84f7b05ecf10f91dbfcdd5d8909b0df4a673f1f2"
    )
    assert binding["foundation152_profile"] == (
        "l28-foundation152-runtime-network-decision-gate/v0.1"
    )
    assert sha256(F152_RECORD) == binding["foundation152_record_sha256"]
    assert sha256(F152_GATE) == binding["foundation152_gate_sha256"]


def test_exact_two_agent_two_process_loopback_scope_is_fixed():
    scope = load_authorization()["exact_authorized_future_experiment"]

    assert scope["agent_count"] == 2
    assert scope["process_count"] == 2
    assert scope["same_local_machine_required"] is True
    assert scope["ipv4_loopback_only"] is True
    assert scope["external_interfaces_or_routes_permitted"] is False
    assert scope["agent_a"] == {
        "id": "agent-a",
        "role": "DESIGNATED_LOCAL_CORE_WRITER",
        "address": "127.0.0.1",
        "port": 28428,
        "process": "process-a",
    }
    assert scope["agent_b"] == {
        "id": "agent-b",
        "role": "PEER_EVIDENCE_ONLY",
        "address": "127.0.0.1",
        "port": 28429,
        "process": "process-b",
    }


def test_session_duration_message_and_identity_bounds_are_exact():
    scope = load_authorization()["exact_authorized_future_experiment"]

    assert scope["maximum_duration_seconds"] == 60
    assert scope["exact_session_count"] == 2
    assert scope["exact_reconnect_count"] == 1
    assert scope["max_frame_bytes"] == 4096
    assert scope["max_payload_bytes"] == 2048
    assert scope["max_messages_per_session"] == 32
    assert scope["permitted_message_types"] == [
        "HELLO",
        "TIP_EVIDENCE",
        "CANDIDATE_EVIDENCE",
    ]
    assert scope["production_identities_or_secrets_permitted"] is False
    assert scope["historical_or_real_value_state_permitted"] is False


def test_replay_and_reviewed_option_a_behavior_are_mandatory():
    scope = load_authorization()["exact_authorized_future_experiment"]

    assert scope["replay_state_preserved_across_reconnect"] is True
    assert scope["option_a_conflict_and_equivocation_handling_mandatory"] is True
    assert scope["option_a_required_transition"] == "SYNCING_TO_HALTED_CONFLICT"
    assert scope["retain_current_local_canonical_state"] is True


def test_execution_prerequisites_keep_this_task_nonexecuting_and_fail_closed():
    prerequisites = load_authorization()["execution_prerequisites"]

    assert prerequisites["explicit_future_execution_invocation_required"] is True
    assert prerequisites["exact_source_bindings_must_match"] is True
    assert prerequisites["foundation152_and_foundation153_tests_must_pass"] is True
    assert prerequisites["reviewed_test_only_executor_required"] is True
    assert prerequisites["executor_present_in_this_candidate"] is False
    assert prerequisites["two_fresh_isolated_data_directories_required"] is True
    assert prerequisites["declared_loopback_endpoints_only"] is True
    assert prerequisites["all_prerequisites_fail_closed"] is True


def test_consumption_is_atomic_once_only_and_has_not_occurred():
    lifecycle = load_authorization()["consumption_expiration_and_lifecycle"]

    assert lifecycle["consume_at"] == (
        "ATOMIC_SUCCESSFUL_EXECUTION_START_TRANSITION"
    )
    assert lifecycle["consumed_now"] is False
    assert lifecycle["consumed_for_reuse_now"] is False
    assert lifecycle["valid_for_active_execution_now"] is False
    assert lifecycle["execution_count_before_consumption"] == 0
    assert lifecycle["maximum_execution_count"] == 1
    assert lifecycle["maximum_execution_window_seconds_after_consumption"] == 60
    assert lifecycle["successful_start_consumes_for_reuse_exactly_once"] is True
    assert lifecycle["consumption_does_not_invalidate_started_execution"] is True
    assert lifecycle["second_start_permitted"] is False
    assert lifecycle["restart_after_stop_abort_or_timeout_permitted"] is False
    assert lifecycle["missing_invalid_changed_or_previously_consumed_start_action"] == (
        "DO_NOT_START_FAIL_CLOSED"
    )


def test_lifecycle_pre_start_is_unconsumed_and_inactive():
    lifecycle = load_authorization()["consumption_expiration_and_lifecycle"]
    pre_start = lifecycle["state_model"]["pre_start"]

    assert pre_start == {
        "authorization_granted": True,
        "authorization_consumed": False,
        "consumed_for_reuse": False,
        "valid_for_active_execution": False,
        "experiment_executed": False,
        "first_start_consumption_available": True,
    }


def test_first_successful_start_consumes_reuse_but_keeps_execution_valid():
    states = load_authorization()["consumption_expiration_and_lifecycle"]["state_model"]
    result, active = transition_lifecycle(states["pre_start"], "SUCCESSFUL_START")

    assert result == "ACTIVE_EXECUTION"
    assert active == states["active_execution"]
    assert active["authorization_consumed"] is True
    assert active["consumed_for_reuse"] is True
    assert active["valid_for_active_execution"] is True


def test_second_start_is_rejected_without_invalidating_active_execution():
    states = load_authorization()["consumption_expiration_and_lifecycle"]["state_model"]
    result, retained = transition_lifecycle(states["active_execution"], "SUCCESSFUL_START")

    assert result == "REJECT_RESTART_FAIL_CLOSED"
    assert retained == states["active_execution"]
    assert retained["valid_for_active_execution"] is True


def test_completion_abort_and_deadline_end_only_active_validity():
    lifecycle = load_authorization()["consumption_expiration_and_lifecycle"]
    states = lifecycle["state_model"]

    assert lifecycle["active_execution_validity_ends_at_earliest_of"] == [
        "NORMAL_COMPLETION",
        "ABORT",
        "SIXTY_SECOND_MAXIMUM_DEADLINE",
    ]
    for event in lifecycle["active_execution_validity_ends_at_earliest_of"]:
        result, terminated = transition_lifecycle(states["active_execution"], event)
        assert result == "TERMINATED_EXECUTION"
        assert terminated == states["terminated_execution"]
        assert terminated["authorization_consumed"] is True
        assert terminated["consumed_for_reuse"] is True
        assert terminated["valid_for_active_execution"] is False


def test_consumed_terminated_authorization_can_never_restart():
    states = load_authorization()["consumption_expiration_and_lifecycle"]["state_model"]
    result, retained = transition_lifecycle(
        states["terminated_execution"],
        "SUCCESSFUL_START",
    )

    assert result == "REJECT_RESTART_FAIL_CLOSED"
    assert retained == states["terminated_execution"]
    assert retained["first_start_consumption_available"] is False


def test_abort_evidence_and_cleanup_requirements_are_complete():
    data = load_authorization()
    evidence = data["required_evidence"]

    assert len(data["abort_criteria"]) == 15
    assert "EXECUTION_GATE_NOT_OPEN" in data["abort_criteria"]
    assert "PEER_CONFLICT_OR_EQUIVOCATION" in data["abort_criteria"]
    assert "EVIDENCE_CAPTURE_OR_CLEANUP_FAILURE" in data["abort_criteria"]
    for field in (
        "authorization_id_scope_digest_and_atomic_consumption",
        "process_agent_endpoint_and_lifecycle_observations",
        "ordered_public_frame_ids_and_sha256_digests",
        "session_reconnect_replay_scope_and_rejection",
        "option_a_assessment_transition_and_sticky_halt",
        "local_canonical_state_before_and_after",
        "abort_completion_timeout_and_cleanup_result",
        "complete_evidence_required_for_pass",
    ):
        assert evidence[field] is True
    assert evidence["secret_or_private_evidence_permitted"] is False

    cleanup = data["cleanup_requirements"]
    assert cleanup["message_admission_stopped"] is True
    assert cleanup["both_loopback_endpoints_closed"] is True
    assert cleanup["both_processes_stopped"] is True
    assert cleanup["both_disposable_data_directories_removed"] is True
    assert cleanup["authorization_remains_consumed"] is True
    assert cleanup["persistent_listener_session_process_or_state_permitted"] is False


def test_only_exact_one_shot_capabilities_are_true_and_all_other_authority_false():
    data = load_authorization()
    capabilities = data["authorized_one_shot_capabilities"]

    assert capabilities == {
        "network": True,
        "socket": True,
        "process_start_stop": True,
        "isolated_disposable_filesystem_state": True,
        "only_while_valid_for_active_execution": True,
    }
    assert all(
        value is False
        for value in data["persistent_and_disallowed_authority"].values()
    )
    assert all(value is False for value in data["authority_firewall"].values())


def test_protocol_economics_history_validator_bitcoin_and_signer_are_preserved():
    protected = load_authorization()["protected_invariants"]

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
    assert protected["option_a_scope"] == "REVIEWED_NON_NORMATIVE_SAFETY_BOUNDARY_ONLY"

    assert tx_validation.L28_MAX_SUPPLY == 28000000
    assert tx_validation.L28_EMISSION_CEILING == 11130000
    assert tx_validation.L28_HISTORICAL_MINED == 2824584
    assert tx_validation.L28_HALVING_INTERVAL == 210000
    assert tx_validation.L28_REWARD_SCHEDULE == (28, 14, 7, 3, 1)
    assert tx_validation.L28_HISTORICAL_LAST_ENTRY == 100877
    assert tx_validation.L28_NEXT_HEIGHT_AFTER_CHECKPOINT == 100878
    assert callable(tx_validation.validate_transaction)


def test_new_foundation153_artifacts_do_not_import_or_invoke_runtime_stacks():
    tree = ast.parse(TEST_FILE.read_text(encoding="utf-8"))
    imports = set()
    dangerous_calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                dangerous_calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                dangerous_calls.add(node.func.attr)

    forbidden_imports = {
        "socket",
        "subprocess",
        "multiprocessing",
        "asyncio",
        "requests",
        "urllib",
        "http",
    }
    forbidden_calls = {
        "bind",
        "connect",
        "listen",
        "Popen",
        "run",
        "system",
        "fork",
    }
    assert forbidden_imports.isdisjoint(imports)
    assert forbidden_calls.isdisjoint(dangerous_calls)

    record = RECORD.read_text(encoding="utf-8")
    assert "AUTHORIZATION_GRANTED=true" in record
    assert "AUTHORIZATION_CONSUMED=false" in record
    assert "CONSUMED_FOR_REUSE=false" in record
    assert "VALID_FOR_ACTIVE_EXECUTION=false" in record
    assert "EXPERIMENT_EXECUTED=false" in record


def test_duplicate_key_json_is_rejected_by_the_authorization_loader():
    malformed = '{"AUTHORIZATION_GRANTED":true,"AUTHORIZATION_GRANTED":false}'

    try:
        json.loads(malformed, object_pairs_hook=reject_duplicate_keys)
    except ValueError as error:
        assert str(error) == "duplicate key: AUTHORIZATION_GRANTED"
    else:
        raise AssertionError("duplicate JSON key accepted")
