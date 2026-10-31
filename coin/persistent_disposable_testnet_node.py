# SPDX-License-Identifier: Apache-2.0
"""Persistent disposable L28 core: loopback or explicitly bounded private LAN.

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
import hmac
import json
import os
import select
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import platform
import queue
from ipaddress import IPv4Address, IPv4Network
from datetime import datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
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

# This opt-in transport does not modify the production authority constants or
# the existing disposable transaction/network identities.
LAN_PROFILE = "l28-two-host-disposable-sync/v0.1"
PEER_PROFILE = "l28-two-network-disposable-peer/v0.1"
LAN_WRITER_IP = "192.168.68.50"
LAN_FOLLOWER_IP = "192.168.68.54"
LAN_PORT = 42828
LAN_SESSION_SECONDS = 600
LAN_DOMAIN = b"L28-TWO-HOST-DISPOSABLE-HMAC-V0.1\x00"
HANDOFF_PROFILE = "l28-disposable-pinned-tls-handoff/v0.1"
HANDOFF_ALPN = b"l28-disposable-auth-v1"
ENROLLMENT_PROFILE = "l28-public-pin-enrollment/v0.1"
PREPARED_ENROLLMENT_PROFILE = "l28-prepared-public-enrollment/v0.1"
PAIR_PROFILE = "l28-physical-public-pairing/v0.1"
PAIR_DOMAIN = b"L28-PHYSICAL-PUBLIC-PAIRING-V0.1\x00"
LAN_SOURCE_PATHS = (
    "coin/__init__.py", "coin/l28_coin.py", "coin/transaction_builder.py",
    "coin/persistent_disposable_testnet_node.py", "coin/ledger.py",
    "coin/tx_validation.py", "coin/mining.py", "coin/disposable_testnet_identity.py",
    "coin/disposable_testnet_option_a_policy.py", "requirements-m2m.txt",
)

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


def lan_source_inventory() -> dict[str, Any]:
    """Public runtime closure; identical on a Git checkout and a Windows ZIP."""
    root = Path(__file__).resolve().parents[1]
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
              for name in LAN_SOURCE_PATHS}
    return {"files": hashes, "source_digest": hashlib.sha256(_canonical_bytes(hashes)).hexdigest(),
            "python": platform.python_version(), "cryptography": version("cryptography")}


def _lan_hex(value: Any, size: int) -> bool:
    return (isinstance(value, str) and len(value) == size
            and all(c in "0123456789abcdef" for c in value))


def peer_endpoints(writer: Any, follower: Any, port: Any) -> dict[str, Any]:
    """Explicit private-route configuration, never evidence that a route exists.

    RFC1918 and shared address space only; no DNS, inference, public or local
    loopback listeners. Encryption/ownership and physical topology need separate
    operator verification. These are transport bindings, not consensus authority.
    """
    ranges = tuple(IPv4Network(value) for value in (
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10"))
    try:
        if type(writer) is not str or type(follower) is not str:
            raise ValueError
        addresses = [IPv4Address(value) for value in (writer, follower)]
        if (writer == follower or not _exact_int(port) or not 1024 <= port <= 65535
                or any(str(address) != value or not any(address in net for net in ranges)
                       for address, value in zip(addresses, (writer, follower)))):
            raise ValueError
    except (ValueError, TypeError):
        raise PersistentNodeError("peer_endpoints_invalid") from None
    return {"profile": PEER_PROFILE, "writer": writer, "follower": follower, "port": port}


def _peer_config(endpoints: Any = None) -> dict[str, Any]:
    if endpoints is None:
        return {"profile": LAN_PROFILE, "writer": LAN_WRITER_IP,
                "follower": LAN_FOLLOWER_IP, "port": LAN_PORT}
    _exact_mapping(endpoints, {"profile", "writer", "follower", "port"}, "peer_endpoints_invalid")
    if endpoints["profile"] != PEER_PROFILE:
        raise PersistentNodeError("peer_endpoints_invalid")
    return peer_endpoints(endpoints["writer"], endpoints["follower"], endpoints["port"])


def _configured_peers(args: Any) -> dict[str, Any] | None:
    values = [getattr(args, name, None) for name in ("peer_writer_ip", "peer_follower_ip", "peer_port")]
    acknowledged = getattr(args, "ack_encrypted_private_route", False)
    if not any(value is not None for value in values) and not acknowledged:
        return None
    if not acknowledged or any(value is None for value in values):
        raise PersistentNodeError("peer_configuration_and_route_ack_required")
    return peer_endpoints(*values)


def lan_context(session_id: str, started: int, phase: str, source_digest: str,
                *, now: float | None = None, endpoints: Any = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    if (not _lan_hex(session_id, 32) or not _exact_int(started)
            or not started <= now < started + LAN_SESSION_SECONDS
            or phase not in ("initial", "restart") or not _lan_hex(source_digest, 64)):
        raise PersistentNodeError("lan_session_invalid_or_expired")
    binding = persistent_testnet_binding()
    peers = _peer_config(endpoints)
    return {"profile": peers["profile"], "version": 1, "session": session_id,
            "started": started, "phase": phase, "source_digest": source_digest,
            "writer": peers["writer"], "follower": peers["follower"], "port": peers["port"],
            "network": NETWORK_ID, "genesis": binding["genesis_hash"],
            "config": binding["config_hash"]}


def _lan_mac(key: bytes, label: str, value: Any) -> str:
    return hmac.new(key, LAN_DOMAIN + label.encode("ascii") + b"\x00"
                    + _canonical_bytes(value), hashlib.sha256).hexdigest()


class LanChannel:
    """Bounded, strict JSON HMAC frames. No encryption or production authority."""

    def __init__(self, sock: socket.socket, key: bytes, context: dict[str, Any],
                 role: str, deadline: float):
        if role not in ("writer", "follower") or type(key) is not bytes or len(key) != 32:
            raise PersistentNodeError("lan_auth_material_invalid")
        self.sock, self.key, self.context = sock, key, context
        self.role = role
        self.peer = "follower" if role == "writer" else "writer"
        self.deadline = deadline
        self.sent = self.received = 0

    def _timeout(self) -> None:
        remaining = min(self.deadline - time.monotonic(),
                        self.context["started"] + LAN_SESSION_SECONDS - time.time())
        if remaining <= 0:
            raise PersistentNodeError("lan_deadline_expired")
        self.sock.settimeout(min(SOCKET_TIMEOUT_SECONDS, remaining))

    def _read(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            self._timeout()
            chunk = self.sock.recv(size - len(chunks))
            if not chunk:
                raise PersistentNodeError("lan_interrupted")
            chunks.extend(chunk)
        return bytes(chunks)

    def encode(self, kind: str, payload: Any) -> bytes:
        body = {"context": self.context, "role": self.role, "sequence": self.sent + 1,
                "type": kind, "payload": payload}
        raw = _canonical_bytes({"body": body, "mac": _lan_mac(self.key, "frame", body)})
        if not 0 < len(raw) <= MAX_FRAME_BYTES:
            raise PersistentNodeError("lan_frame_size_invalid")
        self.sent += 1
        return struct.pack(">I", len(raw)) + raw

    def decode(self, raw: bytes, kind: str) -> Any:
        if not 0 < len(raw) <= MAX_FRAME_BYTES:
            raise PersistentNodeError("lan_frame_size_invalid")
        try:
            packet = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
            _exact_mapping(packet, {"body", "mac"}, "lan_frame_schema_invalid")
            body = _exact_mapping(packet["body"],
                                  {"context", "role", "sequence", "type", "payload"},
                                  "lan_frame_schema_invalid")
            if _canonical_bytes(packet) != raw:
                raise PersistentNodeError("lan_frame_noncanonical")
        except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
            raise PersistentNodeError("lan_frame_malformed") from exc
        if (_canonical_bytes(body["context"]) != _canonical_bytes(self.context) or body["role"] != self.peer
                or type(body["sequence"]) is not int
                or body["sequence"] != self.received + 1 or body["type"] != kind
                or not _lan_hex(packet["mac"], 64)
                or not hmac.compare_digest(packet["mac"], _lan_mac(self.key, "frame", body))):
            raise PersistentNodeError("lan_frame_auth_or_binding_invalid")
        self.received += 1
        return body["payload"]

    def send(self, kind: str, payload: Any) -> None:
        self._timeout()
        self.sock.sendall(self.encode(kind, payload))

    def receive(self, kind: str) -> Any:
        size = struct.unpack(">I", self._read(4))[0]
        if not 0 < size <= MAX_FRAME_BYTES:
            raise PersistentNodeError("lan_frame_size_invalid")
        return self.decode(self._read(size), kind)

    def authenticate(self) -> None:
        # All handshake messages are authenticated, directional and context-bound.
        # Fresh challenges prevent a captured old session replay after a restart.
        if self.role == "writer":
            writer = secrets.token_hex(32)
            self.send("hello", {"writer": writer})
            challenges = self.receive("challenge")
            _exact_mapping(challenges, {"writer", "follower"}, "lan_challenge_invalid")
            if challenges["writer"] != writer or not _lan_hex(challenges["follower"], 64):
                raise PersistentNodeError("lan_challenge_invalid")
            self.send("proof", challenges)
            if self.receive("ready") != challenges:
                raise PersistentNodeError("lan_challenge_invalid")
        else:
            hello = self.receive("hello")
            _exact_mapping(hello, {"writer"}, "lan_challenge_invalid")
            if not _lan_hex(hello["writer"], 64):
                raise PersistentNodeError("lan_challenge_invalid")
            challenges = {"writer": hello["writer"], "follower": secrets.token_hex(32)}
            self.send("challenge", challenges)
            if self.receive("proof") != challenges:
                raise PersistentNodeError("lan_challenge_invalid")
            self.send("ready", challenges)
        self.key = bytes.fromhex(_lan_mac(self.key, "session-key", {
            "context": self.context, "challenges": challenges}))
        self.sent = self.received = 0


def _tls_backend() -> Any:
    try:
        if version("pyOpenSSL") != "26.4.0" or version("cryptography") != "49.0.0":
            raise PersistentNodeError("tls_dependency_version_invalid")
        from OpenSSL import SSL
        return SSL
    except (ImportError, PackageNotFoundError):
        raise PersistentNodeError("tls_dependency_unavailable") from None


def _handoff_context(context: Any) -> dict[str, Any]:
    if not isinstance(context, dict):
        raise PersistentNodeError("tls_context_invalid")
    endpoints = None
    if context.get("profile") == PEER_PROFILE:
        endpoints = peer_endpoints(context.get("writer"), context.get("follower"), context.get("port"))
    expected = lan_context(context.get("session"), context.get("started"),
                           context.get("phase"), context.get("source_digest"), endpoints=endpoints)
    if _canonical_bytes(context) != _canonical_bytes(expected):
        raise PersistentNodeError("tls_context_invalid")
    if expected["source_digest"] != lan_source_inventory()["source_digest"]:
        raise PersistentNodeError("tls_source_digest_invalid")
    return deepcopy(expected)


class HandoffMaterial:
    """Single-use, process-local input. Repr never includes authentication data."""
    __slots__ = ("_material", "_role", "_context", "closed")

    def __init__(self, material: bytearray, role: str, context: dict[str, Any]):
        if type(material) is not bytearray or len(material) != 32:
            raise PersistentNodeError("tls_material_invalid")
        self._material = bytearray(material)
        self._role, self._context, self.closed = role, deepcopy(context), False

    def __repr__(self) -> str:
        return "<HandoffMaterial redacted>"

    def consume(self, role: str, context: dict[str, Any]) -> bytes:
        try:
            expected = _handoff_context(context)
            if (self.closed or role != self._role
                    or _canonical_bytes(expected) != _canonical_bytes(self._context)):
                raise PersistentNodeError("tls_material_binding_invalid")
            return bytes(self._material)
        finally:
            self.close()

    def close(self) -> None:
        for i in range(len(self._material)):
            self._material[i] = 0
        self._material.clear()
        self.closed = True


class MemoryTLSIdentity:
    """Disposable TLS identity; no application key serialization or file writes."""
    __slots__ = ("role", "certificate", "_key", "pin", "closed", "endpoints")

    def __init__(self, role: str, *, endpoints: Any = None):
        if role not in ("writer", "follower"):
            raise PersistentNodeError("tls_role_invalid")
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import NameOID
        from ipaddress import ip_address
        self.endpoints = _peer_config(endpoints)
        self.role, self.closed = role, False
        self._key = self.certificate = None
        try:
            self._key = ec.generate_private_key(ec.SECP256R1())
            name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "l28-disposable-" + role)])
            now = datetime.now(timezone.utc)
            address = self.endpoints[role]
            self.certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                                .public_key(self._key.public_key()).serial_number(x509.random_serial_number())
                                .not_valid_before(now - timedelta(seconds=30))
                                .not_valid_after(now + timedelta(seconds=LAN_SESSION_SECONDS))
                                .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ip_address(address))]), False)
                                .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
                                .sign(self._key, hashes.SHA256()))
            self.pin = self.certificate.fingerprint(hashes.SHA256()).hex()
        except Exception:
            self.close()
            raise PersistentNodeError("tls_identity_creation_failed") from None
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        self._key = self.certificate = None
        self.closed = True


class PinnedTLSHandoff:
    """TLS 1.3 memory-BIO endpoint; transport only drain()/feed() ciphertext.

    Peer pins are independently trusted PUBLIC inputs, never learned on-connect.
    Socket integration must additionally enforce physical addresses. Application
    authorization remains the existing mutual HMAC authentication.
    """
    def __init__(self, identity: MemoryTLSIdentity, peer_pin: str,
                 context: dict[str, Any], peer_ip: str):
        self.closed = False
        self._connection = self._tls_context = None
        self._secret, self._incoming = bytearray(), bytearray()
        self._received = self._sent = self._wire_in = self._wire_out = 0
        self._nonce = self._writer_nonce = ""
        self._state = "handshake"
        self.identity = identity
        self.role = identity.role
        self.peer = "follower" if self.role == "writer" else "writer"
        self.peer_pin, self.peer_ip = peer_pin, peer_ip
        self.context = {}
        self._deadline = time.monotonic() + PARENT_DEADLINE_SECONDS
        try:
            self.context = _handoff_context(context)
            if (identity.closed or not _lan_hex(peer_pin, 64)
                    or any(self.context[k] != identity.endpoints[k] for k in identity.endpoints)
                    or peer_ip != identity.endpoints[self.peer]):
                raise PersistentNodeError("tls_peer_binding_invalid")
            self._ssl = _tls_backend()
            ctx = self._ssl.Context(self._ssl.TLS_METHOD)
            self._tls_context = ctx
            ctx.set_min_proto_version(self._ssl.TLS1_3_VERSION)
            ctx.set_max_proto_version(self._ssl.TLS1_3_VERSION)
            ctx.set_session_cache_mode(self._ssl.SESS_CACHE_OFF)
            ctx.set_options(self._ssl.OP_NO_TICKET | self._ssl.OP_NO_COMPRESSION)
            ctx.use_certificate(identity.certificate)
            ctx.use_privatekey(identity._key)
            ctx.check_privatekey()
            ctx.set_verify(self._ssl.VERIFY_PEER | self._ssl.VERIFY_FAIL_IF_NO_PEER_CERT,
                           self._verify_certificate)
            if self.role == "writer":
                ctx.set_alpn_protos([HANDOFF_ALPN])
            else:
                ctx.set_alpn_select_callback(lambda conn, offered: HANDOFF_ALPN
                                             if HANDOFF_ALPN in offered else self._ssl.NO_OVERLAPPING_PROTOCOLS)
            self._connection = self._ssl.Connection(ctx, None)
            if self.role == "writer":
                self._connection.set_connect_state()
            else:
                self._connection.set_accept_state()
        except PersistentNodeError:
            self.close()
            raise
        except Exception:
            self.close()
            raise PersistentNodeError("tls_initialization_failed") from None
        except BaseException:
            self.close()
            raise

    def __repr__(self) -> str:
        return "<PinnedTLSHandoff authentication redacted>"

    @property
    def complete(self) -> bool:
        return self._state in ("done", "consumed") and not self.closed

    def _verify_certificate(self, conn: Any, cert: Any, error: int, depth: int, valid: int) -> bool:
        # Exact pin is the trust anchor for this disposable self-signed leaf.
        # TLS CertificateVerify proves possession of its corresponding private key.
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes
            from cryptography.x509.oid import NameOID
            from ipaddress import ip_address
            leaf = cert.to_cryptography()
            now = datetime.now(timezone.utc)
            names = leaf.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            ips = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            return (depth == 0 and hmac.compare_digest(leaf.fingerprint(hashes.SHA256()).hex(), self.peer_pin)
                    and len(names) == 1 and names[0].value == "l28-disposable-" + self.peer
                    and ips.get_values_for_type(x509.IPAddress) == [ip_address(self.peer_ip)]
                    and leaf.not_valid_before_utc <= now < leaf.not_valid_after_utc)
        except Exception:
            return False

    def _check(self) -> None:
        if self.closed:
            raise PersistentNodeError("tls_endpoint_closed")
        try:
            if time.monotonic() >= self._deadline:
                raise PersistentNodeError("tls_handoff_deadline")
            _handoff_context(self.context)
        except PersistentNodeError:
            self.close()
            raise

    def _proof(self, label: str) -> str:
        if len(self._secret) != 32:
            raise PersistentNodeError("tls_material_invalid")
        body = {"context": self.context, "nonce": self._nonce, "writer_nonce": self._writer_nonce}
        return _lan_mac(bytes(self._secret), "tls-handoff-" + label, body)

    def _send(self, kind: str, payload: dict[str, Any]) -> None:
        self._sent += 1
        body = {"profile": HANDOFF_PROFILE, "context": self.context, "role": self.role,
                "sequence": self._sent, "type": kind, "payload": payload}
        raw = _canonical_bytes(body)
        if len(raw) > MAX_FRAME_BYTES:
            raise PersistentNodeError("tls_frame_size_invalid")
        framed = struct.pack(">I", len(raw)) + raw
        if self._connection.send(framed) != len(framed):
            raise PersistentNodeError("tls_delivery_incomplete")

    def _accept(self, raw: bytes) -> None:
        try:
            body = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
            _exact_mapping(body, {"profile", "context", "role", "sequence", "type", "payload"}, "tls_frame_invalid")
            if (raw != _canonical_bytes(body) or body["profile"] != HANDOFF_PROFILE
                    or _canonical_bytes(body["context"]) != _canonical_bytes(self.context)
                    or body["role"] != self.peer or type(body["sequence"]) is not int
                    or body["sequence"] != self._received + 1):
                raise PersistentNodeError("tls_frame_binding_invalid")
            expected = {"wait_ready": "ready", "wait_deliver": "deliver", "wait_ack": "ack",
                        "wait_commit": "commit", "wait_complete": "complete"}.get(self._state)
            if expected is None or body["type"] != expected:
                raise PersistentNodeError("tls_frame_order_invalid")
            self._received += 1
            payload = body["payload"]
            if expected == "ready":
                _exact_mapping(payload, {"nonce"}, "tls_frame_invalid")
                if not _lan_hex(payload["nonce"], 64):
                    raise PersistentNodeError("tls_nonce_invalid")
                self._nonce, self._writer_nonce = payload["nonce"], secrets.token_hex(32)
                self._secret = bytearray(secrets.token_bytes(32))
                self._send("deliver", {"nonce": self._nonce, "writer_nonce": self._writer_nonce,
                                       "secret": self._secret.hex()})
                self._state = "wait_ack"
            elif expected == "deliver":
                _exact_mapping(payload, {"nonce", "writer_nonce", "secret"}, "tls_frame_invalid")
                if (payload["nonce"] != self._nonce or not _lan_hex(payload["writer_nonce"], 64)
                        or not _lan_hex(payload["secret"], 64)):
                    raise PersistentNodeError("tls_material_invalid")
                self._writer_nonce = payload["writer_nonce"]
                self._secret = bytearray.fromhex(payload["secret"])
                self._send("ack", {"proof": self._proof("ack")})
                self._state = "wait_commit"
            else:
                _exact_mapping(payload, {"proof"}, "tls_frame_invalid")
                if (not _lan_hex(payload["proof"], 64)
                        or not hmac.compare_digest(payload["proof"], self._proof(expected))):
                    raise PersistentNodeError("tls_authentication_failed")
                if expected == "ack":
                    self._send("commit", {"proof": self._proof("commit")})
                    self._state = "wait_complete"
                elif expected == "commit":
                    self._send("complete", {"proof": self._proof("complete")})
                    self._state = "done"
                else:
                    self._state = "done"
        except (ValueError, UnicodeError, TypeError, RecursionError):
            raise PersistentNodeError("tls_frame_invalid") from None

    def advance(self) -> bool:
        try:
            self._check()
            progressed = False
            if self._state == "handshake":
                try:
                    self._connection.do_handshake()
                except (self._ssl.WantReadError, self._ssl.WantWriteError):
                    return False
                if (self._connection.get_protocol_version_name() != "TLSv1.3"
                        or self._connection.get_alpn_proto_negotiated() != HANDOFF_ALPN):
                    raise PersistentNodeError("tls_protocol_invalid")
                self._state = "wait_ready" if self.role == "writer" else "wait_deliver"
                progressed = True
                if self.role == "follower":
                    self._nonce = secrets.token_hex(32)
                    self._send("ready", {"nonce": self._nonce})
            for _ in range(8):
                try:
                    raw = self._connection.recv(MAX_FRAME_BYTES)
                except (self._ssl.WantReadError, self._ssl.WantWriteError):
                    break
                if not raw:
                    raise PersistentNodeError("tls_delivery_incomplete")
                self._incoming.extend(raw)
                if len(self._incoming) > MAX_FRAME_BYTES + 4:
                    raise PersistentNodeError("tls_frame_size_invalid")
                progressed = True
                while len(self._incoming) >= 4:
                    size = struct.unpack(">I", self._incoming[:4])[0]
                    if not 0 < size <= MAX_FRAME_BYTES:
                        raise PersistentNodeError("tls_frame_size_invalid")
                    if len(self._incoming) < size + 4:
                        break
                    packet = bytes(self._incoming[4:size + 4])
                    del self._incoming[:size + 4]
                    self._accept(packet)
            return progressed
        except PersistentNodeError:
            self.close()
            raise
        except self._ssl.Error:
            self.close()
            raise PersistentNodeError("tls_peer_or_record_authentication_failed") from None

    def drain(self) -> bytes:
        self._check()
        chunks = bytearray()
        try:
            while True:
                try:
                    part = self._connection.bio_read(MAX_FRAME_BYTES)
                except self._ssl.WantReadError:
                    break
                chunks.extend(part)
                self._wire_out += len(part)
                if self._wire_out > 16 * MAX_FRAME_BYTES:
                    raise PersistentNodeError("tls_wire_limit_exceeded")
        except (PersistentNodeError, self._ssl.Error):
            self.close()
            raise PersistentNodeError("tls_wire_failure") from None
        return bytes(chunks)

    def feed(self, raw: bytes) -> None:
        self._check()
        if type(raw) is not bytes or not raw or len(raw) > 2 * MAX_FRAME_BYTES:
            self.close()
            raise PersistentNodeError("tls_wire_invalid")
        self._wire_in += len(raw)
        if self._wire_in > 16 * MAX_FRAME_BYTES:
            self.close()
            raise PersistentNodeError("tls_wire_limit_exceeded")
        try:
            if self._connection.bio_write(raw) != len(raw):
                raise PersistentNodeError("tls_delivery_incomplete")
        except (PersistentNodeError, self._ssl.Error):
            self.close()
            raise PersistentNodeError("tls_delivery_incomplete") from None

    def take_material(self) -> HandoffMaterial:
        self._check()
        if self._state != "done" or self._incoming or len(self._secret) != 32:
            self.close()
            raise PersistentNodeError("tls_delivery_incomplete")
        material = HandoffMaterial(self._secret, self.role, self.context)
        for i in range(len(self._secret)):
            self._secret[i] = 0
        self._secret.clear()
        self._state = "consumed"
        return material

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.shutdown()
                self._connection.bio_shutdown()
            except Exception:
                pass
        self._connection = self._tls_context = None
        for value in (self._secret, self._incoming):
            for i in range(len(value)):
                value[i] = 0
            value.clear()
        self.identity.close()
        self.closed = True


class _OfflinePipe:
    """Bounded byte transport for the offline interfaces only; never a socket."""
    def __init__(self, role: str = "writer", *, endpoints: Any = None):
        self.endpoints = _peer_config(endpoints)
        self.queue = queue.Queue()
        self.pending, self.closed, self.role, self.timeout = b"", False, role, 2.0
        self.fault = None
    def settimeout(self, value):
        self.timeout = min(value, 2.0)
    def sendall(self, raw):
        if self.closed:
            raise PersistentNodeError("offline_transport_closed")
        if self.fault == "interrupted":
            self.close()
            raise PersistentNodeError("coordinator_interrupted")
        if self.fault in ("bootstrap-context", "bootstrap-pin") and raw[4:5] == b"{":
            announced = json.loads(raw[4:])
            if self.fault == "bootstrap-context":
                announced["context"]["started"] -= 1
            else:
                announced["pin"] = "0" * 64
            body = _canonical_bytes(announced)
            raw = struct.pack(">I", len(body)) + body
            self.fault = None
        if self.fault == "tamper" and raw[4:5] != b"{":
            self.fault = None
            raw = raw[:-1] + bytes([raw[-1] ^ 1])
        self.other.queue.put(raw)
    def recv(self, size):
        if not self.pending:
            try:
                self.pending = self.queue.get(timeout=self.timeout)
            except queue.Empty:
                raise PersistentNodeError("offline_hmac_timeout") from None
        result, self.pending = self.pending[:size], self.pending[size:]
        return result
    def getsockname(self):
        return ((self.endpoints["writer"], 42829) if self.role == "writer"
                else (self.endpoints["follower"], self.endpoints["port"]))
    def getpeername(self):
        return ((self.endpoints["follower"], self.endpoints["port"]) if self.role == "writer"
                else (self.endpoints["writer"], 42829))
    def shutdown(self, how):
        self.close()
    def close(self):
        if not self.closed:
            self.closed, self.pending = True, b""
            self.queue.put(b"")
            self.other.queue.put(b"")


def execute_offline_auth_handoff(case: str = "valid") -> dict[str, Any]:
    """Actual TLS memory-BIO handoff and existing HMAC code, without any sockets."""
    assert_production_authority_inactive()
    if case not in ("valid", "wrong-pin", "wrong-peer", "expired", "incomplete", "tamper", "replay"):
        raise PersistentNodeError("offline_handoff_case_invalid")
    identities, endpoints, materials, channels, pipes, workers = [], [], [], [], [], []
    report = None
    try:
        _tls_backend()
        inventory = lan_source_inventory()
        context = lan_context(secrets.token_hex(16), int(time.time()) - (601 if case == "expired" else 0),
                              "initial", inventory["source_digest"])
        for role in ("writer", "follower"):
            identities.append(MemoryTLSIdentity(role))
        for i, role in enumerate(("writer", "follower")):
            pin = "0" * 64 if case == "wrong-pin" and i == 0 else identities[1-i].pin
            peer_ip = LAN_FOLLOWER_IP if i == 0 else LAN_WRITER_IP
            if case == "wrong-peer" and i == 0:
                peer_ip = LAN_WRITER_IP
            endpoints.append(PinnedTLSHandoff(identities[i], pin, context, peer_ip))
        last_delivery = None
        for _ in range(128):
            progress = False
            for endpoint in endpoints:
                progress = endpoint.advance() or progress
            for i, endpoint in enumerate(endpoints):
                wire = endpoint.drain()
                if wire:
                    if endpoint.role == "writer" and endpoint._state == "wait_ack":
                        if case == "incomplete":
                            raise PersistentNodeError("tls_delivery_incomplete")
                        if case == "tamper":
                            wire = wire[:-1] + bytes([wire[-1] ^ 1])
                    endpoints[1-i].feed(wire)
                    last_delivery = (1-i, wire)
                    progress = True
            if all(e.complete for e in endpoints):
                break
            if not progress:
                raise PersistentNodeError("tls_delivery_incomplete")
        else:
            raise PersistentNodeError("tls_handoff_deadline")
        if case == "replay":
            index, wire = last_delivery
            endpoints[index].feed(wire)
            endpoints[index].advance()
            raise PersistentNodeError("tls_replay_not_rejected")
        for endpoint in endpoints:
            materials.append(endpoint.take_material())

        pipes = [_OfflinePipe("writer"), _OfflinePipe("follower")]
        pipes[0].other, pipes[1].other = pipes[1], pipes[0]
        for i, role in enumerate(("writer", "follower")):
            channels.append(LanChannel(pipes[i], materials[i].consume(role, context), context,
                                       role, time.monotonic() + 10))
        errors = []
        def authenticate(channel):
            try:
                channel.authenticate()
            except PersistentNodeError as exc:
                errors.append(exc.code)
            except Exception:
                errors.append("offline_hmac_internal_failure")
        workers = [threading.Thread(target=authenticate, args=(c,), daemon=True) for c in channels]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=3)
        if any(w.is_alive() for w in workers) or errors:
            raise PersistentNodeError("offline_hmac_authentication_failed")
        channels[0].send("auth_probe", {"public": "verified"})
        if channels[1].receive("auth_probe") != {"public": "verified"}:
            raise PersistentNodeError("offline_hmac_authentication_failed")
        report = {"profile": HANDOFF_PROFILE, "result": "OFFLINE_HANDOFF_PASS",
                  "tls_version": "TLSv1.3", "mutual_certificate_pins_verified": True,
                  "both_node_roles_authenticated": True, "single_use_inputs_consumed": all(m.closed for m in materials),
                  "source_digest": inventory["source_digest"], "writer_ip": LAN_WRITER_IP,
                  "follower_ip": LAN_FOLLOWER_IP, "pyopenssl": version("pyOpenSSL"),
                  "cryptography": version("cryptography"), "physical_two_host_verified": False}
    finally:
        for pipe in pipes:
            pipe.close()
        for worker in workers:
            worker.join(timeout=1)
        for channel in channels:
            channel.key = b""
        for material in materials:
            material.close()
        for endpoint in endpoints:
            endpoint.close()
        for identity in identities:
            identity.close()
    report["cleanup_complete"] = (all(e.closed for e in endpoints) and all(i.closed for i in identities)
                                   and all(m.closed for m in materials) and not any(w.is_alive() for w in workers))
    if not report["cleanup_complete"]:
        raise PersistentNodeError("offline_cleanup_failed")
    return report


def _lan_write_public(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(_canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def _lan_halt(root: Path, reason: str) -> None:
    path = root / "halted.json"
    if not path.exists():
        _lan_write_public(path, {"status": "HALTED_BY_OPTION_A", "reason": reason})


def _lan_agree(root: Path, local: Any, peer: Any) -> None:
    try:
        agreement = assess_state_agreement(local, peer, persistent_testnet_binding())
        if agreement["equal"]:
            return
    except PersistentNodeError:
        _lan_halt(root, "invalid_or_divergent_state")
        raise
    _lan_halt(root, "divergent_state")
    raise PersistentNodeError("lan_divergence_halted")


def _lan_open_state(root: Path, context: dict[str, Any], role: str) -> BlocklessLedger:
    # A new, explicitly named temporary directory; never an active ledger path.
    expected = "l28-disposable-lan-" + context["session"] + "-" + role
    if (root.name != expected or not root.is_absolute()
            or any(p.is_symlink() for p in (root, *root.parents))
            or root.parent.resolve() != Path(tempfile.gettempdir()).resolve()):
        raise PersistentNodeError("lan_data_directory_invalid")
    metadata = {k: v for k, v in context.items() if k != "phase"}
    metadata["role"] = role
    if context["phase"] == "initial":
        root.mkdir(mode=0o700)  # Exclusive creation; never overwrite an old run.
        _lan_write_public(root / "session.json", metadata)
    if not root.is_dir():
        raise PersistentNodeError("lan_state_missing")
    allowed = {"session.json", "ledger"}
    if any(p.name not in allowed or p.is_symlink() for p in root.iterdir()):
        raise PersistentNodeError("lan_state_locked_halted_or_unexpected")
    if (root / "session.json").read_bytes() != _canonical_bytes(metadata):
        raise PersistentNodeError("lan_persisted_session_mismatch")
    _lan_write_public(root / "running.lock", {"pid": os.getpid()})
    directory = root / "ledger"
    if directory.exists():
        files = list(directory.iterdir())
        if len(files) > 5 or any(p.is_symlink() or not p.is_file()
                                or p.name not in {f"shard_{n}.jsonl" for n in range(5)}
                                or p.stat().st_size > MAX_FRAME_BYTES for p in files):
            raise PersistentNodeError("lan_persisted_records_invalid")
    ledger = (asyncio.run(_load_ledger(directory)) if context["phase"] == "restart"
              else _new_ledger(directory))
    events = list(ledger.transactions.values())
    if len(events) > 2 or (events and events[0]["type"] != "coinbase"):
        raise PersistentNodeError("lan_persisted_events_invalid")
    if role == "writer" and context["phase"] == "restart" and len(events) != 2:
        raise PersistentNodeError("lan_writer_incomplete_no_regeneration")
    return ledger


def _lan_replay_probe(ledger: BlocklessLedger, root: Path) -> bool:
    before = ledger_state(ledger)
    files = {p.name: p.read_bytes() for p in (root / "ledger").iterdir()}
    event = list(ledger.transactions.values())[-1]
    if classify_event(ledger, event)[2] != "replay" or asyncio.run(ledger.add_transaction(event)):
        raise PersistentNodeError("lan_replay_probe_failed")
    if before != ledger_state(ledger) or files != {
            p.name: p.read_bytes() for p in (root / "ledger").iterdir()}:
        raise PersistentNodeError("lan_replay_mutated_state")
    return True


def lan_sync(channel: LanChannel, ledger: BlocklessLedger, root: Path) -> dict[str, Any]:
    """Finite two-event protocol. A partial follower resumes only a validated prefix."""
    if channel.role == "writer":
        final = ledger_state(ledger)
        channel.send("offer", final)
        have = channel.receive("prefix")
        local_ids = final["transaction_ids"]
        if not isinstance(have, list) or have != local_ids[:len(have)]:
            _lan_halt(root, "nonprefix_history")
            raise PersistentNodeError("lan_divergence_halted")
        events = list(ledger.transactions.values())
        for i in range(len(have), 2):
            channel.send("event", {"index": i, "event": events[i]})
            if channel.receive("accepted") != events[i]["id"]:
                raise PersistentNodeError("lan_event_ack_invalid")
        peer = channel.receive("state")
        _lan_agree(root, final, peer)
        channel.send("agreement", final)
    else:
        final = validate_public_state(channel.receive("offer"))
        if (len(final["transaction_ids"]) != 2 or final["issued_supply"] != 28
                or sorted(final["balances"].values()) != [0, 28]):
            raise PersistentNodeError("lan_offer_invalid")
        ids = ledger_state(ledger)["transaction_ids"]
        if ids != final["transaction_ids"][:len(ids)]:
            _lan_halt(root, "nonprefix_history")
            raise PersistentNodeError("lan_divergence_halted")
        channel.send("prefix", ids)
        for i in range(len(ids), 2):
            item = _exact_mapping(channel.receive("event"), {"index", "event"}, "lan_event_invalid")
            if type(item["index"]) is not int or item["index"] != i:
                raise PersistentNodeError("lan_event_order_invalid")
            validate_node_event(item["event"])
            if item["event"]["id"] != final["transaction_ids"][i]:
                raise PersistentNodeError("lan_event_identity_invalid")
            asyncio.run(_apply_events(ledger, [item["event"]]))
            channel.send("accepted", item["event"]["id"])
        _lan_agree(root, ledger_state(ledger), final)
        channel.send("state", ledger_state(ledger))
        _lan_agree(root, ledger_state(ledger), channel.receive("agreement"))
    replay = _lan_replay_probe(ledger, root)
    # Deliberate terminal negative probe in the authorized restart invocation.
    # Both hosts persist a halt marker; this disposable session cannot run again.
    halted = False
    if channel.context["phase"] == "restart":
        divergent = deepcopy(final)
        divergent["total_volume"] += 1
        divergent["state_commitment"] = _state_commitment({
            k: v for k, v in divergent.items() if k != "state_commitment"})
        if channel.role == "writer":
            channel.send("divergence_probe", divergent)
            if channel.receive("halted") != "HALTED_BY_OPTION_A":
                raise PersistentNodeError("lan_divergence_probe_failed")
        else:
            peer_probe = channel.receive("divergence_probe")
            if peer_probe != divergent:
                raise PersistentNodeError("lan_divergence_probe_invalid")
        try:
            _lan_agree(root, ledger_state(ledger), divergent)
        except PersistentNodeError as exc:
            if exc.code != "lan_divergence_halted":
                raise
            halted = True
        if not halted:
            raise PersistentNodeError("lan_divergence_probe_failed")
        if channel.role == "follower":
            channel.send("halted", "HALTED_BY_OPTION_A")
    return {"state": ledger_state(ledger), "replay_rejected_without_mutation": replay,
            "terminal_divergence_halt": halted}


def _lan_connected_run(sock: Any, secret: bytes, context: dict[str, Any], role: str,
                       root: Path, deadline: float) -> dict[str, Any]:
    """Shared authenticated ledger path for legacy input and the TLS coordinator."""
    channel, opened = None, False
    try:
        channel = LanChannel(sock, secret, context, role, deadline)
        del secret
        channel.authenticate()
        ledger = _lan_open_state(root, context, role)
        opened = True
        if role == "writer" and context["phase"] == "initial":
            private = Ed25519PrivateKey.generate()
            events = [_build_coinbase(public_identity(_public_key_hex(private))),
                      _build_signed_transfer(private, follower_identity(persistent_testnet_binding()))]
            del private
            asyncio.run(_apply_events(ledger, events))
        result = lan_sync(channel, ledger, root)
        result.update({"profile": context["profile"], "role": role, "phase": context["phase"],
                       "session": context["session"], "session_start": context["started"],
                       "source": lan_source_inventory(),
                       "local_endpoint": sock.getsockname(), "peer_endpoint": sock.getpeername(),
                       "data_dir": str(root), "pid": os.getpid(), "production_authorized": False})
        return result
    finally:
        if channel is not None:
            channel.key = b""
        if opened:
            (root / "running.lock").unlink()


def _coordinator_enrollment(identity: MemoryTLSIdentity, context: Any) -> dict[str, Any]:
    return {"profile": ENROLLMENT_PROFILE, "role": identity.role, "pin": identity.pin,
            "source_digest": lan_source_inventory()["source_digest"], "context": context}


def _coordinator_peer(value: Any, role: str, context: Any) -> dict[str, Any]:
    _exact_mapping(value, {"profile", "role", "pin", "source_digest", "context"},
                   "coordinator_enrollment_invalid")
    peer = "follower" if role == "writer" else "writer"
    if (value["profile"] != ENROLLMENT_PROFILE or value["role"] != peer
            or not _lan_hex(value["pin"], 64)
            or value["source_digest"] != lan_source_inventory()["source_digest"]):
        raise PersistentNodeError("coordinator_enrollment_binding_invalid")
    if role == "follower":
        received = _handoff_context(value["context"])
        if ((context is None and received["phase"] != "initial")
                or (context is not None and _canonical_bytes(received) != _canonical_bytes(context))):
            raise PersistentNodeError("coordinator_session_mismatch")
        return received
    _handoff_context(context)
    expected = None if context["phase"] == "initial" else context
    if _canonical_bytes(value["context"]) != _canonical_bytes(expected):
        raise PersistentNodeError("coordinator_session_mismatch")
    return context


def _coordinator_public_input(prompt: str, deadline: float) -> str:
    # PUBLIC enrollment only. No caller or prompt ever accepts an auth secret.
    if not sys.stdin.isatty():
        raise PersistentNodeError("coordinator_public_terminal_required")
    sys.stdout.write(prompt + "\n")
    sys.stdout.flush()
    if sys.platform == "win32":
        import msvcrt
        chars = []
        while time.monotonic() < deadline:
            if not msvcrt.kbhit():
                time.sleep(0.02)
                continue
            char = msvcrt.getwch()
            if char == "\x03":
                raise KeyboardInterrupt
            if char in ("\r", "\n"):
                sys.stdout.write("\n")
                return "".join(chars)
            if char in ("\x00", "\xe0"):
                raise PersistentNodeError("coordinator_public_input_invalid")
            if char == "\b":
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
            elif char.isprintable():
                chars.append(char)
                sys.stdout.write(char)
            else:
                raise PersistentNodeError("coordinator_public_input_invalid")
            sys.stdout.flush()
            if len(chars) > MAX_FRAME_BYTES:
                raise PersistentNodeError("coordinator_public_input_oversized")
    else:
        remaining = deadline - time.monotonic()
        if remaining > 0 and select.select([sys.stdin], [], [], remaining)[0]:
            line = sys.stdin.readline(MAX_FRAME_BYTES + 2)
            if line.endswith("\n") and len(line) <= MAX_FRAME_BYTES + 1:
                return line.rstrip("\r\n")
            raise PersistentNodeError("coordinator_public_input_invalid")
    raise PersistentNodeError("coordinator_deadline_expired")


def _coordinator_read(sock: Any, size: int, deadline: float, *, enrollment_wait: bool = False) -> bytes:
    value = bytearray()
    while len(value) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PersistentNodeError("coordinator_deadline_expired")
        sock.settimeout(remaining if enrollment_wait else min(SOCKET_TIMEOUT_SECONDS, remaining))
        part = sock.recv(size - len(value))
        if not part:
            raise PersistentNodeError("coordinator_interrupted")
        value.extend(part)
    return bytes(value)


def _coordinator_handoff(sock: Any, endpoint: PinnedTLSHandoff, deadline: float) -> HandoffMaterial:
    for _ in range(128):
        if time.monotonic() >= deadline:
            raise PersistentNodeError("coordinator_deadline_expired")
        endpoint.advance()
        wire = endpoint.drain()
        if wire:
            if len(wire) > 2 * MAX_FRAME_BYTES:
                raise PersistentNodeError("tls_wire_limit_exceeded")
            sock.settimeout(max(0.001, min(SOCKET_TIMEOUT_SECONDS, deadline - time.monotonic())))
            sock.sendall(struct.pack(">I", len(wire)) + wire)
        if endpoint.complete:
            return endpoint.take_material()
        size = struct.unpack(">I", _coordinator_read(sock, 4, deadline))[0]
        if not 0 < size <= 2 * MAX_FRAME_BYTES:
            raise PersistentNodeError("tls_wire_limit_exceeded")
        endpoint.feed(_coordinator_read(sock, size, deadline))
    raise PersistentNodeError("coordinator_deadline_expired")


def _coordinator_connected(sock: Any, identity: MemoryTLSIdentity, peer: dict[str, Any],
                           context: Any, root: Path | None, deadline: float, *, activation: Any = None) -> dict[str, Any]:
    endpoint = material = None
    try:
        role = identity.role
        peers = identity.endpoints
        local_ip, remote_ip = peers[role], peers["follower" if role == "writer" else "writer"]
        local, remote = sock.getsockname(), sock.getpeername()
        if (local[0] != local_ip or remote[0] != remote_ip
                or (local[1] if role == "follower" else remote[1]) != peers["port"]):
            raise PersistentNodeError("coordinator_peer_address_invalid")
        # Public bootstrap is UNTRUSTED metadata, not enrollment or authority.
        # The pin comes only from the operator's direct peer-terminal comparison.
        # The entire context must subsequently match inside pinned TLS and HMAC.
        if role == "writer":
            context = _coordinator_peer(peer, role, context)
            raw = _canonical_bytes(_coordinator_enrollment(identity, context))
            sock.settimeout(max(0.001, min(SOCKET_TIMEOUT_SECONDS, deadline - time.monotonic())))
            sock.sendall(struct.pack(">I", len(raw)) + raw)
        else:
            trusted_pin = peer["pin"]
            if not _lan_hex(trusted_pin, 64):
                raise PersistentNodeError("coordinator_pin_invalid")
            size = struct.unpack(">I", _coordinator_read(sock, 4, deadline))[0]
            if not 0 < size <= MAX_FRAME_BYTES:
                raise PersistentNodeError("coordinator_bootstrap_invalid")
            raw = _coordinator_read(sock, size, deadline)
            try:
                announced = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
                if raw != _canonical_bytes(announced):
                    raise PersistentNodeError("coordinator_bootstrap_invalid")
            except (ValueError, UnicodeError, TypeError, RecursionError):
                raise PersistentNodeError("coordinator_bootstrap_invalid") from None
            context = _coordinator_peer(announced, role, context)
            if not hmac.compare_digest(announced["pin"], trusted_pin):
                raise PersistentNodeError("coordinator_pin_mismatch")
            peer = {**announced, "pin": trusted_pin}  # Never adopt a network pin.
        root = root or (Path(tempfile.gettempdir()).resolve()
                        / ("l28-disposable-lan-" + context["session"] + "-" + role))
        endpoint = PinnedTLSHandoff(identity, peer["pin"], context, remote_ip)
        material = _coordinator_handoff(sock, endpoint, deadline)
        if activation is not None:
            deadline = activation(context)
        endpoint.close()
        result = _lan_connected_run(sock, material.consume(role, context), context, role, root, deadline)
        result["pinned_tls_handoff_verified"] = True
    finally:
        if material is not None:
            material.close()
        if endpoint is not None:
            endpoint.close()
        identity.close()
        try:
            _close_socket(sock)
        except OSError:
            raise PersistentNodeError("coordinator_cleanup_failed") from None
    result["connection_and_identity_closed"] = identity.closed and (endpoint is None or endpoint.closed)
    return result


def _coordinator_restart_context(root: Path, role: str, *, endpoints: Any = None) -> dict[str, Any]:
    prefix, suffix = "l28-disposable-lan-", "-" + role
    if (not root.is_absolute() or root.parent.resolve() != Path(tempfile.gettempdir()).resolve()
            or not root.name.startswith(prefix) or not root.name.endswith(suffix)
            or not _lan_hex(root.name[len(prefix):-len(suffix)], 32)
            or any(p.is_symlink() for p in (root, *root.parents))):
        raise PersistentNodeError("lan_data_directory_invalid")
    path = root / "session.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FRAME_BYTES:
        raise PersistentNodeError("coordinator_restart_metadata_invalid")
    raw = path.read_bytes()
    try:
        metadata = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        context = {k: v for k, v in metadata.items() if k != "role"}
        context["phase"] = "restart"
        context = _handoff_context(context)
        if any(context[k] != value for k, value in _peer_config(endpoints).items()):
            raise PersistentNodeError("coordinator_restart_peer_configuration_invalid")
        expected = {k: v for k, v in context.items() if k != "phase"}
        expected["role"] = role
        if raw != _canonical_bytes(expected) or root.name != prefix + context["session"] + suffix:
            raise PersistentNodeError("coordinator_restart_metadata_invalid")
        return context
    except (ValueError, UnicodeError, AttributeError, TypeError, RecursionError):
        raise PersistentNodeError("coordinator_restart_metadata_invalid") from None


def coordinator_runtime_check(expected: str) -> dict[str, Any]:
    _tls_backend()
    inventory = lan_source_inventory()
    if sys.version_info[:2] != (3, 11):
        raise PersistentNodeError("coordinator_python_version_invalid")
    if not _lan_hex(expected, 64) or inventory["source_digest"] != expected:
        raise PersistentNodeError("coordinator_source_parity_invalid")
    return {"result": "RUNTIME_CHECK_PASS", "source": inventory,
            "pyopenssl": version("pyOpenSSL"), "network_started": False}


def _coordinator_preparation_input(prompt: str, deadline: float) -> str:
    """Public preparation is bounded by the existing identity, never a new lease."""
    if time.monotonic() >= deadline:
        raise PersistentNodeError("coordinator_preparation_expired")
    try:
        value = _coordinator_public_input(prompt, deadline)
    except PersistentNodeError as exc:
        if exc.code == "coordinator_deadline_expired":
            raise PersistentNodeError("coordinator_preparation_expired") from None
        raise
    if time.monotonic() >= deadline:
        raise PersistentNodeError("coordinator_preparation_expired")
    return value


def _coordinator_prepared_record(identity: MemoryTLSIdentity, phase: str,
                                 context: Any) -> dict[str, Any]:
    from cryptography.hazmat.primitives.serialization import Encoding
    if identity.closed or identity.certificate is None or phase not in ("initial", "restart"):
        raise PersistentNodeError("coordinator_credentials_expired")
    return {"status": "PUBLIC_ENROLLMENT", "enrollment": {
        **_coordinator_enrollment(identity, context), "profile": PREPARED_ENROLLMENT_PROFILE,
        "phase": phase, "writer": identity.endpoints["writer"], "follower": identity.endpoints["follower"],
        "port": identity.endpoints["port"], "certificate_der": identity.certificate.public_bytes(Encoding.DER).hex()}}


def _coordinator_prepared_peer(raw: str, identity: MemoryTLSIdentity, phase: str,
                               context: Any) -> tuple[dict[str, Any], float]:
    """Import an operator-physically-verified PUBLIC record, not network metadata.

    VERIFIED is a local human attestation bound to the following complete record,
    not cryptographic evidence of physical inspection. TLS still proves key possession.
    """
    if not isinstance(raw, str) or not raw.startswith("VERIFIED "):
        raise PersistentNodeError("coordinator_physical_verification_required")
    return _coordinator_record_peer(raw[len("VERIFIED "):], identity, phase, context)


def _coordinator_record_peer(raw: str, identity: MemoryTLSIdentity, phase: str,
                             context: Any) -> tuple[dict[str, Any], float]:
    """Public syntax/certificate/binding checks ONLY; this does not approve trust."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import Encoding
    from cryptography.x509.oid import NameOID
    from ipaddress import ip_address
    try:
        encoded = raw.encode("utf-8")
        if not 0 < len(encoded) <= MAX_FRAME_BYTES:
            raise ValueError
        envelope = json.loads(encoded, object_pairs_hook=_reject_duplicate_keys)
        _exact_mapping(envelope, {"status", "enrollment"}, "coordinator_prepared_record_invalid")
        if envelope["status"] != "PUBLIC_ENROLLMENT" or _canonical_bytes(envelope) != encoded:
            raise ValueError
        peer = _exact_mapping(envelope["enrollment"], {"profile", "role", "pin", "source_digest",
            "context", "phase", "writer", "follower", "port", "certificate_der"},
            "coordinator_prepared_record_invalid")
        role = "follower" if identity.role == "writer" else "writer"
        peers = identity.endpoints
        if (peer["profile"] != PREPARED_ENROLLMENT_PROFILE or peer["role"] != role
                or peer["phase"] != phase or peer["writer"] != peers["writer"]
                or peer["follower"] != peers["follower"] or not _exact_int(peer["port"])
                or peer["port"] != peers["port"] or not _lan_hex(peer["pin"], 64)
                or hmac.compare_digest(peer["pin"], identity.pin)
                or peer["source_digest"] != lan_source_inventory()["source_digest"]):
            raise ValueError
        if phase == "initial":
            if context is not None or peer["context"] is not None:
                raise ValueError
        elif phase == "restart":
            if _canonical_bytes(_handoff_context(peer["context"])) != _canonical_bytes(_handoff_context(context)):
                raise ValueError
        else:
            raise ValueError
        der = peer["certificate_der"]
        if not isinstance(der, str) or not 0 < len(der) <= 4096 or len(der) % 2 or not _lan_hex(der, len(der)):
            raise ValueError
        certificate = x509.load_der_x509_certificate(bytes.fromhex(der))
        public_key = certificate.public_key()
        before, after = (certificate.not_valid_before_utc.timestamp(), certificate.not_valid_after_utc.timestamp())
        names = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        ips = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        if (certificate.public_bytes(Encoding.DER).hex() != der
                or certificate.issuer != certificate.subject
                or not hmac.compare_digest(certificate.fingerprint(hashes.SHA256()).hex(), peer["pin"])
                or len(names) != 1 or names[0].value != "l28-disposable-" + role
                or ips.get_values_for_type(x509.IPAddress) != [ip_address(peers[role])]
                or not 0 < after - before <= LAN_SESSION_SECONDS + 30
                or not isinstance(public_key, ec.EllipticCurvePublicKey)
                or not isinstance(public_key.curve, ec.SECP256R1)
                or not isinstance(certificate.signature_hash_algorithm, hashes.SHA256)):
            raise ValueError
        public_key.verify(certificate.signature, certificate.tbs_certificate_bytes,
                          ec.ECDSA(certificate.signature_hash_algorithm))
        if not before <= time.time() < after:
            raise PersistentNodeError("coordinator_peer_credentials_expired")
        wire_peer = {k: peer[k] for k in ("role", "pin", "source_digest", "context")}
        wire_peer["profile"] = ENROLLMENT_PROFILE
        return wire_peer, after
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError,
            InvalidSignature, UnsupportedAlgorithm, x509.ExtensionNotFound, x509.DuplicateExtension):
        raise PersistentNodeError("coordinator_prepared_record_invalid") from None


def _pair_send(sock: Any, value: Any, deadline: float) -> None:
    raw = _canonical_bytes(value)
    remaining = deadline - time.monotonic()
    if not 0 < len(raw) <= MAX_FRAME_BYTES or remaining <= 0:
        raise PersistentNodeError("pair_frame_or_deadline_invalid")
    sock.settimeout(min(SOCKET_TIMEOUT_SECONDS, remaining))
    sock.sendall(struct.pack(">I", len(raw)) + raw)


def _pair_receive(sock: Any, deadline: float, *, enrollment_wait: bool = False) -> dict[str, Any]:
    size = struct.unpack(">I", _coordinator_read(sock, 4, deadline, enrollment_wait=enrollment_wait))[0]
    if not 0 < size <= MAX_FRAME_BYTES:
        raise PersistentNodeError("pair_frame_oversized")
    raw = _coordinator_read(sock, size, deadline, enrollment_wait=enrollment_wait)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        if not isinstance(value, dict) or _canonical_bytes(value) != raw:
            raise ValueError
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise PersistentNodeError("pair_frame_noncanonical") from None


def _pair_fingerprint(left: dict[str, Any], right: dict[str, Any]) -> str:
    records = {r["enrollment"]["role"]: r for r in (left, right)}
    if set(records) != {"writer", "follower"}:
        raise PersistentNodeError("pair_roles_invalid")
    return hashlib.sha256(PAIR_DOMAIN + _canonical_bytes({"profile": PAIR_PROFILE,
        "writer": records["writer"], "follower": records["follower"]})).hexdigest()


def _pair_exchange(sock: Any, identity: MemoryTLSIdentity, phase: str,
                   context: Any, deadline: float) -> tuple[dict[str, Any], float, str, str]:
    local = _coordinator_prepared_record(identity, phase, context)
    _pair_send(sock, local, deadline)  # PUBLIC only; transport is not a trust anchor.
    remote = _pair_receive(sock, deadline)
    raw = _canonical_bytes(remote).decode()
    peer, expiry = _coordinator_record_peer(raw, identity, phase, context)
    deadline = min(deadline, time.monotonic() + expiry - time.time())
    fingerprint = _pair_fingerprint(local, remote)
    _emit({"status": "PAIRING_REQUIRED", "profile": PAIR_PROFILE, "phase": phase,
           "role": identity.role, "fingerprint": fingerprint, "records": "UNTRUSTED",
           "ledger_started": False})
    if _coordinator_preparation_input(
            "Physically compare the COMPLETE 64-character fingerprint on BOTH computers. Type PAIR locally only if identical; otherwise stop:", deadline) != "PAIR":
        raise PersistentNodeError("pairing_not_approved")
    confirmation = {"profile": PAIR_PROFILE, "type": "local_physical_approval", "fingerprint": fingerprint}
    _pair_send(sock, confirmation, deadline)
    if _pair_receive(sock, deadline, enrollment_wait=True) != confirmation:
        raise PersistentNodeError("pairing_fingerprint_mismatch")
    # The public acknowledgment alone proves nothing. Both honest roles gate TLS
    # on their own local input; pinned TLS must prove possession before any ledger.
    _coordinator_record_peer(raw, identity, phase, context)
    return peer, expiry, fingerprint, raw


class _PairOfflineSocket:
    """Explicit offline AF_UNIX adapter; never represents physical IP evidence."""
    def __init__(self, fd: int, role: str, *, endpoints: Any = None):
        self.endpoints = _peer_config(endpoints)
        self.sock = socket.socket(fileno=fd)
        if self.sock.family != socket.AF_UNIX:
            self.sock.close()
            raise PersistentNodeError("pair_offline_transport_invalid")
        self.role = role
    def getsockname(self):
        return ((self.endpoints["writer"], 42829) if self.role == "writer"
                else (self.endpoints["follower"], self.endpoints["port"]))
    def getpeername(self):
        return ((self.endpoints["follower"], self.endpoints["port"]) if self.role == "writer"
                else (self.endpoints["writer"], 42829))
    def settimeout(self, value):
        self.sock.settimeout(value)
    def recv(self, size):
        return self.sock.recv(size)
    def sendall(self, raw):
        self.sock.sendall(raw)
    def shutdown(self, how):
        self.sock.shutdown(how)
    def close(self):
        self.sock.close()


def _pair_open(role: str, deadline: float, endpoints: Any = None) -> Any:
    peers = _peer_config(endpoints)
    if role == "follower":
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Same restart binding as the existing disposable loopback listener.
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.settimeout(max(0.001, deadline - time.monotonic()))
            listener.bind((peers["follower"], peers["port"]))
            listener.listen(1)
            _emit({"status": "PAIRING_LISTENING", "role": role})
            sock, address = listener.accept()
            if address[0] != peers["writer"]:
                _close_socket(sock)
                raise PersistentNodeError("coordinator_peer_address_invalid")
            return sock
        finally:
            _close_socket(listener)
    # Startup wait only, before a session/approval exists. Never reconnect after
    # an accepted connection, pairing failure or authentication failure.
    while time.monotonic() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(min(SOCKET_TIMEOUT_SECONDS, max(0.001, deadline - time.monotonic())))
            sock.bind((peers["writer"], 0))
            sock.connect((peers["follower"], peers["port"]))
            return sock
        except ConnectionRefusedError:
            _close_socket(sock)
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        except BaseException:
            _close_socket(sock)
            raise
    raise PersistentNodeError("pair_startup_expired")


def _pair_report_context(args: Any) -> Any:
    root = args.report_dir
    if (root is None or not root.is_absolute() or not root.name.startswith("l28-pair-launch-")
            or root.parent.resolve() != Path(tempfile.gettempdir()).resolve()
            or any(p.is_symlink() for p in (root, *root.parents)) or not root.is_dir()
            or any(p.name not in {"initial.json"} or not p.is_file() or p.is_symlink() for p in root.iterdir())):
        raise PersistentNodeError("pair_report_directory_invalid")
    initial = root / "initial.json"
    if args.phase == "initial":
        if initial.exists():
            raise PersistentNodeError("pair_report_already_exists")
        return None
    if not initial.is_file() or initial.stat().st_size > MAX_FRAME_BYTES:
        raise PersistentNodeError("pair_initial_report_invalid")
    try:
        raw = initial.read_bytes()
        report = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
        if (raw != _canonical_bytes(report) or report["result"] != "PAIR_PHASE_PASS"
                or report["role"] != args.role or report["phase"] != "initial"
                or report["source"]["source_digest"] != args.expected_source_digest
                or not _exact_int(report["pid"]) or report["pid"] == os.getpid()
                or report["data_dir"] != str(args.data_dir)):
            raise ValueError
        endpoints = _configured_peers(args)
        if endpoints is not None and report.get("peer_configuration") != endpoints:
            raise ValueError
        return report
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError):
        raise PersistentNodeError("pair_initial_report_invalid") from None


def paired_coordinator_main(args: Any) -> int:
    assert_production_authority_inactive()
    endpoints = _configured_peers(args)
    peers = _peer_config(endpoints)
    offline = args.offline_pair_role
    if (args.role not in ("writer", "follower") or args.phase not in ("initial", "restart")
            or args.port is not None or args.session_id is not None or args.session_start is not None
            or (args.phase == "initial" and args.data_dir is not None)
            or (args.phase == "restart" and args.data_dir is None)
            or (offline and (os.name != "posix" or not _exact_int(args.offline_fd) or args.offline_fd < 0 or args.ack_private_lan))
            or (not offline and ((not args.ack_private_lan and endpoints is None) or args.offline_fd is not None))):
        raise PersistentNodeError("pair_arguments_invalid")
    coordinator_runtime_check(args.expected_source_digest)
    identity = sock = watchdog = None
    try:
        prior = _pair_report_context(args)
        identity = (MemoryTLSIdentity(args.role) if endpoints is None
                    else MemoryTLSIdentity(args.role, endpoints=endpoints))
        own_pin = identity.pin
        deadline = time.monotonic() + min(LAN_SESSION_SECONDS,
            identity.certificate.not_valid_after_utc.timestamp() - time.time())
        context = (None if args.phase == "initial" else
                   _coordinator_restart_context(args.data_dir, args.role, endpoints=endpoints))
        if context is not None:
            deadline = min(deadline, time.monotonic() + context["started"] + LAN_SESSION_SECONDS - time.time())
        if deadline <= time.monotonic():
            raise PersistentNodeError("coordinator_credentials_expired")
        watchdog = threading.Timer(deadline - time.monotonic(), lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
        if offline:
            sock = _PairOfflineSocket(args.offline_fd, args.role, endpoints=endpoints)
        else:
            sock = (_pair_open(args.role, deadline) if endpoints is None
                    else _pair_open(args.role, deadline, endpoints))
        local, remote = sock.getsockname(), sock.getpeername()
        if ((local[0], remote[0]) != ((peers["writer"], peers["follower"]) if args.role == "writer"
                else (peers["follower"], peers["writer"])) or (remote[1] if args.role == "writer" else local[1]) != peers["port"]):
            raise PersistentNodeError("coordinator_peer_address_invalid")
        peer, expiry, fingerprint, raw_peer = _pair_exchange(sock, identity, args.phase, context, deadline)
        deadline = min(deadline, time.monotonic() + expiry - time.time())
        if not identity.certificate.not_valid_before_utc.timestamp() <= time.time() < identity.certificate.not_valid_after_utc.timestamp():
            raise PersistentNodeError("coordinator_credentials_expired")
        if context is None and args.role == "writer":
            context = lan_context(secrets.token_hex(16), int(time.time()), "initial", args.expected_source_digest,
                                  endpoints=endpoints)
        def activate(resolved):
            nonlocal watchdog
            coordinator_runtime_check(args.expected_source_digest)
            _coordinator_record_peer(raw_peer, identity, args.phase,
                                     resolved if args.phase == "restart" else None)
            resolved = _handoff_context(resolved)
            remaining = min(PARENT_DEADLINE_SECONDS, deadline - time.monotonic(),
                            identity.certificate.not_valid_after_utc.timestamp() - time.time(),
                            expiry - time.time(),
                            resolved["started"] + LAN_SESSION_SECONDS - time.time())
            if remaining <= 0:
                raise PersistentNodeError("coordinator_deadline_expired")
            active_deadline = time.monotonic() + remaining
            watchdog.cancel()
            watchdog.join(timeout=1)
            remaining = active_deadline - time.monotonic()
            if remaining <= 0:
                raise PersistentNodeError("coordinator_deadline_expired")
            watchdog = threading.Timer(remaining, lambda: os._exit(124))
            watchdog.daemon = True
            watchdog.start()
            return active_deadline
        result = _coordinator_connected(sock, identity, peer, context, args.data_dir, deadline, activation=activate)
        result.update(result="PAIR_PHASE_PASS", pairing_fingerprint=fingerprint,
            local_certificate_pin=own_pin, peer_certificate_pin=peer["pin"],
            physical_comparison="operator_attested" if not offline else "offline_fixture",
            physical_two_host_verified=False, physical_cross_network_verified=False,
            peer_configuration=peers, encrypted_route_verified=False,
            transport="OFFLINE_IPC" if offline else ("PRIVATE_ROUTE_OPERATOR_ATTESTED" if endpoints else "PRIVATE_LAN"))
        if prior is not None:
            if (result["state"] != prior["state"] or result["session"] != prior["session"]
                    or result["session_start"] != prior["session_start"]
                    or own_pin == prior["local_certificate_pin"] or peer["pin"] == prior["peer_certificate_pin"]
                    or not result["replay_rejected_without_mutation"] or not result["terminal_divergence_halt"]):
                raise PersistentNodeError("pair_restart_verification_failed")
            result.update(result="PAIR_WORKFLOW_PASS", previous_pid=prior["pid"],
                          genuine_local_process_restart_verified=True, durable_restart_agreement=True)
    except (OSError, ValueError, EOFError, KeyError, TypeError):
        raise PersistentNodeError("pair_io_or_report_failure") from None
    except KeyboardInterrupt:
        raise PersistentNodeError("coordinator_cancelled") from None
    finally:
        try:
            _close_socket(sock)
        finally:
            if identity is not None:
                identity.close()
            if watchdog is not None:
                watchdog.cancel()
                if watchdog.ident is not None:
                    watchdog.join(timeout=1)
    try:
        _lan_write_public(args.report_dir / (args.phase + ".json"), result)
    except OSError:
        raise PersistentNodeError("pair_report_write_failed") from None
    _emit(result)
    return 0


def pairing_launcher(args: Any) -> str:
    """Print public-only native shell orchestration; never start a node here."""
    import shlex
    endpoints = _configured_peers(args)
    if (args.role not in ("writer", "follower") or args.phase is not None or args.data_dir is not None
            or args.report_dir is not None or args.offline_fd is not None or args.port is not None
            or args.session_id is not None or args.session_start is not None
            or (not args.ack_private_lan and endpoints is None)):
        raise PersistentNodeError("pair_launcher_arguments_invalid")
    coordinator_runtime_check(args.expected_source_digest)
    target = args.launcher_platform or ("windows" if sys.platform == "win32" else "mac")
    if (target, args.role) not in (("mac", "writer"), ("windows", "follower")):
        raise PersistentNodeError("pair_launcher_platform_role_invalid")
    root, python, digest = str(Path(__file__).resolve().parents[1]), sys.executable, args.expected_source_digest
    if target == "mac":
        import OpenSSL
        values = {"@ROOT@": shlex.quote(root), "@PYTHON@": shlex.quote(python),
                  "@DIGEST@": shlex.quote(digest),
                  "@REPORTPATTERN@": shlex.quote(str(Path(tempfile.gettempdir()).resolve() / "l28-pair-launch-XXXXXXXX")),
                  "@BACKEND@": shlex.quote(str(Path(OpenSSL.__file__).resolve().parents[1]))}
        script = r'''(
setopt pipefail
zmodload zsh/system || exit 1
l28Parent=$sysparams[pid]
cd @ROOT@ || exit 1
export PYTHONPATH=@BACKEND@
l28Py=@PYTHON@
l28Digest=@DIGEST@
[[ "$(/sbin/ifconfig en0 | /usr/bin/awk '$1=="inet" {print $2}')" == 192.168.68.50 ]] || { print 'STOP: Mac IP changed'; exit 1; }
/usr/sbin/lsof -nP -iTCP:42828 -sTCP:LISTEN
(( $? == 1 )) || { print 'STOP: port check failed or listener remains'; exit 1; }
/usr/bin/pgrep -l -f '[p]ersistent_disposable_testnet_node'
(( $? == 1 )) || { print 'STOP: old node remains or process check failed'; exit 1; }
l28Reports=$(/usr/bin/mktemp -d @REPORTPATTERN@) || exit 1
print 'NETWORK uma: operator-attested; scope Mac 192.168.68.50 / Surface 192.168.68.54 / TCP 42828'
print "PUBLIC_REPORTS=$l28Reports"
l28_cleanup() {
  local result=$?
  local cleanup=0
  trap - EXIT INT TERM
  local child
  for child in $(/usr/bin/pgrep -P "$l28Parent" -f '[p]ersistent_disposable_testnet_node.*--paired-coordinate'); do
    kill -TERM "$child" 2>/dev/null
    wait "$child" 2>/dev/null
  done
  /usr/sbin/lsof -nP -iTCP:42828 -sTCP:LISTEN
  if (( $? != 1 )); then result=1; cleanup=1; print 'MAC_CLEANUP_FAILED: listener/check'; fi
  /usr/bin/pgrep -l -f '[p]ersistent_disposable_testnet_node'
  if (( $? != 1 )); then result=1; cleanup=1; print 'MAC_CLEANUP_FAILED: process/check'; fi
  if (( cleanup == 0 )); then print 'MAC_CLEANUP_VERIFIED'; fi
  if (( result != 0 )); then print 'STOP: no retry; preserve public evidence'; fi
  exit "$result"
}
trap l28_cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
"$l28Py" -B -m coin.persistent_disposable_testnet_node --paired-coordinate --role writer --phase initial --report-dir "$l28Reports" --ack-private-lan --expected-source-digest "$l28Digest"
l28Code=$?; print "MAC_INITIAL_EXIT=$l28Code"
(( l28Code == 0 )) || exit "$l28Code"
l28State=$(/usr/bin/plutil -extract data_dir raw -o - "$l28Reports/initial.json") || exit 1
"$l28Py" -B -m coin.persistent_disposable_testnet_node --paired-coordinate --role writer --phase restart --data-dir "$l28State" --report-dir "$l28Reports" --ack-private-lan --expected-source-digest "$l28Digest"
l28Code=$?; print "MAC_RESTART_EXIT=$l28Code"
exit "$l28Code"
)'''
    else:
        quote = lambda value: "'" + value.replace("'", "''") + "'"
        values = {"@ROOT@": quote(root), "@PYTHON@": quote(python), "@DIGEST@": quote(digest)}
        script = r'''& {
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath @ROOT@
$l28Py = @PYTHON@
$l28Digest = @DIGEST@
$l28Rule = 'L28-TEMP-TWOHOST-42828'
$l28IP = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -eq '192.168.68.54')
if ($l28IP.Count -ne 1) { throw 'STOP: Surface IP changed' }
$l28Profile = Get-NetConnectionProfile -InterfaceIndex $l28IP[0].InterfaceIndex
if ($l28Profile.NetworkCategory -ne 'Private') { throw 'STOP: Private profile required' }
$l28Wifi = & netsh wlan show interfaces
if ($LASTEXITCODE -ne 0 -or @($l28Wifi -match '^\s*SSID\s*:\s*uma\s*$').Count -ne 1) { throw 'STOP: uma not confirmed' }
if (Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq 42828) { throw 'STOP: port occupied' }
if (Get-NetFirewallRule -ErrorAction Stop | Where-Object Name -eq $l28Rule) { throw 'STOP: previous rule remains' }
if (Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object CommandLine -match 'coin\.persistent_disposable_testnet_node') { throw 'STOP: previous node remains' }
$l28Reports = Join-Path ([IO.Path]::GetTempPath()) ('l28-pair-launch-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $l28Reports -ErrorAction Stop | Out-Null
Write-Host "PUBLIC_REPORTS=$l28Reports"
try {
  New-NetFirewallRule -Name $l28Rule -DisplayName $l28Rule -Profile Private -Direction Inbound -Action Allow -Protocol TCP -LocalAddress 192.168.68.54 -RemoteAddress 192.168.68.50 -LocalPort 42828 | Out-Null
  & $l28Py -B -m coin.persistent_disposable_testnet_node --paired-coordinate --role follower --phase initial --report-dir $l28Reports --ack-private-lan --expected-source-digest $l28Digest
  $l28Code = $LASTEXITCODE; Write-Host "SURFACE_INITIAL_EXIT=$l28Code"
  if ($l28Code -ne 0) { throw "Initial failed: exit $l28Code; no retry" }
  $l28State = (Get-Content -LiteralPath (Join-Path $l28Reports 'initial.json') -Raw | ConvertFrom-Json).data_dir
  & $l28Py -B -m coin.persistent_disposable_testnet_node --paired-coordinate --role follower --phase restart --data-dir $l28State --report-dir $l28Reports --ack-private-lan --expected-source-digest $l28Digest
  $l28Code = $LASTEXITCODE; Write-Host "SURFACE_RESTART_EXIT=$l28Code"
  if ($l28Code -ne 0) { throw "Restart failed: exit $l28Code; no retry" }
} finally {
  Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object { $_.ParentProcessId -eq $PID -and $_.CommandLine -match 'coin\.persistent_disposable_testnet_node.*--paired-coordinate' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop }
  Remove-NetFirewallRule -Name $l28Rule -ErrorAction SilentlyContinue
  if (Get-NetFirewallRule -ErrorAction Stop | Where-Object Name -eq $l28Rule) { throw 'STOP: firewall cleanup failed' }
  if (Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq 42828) { throw 'STOP: listener remains' }
  if (Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object CommandLine -match 'coin\.persistent_disposable_testnet_node') { throw 'STOP: node remains' }
  Write-Host 'SURFACE_CLEANUP_VERIFIED'
}
}'''
    if endpoints is not None:
        # Render validated PUBLIC values only, leaving the accepted LAN template
        # unchanged. Tokens avoid cascading substitutions when addresses overlap.
        script = script.replace(LAN_WRITER_IP, "@WRITER@").replace(LAN_FOLLOWER_IP, "@FOLLOWER@")
        script = script.replace("L28-TEMP-TWOHOST-42828", "L28-TEMP-TWONET-@PORT@")
        script = script.replace("42828", "@PORT@")
        script = script.replace("--ack-private-lan", "--peer-writer-ip @WRITER@ --peer-follower-ip @FOLLOWER@ --peer-port @PORT@ --ack-encrypted-private-route")
        script = script.replace("/sbin/ifconfig en0 | /usr/bin/awk '$1==\"inet\" {print $2}'",
                                "/sbin/ifconfig | /usr/bin/awk '$1==\"inet\" && $2==\"@WRITER@\" {print $2}'")
        script = script.replace("NETWORK uma: operator-attested; scope", "ENCRYPTED PRIVATE ROUTE: operator-attested, not programmatically verified; scope")
        script = script.replace("$l28Wifi = & netsh wlan show interfaces\nif ($LASTEXITCODE -ne 0 -or @($l28Wifi -match '^\\s*SSID\\s*:\\s*uma\\s*$').Count -ne 1) { throw 'STOP: uma not confirmed' }",
                                "Write-Host 'ENCRYPTED PRIVATE ROUTE: operator-attested, not programmatically verified'")
        values.update({"@WRITER@": endpoints["writer"], "@FOLLOWER@": endpoints["follower"],
                       "@PORT@": str(endpoints["port"])})
    for key, value in values.items():
        script = script.replace(key, value)
    return script


def coordinator_main(args: Any) -> int:
    assert_production_authority_inactive()
    if (not args.ack_private_lan or args.role not in ("writer", "follower")
            or args.phase not in ("initial", "restart") or args.port is not None
            or args.session_id is not None or args.session_start is not None
            or (args.phase == "initial" and args.data_dir is not None)
            or (args.phase == "restart" and args.data_dir is None)):
        raise PersistentNodeError("coordinator_arguments_invalid")
    coordinator_runtime_check(args.expected_source_digest)
    context = None
    identity = sock = listener = watchdog = None
    # Last-resort process deadline: the OS closes handles on exit. No secret files
    # exist. Public crash locks remain fail-closed; never remove them to force retry.
    try:
        identity = MemoryTLSIdentity(args.role)
        preparation_deadline = time.monotonic() + (identity.certificate.not_valid_after_utc.timestamp() - time.time())
        if preparation_deadline <= time.monotonic():
            raise PersistentNodeError("coordinator_credentials_expired")
        watchdog = threading.Timer(max(0.001, preparation_deadline - time.monotonic()), lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
        if args.phase == "restart":
            context = _coordinator_restart_context(args.data_dir, args.role)
        _emit(_coordinator_prepared_record(identity, args.phase, context))
        raw_peer = _coordinator_preparation_input(
            "After DIRECT PHYSICAL inspection on the peer computer, paste VERIFIED followed by a space and its COMPLETE PUBLIC_ENROLLMENT JSON line; never a secret or unverified network record:", preparation_deadline)
        peer, peer_expiration = _coordinator_prepared_peer(raw_peer, identity, args.phase, context)
        peer_deadline = time.monotonic() + peer_expiration - time.time()
        _emit({"status": "PREPARED_ENROLLED", "role": args.role, "peer_pin": peer["pin"],
               "physical_inspection": "operator_attested", "network_started": False})
        if args.role == "writer":
            if _coordinator_preparation_input(
                    "After Surface says FOLLOWER_LISTENING, enter READY (public):", preparation_deadline) != "READY":
                raise PersistentNodeError("coordinator_readiness_not_confirmed")

        # No socket, ledger access or fresh network session precedes this transition.
        active_started = time.monotonic()
        now = time.time()
        if (identity.closed or identity.certificate is None
                or not identity.certificate.not_valid_before_utc.timestamp() <= now
                       < identity.certificate.not_valid_after_utc.timestamp()):
            raise PersistentNodeError("coordinator_credentials_expired")
        coordinator_runtime_check(args.expected_source_digest)
        peer, peer_expiration = _coordinator_prepared_peer(raw_peer, identity, args.phase, context)
        if context is not None:
            context = _handoff_context(context)  # Recheck original START after enrollment.
        elif args.role == "writer":
            context = lan_context(secrets.token_hex(16), int(now), "initial", args.expected_source_digest)
        remaining = min(PARENT_DEADLINE_SECONDS, preparation_deadline - active_started,
                        peer_deadline - active_started,
                        identity.certificate.not_valid_after_utc.timestamp() - now, peer_expiration - now)
        if context is not None:
            remaining = min(remaining, context["started"] + LAN_SESSION_SECONDS - now)
        if remaining <= 0:
            raise PersistentNodeError("coordinator_deadline_expired")
        deadline = active_started + remaining
        watchdog.cancel()
        watchdog.join(timeout=1)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PersistentNodeError("coordinator_deadline_expired")
        watchdog = threading.Timer(remaining, lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
        if args.role == "follower":
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.settimeout(max(0.001, deadline - time.monotonic()))
            listener.bind((LAN_FOLLOWER_IP, LAN_PORT))
            listener.listen(1)
            _emit({"status": "FOLLOWER_LISTENING", "role": "follower"})
            sock, _ = listener.accept()
            _close_socket(listener)
            listener = None
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(max(0.001, min(SOCKET_TIMEOUT_SECONDS, deadline - time.monotonic())))
            sock.bind((LAN_WRITER_IP, 0))
            sock.connect((LAN_FOLLOWER_IP, LAN_PORT))
        result = _coordinator_connected(sock, identity, peer, context, args.data_dir, deadline)
        result["result"] = "COORDINATOR_PHASE_PASS"
    except (OSError, ValueError, EOFError):
        raise PersistentNodeError("coordinator_io_failure") from None
    except KeyboardInterrupt:
        raise PersistentNodeError("coordinator_cancelled") from None
    finally:
        cleanup_error = False
        for connection in (sock, listener):
            try:
                _close_socket(connection)
            except OSError:
                cleanup_error = True
        if identity is not None:
            identity.close()
        if watchdog is not None:
            watchdog.cancel()
            if watchdog.ident is not None:
                watchdog.join(timeout=1)
        if cleanup_error:
            raise PersistentNodeError("coordinator_cleanup_failed")
    _emit(result)
    return 0


def execute_offline_coordinator(case: str = "valid", *, endpoints: Any = None) -> dict[str, Any]:
    """Integrated TLS wire driver -> HMAC -> ledger -> durable reopen, no sockets."""
    if case not in ("valid", "wrong-pin", "wrong-peer", "source-mismatch", "interrupted", "tamper",
                    "bootstrap-context", "bootstrap-pin", "unverified-record", "substituted-record",
                    "wrong-record-source", "wrong-record-role"):
        raise PersistentNodeError("coordinator_offline_case_invalid")
    assert_production_authority_inactive()
    peers = _peer_config(endpoints)
    context = lan_context(secrets.token_hex(16), int(time.time()), "initial",
                          lan_source_inventory()["source_digest"], endpoints=endpoints)
    roots = [Path(tempfile.gettempdir()).resolve() / ("l28-disposable-lan-" + context["session"] + "-" + r)
             for r in ("writer", "follower")]
    if any(root.exists() for root in roots):
        raise PersistentNodeError("coordinator_offline_path_exists")
    identities, pipes, workers, results, errors = [], [], [], [], []
    initial = None
    try:
        for phase in ("initial", "restart"):
            context = {**context, "phase": phase}
            if phase == "restart" and any(_coordinator_restart_context(root, role, endpoints=endpoints) != context
                    for root, role in zip(roots, ("writer", "follower"))):
                raise PersistentNodeError("coordinator_offline_restart_failed")
            identities = []
            for role in ("writer", "follower"):
                identities.append(MemoryTLSIdentity(role) if endpoints is None
                                  else MemoryTLSIdentity(role, endpoints=endpoints))
            # Deterministic offline fixture stands in for direct physical inspection;
            # it is not evidence of physical/operator verification on two machines.
            prepared = [_coordinator_prepared_record(i, phase, context if phase == "restart" else None)
                        for i in identities]
            if case == "substituted-record":
                prepared[1]["enrollment"]["certificate_der"] = prepared[0]["enrollment"]["certificate_der"]
            elif case == "wrong-record-source":
                prepared[1]["enrollment"]["source_digest"] = "0" * 64
            elif case == "wrong-record-role":
                prepared[1]["enrollment"]["role"] = "writer"
            enrollments = [_coordinator_prepared_peer(("" if case == "unverified-record" else "VERIFIED ") + _canonical_bytes(record).decode(),
                identities[1-index], phase, context if phase == "restart" else None)[0]
                for index, record in enumerate(prepared)]
            if case == "wrong-pin":
                enrollments[1]["pin"] = "0" * 64
            if case == "source-mismatch":
                enrollments[1]["source_digest"] = "0" * 64
            pipes = ([_OfflinePipe("writer"), _OfflinePipe("follower")] if endpoints is None else
                     [_OfflinePipe(role, endpoints=endpoints) for role in ("writer", "follower")])
            pipes[0].other, pipes[1].other = pipes[1], pipes[0]
            if case in ("interrupted", "tamper", "bootstrap-context", "bootstrap-pin"):
                pipes[0].fault = case
            if case == "wrong-peer":
                pipes[0].getpeername = lambda: (peers["writer"], peers["port"])
            results, errors = [None, None], []
            def run(index):
                try:
                    results[index] = _coordinator_connected(pipes[index], identities[index], enrollments[1-index],
                                                             None if index == 1 and phase == "initial" else context,
                                                             roots[index], time.monotonic() + 10)
                except PersistentNodeError as exc:
                    errors.append(exc.code)
                except Exception:
                    errors.append("coordinator_offline_internal_failure")
            workers = [threading.Thread(target=run, args=(i,), daemon=True) for i in range(2)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=5)
            if any(worker.is_alive() for worker in workers):
                raise PersistentNodeError("coordinator_offline_deadline")
            if errors:
                priority = ("coordinator_enrollment_binding_invalid", "coordinator_peer_address_invalid",
                            "tls_peer_or_record_authentication_failed", "tls_frame_binding_invalid",
                            "coordinator_pin_mismatch", "coordinator_session_mismatch", "coordinator_interrupted")
                raise PersistentNodeError(next((c for c in priority if c in errors), errors[0]))
            if case != "valid":
                raise PersistentNodeError("coordinator_negative_probe_not_rejected")
            left, right = results
            if (left["state"] != right["state"] or not all(r["pinned_tls_handoff_verified"]
                    and r["connection_and_identity_closed"] and r["replay_rejected_without_mutation"] for r in results)):
                raise PersistentNodeError("coordinator_offline_agreement_failed")
            if phase == "initial":
                initial = left["state"]
            elif (left["state"] != initial or not all(r["terminal_divergence_halt"] for r in results)
                  or not all((root / "halted.json").is_file() for root in roots)):
                raise PersistentNodeError("coordinator_offline_restart_failed")
    finally:
        for pipe in pipes:
            pipe.close()
        for worker in workers:
            worker.join(timeout=2)
        for identity in identities:
            identity.close()
        # Only these fresh, uniquely named offline disposable paths belong to us.
        for root in roots:
            if root.exists():
                shutil.rmtree(root)
    if (any(w.is_alive() for w in workers) or any(root.exists() for root in roots)
            or not all(i.closed for i in identities) or not all(p.closed for p in pipes)):
        raise PersistentNodeError("coordinator_offline_cleanup_failed")
    if initial["issued_supply"] != 28 or sorted(initial["balances"].values()) != [0, 28]:
        raise PersistentNodeError("coordinator_offline_supply_invalid")
    return {"result": "OFFLINE_COORDINATOR_PASS", "source_digest": context["source_digest"],
            "peer_configuration": peers, "network_started": False,
            "encrypted_route_verified": False, "physical_cross_network_verified": False,
            "prepared_public_records_verified": True, "physical_inspection_verified": False,
            "state": initial, "pinned_tls_and_hmac_verified": True,
            "independent_validation": True, "durable_reopen_agreement": True,
            "replay_rejected": True, "divergence_halted": True, "cleanup_complete": True,
            "physical_two_host_verified": False, "physical_process_restart_verified": False}


def lan_main(args: Any, *, authentication: HandoffMaterial | None = None) -> int:
    assert_production_authority_inactive()
    inventory = lan_source_inventory()
    if (args.role not in ("writer", "follower") or args.phase is None
            or args.data_dir is None or args.port is not None or not args.ack_private_lan):
        raise PersistentNodeError("lan_arguments_or_prerequisites_missing")
    context = lan_context(args.session_id, args.session_start, args.phase, inventory["source_digest"])
    if not isinstance(authentication, HandoffMaterial):
        raise PersistentNodeError("lan_authentication_handoff_required")
    secret = authentication.consume(args.role, context)
    remaining = min(PARENT_DEADLINE_SECONDS, context["started"] + LAN_SESSION_SECONDS - time.time())
    deadline = time.monotonic() + remaining
    watchdog = threading.Timer(remaining, lambda: os._exit(124))
    watchdog.daemon = True
    watchdog.start()
    sock = listener = None
    try:
        if args.role == "follower":
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.settimeout(max(0.001, deadline - time.monotonic()))
            listener.bind((LAN_FOLLOWER_IP, LAN_PORT))
            listener.listen(1)
            sock, peer = listener.accept()
            _close_socket(listener)
            listener = None
            if peer[0] != LAN_WRITER_IP:
                raise PersistentNodeError("lan_peer_address_invalid")
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(min(SOCKET_TIMEOUT_SECONDS, max(0.001, deadline - time.monotonic())))
            sock.bind((LAN_WRITER_IP, 0))
            sock.connect((LAN_FOLLOWER_IP, LAN_PORT))
        result = _lan_connected_run(sock, secret, context, args.role, args.data_dir, deadline)
        del secret
        _close_socket(sock)
        sock = None
        _emit(result)
        return 0
    finally:
        _close_socket(sock)
        _close_socket(listener)
        watchdog.cancel()


def main(argv: list[str] | None = None, *, authentication: HandoffMaterial | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.persistent_disposable_testnet_node"
    )
    parser.add_argument(
        "--role", choices=("parent", "writer", "follower"), default="parent"
    )
    parser.add_argument("--phase", choices=("initial", "restart"))
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--port", type=int)
    parser.add_argument("--lan", action="store_true")
    parser.add_argument("--source-inventory", action="store_true")
    parser.add_argument("--session-id")
    parser.add_argument("--session-start", type=int)
    parser.add_argument("--ack-private-lan", action="store_true")
    parser.add_argument("--offline-auth-handoff", action="store_true")
    parser.add_argument("--handoff-case", choices=("valid", "wrong-pin", "wrong-peer", "expired", "incomplete", "tamper", "replay"))
    parser.add_argument("--coordinate", action="store_true")
    parser.add_argument("--paired-coordinate", action="store_true")
    parser.add_argument("--offline-pair-role", action="store_true")
    parser.add_argument("--offline-fd", type=int)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--print-launcher", action="store_true")
    parser.add_argument("--launcher-platform", choices=("mac", "windows"))
    parser.add_argument("--offline-coordinator", action="store_true")
    parser.add_argument("--coordinator-case", choices=("valid", "wrong-pin", "wrong-peer", "source-mismatch", "interrupted", "tamper", "bootstrap-context", "bootstrap-pin", "unverified-record", "substituted-record", "wrong-record-source", "wrong-record-role"))
    parser.add_argument("--runtime-check", action="store_true")
    parser.add_argument("--expected-source-digest")
    parser.add_argument("--peer-writer-ip")
    parser.add_argument("--peer-follower-ip")
    parser.add_argument("--peer-port", type=int)
    parser.add_argument("--ack-encrypted-private-route", action="store_true")
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        endpoints = _configured_peers(args)
        if endpoints is not None and (args.ack_private_lan or not any((
                args.paired_coordinate, args.offline_pair_role, args.print_launcher,
                args.offline_coordinator, args.runtime_check))):
            raise PersistentNodeError("peer_configuration_mode_invalid")
        if authentication is not None and not args.lan:
            raise PersistentNodeError("lan_input_mode_required")
        if args.paired_coordinate or args.offline_pair_role or args.print_launcher:
            if (sum((args.paired_coordinate, args.offline_pair_role, args.print_launcher)) != 1
                    or args.coordinate or args.offline_coordinator or args.runtime_check or args.lan
                    or args.source_inventory or args.offline_auth_handoff or args.handoff_case is not None
                    or args.coordinator_case is not None or authentication is not None
                    or (not args.print_launcher and args.launcher_platform is not None)):
                raise PersistentNodeError("coordinator_mode_conflict")
            if args.print_launcher:
                sys.stdout.write(pairing_launcher(args) + "\n")
                return 0
            return paired_coordinator_main(args)
        if args.report_dir is not None or args.offline_fd is not None or args.launcher_platform is not None:
            raise PersistentNodeError("pair_mode_required")
        if args.coordinate or args.offline_coordinator or args.runtime_check:
            if (sum((args.coordinate, args.offline_coordinator, args.runtime_check)) != 1
                    or args.lan or args.source_inventory or args.offline_auth_handoff
                    or args.handoff_case is not None or authentication is not None):
                raise PersistentNodeError("coordinator_mode_conflict")
            if args.coordinate:
                if args.coordinator_case is not None:
                    raise PersistentNodeError("coordinator_mode_conflict")
                return coordinator_main(args)
            if (args.role != "parent" or args.phase is not None or args.data_dir is not None
                    or args.port is not None or args.session_id is not None or args.session_start is not None
                    or args.ack_private_lan or (args.runtime_check and args.coordinator_case is not None)
                    or (args.offline_coordinator and args.expected_source_digest is not None)):
                raise PersistentNodeError("coordinator_arguments_invalid")
            if args.runtime_check:
                result = coordinator_runtime_check(args.expected_source_digest)
                if endpoints is not None:
                    result.update(peer_configuration=endpoints, encrypted_route_verified=False)
                _emit(result)
            else:
                _emit(execute_offline_coordinator(args.coordinator_case or "valid", endpoints=endpoints))
            return 0
        if args.coordinator_case is not None or args.expected_source_digest is not None:
            raise PersistentNodeError("coordinator_mode_required")
        if args.offline_auth_handoff:
            if (args.lan or args.source_inventory or args.role != "parent" or args.phase is not None
                    or args.data_dir is not None or args.port is not None or args.session_id is not None
                    or args.session_start is not None or args.ack_private_lan or authentication is not None):
                raise PersistentNodeError("offline_handoff_arguments_invalid")
            _emit(execute_offline_auth_handoff(args.handoff_case or "valid"))
            return 0
        if args.handoff_case is not None:
            raise PersistentNodeError("offline_handoff_mode_required")
        if args.source_inventory:
            _emit(lan_source_inventory())
            return 0
        if args.lan:
            try:
                return lan_main(args, authentication=authentication)
            except (OSError, ValueError, EOFError):
                raise PersistentNodeError("lan_io_or_persisted_state_failure") from None
        if args.session_id is not None or args.session_start is not None or args.ack_private_lan:
            raise PersistentNodeError("lan_options_require_explicit_lan_mode")
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
    finally:
        if isinstance(authentication, HandoffMaterial):
            authentication.close()
    _emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
