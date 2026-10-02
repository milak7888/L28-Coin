# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
import os
import socket
import struct
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import isolated_local_network_service_demo as net
from coin.disposable_offline_transfer_demo import (
    ALICE_INITIAL_BALANCE,
    BOB_INITIAL_BALANCE,
    DEMO_TIMESTAMP,
    _open_ledger,
    apply_transfer,
    build_signed_transfer,
    classify_transfer,
    public_identity,
)
from coin.two_agent_service_transaction_demo import (
    PAYMENT_AUTH_BODY_FIELDS,
    PAYMENT_AUTH_SIGN_DOMAIN,
    PRICE_L28,
    _artifact_body,
    _digest,
    _perform_paid_service,
    _public_key_hex,
    _sign_domain,
    build_payment_authorization,
    build_service_quote,
    build_service_receipt,
    build_service_request,
    build_service_result,
    structured_text_analysis,
    verify_payment_intent_binding,
    verify_service_receipt,
    verify_service_result,
)
from coin.tx_validation import (
    L28_EMISSION_CEILING,
    L28_HALVING_INTERVAL,
    L28_HISTORICAL_LAST_ENTRY,
    L28_HISTORICAL_MINED,
    L28_MAX_SUPPLY,
    L28_NEXT_HEIGHT_AFTER_CHECKPOINT,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/isolated_local_network_service_demo.py"
HISTORICAL_PATHS = (
    ROOT / "PROTOCOL.md",
    ROOT / "coin/tx_validation.py",
    ROOT / "coin/ledger.py",
    ROOT / "docs/l28_historical_continuity_manifest_v0.1.json",
)
INPUT_TEXT = "L28 enables machine payments between autonomous systems."


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pair() -> tuple[socket.socket, socket.socket]:
    left, right = socket.socketpair()
    left.settimeout(2)
    right.settimeout(2)
    return left, right


def _parties():
    payer = Ed25519PrivateKey.generate()
    provider = Ed25519PrivateKey.generate()
    provider_identity = public_identity(_public_key_hex(provider))
    request = build_service_request(
        payer,
        provider_identity=provider_identity,
        input_text=INPUT_TEXT,
    )
    quote = build_service_quote(provider, request=request)
    payment = build_signed_transfer(
        payer,
        receiver=provider_identity,
        amount=PRICE_L28,
        timestamp=DEMO_TIMESTAMP,
        nonce=100,
    )
    authorization = build_payment_authorization(
        payer,
        request=request,
        quote=quote,
        payment_tx=payment,
    )
    return payer, provider, request, quote, payment, authorization


def test_frame_round_trip_and_strict_rejections():
    frame = net.encode_frame("provider_hello", 1, {
        "provider_identity": "abc",
        "provider_public_key": "ab" * 32,
    })
    body = frame[4:]
    decoded = net.decode_frame(body, expected_sequence=1)
    assert decoded["message_type"] == "provider_hello"
    assert decoded["sequence"] == 1
    with pytest.raises(net.NetworkDemoError, match="malformed_frame"):
        net.decode_frame(b"{", expected_sequence=1)
    with pytest.raises(net.NetworkDemoError, match="wrong_profile"):
        net.decode_frame(
            json.dumps({
                "profile": "other",
                "version": 1,
                "message_type": "provider_hello",
                "sequence": 1,
                "payload": {},
            }).encode(),
            expected_sequence=1,
        )
    with pytest.raises(net.NetworkDemoError, match="unknown_message_type"):
        net.decode_frame(
            json.dumps({
                "profile": net.DEMO_PROFILE,
                "version": 1,
                "message_type": "hello",
                "sequence": 1,
                "payload": {},
            }).encode(),
            expected_sequence=1,
        )
    with pytest.raises(net.NetworkDemoError, match="duplicate_sequence"):
        net.decode_frame(body, expected_sequence=2)
    future = json.dumps({
        "profile": net.DEMO_PROFILE,
        "version": 1,
        "message_type": "service_quote",
        "sequence": 3,
        "payload": {},
    }).encode()
    with pytest.raises(net.NetworkDemoError, match="wrong_sequence"):
        net.decode_frame(future, expected_sequence=1)
    oversized = dict(json.loads(body))
    oversized["extra"] = True
    with pytest.raises(net.NetworkDemoError, match="unexpected_field"):
        net.decode_frame(json.dumps(oversized).encode(), expected_sequence=1)
    with pytest.raises(net.NetworkDemoError, match="oversized_frame"):
        net.decode_frame(b"x" * (net.MAX_FRAME_BYTES + 1), expected_sequence=1)


def test_truncated_and_oversized_socket_frames_fail_closed():
    left, right = _pair()
    right.sendall(struct.pack(">I", 8) + b"{")
    right.shutdown(socket.SHUT_WR)
    with pytest.raises(net.NetworkDemoError, match="truncated_frame"):
        net.read_frame(left, expected_sequence=1)
    left.close()
    right.close()
    left, right = _pair()
    right.sendall(struct.pack(">I", net.MAX_FRAME_BYTES + 1))
    with pytest.raises(net.NetworkDemoError, match="oversized_frame"):
        net.read_frame(left, expected_sequence=1)
    left.close()
    right.close()
    left, right = _pair()
    right.close()
    with pytest.raises(net.NetworkDemoError, match="premature_eof"):
        net.read_frame(left, expected_sequence=1)
    left.close()


def test_non_loopback_configuration_is_rejected():
    for host in ("0.0.0.0", "10.0.0.8", "localhost", "::1"):
        with pytest.raises(net.NetworkDemoError, match="non_loopback_host"):
            net.require_loopback_host(host)
        with pytest.raises(net.NetworkDemoError, match="non_loopback_host"):
            net.open_provider_listener(host)
    listener = net.open_provider_listener(net.LOOPBACK_HOST)
    host, _port = listener.getsockname()
    listener.close()
    assert host == "127.0.0.1"


def test_wrong_provider_amount_party_and_quote_mismatch_are_rejected():
    _payer, provider, request, quote, payment, authorization = _parties()
    hello = {
        "provider_identity": "not-the-provider",
        "provider_public_key": _public_key_hex(provider),
    }
    with pytest.raises(net.NetworkDemoError, match="wrong_provider_identity"):
        net.verify_provider_hello(hello)
    wrong_payer = Ed25519PrivateKey.generate()
    wrong_tx = build_signed_transfer(
        wrong_payer,
        receiver=payment["receiver"],
        amount=PRICE_L28,
        timestamp=DEMO_TIMESTAMP,
        nonce=103,
    )
    with pytest.raises(Exception):
        verify_payment_intent_binding(
            request=request,
            quote=quote,
            payment_tx=wrong_tx,
            payment_authorization=authorization,
        )
    wrong_amount = build_signed_transfer(
        _payer,
        receiver=payment["receiver"],
        amount=PRICE_L28 - 1,
        timestamp=DEMO_TIMESTAMP,
        nonce=102,
    )
    wrong_amount_auth = build_payment_authorization(
        _payer,
        request=request,
        quote=quote,
        payment_tx=wrong_amount,
    )
    with pytest.raises(Exception):
        verify_payment_intent_binding(
            request=request,
            quote=quote,
            payment_tx=wrong_amount,
            payment_authorization=wrong_amount_auth,
        )
    other = Ed25519PrivateKey.generate()
    wrong_party = build_signed_transfer(
        _payer,
        receiver=public_identity(_public_key_hex(other)),
        amount=PRICE_L28,
        timestamp=DEMO_TIMESTAMP,
        nonce=104,
    )
    wrong_party_auth = build_payment_authorization(
        _payer,
        request=request,
        quote=quote,
        payment_tx=wrong_party,
    )
    with pytest.raises(Exception):
        verify_payment_intent_binding(
            request=request,
            quote=quote,
            payment_tx=wrong_party,
            payment_authorization=wrong_party_auth,
        )
    mismatched = dict(authorization)
    mismatched["quote_id"] = "00" * 32
    body = _artifact_body(mismatched, PAYMENT_AUTH_BODY_FIELDS)
    mismatched["authorization_id"] = _digest(body)
    mismatched["signature"] = _sign_domain(_payer, PAYMENT_AUTH_SIGN_DOMAIN, body)
    with pytest.raises(Exception):
        verify_payment_intent_binding(
            request=request,
            quote=quote,
            payment_tx=payment,
            payment_authorization=mismatched,
        )


def test_invalid_signature_and_replay_do_not_move_extra_balance(tmp_path):
    payer, _provider, _request, _quote, payment, _authorization = _parties()
    ledger = _open_ledger(str(tmp_path))
    ledger.balances[payment["sender"]] = ALICE_INITIAL_BALANCE
    ledger.balances[payment["receiver"]] = BOB_INITIAL_BALANCE
    invalid = deepcopy(payment)
    invalid["signature"] = "00" * 64
    invalid["id"] = __import__("coin.tx_validation", fromlist=["compute_tx_id"]).compute_tx_id(invalid)
    bad_ok, _bad_id, bad_reason = classify_transfer(ledger, invalid)
    assert bad_ok is False and bad_reason == "bad_signature"
    assert __import__("asyncio").run(apply_transfer(ledger, invalid)) is False
    assert (ledger.get_balance(payment["sender"]), ledger.get_balance(payment["receiver"])) == (100, 0)
    assert classify_transfer(ledger, payment)[0] is True
    assert __import__("asyncio").run(apply_transfer(ledger, payment)) is True
    replay_ok, _replay_id, replay_reason = classify_transfer(ledger, payment)
    assert replay_ok is False and replay_reason == "replay"
    assert __import__("asyncio").run(apply_transfer(ledger, payment)) is False
    assert (ledger.get_balance(payment["sender"]), ledger.get_balance(payment["receiver"])) == (72, 28)
    assert ledger.total_transactions == 1
    with pytest.raises(Exception, match="payment_not_verified"):
        _perform_paid_service(INPUT_TEXT, payment_verified=False)


def test_tampered_result_and_receipt_are_rejected():
    payer, provider, request, quote, payment, _authorization = _parties()
    output = structured_text_analysis(INPUT_TEXT)
    result = build_service_result(
        provider,
        request=request,
        quote=quote,
        payment_tx_id=payment["id"],
        output=output,
    )
    tampered = deepcopy(result)
    tampered["output"] = dict(tampered["output"])
    tampered["output"]["word_count"] = tampered["output"]["word_count"] + 1
    with pytest.raises(Exception):
        verify_service_result(
            tampered,
            request=request,
            quote=quote,
            payment_tx_id=payment["id"],
        )
    receipt = build_service_receipt(
        provider,
        request=request,
        quote=quote,
        service_result=result,
        payment_tx_id=payment["id"],
    )
    bad_receipt = deepcopy(receipt)
    bad_receipt["signature"] = "11" * 64
    with pytest.raises(Exception):
        verify_service_receipt(
            bad_receipt,
            request=request,
            quote=quote,
            service_result=result,
            payment_tx_id=payment["id"],
        )
    del payer


def test_failed_provider_process_exits_without_success():
    proc = subprocess.Popen(
        [sys.executable, "-m", "coin.isolated_local_network_service_demo", "--role", "provider"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    ready = json.loads(proc.stdout.readline())
    sock = socket.create_connection((ready["host"], ready["port"]), timeout=5)
    sock.sendall(struct.pack(">I", 4) + b"nope")
    sock.close()
    stdout, stderr = proc.communicate(timeout=10)
    assert proc.returncode not in (None, 0)
    assert proc.poll() is not None
    combined = stdout + stderr
    assert "canonical_validation" not in combined
    assert "receipt_verified" not in combined
    assert "PASS" not in combined


def test_network_product_moves_payment_and_terminates_children():
    before = {path: _sha256(path) for path in HISTORICAL_PATHS}
    result = net.execute_isolated_local_network_service(INPUT_TEXT)
    assert result["demo_profile"] == "l28-isolated-local-network-service/v0.1"
    assert result["agent_process_count"] == 2
    assert result["distinct_agent_processes"] is True
    assert result["agent_a_pid"] != result["agent_b_pid"]
    assert result["network_transport"] == "tcp_ipv4_loopback"
    assert result["provider_bound_host"] == "127.0.0.1"
    assert result["external_network_used"] is False
    for flag in (
        "provider_hello_crossed_network",
        "service_request_crossed_network",
        "service_quote_crossed_network",
        "payment_package_crossed_network",
        "service_result_package_crossed_network",
        "request_verified",
        "quote_verified",
        "payment_applied",
        "payment_verified",
        "service_executed",
        "service_result_verified",
        "receipt_created",
        "receipt_verified",
        "both_processes_terminal",
        "sockets_closed",
    ):
        assert result[flag] is True
    assert result["quoted_amount"] == 28
    assert result["canonical_validation"] == "PASS"
    assert result["agent_a_balance_before"] == 100
    assert result["agent_b_balance_before"] == 0
    assert result["agent_a_balance_after"] == 72
    assert result["agent_b_balance_after"] == 28
    assert result["service_output"] == structured_text_analysis(INPUT_TEXT)
    assert result["canonical_history_touched"] is False
    assert result["public_network_used"] is False
    assert result["production_keys_used"] is False
    assert result["production_settlement"] is False
    assert len(result["payment_tx_id"]) == 64
    for pid in (result["agent_a_pid"], result["agent_b_pid"]):
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    assert {path: _sha256(path) for path in HISTORICAL_PATHS} == before
    assert L28_MAX_SUPPLY == 28_000_000
    assert L28_EMISSION_CEILING == 11_130_000
    assert L28_HISTORICAL_MINED == 2_824_584
    assert L28_HISTORICAL_LAST_ENTRY == 100_877
    assert L28_NEXT_HEIGHT_AFTER_CHECKPOINT == 100_878
    assert L28_HALVING_INTERVAL == 210_000


def test_cli_prints_success_and_failure_does_not():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "coin.isolated_local_network_service_demo",
            "--input",
            INPUT_TEXT,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["canonical_validation"] == "PASS"
    assert payload["agent_a_balance_after"] == 72
    assert payload["agent_b_balance_after"] == 28
    assert "private_key" not in completed.stdout
    assert "mnemonic" not in completed.stdout
    failed = subprocess.run(
        [sys.executable, "-m", "coin.isolated_local_network_service_demo", "--input", ""],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert failed.returncode != 0
    assert "canonical_validation" not in failed.stdout
    assert "PASS" not in failed.stdout


def test_security_boundary_and_no_second_payment_engine():
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
    assert "socket" in imports
    assert "subprocess" in imports
    assert {"requests", "urllib", "http", "multiprocessing"}.isdisjoint(imports)
    assert "private_bytes" not in source
    assert "from_private_bytes" not in source
    assert "environ" not in source
    assert ".env" not in source
    assert "validate_transaction" not in source.split("classify_transfer")[0] or "def validate_transaction" not in source
    assert "def validate_transaction" not in source
    assert "def add_transaction" not in source
    assert "fork" not in source
    assert "reorg" not in source
    assert "shell" not in calls
    assert "0.0.0.0" not in source
    assert "Ed25519PrivateKey.generate" in source
