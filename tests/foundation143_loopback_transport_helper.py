# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import json
import socket
import struct
import sys
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coin.disposable_testnet_identity import PROTECTED_ECONOMIC_FACTS
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


PROFILE = "l28-foundation143-isolated-loopback-experiment/v0.1"
HOST = "127.0.0.1"
PORT_A = 28428
PORT_B = 28429
MAX_FRAME_BYTES = 4096
PREFIX_BYTES = 4
SOCKET_TIMEOUT_SECONDS = 3.0


class Foundation143ExperimentError(Exception):
    pass


def valid_config() -> dict[str, Any]:
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
            "protected_economic_facts": copy.deepcopy(
                PROTECTED_ECONOMIC_FACTS
            ),
        },
        "key_policy": {
            "allow_production_keys": False,
            "allow_creator_private_material": False,
            "allow_external_wallet_paths": False,
        },
        "acknowledge_disposable_test_only": True,
    }


def runtime_context():
    binding, tip = prepare_runtime_boundary(
        valid_config(),
        acknowledge_test_only=True,
    )

    plan = build_two_agent_experiment_plan(
        binding,
        tip,
    )

    validate_two_agent_experiment_plan(
        plan,
        binding,
        tip,
    )

    if plan.readiness != READINESS:
        raise Foundation143ExperimentError(
            "foundation142_readiness_missing"
        )

    by_id = {
        item.agent_id: item
        for item in plan.agents
    }

    if (
        by_id[AGENT_A].host != HOST
        or by_id[AGENT_A].port != PORT_A
        or by_id[AGENT_B].host != HOST
        or by_id[AGENT_B].port != PORT_B
    ):
        raise Foundation143ExperimentError(
            "foundation142_topology_mismatch"
        )

    return binding, tip, plan


def _recv_exact(
    sock: socket.socket,
    count: int,
) -> bytes:
    chunks = []
    remaining = count

    while remaining:
        chunk = sock.recv(remaining)

        if not chunk:
            raise Foundation143ExperimentError(
                "unexpected_transport_eof"
            )

        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)


def _send_wire(
    sock: socket.socket,
    payload: bytes,
) -> None:
    if type(payload) is not bytes:
        raise Foundation143ExperimentError(
            "wire_payload_not_bytes"
        )

    if len(payload) > MAX_FRAME_BYTES:
        raise Foundation143ExperimentError(
            "wire_frame_too_large"
        )

    sock.sendall(
        struct.pack("!I", len(payload))
        + payload
    )


def _recv_wire(
    sock: socket.socket,
) -> bytes:
    prefix = _recv_exact(
        sock,
        PREFIX_BYTES,
    )

    size = struct.unpack(
        "!I",
        prefix,
    )[0]

    if size > MAX_FRAME_BYTES:
        raise Foundation143ExperimentError(
            "wire_frame_too_large"
        )

    return _recv_exact(
        sock,
        size,
    )


def _build_frames(
    binding,
    tip,
):
    hello_b = build_offline_frame(
        binding,
        tip,
        message_type="HELLO",
        peer_id=AGENT_B,
        nonce="f143-b-hello-001",
        timestamp=1000,
        expiry=1100,
        payload={
            "agent_id": AGENT_B,
            "evidence_only": True,
        },
    )

    tip_b = build_offline_frame(
        binding,
        tip,
        message_type="TIP_EVIDENCE",
        peer_id=AGENT_B,
        nonce="f143-b-tip-001",
        timestamp=1000,
        expiry=1100,
        payload={
            "height": 0,
            "evidence_only": True,
        },
    )

    candidate_b = build_offline_frame(
        binding,
        tip,
        message_type="CANDIDATE_EVIDENCE",
        peer_id=AGENT_B,
        nonce="f143-b-candidate-001",
        timestamp=1000,
        expiry=1100,
        payload={
            "candidate_id": "candidate-001",
            "evidence_only": True,
            "apply": False,
        },
    )

    hello_a = build_offline_frame(
        binding,
        tip,
        message_type="HELLO",
        peer_id=AGENT_A,
        nonce="f143-a-hello-001",
        timestamp=1000,
        expiry=1100,
        payload={
            "agent_id": AGENT_A,
            "evidence_only": True,
        },
    )

    return {
        "hello_b": (
            hello_b,
            encode_frame_bytes(hello_b),
        ),
        "tip_b": (
            tip_b,
            encode_frame_bytes(tip_b),
        ),
        "candidate_b": (
            candidate_b,
            encode_frame_bytes(candidate_b),
        ),
        "hello_a": (
            hello_a,
            encode_frame_bytes(hello_a),
        ),
    }


def _make_listener() -> socket.socket:
    listener = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    listener.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    listener.settimeout(
        SOCKET_TIMEOUT_SECONDS
    )

    listener.bind(
        (HOST, PORT_A)
    )

    listener.listen(2)

    bound = listener.getsockname()

    if bound[0] != HOST or bound[1] != PORT_A:
        listener.close()
        raise Foundation143ExperimentError(
            "listener_scope_mismatch"
        )

    return listener


def _make_client() -> socket.socket:
    client = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    client.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    client.settimeout(
        SOCKET_TIMEOUT_SECONDS
    )

    client.bind(
        (HOST, PORT_B)
    )

    bound = client.getsockname()

    if bound[0] != HOST or bound[1] != PORT_B:
        client.close()
        raise Foundation143ExperimentError(
            "client_scope_mismatch"
        )

    client.connect(
        (HOST, PORT_A)
    )

    peer = client.getpeername()

    if peer[0] != HOST or peer[1] != PORT_A:
        client.close()
        raise Foundation143ExperimentError(
            "client_peer_scope_mismatch"
        )

    return client


def run_authorized_experiment() -> dict[str, Any]:
    binding, tip, plan = runtime_context()
    frames = _build_frames(
        binding,
        tip,
    )

    local_tip_before = tip.read_height()

    server_seen_ids: set[str] = set()
    server_seen_nonces: set[str] = set()

    client_seen_ids: set[str] = set()
    client_seen_nonces: set[str] = set()

    server_state: dict[str, Any] = {
        "error": None,
        "valid_codes": [],
        "replay_code": None,
        "source_endpoint_verified": False,
    }

    listener = _make_listener()

    def server_worker() -> None:
        try:
            conn, address = listener.accept()

            with conn:
                conn.settimeout(
                    SOCKET_TIMEOUT_SECONDS
                )

                if (
                    address[0] != HOST
                    or address[1] != PORT_B
                ):
                    raise Foundation143ExperimentError(
                        "unexpected_agent_b_endpoint"
                    )

                server_state[
                    "source_endpoint_verified"
                ] = True

                for name in (
                    "hello_b",
                    "tip_b",
                    "candidate_b",
                ):
                    incoming = _recv_wire(
                        conn
                    )

                    result = assess_frame_bytes(
                        incoming,
                        binding,
                        tip,
                        now_ts=1000,
                        seen_message_ids=server_seen_ids,
                        seen_nonce_keys=server_seen_nonces,
                    )

                    server_state[
                        "valid_codes"
                    ].append(result.code)

                    if (
                        not result.ok
                        or result.normalized_frame is None
                    ):
                        raise Foundation143ExperimentError(
                            "valid_frame_rejected:"
                            + result.code
                        )

                    server_seen_ids.add(
                        result.message_id
                    )

                    server_seen_nonces.add(
                        nonce_replay_key(
                            result.normalized_frame
                        )
                    )

                _send_wire(
                    conn,
                    frames["hello_a"][1],
                )

            replay_conn, replay_address = (
                listener.accept()
            )

            with replay_conn:
                replay_conn.settimeout(
                    SOCKET_TIMEOUT_SECONDS
                )

                if (
                    replay_address[0] != HOST
                    or replay_address[1] != PORT_B
                ):
                    raise Foundation143ExperimentError(
                        "unexpected_reconnect_endpoint"
                    )

                replay_bytes = _recv_wire(
                    replay_conn
                )

                replay_result = assess_frame_bytes(
                    replay_bytes,
                    binding,
                    tip,
                    now_ts=1000,
                    seen_message_ids=server_seen_ids,
                    seen_nonce_keys=server_seen_nonces,
                )

                server_state[
                    "replay_code"
                ] = replay_result.code

                if (
                    replay_result.ok
                    or replay_result.code
                    != "message_replayed"
                ):
                    raise Foundation143ExperimentError(
                        "replay_not_rejected"
                    )

        except Exception as exc:
            server_state["error"] = (
                type(exc).__name__
                + ":"
                + str(exc)
            )

        finally:
            listener.close()

    thread = threading.Thread(
        target=server_worker,
        name="foundation143-agent-a",
        daemon=False,
    )

    thread.start()

    with _make_client() as client:
        for name in (
            "hello_b",
            "tip_b",
            "candidate_b",
        ):
            _send_wire(
                client,
                frames[name][1],
            )

        response = _recv_wire(
            client
        )

        response_result = assess_frame_bytes(
            response,
            binding,
            tip,
            now_ts=1000,
            seen_message_ids=client_seen_ids,
            seen_nonce_keys=client_seen_nonces,
        )

        if (
            not response_result.ok
            or response_result.message_type
            != "HELLO"
            or response_result.peer_id
            != AGENT_A
            or response_result.normalized_frame
            is None
        ):
            raise Foundation143ExperimentError(
                "agent_a_hello_rejected:"
                + response_result.code
            )

        client_seen_ids.add(
            response_result.message_id
        )

        client_seen_nonces.add(
            nonce_replay_key(
                response_result.normalized_frame
            )
        )

    with _make_client() as replay_client:
        _send_wire(
            replay_client,
            frames["hello_b"][1],
        )

    thread.join(
        SOCKET_TIMEOUT_SECONDS
    )

    if thread.is_alive():
        raise Foundation143ExperimentError(
            "server_thread_did_not_stop"
        )

    if server_state["error"] is not None:
        raise Foundation143ExperimentError(
            server_state["error"]
        )

    if server_state["valid_codes"] != [
        "admitted_offline_evidence",
        "admitted_offline_evidence",
        "admitted_offline_evidence",
    ]:
        raise Foundation143ExperimentError(
            "unexpected_admission_codes"
        )

    if server_state["replay_code"] != "message_replayed":
        raise Foundation143ExperimentError(
            "replay_evidence_missing"
        )

    local_tip_after = tip.read_height()

    if local_tip_before != 0 or local_tip_after != 0:
        raise Foundation143ExperimentError(
            "local_tip_changed"
        )

    frame_hashes = {
        name: hashlib.sha256(
            value[1]
        ).hexdigest()
        for name, value in frames.items()
    }

    frame_ids = {
        name: value[0]["message_id"]
        for name, value in frames.items()
    }

    return {
        "profile": PROFILE,
        "result": "PASS",
        "operator_authorization_scope": (
            "FOUNDATION143_ISOLATED_LOOPBACK_NETWORK_EXPERIMENT"
        ),
        "authorization_persistent": False,
        "topology": {
            "agent_count": 2,
            "agent_a": {
                "id": AGENT_A,
                "host": HOST,
                "port": PORT_A,
                "role": "DESIGNATED_LOCAL_CORE_WRITER",
            },
            "agent_b": {
                "id": AGENT_B,
                "host": HOST,
                "port": PORT_B,
                "role": "PEER_EVIDENCE_ONLY",
            },
            "ipv4_loopback_only": True,
            "external_network_used": False,
        },
        "actual_transport": {
            "socket_opened": True,
            "listener_started": True,
            "outbound_connection_started": True,
            "tcp_connection_established": True,
            "source_endpoint_verified": server_state[
                "source_endpoint_verified"
            ],
            "valid_session_completed": True,
            "reconnect_completed": True,
            "sockets_closed_after_experiment": True,
            "subprocess_started": False,
            "production_p2p_runtime_started": False,
            "rpc_started": False,
        },
        "propagation": {
            "agent_b_to_agent_a": [
                "HELLO",
                "TIP_EVIDENCE",
                "CANDIDATE_EVIDENCE",
            ],
            "agent_a_to_agent_b": [
                "HELLO",
            ],
            "all_valid_frames_admitted": True,
            "frame_ids": frame_ids,
            "frame_sha256": frame_hashes,
        },
        "reconnect_replay": {
            "replay_state_preserved": True,
            "replayed_message_rejected": True,
            "stable_code": "message_replayed",
            "disconnect_required": True,
        },
        "authority_preservation": {
            "local_tip_before": local_tip_before,
            "local_tip_after": local_tip_after,
            "ledger_mutated": False,
            "canonical_height_overridden": False,
            "issuance_authority_granted": False,
            "supply_authority_granted": False,
            "validation_authority_granted": False,
            "history_authority_granted": False,
            "wallet_created": False,
            "key_generated": False,
            "signing_performed": False,
            "mining_performed": False,
            "public_broadcast_performed": False,
            "settlement_performed": False,
            "real_value_used": False,
            "historical_state_imported": False,
        },
        "policy_state": {
            "production_peer_authentication_defined": False,
            "trusted_production_time_defined": False,
            "production_resource_limits_defined": False,
            "confirmation_policy_defined": False,
            "reorg_policy_defined": False,
        },
        "gap_reassessment": {
            "F37-07": (
                "PARTIAL_ISOLATED_LOOPBACK_TRANSPORT_EVIDENCE"
            ),
            "F37-10": (
                "PARTIAL_ISOLATED_LOOPBACK_PROPAGATION_EVIDENCE"
            ),
            "F37-11": "BLOCKED_REORG_POLICY",
        },
        "status": (
            "ISOLATED_TWO_AGENT_PROPAGATION_EVIDENCE=PASS"
        ),
    }


def main() -> None:
    evidence = run_authorized_experiment()

    print(
        json.dumps(
            evidence,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
