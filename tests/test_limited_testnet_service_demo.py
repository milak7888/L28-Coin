# SPDX-License-Identifier: Apache-2.0
import ast
import asyncio
import json
import socket
import struct
from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import limited_testnet_service_demo as demo
from coin.disposable_offline_transfer_demo import (
    DEMO_TIMESTAMP,
    _open_ledger,
    build_signed_transfer,
    classify_transfer,
    public_identity,
)
from coin.disposable_testnet_identity import (
    BROADCAST_AUTHORIZED,
    MINING_AUTHORIZED,
    NETWORK_AUTHORIZED,
    RUNTIME_AUTHORIZED,
    SETTLEMENT_AUTHORIZED,
    SIGNING_AUTHORIZED,
    TESTNET_START_AUTHORIZED,
)
from coin.two_agent_service_transaction_demo import (
    PRICE_L28,
    _perform_paid_service,
    _public_key_hex,
    build_payment_authorization,
    build_service_quote,
    build_service_receipt,
    build_service_request,
    build_service_result,
    structured_text_analysis,
    verify_service_receipt,
    verify_service_result,
)
from coin.tx_validation import compute_tx_id


IMPL_PATH = Path(__file__).resolve().parents[1] / "coin/limited_testnet_service_demo.py"
INPUT_TEXT = "L28 enables machine payments between autonomous systems."


def _binding():
    return demo.limited_testnet_binding()


def _parties():
    payer = Ed25519PrivateKey.generate()
    provider = Ed25519PrivateKey.generate()
    provider_identity = public_identity(_public_key_hex(provider))
    request = build_service_request(payer, provider_identity=provider_identity, input_text=INPUT_TEXT)
    quote = build_service_quote(provider, request=request)
    payment = build_signed_transfer(
        payer,
        receiver=provider_identity,
        amount=PRICE_L28,
        timestamp=DEMO_TIMESTAMP,
        nonce=100,
    )
    authorization = build_payment_authorization(payer, request=request, quote=quote, payment_tx=payment)
    return payer, provider, request, quote, payment, authorization


def test_rfc1918_validation_rejects_loopback_public_and_unspecified():
    assert demo.classify_private_ipv4("10.1.2.3") == "10.1.2.3"
    assert demo.classify_private_ipv4("172.16.5.5") == "172.16.5.5"
    assert demo.classify_private_ipv4("192.168.1.108") == "192.168.1.108"
    for host, code in (
        ("127.0.0.1", "loopback_rejected"),
        ("127.0.0.2", "loopback_rejected"),
        ("0.0.0.0", "unspecified_address_rejected"),
        ("8.8.8.8", "public_ip_rejected"),
        ("172.32.0.1", "public_ip_rejected"),
        ("169.254.1.1", "public_ip_rejected"),
        ("224.0.0.1", "public_ip_rejected"),
        ("localhost", "public_ip_rejected"),
    ):
        with pytest.raises(demo.LimitedTestnetError, match=code):
            demo.classify_private_ipv4(host)
    with pytest.raises(demo.LimitedTestnetError, match="loopback_rejected"):
        demo.open_provider_listener("127.0.0.1")
    with pytest.raises(demo.LimitedTestnetError, match="unspecified_address_rejected"):
        demo.open_provider_listener("0.0.0.0")
    with pytest.raises(demo.LimitedTestnetError, match="public_ip_rejected"):
        demo.open_provider_listener("1.1.1.1")


def test_distinct_allowlist_and_single_endpoint_blocker():
    left, right = demo.require_distinct_endpoints("10.0.0.2", "10.0.0.3")
    assert left != right
    with pytest.raises(demo.LimitedTestnetError, match=demo.ENDPOINT_BLOCKER):
        demo.require_distinct_endpoints("192.168.0.2", "192.168.0.2")
    with pytest.raises(demo.LimitedTestnetError, match="peer_not_allowlisted"):
        demo.enforce_allowlisted_peer("10.0.0.4", "10.0.0.5")
    assert demo.enforce_allowlisted_peer("10.1.1.1", "10.1.1.1") == "10.1.1.1"
    with pytest.raises(demo.LimitedTestnetError, match=demo.ENDPOINT_BLOCKER):
        demo.select_distinct_endpoints(["127.0.0.1", "192.168.1.108", "8.8.8.8"])
    chosen = demo.select_distinct_endpoints(["127.0.0.1", "10.0.0.8", "192.168.9.9"])
    assert chosen == ("10.0.0.8", "192.168.9.9")


def test_network_binding_and_frame_order():
    binding = _binding()
    assert binding["network_id"] == "L28-DISPOSABLE-LIMITED001"
    assert binding["data_dir_tag"] == "l28-disposable-testnet:limited001"
    frame = demo.encode_frame("provider_hello", 1, {"provider_identity": "a", "provider_public_key": "ab" * 32}, binding)
    decoded = demo.decode_frame(frame[4:], expected_sequence=1, binding=binding)
    assert decoded["network_id"] == binding["network_id"]
    assert decoded["genesis_hash"] == binding["genesis_hash"]
    assert decoded["config_hash"] == binding["config_hash"]
    foreign = json.loads(frame[4:])
    foreign["network_id"] = "L28-DISPOSABLE-OTHER001"
    with pytest.raises(demo.LimitedTestnetError, match="wrong_network"):
        demo.decode_frame(json.dumps(foreign).encode(), expected_sequence=1, binding=binding)
    foreign["network_id"] = binding["network_id"]
    foreign["genesis_hash"] = "00" * 32
    with pytest.raises(demo.LimitedTestnetError, match="wrong_network_binding"):
        demo.decode_frame(json.dumps(foreign).encode(), expected_sequence=1, binding=binding)
    with pytest.raises(demo.LimitedTestnetError, match="malformed_frame"):
        demo.decode_frame(b"{", expected_sequence=1, binding=binding)
    with pytest.raises(demo.LimitedTestnetError, match="duplicate_sequence"):
        demo.decode_frame(frame[4:], expected_sequence=2, binding=binding)
    with pytest.raises(demo.LimitedTestnetError, match="oversized_frame"):
        demo.decode_frame(b"x" * (demo.MAX_FRAME_BYTES + 1), expected_sequence=1, binding=binding)
    left, right = socket.socketpair()
    left.settimeout(2)
    right.settimeout(2)
    right.sendall(struct.pack(">I", 6) + b"{")
    right.shutdown(socket.SHUT_WR)
    with pytest.raises(demo.LimitedTestnetError, match="truncated_frame"):
        demo.read_frame(left, expected_sequence=1, binding=binding)
    left.close()
    right.close()


def test_payment_is_canonical_exactly_once_and_work_waits(tmp_path, monkeypatch):
    payer, _provider, request, quote, payment, authorization = _parties()
    calls = {"validate": 0}
    original = demo.classify_transfer

    def wrapped(ledger, tx):
        calls["validate"] += 1
        return original(ledger, tx)

    monkeypatch.setattr(demo, "classify_transfer", wrapped)
    ledger = _open_ledger(str(tmp_path))
    tx_id, before_a, before_b, after_a, after_b = demo.settle_disposable_payment(
        ledger,
        request=request,
        quote=quote,
        payment_tx=payment,
        authorization=authorization,
    )
    assert calls["validate"] >= 1
    assert tx_id == payment["id"] == compute_tx_id(payment)
    assert (before_a, before_b, after_a, after_b) == (100, 0, 72, 28)
    assert ledger.total_transactions == 1
    replay_ok, _replay_id, replay_reason = classify_transfer(ledger, payment)
    assert replay_ok is False and replay_reason == "replay"
    assert asyncio.run(demo.apply_transfer(ledger, payment)) is False
    assert (ledger.get_balance(payment["sender"]), ledger.get_balance(payment["receiver"])) == (72, 28)
    with pytest.raises(Exception, match="payment_not_verified"):
        _perform_paid_service(INPUT_TEXT, payment_verified=False)
    invalid = deepcopy(payment)
    invalid["signature"] = "00" * 64
    invalid["id"] = compute_tx_id(invalid)
    invalid_authorization = build_payment_authorization(
        payer,
        request=request,
        quote=quote,
        payment_tx=invalid,
    )
    fresh = _open_ledger(str(tmp_path / "fresh"))
    with pytest.raises(demo.LimitedTestnetError, match="canonical_validation_failed"):
        demo.settle_disposable_payment(
            fresh,
            request=request,
            quote=quote,
            payment_tx=invalid,
            authorization=invalid_authorization,
        )
    assert (fresh.get_balance(invalid["sender"]), fresh.get_balance(invalid["receiver"])) == (100, 0)


def test_tampered_result_and_receipt_fail_and_flags_stay_false():
    payer, provider, request, quote, payment, _authorization = _parties()
    output = structured_text_analysis(INPUT_TEXT)
    result = build_service_result(provider, request=request, quote=quote, payment_tx_id=payment["id"], output=output)
    tampered = deepcopy(result)
    tampered["output"] = dict(tampered["output"])
    tampered["output"]["character_count"] = 1
    with pytest.raises(Exception):
        verify_service_result(tampered, request=request, quote=quote, payment_tx_id=payment["id"])
    receipt = build_service_receipt(
        provider,
        request=request,
        quote=quote,
        service_result=result,
        payment_tx_id=payment["id"],
    )
    receipt["signature"] = "22" * 64
    with pytest.raises(Exception):
        verify_service_receipt(receipt, request=request, quote=quote, service_result=result, payment_tx_id=payment["id"])
    del payer
    demo.assert_identity_flags_unchanged()
    assert RUNTIME_AUTHORIZED is False
    assert NETWORK_AUTHORIZED is False
    assert TESTNET_START_AUTHORIZED is False
    assert SIGNING_AUTHORIZED is False
    assert MINING_AUTHORIZED is False
    assert BROADCAST_AUTHORIZED is False
    assert SETTLEMENT_AUTHORIZED is False


def test_missing_fcntl_fails_closed_and_explicit_endpoints_still_work(monkeypatch, capsys):
    monkeypatch.setattr(demo, "fcntl", None)
    with pytest.raises(demo.LimitedTestnetError, match=demo.ENDPOINT_BLOCKER):
        demo.discover_local_ipv4()
    with pytest.raises(demo.LimitedTestnetError, match=demo.ENDPOINT_BLOCKER):
        demo.discover_distinct_rfc1918_endpoints()
    assert demo.require_distinct_endpoints("10.0.0.2", "192.168.1.9") == ("10.0.0.2", "192.168.1.9")
    assert demo.enforce_allowlisted_peer("172.16.4.4", "172.16.4.4") == "172.16.4.4"

    def _discovery_must_not_run() -> list[str]:
        raise AssertionError("discover_local_ipv4 called")

    monkeypatch.setattr(demo, "discover_local_ipv4", _discovery_must_not_run)
    code = demo.main(
        [
            "--role",
            "requester",
            "--requester-host",
            "10.0.0.2",
            "--provider-host",
            "192.168.1.9",
            "--input",
            INPUT_TEXT,
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert captured.err.strip() == "BLOCKER=DISTINCT_PRIVATE_TESTNET_ENDPOINT_UNAVAILABLE"
    assert captured.out == ""


def _local_rfc1918() -> str | None:
    for address in demo.discover_local_ipv4():
        try:
            return demo.classify_private_ipv4(address)
        except demo.LimitedTestnetError:
            continue
    return None


def test_explicit_provider_port_binding_and_clean_accept_timeout(monkeypatch, capsys):
    host = _local_rfc1918()
    assert host is not None
    for bad in (-1, 65536, True, 1.5, "28428", None):
        with pytest.raises(demo.LimitedTestnetError, match="invalid_port"):
            demo.open_provider_listener(host, bad)
    with pytest.raises(demo.LimitedTestnetError, match="loopback_rejected"):
        demo.open_provider_listener("127.0.0.1", 28428)
    with pytest.raises(demo.LimitedTestnetError, match="unspecified_address_rejected"):
        demo.open_provider_listener("0.0.0.0", 28428)
    with pytest.raises(demo.LimitedTestnetError, match="public_ip_rejected"):
        demo.open_provider_listener("8.8.8.8", 28428)

    ephemeral = demo.open_provider_listener(host)
    try:
        bound_host, bound_port = ephemeral.getsockname()
        assert bound_host == host
        assert bound_port != 0
        assert ephemeral.gettimeout() == demo.SOCKET_TIMEOUT_SECONDS
    finally:
        ephemeral.close()

    explicit = demo.open_provider_listener(
        host,
        bound_port,
        accept_timeout=demo.MANUAL_ACCEPT_TIMEOUT_SECONDS,
    )
    try:
        assert explicit.getsockname() == (host, bound_port)
        assert explicit.gettimeout() == demo.MANUAL_ACCEPT_TIMEOUT_SECONDS
    finally:
        explicit.close()

    code = demo.main(
        [
            "--role",
            "provider",
            "--requester-host",
            "10.0.0.2",
            "--provider-host",
            "10.0.0.3",
            "--port",
            "0",
        ]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err.strip() == "invalid_port"
    assert "Traceback" not in captured.err
    assert captured.out == ""

    monkeypatch.setattr(demo, "MANUAL_ACCEPT_TIMEOUT_SECONDS", 0.05)
    code = demo.provider_main(host, "10.0.0.9", bound_port)
    captured = capsys.readouterr()
    ready = json.loads(captured.out)
    assert ready == {"coordination": "provider_ready", "host": host, "port": bound_port}
    assert code == 1
    assert captured.err.strip() == "accept_timeout"
    assert "Traceback" not in captured.err

    seen: dict[str, object] = {}

    def _record(provider_host: str, port: int = 0, *, accept_timeout: float = demo.SOCKET_TIMEOUT_SECONDS):
        seen["host"] = provider_host
        seen["port"] = port
        seen["accept_timeout"] = accept_timeout
        raise demo.LimitedTestnetError("listener_failed")

    monkeypatch.setattr(demo, "open_provider_listener", _record)
    parent_argv = demo._argv("provider", "192.168.1.129", "192.168.1.138")
    assert "--port" not in parent_argv
    code = demo.provider_main("192.168.1.138", "192.168.1.129")
    assert code == 1
    assert seen == {
        "host": "192.168.1.138",
        "port": 0,
        "accept_timeout": demo.SOCKET_TIMEOUT_SECONDS,
    }
    code = demo.provider_main("192.168.1.138", "192.168.1.129", 28428)
    assert code == 1
    assert seen["port"] == 28428
    assert seen["accept_timeout"] == 0.05


def test_product_command_does_not_substitute_loopback():
    completed = __import__("subprocess").run(
        [__import__("sys").executable, "-m", "coin.limited_testnet_service_demo", "--input", INPUT_TEXT],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 2
    assert completed.stderr.strip() == "BLOCKER=DISTINCT_PRIVATE_TESTNET_ENDPOINT_UNAVAILABLE"
    assert completed.stdout == ""
    assert "127.0.0.1" not in completed.stdout


def test_listener_on_real_rfc1918_closes_and_source_has_no_secrets():
    addresses = [item for item in demo.discover_local_ipv4() if item.startswith("192.168.")]
    if addresses:
        listener = demo.open_provider_listener(addresses[0])
        host, _port = listener.getsockname()
        listener.close()
        assert host == addresses[0]
        with pytest.raises(OSError):
            listener.getsockname()
    source = IMPL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert "private_bytes" not in source
    assert "from_private_bytes" not in source
    assert "environ" not in source
    assert "def validate_transaction" not in source
    assert "def add_transaction" not in source
    assert {"requests", "urllib"}.isdisjoint(imports)
    assert RUNTIME_AUTHORIZED is False
