# SPDX-License-Identifier: Apache-2.0
import ast
import asyncio
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import disposable_offline_transfer_demo as demo
from coin.tx_validation import (
    L28_EMISSION_CEILING,
    L28_HALVING_INTERVAL,
    L28_HISTORICAL_LAST_ENTRY,
    L28_HISTORICAL_MINED,
    L28_MAX_SUPPLY,
    L28_NEXT_HEIGHT_AFTER_CHECKPOINT,
    compute_tx_id,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/disposable_offline_transfer_demo.py"
HISTORICAL_PATHS = (
    ROOT / "PROTOCOL.md",
    ROOT / "coin/tx_validation.py",
    ROOT / "coin/ledger.py",
    ROOT / "coin/historical_continuity_verifier.py",
    ROOT / "docs/l28_historical_continuity_manifest_v0.1.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_happy_path_moves_100_0_to_72_28_and_rejects_failures():
    result = demo.execute_disposable_offline_transfer()
    assert result == {
        "demo_profile": demo.DEMO_PROFILE,
        "transfer_amount": 28,
        "alice_balance_before": 100,
        "bob_balance_before": 0,
        "canonical_validation": "PASS",
        "ledger_transition": "PASS",
        "alice_balance_after": 72,
        "bob_balance_after": 28,
        "invalid_signature_rejected": True,
        "replay_rejected": True,
        "invalid_state_rejected": True,
        "canonical_history_touched": False,
        "public_network_used": False,
        "production_keys_used": False,
    }


def test_canonical_validator_and_ledger_are_actually_called(monkeypatch):
    calls = {"validate": 0, "ledger": 0}
    original_validate = demo.validate_transaction
    original_apply = demo.apply_transfer

    def validate_wrapper(*args, **kwargs):
        calls["validate"] += 1
        return original_validate(*args, **kwargs)

    async def apply_wrapper(ledger, tx):
        calls["ledger"] += 1
        return await original_apply(ledger, tx)

    monkeypatch.setattr(demo, "validate_transaction", validate_wrapper)
    monkeypatch.setattr(demo, "apply_transfer", apply_wrapper)
    result = demo.execute_disposable_offline_transfer()
    assert result["canonical_validation"] == "PASS"
    assert result["ledger_transition"] == "PASS"
    assert calls["validate"] >= 1
    assert calls["ledger"] >= 1


def test_valid_signature_passes_and_invalid_signature_is_bad_signature(tmp_path):
    alice = Ed25519PrivateKey.generate()
    bob = Ed25519PrivateKey.generate()
    wrong = Ed25519PrivateKey.generate()
    bob_id = demo.public_identity(demo._public_key_hex(bob))
    ledger = demo._open_ledger(str(tmp_path))
    alice_id = demo.public_identity(demo._public_key_hex(alice))
    ledger.balances[alice_id] = 100
    ledger.balances[bob_id] = 0
    transfer = demo.build_signed_transfer(
        alice, receiver=bob_id, amount=28, timestamp=demo.DEMO_TIMESTAMP, nonce=1
    )
    ok, tx_id, reason = demo.classify_transfer(ledger, transfer)
    assert ok is True and reason == "ok" and tx_id == transfer["id"]
    assert asyncio.run(demo.apply_transfer(ledger, transfer)) is True
    forged = demo.build_signed_transfer(
        wrong, receiver=bob_id, amount=28, timestamp=demo.DEMO_TIMESTAMP, nonce=2
    )
    forged["sender"] = alice_id
    forged["sender_public_key"] = transfer["sender_public_key"]
    forged["id"] = compute_tx_id(forged)
    bad_ok, _bad_id, bad_reason = demo.classify_transfer(ledger, forged)
    assert bad_ok is False and bad_reason == "bad_signature"
    assert asyncio.run(demo.apply_transfer(ledger, forged)) is False
    assert (ledger.get_balance(alice_id), ledger.get_balance(bob_id)) == (72, 28)


def test_replay_insufficient_and_malformed_do_not_mutate_balances(tmp_path):
    alice = Ed25519PrivateKey.generate()
    bob = Ed25519PrivateKey.generate()
    ledger = demo._open_ledger(str(tmp_path))
    alice_id = demo.public_identity(demo._public_key_hex(alice))
    bob_id = demo.public_identity(demo._public_key_hex(bob))
    ledger.balances[alice_id] = 100
    transfer = demo.build_signed_transfer(
        alice, receiver=bob_id, amount=28, timestamp=demo.DEMO_TIMESTAMP, nonce=7
    )
    assert asyncio.run(demo.apply_transfer(ledger, transfer)) is True
    replay_ok, _replay_id, replay_reason = demo.classify_transfer(ledger, transfer)
    assert replay_ok is False and replay_reason == "replay"
    assert asyncio.run(demo.apply_transfer(ledger, transfer)) is False
    insufficient = demo.build_signed_transfer(
        alice, receiver=bob_id, amount=101, timestamp=demo.DEMO_TIMESTAMP, nonce=8
    )
    insufficient_ok, _insufficient_id, insufficient_reason = demo.classify_transfer(
        ledger, insufficient
    )
    assert insufficient_ok is False and insufficient_reason == "insufficient_balance"
    assert asyncio.run(demo.apply_transfer(ledger, insufficient)) is False
    malformed = {
        "sender": alice_id,
        "receiver": bob_id,
        "amount": "28",
        "timestamp": demo.DEMO_TIMESTAMP,
    }
    before = deepcopy(malformed)
    malformed_ok, _malformed_id, malformed_reason = demo.classify_transfer(ledger, malformed)
    assert malformed == before
    assert malformed_ok is False and malformed_reason == "amount_not_int"
    assert asyncio.run(demo.apply_transfer(ledger, malformed)) is False
    assert (ledger.get_balance(alice_id), ledger.get_balance(bob_id)) == (72, 28)
    assert ledger.issued_supply == 0
    assert ledger.mint_height == 0


def test_transaction_id_is_stable_and_preimage_excludes_signature_and_id():
    alice = Ed25519PrivateKey.generate()
    bob = Ed25519PrivateKey.generate()
    bob_id = demo.public_identity(demo._public_key_hex(bob))
    transfer = demo.build_signed_transfer(
        alice, receiver=bob_id, amount=28, timestamp=demo.DEMO_TIMESTAMP, nonce=4
    )
    assert transfer["id"] == compute_tx_id(transfer) == compute_tx_id(deepcopy(transfer))
    preimage = demo.signable_transfer_bytes(transfer)
    assert b"signature" not in preimage
    assert transfer["id"].encode("ascii") not in preimage
    changed = dict(transfer)
    changed["amount"] = 29
    changed.pop("id")
    assert demo.signable_transfer_bytes(changed) != preimage


def test_input_transaction_is_not_silently_repaired(tmp_path):
    alice = Ed25519PrivateKey.generate()
    bob = Ed25519PrivateKey.generate()
    ledger = demo._open_ledger(str(tmp_path))
    alice_id = demo.public_identity(demo._public_key_hex(alice))
    bob_id = demo.public_identity(demo._public_key_hex(bob))
    ledger.balances[alice_id] = 100
    transfer = demo.build_signed_transfer(
        alice, receiver=bob_id, amount=28, timestamp=demo.DEMO_TIMESTAMP, nonce=5
    )
    broken = dict(transfer)
    broken["id"] = "not-the-canonical-id"
    before = deepcopy(broken)
    ok, _tx_id, reason = demo.classify_transfer(ledger, broken)
    assert broken == before
    assert ok is False and reason == "tx_id_mismatch"
    assert asyncio.run(demo.apply_transfer(ledger, broken)) is False
    assert ledger.get_balance(alice_id) == 100


def test_private_material_is_absent_from_result_and_cli(capsys):
    result = demo.execute_disposable_offline_transfer()
    encoded = json.dumps(result)
    assert "private_key" not in encoded
    assert "seed" not in encoded
    assert "mnemonic" not in encoded
    assert "xprv" not in encoded
    assert demo.main([]) == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["alice_balance_after"] == 72
    assert payload["bob_balance_after"] == 28
    for forbidden in ("private_key", "privkey", "seed_phrase", "mnemonic", "xprv", "BEGIN PRIVATE"):
        assert forbidden not in output


def test_temp_ledger_is_disposable_and_historical_files_stay_untouched():
    before = {path: _sha256(path) for path in HISTORICAL_PATHS}
    data_dir = ROOT / "data" / "ledger"
    existed = data_dir.exists()
    demo.execute_disposable_offline_transfer()
    after = {path: _sha256(path) for path in HISTORICAL_PATHS}
    assert after == before
    assert data_dir.exists() is existed
    source = IMPL_PATH.read_text(encoding="utf-8")
    assert "TemporaryDirectory" in source
    assert "historical_continuity" not in source
    assert "genesis_state" not in source
    assert "issued_supply =" not in source


def test_protected_economics_remain_the_canonical_constants():
    demo.execute_disposable_offline_transfer()
    assert L28_MAX_SUPPLY == 28_000_000
    assert L28_EMISSION_CEILING == 11_130_000
    assert L28_HISTORICAL_MINED == 2_824_584
    assert L28_HISTORICAL_LAST_ENTRY == 100_877
    assert L28_NEXT_HEIGHT_AFTER_CHECKPOINT == 100_878
    assert L28_HALVING_INTERVAL == 210_000


def test_no_network_rpc_wallet_or_private_serialization():
    source = IMPL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                calls.add(func.attr)
            elif isinstance(func, ast.Name):
                calls.add(func.id)
    assert {
        "socket",
        "subprocess",
        "requests",
        "urllib",
        "http",
        "multiprocessing",
    }.isdisjoint(imports)
    assert "validate_transaction" in calls or "classify_transfer" in source
    assert "private_bytes" not in source
    assert "from_private_bytes" not in source
    assert "environ" not in source
    assert ".env" not in source
    assert {"private_bytes", "from_private_bytes", "connect", "Popen"}.isdisjoint(calls)
