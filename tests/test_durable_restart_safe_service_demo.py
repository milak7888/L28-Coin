# SPDX-License-Identifier: Apache-2.0
"""Restart-safe disposable payment runtime tests."""

from __future__ import annotations

import ast
import json
import socket
import sqlite3
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import coin.durable_restart_safe_service_demo as demo
from coin.disposable_offline_transfer_demo import DEMO_TIMESTAMP, build_signed_transfer, public_identity
from coin.disposable_testnet_identity import (
    BROADCAST_AUTHORIZED,
    MINING_AUTHORIZED,
    NETWORK_AUTHORIZED,
    RUNTIME_AUTHORIZED,
    SETTLEMENT_AUTHORIZED,
    SIGNING_AUTHORIZED,
    TESTNET_START_AUTHORIZED,
)
from coin.tx_validation import compute_tx_id
from coin.two_agent_service_transaction_demo import (
    PRICE_L28,
    DemoError,
    _perform_paid_service,
    build_payment_authorization,
    build_service_request,
    verify_service_receipt,
    verify_service_result,
)


INPUT_TEXT = "L28 enables machine payments between autonomous systems."


def _package(provider: demo.DurableProvider, payer: Ed25519PrivateKey, nonce: int, **changes: object) -> dict:
    request = build_service_request(payer, provider_identity=provider.identity, input_text=INPUT_TEXT)
    quote = provider.quote_for(request)
    receiver = changes.get("receiver", provider.identity)
    amount = changes.get("amount", PRICE_L28)
    signer = changes.get("signer", payer)
    payment_tx = build_signed_transfer(
        signer,
        receiver=str(receiver),
        amount=int(amount),
        timestamp=DEMO_TIMESTAMP,
        nonce=nonce,
    )
    if changes.get("bad_signature"):
        payment_tx["signature"] = "00" * 64
        payment_tx["id"] = compute_tx_id(payment_tx)
    authorization = build_payment_authorization(payer, request=request, quote=quote, payment_tx=payment_tx)
    return {
        "request": request,
        "quote": quote,
        "payment_tx": payment_tx,
        "payment_authorization": authorization,
    }


def test_identity_flags_stay_false() -> None:
    binding = demo.production_entry_binding()
    assert binding["network_id"] == "L28-DISPOSABLE-PRODUCTION-ENTRY001"
    assert all(
        flag is False
        for flag in (
            RUNTIME_AUTHORIZED,
            NETWORK_AUTHORIZED,
            TESTNET_START_AUTHORIZED,
            SIGNING_AUTHORIZED,
            MINING_AUTHORIZED,
            BROADCAST_AUTHORIZED,
            SETTLEMENT_AUTHORIZED,
        )
    )


def test_first_payment_applies_once_and_persists_tx_id(tmp_path: Path) -> None:
    payer = Ed25519PrivateKey.generate()
    provider = demo.DurableProvider(tmp_path)
    try:
        package = _package(provider, payer, 100)
        first = provider.handle_payment(package)
        second = provider.handle_payment(package)
    finally:
        provider.close()
    assert first["ok"] is True
    evidence = first["evidence"]
    assert evidence["canonical_validation"] == "PASS"
    assert evidence["payment_applied"] is True
    assert (evidence["requester_balance_before"], evidence["provider_balance_before"]) == (100, 0)
    assert (evidence["requester_balance_after"], evidence["provider_balance_after"]) == (72, 28)
    assert evidence["service_executed"] is True
    assert evidence["result_verified"] is True
    assert evidence["receipt_verified"] is True
    assert evidence["durable_state_reopened"] is False
    assert evidence["canonical_history_touched"] is False
    assert second["ok"] is False
    assert second["error"] == "replay"
    assert second["evidence"]["payment_applied"] is False
    assert second["evidence"]["requester_balance_after"] == 72
    assert second["evidence"]["provider_balance_after"] == 28
    reopened = demo.DurableStore(tmp_path)
    reopened.open()
    try:
        snapshot = reopened.snapshot()
    finally:
        reopened.close()
    assert evidence["payment_tx_id"] in snapshot["accepted"]
    assert reopened.reopened is True
    assert snapshot["restart_generation"] == 2
    assert snapshot["state_version"] == 1


def test_canonical_validator_and_work_follow_durable_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    work: list[bool] = []
    real_classify = demo.classify_transfer
    real_work = demo._perform_paid_service

    def classify(ledger, payment_tx):
        calls.append("classify")
        return real_classify(ledger, payment_tx)

    def perform(text: str, *, payment_verified: bool):
        work.append(payment_verified)
        return real_work(text, payment_verified=payment_verified)

    monkeypatch.setattr(demo, "classify_transfer", classify)
    monkeypatch.setattr(demo, "_perform_paid_service", perform)
    payer = Ed25519PrivateKey.generate()
    provider = demo.DurableProvider(tmp_path)
    try:
        package = _package(provider, payer, 100)
        with pytest.raises(demo.DurableRuntimeError) as interrupted:
            provider.handle_payment(package, fault="before_commit")
        assert interrupted.value.code == "interrupted_before_commit"
        assert work == []
        assert provider.store.snapshot()["accepted"] == {}
        result = provider.handle_payment(package)
    finally:
        provider.close()
    assert calls
    assert work == [True]
    assert result["ok"] is True
    with pytest.raises(DemoError) as unpaid:
        _perform_paid_service(INPUT_TEXT, payment_verified=False)
    assert unpaid.value.code == "payment_not_verified"


def test_crash_after_commit_cannot_reapply_or_repeat_work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    work: list[bool] = []
    real_work = demo._perform_paid_service

    def perform(text: str, *, payment_verified: bool):
        work.append(payment_verified)
        return real_work(text, payment_verified=payment_verified)

    monkeypatch.setattr(demo, "_perform_paid_service", perform)
    payer = Ed25519PrivateKey.generate()
    provider = demo.DurableProvider(tmp_path)
    package = _package(provider, payer, 100)
    with pytest.raises(demo.DurableRuntimeError) as interrupted:
        provider.handle_payment(package, fault="after_commit")
    provider.close()
    assert interrupted.value.code == "interrupted_after_commit"
    assert work == []
    restarted = demo.DurableProvider(tmp_path)
    try:
        replay = restarted.handle_payment(package)
        assert replay["error"] == "replay"
        assert replay["evidence"]["service_executed"] is False
        assert replay["evidence"]["requester_balance_after"] == 72
        assert replay["evidence"]["provider_balance_after"] == 28
        assert restarted.store.snapshot()["accepted"][package["payment_tx"]["id"]]["service_executed"] is False
    finally:
        restarted.close()
    assert work == []


def test_corrupt_and_missing_state_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    store = demo.DurableStore(missing)
    store.open()
    store.close()
    store.db_path.unlink()
    with pytest.raises(demo.DurableRuntimeError) as missing_error:
        demo.DurableStore(missing).open()
    assert missing_error.value.code == "missing_state"

    corrupt = tmp_path / "corrupt"
    created = demo.DurableStore(corrupt)
    created.open()
    created.close()
    created.db_path.write_bytes(b"this is not a sqlite database")
    with pytest.raises(demo.DurableRuntimeError) as corrupt_error:
        demo.DurableStore(corrupt).open()
    assert corrupt_error.value.code == "corrupt_state"


def test_state_version_cannot_move_backward(tmp_path: Path) -> None:
    payer = Ed25519PrivateKey.generate()
    provider = demo.DurableProvider(tmp_path)
    try:
        provider.handle_payment(_package(provider, payer, 100))
        with pytest.raises(sqlite3.IntegrityError):
            provider.store.connection.execute("UPDATE meta SET state_version = state_version - 1")
    finally:
        provider.close()


def test_invalid_signature_amount_and_parties_are_rejected(tmp_path: Path) -> None:
    payer = Ed25519PrivateKey.generate()
    other = Ed25519PrivateKey.generate()
    provider = demo.DurableProvider(tmp_path)
    try:
        with pytest.raises(demo.DurableRuntimeError) as bad_signature:
            provider.handle_payment(_package(provider, payer, 100, bad_signature=True))
        assert bad_signature.value.code == "bad_signature"
        with pytest.raises(demo.DurableRuntimeError) as wrong_amount:
            provider.handle_payment(_package(provider, payer, 101, amount=27))
        assert wrong_amount.value.code == "wrong_amount"
        wrong_receiver = public_identity(demo._public_key_hex(other))
        with pytest.raises(DemoError) as wrong_party:
            provider.handle_payment(_package(provider, payer, 102, receiver=wrong_receiver))
        assert wrong_party.value.code == "payment_binding_invalid"
        other_tx = build_signed_transfer(
            other,
            receiver=provider.identity,
            amount=PRICE_L28,
            timestamp=DEMO_TIMESTAMP,
            nonce=103,
        )
        request = build_service_request(payer, provider_identity=provider.identity, input_text=INPUT_TEXT)
        quote = provider.quote_for(request)
        authorization = build_payment_authorization(payer, request=request, quote=quote, payment_tx=other_tx)
        with pytest.raises(DemoError) as wrong_payer:
            provider.handle_payment(
                {
                    "request": request,
                    "quote": quote,
                    "payment_tx": other_tx,
                    "payment_authorization": authorization,
                }
            )
        assert wrong_payer.value.code == "payment_binding_invalid"
        assert provider.store.snapshot()["accepted"] == {}
        assert provider.store.snapshot()["opening_seeded"] is False
    finally:
        provider.close()


def test_tampered_receipt_fails_its_verifier(tmp_path: Path) -> None:
    payer = Ed25519PrivateKey.generate()
    provider = demo.DurableProvider(tmp_path)
    try:
        package = _package(provider, payer, 100)
        result = provider.handle_payment(package)
    finally:
        provider.close()
    tampered = dict(result["receipt"])
    tampered["signature"] = "ab" * 64
    with pytest.raises(DemoError) as error:
        verify_service_receipt(
            tampered,
            request=package["request"],
            quote=package["quote"],
            service_result=result["service_result"],
            payment_tx_id=result["evidence"]["payment_tx_id"],
        )
    assert error.value.code in {"signature_invalid", "digest_mismatch"}
    tampered_result = dict(result["service_result"])
    tampered_result["output"] = {"character_count": 0}
    with pytest.raises(DemoError):
        verify_service_result(
            tampered_result,
            request=package["request"],
            quote=package["quote"],
            payment_tx_id=result["evidence"]["payment_tx_id"],
        )


def test_bounded_body_and_no_secret_or_history_paths(tmp_path: Path) -> None:
    provider = demo.DurableProvider(tmp_path)
    server, thread, _started = demo.start_provider(tmp_path / "http")
    try:
        with pytest.raises(DemoError) as bounded_input:
            build_service_request(Ed25519PrivateKey.generate(), provider_identity=provider.identity, input_text="x" * 5000)
        assert bounded_input.value.code == "input_invalid"
        connection = socket.create_connection((demo.LOOPBACK_HOST, server.server_address[1]), timeout=2)
        connection.settimeout(2)
        connection.sendall(
            (
                f"POST {demo.PAYMENT_PATH} HTTP/1.1\r\n"
                f"Host: {demo.LOOPBACK_HOST}\r\n"
                "Content-Length: 70000\r\n"
                "Connection: close\r\n\r\n"
            ).encode("ascii")
        )
        response = connection.recv(4096)
        connection.close()
        assert b"oversized_body" in response
        assert server.server_address[0] == demo.LOOPBACK_HOST
    finally:
        provider.close()
        demo.stop_provider(server, thread)
    source = Path(demo.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "environ" not in names and "environ" not in attributes
    assert "private_bytes" not in names and "private_bytes" not in attributes
    assert "from_private_bytes" not in names and "from_private_bytes" not in attributes
    assert "0.0.0.0" not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            assert all(keyword.arg != "shell" for keyword in node.keywords)
    state_bytes = b"".join(path.read_bytes() for path in tmp_path.rglob("*") if path.is_file())
    assert b"PRIVATE KEY" not in state_bytes
    assert b"2824584" not in state_bytes


def test_real_process_restart_rejects_replay_then_accepts_fresh_payment(tmp_path: Path) -> None:
    result = demo.execute_durable_restart_sequence(tmp_path, INPUT_TEXT)
    run1 = result["run1"]
    replay = result["run2_replay"]
    run3 = result["run3"]
    assert run1["payment_applied"] is True
    assert run1["canonical_validation"] == "PASS"
    assert (run1["requester_balance_before"], run1["provider_balance_before"]) == (100, 0)
    assert (run1["requester_balance_after"], run1["provider_balance_after"]) == (72, 28)
    assert run1["durable_state_reopened"] is False
    assert replay["durable_state_reopened"] is True
    assert replay["replay_rejected"] is True
    assert replay["payment_applied"] is False
    assert replay["service_executed"] is False
    assert (replay["requester_balance_after"], replay["provider_balance_after"]) == (72, 28)
    assert replay["payment_tx_id"] == run1["payment_tx_id"]
    assert run3["payment_applied"] is True
    assert run3["result_verified"] is True
    assert run3["receipt_verified"] is True
    assert run3["service_executed"] is True
    assert run3["payment_tx_id"] != run1["payment_tx_id"]
    assert run3["durable_balances"][run1["receiver"]] == 28
    assert result["production_signing"] is False
    assert result["canonical_broadcast_used"] is False
    assert result["production_settlement"] is False
    assert result["canonical_history_touched"] is False
    encoded = json.dumps(result)
    assert "private_bytes" not in encoded
