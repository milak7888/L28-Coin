# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import importlib.util
import json
import threading
import time
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tests/foundation158_corrected_one_shot_execution_helper.py"
GATE = (
    ROOT
    / "docs/l28_foundation158_corrected_one_shot_execution_preflight_gate_v0.1.json"
)
DOCUMENT = (
    ROOT / "docs/foundation158_corrected_one_shot_execution_preflight_v0.1.md"
)

spec = importlib.util.spec_from_file_location("foundation158_helper", HELPER)
helper = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(helper)


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


class FakeProcess:
    def __init__(
        self,
        *,
        stall_start=False,
        ignore_terminate=False,
        ignore_kill=False,
        terminate_error=None,
        join_error=None,
        kill_error=None,
    ):
        self.pid = 1
        self.alive = True
        self.stall_start = stall_start
        self.ignore_terminate = ignore_terminate
        self.ignore_kill = ignore_kill
        self.terminate_error = terminate_error
        self.join_error = join_error
        self.kill_error = kill_error
        self.start_release = threading.Event()
        self.terminate_calls = 0
        self.kill_calls = 0

    def start(self):
        if self.stall_start:
            self.start_release.wait()

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminate_calls += 1
        self.start_release.set()
        if self.terminate_error is not None:
            raise self.terminate_error
        if not self.ignore_terminate:
            self.alive = False

    def kill(self):
        self.kill_calls += 1
        self.start_release.set()
        if self.kill_error is not None:
            raise self.kill_error
        if not self.ignore_kill:
            self.alive = False

    def join(self, _timeout=0):
        if self.join_error is not None:
            raise self.join_error


def cleanup_with_fake(monkeypatch, process, tmp_path=None):
    monkeypatch.setattr(helper, "_port_a_is_free", lambda: True)
    return helper._cleanup_after_claim(
        [process],
        [],
        tmp_path,
    )


def test_exact_baseline_authorization_and_artifact_bindings_match():
    data = gate()
    source = data["source_binding"]
    assert source["repository"] == "milak7888/L28-Coin"
    assert source["baseline_commit"] == (
        "25d3bdc8ec77b96c0af717b1864650388559da5e"
    )
    assert data["authorization_id"] == (
        "L28-F157-CORRECTED-RECONNECT-ONE-SHOT-001"
    )
    for path_key, digest_key in (
        ("foundation157_package", "foundation157_package_sha256"),
        ("foundation157_authorization", "foundation157_authorization_sha256"),
        ("foundation157_tests", "foundation157_tests_sha256"),
        ("foundation158_helper", "foundation158_helper_sha256"),
    ):
        assert hashlib.sha256((ROOT / source[path_key]).read_bytes()).hexdigest() == (
            source[digest_key]
        )


def test_authoritative_history_and_f157_pre_start_state_are_exact():
    data = gate()
    assert data["authoritative_history"] == {
        "foundation153_authorization_consumed_permanently": True,
        "foundation154_result": "ABORT",
        "foundation155_corrected_reconnect_design_review": "PASS",
        "foundation157_authorization_granted": True,
        "historical_artifacts_modified": False,
    }
    assert data["authorization_state"] == {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": False,
        "CONSUMED_FOR_REUSE": False,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXPERIMENT_EXECUTED": False,
        "EXECUTION_GATE_OPEN": False,
    }


def test_dry_run_opens_no_socket_or_process_and_consumes_nothing(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("runtime capability used during dry run")

    monkeypatch.setattr(helper.socket, "socket", forbidden)
    monkeypatch.setattr(helper.multiprocessing, "get_context", forbidden)
    monkeypatch.setattr(helper, "_claim_authorization", forbidden)
    report = helper.dry_run_preflight()
    assert report["mode"] == "DRY_RUN_PREFLIGHT"
    assert report["sockets_opened"] is False
    assert report["processes_started"] is False
    assert report["network_traffic"] is False
    assert report["authorization_consumed"] is False
    assert report["execution_gate_open"] is False
    assert report["experiment_executed"] is False


def test_dry_run_proves_identity_replay_option_a_and_unchanged_state():
    report = helper.dry_run_preflight()
    assert report["transport_port_is_peer_identity"] is False
    assert report["application_identity_persists_across_reconnect"] is True
    assert report["replay_state_persists_across_reconnect"] is True
    assert report["continuity"] == {
        "peer_id": "agent-b",
        "replay_code": "message_replayed",
        "replay_disconnect": True,
        "option_a_code": "HALT_SYNC_PEER_EQUIVOCATION",
        "option_a_state": "HALTED_CONFLICT",
        "retain_current_local_canonical_state": True,
        "ledger_mutated": False,
        "canonical_state_changed": False,
    }
    assert report["local_height_before"] == report["local_height_after"] == 0
    assert report["candidate_auto_applied"] is False
    assert report["automatic_reorg"] is False
    assert report["fork_winner_selected"] is False


def test_every_application_frame_binds_authorization_not_transport_port():
    binding, tip = helper._runtime_context()
    frames = helper._build_frames(binding, tip)
    for encoded in frames.values():
        frame = json.loads(encoded)
        assert frame["payload"]["authorization_id"] == (
            "L28-F157-CORRECTED-RECONNECT-ONE-SHOT-001"
        )
        assert "transport_source_port" not in frame
        assert "transport_source_port" not in frame["payload"]


def test_exact_corrected_endpoint_and_session_scope_is_bound_to_f157():
    report = helper.dry_run_preflight()
    scope = gate()["future_execution_scope"]
    assert report["agent_count"] == scope["agent_count"] == 2
    assert report["process_count"] == scope["process_count"] == 2
    assert report["agent_a_listener"] == ["127.0.0.1", 28428]
    assert report["agent_b_bind"] == ["127.0.0.1", 0]
    assert report["fixed_agent_b_source_port_28429_permitted"] is False
    assert report["fresh_ephemeral_source_port_per_session"] is True
    assert report["session_count"] == scope["exact_session_count"] == 2
    assert report["reconnect_count"] == scope["exact_reconnect_count"] == 1
    assert report["maximum_active_duration_seconds"] == 60


def test_tampered_fixed_client_port_and_scope_expansion_fail_closed(
    monkeypatch, tmp_path
):
    original = gate()
    for mutation, code in (
        (("future_execution_scope", "agent_b", "bind_port_argument", 28429),
         "execution_scope_binding_mismatch"),
        (("future_execution_scope", "process_count", 3),
         "execution_scope_binding_mismatch"),
    ):
        changed = deepcopy(original)
        target = changed
        for key in mutation[:-2]:
            target = target[key]
        target[mutation[-2]] = mutation[-1]
        forged = tmp_path / (code + str(len(list(tmp_path.iterdir()))) + ".json")
        forged.write_text(json.dumps(changed), encoding="utf-8")
        monkeypatch.setattr(helper, "PREFLIGHT_GATE_PATH", forged)
        with pytest.raises(helper.Foundation158PreflightError, match=code):
            helper.load_and_validate_preflight()
        monkeypatch.setattr(helper, "PREFLIGHT_GATE_PATH", GATE)


def test_execution_lifecycle_is_atomic_single_use_and_permanently_terminal():
    lifecycle = gate()["execution_lifecycle"]
    assert lifecycle["pre_start"] == gate()["authorization_state"]
    assert lifecycle["successful_start"] == {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": True,
        "CONSUMED_FOR_REUSE": True,
        "VALID_FOR_ACTIVE_EXECUTION": True,
        "EXECUTION_GATE_OPEN": True,
        "EXPERIMENT_EXECUTED": True,
    }
    assert lifecycle["termination"] == {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": True,
        "CONSUMED_FOR_REUSE": True,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXECUTION_GATE_OPEN": False,
        "EXPERIMENT_EXECUTED": True,
        "RESTART_ALLOWED": False,
    }
    assert lifecycle["atomic_consumption_required_before_process_or_socket_start"] is True
    assert lifecycle["deadline_established_immediately_after_atomic_consumption"] is True
    assert lifecycle["process_setup_supervised_within_deadline"] is True
    assert lifecycle["process_start_supervised_within_deadline"] is True
    assert lifecycle["terminal_state_persistence_attempted_regardless_of_cleanup_errors"] is True
    assert lifecycle["terminalization_failure_reported_explicitly"] is True
    assert lifecycle["second_start_permitted"] is False
    assert lifecycle["restart_after_any_result_permitted"] is False


def test_disposable_claim_is_exclusive_and_terminal_without_runtime(
    monkeypatch, tmp_path
):
    disposable_state = tmp_path / "foundation158-state.json"
    monkeypatch.setattr(helper, "EXECUTION_STATE_PATH", disposable_state)
    helper._claim_authorization()
    claimed = json.loads(disposable_state.read_text(encoding="utf-8"))
    assert claimed["state"]["AUTHORIZATION_CONSUMED"] is True
    assert claimed["state"]["CONSUMED_FOR_REUSE"] is True
    with pytest.raises(
        helper.Foundation158PreflightError,
        match="authorization_already_consumed",
    ):
        helper._claim_authorization()
    helper._finalize_authorization("ABORT")
    terminal = json.loads(disposable_state.read_text(encoding="utf-8"))
    assert terminal["result"] == "ABORT"
    assert terminal["state"] == {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": True,
        "CONSUMED_FOR_REUSE": True,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXECUTION_GATE_OPEN": False,
        "EXPERIMENT_EXECUTED": True,
        "RESTART_ALLOWED": False,
    }


def test_child_ignoring_terminate_is_killed_and_removed(monkeypatch):
    process = FakeProcess(ignore_terminate=True)
    cleanup = cleanup_with_fake(monkeypatch, process)
    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert cleanup["cleanup_success"] is True
    assert cleanup["child_processes_remaining"] == 0


def test_child_alive_after_strong_escalation_is_terminal_cleanup_failure(monkeypatch):
    process = FakeProcess(ignore_terminate=True, ignore_kill=True)
    cleanup = cleanup_with_fake(monkeypatch, process)
    assert cleanup["cleanup_success"] is False
    assert cleanup["processes_terminated"] is False
    assert cleanup["child_processes_remaining"] == 1


@pytest.mark.parametrize(
    ("process", "error_fragment"),
    [
        (FakeProcess(terminate_error=RuntimeError("terminate failed")), "terminate"),
        (FakeProcess(join_error=RuntimeError("join failed")), "join_after_terminate"),
        (
            FakeProcess(
                ignore_terminate=True,
                kill_error=RuntimeError("kill failed"),
            ),
            "kill",
        ),
    ],
)
def test_process_cleanup_errors_are_recorded_without_false_success(
    monkeypatch, process, error_fragment
):
    cleanup = cleanup_with_fake(monkeypatch, process)
    assert cleanup["cleanup_success"] is False
    assert any(error_fragment in error for error in cleanup["errors"])


def test_temp_state_cleanup_error_is_recorded(monkeypatch, tmp_path):
    disposable = tmp_path / "state"
    disposable.mkdir()
    monkeypatch.setattr(
        helper.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(RuntimeError("rmtree failed")),
    )
    cleanup = cleanup_with_fake(monkeypatch, FakeProcess(ignore_terminate=False), disposable)
    assert cleanup["cleanup_success"] is False
    assert cleanup["temporary_state_removed"] is False
    assert any("temporary_state_cleanup" in error for error in cleanup["errors"])


def test_port_verification_error_is_recorded(monkeypatch):
    monkeypatch.setattr(
        helper,
        "_port_a_is_free",
        lambda: (_ for _ in ()).throw(RuntimeError("probe failed")),
    )
    cleanup = helper._cleanup_after_claim([FakeProcess()], [], None)
    assert cleanup["cleanup_success"] is False
    assert cleanup["port_28428_free"] is False
    assert any("port_28428_verification" in error for error in cleanup["errors"])


@pytest.mark.parametrize(
    "cleanup",
    [
        {"cleanup_success": False, "errors": ["terminate:RuntimeError"]},
        {"cleanup_success": False, "errors": ["join:RuntimeError"]},
        {"cleanup_success": False, "errors": ["kill:RuntimeError"]},
        {"cleanup_success": False, "errors": ["rmtree:RuntimeError"]},
        {"cleanup_success": False, "errors": ["port_probe:RuntimeError"]},
    ],
)
def test_every_cleanup_failure_persists_inactive_gate_closed_state(
    monkeypatch, tmp_path, cleanup
):
    disposable_state = tmp_path / "foundation158-terminal.json"
    monkeypatch.setattr(helper, "EXECUTION_STATE_PATH", disposable_state)
    helper._claim_authorization()
    helper._finalize_authorization("TERMINAL_CLEANUP_FAILURE", cleanup)
    terminal = json.loads(disposable_state.read_text(encoding="utf-8"))
    assert terminal["cleanup"] == cleanup
    assert terminal["state"]["AUTHORIZATION_CONSUMED"] is True
    assert terminal["state"]["CONSUMED_FOR_REUSE"] is True
    assert terminal["state"]["VALID_FOR_ACTIVE_EXECUTION"] is False
    assert terminal["state"]["EXECUTION_GATE_OPEN"] is False
    assert terminal["state"]["RESTART_ALLOWED"] is False


@pytest.mark.parametrize("stall_index", [0, 1])
def test_first_or_second_process_start_stall_is_bounded_and_cleaned(
    monkeypatch, stall_index
):
    processes = [
        FakeProcess(stall_start=index == stall_index)
        for index in range(2)
    ]
    records = []
    deadline = time.monotonic() + 0.02
    started_at = time.monotonic()
    with pytest.raises(
        helper.Foundation158PreflightError,
        match="maximum_duration_exceeded_during_startup",
    ):
        helper._start_exact_processes_bounded(processes, deadline, records)
    assert time.monotonic() - started_at < 0.5
    monkeypatch.setattr(helper, "_port_a_is_free", lambda: True)
    cleanup = helper._cleanup_after_claim(processes, records, None)
    assert cleanup["child_processes_remaining"] == 0
    assert all(not process.is_alive() for process in processes)


def test_process_setup_stall_is_bounded_without_real_processes(monkeypatch, tmp_path):
    release = threading.Event()
    event_calls = []

    class CancelledContext:
        def Event(self):
            event_calls.append("Event")
            raise AssertionError("cancelled setup continued")

    def stalled_context(_mode):
        release.wait()
        return CancelledContext()

    monkeypatch.setattr(helper.multiprocessing, "get_context", stalled_context)
    records = []
    started_at = time.monotonic()
    with pytest.raises(
        helper.Foundation158PreflightError,
        match="maximum_duration_exceeded_during_setup",
    ):
        helper._build_process_bundle_bounded(
            {},
            tmp_path / "agent-a",
            tmp_path / "agent-b",
            time.monotonic() + 0.02,
            records,
        )
    assert time.monotonic() - started_at < 0.5
    release.set()
    records[0]["thread"].join(0.5)
    assert records[0]["thread"].is_alive() is False
    assert event_calls == []


def test_deadline_abort_terminalizes_consumed_authorization_without_real_runtime(
    monkeypatch, tmp_path
):
    disposable_state = tmp_path / "foundation158-deadline-state.json"
    monkeypatch.setattr(helper, "EXECUTION_STATE_PATH", disposable_state)
    process = FakeProcess(stall_start=True)
    records = []
    helper._claim_authorization()
    with pytest.raises(
        helper.Foundation158PreflightError,
        match="maximum_duration_exceeded_during_startup",
    ):
        helper._start_exact_processes_bounded(
            [process], time.monotonic() + 0.02, records
        )
    monkeypatch.setattr(helper, "_port_a_is_free", lambda: True)
    cleanup = helper._cleanup_after_claim([process], records, None)
    helper._finalize_authorization("ABORT", cleanup, "startup_deadline")
    terminal = json.loads(disposable_state.read_text(encoding="utf-8"))
    assert terminal["state"]["AUTHORIZATION_CONSUMED"] is True
    assert terminal["state"]["VALID_FOR_ACTIVE_EXECUTION"] is False
    assert terminal["state"]["EXECUTION_GATE_OPEN"] is False
    with pytest.raises(
        helper.Foundation158PreflightError,
        match="authorization_already_consumed",
    ):
        helper._claim_authorization()


def test_outer_cleanup_exception_still_terminalizes_inactive_state(
    monkeypatch, tmp_path
):
    disposable_state = tmp_path / "foundation158-outer-state.json"
    runtime_root = tmp_path / "runtime"

    def make_runtime(*, prefix):
        assert prefix == "l28-f158-"
        runtime_root.mkdir()
        return str(runtime_root)

    monkeypatch.setattr(helper, "EXECUTION_STATE_PATH", disposable_state)
    monkeypatch.setattr(helper.tempfile, "mkdtemp", make_runtime)
    monkeypatch.setattr(
        helper.multiprocessing,
        "get_context",
        lambda _mode: (_ for _ in ()).throw(RuntimeError("setup failed")),
    )
    monkeypatch.setattr(
        helper,
        "_cleanup_after_claim",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("cleanup failed")),
    )
    with pytest.raises(
        helper.Foundation158PreflightError,
        match="process_setup_failed:RuntimeError:setup failed",
    ):
        helper.run_authorized_experiment_once(
            authorization_id=helper.AUTHORIZATION_ID,
            baseline_commit=helper.BASELINE_COMMIT,
            preflight_gate_sha256=hashlib.sha256(GATE.read_bytes()).hexdigest(),
        )
    terminal = json.loads(disposable_state.read_text(encoding="utf-8"))
    assert terminal["result"] == "TERMINAL_CLEANUP_FAILURE"
    assert terminal["state"]["AUTHORIZATION_CONSUMED"] is True
    assert terminal["state"]["VALID_FOR_ACTIVE_EXECUTION"] is False
    assert terminal["state"]["EXECUTION_GATE_OPEN"] is False
    assert terminal["state"]["RESTART_ALLOWED"] is False
    assert terminal["cleanup"]["errors"] == [
        "cleanup_supervisor:RuntimeError:cleanup failed"
    ]


def test_terminalization_failure_is_explicit_and_not_hidden(monkeypatch, tmp_path):
    disposable_state = tmp_path / "foundation158-terminalization-state.json"
    runtime_root = tmp_path / "runtime-terminalization"

    def make_runtime(*, prefix):
        assert prefix == "l28-f158-"
        runtime_root.mkdir()
        return str(runtime_root)

    monkeypatch.setattr(helper, "EXECUTION_STATE_PATH", disposable_state)
    monkeypatch.setattr(helper.tempfile, "mkdtemp", make_runtime)
    monkeypatch.setattr(
        helper.multiprocessing,
        "get_context",
        lambda _mode: (_ for _ in ()).throw(RuntimeError("setup failed")),
    )
    monkeypatch.setattr(
        helper,
        "_cleanup_after_claim",
        lambda *_args: {"cleanup_success": True, "errors": []},
    )
    monkeypatch.setattr(
        helper,
        "_finalize_authorization",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("terminal write failed")),
    )
    with pytest.raises(
        helper.Foundation158TerminalizationError,
        match="terminalization_failed:RuntimeError:terminal write failed",
    ):
        helper.run_authorized_experiment_once(
            authorization_id=helper.AUTHORIZATION_ID,
            baseline_commit=helper.BASELINE_COMMIT,
            preflight_gate_sha256=hashlib.sha256(GATE.read_bytes()).hexdigest(),
        )


def test_all_fail_closed_prerequisites_and_abort_criteria_are_explicit():
    prerequisites = gate()["fail_closed_prerequisites"]
    required = {
        "exact_authorization_id_and_baseline_binding_required",
        "authorization_granted_and_unconsumed_required",
        "exact_two_agent_two_process_topology_required",
        "agent_a_listener_127_0_0_1_28428_available_required",
        "agent_b_bind_127_0_0_1_port_zero_required",
        "agent_b_fixed_source_port_28429_forbidden",
        "no_external_network_path_required",
        "option_a_available_required",
        "replay_state_initialized_required",
        "cleanup_handlers_installed_required",
        "maximum_runtime_guard_active_required",
    }
    assert {key for key in required if prerequisites[key] is True} == required
    assert prerequisites["missing_invalid_changed_or_conflicting_evidence_action"] == (
        "DO_NOT_START_FAIL_CLOSED"
    )
    aborts = gate()["abort_criteria"]
    assert aborts["retry_after_abort_permitted"] is False
    assert set(value for key, value in aborts.items() if key != "retry_after_abort_permitted") == {True}


def test_mandatory_cleanup_and_no_persistent_runtime_are_exact():
    cleanup = gate()["mandatory_cleanup"]
    assert cleanup == {
        "all_sockets_closed_required": True,
        "both_processes_terminated_required": True,
        "terminate_then_bounded_join_required": True,
        "strong_kill_if_still_alive_required": True,
        "bounded_final_join_required": True,
        "agent_a_port_28428_free_required": True,
        "zero_experiment_child_processes_required": True,
        "temporary_state_removed_or_reset_required": True,
        "persistent_runtime_or_service_permitted": False,
        "consumed_marker_retained_required": True,
    }


def test_future_runner_has_exact_bind_calls_and_atomic_claim_before_start():
    source = HELPER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    bind_calls = [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "bind"
    ]
    assert bind_calls == [
        "client.bind((HOST, CLIENT_BIND_PORT))",
        "listener.bind((HOST, PORT_A))",
        "probe.bind((HOST, PORT_A))",
    ]
    assert "client.bind((HOST, FORBIDDEN_FIXED_CLIENT_PORT))" not in source
    assert "os.O_EXCL" in source
    run_source = source[source.index("def run_authorized_experiment_once"):]
    assert run_source.index("_claim_authorization()") < run_source.index(
        "_start_exact_processes_bounded("
    )
    assert run_source.index("_claim_authorization()") < run_source.index(
        "_build_process_bundle_bounded("
    )
    bounded_start_source = source[
        source.index("def _start_process_bounded"):source.index(
            "def _start_exact_processes_bounded"
        )
    ]
    assert "process.start()" in bounded_start_source
    assert "done.wait(remaining)" in bounded_start_source
    assert "len(set(source_ports)) != SESSION_COUNT" in source


def test_incomplete_or_mismatched_explicit_invocation_fails_before_claim(monkeypatch):
    def forbidden():
        raise AssertionError("authorization claim must not occur")

    monkeypatch.setattr(helper, "_claim_authorization", forbidden)
    with pytest.raises(
        helper.Foundation158PreflightError,
        match="explicit_authorization_id_invalid",
    ):
        helper.run_authorized_experiment_once(
            authorization_id="wrong",
            baseline_commit=helper.BASELINE_COMMIT,
            preflight_gate_sha256=hashlib.sha256(GATE.read_bytes()).hexdigest(),
        )


def test_rejected_repeat_claim_starts_no_socket_or_process(monkeypatch):
    def consumed():
        raise helper.Foundation158PreflightError("authorization_already_consumed")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("runtime capability used after rejected claim")

    monkeypatch.setattr(helper, "_claim_authorization", consumed)
    monkeypatch.setattr(helper.socket, "socket", forbidden)
    monkeypatch.setattr(helper.multiprocessing, "get_context", forbidden)
    with pytest.raises(
        helper.Foundation158PreflightError,
        match="authorization_already_consumed",
    ):
        helper.run_authorized_experiment_once(
            authorization_id=helper.AUTHORIZATION_ID,
            baseline_commit=helper.BASELINE_COMMIT,
            preflight_gate_sha256=hashlib.sha256(GATE.read_bytes()).hexdigest(),
        )


def test_all_prohibited_authority_remains_false_and_keys_are_exact():
    authority = gate()["authority_firewall"]
    assert set(authority) == {
        "persistent_p2p_runtime_authorized",
        "rpc_authorized",
        "wallet_creation_authorized",
        "key_creation_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "settlement_authorized",
        "public_testnet_authorized",
        "deployment_authorized",
        "ledger_mutation_authorized",
        "canonical_height_override_authorized",
        "issuance_authority",
        "supply_authority",
        "validation_authority",
        "history_authority",
        "protocol_authority",
        "automatic_reorg_authorized",
        "fork_winner_selected",
    }
    assert set(authority.values()) == {False}


def test_protocol_economics_validator_and_boundaries_remain_exact():
    protected = gate()["protected_invariants"]
    assert protected == {
        "protocol_version": "1.0.0",
        "protocol_sha256": "eabd5f2a11916781e6a047e5b2c2188fe4e0f1eae2fdcdc2f68e4c19193c397d",
        "canonical_validator": "coin.tx_validation.validate_transaction",
        "tx_validation_sha256": "ac36bd95c932733a60ffc3acbb10b8a9f57e09c9533d0b64ff83affa876f3004",
        "coinbase_only_issuance": True,
        "hard_cap": 28000000,
        "emission_ceiling": 11130000,
        "historically_mined": 2824584,
        "treasury_locked": 500000,
        "circulating_snapshot": 2324584,
        "halving_interval": 210000,
        "reward_schedule": [28, 14, 7, 3, 1, 0],
        "historical_mined_through_entry": 100877,
        "next_canonical_height": 100878,
        "canonical_height_authority": "CONSENSUS_DERIVED_ONLY",
        "historical_evidence_immutable": True,
        "bitcoin_authority": "EXTERNAL_EVIDENCE_ONLY_ZERO_L28_AUTHORITY",
        "signer_runtime_authorized": False,
        "option_a_scope": "REVIEWED_NON_NORMATIVE_SAFETY_BOUNDARY_ONLY",
    }
    assert hashlib.sha256((ROOT / "PROTOCOL.md").read_bytes()).hexdigest() == (
        protected["protocol_sha256"]
    )
    assert hashlib.sha256((ROOT / "coin/tx_validation.py").read_bytes()).hexdigest() == (
        protected["tx_validation_sha256"]
    )


def test_readiness_is_true_while_execution_gate_and_execution_remain_false():
    assert gate()["readiness"] == {
        "READY_FOR_EXPLICIT_EXECUTION_INVOCATION": True,
        "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "EXECUTION_GATE_OPEN": False,
        "AUTHORIZATION_CONSUMED": False,
        "EXPERIMENT_EXECUTED": False,
        "NO_EXECUTION_OCCURRED": True,
    }
    text = DOCUMENT.read_text(encoding="utf-8")
    assert "READY_FOR_EXPLICIT_EXECUTION_INVOCATION=true" in text
    assert "EXECUTION_GATE_OPEN=false" in text
    assert "AUTHORIZATION_CONSUMED=false" in text
    assert "EXPERIMENT_EXECUTED=false" in text
