# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import multiprocessing
import os
import shutil
import socket
import struct
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coin.disposable_testnet_identity import PROTECTED_ECONOMIC_FACTS
from coin.disposable_testnet_option_a_policy import (
    CandidateHistory,
    HistoryEntry,
    OptionAPolicyState,
    assess_peer_equivocation,
    transition_sync_state,
)
from coin.disposable_testnet_p2p_conformance import (
    assess_frame_bytes,
    build_offline_frame,
    encode_frame_bytes,
    nonce_replay_key,
)
from coin.disposable_testnet_runtime_boundary import prepare_runtime_boundary


PROFILE = "l28-foundation158-corrected-one-shot-execution/v0.1"
AUTHORIZATION_ID = "L28-F157-CORRECTED-RECONNECT-ONE-SHOT-001"
BASELINE_COMMIT = "25d3bdc8ec77b96c0af717b1864650388559da5e"
AUTHORIZATION_PATH = (
    ROOT
    / "docs/l28_foundation156_corrected_reconnect_authorization_gate_v0.1.json"
)
PREFLIGHT_GATE_PATH = (
    ROOT
    / "docs/l28_foundation158_corrected_one_shot_execution_preflight_gate_v0.1.json"
)
EXECUTION_STATE_PATH = (
    ROOT / "docs/l28_foundation158_corrected_one_shot_execution_state_v1.0.json"
)
HOST = "127.0.0.1"
PORT_A = 28428
CLIENT_BIND_PORT = 0
FORBIDDEN_FIXED_CLIENT_PORT = 28429
SESSION_COUNT = 2
RECONNECT_COUNT = 1
MAX_DURATION_SECONDS = 60
SOCKET_TIMEOUT_SECONDS = 5.0
CLEANUP_JOIN_SECONDS = 2.0
MAX_FRAME_BYTES = 4096
PREFIX_BYTES = 4
AGENT_A = "agent-a"
AGENT_B = "agent-b"


class Foundation158PreflightError(Exception):
    pass


class Foundation158TerminalizationError(Foundation158PreflightError):
    def __init__(self, terminalization_error: BaseException, cleanup: dict[str, Any]):
        self.terminalization_error = (
            type(terminalization_error).__name__ + ":" + str(terminalization_error)
        )
        self.cleanup = cleanup
        super().__init__("terminalization_failed:" + self.terminalization_error)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Foundation158PreflightError("duplicate_key:" + key)
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_config() -> dict[str, Any]:
    network_id = "L28-DISPOSABLE-LAB001"
    return {
        "profile": "l28-disposable-testnet-m1-binding/v0.1",
        "protocol_version": "1.0.0",
        "network_scope": "DISPOSABLE_TEST_ONLY",
        "network_id": network_id,
        "data_dir_tag": "l28-disposable-testnet:lab001",
        "genesis": {
            "profile": "l28-disposable-genesis/v0.1",
            "network_id": network_id,
            "initial_height": 0,
            "initial_issued_supply": 0,
            "historical_checkpoint_imported": False,
            "historical_balances_loaded": False,
            "protected_economic_facts": copy.deepcopy(PROTECTED_ECONOMIC_FACTS),
        },
        "key_policy": {
            "allow_production_keys": False,
            "allow_creator_private_material": False,
            "allow_external_wallet_paths": False,
        },
        "acknowledge_disposable_test_only": True,
    }


def _runtime_context():
    return prepare_runtime_boundary(_valid_config(), acknowledge_test_only=True)


def _candidate_histories() -> tuple[CandidateHistory, CandidateHistory]:
    common = HistoryEntry(0, "f158-public-genesis", "GENESIS")
    left = CandidateHistory(
        source_id=AGENT_B,
        network_id="L28-DISPOSABLE-LAB001",
        genesis_hash="f158-public-genesis",
        entries=(common, HistoryEntry(1, "f158-public-left", common.block_id)),
    )
    right = CandidateHistory(
        source_id=AGENT_B,
        network_id="L28-DISPOSABLE-LAB001",
        genesis_hash="f158-public-genesis",
        entries=(common, HistoryEntry(1, "f158-public-right", common.block_id)),
    )
    return left, right


def _build_frames(binding, tip) -> dict[str, bytes]:
    specs = {
        "hello_b": (
            "HELLO",
            "f158-b-hello-001",
            {"agent_id": AGENT_B, "evidence_only": True},
        ),
        "tip_b": (
            "TIP_EVIDENCE",
            "f158-b-tip-001",
            {"height": 0, "evidence_only": True},
        ),
        "candidate_session1": (
            "CANDIDATE_EVIDENCE",
            "f158-b-candidate-001",
            {
                "candidate_id": "f158-public-baseline",
                "evidence_only": True,
                "apply": False,
            },
        ),
        "candidate_left": (
            "CANDIDATE_EVIDENCE",
            "f158-b-candidate-002",
            {
                "candidate_id": "f158-public-left",
                "evidence_only": True,
                "apply": False,
            },
        ),
        "candidate_right": (
            "CANDIDATE_EVIDENCE",
            "f158-b-candidate-003",
            {
                "candidate_id": "f158-public-right",
                "evidence_only": True,
                "apply": False,
            },
        ),
        "hello_a": (
            "HELLO",
            "f158-a-hello-001",
            {"agent_id": AGENT_A, "evidence_only": True},
        ),
    }
    return {
        name: encode_frame_bytes(
            build_offline_frame(
                binding,
                tip,
                message_type=message_type,
                peer_id=AGENT_A if name == "hello_a" else AGENT_B,
                nonce=nonce,
                timestamp=1000,
                expiry=1100,
                payload={**payload, "authorization_id": AUTHORIZATION_ID},
            )
        )
        for name, (message_type, nonce, payload) in specs.items()
    }


def load_and_validate_preflight() -> tuple[dict[str, Any], dict[str, Any]]:
    gate = _load_json(PREFLIGHT_GATE_PATH)
    authorization = _load_json(AUTHORIZATION_PATH)
    source = gate["source_binding"]
    if source["baseline_commit"] != BASELINE_COMMIT:
        raise Foundation158PreflightError("baseline_binding_invalid")
    for path_key, digest_key in (
        ("foundation157_package", "foundation157_package_sha256"),
        ("foundation157_authorization", "foundation157_authorization_sha256"),
        ("foundation157_tests", "foundation157_tests_sha256"),
        ("foundation158_helper", "foundation158_helper_sha256"),
    ):
        if _sha256(ROOT / source[path_key]) != source[digest_key]:
            raise Foundation158PreflightError("artifact_binding_mismatch:" + path_key)
    if authorization["authorization_id"] != AUTHORIZATION_ID:
        raise Foundation158PreflightError("authorization_id_invalid")
    required_state = {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": False,
        "CONSUMED_FOR_REUSE": False,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXPERIMENT_EXECUTED": False,
        "EXECUTION_GATE_OPEN": False,
    }
    if authorization["authorization_state"] != required_state:
        raise Foundation158PreflightError("authorization_state_invalid")
    if gate["authorization_state"] != required_state:
        raise Foundation158PreflightError("preflight_state_invalid")
    scope = gate["future_execution_scope"]
    if scope != authorization["corrected_future_experiment"]:
        raise Foundation158PreflightError("execution_scope_binding_mismatch")
    if scope["agent_b"]["bind_port_argument"] != CLIENT_BIND_PORT:
        raise Foundation158PreflightError("fixed_client_port_forbidden")
    if scope["agent_b"]["fixed_source_port_28429_permitted"] is not False:
        raise Foundation158PreflightError("fixed_client_port_forbidden")
    if set(gate["authority_firewall"].values()) != {False}:
        raise Foundation158PreflightError("authority_firewall_invalid")
    protected = gate["protected_invariants"]
    if _sha256(ROOT / "PROTOCOL.md") != protected["protocol_sha256"]:
        raise Foundation158PreflightError("protocol_binding_mismatch")
    if _sha256(ROOT / "coin/tx_validation.py") != protected["tx_validation_sha256"]:
        raise Foundation158PreflightError("validator_binding_mismatch")
    if gate["readiness"] != {
        "READY_FOR_EXPLICIT_EXECUTION_INVOCATION": True,
        "SEPARATE_EXPLICIT_EXECUTION_INVOCATION_REQUIRED": True,
        "EXECUTION_GATE_OPEN": False,
        "AUTHORIZATION_CONSUMED": False,
        "EXPERIMENT_EXECUTED": False,
        "NO_EXECUTION_OCCURRED": True,
    }:
        raise Foundation158PreflightError("readiness_invalid")
    return gate, authorization


def _pure_continuity_assessment(binding, tip, frames: dict[str, bytes]) -> dict[str, Any]:
    seen_ids: set[str] = set()
    seen_nonces: set[str] = set()
    first = assess_frame_bytes(
        frames["hello_b"],
        binding,
        tip,
        now_ts=1000,
        seen_message_ids=seen_ids,
        seen_nonce_keys=seen_nonces,
    )
    if not first.ok or first.normalized_frame is None:
        raise Foundation158PreflightError("initial_identity_admission_failed")
    seen_ids.add(first.message_id)
    seen_nonces.add(nonce_replay_key(first.normalized_frame))
    replay = assess_frame_bytes(
        frames["hello_b"],
        binding,
        tip,
        now_ts=1000,
        seen_message_ids=seen_ids,
        seen_nonce_keys=seen_nonces,
    )
    left, right = _candidate_histories()
    assessment = assess_peer_equivocation(left, right)
    halted = transition_sync_state(
        OptionAPolicyState("SYNCING", "F158_PREFLIGHT"), assessment
    )
    if replay.ok or replay.code != "message_replayed":
        raise Foundation158PreflightError("replay_not_rejected")
    if assessment.code != "HALT_SYNC_PEER_EQUIVOCATION":
        raise Foundation158PreflightError("option_a_unavailable")
    if halted.status != "HALTED_CONFLICT":
        raise Foundation158PreflightError("option_a_transition_invalid")
    return {
        "peer_id": first.peer_id,
        "replay_code": replay.code,
        "replay_disconnect": replay.disconnect,
        "option_a_code": assessment.code,
        "option_a_state": halted.status,
        "retain_current_local_canonical_state": assessment.retain_current_local_canonical_state,
        "ledger_mutated": halted.ledger_mutated,
        "canonical_state_changed": halted.canonical_state_changed,
    }


def dry_run_preflight() -> dict[str, Any]:
    gate, authorization = load_and_validate_preflight()
    binding, tip = _runtime_context()
    frames = _build_frames(binding, tip)
    local_height_before = tip.read_height()
    continuity = _pure_continuity_assessment(binding, tip, frames)
    local_height_after = tip.read_height()
    if local_height_before != local_height_after:
        raise Foundation158PreflightError("canonical_state_mutated")
    return {
        "profile": PROFILE,
        "mode": "DRY_RUN_PREFLIGHT",
        "authorization_id": authorization["authorization_id"],
        "baseline_commit": gate["source_binding"]["baseline_commit"],
        "agent_count": 2,
        "process_count": 2,
        "agent_a_listener": [HOST, PORT_A],
        "agent_b_bind": [HOST, CLIENT_BIND_PORT],
        "fixed_agent_b_source_port_28429_permitted": False,
        "fresh_ephemeral_source_port_per_session": True,
        "session_count": SESSION_COUNT,
        "reconnect_count": RECONNECT_COUNT,
        "maximum_active_duration_seconds": MAX_DURATION_SECONDS,
        "transport_port_is_peer_identity": False,
        "application_identity_persists_across_reconnect": True,
        "replay_state_persists_across_reconnect": True,
        "continuity": continuity,
        "local_height_before": local_height_before,
        "local_height_after": local_height_after,
        "candidate_auto_applied": False,
        "automatic_reorg": False,
        "fork_winner_selected": False,
        "sockets_opened": False,
        "processes_started": False,
        "network_traffic": False,
        "authorization_consumed": False,
        "experiment_executed": False,
        "execution_gate_open": False,
    }


def _recv_exact(sock: socket.socket, count: int) -> bytes:
    chunks: list[bytes] = []
    while count:
        chunk = sock.recv(count)
        if not chunk:
            raise Foundation158PreflightError("unexpected_transport_eof")
        chunks.append(chunk)
        count -= len(chunk)
    return b"".join(chunks)


def _send_wire(sock: socket.socket, payload: bytes) -> None:
    if type(payload) is not bytes or len(payload) > MAX_FRAME_BYTES:
        raise Foundation158PreflightError("wire_frame_invalid")
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def _recv_wire(sock: socket.socket) -> bytes:
    size = struct.unpack("!I", _recv_exact(sock, PREFIX_BYTES))[0]
    if size > MAX_FRAME_BYTES:
        raise Foundation158PreflightError("wire_frame_too_large")
    return _recv_exact(sock, size)


def _connect_client() -> tuple[socket.socket, int]:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(SOCKET_TIMEOUT_SECONDS)
    client.bind((HOST, CLIENT_BIND_PORT))
    assigned_host, assigned_port = client.getsockname()
    if assigned_host != HOST or not (1 <= assigned_port <= 65535):
        client.close()
        raise Foundation158PreflightError("agent_b_ephemeral_bind_invalid")
    client.connect((HOST, PORT_A))
    if client.getpeername() != (HOST, PORT_A):
        client.close()
        raise Foundation158PreflightError("agent_b_peer_scope_invalid")
    return client, assigned_port


def _agent_a(frames: dict[str, bytes], data_dir: str, ready, results) -> None:
    listener = None
    try:
        if not Path(data_dir).is_dir():
            raise Foundation158PreflightError("agent_a_data_dir_missing")
        binding, tip = _runtime_context()
        local_before = tip.read_height()
        seen_ids: set[str] = set()
        seen_nonces: set[str] = set()
        source_ports: list[int] = []
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.settimeout(SOCKET_TIMEOUT_SECONDS)
        listener.bind((HOST, PORT_A))
        listener.listen(1)
        if listener.getsockname() != (HOST, PORT_A):
            raise Foundation158PreflightError("agent_a_bind_scope_invalid")
        ready.set()
        for session in range(SESSION_COUNT):
            conn, address = listener.accept()
            with conn:
                conn.settimeout(SOCKET_TIMEOUT_SECONDS)
                if address[0] != HOST or not (1 <= address[1] <= 65535):
                    raise Foundation158PreflightError("agent_b_endpoint_invalid")
                source_ports.append(address[1])
                names = (
                    ("hello_b", "tip_b", "candidate_session1")
                    if session == 0
                    else ("candidate_left", "candidate_right")
                )
                for name in names:
                    admitted = assess_frame_bytes(
                        _recv_wire(conn),
                        binding,
                        tip,
                        now_ts=1000,
                        seen_message_ids=seen_ids,
                        seen_nonce_keys=seen_nonces,
                    )
                    if not admitted.ok or admitted.normalized_frame is None:
                        raise Foundation158PreflightError(
                            "frame_admission_failed:" + admitted.code
                        )
                    seen_ids.add(admitted.message_id)
                    seen_nonces.add(nonce_replay_key(admitted.normalized_frame))
                if session == 0:
                    _send_wire(conn, frames["hello_a"])
                else:
                    replay = assess_frame_bytes(
                        _recv_wire(conn),
                        binding,
                        tip,
                        now_ts=1000,
                        seen_message_ids=seen_ids,
                        seen_nonce_keys=seen_nonces,
                    )
                    if replay.ok or replay.code != "message_replayed":
                        raise Foundation158PreflightError("replay_not_rejected")
        if len(set(source_ports)) != SESSION_COUNT:
            raise Foundation158PreflightError("ephemeral_source_port_reused")
        left, right = _candidate_histories()
        assessment = assess_peer_equivocation(left, right)
        halted = transition_sync_state(
            OptionAPolicyState("SYNCING", "F158_ACTIVE"), assessment
        )
        local_after = tip.read_height()
        results.put(
            {
                "agent": AGENT_A,
                "result": "PASS",
                "source_ports": source_ports,
                "replay_code": replay.code,
                "option_a_code": assessment.code,
                "option_a_state": halted.status,
                "local_height_before": local_before,
                "local_height_after": local_after,
                "ledger_mutated": halted.ledger_mutated,
                "canonical_state_changed": halted.canonical_state_changed,
            }
        )
    except Exception as exc:
        ready.set()
        results.put(
            {
                "agent": AGENT_A,
                "result": "FAIL",
                "error": type(exc).__name__ + ":" + str(exc),
            }
        )
    finally:
        if listener is not None:
            listener.close()


def _agent_b(frames: dict[str, bytes], data_dir: str, ready, results) -> None:
    try:
        if not Path(data_dir).is_dir():
            raise Foundation158PreflightError("agent_b_data_dir_missing")
        if not ready.wait(SOCKET_TIMEOUT_SECONDS):
            raise Foundation158PreflightError("agent_a_not_ready")
        binding, tip = _runtime_context()
        source_ports: list[int] = []
        client, source_port = _connect_client()
        source_ports.append(source_port)
        with client:
            for name in ("hello_b", "tip_b", "candidate_session1"):
                _send_wire(client, frames[name])
            response = assess_frame_bytes(
                _recv_wire(client),
                binding,
                tip,
                now_ts=1000,
                seen_message_ids=set(),
                seen_nonce_keys=set(),
            )
            if not response.ok or response.peer_id != AGENT_A:
                raise Foundation158PreflightError("agent_a_response_invalid")
        client, source_port = _connect_client()
        source_ports.append(source_port)
        if len(set(source_ports)) != SESSION_COUNT:
            client.close()
            raise Foundation158PreflightError("ephemeral_source_port_reused")
        with client:
            _send_wire(client, frames["candidate_left"])
            _send_wire(client, frames["candidate_right"])
            _send_wire(client, frames["hello_b"])
        results.put(
            {
                "agent": AGENT_B,
                "result": "PASS",
                "source_ports": source_ports,
                "session_count": SESSION_COUNT,
                "reconnect_count": RECONNECT_COUNT,
            }
        )
    except Exception as exc:
        results.put(
            {
                "agent": AGENT_B,
                "result": "FAIL",
                "error": type(exc).__name__ + ":" + str(exc),
            }
        )


def _claim_authorization() -> None:
    claim = {
        "profile": "l28-foundation158-corrected-one-shot-execution-state/v1.0",
        "authorization_id": AUTHORIZATION_ID,
        "baseline_commit": BASELINE_COMMIT,
        "state": {
            "AUTHORIZATION_GRANTED": True,
            "AUTHORIZATION_CONSUMED": True,
            "CONSUMED_FOR_REUSE": True,
            "VALID_FOR_ACTIVE_EXECUTION": True,
            "EXECUTION_GATE_OPEN": True,
            "EXPERIMENT_EXECUTED": True,
        },
    }
    try:
        descriptor = os.open(
            EXECUTION_STATE_PATH,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise Foundation158PreflightError("authorization_already_consumed") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(claim, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _finalize_authorization(
    result: str,
    cleanup: dict[str, Any] | None = None,
    execution_error: str | None = None,
) -> None:
    state = _load_json(EXECUTION_STATE_PATH)
    state["result"] = result
    state["cleanup"] = cleanup
    state["execution_error"] = execution_error
    state["state"] = {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": True,
        "CONSUMED_FOR_REUSE": True,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXECUTION_GATE_OPEN": False,
        "EXPERIMENT_EXECUTED": True,
        "RESTART_ALLOWED": False,
    }
    temporary = EXECUTION_STATE_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, EXECUTION_STATE_PATH)


def _port_a_is_free() -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((HOST, PORT_A))
        return probe.getsockname() == (HOST, PORT_A)
    except OSError:
        return False
    finally:
        probe.close()


def _exception_text(exc: BaseException) -> str:
    return type(exc).__name__ + ":" + str(exc)


def _is_alive(process, label: str, errors: list[str]) -> bool:
    try:
        return process.is_alive()
    except BaseException as exc:
        errors.append(label + ":is_alive:" + _exception_text(exc))
        return True


def _best_effort_force_stop(process) -> None:
    try:
        if process.is_alive():
            process.terminate()
    except BaseException:
        pass
    try:
        if process.is_alive() and callable(getattr(process, "kill", None)):
            process.kill()
    except BaseException:
        pass


def _start_process_bounded(
    process, deadline: float, startup_records: list[dict[str, Any]]
) -> None:
    done = threading.Event()
    cancel = threading.Event()
    errors: list[BaseException] = []

    def start_target() -> None:
        try:
            process.start()
        except BaseException as exc:
            errors.append(exc)
        finally:
            if cancel.is_set():
                _best_effort_force_stop(process)
            done.set()

    thread = threading.Thread(
        target=start_target,
        name="foundation158-bounded-process-start",
        daemon=True,
    )
    record = {"thread": thread, "cancel": cancel, "done": done, "process": process}
    startup_records.append(record)
    thread.start()
    remaining = deadline - time.monotonic()
    if remaining <= 0 or not done.wait(remaining):
        cancel.set()
        raise Foundation158PreflightError("maximum_duration_exceeded_during_startup")
    thread.join(0)
    if errors:
        raise Foundation158PreflightError(
            "process_start_failed:" + _exception_text(errors[0])
        )


def _build_process_bundle_bounded(
    frames: dict[str, bytes],
    data_a: Path,
    data_b: Path,
    deadline: float,
    startup_records: list[dict[str, Any]],
) -> tuple[Any, list[Any]]:
    done = threading.Event()
    cancel = threading.Event()
    errors: list[BaseException] = []
    values: list[tuple[Any, list[Any]]] = []

    def setup_target() -> None:
        processes: list[Any] = []
        results = None

        def require_not_cancelled() -> None:
            if cancel.is_set():
                raise Foundation158PreflightError("process_setup_cancelled")

        try:
            ctx = multiprocessing.get_context("spawn")
            require_not_cancelled()
            ready = ctx.Event()
            require_not_cancelled()
            results = ctx.Queue()
            require_not_cancelled()
            processes = [
                ctx.Process(
                    target=_agent_a,
                    args=(frames, str(data_a), ready, results),
                    name="foundation158-agent-a",
                ),
                ctx.Process(
                    target=_agent_b,
                    args=(frames, str(data_b), ready, results),
                    name="foundation158-agent-b",
                ),
            ]
            require_not_cancelled()
            values.append((results, processes))
        except BaseException as exc:
            errors.append(exc)
        finally:
            if cancel.is_set():
                for process in processes:
                    _best_effort_force_stop(process)
                if results is not None:
                    try:
                        results.close()
                    except BaseException:
                        pass
            done.set()

    thread = threading.Thread(
        target=setup_target,
        name="foundation158-bounded-process-setup",
        daemon=True,
    )
    record = {"thread": thread, "cancel": cancel, "done": done, "process": None}
    startup_records.append(record)
    thread.start()
    remaining = deadline - time.monotonic()
    if remaining <= 0 or not done.wait(remaining):
        cancel.set()
        raise Foundation158PreflightError("maximum_duration_exceeded_during_setup")
    thread.join(0)
    if errors:
        raise Foundation158PreflightError(
            "process_setup_failed:" + _exception_text(errors[0])
        )
    if len(values) != 1 or len(values[0][1]) != 2:
        raise Foundation158PreflightError("process_setup_scope_invalid")
    return values[0]


def _start_exact_processes_bounded(
    processes: list[Any], deadline: float, startup_records: list[dict[str, Any]]
) -> int:
    started = 0
    for process in processes:
        _start_process_bounded(process, deadline, startup_records)
        started += 1
    return started


def _cleanup_after_claim(
    processes: list[Any],
    startup_records: list[dict[str, Any]],
    temp_root: Path | None,
) -> dict[str, Any]:
    errors: list[str] = []
    for record in startup_records:
        record["cancel"].set()

    for index, process in enumerate(processes):
        label = "process_" + str(index)
        if _is_alive(process, label, errors):
            try:
                process.terminate()
            except BaseException as exc:
                errors.append(label + ":terminate:" + _exception_text(exc))

    for index, process in enumerate(processes):
        label = "process_" + str(index)
        try:
            if process.pid is not None:
                process.join(CLEANUP_JOIN_SECONDS)
        except BaseException as exc:
            errors.append(label + ":join_after_terminate:" + _exception_text(exc))

    for index, process in enumerate(processes):
        label = "process_" + str(index)
        if _is_alive(process, label, errors):
            kill = getattr(process, "kill", None)
            if not callable(kill):
                errors.append(label + ":strong_termination_unavailable")
            else:
                try:
                    kill()
                except BaseException as exc:
                    errors.append(label + ":kill:" + _exception_text(exc))

    for index, process in enumerate(processes):
        label = "process_" + str(index)
        try:
            if process.pid is not None:
                process.join(CLEANUP_JOIN_SECONDS)
        except BaseException as exc:
            errors.append(label + ":final_join:" + _exception_text(exc))

    children_remaining = sum(
        _is_alive(process, "process_" + str(index), errors)
        for index, process in enumerate(processes)
    )
    for index, record in enumerate(startup_records):
        try:
            record["thread"].join(0)
        except BaseException as exc:
            errors.append("startup_" + str(index) + ":join:" + _exception_text(exc))
    startup_supervisors_remaining = sum(
        record["thread"].is_alive() for record in startup_records
    )
    if startup_supervisors_remaining:
        errors.append("startup_supervisor_still_running")

    temporary_state_removed = temp_root is None
    if temp_root is not None:
        try:
            shutil.rmtree(temp_root)
            temporary_state_removed = not temp_root.exists()
        except BaseException as exc:
            errors.append("temporary_state_cleanup:" + _exception_text(exc))
            temporary_state_removed = False

    port_28428_free = False
    try:
        port_28428_free = _port_a_is_free()
        if not port_28428_free:
            errors.append("port_28428_not_free")
    except BaseException as exc:
        errors.append("port_28428_verification:" + _exception_text(exc))

    processes_terminated = children_remaining == 0
    cleanup_success = (
        processes_terminated
        and startup_supervisors_remaining == 0
        and temporary_state_removed
        and port_28428_free
        and not errors
    )
    return {
        "cleanup_success": cleanup_success,
        "sockets_closed": processes_terminated and port_28428_free,
        "processes_terminated": processes_terminated,
        "port_28428_free": port_28428_free,
        "child_processes_remaining": children_remaining,
        "startup_supervisors_remaining": startup_supervisors_remaining,
        "temporary_state_removed": temporary_state_removed,
        "persistent_runtime_created": False,
        "errors": errors,
    }


def run_authorized_experiment_once(
    *, authorization_id: str, baseline_commit: str, preflight_gate_sha256: str
) -> dict[str, Any]:
    if authorization_id != AUTHORIZATION_ID:
        raise Foundation158PreflightError("explicit_authorization_id_invalid")
    if baseline_commit != BASELINE_COMMIT:
        raise Foundation158PreflightError("explicit_baseline_invalid")
    if preflight_gate_sha256 != _sha256(PREFLIGHT_GATE_PATH):
        raise Foundation158PreflightError("explicit_gate_digest_invalid")
    load_and_validate_preflight()
    binding, tip = _runtime_context()
    frames = _build_frames(binding, tip)
    temp_root = None
    processes = []
    startup_records: list[dict[str, Any]] = []
    results = None
    reports: list[dict[str, Any]] = []
    started_count = 0
    started_at = 0.0
    result = "ABORT"
    claimed = False
    cleanup: dict[str, Any] = {}
    execution_error: BaseException | None = None
    terminalization_error: BaseException | None = None
    try:
        _claim_authorization()
        claimed = True
        started_at = time.monotonic()
        deadline = started_at + MAX_DURATION_SECONDS
        temp_root = Path(tempfile.mkdtemp(prefix="l28-f158-"))
        data_a = temp_root / AGENT_A
        data_b = temp_root / AGENT_B
        data_a.mkdir()
        data_b.mkdir()
        results, processes = _build_process_bundle_bounded(
            frames, data_a, data_b, deadline, startup_records
        )
        started_count = _start_exact_processes_bounded(
            processes, deadline, startup_records
        )
        for process in processes:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Foundation158PreflightError("maximum_duration_exceeded")
            process.join(remaining)
        if any(process.is_alive() for process in processes):
            raise Foundation158PreflightError("maximum_duration_exceeded")
        for _ in range(2):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Foundation158PreflightError("maximum_duration_exceeded")
            reports.append(results.get(timeout=min(1.0, remaining)))
        if any(report.get("result") != "PASS" for report in reports):
            raise Foundation158PreflightError("agent_failure")
        by_agent = {report["agent"]: report for report in reports}
        agent_a = by_agent[AGENT_A]
        if (
            started_count != 2
            or agent_a["replay_code"] != "message_replayed"
            or agent_a["option_a_state"] != "HALTED_CONFLICT"
            or agent_a["local_height_before"] != agent_a["local_height_after"]
            or agent_a["ledger_mutated"] is not False
            or agent_a["canonical_state_changed"] is not False
        ):
            raise Foundation158PreflightError("required_evidence_incomplete")
        if time.monotonic() >= deadline:
            raise Foundation158PreflightError("maximum_duration_exceeded")
        result = "PASS"
    except BaseException as exc:
        execution_error = exc
        result = "ABORT"
    finally:
        if claimed:
            try:
                cleanup = _cleanup_after_claim(
                    processes, startup_records, temp_root
                )
            except BaseException as exc:
                cleanup = {
                    "cleanup_success": False,
                    "errors": ["cleanup_supervisor:" + _exception_text(exc)],
                }
            if not cleanup.get("cleanup_success", False):
                result = "TERMINAL_CLEANUP_FAILURE"
            try:
                _finalize_authorization(
                    result,
                    cleanup,
                    _exception_text(execution_error) if execution_error else None,
                )
            except BaseException as exc:
                terminalization_error = exc
    if terminalization_error is not None:
        raise Foundation158TerminalizationError(
            terminalization_error, cleanup
        ) from execution_error
    if execution_error is not None:
        raise execution_error
    return {
        "profile": PROFILE,
        "result": result,
        "authorization_id": AUTHORIZATION_ID,
        "agent_count": 2,
        "process_count": started_count,
        "session_count": SESSION_COUNT,
        "reconnect_count": RECONNECT_COUNT,
        "maximum_active_duration_seconds": MAX_DURATION_SECONDS,
        "agent_reports": {report["agent"]: report for report in reports},
        "cleanup": cleanup,
        "authority": {
            key: False for key in (
                "candidate_auto_applied",
                "automatic_reorg",
                "fork_winner_selected",
                "canonical_height_overridden",
                "ledger_mutated",
                "issuance_authority",
                "supply_authority",
                "validation_authority",
                "history_authority",
                "protocol_authority",
                "wallet_created",
                "signing_performed",
                "mining_performed",
                "broadcast_performed",
                "settlement_performed",
                "external_network_used",
            )
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--execute-once", action="store_true")
    parser.add_argument("--authorization-id")
    parser.add_argument("--baseline-commit")
    parser.add_argument("--preflight-gate-sha256")
    args = parser.parse_args()
    if args.dry_run:
        result = dry_run_preflight()
    else:
        if not all(
            (
                args.authorization_id,
                args.baseline_commit,
                args.preflight_gate_sha256,
            )
        ):
            raise Foundation158PreflightError("explicit_execution_invocation_incomplete")
        result = run_authorized_experiment_once(
            authorization_id=args.authorization_id,
            baseline_commit=args.baseline_commit,
            preflight_gate_sha256=args.preflight_gate_sha256,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
