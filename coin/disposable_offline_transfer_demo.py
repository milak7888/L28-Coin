# SPDX-License-Identifier: Apache-2.0
"""Disposable offline L28 transfer between two local test participants.

Operator authorization for this slice is test-only and in-memory:
Ed25519PrivateKey.generate(), one PureEd25519 signature, canonical
validation, and a TemporaryDirectory ledger. It does not authorize
production keys, wallets, seeds, import, backup, networking, broadcast,
mining, or settlement.

Private keys stay function-local. They are never returned, printed,
serialized, or loaded from disk.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import tempfile
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from coin.ledger import BlocklessLedger
from coin.tx_validation import (
    L28_EMISSION_CEILING,
    L28_HALVING_INTERVAL,
    L28_HISTORICAL_LAST_ENTRY,
    L28_HISTORICAL_MINED,
    L28_MAX_SUPPLY,
    L28_NEXT_HEIGHT_AFTER_CHECKPOINT,
    TxPolicy,
    compute_tx_id,
    validate_transaction,
)


DEMO_PROFILE = "l28-disposable-offline-transfer/v0.1"
NETWORK = "DISPOSABLE_OFFLINE"
SIGN_DOMAIN = b"L28-DISPOSABLE-OFFLINE-TRANSFER/v0.1\x00"
TRANSFER_AMOUNT = 28
ALICE_INITIAL_BALANCE = 100
BOB_INITIAL_BALANCE = 0
DEMO_TIMESTAMP = 1_700_000_000

SIGNABLE_FIELDS = (
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
PROTECTED_ECONOMICS = {
    "L28_MAX_SUPPLY": 28_000_000,
    "L28_EMISSION_CEILING": 11_130_000,
    "L28_HISTORICAL_MINED": 2_824_584,
    "L28_HISTORICAL_LAST_ENTRY": 100_877,
    "L28_NEXT_HEIGHT_AFTER_CHECKPOINT": 100_878,
    "L28_HALVING_INTERVAL": 210_000,
}


class DemoError(Exception):
    """Fail-closed disposable-demo error. The code is public and non-secret."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _exact_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool)


def _require_protected_economics() -> None:
    actual = {
        "L28_MAX_SUPPLY": L28_MAX_SUPPLY,
        "L28_EMISSION_CEILING": L28_EMISSION_CEILING,
        "L28_HISTORICAL_MINED": L28_HISTORICAL_MINED,
        "L28_HISTORICAL_LAST_ENTRY": L28_HISTORICAL_LAST_ENTRY,
        "L28_NEXT_HEIGHT_AFTER_CHECKPOINT": L28_NEXT_HEIGHT_AFTER_CHECKPOINT,
        "L28_HALVING_INTERVAL": L28_HALVING_INTERVAL,
    }
    if actual != PROTECTED_ECONOMICS:
        raise DemoError("protected_economics_changed")


def public_identity(public_key_hex: str) -> str:
    """Deterministic disposable participant id from a raw Ed25519 public key."""

    try:
        raw = bytes.fromhex(public_key_hex)
    except ValueError as exc:
        raise DemoError("malformed_public_key") from exc
    if len(raw) != 32:
        raise DemoError("malformed_public_key")
    return "l28disp_" + hashlib.sha256(raw).hexdigest()


def _public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes_raw().hex()


def signable_transfer_bytes(tx: Mapping[str, Any]) -> bytes:
    """Domain-separated preimage. Excludes signature and derived transaction id."""

    if not isinstance(tx, Mapping):
        raise DemoError("malformed_transfer")
    payload: dict[str, Any] = {}
    for field in SIGNABLE_FIELDS:
        if field not in tx:
            raise DemoError("malformed_transfer")
        payload[field] = tx[field]
    if payload["type"] != "transfer":
        raise DemoError("malformed_transfer")
    if payload["network"] != NETWORK or payload["profile"] != DEMO_PROFILE:
        raise DemoError("malformed_transfer")
    if not all(isinstance(payload[name], str) and payload[name] for name in (
        "sender",
        "receiver",
        "sender_public_key",
    )):
        raise DemoError("malformed_transfer")
    if not all(_exact_int(payload[name]) for name in ("amount", "timestamp", "nonce")):
        raise DemoError("malformed_transfer")
    if payload["sender"] != public_identity(payload["sender_public_key"]):
        raise DemoError("sender_key_mismatch")
    blob = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return SIGN_DOMAIN + blob


def verify_transfer_signature(tx: Mapping[str, Any]) -> bool:
    """Bind sender to the public key and verify PureEd25519. Fail closed."""

    try:
        if not isinstance(tx, dict):
            return False
        message = signable_transfer_bytes(tx)
        signature_hex = tx.get("signature")
        public_hex = tx.get("sender_public_key")
        if not isinstance(signature_hex, str) or not isinstance(public_hex, str):
            return False
        signature = bytes.fromhex(signature_hex)
        public_key = bytes.fromhex(public_hex)
        if len(signature) != 64 or len(public_key) != 32:
            return False
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
    except (DemoError, InvalidSignature, ValueError):
        return False
    return True


def build_signed_transfer(
    private_key: Ed25519PrivateKey,
    *,
    receiver: str,
    amount: int,
    timestamp: int,
    nonce: int,
) -> dict[str, Any]:
    """Sign a new transfer. The private key is not copied into the result."""

    public_hex = _public_key_hex(private_key)
    body = {
        "sender": public_identity(public_hex),
        "receiver": receiver,
        "sender_public_key": public_hex,
        "amount": amount,
        "timestamp": timestamp,
        "type": "transfer",
        "network": NETWORK,
        "profile": DEMO_PROFILE,
        "nonce": nonce,
    }
    signature = private_key.sign(signable_transfer_bytes(body)).hex()
    signed = dict(body)
    signed["signature"] = signature
    signed["id"] = compute_tx_id(signed)
    return signed


def _policy() -> TxPolicy:
    return TxPolicy(require_signatures=True)


def classify_transfer(
    ledger: BlocklessLedger,
    tx: dict[str, Any],
) -> tuple[bool, str, str]:
    """Canonical validation. Does not repair or mutate the input transaction."""

    if not isinstance(tx, dict):
        return False, "", "tx_not_dict"
    before = deepcopy(tx)
    outcome = validate_transaction(
        tx,
        policy=_policy(),
        current_balance_lookup=ledger._current_balance_lookup,
        seen_tx_lookup=ledger._seen_tx_lookup,
        verify_signature=verify_transfer_signature,
        now_ts=DEMO_TIMESTAMP,
    )
    if tx != before:
        raise DemoError("input_mutated")
    return outcome


async def apply_transfer(ledger: BlocklessLedger, tx: dict[str, Any]) -> bool:
    """Ledger transition through BlocklessLedger.add_transaction. No input repair."""

    before = deepcopy(tx)
    applied = await ledger.add_transaction(tx)
    if tx != before:
        raise DemoError("input_mutated")
    return bool(applied)


def _open_ledger(data_dir: str) -> BlocklessLedger:
    return BlocklessLedger(
        data_dir=data_dir,
        policy=_policy(),
        verify_signature=verify_transfer_signature,
        require_signatures=True,
    )


def _signed_by(private_key: Ed25519PrivateKey, body: Mapping[str, Any]) -> dict[str, Any]:
    """Attach a signature over the exact body. Does not alter unrelated fields."""

    signed = dict(body)
    signed["signature"] = private_key.sign(signable_transfer_bytes(signed)).hex()
    signed["id"] = compute_tx_id(signed)
    return signed


async def _run_scenario(
    ledger: BlocklessLedger,
    alice_key: Ed25519PrivateKey,
    wrong_key: Ed25519PrivateKey,
    alice: str,
    bob: str,
) -> tuple[int, int, int, int]:
    alice_before = ledger.get_balance(alice)
    bob_before = ledger.get_balance(bob)
    transfer = build_signed_transfer(
        alice_key,
        receiver=bob,
        amount=TRANSFER_AMOUNT,
        timestamp=DEMO_TIMESTAMP,
        nonce=1,
    )
    if compute_tx_id(transfer) != transfer["id"]:
        raise DemoError("tx_id_unstable")

    ok, _tx_id, reason = classify_transfer(ledger, transfer)
    if not ok or reason != "ok":
        raise DemoError("canonical_validation_failed")
    if not await apply_transfer(ledger, transfer):
        raise DemoError("ledger_transition_failed")

    alice_after = ledger.get_balance(alice)
    bob_after = ledger.get_balance(bob)
    if (alice_before, bob_before, alice_after, bob_after) != (100, 0, 72, 28):
        raise DemoError("balance_transition_mismatch")

    invalid_signature = _signed_by(
        wrong_key,
        {
            "sender": alice,
            "receiver": bob,
            "sender_public_key": transfer["sender_public_key"],
            "amount": TRANSFER_AMOUNT,
            "timestamp": DEMO_TIMESTAMP,
            "type": "transfer",
            "network": NETWORK,
            "profile": DEMO_PROFILE,
            "nonce": 2,
        },
    )
    bad_ok, _bad_id, bad_reason = classify_transfer(ledger, invalid_signature)
    if bad_ok or bad_reason != "bad_signature" or await apply_transfer(ledger, invalid_signature):
        raise DemoError("invalid_signature_not_rejected")
    if (ledger.get_balance(alice), ledger.get_balance(bob)) != (72, 28):
        raise DemoError("rejected_transfer_mutated_balance")

    replay_ok, _replay_id, replay_reason = classify_transfer(ledger, transfer)
    if replay_ok or replay_reason != "replay" or await apply_transfer(ledger, transfer):
        raise DemoError("replay_not_rejected")
    if (ledger.get_balance(alice), ledger.get_balance(bob)) != (72, 28):
        raise DemoError("rejected_transfer_mutated_balance")

    insufficient = build_signed_transfer(
        alice_key,
        receiver=bob,
        amount=101,
        timestamp=DEMO_TIMESTAMP,
        nonce=3,
    )
    insufficient_ok, _insufficient_id, insufficient_reason = classify_transfer(ledger, insufficient)
    malformed = {
        "sender": alice,
        "receiver": bob,
        "amount": "28",
        "timestamp": DEMO_TIMESTAMP,
        "type": "transfer",
        "signature": transfer["signature"],
    }
    malformed_before = deepcopy(malformed)
    malformed_ok, _malformed_id, malformed_reason = classify_transfer(ledger, malformed)
    if malformed != malformed_before:
        raise DemoError("input_mutated")
    if (
        insufficient_ok
        or insufficient_reason != "insufficient_balance"
        or await apply_transfer(ledger, insufficient)
        or malformed_ok
        or malformed_reason != "amount_not_int"
        or await apply_transfer(ledger, malformed)
    ):
        raise DemoError("invalid_state_not_rejected")
    if (ledger.get_balance(alice), ledger.get_balance(bob)) != (72, 28):
        raise DemoError("rejected_transfer_mutated_balance")
    if ledger.issued_supply != 0 or ledger.mint_height != 0:
        raise DemoError("canonical_issuance_mutated")
    return alice_before, bob_before, alice_after, bob_after


def execute_disposable_offline_transfer() -> dict[str, Any]:
    """Run Alice → validate → ledger → Bob, then the required rejection cases."""

    _require_protected_economics()
    alice_key = Ed25519PrivateKey.generate()
    bob_key = Ed25519PrivateKey.generate()
    wrong_key = Ed25519PrivateKey.generate()
    alice = public_identity(_public_key_hex(alice_key))
    bob = public_identity(_public_key_hex(bob_key))

    with tempfile.TemporaryDirectory(prefix="l28-disposable-offline-transfer-") as data_dir:
        ledger = _open_ledger(data_dir)
        if ledger.issued_supply != 0 or ledger.mint_height != 0:
            raise DemoError("canonical_issuance_mutated")
        ledger.balances[alice] = ALICE_INITIAL_BALANCE
        ledger.balances[bob] = BOB_INITIAL_BALANCE
        alice_before, bob_before, alice_after, bob_after = asyncio.run(
            _run_scenario(ledger, alice_key, wrong_key, alice, bob)
        )

    _require_protected_economics()
    del alice_key, bob_key, wrong_key
    return {
        "demo_profile": DEMO_PROFILE,
        "transfer_amount": TRANSFER_AMOUNT,
        "alice_balance_before": alice_before,
        "bob_balance_before": bob_before,
        "canonical_validation": "PASS",
        "ledger_transition": "PASS",
        "alice_balance_after": alice_after,
        "bob_balance_after": bob_after,
        "invalid_signature_rejected": True,
        "replay_rejected": True,
        "invalid_state_rejected": True,
        "canonical_history_touched": False,
        "public_network_used": False,
        "production_keys_used": False,
    }


def main(argv: list[str] | None = None) -> int:
    """Runnable product: python -m coin.disposable_offline_transfer_demo"""

    if argv is None:
        argv = sys.argv[1:]
    if argv:
        sys.stderr.write("usage: python -m coin.disposable_offline_transfer_demo\n")
        return 2
    try:
        result = execute_disposable_offline_transfer()
    except DemoError as exc:
        sys.stderr.write(exc.code + "\n")
        return 1
    sys.stdout.write(
        json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
