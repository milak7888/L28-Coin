# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/l28_foundation156_corrected_reconnect_authorization_gate_v0.1.json"
PACKAGE = ROOT / "docs/foundation156_corrected_reconnect_one_shot_authorization_package_v0.1.md"
TEST_FILE = Path(__file__)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key: " + key)
        result[key] = value
    return result


def gate():
    return json.loads(
        GATE.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def assess_scope(scope):
    if scope["agent_count"] != 2 or scope["process_count"] != 2:
        return "REJECT_SCOPE_EXPANSION"
    if scope["agent_a"] != {
        "id": "agent-a",
        "role": "DESIGNATED_LOCAL_CORE_WRITER_AND_FIXED_LISTENER",
        "listener_address": "127.0.0.1",
        "listener_port": 28428,
        "process": "process-a",
    }:
        return "REJECT_AGENT_A_ENDPOINT"
    agent_b = scope["agent_b"]
    if agent_b["source_address"] != "127.0.0.1":
        return "REJECT_NON_LOOPBACK"
    if agent_b["bind_port_argument"] != 0:
        return "REJECT_FIXED_CLIENT_SOURCE_PORT"
    if agent_b["fixed_source_port_28429_permitted"] is not False:
        return "REJECT_FIXED_CLIENT_SOURCE_PORT"
    if agent_b["distinct_source_port_per_session_required"] is not True:
        return "REJECT_SOURCE_PORT_REUSE"
    if scope["exact_session_count"] != 2 or scope["exact_reconnect_count"] != 1:
        return "REJECT_SESSION_SCOPE"
    if scope["maximum_active_duration_seconds"] != 60:
        return "REJECT_DURATION_SCOPE"
    if scope["ipv4_loopback_only"] is not True:
        return "REJECT_NON_LOOPBACK"
    if scope["external_interfaces_or_routes_permitted"] is not False:
        return "REJECT_EXTERNAL_NETWORK"
    return "DECISION_READY_NOT_AUTHORIZED"


def test_exact_baseline_and_f155_artifact_bindings_match():
    source = gate()["source_binding"]
    assert source["baseline_commit"] == "2d5b6c65255cc21b50ea6632231c6c18f02dfd1b"
    for path_key, digest_key in (
        ("foundation155_review", "foundation155_review_sha256"),
        ("foundation155_decision", "foundation155_decision_sha256"),
        ("foundation154_execution_state", "foundation154_execution_state_sha256"),
        ("foundation153_authorization", "foundation153_authorization_sha256"),
    ):
        assert hashlib.sha256((ROOT / source[path_key]).read_bytes()).hexdigest() == source[digest_key]


def test_f153_consumed_history_f154_abort_and_f155_review_are_preserved():
    history = gate()["authoritative_history"]
    assert history["foundation153_record_role"] == "IMMUTABLE_PRE_EXECUTION_AUTHORIZATION_SNAPSHOT"
    assert history["foundation153_reusable"] is False
    assert history["foundation154_result"] == "ABORT"
    assert history["foundation154_current_terminal_state"] == {
        "AUTHORIZATION_CONSUMED": True,
        "CONSUMED_FOR_REUSE": True,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXPERIMENT_EXECUTED": True,
        "RESTART_ALLOWED": False,
    }
    assert history["foundation155_committed_record_disposition"] == {
        "PASS": 2,
        "GAP": 1,
        "BLOCKED": 1,
    }
    assert history["foundation155_later_independent_review"] == "PASS"
    assert history["foundation155_later_independent_review_disposition"] == {
        "PASS": 15,
        "GAP": 0,
        "BLOCKED": 0,
    }
    assert history["historical_artifacts_modified"] is False


def test_foundation157_operator_decision_is_explicit_and_selected_exactly():
    decision = gate()["operator_decision"]
    assert gate()["authorization_id"] == "L28-F157-CORRECTED-RECONNECT-ONE-SHOT-001"
    assert decision["selection_status"] == "SELECTED_BY_EXPLICIT_OPERATOR_DECISION"
    assert decision["selected_option"] == (
        "AUTHORIZE_ONE_CORRECTED_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT"
    )
    assert decision["decision_explicit"] is True
    assert decision["decision_source"] == "FOUNDATION157_OPERATOR_INSTRUCTION"
    assert decision["options"] == [
        "AUTHORIZE_ONE_CORRECTED_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT",
        "DEFER",
        "REJECT_AND_REVISE",
    ]
    assert decision["automatic_selection_permitted"] is False


def test_authorization_is_granted_but_unconsumed_inactive_and_unexecuted():
    assert gate()["authorization_state"] == {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": False,
        "CONSUMED_FOR_REUSE": False,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXPERIMENT_EXECUTED": False,
        "EXECUTION_GATE_OPEN": False,
    }


def test_corrected_scope_requires_ephemeral_loopback_client_ports():
    scope = gate()["corrected_future_experiment"]
    assert assess_scope(scope) == "DECISION_READY_NOT_AUTHORIZED"
    assert scope["agent_b"]["source_port_policy"] == (
        "OS_ASSIGNED_FRESH_EPHEMERAL_PER_SESSION"
    )
    assert scope["replay_state_preserved_across_reconnect"] is True
    assert scope["option_a_required_transition"] == "SYNCING_TO_HALTED_CONFLICT"
    assert scope["retain_current_local_canonical_state"] is True


def test_fixed_client_port_and_external_or_expanded_scope_fail_closed():
    scope = gate()["corrected_future_experiment"]
    fixed = deepcopy(scope)
    fixed["agent_b"]["bind_port_argument"] = 28429
    assert assess_scope(fixed) == "REJECT_FIXED_CLIENT_SOURCE_PORT"
    external = deepcopy(scope)
    external["agent_b"]["source_address"] = "192.0.2.1"
    assert assess_scope(external) == "REJECT_NON_LOOPBACK"
    expanded = deepcopy(scope)
    expanded["process_count"] = 3
    assert assess_scope(expanded) == "REJECT_SCOPE_EXPANSION"


def test_application_identity_and_replay_are_transport_port_independent():
    binding = gate()["application_identity_and_replay_binding"]
    assert binding["transport_source_port_is_identity_authority"] is False
    assert binding["required_bindings"] == [
        "authorization_id",
        "peer_id",
        "protocol_version",
        "network_id",
        "genesis_hash",
        "config_hash",
        "message_id",
        "nonce_replay_key",
    ]
    assert binding["binding_persists_across_both_sessions"] is True
    assert binding["replay_state_is_independent_of_transport_source_port"] is True


def test_lifecycle_separates_authorization_recording_start_and_termination():
    lifecycle = gate()["lifecycle"]
    assert lifecycle["initial_decision_ready"]["AUTHORIZATION_GRANTED"] is False
    assert lifecycle["initial_decision_ready"]["EXECUTION_GATE_OPEN"] is False
    assert lifecycle["authorized_pre_start"] == gate()["authorization_state"]
    assert lifecycle["authorized_pre_start"]["AUTHORIZATION_GRANTED"] is True
    assert lifecycle["authorized_pre_start"]["EXECUTION_GATE_OPEN"] is False
    assert lifecycle["successful_start"]["AUTHORIZATION_CONSUMED"] is True
    assert lifecycle["successful_start"]["CONSUMED_FOR_REUSE"] is True
    assert lifecycle["successful_start"]["VALID_FOR_ACTIVE_EXECUTION"] is True
    assert lifecycle["terminated"]["VALID_FOR_ACTIVE_EXECUTION"] is False
    assert lifecycle["terminated"]["RESTART_ALLOWED"] is False
    assert lifecycle["second_or_repeated_start_permitted"] is False


def test_fail_closed_prerequisites_require_new_authorization_and_invocation():
    prerequisites = gate()["fail_closed_prerequisites"]
    assert prerequisites["new_explicit_authorization_granted_unconsumed_and_unexpired_required"] is True
    assert prerequisites["separate_explicit_execution_invocation_required"] is True
    assert prerequisites["agent_a_listener_127_0_0_1_28428_free_required"] is True
    assert prerequisites["agent_b_bind_127_0_0_1_port_zero_required"] is True
    assert prerequisites["agent_b_fixed_source_port_28429_forbidden"] is True
    assert prerequisites["missing_invalid_changed_or_conflicting_evidence_action"] == (
        "DO_NOT_START_FAIL_CLOSED"
    )


def test_all_prohibited_authority_remains_false():
    assert set(gate()["authority_firewall"].values()) == {False}


def test_protected_facts_validator_and_non_normative_option_a_are_exact():
    protected = gate()["protected_invariants"]
    assert protected["hard_cap"] == 28000000
    assert protected["emission_ceiling"] == 11130000
    assert protected["historically_mined"] == 2824584
    assert protected["treasury_locked"] == 500000
    assert protected["circulating_snapshot"] == 2324584
    assert protected["halving_interval"] == 210000
    assert protected["reward_schedule"] == [28, 14, 7, 3, 1, 0]
    assert protected["historical_mined_through_entry"] == 100877
    assert protected["next_canonical_height"] == 100878
    assert protected["canonical_validator"] == "coin.tx_validation.validate_transaction"
    assert protected["option_a_scope"] == "REVIEWED_NON_NORMATIVE_SAFETY_BOUNDARY_ONLY"
    assert hashlib.sha256((ROOT / "PROTOCOL.md").read_bytes()).hexdigest() == protected["protocol_sha256"]
    assert hashlib.sha256((ROOT / "coin/tx_validation.py").read_bytes()).hexdigest() == protected["tx_validation_sha256"]


def test_readiness_grants_no_authorization_or_execution():
    readiness = gate()["readiness"]
    assert readiness == {
        "NEW_AUTHORIZATION_REQUIRED": True,
        "NEW_AUTHORIZATION_REQUIREMENT_SATISFIED": True,
        "INDEPENDENT_REVIEW_REQUIRED_BEFORE_EXECUTION": True,
        "EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "AUTHORIZATION_RECORDED": True,
        "EXECUTION_AUTHORIZED": False,
        "NO_EXECUTION_OCCURRED": True,
        "f37_status_changed": False,
    }


def test_foundation156_files_have_no_runtime_execution_capability():
    source = TEST_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                calls.add(node.func.id)
    assert {"socket", "multiprocessing", "subprocess", "requests", "urllib", "http", "asyncio"}.isdisjoint(imports)
    assert {"connect", "bind", "listen", "accept", "start", "run", "Popen"}.isdisjoint(calls)
    combined = PACKAGE.read_text(encoding="utf-8") + GATE.read_text(encoding="utf-8")
    assert "AUTHORIZATION_GRANTED=true" in combined
    assert "EXECUTION_GATE_OPEN=false" in combined
    assert "NO_EXECUTION_OCCURRED" in combined
