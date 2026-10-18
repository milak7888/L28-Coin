# SPDX-License-Identifier: Apache-2.0
"""Persistent two-node disposable L28 ledger core over IPv4 loopback.

This module is an explicitly bounded non-production executable. A writer and
follower independently validate the same coinbase and transfer, persist them
through :class:`BlocklessLedger`, stop, restart, validate durable replay, and
compare public state commitments. It does not implement consensus, finality,
mining, canonical history, public networking, or production signing.

One disposable Ed25519 private key exists only inside the initial writer
process. It is never serialized, persisted, logged, or returned as evidence.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import select
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from coin.disposable_testnet_identity import (
    BROADCAST_AUTHORIZED,
    GENESIS_PROFILE,
    MINING_AUTHORIZED,
    NETWORK_AUTHORIZED,
    NETWORK_SCOPE,
    PROFILE as IDENTITY_PROFILE,
    PROTECTED_ECONOMIC_FACTS,
    PROTOCOL_VERSION,
    RUNTIME_AUTHORIZED,
    SETTLEMENT_AUTHORIZED,
    SIGNING_AUTHORIZED,
    TESTNET_START_AUTHORIZED,
    validate_and_bind_disposable_testnet_config,
)
from coin.disposable_testnet_option_a_policy import (
    CandidateHistory,
    HistoryEntry,
    OptionAPolicyState,
    assess_option_a,
    transition_sync_state,
)
from coin.ledger import BlocklessLedger
from coin.mining import build_coinbase_tx
from coin.tx_validation import TxPolicy, compute_tx_id, validate_transaction


PROFILE = "l28-persistent-disposable-two-node-core/v0.1"
NETWORK_ID = "L28-DISPOSABLE-PERSISTENT001"
DATA_DIR_TAG = "l28-disposable-testnet:persistent001"
HOST = "127.0.0.1"
TRANSPORT_VERSION = 1
MAX_FRAME_BYTES = 65_536
SOCKET_TIMEOUT_SECONDS = 10.0
PARENT_DEADLINE_SECONDS = 120.0
COINBASE_TIMESTAMP = 1_700_000_000
TRANSFER_TIMESTAMP = COINBASE_TIMESTAMP + 1
TRANSFER_AMOUNT = 28
SIGN_DOMAIN = b"L28-PERSISTENT-DISPOSABLE-TRANSFER-V0.1\x00"

FRAME_FIELDS = (
    "config_hash",
    "genesis_hash",
    "message_type",
    "network_id",
    "payload",
    "profile",
    "sequence",
    "version",
)
MESSAGE_TYPES = frozenset(
    {"initial_events", "initial_state", "restart_probe", "restart_state"}
)
COINBASE_FIELDS = frozenset(
    {
        "amount",
        "coinbase",
        "height",
        "id",
        "miner",
        "network",
        "nonce",
        "profile",
        "receiver",
        "sender",
        "signature",
        "timestamp",
        "type",
    }
)
TRANSFER_FIELDS = frozenset(
    {
        "amount",
        "id",
        "network",
        "nonce",
        "profile",
        "receiver",
        "sender",
        "sender_public_key",
        "signature",
        "timestamp",
        "type",
    }
)
SIGNABLE_TRANSFER_FIELDS = (
    "amount",
    "network",
    "nonce",
    "profile",
    "receiver",
    "sender",
    "sender_public_key",
    "timestamp",
    "type",
)
STATE_FIELDS = frozenset(
    {
        "balances",
        "issued_supply",
        "mint_height",
        "state_commitment",
        "total_transactions",
        "total_volume",
        "transaction_ids",
    }
)


class PersistentNodeError(Exception):
    """Fail-closed public error code for the disposable node workflow."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise PersistentNodeError("noncanonical_json") from exc


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PersistentNodeError("duplicate_json_key")
        result[key] = value
    return result


def _exact_mapping(
    value: Any,
    fields: frozenset[str] | set[str],
    code: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(fields):
        raise PersistentNodeError(code)
    return value


def _exact_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool)


def assert_production_authority_inactive() -> None:
    if any(
        (
            RUNTIME_AUTHORIZED,
            NETWORK_AUTHORIZED,
            TESTNET_START_AUTHORIZED,
            SIGNING_AUTHORIZED,
            MINING_AUTHORIZED,
            BROADCAST_AUTHORIZED,
            SETTLEMENT_AUTHORIZED,
        )
    ):
        raise PersistentNodeError("production_authority_mutated")


def persistent_testnet_config() -> dict[str, Any]:
    return {
        "profile": IDENTITY_PROFILE,
        "protocol_version": PROTOCOL_VERSION,
        "network_scope": NETWORK_SCOPE,
        "network_id": NETWORK_ID,
        "data_dir_tag": DATA_DIR_TAG,
        "genesis": {
            "profile": GENESIS_PROFILE,
            "network_id": NETWORK_ID,
            "initial_height": 0,
            "initial_issued_supply": 0,
            "historical_checkpoint_imported": False,
            "historical_balances_loaded": False,
            "protected_economic_facts": dict(PROTECTED_ECONOMIC_FACTS),
        },
        "key_policy": {
            "allow_production_keys": False,
            "allow_creator_private_material": False,
            "allow_external_wallet_paths": False,
        },
        "acknowledge_disposable_test_only": True,
    }


def persistent_testnet_binding() -> dict[str, Any]:
    assert_production_authority_inactive()
    binding = validate_and_bind_disposable_testnet_config(
        persistent_testnet_config()
    )
    if (
        binding["network_id"] != NETWORK_ID
        or binding["data_dir_tag"] != DATA_DIR_TAG
        or binding["runtime_authorized"] is not False
        or binding["network_authorized"] is not False
        or binding["testnet_start_authorized"] is not False
        or binding["signing_authorized"] is not False
        or binding["mining_authorized"] is not False
        or binding["broadcast_authorized"] is not False
        or binding["settlement_authorized"] is not False
    ):
        raise PersistentNodeError("disposable_binding_invalid")
    return binding


def _public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes_raw().hex()


def public_identity(public_key_hex: str) -> str:
    try:
        raw = bytes.fromhex(public_key_hex)
    except (TypeError, ValueError) as exc:
        raise PersistentNodeError("public_key_invalid") from exc
    if len(raw) != 32:
        raise PersistentNodeError("public_key_invalid")
    return "l28disp_" + hashlib.sha256(raw).hexdigest()


def follower_identity(binding: Mapping[str, Any]) -> str:
    material = (
        "L28-PERSISTENT-FOLLOWER-V0.1:" + str(binding["config_hash"])
    ).encode("ascii")
    return "l28disp_" + hashlib.sha256(material).hexdigest()


def signable_transfer_bytes(tx: Mapping[str, Any]) -> bytes:
    if not isinstance(tx, Mapping):
        raise PersistentNodeError("transfer_malformed")
    payload: dict[str, Any] = {}
    for field in SIGNABLE_TRANSFER_FIELDS:
        if field not in tx:
            raise PersistentNodeError("transfer_malformed")
        payload[field] = tx[field]
    if (
        payload["network"] != NETWORK_ID
        or payload["profile"] != PROFILE
        or payload["type"] != "transfer"
    ):
        raise PersistentNodeError("transfer_binding_invalid")
    return SIGN_DOMAIN + _canonical_bytes(payload)


def verify_transfer_signature(tx: Mapping[str, Any]) -> bool:
    try:
        if not isinstance(tx, dict):
            return False
        public_hex = tx.get("sender_public_key")
        signature_hex = tx.get("signature")
        if not isinstance(public_hex, str) or not isinstance(signature_hex, str):
            return False
        public_bytes = bytes.fromhex(public_hex)
        signature = bytes.fromhex(signature_hex)
        if len(public_bytes) != 32 or len(signature) != 64:
            return False
        if tx.get("sender") != public_identity(public_hex):
            return False
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(
            signature,
            signable_transfer_bytes(tx),
        )
    except (InvalidSignature, PersistentNodeError, TypeError, ValueError):
        return False
    return True


def _build_coinbase(writer_identity: str) -> dict[str, Any]:
    tx = build_coinbase_tx(
        writer_identity,
        nonce=0,
        height=0,
        timestamp=COINBASE_TIMESTAMP,
        network=NETWORK_ID,
    )
    tx["profile"] = PROFILE
    tx["id"] = compute_tx_id(tx)
    validate_node_event(tx)
    return tx


def _build_signed_transfer(
    private_key: Ed25519PrivateKey,
    receiver: str,
) -> dict[str, Any]:
    public_hex = _public_key_hex(private_key)
    body = {
        "sender": public_identity(public_hex),
        "receiver": receiver,
        "sender_public_key": public_hex,
        "amount": TRANSFER_AMOUNT,
        "timestamp": TRANSFER_TIMESTAMP,
        "type": "transfer",
        "network": NETWORK_ID,
        "profile": PROFILE,
        "nonce": 1,
    }
    tx = dict(body)
    tx["signature"] = private_key.sign(signable_transfer_bytes(body)).hex()
    tx["id"] = compute_tx_id(tx)
    validate_node_event(tx)
    return tx


def validate_node_event(tx: Any) -> bool:
    if not isinstance(tx, dict):
        raise PersistentNodeError("event_malformed")
    event_type = tx.get("type")
    fields = COINBASE_FIELDS if event_type == "coinbase" else TRANSFER_FIELDS
    _exact_mapping(tx, fields, "event_schema_invalid")
    if tx.get("network") != NETWORK_ID or tx.get("profile") != PROFILE:
        raise PersistentNodeError("event_network_invalid")
    if not isinstance(tx.get("id"), str) or tx["id"] != compute_tx_id(tx):
        raise PersistentNodeError("event_id_invalid")
    if event_type == "coinbase":
        if (
            tx["sender"] != "COINBASE"
            or tx["coinbase"] is not True
            or tx["signature"] != "COINBASE"
            or tx["receiver"] != tx["miner"]
            or not isinstance(tx["receiver"], str)
            or not tx["receiver"]
            or tx["amount"] != 28
            or tx["height"] != 0
            or tx["nonce"] != 0
            or tx["timestamp"] != COINBASE_TIMESTAMP
            or not all(
                _exact_int(tx[field])
                for field in ("amount", "height", "nonce", "timestamp")
            )
        ):
            raise PersistentNodeError("coinbase_invalid")
        return True
    if (
        event_type != "transfer"
        or tx["receiver"] != follower_identity(persistent_testnet_binding())
        or tx["amount"] != TRANSFER_AMOUNT
        or tx["timestamp"] != TRANSFER_TIMESTAMP
        or tx["nonce"] != 1
        or not all(
            _exact_int(tx[field])
            for field in ("amount", "timestamp", "nonce")
        )
        or not verify_transfer_signature(tx)
    ):
        raise PersistentNodeError("transfer_invalid")
    return True


def _open_ledger(data_dir: Path) -> BlocklessLedger:
    return BlocklessLedger(
        data_dir=str(data_dir),
        policy=TxPolicy(require_signatures=True),
        verify_signature=verify_transfer_signature,
        require_signatures=True,
    )


def _new_ledger(data_dir: Path) -> BlocklessLedger:
    ledger = _open_ledger(data_dir)
    ledger.initialize_disposable_test_issuance_state(
        mint_height=0,
        issued_supply=0,
        acknowledge_test_only=True,
    )
    return ledger


async def _load_ledger(data_dir: Path) -> BlocklessLedger:
    ledger = _open_ledger(data_dir)
    await ledger.load_from_disk(
        validate_replay=True,
        acknowledge_disposable_test_only=True,
        expected_network=NETWORK_ID,
        validate_record=validate_node_event,
    )
    return ledger


def classify_event(
    ledger: BlocklessLedger,
    tx: dict[str, Any],
) -> tuple[bool, str, str]:
    try:
        validate_node_event(tx)
    except PersistentNodeError as exc:
        return False, "", exc.code
    before = deepcopy(tx)
    outcome = validate_transaction(
        tx,
        policy=ledger.policy,
        current_balance_lookup=ledger._current_balance_lookup,
        seen_tx_lookup=ledger._seen_tx_lookup,
        verify_signature=verify_transfer_signature,
        current_height_lookup=(lambda: int(ledger.mint_height)),
        current_issued_lookup=(lambda: int(ledger.issued_supply)),
        now_ts=TRANSFER_TIMESTAMP,
        network=NETWORK_ID,
    )
    if tx != before:
        raise PersistentNodeError("validator_mutated_event")
    return outcome


async def _apply_events(
    ledger: BlocklessLedger,
    events: list[dict[str, Any]],
) -> list[str]:
    validated: list[str] = []
    for tx in events:
        ok, tx_id, reason = classify_event(ledger, tx)
        if not ok or reason != "ok" or tx_id != tx.get("id"):
            raise PersistentNodeError("event_validation_failed:" + reason)
        if not await ledger.add_transaction(tx):
            raise PersistentNodeError("event_persistence_failed")
        validated.append(tx_id)
    return validated


def _state_commitment(material: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        b"L28-PERSISTENT-DISPOSABLE-STATE-V0.1\x00" + _canonical_bytes(material)
    ).hexdigest()


def ledger_state(ledger: BlocklessLedger) -> dict[str, Any]:
    material = {
        "transaction_ids": list(ledger.transactions.keys()),
        "balances": {
            key: int(value) for key, value in sorted(ledger.balances.items())
        },
        "issued_supply": int(ledger.issued_supply),
        "mint_height": int(ledger.mint_height),
        "total_transactions": int(ledger.total_transactions),
        "total_volume": int(ledger.total_volume),
    }
    return {**material, "state_commitment": _state_commitment(material)}


def validate_public_state(value: Any) -> dict[str, Any]:
    state = _exact_mapping(value, STATE_FIELDS, "state_schema_invalid")
    ids = state["transaction_ids"]
    balances = state["balances"]
    if (
        not isinstance(ids, list)
        or not ids
        or not all(
            isinstance(item, str)
            and len(item) == 64
            and all(char in "0123456789abcdef" for char in item)
            for item in ids
        )
        or len(ids) != len(set(ids))
        or not isinstance(balances, dict)
        or not balances
        or not all(
            isinstance(key, str)
            and key
            and _exact_int(amount)
            and amount >= 0
            for key, amount in balances.items()
        )
        or not all(
            _exact_int(state[field]) and state[field] >= 0
            for field in (
                "issued_supply",
                "mint_height",
                "total_transactions",
                "total_volume",
            )
        )
        or state["total_transactions"] != len(ids)
    ):
        raise PersistentNodeError("state_schema_invalid")
    material = {key: state[key] for key in STATE_FIELDS if key != "state_commitment"}
    if state["state_commitment"] != _state_commitment(material):
        raise PersistentNodeError("state_commitment_invalid")
    return state


def _candidate_history(
    state: Mapping[str, Any],
    *,
    source_id: str,
    binding: Mapping[str, Any],
) -> CandidateHistory:
    block_ids = [*state["transaction_ids"], state["state_commitment"]]
    entries = tuple(
        HistoryEntry(
            height=index,
            block_id=block_id,
            parent_id="GENESIS" if index == 0 else block_ids[index - 1],
        )
        for index, block_id in enumerate(block_ids)
    )
    return CandidateHistory(
        source_id=source_id,
        network_id=str(binding["network_id"]),
        genesis_hash=str(binding["genesis_hash"]),
        entries=entries,
    )


def assess_state_agreement(
    local_state: Any,
    peer_state: Any,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    local = validate_public_state(local_state)
    peer = validate_public_state(peer_state)
    local_before = deepcopy(local)
    assessment = assess_option_a(
        _candidate_history(local, source_id="LOCAL_CORE", binding=binding),
        _candidate_history(peer, source_id="PEER_FOLLOWER", binding=binding),
    )
    policy_state = transition_sync_state(
        OptionAPolicyState(status="SYNCING", code="INITIAL_SYNC"),
        assessment,
    )
    if local != local_before:
        raise PersistentNodeError("option_a_rewrote_local_state")
    equal = local == peer
    if equal and assessment.conflict:
        raise PersistentNodeError("agreement_assessment_invalid")
    if not equal and not assessment.conflict:
        raise PersistentNodeError("state_length_or_prefix_mismatch")
    return {
        "equal": equal,
        "conflict": bool(assessment.conflict),
        "assessment_code": assessment.code,
        "policy_status": policy_state.status,
        "policy_code": policy_state.code,
        "halt_height": policy_state.halt_height,
        "canonical_state_changed": policy_state.canonical_state_changed,
        "ledger_mutated": policy_state.ledger_mutated,
    }


def encode_frame(
    message_type: str,
    sequence: int,
    payload: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> bytes:
    if (
        message_type not in MESSAGE_TYPES
        or not _exact_int(sequence)
        or sequence not in (1, 2)
    ):
        raise PersistentNodeError("frame_sequence_invalid")
    if not isinstance(payload, Mapping):
        raise PersistentNodeError("frame_payload_invalid")
    frame = {
        "profile": PROFILE,
        "version": TRANSPORT_VERSION,
        "network_id": binding["network_id"],
        "genesis_hash": binding["genesis_hash"],
        "config_hash": binding["config_hash"],
        "message_type": message_type,
        "sequence": sequence,
        "payload": dict(payload),
    }
    body = _canonical_bytes(frame)
    if not body or len(body) > MAX_FRAME_BYTES:
        raise PersistentNodeError("frame_size_invalid")
    return struct.pack(">I", len(body)) + body


def decode_frame(
    body: bytes,
    *,
    expected_sequence: int,
    expected_message_type: str,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(body, bytes) or not body or len(body) > MAX_FRAME_BYTES:
        raise PersistentNodeError("frame_size_invalid")
    try:
        frame = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except PersistentNodeError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PersistentNodeError("frame_malformed") from exc
    _exact_mapping(frame, set(FRAME_FIELDS), "frame_schema_invalid")
    if body != _canonical_bytes(frame):
        raise PersistentNodeError("frame_noncanonical")
    if (
        frame["profile"] != PROFILE
        or not _exact_int(frame["version"])
        or frame["version"] != TRANSPORT_VERSION
    ):
        raise PersistentNodeError("frame_profile_invalid")
    if frame["network_id"] != binding["network_id"]:
        raise PersistentNodeError("frame_network_invalid")
    if (
        frame["genesis_hash"] != binding["genesis_hash"]
        or frame["config_hash"] != binding["config_hash"]
    ):
        raise PersistentNodeError("frame_binding_invalid")
    if (
        not _exact_int(frame["sequence"])
        or frame["sequence"] != expected_sequence
        or frame["message_type"] != expected_message_type
    ):
        raise PersistentNodeError("frame_sequence_invalid")
    if not isinstance(frame["payload"], dict):
        raise PersistentNodeError("frame_payload_invalid")
    return frame


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        try:
            chunk = sock.recv(size - len(chunks))
        except socket.timeout as exc:
            raise PersistentNodeError("socket_timeout") from exc
        if not chunk:
            raise PersistentNodeError("frame_truncated")
        chunks.extend(chunk)
    return bytes(chunks)


def read_frame(
    sock: socket.socket,
    *,
    expected_sequence: int,
    expected_message_type: str,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    length = struct.unpack(">I", _read_exact(sock, 4))[0]
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise PersistentNodeError("frame_size_invalid")
    return decode_frame(
        _read_exact(sock, length),
        expected_sequence=expected_sequence,
        expected_message_type=expected_message_type,
        binding=binding,
    )


def write_frame(
    sock: socket.socket,
    message_type: str,
    sequence: int,
    payload: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> None:
    try:
        sock.sendall(encode_frame(message_type, sequence, payload, binding))
    except OSError as exc:
        raise PersistentNodeError("socket_write_failed") from exc


def _close_socket(sock: socket.socket | None) -> None:
    if sock is None:
        return
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


def _emit(payload: Mapping[str, Any]) -> None:
    sys.stdout.write(_canonical_bytes(payload).decode("utf-8") + "\n")
    sys.stdout.flush()


def _open_listener() -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((HOST, 0))
        if listener.getsockname()[0] != HOST:
            raise PersistentNodeError("non_loopback_listener")
        listener.listen(1)
        listener.settimeout(SOCKET_TIMEOUT_SECONDS)
        return listener
    except Exception:
        listener.close()
        raise


def _connect(port: int) -> socket.socket:
    if not _exact_int(port) or not 1 <= port <= 65_535:
        raise PersistentNodeError("port_invalid")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SOCKET_TIMEOUT_SECONDS)
    try:
        sock.connect((HOST, port))
        if sock.getpeername()[0] != HOST or sock.getsockname()[0] != HOST:
            raise PersistentNodeError("non_loopback_peer")
        return sock
    except Exception:
        sock.close()
        raise


def follower_main(data_dir: Path, phase: str) -> int:
    listener = None
    connection = None
    try:
        binding = persistent_testnet_binding()
        ledger = (
            _new_ledger(data_dir)
            if phase == "initial"
            else asyncio.run(_load_ledger(data_dir))
        )
        listener = _open_listener()
        _emit(
            {
                "coordination": "follower_ready",
                "host": HOST,
                "phase": phase,
                "pid": os.getpid(),
                "port": listener.getsockname()[1],
            }
        )
        connection, address = listener.accept()
        connection.settimeout(SOCKET_TIMEOUT_SECONDS)
        if address[0] != HOST:
            raise PersistentNodeError("non_loopback_peer")

        if phase == "initial":
            frame = read_frame(
                connection,
                expected_sequence=1,
                expected_message_type="initial_events",
                binding=binding,
            )
            payload = _exact_mapping(
                frame["payload"], {"events"}, "initial_payload_invalid"
            )
            events = payload["events"]
            if not isinstance(events, list) or len(events) != 2:
                raise PersistentNodeError("initial_event_count_invalid")
            validated = asyncio.run(_apply_events(ledger, events))
            state = ledger_state(ledger)
            write_frame(
                connection,
                "initial_state",
                2,
                {"state": state},
                binding,
            )
            evidence = {
                "phase": phase,
                "pid": os.getpid(),
                "validated_event_ids": validated,
                "state": state,
                "replay_rejected": False,
            }
        elif phase == "restart":
            frame = read_frame(
                connection,
                expected_sequence=1,
                expected_message_type="restart_probe",
                binding=binding,
            )
            payload = _exact_mapping(
                frame["payload"],
                {"replay_event", "state"},
                "restart_payload_invalid",
            )
            local_before = ledger_state(ledger)
            agreement = assess_state_agreement(
                local_before, payload["state"], binding
            )
            if not agreement["equal"]:
                raise PersistentNodeError("restart_divergence_halted")
            replay_event = payload["replay_event"]
            replay_ok, _replay_id, replay_reason = classify_event(
                ledger, replay_event
            )
            if replay_ok or replay_reason != "replay":
                raise PersistentNodeError("restart_replay_not_rejected")
            if asyncio.run(ledger.add_transaction(replay_event)):
                raise PersistentNodeError("restart_replay_applied")
            state = ledger_state(ledger)
            if state != local_before:
                raise PersistentNodeError("restart_replay_mutated_state")
            write_frame(
                connection,
                "restart_state",
                2,
                {"replay_reason": replay_reason, "state": state},
                binding,
            )
            evidence = {
                "phase": phase,
                "pid": os.getpid(),
                "validated_event_ids": state["transaction_ids"],
                "state": state,
                "replay_rejected": True,
            }
        else:
            raise PersistentNodeError("phase_invalid")
        _emit({"coordination": "follower_evidence", **evidence})
        return 0
    except (PersistentNodeError, OSError, ValueError) as exc:
        sys.stderr.write(getattr(exc, "code", "follower_failed") + "\n")
        return 1
    finally:
        _close_socket(connection)
        _close_socket(listener)


def writer_main(data_dir: Path, phase: str, port: int) -> int:
    sock = None
    try:
        binding = persistent_testnet_binding()
        if phase == "initial":
            ledger = _new_ledger(data_dir)
            private_key = Ed25519PrivateKey.generate()
            writer_identity = public_identity(_public_key_hex(private_key))
            events = [
                _build_coinbase(writer_identity),
                _build_signed_transfer(private_key, follower_identity(binding)),
            ]
            del private_key
            validated = asyncio.run(_apply_events(ledger, events))
            local_state = ledger_state(ledger)
            sock = _connect(port)
            write_frame(
                sock,
                "initial_events",
                1,
                {"events": events},
                binding,
            )
            frame = read_frame(
                sock,
                expected_sequence=2,
                expected_message_type="initial_state",
                binding=binding,
            )
            payload = _exact_mapping(
                frame["payload"], {"state"}, "initial_state_invalid"
            )
            agreement = assess_state_agreement(
                local_state, payload["state"], binding
            )
            if not agreement["equal"]:
                raise PersistentNodeError("initial_divergence_halted")
            evidence = {
                "phase": phase,
                "pid": os.getpid(),
                "validated_event_ids": validated,
                "state": local_state,
                "agreement": agreement,
                "replay_rejected": False,
            }
        elif phase == "restart":
            ledger = asyncio.run(_load_ledger(data_dir))
            local_state = ledger_state(ledger)
            replay_event = ledger.transactions[local_state["transaction_ids"][-1]]
            replay_ok, _replay_id, replay_reason = classify_event(
                ledger, replay_event
            )
            if replay_ok or replay_reason != "replay":
                raise PersistentNodeError("restart_replay_not_rejected")
            sock = _connect(port)
            write_frame(
                sock,
                "restart_probe",
                1,
                {"replay_event": replay_event, "state": local_state},
                binding,
            )
            frame = read_frame(
                sock,
                expected_sequence=2,
                expected_message_type="restart_state",
                binding=binding,
            )
            payload = _exact_mapping(
                frame["payload"],
                {"replay_reason", "state"},
                "restart_state_invalid",
            )
            if payload["replay_reason"] != "replay":
                raise PersistentNodeError("peer_replay_not_rejected")
            agreement = assess_state_agreement(
                local_state, payload["state"], binding
            )
            if not agreement["equal"]:
                raise PersistentNodeError("restart_divergence_halted")
            evidence = {
                "phase": phase,
                "pid": os.getpid(),
                "validated_event_ids": local_state["transaction_ids"],
                "state": local_state,
                "agreement": agreement,
                "replay_rejected": True,
            }
        else:
            raise PersistentNodeError("phase_invalid")
        _emit({"coordination": "writer_evidence", **evidence})
        return 0
    except (PersistentNodeError, OSError, ValueError) as exc:
        sys.stderr.write(getattr(exc, "code", "writer_failed") + "\n")
        return 1
    finally:
        _close_socket(sock)


def _child_argv(
    role: str,
    phase: str,
    data_dir: Path,
    port: int | None = None,
) -> list[str]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "coin.persistent_disposable_testnet_node",
        "--role",
        role,
        "--phase",
        phase,
        "--data-dir",
        str(data_dir),
    ]
    if port is not None:
        command.extend(["--port", str(port)])
    return command


def _read_json_line(stream: Any, deadline: float) -> dict[str, Any]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise PersistentNodeError("parent_deadline")
    ready, _unused, _errors = select.select([stream], [], [], remaining)
    if not ready:
        raise PersistentNodeError("parent_deadline")
    line = stream.readline()
    if not line:
        raise PersistentNodeError("child_premature_eof")
    try:
        payload = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, PersistentNodeError) as exc:
        raise PersistentNodeError("child_output_invalid") from exc
    if not isinstance(payload, dict):
        raise PersistentNodeError("child_output_invalid")
    return payload


def _terminate(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    if process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _execute_phase(
    phase: str,
    writer_dir: Path,
    follower_dir: Path,
    deadline: float,
) -> dict[str, Any]:
    follower = subprocess.Popen(
        _child_argv("follower", phase, follower_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    writer: subprocess.Popen[str] | None = None
    try:
        if follower.stdout is None:
            raise PersistentNodeError("follower_coordination_failed")
        ready = _read_json_line(follower.stdout, deadline)
        if (
            ready.get("coordination") != "follower_ready"
            or ready.get("host") != HOST
            or ready.get("phase") != phase
            or not _exact_int(ready.get("port"))
        ):
            raise PersistentNodeError("follower_coordination_failed")
        writer = subprocess.Popen(
            _child_argv("writer", phase, writer_dir, ready["port"]),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        writer_out, writer_err = writer.communicate(
            timeout=max(0.1, deadline - time.monotonic())
        )
        follower_out, follower_err = follower.communicate(
            timeout=max(0.1, deadline - time.monotonic())
        )
        if writer.returncode != 0 or follower.returncode != 0:
            code = (writer_err.strip() or follower_err.strip() or "child_failed").splitlines()[0]
            raise PersistentNodeError(code)
        try:
            writer_evidence = json.loads(
                writer_out, object_pairs_hook=_reject_duplicate_keys
            )
            follower_evidence = json.loads(
                follower_out, object_pairs_hook=_reject_duplicate_keys
            )
        except (json.JSONDecodeError, PersistentNodeError) as exc:
            raise PersistentNodeError("child_output_invalid") from exc
        if (
            writer_evidence.get("coordination") != "writer_evidence"
            or follower_evidence.get("coordination") != "follower_evidence"
            or writer_evidence.get("phase") != phase
            or follower_evidence.get("phase") != phase
            or writer_evidence.get("pid") == follower_evidence.get("pid")
            or writer_evidence.get("state") != follower_evidence.get("state")
            or writer_evidence.get("validated_event_ids")
            != follower_evidence.get("validated_event_ids")
        ):
            raise PersistentNodeError("phase_agreement_invalid")
        return {
            "phase": phase,
            "writer_pid": writer_evidence["pid"],
            "follower_pid": follower_evidence["pid"],
            "validated_event_ids": writer_evidence["validated_event_ids"],
            "state": writer_evidence["state"],
            "replay_rejected": (
                writer_evidence["replay_rejected"] is True
                and follower_evidence["replay_rejected"] is True
            ),
        }
    except subprocess.TimeoutExpired as exc:
        raise PersistentNodeError("parent_deadline") from exc
    finally:
        _terminate(writer)
        _terminate(follower)


def _expect_error(code: str, action: Any) -> bool:
    try:
        action()
    except PersistentNodeError as exc:
        return exc.code == code
    return False


def _adversarial_probes(
    root: Path,
    state: dict[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, bool]:
    frame = {
        "profile": PROFILE,
        "version": TRANSPORT_VERSION,
        "network_id": "L28-DISPOSABLE-WRONG001",
        "genesis_hash": binding["genesis_hash"],
        "config_hash": binding["config_hash"],
        "message_type": "restart_probe",
        "sequence": 1,
        "payload": {"replay_event": {}, "state": state},
    }
    cross_network_rejected = _expect_error(
        "frame_network_invalid",
        lambda: decode_frame(
            _canonical_bytes(frame),
            expected_sequence=1,
            expected_message_type="restart_probe",
            binding=binding,
        ),
    )
    malformed_rejected = _expect_error(
        "frame_malformed",
        lambda: decode_frame(
            b"{",
            expected_sequence=1,
            expected_message_type="restart_probe",
            binding=binding,
        ),
    )

    divergent = deepcopy(state)
    balance_key = sorted(divergent["balances"])[0]
    divergent["balances"][balance_key] += 1
    material = {
        key: divergent[key]
        for key in STATE_FIELDS
        if key != "state_commitment"
    }
    divergent["state_commitment"] = _state_commitment(material)
    local_before = deepcopy(state)
    divergence = assess_state_agreement(state, divergent, binding)
    conflicting_state_halted = (
        divergence["conflict"] is True
        and divergence["policy_status"] == "HALTED_CONFLICT"
        and divergence["policy_code"] == "HALTED_BY_OPTION_A"
        and divergence["canonical_state_changed"] is False
        and divergence["ledger_mutated"] is False
        and state == local_before
    )

    corrupt_dir = root / "corrupt-probe"
    shutil.copytree(root / "follower", corrupt_dir)
    shard_files = sorted(corrupt_dir.glob("shard_*.jsonl"))
    if not shard_files:
        raise PersistentNodeError("corruption_probe_missing_state")
    target = next((path for path in shard_files if path.stat().st_size), None)
    if target is None:
        raise PersistentNodeError("corruption_probe_missing_state")
    raw = target.read_bytes()
    target.write_bytes(raw[:-1])
    try:
        asyncio.run(_load_ledger(corrupt_dir))
    except (PersistentNodeError, ValueError, json.JSONDecodeError):
        corruption_rejected = True
    else:
        corruption_rejected = False

    return {
        "cross_network_rejected": cross_network_rejected,
        "malformed_rejected": malformed_rejected,
        "conflicting_state_halted": conflicting_state_halted,
        "corruption_rejected": corruption_rejected,
    }


def execute_persistent_two_node_workflow(root: Path) -> dict[str, Any]:
    assert_production_authority_inactive()
    binding = persistent_testnet_binding()
    root = Path(root)
    if root.exists() and (root.is_symlink() or any(root.iterdir())):
        raise PersistentNodeError("work_directory_not_empty")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    writer_dir = root / "writer"
    follower_dir = root / "follower"
    writer_dir.mkdir(mode=0o700)
    follower_dir.mkdir(mode=0o700)

    deadline = time.monotonic() + PARENT_DEADLINE_SECONDS
    initial = _execute_phase("initial", writer_dir, follower_dir, deadline)
    restart = _execute_phase("restart", writer_dir, follower_dir, deadline)
    if (
        initial["state"] != restart["state"]
        or initial["validated_event_ids"] != restart["validated_event_ids"]
        or restart["replay_rejected"] is not True
        or len(
            {
                initial["writer_pid"],
                initial["follower_pid"],
                restart["writer_pid"],
                restart["follower_pid"],
            }
        )
        != 4
    ):
        raise PersistentNodeError("restart_recovery_invalid")
    state = restart["state"]
    probes = _adversarial_probes(root, state, binding)
    if not all(probes.values()):
        raise PersistentNodeError("adversarial_probe_failed")
    assert_production_authority_inactive()
    return {
        "profile": PROFILE,
        "protocol_version": PROTOCOL_VERSION,
        "network_scope": NETWORK_SCOPE,
        "network_id": NETWORK_ID,
        "genesis_hash": binding["genesis_hash"],
        "config_hash": binding["config_hash"],
        "transport": "IPv4_LOOPBACK_ONLY",
        "node_processes_per_phase": 2,
        "initial_processes_terminal": True,
        "restart_processes_terminal": True,
        "processes_restarted": True,
        "independent_validation": True,
        "validated_event_ids": state["transaction_ids"],
        "state_commitment": state["state_commitment"],
        "balances": state["balances"],
        "issued_supply": state["issued_supply"],
        "mint_height": state["mint_height"],
        "total_transactions": state["total_transactions"],
        "durable_restart_agreement": True,
        "replay_rejected_after_restart": True,
        "corruption_rejected": probes["corruption_rejected"],
        "malformed_input_rejected": probes["malformed_rejected"],
        "cross_network_input_rejected": probes["cross_network_rejected"],
        "divergence_halted_by_option_a": probes["conflicting_state_halted"],
        "canonical_history_touched": False,
        "historical_state_imported": False,
        "production_keys_used": False,
        "private_test_material_persisted": False,
        "mining_used": False,
        "public_network_used": False,
        "broadcast_used": False,
        "production_settlement": False,
        "custody_gate_changed": False,
        "f171_changed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.persistent_disposable_testnet_node"
    )
    parser.add_argument(
        "--role", choices=("parent", "writer", "follower"), default="parent"
    )
    parser.add_argument("--phase", choices=("initial", "restart"))
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--port", type=int)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.role == "follower":
            if args.phase is None or args.data_dir is None:
                raise PersistentNodeError("child_arguments_invalid")
            return follower_main(args.data_dir, args.phase)
        if args.role == "writer":
            if (
                args.phase is None
                or args.data_dir is None
                or args.port is None
            ):
                raise PersistentNodeError("child_arguments_invalid")
            return writer_main(args.data_dir, args.phase, args.port)
        if args.phase is not None or args.data_dir is not None or args.port is not None:
            raise PersistentNodeError("parent_arguments_invalid")
        with tempfile.TemporaryDirectory(
            prefix="l28-disposable-testnet-persistent001-"
        ) as directory:
            result = execute_persistent_two_node_workflow(Path(directory))
    except PersistentNodeError as exc:
        sys.stderr.write(exc.code + "\n")
        return 1
    _emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
