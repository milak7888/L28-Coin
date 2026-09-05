# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import multiprocessing
import shutil
import socket
import struct
import sys
import tempfile
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
from coin.disposable_testnet_two_agent_gate import (
    AGENT_A,
    AGENT_B,
    READINESS,
    build_two_agent_experiment_plan,
    validate_two_agent_experiment_plan,
)


PROFILE = "l28-foundation154-one-shot-loopback-experiment/v1.0"
AUTHORIZATION_ID = "L28-F153-OPTION-A-ONE-SHOT-001"
AUTHORIZATION_PATH = (
    ROOT
    / "docs/l28_foundation153_option_a_one_shot_runtime_authorization_v1.0.json"
)
EXECUTION_STATE_PATH = (
    ROOT / "docs/l28_foundation154_one_shot_execution_state_v1.0.json"
)
HOST = "127.0.0.1"
PORT_A = 28428
PORT_B = 28429
MAX_DURATION_SECONDS = 60
MAX_FRAME_BYTES = 4096
SOCKET_TIMEOUT_SECONDS = 5.0
PREFIX_BYTES = 4
SESSION_COUNT = 2
RECONNECT_COUNT = 1


class Foundation154ExperimentError(Exception):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Foundation154ExperimentError("authorization_duplicate_key")
        result[key] = value
    return result


def load_and_validate_authorization() -> dict[str, Any]:
    data = json.loads(
        AUTHORIZATION_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    state = data["authorization_state"]
    scope = data["exact_authorized_future_experiment"]
    decision = data["operator_decision"]

    required_state = {
        "AUTHORIZATION_GRANTED": True,
        "AUTHORIZATION_CONSUMED": False,
        "CONSUMED_FOR_REUSE": False,
        "VALID_FOR_ACTIVE_EXECUTION": False,
        "EXPERIMENT_EXECUTED": False,
        "execution_gate_open": False,
        "execution_prerequisites_satisfied": False,
    }
    if state != required_state:
        raise Foundation154ExperimentError("authorization_state_invalid")
    if data["authorization_id"] != AUTHORIZATION_ID:
        raise Foundation154ExperimentError("authorization_id_invalid")
    if decision["selected_option"] != (
        "AUTHORIZE_ONE_BOUNDED_ISOLATED_RUNTIME_EXPERIMENT"
    ):
        raise Foundation154ExperimentError("authorization_decision_invalid")
    if (
        scope["agent_count"] != 2
        or scope["process_count"] != 2
        or scope["ipv4_loopback_only"] is not True
        or scope["agent_a"]["address"] != HOST
        or scope["agent_a"]["port"] != PORT_A
        or scope["agent_b"]["address"] != HOST
        or scope["agent_b"]["port"] != PORT_B
        or scope["exact_session_count"] != SESSION_COUNT
        or scope["exact_reconnect_count"] != RECONNECT_COUNT
        or scope["maximum_duration_seconds"] != MAX_DURATION_SECONDS
        or scope["replay_state_preserved_across_reconnect"] is not True
        or scope["option_a_conflict_and_equivocation_handling_mandatory"]
        is not True
        or scope["external_interfaces_or_routes_permitted"] is not False
        or scope["production_identities_or_secrets_permitted"] is not False
        or scope["historical_or_real_value_state_permitted"] is not False
    ):
        raise Foundation154ExperimentError("authorization_scope_invalid")

    for value in data["persistent_and_disallowed_authority"].values():
        if value is not False:
            raise Foundation154ExperimentError("disallowed_authority_enabled")
    for value in data["authority_firewall"].values():
        if value is not False:
            raise Foundation154ExperimentError("authority_firewall_invalid")

    source = data["source_binding"]
    for path_key, digest_key in (
        ("foundation152_record", "foundation152_record_sha256"),
        ("foundation152_gate", "foundation152_gate_sha256"),
    ):
        path = ROOT / source[path_key]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source[digest_key]:
            raise Foundation154ExperimentError("authorization_binding_mismatch")
    return data


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
    binding, tip = prepare_runtime_boundary(
        _valid_config(), acknowledge_test_only=True
    )
    plan = build_two_agent_experiment_plan(binding, tip)
    validate_two_agent_experiment_plan(plan, binding, tip)
    by_id = {agent.agent_id: agent for agent in plan.agents}
    if (
        plan.readiness != READINESS
        or len(plan.agents) != 2
        or by_id[AGENT_A].host != HOST
        or by_id[AGENT_A].port != PORT_A
        or by_id[AGENT_B].host != HOST
        or by_id[AGENT_B].port != PORT_B
    ):
        raise Foundation154ExperimentError("two_agent_plan_invalid")
    return binding, tip


def _candidate_histories() -> tuple[CandidateHistory, CandidateHistory]:
    common = HistoryEntry(0, "f154-public-genesis", "GENESIS")
    first = CandidateHistory(
        source_id=AGENT_B,
        network_id="L28-DISPOSABLE-LAB001",
        genesis_hash="f154-public-genesis",
        entries=(common, HistoryEntry(1, "f154-public-left", common.block_id)),
    )
    second = CandidateHistory(
        source_id=AGENT_B,
        network_id="L28-DISPOSABLE-LAB001",
        genesis_hash="f154-public-genesis",
        entries=(common, HistoryEntry(1, "f154-public-right", common.block_id)),
    )
    return first, second


def _build_frames(binding, tip) -> dict[str, bytes]:
    specs = {
        "hello_b": ("HELLO", "f154-b-hello-001", {"agent_id": AGENT_B, "evidence_only": True}),
        "tip_b": ("TIP_EVIDENCE", "f154-b-tip-001", {"height": 0, "evidence_only": True}),
        "candidate_session1": ("CANDIDATE_EVIDENCE", "f154-b-candidate-001", {"candidate_id": "f154-public-baseline", "evidence_only": True, "apply": False}),
        "candidate_left": ("CANDIDATE_EVIDENCE", "f154-b-candidate-002", {"candidate_id": "f154-public-left", "evidence_only": True, "apply": False}),
        "candidate_right": ("CANDIDATE_EVIDENCE", "f154-b-candidate-003", {"candidate_id": "f154-public-right", "evidence_only": True, "apply": False}),
        "hello_a": ("HELLO", "f154-a-hello-001", {"agent_id": AGENT_A, "evidence_only": True}),
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
                payload=payload,
            )
        )
        for name, (message_type, nonce, payload) in specs.items()
    }


def dry_run_preflight() -> dict[str, Any]:
    authorization = load_and_validate_authorization()
    binding, tip = _runtime_context()
    frames = _build_frames(binding, tip)
    first, second = _candidate_histories()
    assessment = assess_peer_equivocation(first, second)
    halted = transition_sync_state(
        OptionAPolicyState("SYNCING", "F154_PRE_EXECUTION"), assessment
    )
    if assessment.code != "HALT_SYNC_PEER_EQUIVOCATION" or halted.status != "HALTED_CONFLICT":
        raise Foundation154ExperimentError("option_a_integration_invalid")
    return {
        "profile": PROFILE,
        "mode": "DRY_RUN_PREFLIGHT",
        "authorization_id": authorization["authorization_id"],
        "agent_count": 2,
        "process_count": 2,
        "host": HOST,
        "ports": [PORT_A, PORT_B],
        "session_count": SESSION_COUNT,
        "reconnect_count": RECONNECT_COUNT,
        "maximum_duration_seconds": MAX_DURATION_SECONDS,
        "frame_count": len(frames),
        "option_a_code": assessment.code,
        "option_a_state": halted.status,
        "sockets_opened": False,
        "processes_started": False,
        "authorization_consumed": False,
        "experiment_executed": False,
    }


def _recv_exact(sock: socket.socket, count: int) -> bytes:
    chunks: list[bytes] = []
    while count:
        chunk = sock.recv(count)
        if not chunk:
            raise Foundation154ExperimentError("unexpected_transport_eof")
        chunks.append(chunk)
        count -= len(chunk)
    return b"".join(chunks)


def _send_wire(sock: socket.socket, payload: bytes) -> None:
    if type(payload) is not bytes or len(payload) > MAX_FRAME_BYTES:
        raise Foundation154ExperimentError("wire_frame_invalid")
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def _recv_wire(sock: socket.socket) -> bytes:
    size = struct.unpack("!I", _recv_exact(sock, PREFIX_BYTES))[0]
    if size > MAX_FRAME_BYTES:
        raise Foundation154ExperimentError("wire_frame_too_large")
    return _recv_exact(sock, size)


def _agent_a(frames: dict[str, bytes], data_dir: str, ready, results) -> None:
    listener = None
    try:
        if not Path(data_dir).is_dir():
            raise Foundation154ExperimentError("agent_a_data_dir_missing")
        binding, tip = _runtime_context()
        local_before = tip.read_height()
        seen_ids: set[str] = set()
        seen_nonces: set[str] = set()
        admitted: list[str] = []
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.settimeout(SOCKET_TIMEOUT_SECONDS)
        listener.bind((HOST, PORT_A))
        listener.listen(1)
        if listener.getsockname() != (HOST, PORT_A):
            raise Foundation154ExperimentError("agent_a_bind_scope_invalid")
        ready.set()

        conn, address = listener.accept()
        with conn:
            conn.settimeout(SOCKET_TIMEOUT_SECONDS)
            if address != (HOST, PORT_B):
                raise Foundation154ExperimentError("agent_b_endpoint_invalid")
            for _ in range(3):
                result = assess_frame_bytes(
                    _recv_wire(conn), binding, tip, now_ts=1000,
                    seen_message_ids=seen_ids, seen_nonce_keys=seen_nonces,
                )
                if not result.ok or result.normalized_frame is None:
                    raise Foundation154ExperimentError("session1_admission_failed:" + result.code)
                admitted.append(result.code)
                seen_ids.add(result.message_id)
                seen_nonces.add(nonce_replay_key(result.normalized_frame))
            _send_wire(conn, frames["hello_a"])

        conn, address = listener.accept()
        with conn:
            conn.settimeout(SOCKET_TIMEOUT_SECONDS)
            if address != (HOST, PORT_B):
                raise Foundation154ExperimentError("agent_b_reconnect_endpoint_invalid")
            for _ in range(2):
                result = assess_frame_bytes(
                    _recv_wire(conn), binding, tip, now_ts=1000,
                    seen_message_ids=seen_ids, seen_nonce_keys=seen_nonces,
                )
                if not result.ok or result.normalized_frame is None:
                    raise Foundation154ExperimentError("session2_candidate_failed:" + result.code)
                admitted.append(result.code)
                seen_ids.add(result.message_id)
                seen_nonces.add(nonce_replay_key(result.normalized_frame))
            first, second = _candidate_histories()
            assessment = assess_peer_equivocation(first, second)
            halted = transition_sync_state(
                OptionAPolicyState("SYNCING", "F154_ACTIVE"), assessment
            )
            replay = assess_frame_bytes(
                _recv_wire(conn), binding, tip, now_ts=1000,
                seen_message_ids=seen_ids, seen_nonce_keys=seen_nonces,
            )
            if replay.ok or replay.code != "message_replayed":
                raise Foundation154ExperimentError("replay_not_rejected")
            local_after = tip.read_height()
            results.put({
                "agent": AGENT_A,
                "result": "PASS",
                "session_count": 2,
                "admission_codes": admitted,
                "replay_code": replay.code,
                "replay_disconnect": replay.disconnect,
                "equivocation_code": assessment.code,
                "equivocation_detected": assessment.conflict,
                "option_a_status": halted.status,
                "option_a_code": halted.code,
                "halt_height": halted.halt_height,
                "retain_current_local_canonical_state": assessment.retain_current_local_canonical_state,
                "local_tip_before": local_before,
                "local_tip_after": local_after,
                "ledger_mutated": halted.ledger_mutated,
                "canonical_state_changed": halted.canonical_state_changed,
            })
    except Exception as exc:
        ready.set()
        results.put({"agent": AGENT_A, "result": "FAIL", "error": type(exc).__name__ + ":" + str(exc)})
    finally:
        if listener is not None:
            listener.close()


def _connect_client() -> socket.socket:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client.settimeout(SOCKET_TIMEOUT_SECONDS)
    client.bind((HOST, PORT_B))
    if client.getsockname() != (HOST, PORT_B):
        client.close()
        raise Foundation154ExperimentError("agent_b_bind_scope_invalid")
    client.connect((HOST, PORT_A))
    if client.getpeername() != (HOST, PORT_A):
        client.close()
        raise Foundation154ExperimentError("agent_b_peer_scope_invalid")
    return client


def _agent_b(frames: dict[str, bytes], data_dir: str, ready, results) -> None:
    try:
        if not Path(data_dir).is_dir():
            raise Foundation154ExperimentError("agent_b_data_dir_missing")
        if not ready.wait(SOCKET_TIMEOUT_SECONDS):
            raise Foundation154ExperimentError("agent_a_not_ready")
        binding, tip = _runtime_context()
        with _connect_client() as client:
            for name in ("hello_b", "tip_b", "candidate_session1"):
                _send_wire(client, frames[name])
            response = assess_frame_bytes(
                _recv_wire(client), binding, tip, now_ts=1000,
                seen_message_ids=set(), seen_nonce_keys=set(),
            )
            if not response.ok or response.peer_id != AGENT_A:
                raise Foundation154ExperimentError("agent_a_response_invalid")
        with _connect_client() as client:
            _send_wire(client, frames["candidate_left"])
            _send_wire(client, frames["candidate_right"])
            _send_wire(client, frames["hello_b"])
        results.put({"agent": AGENT_B, "result": "PASS", "session_count": 2, "reconnect_count": 1})
    except Exception as exc:
        results.put({"agent": AGENT_B, "result": "FAIL", "error": type(exc).__name__ + ":" + str(exc)})


def run_authorized_experiment_once() -> dict[str, Any]:
    if EXECUTION_STATE_PATH.exists():
        state = json.loads(
            EXECUTION_STATE_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
        final_state = state.get("final_state", {})
        if final_state.get("AUTHORIZATION_CONSUMED") is True:
            raise Foundation154ExperimentError("authorization_already_consumed")
        raise Foundation154ExperimentError("execution_state_conflict")
    authorization = load_and_validate_authorization()
    binding, tip = _runtime_context()
    frames = _build_frames(binding, tip)
    temp_root = Path(tempfile.mkdtemp(prefix="l28-f154-"))
    data_a = temp_root / "agent-a"
    data_b = temp_root / "agent-b"
    data_a.mkdir()
    data_b.mkdir()
    ctx = multiprocessing.get_context("spawn")
    ready = ctx.Event()
    results = ctx.Queue()
    processes = [
        ctx.Process(target=_agent_a, args=(frames, str(data_a), ready, results), name="foundation154-agent-a"),
        ctx.Process(target=_agent_b, args=(frames, str(data_b), ready, results), name="foundation154-agent-b"),
    ]
    started_at_epoch = int(time.time())
    started_at_monotonic = time.monotonic()
    started_count = 0
    reports: list[dict[str, Any]] = []
    cleanup = {"sockets_closed": False, "processes_stopped": False, "temp_state_cleaned": False}
    try:
        for process in processes:
            process.start()
            started_count += 1
        deadline = started_at_monotonic + MAX_DURATION_SECONDS
        for process in processes:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Foundation154ExperimentError("maximum_duration_exceeded")
            process.join(remaining)
        if any(process.is_alive() for process in processes):
            raise Foundation154ExperimentError("maximum_duration_exceeded")
        reports = [results.get(timeout=1.0) for _ in range(2)]
        if any(report.get("result") != "PASS" for report in reports):
            raise Foundation154ExperimentError("agent_failure:" + json.dumps(reports, sort_keys=True))
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
        for process in processes:
            process.join(2.0)
        cleanup["processes_stopped"] = all(not process.is_alive() for process in processes)
        cleanup["sockets_closed"] = cleanup["processes_stopped"]
        shutil.rmtree(temp_root)
        cleanup["temp_state_cleaned"] = not temp_root.exists()

    duration = time.monotonic() - started_at_monotonic
    by_agent = {report["agent"]: report for report in reports}
    agent_a = by_agent[AGENT_A]
    result = "PASS" if (
        started_count == 2
        and duration < MAX_DURATION_SECONDS
        and agent_a["replay_code"] == "message_replayed"
        and agent_a["equivocation_code"] == "HALT_SYNC_PEER_EQUIVOCATION"
        and agent_a["option_a_status"] == "HALTED_CONFLICT"
        and agent_a["local_tip_before"] == agent_a["local_tip_after"] == 0
        and agent_a["ledger_mutated"] is False
        and agent_a["canonical_state_changed"] is False
        and all(cleanup.values())
    ) else "FAIL"
    frame_sha256 = {
        name: hashlib.sha256(value).hexdigest() for name, value in frames.items()
    }
    return {
        "profile": PROFILE,
        "result": result,
        "authorization_id": authorization["authorization_id"],
        "started_at_epoch_seconds": started_at_epoch,
        "duration_seconds": round(duration, 6),
        "process_count": started_count,
        "agent_count": 2,
        "addresses": {"agent_a": f"{HOST}:{PORT_A}", "agent_b": f"{HOST}:{PORT_B}"},
        "session_count": 2,
        "reconnect_count": 1,
        "external_network_used": False,
        "frame_sha256": frame_sha256,
        "agent_reports": by_agent,
        "cleanup": cleanup,
        "authority": {
            "candidate_auto_applied": False,
            "automatic_reorg": False,
            "fork_winner_selected": False,
            "canonical_height_overridden": False,
            "ledger_mutated": False,
            "issuance_authority": False,
            "supply_authority": False,
            "validation_authority": False,
            "consensus_authority": False,
            "history_authority": False,
            "settlement_authority": False,
            "wallet_created": False,
            "key_created": False,
            "signing_performed": False,
            "mining_performed": False,
            "broadcast_performed": False,
        },
        "final_authorization": {
            "AUTHORIZATION_CONSUMED": True,
            "CONSUMED_FOR_REUSE": True,
            "VALID_FOR_ACTIVE_EXECUTION": False,
            "EXPERIMENT_EXECUTED": True,
            "RESTART_ALLOWED": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--execute-once", action="store_true")
    args = parser.parse_args()
    result = dry_run_preflight() if args.dry_run else run_authorized_experiment_once()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
