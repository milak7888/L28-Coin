# SPDX-License-Identifier: Apache-2.0
import ast
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tests/foundation154_one_shot_loopback_experiment_helper.py"
AUTHORIZATION = ROOT / "docs/l28_foundation153_option_a_one_shot_runtime_authorization_v1.0.json"
EVIDENCE = ROOT / "docs/foundation154_one_shot_loopback_experiment_evidence_v1.0.json"
STATE = ROOT / "docs/l28_foundation154_one_shot_execution_state_v1.0.json"

spec = importlib.util.spec_from_file_location("foundation154_helper", HELPER)
helper = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(helper)


def _authorization():
    return json.loads(AUTHORIZATION.read_text(encoding="utf-8"))


def _evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_dry_run_opens_no_socket_or_process_and_preserves_authorization():
    report = helper.dry_run_preflight()
    assert report["mode"] == "DRY_RUN_PREFLIGHT"
    assert report["sockets_opened"] is False
    assert report["processes_started"] is False
    assert report["authorization_consumed"] is False
    assert report["experiment_executed"] is False


def test_exact_authorized_topology_and_bounds():
    report = helper.dry_run_preflight()
    assert report["agent_count"] == 2
    assert report["process_count"] == 2
    assert report["host"] == "127.0.0.1"
    assert report["ports"] == [28428, 28429]
    assert report["session_count"] == 2
    assert report["reconnect_count"] == 1
    assert report["maximum_duration_seconds"] == 60


def test_authorization_binding_and_lifecycle_are_pre_start():
    data = helper.load_and_validate_authorization()
    assert data["authorization_id"] == "L28-F153-OPTION-A-ONE-SHOT-001"
    assert data["authorization_state"]["AUTHORIZATION_GRANTED"] is True
    assert data["authorization_state"]["AUTHORIZATION_CONSUMED"] is False
    assert data["authorization_state"]["CONSUMED_FOR_REUSE"] is False
    assert data["authorization_state"]["VALID_FOR_ACTIVE_EXECUTION"] is False
    assert data["authorization_state"]["EXPERIMENT_EXECUTED"] is False


def test_option_a_integration_is_fail_closed_and_retains_local_state():
    report = helper.dry_run_preflight()
    assert report["option_a_code"] == "HALT_SYNC_PEER_EQUIVOCATION"
    assert report["option_a_state"] == "HALTED_CONFLICT"


def test_external_or_expanded_scope_fails_closed(monkeypatch, tmp_path):
    data = _authorization()
    data["exact_authorized_future_experiment"]["agent_a"]["address"] = "127.0.0.2"
    forged = tmp_path / "forged-authorization.json"
    forged.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(helper, "AUTHORIZATION_PATH", forged)
    with pytest.raises(helper.Foundation154ExperimentError, match="authorization_scope_invalid"):
        helper.load_and_validate_authorization()


def test_all_disallowed_and_authority_fields_remain_false():
    data = _authorization()
    assert set(data["persistent_and_disallowed_authority"].values()) == {False}
    assert set(data["authority_firewall"].values()) == {False}


def test_helper_is_test_only_fixed_scope_and_has_no_forbidden_capability_imports():
    source = HELPER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                calls.add(node.func.id)
    assert {"wallet", "subprocess", "requests", "urllib", "http", "asyncio"}.isdisjoint(imports)
    assert {"getaddrinfo", "gethostbyname", "create_connection"}.isdisjoint(calls)
    assert 'HOST = "127.0.0.1"' in source
    assert "0.0.0.0" not in source
    assert "AF_INET6" not in source


def test_actual_one_shot_is_consumed_aborted_and_permanently_nonrestartable():
    evidence = _evidence()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    assert evidence["result"] == "ABORT"
    assert state["final_state"] == {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": True,
        "CONSUMED_FOR_REUSE": True,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXPERIMENT_EXECUTED": True,
        "RESTART_ALLOWED": False,
    }
    assert state["termination"]["retry_permitted"] is False


def test_abort_evidence_is_precise_and_does_not_invent_required_outcomes():
    observations = _evidence()["observations"]
    assert observations["execution_started"] is True
    assert observations["session_1_completed"] is True
    assert observations["session_count_completed"] == 1
    assert observations["reconnect_attempted"] is True
    assert observations["reconnect_count_completed"] == 0
    assert observations["reconnect_failure_code"] == "RECONNECT_SOURCE_PORT_REBIND_FAILED"
    for field in (
        "replay_state_preservation_exercised",
        "replay_rejection_exercised",
        "equivocation_exercised",
        "option_a_halt_exercised",
        "required_active_path_evidence_complete",
    ):
        assert observations[field] is False


def test_cleanup_and_authority_firewall_are_recorded_exactly():
    evidence = _evidence()
    assert evidence["cleanup"] == {
        "both_sockets_closed": True,
        "both_processes_stopped": True,
        "ports_28428_and_28429_free": True,
        "child_processes_remaining": 0,
        "temporary_state_cleaned": True,
        "persistent_service_created": False,
        "cleanup_result": "PASS",
    }
    assert set(evidence["authority_invariants"].values()) == {False}


def test_protected_facts_validator_and_f37_status_are_unchanged():
    evidence = _evidence()
    protected = evidence["protected_invariants"]
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
    assert evidence["f37_reassessment"]["foundation154_advancement"] is False


def test_consumed_state_blocks_any_future_runner_start():
    with pytest.raises(helper.Foundation154ExperimentError, match="authorization_already_consumed"):
        helper.run_authorized_experiment_once()
