# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/foundation155_f154_post_abort_reconnect_root_cause_review_v0.1.md"
DECISION = ROOT / "docs/l28_foundation155_f154_reconnect_remediation_decision_v0.1.json"
TEST_FILE = Path(__file__)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key: " + key)
        result[key] = value
    return result


def decision():
    return json.loads(
        DECISION.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def assess_corrected_design(candidate):
    if candidate["agent_count"] != 2 or candidate["process_count"] != 2:
        return "REJECT_SCOPE_EXPANSION"
    if candidate["agent_a_listener_host"] != "127.0.0.1":
        return "REJECT_NON_LOOPBACK"
    if candidate["agent_a_listener_port"] != 28428:
        return "REJECT_LISTENER_PORT"
    if candidate["agent_b_source_host"] != "127.0.0.1":
        return "REJECT_NON_LOOPBACK"
    if candidate["agent_b_bind_port_argument"] != 0:
        return "REJECT_FIXED_CLIENT_SOURCE_PORT"
    if candidate["agent_b_fixed_source_port_required"] is not False:
        return "REJECT_FIXED_CLIENT_SOURCE_PORT"
    if candidate["distinct_client_source_port_per_session_required"] is not True:
        return "REJECT_SOURCE_PORT_REUSE"
    if candidate["session_count"] != 2 or candidate["reconnect_count"] != 1:
        return "REJECT_SESSION_SCOPE"
    if candidate["maximum_duration_seconds"] != 60:
        return "REJECT_DURATION_SCOPE"
    if candidate["dns_or_hostname_resolution_permitted"] is not False:
        return "REJECT_DNS"
    if candidate["external_interface_or_route_permitted"] is not False:
        return "REJECT_EXTERNAL_NETWORK"
    if candidate["SO_REUSEPORT_permitted"] is not False:
        return "REJECT_BIND_SHARING"
    if candidate["abortive_close_permitted"] is not False:
        return "REJECT_ABORTIVE_CLOSE"
    if candidate["replay_state_preserved_across_sessions"] is not True:
        return "REJECT_REPLAY_STATE_LOSS"
    if candidate["option_a_halt_on_conflict_required"] is not True:
        return "REJECT_OPTION_A_REMOVAL"
    return "DECISION_READY_NOT_AUTHORIZED"


def test_f154_abort_and_consumed_lifecycle_are_preserved():
    data = decision()["foundation154"]
    assert data["result"] == "ABORT"
    assert data["evidence_remains_valid"] is True
    assert data["historical_artifacts_modified"] is False
    assert data["AUTHORIZATION_CONSUMED"] is True
    assert data["CONSUMED_FOR_REUSE"] is True
    assert data["VALID_FOR_ACTIVE_EXECUTION"] is False
    assert data["EXPERIMENT_EXECUTED"] is True
    assert data["RESTART_ALLOWED"] is False


def test_all_f154_artifact_bindings_match_without_modification():
    for relative, expected in decision()["foundation154"]["artifact_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_root_cause_distinguishes_observed_failure_from_tcp_state_inference():
    cause = decision()["root_cause"]
    assert cause["confirmed_failure_operation"] == "AGENT_B_SECOND_SESSION_CLIENT_BIND"
    assert cause["confirmed_endpoint"] == "127.0.0.1:28429"
    assert cause["failure_before_second_connect"] is True
    assert cause["tcp_teardown_or_time_wait_mechanism_applicable"] is True
    assert cause["exact_kernel_tcp_state_observed"] is False
    assert cause["replay_or_option_a_caused_failure"] is False


def test_corrected_design_is_purely_decision_ready_and_preserves_bounds():
    proposed = decision()["proposed_corrected_design"]
    assert assess_corrected_design(proposed) == "DECISION_READY_NOT_AUTHORIZED"
    assert proposed["agent_b_source_port_policy"] == (
        "OS_ASSIGNED_FRESH_EPHEMERAL_PER_SESSION"
    )
    assert proposed["identity_binding"] == [
        "authorization_id",
        "peer_id",
        "protocol_version",
        "network_id",
        "genesis_hash",
        "config_hash",
        "message_id",
        "nonce_replay_key",
    ]


def test_pure_design_model_fails_closed_on_fixed_port_and_scope_expansion():
    proposed = decision()["proposed_corrected_design"]
    fixed = deepcopy(proposed)
    fixed["agent_b_bind_port_argument"] = 28429
    assert assess_corrected_design(fixed) == "REJECT_FIXED_CLIENT_SOURCE_PORT"
    external = deepcopy(proposed)
    external["agent_b_source_host"] = "192.0.2.10"
    assert assess_corrected_design(external) == "REJECT_NON_LOOPBACK"
    expanded = deepcopy(proposed)
    expanded["process_count"] = 3
    assert assess_corrected_design(expanded) == "REJECT_SCOPE_EXPANSION"


def test_new_authorization_review_and_invocation_are_mandatory():
    scope = decision()["scope_assessment"]
    assert scope["isolation_weakened"] is False
    assert scope["authority_boundary_changed"] is False
    assert scope["transport_endpoint_contract_changed"] is True
    assert scope["foundation153_scope_reusable"] is False
    assert scope["NEW_AUTHORIZATION_REQUIRED"] is True
    assert scope["INDEPENDENT_REVIEW_REQUIRED"] is True
    assert scope["EXPLICIT_EXECUTION_INVOCATION_REQUIRED"] is True
    assert scope["AUTOMATIC_EXECUTION_AUTHORIZED"] is False
    assert scope["NO_EXECUTION_OCCURRED"] is True


def test_all_runtime_and_protocol_authorities_remain_false():
    assert set(decision()["authority_firewall"].values()) == {False}


def test_protected_facts_and_validator_hashes_remain_exact():
    protected = decision()["protected_invariants"]
    assert protected["hard_cap"] == 28000000
    assert protected["emission_ceiling"] == 11130000
    assert protected["historically_mined"] == 2824584
    assert protected["treasury_locked"] == 500000
    assert protected["circulating_snapshot"] == 2324584
    assert protected["halving_interval"] == 210000
    assert protected["reward_schedule"] == [28, 14, 7, 3, 1, 0]
    assert protected["historical_mined_through_entry"] == 100877
    assert protected["next_canonical_height"] == 100878
    assert hashlib.sha256((ROOT / "PROTOCOL.md").read_bytes()).hexdigest() == protected["protocol_sha256"]
    assert hashlib.sha256((ROOT / "coin/tx_validation.py").read_bytes()).hexdigest() == protected["tx_validation_sha256"]


def test_foundation155_test_and_artifacts_contain_no_execution_capability():
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
    combined = REVIEW.read_text(encoding="utf-8") + DECISION.read_text(encoding="utf-8")
    assert "NEW_AUTHORIZATION_REQUIRED=true" in combined
    assert "NO_EXECUTION_OCCURRED=true" in combined
