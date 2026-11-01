# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
import socket
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import public_testnet_service_demo as demo
from coin import two_agent_service_transaction_demo as service_core
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
from coin.two_agent_service_external_access_demo import SERVICE_ID as HTTP_SERVICE_ID
from coin.two_agent_service_external_access_demo import purchase_service
from coin.two_agent_service_transaction_demo import (
    PRICE_L28,
    _perform_paid_service,
    _public_key_hex,
    build_payment_authorization,
    build_service_quote,
    build_service_request,
    verify_service_receipt,
    verify_service_result,
)
from coin.tx_validation import compute_tx_id


IMPL_PATH = Path(__file__).resolve().parents[1] / "coin/public_testnet_service_demo.py"
REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = REPO_ROOT / "release/public-testnet-v0.1.0-rc1"
INPUT_TEXT = "L28 enables machine payments between autonomous systems."


def _pilot_config(port=28429):
    import time
    return demo.pilot_config(session_id="12" * 16, provider_host="127.0.0.1", requester_host="127.0.0.1",
                             port=port, created_at=int(time.time()))


def _pilot_package(provider, payer):
    request = build_service_request(payer, provider_identity=provider.identity, input_text=INPUT_TEXT,
                                    service_id=demo.SUMMARY_SERVICE_ID)
    quote = provider.backend.quote_for(request)
    tx = build_signed_transfer(payer, receiver=provider.identity, amount=28, timestamp=DEMO_TIMESTAMP, nonce=100)
    auth = build_payment_authorization(payer, request=request, quote=quote, payment_tx=tx)
    return {"request": request, "quote": quote, "payment_tx": tx, "payment_authorization": auth}


def test_private_pilot_discovery_and_envelope_bindings():
    config = _pilot_config()
    key, peer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    target = _public_key_hex(peer)
    payload = demo.build_service_discovery(demo.public_testnet_binding(), service_id=demo.SUMMARY_SERVICE_ID, private_pilot=True)
    signed = demo.pilot_envelope(key, config, "provider", target, "GET", demo.DISCOVERY_PATH, payload)
    assert demo.verify_pilot_envelope(signed, config, "provider", target, "GET", demo.DISCOVERY_PATH) == payload
    assert payload["http_json"]["external_https_required"] is False
    for field, changed in (("context", "0" * 64), ("role", "requester"), ("peer", "0" * 64),
                           ("public_key", _public_key_hex(peer)), ("signature", "00" * 64),
                           ("path", demo.HELLO_PATH), ("method", "POST")):
        bad = deepcopy(signed)
        bad[field] = changed
        with pytest.raises((demo.PublicTestnetError, service_core.DemoError)):
            demo.verify_pilot_envelope(bad, config, "provider", target, "GET", demo.DISCOVERY_PATH)
    bad = deepcopy(signed)
    bad["payload"]["services"][0]["price"] = 27
    with pytest.raises(service_core.DemoError):
        demo.verify_pilot_envelope(bad, config, "provider", target, "GET", demo.DISCOVERY_PATH)


@pytest.mark.parametrize("field,value", [
    ("provider_host", "0.0.0.0"), ("requester_host", "8.8.8.8"), ("provider_host", "localhost"),
    ("provider_host", True), ("port", True), ("port", 0), ("session_id", "bad"),
    ("created_at", True), ("expires_at", 0), ("source_digest", "0" * 64),
    ("network_id", "OTHER"), ("payment_network_id", "L28-DISPOSABLE-PERSISTENT001"),
    ("service_id", demo.SERVICE_ID), ("price", 27), ("price", 28.0), ("unexpected", True),
])
def test_private_pilot_config_fails_closed(field, value):
    config = _pilot_config()
    config[field] = value
    with pytest.raises(demo.PublicTestnetError):
        demo.validate_pilot_config(config)


@pytest.mark.parametrize("body", [b"{}", b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'\xff', b'{' * 1000, b'x' * 65537])
def test_private_pilot_malformed_envelopes(body):
    with pytest.raises((demo.PublicTestnetError, service_core.DemoError)):
        demo.verify_pilot_envelope(demo._pilot_json(body), _pilot_config(), "provider", "", "GET", demo.DISCOVERY_PATH)


def test_private_pilot_route_requires_real_device_status(monkeypatch):
    config = _pilot_config()
    # Synthetic shared-address-space peers and keys; all device status is mocked.
    config.update(provider_host="100.64.0.10", requester_host="100.64.0.11",
                  route_keys={"provider": "nodekey:" + "1" * 64, "requester": "nodekey:" + "2" * 64})
    config = demo.validate_pilot_config(config)
    class Status:
        stdout = b'{"BackendState":"Running","Self":{"PublicKey":"wrong"},"Peer":{}}'
    calls = []
    def status(command, **kwargs):
        calls.append(command)
        return Status()
    monkeypatch.setattr(demo.subprocess, "run", status)
    with pytest.raises(demo.PublicTestnetError, match="private_route_not_verified"):
        demo.verify_pilot_route(config, "provider")
    assert calls == [["tailscale", "status", "--json"]]
    correct = {"BackendState": "Running", "Self": {"PublicKey": config["route_keys"]["provider"], "TailscaleIPs": [config["provider_host"]]},
               "Peer": {"x": {"PublicKey": config["route_keys"]["requester"], "TailscaleIPs": [config["requester_host"]], "Online": True}}}
    Status.stdout = json.dumps(correct).encode()
    demo.verify_pilot_route(config, "provider")
    correct["Peer"]["x"]["Online"] = False
    Status.stdout = json.dumps(correct).encode()
    with pytest.raises(demo.PublicTestnetError):
        demo.verify_pilot_route(config, "provider")


def test_private_pilot_slow_response_has_absolute_deadline_and_cleans_up(monkeypatch):
    import threading
    import time
    aborted = threading.Event()
    closed = []
    timers = []
    real_timer = threading.Timer
    class Transport:
        def getpeername(self): return ("127.0.0.1", 28429)
        def getsockname(self): return ("127.0.0.1", 50000)
        def shutdown(self, how): aborted.set()
    class Response:
        status = 200
        def read(self, limit):
            assert aborted.wait(.5), "absolute watchdog did not interrupt the slow read"
            return b"{}"
    class Connection:
        sock = Transport()
        def __init__(self, *args, **kwargs): pass
        def connect(self): pass
        def request(self, *args, **kwargs): pass
        def getresponse(self): return Response()
        def close(self): closed.append(True)
    def timer(*args, **kwargs):
        instance = real_timer(*args, **kwargs)
        timers.append(instance)
        return instance
    monkeypatch.setattr(demo.http.client, "HTTPConnection", Connection)
    monkeypatch.setattr(demo.threading, "Timer", timer)
    monkeypatch.setattr(demo, "REQUEST_TIMEOUT_SECONDS", .02)
    start = time.monotonic()
    with pytest.raises(demo.PublicTestnetError, match="pilot_request_timeout"):
        demo.pilot_http_exchange(_pilot_config(), "GET", demo.DISCOVERY_PATH, None)
    assert time.monotonic() - start < .5
    assert aborted.is_set() and closed == [True]
    assert len(timers) == 1 and not timers[0].is_alive()


@pytest.mark.parametrize("kind", ["signature", "amount", "recipient", "session", "peer", "quote", "network"])
def test_private_pilot_rejected_payment_no_work_or_mutation(tmp_path, monkeypatch, kind):
    from coin import durable_restart_safe_service_demo as durable
    provider = demo.PrivatePilotProvider(_pilot_config(), tmp_path / "state")
    payer = Ed25519PrivateKey.generate()
    def no_work(*args, **kwargs):
        raise AssertionError("rejected payment reached work")
    monkeypatch.setattr(durable, "_perform_paid_service", no_work)
    try:
        package = _pilot_package(provider, payer)
        provider.dispatch("GET", demo.HELLO_PATH, None)
        request_frame = json.loads(demo.frame_bytes("service_request", 2, package["request"], provider.binding))
        envelope = demo.pilot_envelope(payer, provider.config, "requester", provider.public_key, "POST", demo.SESSION_PATH, request_frame)
        quote_reply = provider.dispatch("POST", demo.SESSION_PATH, demo._pilot_bytes(envelope))
        package["quote"] = quote_reply["payload"]["payload"]
        package["payment_authorization"] = build_payment_authorization(payer, request=package["request"], quote=package["quote"], payment_tx=package["payment_tx"])
        if kind in {"signature", "amount", "recipient", "network"}:
            package["payment_tx"][{"signature": "signature", "amount": "amount", "recipient": "receiver", "network": "network"}[kind]] = {
                "signature": "00" * 64, "amount": 27, "recipient": "l28disp_" + "0" * 64, "network": "OTHER"}[kind]
            package["payment_tx"]["id"] = compute_tx_id(package["payment_tx"])
        if kind == "quote":
            package["payment_authorization"]["quote_id"] = "0" * 64
        frame = json.loads(demo.frame_bytes("payment_package", 4, {k: package[k] for k in ("payment_tx", "payment_authorization")}, provider.binding))
        envelope = demo.pilot_envelope(payer, provider.config, "requester", provider.public_key, "POST", demo.SESSION_PATH, frame)
        if kind == "session":
            envelope["context"] = "0" * 64
        if kind == "peer":
            envelope["peer"] = "0" * 64
        before = provider.backend.store.snapshot()
        disk_before = {p.name: p.read_bytes() for p in (tmp_path / "state").iterdir() if p.is_file()}
        with pytest.raises((demo.PublicTestnetError, service_core.DemoError, durable.DurableRuntimeError)):
            provider.dispatch("POST", demo.SESSION_PATH, demo._pilot_bytes(envelope))
        assert provider.backend.store.snapshot() == before
        assert {p.name: p.read_bytes() for p in (tmp_path / "state").iterdir() if p.is_file()} == disk_before
        assert before["state_version"] == 0 and before["balances"] == {} and before["accepted"] == {}
    finally:
        provider.close()


@pytest.mark.parametrize("accepted", [False, True])
def test_private_pilot_replay_probe_never_recomputes_useful_work(tmp_path, monkeypatch, accepted):
    provider = demo.PrivatePilotProvider(_pilot_config(), tmp_path / "state")
    payer = Ed25519PrivateKey.generate()
    try:
        package = _pilot_package(provider, payer)
        artifacts = {**package, "service_result": {}, "receipt": {}}
        if accepted:
            result = provider.backend.handle_payment(package)
            artifacts.update(service_result=result["service_result"], receipt=result["receipt"])
        def no_summary(*args, **kwargs):
            raise AssertionError("replay probe recomputed useful work")
        monkeypatch.setattr(service_core, "service_output", no_summary)
        envelope = demo.pilot_envelope(payer, provider.config, "requester", provider.public_key, "POST", demo.SESSION_PATH,
                                       {"action": "replay", "artifacts": artifacts})
        before = provider.backend.store.snapshot()
        if accepted:
            reply = provider.dispatch("POST", demo.SESSION_PATH, demo._pilot_bytes(envelope))
            assert reply["payload"]["error"] == "replay"
            assert reply["payload"]["evidence"]["service_executed"] is False
        else:
            with pytest.raises(demo.PublicTestnetError, match="unknown_payment"):
                provider.dispatch("POST", demo.SESSION_PATH, demo._pilot_bytes(envelope))
        assert provider.backend.store.snapshot() == before
    finally:
        provider.close()


def test_private_pilot_real_http_restart_and_cleanup(tmp_path):
    import selectors
    import time
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = _pilot_config(port)
    config_path = tmp_path / "public-config.json"
    config_path.write_bytes(demo._pilot_bytes(config))
    artifacts_path = tmp_path / "public-artifacts.json"
    commands = [sys.executable, "-B", "-m", "coin.public_testnet_service_demo"]
    provider_reports = []
    pids = []
    for restart in (False, True):
        provider = subprocess.Popen(commands + ["--role", "provider", "--private-pilot", "--pilot-config", str(config_path), "--state-dir", str(tmp_path / "state")],
                                    cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pids.append(provider.pid)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(provider.stdout, selectors.EVENT_READ)
                assert selector.select(10), "provider did not report readiness"
                line = provider.stdout.readline()
                assert line, "startup failed: " + provider.stderr.read()
                ready = json.loads(line)
            assert ready["coordination"] == "pilot_provider_ready"
            options = ["--replay-artifacts", str(artifacts_path)] if restart else []
            requester = subprocess.run(commands + ["--role", "requester", "--private-pilot", "--pilot-config", str(config_path), "--input", INPUT_TEXT] + options,
                                       cwd=REPO_ROOT, capture_output=True, text=True, timeout=20)
            assert requester.returncode == 0, requester.stderr
            result = json.loads(requester.stdout)
            assert result["physical_remote_verified"] is False
            assert result["replay"]["replay_rejected"] is True
            assert result["replay"]["service_executed"] is False
            assert result["issued_supply"] == result["mint_height"] == 0
            if not restart:
                assert result["service_output"]["input_digest"] == hashlib.sha256(INPUT_TEXT.encode()).hexdigest()
                assert result["receipt_verified"] and result["service_result_verified"]
                artifacts_path.write_bytes(demo._pilot_bytes(result["public_artifacts"]))
            output, error = provider.communicate(timeout=10)
            assert provider.returncode == 0, error
            report = json.loads(output)
            provider_reports.append(report)
            assert report["state"]["state_version"] == 1
            assert sorted(report["state"]["balances"].values()) == [28, 72]
            assert report["listener_closed"] is True
        finally:
            if provider.poll() is None:
                provider.terminate()
                provider.wait(timeout=5)
            provider.stdout.close()
            provider.stderr.close()
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0
    assert pids[0] != pids[1]
    assert provider_reports[0]["state_commitment"] == provider_reports[1]["state_commitment"]
    assert provider_reports[1]["evidence"]["durable_state_reopened"] is True
    assert provider_reports[0]["purchase_evidence"]["service_executed"] is True


def test_public_identity_binding_and_authorization_flags_stay_false():
    binding = demo.public_testnet_binding()
    assert binding["network_id"] == "L28-DISPOSABLE-PUBLIC001"
    assert binding["data_dir_tag"] == "l28-disposable-testnet:public001"
    demo.assert_identity_flags_unchanged()
    assert RUNTIME_AUTHORIZED is NETWORK_AUTHORIZED is TESTNET_START_AUTHORIZED is False
    assert SIGNING_AUTHORIZED is MINING_AUTHORIZED is BROADCAST_AUTHORIZED is SETTLEMENT_AUTHORIZED is False
    frame = json.loads(demo.frame_bytes("provider_hello", 1, {"provider_identity": "a", "provider_public_key": "ab"}, binding))
    frame["network_id"] = "L28-DISPOSABLE-OTHER001"
    with pytest.raises(demo.PublicTestnetError, match="wrong_network"):
        demo.parse_frame(json.dumps(frame).encode(), expected_sequence=1, binding=binding)
    frame["network_id"] = binding["network_id"]
    frame["genesis_hash"] = "00" * 32
    with pytest.raises(demo.PublicTestnetError, match="wrong_network_binding"):
        demo.parse_frame(json.dumps(frame).encode(), expected_sequence=1, binding=binding)
    frame["genesis_hash"] = binding["genesis_hash"]
    frame["config_hash"] = "11" * 32
    with pytest.raises(demo.PublicTestnetError, match="wrong_network_binding"):
        demo.parse_frame(json.dumps(frame).encode(), expected_sequence=1, binding=binding)


def test_service_discovery_is_exact_and_fails_closed():
    binding = demo.public_testnet_binding()
    discovery = demo.build_service_discovery(binding)
    assert discovery == {
        "discovery_profile": "l28-public-testnet-service-discovery/v0.1",
        "discovery_version": 1,
        "release_candidate": "l28-public-testnet-v0.1.0-rc1",
        "designation": "NON_PRODUCTION_DISPOSABLE_TESTNET",
        "network_id": "L28-DISPOSABLE-PUBLIC001",
        "protocol_version": "1.0.0",
        "genesis_hash": binding["genesis_hash"],
        "config_hash": binding["config_hash"],
        "transport_profile": "l28-public-testnet-service/v0.1",
        "http_json": {
            "discovery_path": "/v1/l28/public-testnet/services",
            "provider_hello_path": "/v1/l28/public-testnet/provider_hello",
            "session_path": "/v1/l28/public-testnet/session",
            "external_https_required": True,
            "max_body_bytes": 65536,
            "request_timeout_seconds": 10,
            "session_deadline_seconds": 120,
        },
        "services": [
            {
                "service_id": "l28.service.structured_text_analysis/v0.1",
                "asset_id": "L28",
                "price": 28,
                "max_input_chars": 4096,
                "one_shot": True,
            }
        ],
        "production_authority": False,
    }
    body = json.dumps(discovery, separators=(",", ":"), ensure_ascii=False).encode()
    assert demo.validate_service_discovery(body, binding) == discovery

    for mutator in (
        lambda value: value["services"][0].update(price=29),
        lambda value: value["services"][0].update(price=28.0),
        lambda value: value.update(discovery_version=True),
        lambda value: value.update(network_id="L28-DISPOSABLE-OTHER001"),
        lambda value: value.update(unexpected=True),
        lambda value: value.pop("services"),
    ):
        tampered = deepcopy(discovery)
        mutator(tampered)
        with pytest.raises(demo.PublicTestnetError, match="discovery_invalid"):
            demo.validate_service_discovery(json.dumps(tampered).encode(), binding)
    with pytest.raises(demo.PublicTestnetError, match="malformed_json"):
        demo.validate_service_discovery(b'{"discovery_version":1,"discovery_version":1}', binding)
    with pytest.raises(demo.PublicTestnetError, match="discovery_invalid"):
        demo.validate_service_discovery(b'{"discovery_version":NaN}', binding)


def test_requester_rejects_discovery_before_identity_or_payment(monkeypatch):
    binding = demo.public_testnet_binding()
    calls: list[tuple[str, str, bytes | None]] = []

    class NoDisposableKeyBeforeDiscovery:
        @staticmethod
        def generate():
            raise AssertionError("disposable payer created before discovery validation")

    monkeypatch.setattr(demo, "Ed25519PrivateKey", NoDisposableKeyBeforeDiscovery)

    def exchange(method: str, path: str, body: bytes | None) -> bytes:
        calls.append((method, path, body))
        tampered = demo.build_service_discovery(binding)
        tampered["services"][0]["price"] = 27
        return json.dumps(tampered).encode()

    with pytest.raises(demo.PublicTestnetError, match="discovery_invalid"):
        demo.run_requester(exchange, INPUT_TEXT, binding)
    assert calls == [("GET", demo.DISCOVERY_PATH, None)]


def test_malformed_json_body_bound_and_request_timeout():
    binding = demo.public_testnet_binding()
    with pytest.raises(demo.PublicTestnetError, match="malformed_json"):
        demo.parse_frame(b"{", expected_sequence=1, binding=binding)
    with pytest.raises(demo.PublicTestnetError, match="oversized_body"):
        demo.enforce_body_bound(demo.MAX_BODY_BYTES + 1)
    with pytest.raises(demo.PublicTestnetError, match="oversized_body"):
        demo.parse_frame(b"x" * (demo.MAX_BODY_BYTES + 1), expected_sequence=1, binding=binding)
    listener = __import__("socket").socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(2)

    def _hold() -> None:
        try:
            connection, _address = listener.accept()
        except OSError:
            return
        try:
            connection.recv(64)
            __import__("time").sleep(1)
        finally:
            connection.close()

    __import__("threading").Thread(target=_hold, daemon=True).start()
    port = listener.getsockname()[1]
    try:
        with pytest.raises(demo.PublicTestnetError, match="request_timeout"):
            demo.http_exchange(f"http://127.0.0.1:{port}", "GET", demo.HELLO_PATH, None, 0.2, allow_local_harness=True)
    finally:
        listener.close()


def test_public_endpoint_rejects_localhost_and_lan():
    with pytest.raises(demo.PublicTestnetError, match="PUBLIC_TESTNET_ENDPOINT_UNAVAILABLE"):
        demo.require_public_https_endpoint("http://127.0.0.1:9/purchase")
    with pytest.raises(demo.PublicTestnetError, match="localhost_request_path"):
        demo.require_public_https_endpoint("https://127.0.0.1/purchase")
    with pytest.raises(demo.PublicTestnetError, match="localhost_request_path"):
        demo.require_public_https_endpoint("https://localhost/purchase")
    with pytest.raises(demo.PublicTestnetError, match="direct_lan_request_path"):
        demo.require_public_https_endpoint("https://192.168.1.138/purchase")
    with pytest.raises(demo.PublicTestnetError, match="direct_lan_request_path"):
        demo.require_public_https_endpoint("https://10.0.0.2/purchase")
    assert demo.require_public_https_endpoint("https://l28-public.example/purchase") == "https://l28-public.example/purchase"
    with pytest.raises(demo.PublicTestnetError, match="localhost_request_path"):
        demo.build_public_evidence(
            "https://127.0.0.1/purchase",
            {"payment_tx_id": "a", "requester_balance_before": 100, "provider_balance_before": 0, "requester_balance_after": 72, "provider_balance_after": 28, "replay_rejected": True},
            {"payment_tx_id": "a", "service_result_verified": True, "receipt_verified": True},
        )


def test_quote_payment_replay_work_gate_and_tamper(tmp_path):
    binding = demo.public_testnet_binding()
    provider = demo.PublicProvider()
    payer = Ed25519PrivateKey.generate()
    hello = provider.hello_frame()
    assert hello["sequence"] == 1
    request = build_service_request(payer, provider_identity=provider.identity, input_text=INPUT_TEXT)
    quote_frame = provider.handle_frame(demo.frame_bytes("service_request", 2, request, binding))
    quote = quote_frame["payload"]
    assert quote["amount"] == 28 == PRICE_L28
    payment = build_signed_transfer(
        payer,
        receiver=provider.identity,
        amount=28,
        timestamp=DEMO_TIMESTAMP,
        nonce=100,
    )
    authorization = build_payment_authorization(payer, request=request, quote=quote, payment_tx=payment)
    with pytest.raises(Exception, match="payment_not_verified"):
        _perform_paid_service(INPUT_TEXT, payment_verified=False)
    result = provider.handle_frame(
        demo.frame_bytes(
            "payment_package",
            4,
            {"payment_tx": payment, "payment_authorization": authorization},
            binding,
        )
    )
    assert provider.evidence["canonical_validation"] == "PASS"
    assert provider.evidence["replay_rejected"] is True
    assert provider.evidence["receipt_created"] is True
    with pytest.raises(demo.PublicTestnetError, match="provider_evidence_incomplete"):
        demo.provider_evidence_record(provider.evidence, network_id=binding["network_id"], shutdown_complete=False)
    record = demo.provider_evidence_record(provider.evidence, network_id=binding["network_id"], shutdown_complete=True)
    assert record["coordination"] == "provider_evidence"
    assert record["public_testnet"] is True
    assert record["network_id"] == "L28-DISPOSABLE-PUBLIC001"
    assert record["payment_tx_id"] == payment["id"]
    assert record["bounded_provider_shutdown"] is True
    assert (
        record["requester_balance_before"],
        record["provider_balance_before"],
        record["requester_balance_after"],
        record["provider_balance_after"],
    ) == (100, 0, 72, 28)
    assert (
        provider.evidence["requester_balance_before"],
        provider.evidence["provider_balance_before"],
        provider.evidence["requester_balance_after"],
        provider.evidence["provider_balance_after"],
    ) == (100, 0, 72, 28)
    assert provider.finished.is_set()
    with pytest.raises(demo.PublicTestnetError, match="session_closed"):
        provider.hello_frame()
    service_result = result["payload"]["service_result"]
    receipt = result["payload"]["receipt"]
    verify_service_result(service_result, request=request, quote=quote, payment_tx_id=payment["id"])
    verify_service_receipt(receipt, request=request, quote=quote, service_result=service_result, payment_tx_id=payment["id"])
    tampered = deepcopy(service_result)
    tampered["output"] = dict(tampered["output"])
    tampered["output"]["character_count"] = 1
    with pytest.raises(Exception):
        verify_service_result(tampered, request=request, quote=quote, payment_tx_id=payment["id"])
    bad_receipt = deepcopy(receipt)
    bad_receipt["signature"] = "22" * 64
    with pytest.raises(Exception):
        verify_service_receipt(bad_receipt, request=request, quote=quote, service_result=service_result, payment_tx_id=payment["id"])
    second = demo.PublicProvider()
    second.hello_frame()
    second_request = build_service_request(payer, provider_identity=second.identity, input_text=INPUT_TEXT)
    second_quote = second.handle_frame(demo.frame_bytes("service_request", 2, second_request, binding))["payload"]
    invalid = build_signed_transfer(
        payer,
        receiver=second.identity,
        amount=28,
        timestamp=DEMO_TIMESTAMP,
        nonce=100,
    )
    invalid["signature"] = "00" * 64
    invalid["id"] = compute_tx_id(invalid)
    invalid_auth = build_payment_authorization(payer, request=second_request, quote=second_quote, payment_tx=invalid)
    with pytest.raises(demo.PublicTestnetError, match="canonical_validation_failed"):
        second.handle_frame(
            demo.frame_bytes(
                "payment_package",
                4,
                {"payment_tx": invalid, "payment_authorization": invalid_auth},
                binding,
            )
        )
    assert second.evidence is None
    del payer
    assert tmp_path.exists()


def test_one_shot_http_harness_shuts_down_and_is_not_public_evidence():
    server, thread, provider = demo.start_one_shot_server()
    host, port = server.server_address
    assert host == "127.0.0.1"
    base = f"http://{host}:{port}"

    def exchange(method: str, path: str, body: bytes | None) -> bytes:
        return demo.http_exchange(base, method, path, body, 5, allow_local_harness=True)

    try:
        requester = demo.run_requester(exchange, INPUT_TEXT, provider.binding)
    finally:
        demo.stop_one_shot_server(server, thread)
    assert provider.finished.is_set()
    assert requester["service_discovery_verified"] is True
    assert requester["discovered_service_id"] == "l28.service.structured_text_analysis/v0.1"
    assert requester["discovered_price"] == 28
    assert requester["quote_verified"] is True
    assert requester["service_result_verified"] is True
    assert requester["receipt_verified"] is True
    assert requester["payment_tx_id"] == provider.evidence["payment_tx_id"]
    assert provider.evidence["quoted_amount"] == 28
    record = demo.provider_evidence_record(
        provider.evidence,
        network_id=provider.binding["network_id"],
        shutdown_complete=True,
    )
    assert record["coordination"] == "provider_evidence"
    assert record["payment_tx_id"] == requester["payment_tx_id"]
    assert record["receipt_created"] is True
    assert record["bounded_provider_shutdown"] is True
    with pytest.raises(OSError):
        probe = __import__("socket").create_connection((host, port), timeout=0.2)
        probe.close()
    with pytest.raises(demo.PublicTestnetError, match="localhost_request_path"):
        demo.build_public_evidence(f"https://{host}:{port}/", provider.evidence, requester)


def test_product_command_does_not_substitute_localhost_or_lan():
    completed = subprocess.run(
        [sys.executable, "-m", "coin.public_testnet_service_demo", "--input", INPUT_TEXT],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 2
    assert completed.stderr.strip() == "BLOCKER=PUBLIC_TESTNET_ENDPOINT_UNAVAILABLE"
    assert completed.stdout == ""
    for forbidden in ("127.0.0.1", "192.168.", "canonical_validation"):
        assert forbidden not in completed.stdout


def test_local_release_example_command_exercises_actual_http_product():
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "coin.public_testnet_service_demo",
            "--role",
            "local-example",
            "--input",
            INPUT_TEXT,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert completed.stderr.strip() == (
        f"❌ Reject tx id={result['payment_tx_id']} reason=replay"
    )
    assert result["release_candidate"] == "l28-public-testnet-v0.1.0-rc1"
    assert result["designation"] == "NON_PRODUCTION_DISPOSABLE_TESTNET"
    assert result["verification_scope"] == "LOCAL_ONLY"
    assert result["service_discovery_verified"] is True
    assert result["service_id"] == "l28.service.structured_text_analysis/v0.1"
    assert result["network_id"] == "L28-DISPOSABLE-PUBLIC001"
    assert result["quoted_amount"] == 28
    assert result["canonical_validation"] == "PASS"
    assert result["payment_verified"] is True
    assert result["replay_rejected"] is True
    assert result["service_executed"] is True
    assert result["service_result_verified"] is True
    assert result["receipt_verified"] is True
    assert result["bounded_provider_shutdown"] is True
    assert result["canonical_history_touched"] is False
    assert result["production_keys_used"] is False
    assert result["public_network_used"] is False
    assert result["external_https_exposure"] is False
    assert result["production_settlement"] is False


def test_release_manifest_and_sha256_inventory_are_reproducible():
    # This immutable inventory describes the paid-summary release commit, not
    # later feature worktrees. Verify those exact Git objects; never rewrite it.
    release_commit = "b6f9afdb12dee86639476d4fcd357a75843a2008"
    def release_bytes(path):
        return subprocess.check_output(["git", "show", f"{release_commit}:{path}"], cwd=REPO_ROOT)
    manifest_path = RELEASE_DIR / "manifest.json"
    sums_path = RELEASE_DIR / "SHA256SUMS"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path.read_bytes() == release_bytes("release/public-testnet-v0.1.0-rc1/manifest.json")
    assert manifest["schema"] == "l28.public-testnet-release-manifest"
    assert manifest["schema_version"] == "0.1"
    assert manifest["release_candidate"] == "l28-public-testnet-v0.1.0-rc1"
    assert manifest["source_parent"] == "b2674aff02f67da002442a87f3ff739c73563d11"
    assert manifest["designation"] == "NON_PRODUCTION_DISPOSABLE_TESTNET"
    assert manifest["network_id"] == "L28-DISPOSABLE-PUBLIC001"
    assert manifest["service"]["price"] == 28
    assert manifest["transport"]["mcp"] == "LOCAL_STDIO_ONLY"
    assert manifest["public_endpoint_configured"] is False
    assert manifest["deployment_authorized"] is False
    assert manifest["production_authority"] is False

    manifest_paths = []
    for artifact in manifest["artifacts"]:
        content = release_bytes(artifact["path"])
        manifest_paths.append(artifact["path"])
        assert len(content) == artifact["size_bytes"]
        assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
    assert manifest_paths == sorted(manifest_paths)

    expected_sums = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        digest, path = line.split("  ", 1)
        expected_sums[path] = digest
    assert sorted(expected_sums) == sorted(
        manifest_paths + ["release/public-testnet-v0.1.0-rc1/manifest.json"]
    )
    for path, digest in expected_sums.items():
        assert hashlib.sha256(release_bytes(path)).hexdigest() == digest


def test_existing_http_service_still_purchases_and_source_has_no_secrets():
    purchased = purchase_service({"service_id": HTTP_SERVICE_ID, "input": INPUT_TEXT})
    assert purchased["ok"] is True
    assert purchased["service_id"] == "l28.service.structured_text_analysis/v0.1"
    assert purchased["purchase"]["quoted_amount"] == 28
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
    assert "requests" not in imports
    assert public_identity(_public_key_hex(Ed25519PrivateKey.generate())).startswith("l28disp_")


SUMMARY_ID = service_core.SUMMARY_SERVICE_ID
SUMMARY_INPUT = 'Rare opener. L28 payments help agents. L28 payments buy summaries. L28 payments bind receipts.'


def _summary_purchase():
    provider = demo.PublicProvider(service_id=SUMMARY_ID)

    def exchange(method, path, body):
        if (method, path) == ('GET', demo.DISCOVERY_PATH):
            response = demo.build_service_discovery(provider.binding, service_id=SUMMARY_ID)
        elif (method, path) == ('GET', demo.HELLO_PATH):
            response = provider.hello_frame()
        else:
            response = provider.handle_frame(body)
        return json.dumps(response, ensure_ascii=False).encode('utf-8')

    requester = demo.run_requester(exchange, SUMMARY_INPUT, provider.binding, service_id=SUMMARY_ID)
    return provider, requester


def test_summary_discovery_requires_exact_expected_service_before_payment(monkeypatch):
    binding = demo.public_testnet_binding()
    catalog = demo.build_service_discovery(binding, service_id=SUMMARY_ID)
    assert catalog['services'] == [{'service_id': SUMMARY_ID, 'asset_id': 'L28', 'price': 28,
                                    'max_input_chars': 4096, 'one_shot': True}]
    assert demo.validate_service_discovery(json.dumps(catalog).encode(), binding, service_id=SUMMARY_ID) == catalog
    with pytest.raises(demo.PublicTestnetError, match='discovery_invalid'):
        demo.validate_service_discovery(json.dumps(catalog).encode(), binding)
    monkeypatch.setattr(demo, 'Ed25519PrivateKey', type('NoPayer', (), {'generate': staticmethod(lambda: pytest.fail('payer before valid discovery'))}))
    calls = []

    def exchange(method, path, body):
        calls.append((method, path))
        return json.dumps(demo.build_service_discovery(binding)).encode()

    with pytest.raises(demo.PublicTestnetError, match='discovery_invalid'):
        demo.run_requester(exchange, SUMMARY_INPUT, binding, service_id=SUMMARY_ID)
    assert calls == [('GET', demo.DISCOVERY_PATH)]


def test_summary_artifacts_independently_verify_and_replay_creates_no_work(monkeypatch):
    provider, requester = _summary_purchase()
    artifacts = requester['public_artifacts']
    assert requester['service_output'] == service_core.text_summary(SUMMARY_INPUT)
    assert demo.verify_purchase_artifacts(artifacts, input_text=SUMMARY_INPUT, service_id=SUMMARY_ID) == requester['service_output']
    assert provider.evidence['payment_verified'] is True
    assert (provider.evidence['requester_balance_after'], provider.evidence['provider_balance_after']) == (72, 28)
    assert provider._key is None
    monkeypatch.setattr(demo, '_perform_paid_service', lambda *_a, **_kw: pytest.fail('replay work'))
    before = deepcopy(provider.evidence)
    package = {'payment_tx': artifacts['payment_tx'], 'payment_authorization': artifacts['payment_authorization']}
    with pytest.raises(demo.PublicTestnetError, match='session_closed'):
        provider.handle_frame(demo.frame_bytes('payment_package', 4, package, provider.binding))
    assert provider.evidence == before
    for field in ('request', 'quote', 'payment_authorization', 'service_result'):
        assert artifacts[field]['service_id'] == SUMMARY_ID


@pytest.mark.parametrize('kind', ['signature', 'amount', 'recipient', 'quote', 'network', 'nonce'])
def test_summary_invalid_payment_creates_no_ledger_or_work(kind, monkeypatch):
    import coin.disposable_offline_transfer_demo as transfer

    provider = demo.PublicProvider(service_id=SUMMARY_ID)
    payer = Ed25519PrivateKey.generate()
    provider.hello_frame()
    request = build_service_request(payer, provider_identity=provider.identity, input_text=SUMMARY_INPUT, service_id=SUMMARY_ID)
    quote = provider.handle_frame(demo.frame_bytes('service_request', 2, request, provider.binding))['payload']
    payment = build_signed_transfer(payer, receiver=('l28disp_' + '0' * 64) if kind == 'recipient' else provider.identity,
                                    amount=27 if kind == 'amount' else 28, timestamp=DEMO_TIMESTAMP, nonce=100)
    if kind == 'signature':
        payment['signature'] = '00' * 64
    elif kind == 'network':
        payment['network'] = 'DISPOSABLE_OTHER'
    elif kind == 'nonce':
        payment['nonce'] = True
    payment['id'] = compute_tx_id(payment)
    authorization = build_payment_authorization(payer, request=request, quote=quote, payment_tx=payment)
    if kind == 'quote':
        authorization['quote_id'] = '00' * 32
        body = service_core._artifact_body(authorization, service_core.PAYMENT_AUTH_BODY_FIELDS)
        authorization['authorization_id'] = service_core._digest(body)
        authorization['signature'] = service_core._sign_domain(payer, service_core.PAYMENT_AUTH_SIGN_DOMAIN, body)
    monkeypatch.setattr(transfer, '_open_ledger', lambda *_a: pytest.fail('rejected payment opened ledger'))
    monkeypatch.setattr(demo, '_perform_paid_service', lambda *_a, **_kw: pytest.fail('unpaid work'))
    monkeypatch.setattr(service_core, 'text_summary', lambda *_a: pytest.fail('unpaid summary'))
    before = (provider.expected, deepcopy(provider._request), deepcopy(provider._quote))
    try:
        with pytest.raises((demo.PublicTestnetError, service_core.DemoError)):
            provider.handle_frame(demo.frame_bytes('payment_package', 4,
                                  {'payment_tx': payment, 'payment_authorization': authorization}, provider.binding))
        assert provider.evidence is None and not provider.finished.is_set()
        assert (provider.expected, provider._request, provider._quote) == before
    finally:
        provider.close()


@pytest.mark.parametrize('field', ['request', 'quote', 'payment_tx', 'payment_authorization', 'service_result', 'receipt'])
def test_summary_public_artifact_tampering_rejects(field):
    _provider, requester = _summary_purchase()
    artifacts = deepcopy(requester['public_artifacts'])
    if field == 'request':
        artifacts[field]['input']['text'] = 'Different source.'
    elif field == 'quote':
        artifacts[field]['amount'] = 27
    elif field == 'payment_authorization':
        artifacts[field]['quote_id'] = '00' * 32
    elif field == 'service_result':
        artifacts[field]['output']['summary'] = 'Fabricated summary.'
    else:
        artifacts[field]['signature'] = '00' * 64
    with pytest.raises((demo.PublicTestnetError, service_core.DemoError)):
        demo.verify_purchase_artifacts(artifacts, input_text=SUMMARY_INPUT, service_id=SUMMARY_ID)


def test_summary_artifact_input_and_service_substitution_reject():
    _provider, requester = _summary_purchase()
    artifacts = requester['public_artifacts']
    with pytest.raises(demo.PublicTestnetError, match='input_binding_invalid'):
        demo.verify_purchase_artifacts(artifacts, input_text='Different source.', service_id=SUMMARY_ID)
    with pytest.raises(service_core.DemoError, match='service_invalid'):
        demo.verify_purchase_artifacts(artifacts, input_text=SUMMARY_INPUT)
    with pytest.raises(demo.PublicTestnetError, match='purchase_artifacts_invalid'):
        demo.verify_purchase_artifacts({}, input_text=SUMMARY_INPUT, service_id=SUMMARY_ID)


@pytest.mark.parametrize('endpoint', ['http://192.168.68.54:42828', 'https://127.0.0.1:12345', 'http://localhost:12345', 'http://user@127.0.0.1:12345'])
def test_local_example_cannot_contact_other_hosts_or_downgrade_public_requester(endpoint):
    with pytest.raises(demo.PublicTestnetError, match='local_endpoint_invalid'):
        demo.http_exchange(endpoint, 'GET', demo.DISCOVERY_PATH, None, 0.1, allow_local_harness=True)


def test_summary_cli_two_process_product_returns_actual_summary_and_receipt():
    completed = subprocess.run([sys.executable, '-m', 'coin.public_testnet_service_demo', '--role', 'local-example',
                                '--service-id', SUMMARY_ID, '--input', SUMMARY_INPUT],
                               check=False, capture_output=True, text=True, timeout=120)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result['requester_pid'] != result['provider_pid']
    assert result['provider_exit'] == 0 and result['listener_closed'] is True
    assert result['service_output'] == service_core.text_summary(SUMMARY_INPUT)
    assert demo.verify_purchase_artifacts(result['public_artifacts'], input_text=SUMMARY_INPUT, service_id=SUMMARY_ID) == result['service_output']
    assert result['public_artifacts']['receipt']['payment_tx_id'] == result['payment_tx_id']
    assert (result['requester_balance_before'], result['provider_balance_before'],
            result['requester_balance_after'], result['provider_balance_after']) == (100, 0, 72, 28)
    for key in ('service_discovery_verified', 'payment_verified', 'replay_rejected', 'service_result_verified', 'receipt_verified'):
        assert result[key] is True
    for key in ('canonical_history_touched', 'public_network_used', 'external_https_exposure', 'production_settlement'):
        assert result[key] is False
    for forbidden in ('private_key', 'secret_key', 'seed_phrase', 'BEGIN PRIVATE'):
        assert forbidden not in completed.stdout + completed.stderr


def test_failed_summary_input_stops_provider_and_closes_listener(monkeypatch):
    processes, endpoints = [], []
    original_spawn, original_exchange = demo.subprocess.Popen, demo.http_exchange

    def spawn(*args, **kwargs):
        process = original_spawn(*args, **kwargs)
        processes.append(process)
        return process

    def exchange(endpoint, *args, **kwargs):
        endpoints.append(demo.urllib.parse.urlsplit(endpoint))
        return original_exchange(endpoint, *args, **kwargs)

    monkeypatch.setattr(demo.subprocess, 'Popen', spawn)
    monkeypatch.setattr(demo, 'http_exchange', exchange)
    with pytest.raises(service_core.DemoError, match='input_invalid'):
        demo.execute_local_release_example('  ', service_id=SUMMARY_ID)
    assert len(processes) == 1 and processes[0].poll() is not None
    assert processes[0].stdout.closed and processes[0].stderr.closed
    assert endpoints
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        assert probe.connect_ex((endpoints[0].hostname, endpoints[0].port)) != 0


def test_partial_provider_startup_cannot_bypass_deadline_and_is_cleaned(monkeypatch):
    processes = []
    original_spawn = demo.subprocess.Popen

    def spawn(_command, **kwargs):
        process = original_spawn([sys.executable, '-c', "import sys,time;sys.stdout.write('{');sys.stdout.flush();time.sleep(10)"], **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(demo.subprocess, 'Popen', spawn)
    monkeypatch.setattr(demo, 'SESSION_DEADLINE_SECONDS', 5.3)
    with pytest.raises(demo.PublicTestnetError, match='provider_start_timeout'):
        demo.execute_local_release_example(SUMMARY_INPUT, service_id=SUMMARY_ID)
    assert processes[0].poll() is not None
    assert processes[0].stdout.closed and processes[0].stderr.closed


def test_slow_http_response_cannot_extend_absolute_deadline(monkeypatch):
    import time

    processes = []
    original_spawn = demo.subprocess.Popen
    child = '''import json,socket,time
with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as server:
 server.bind(('127.0.0.1',0));server.listen(1)
 print(json.dumps({'coordination':'provider_ready','host':'127.0.0.1','port':server.getsockname()[1]}),flush=True)
 conn,_=server.accept()
 with conn:
  conn.recv(4096);conn.sendall(b'HTTP/1.1 200 OK\\r\\nContent-Length: 100\\r\\n\\r\\n')
  for _ in range(100):conn.sendall(b' ');time.sleep(.1)
'''

    def spawn(_command, **kwargs):
        process = original_spawn([sys.executable, '-c', child], **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(demo.subprocess, 'Popen', spawn)
    monkeypatch.setattr(demo, 'SESSION_DEADLINE_SECONDS', 5.5)
    start = time.monotonic()
    with pytest.raises(demo.PublicTestnetError, match='invocation_timeout'):
        demo.execute_local_release_example(SUMMARY_INPUT, service_id=SUMMARY_ID)
    assert time.monotonic() - start < 2
    assert processes[0].poll() is not None
    assert processes[0].stdout.closed and processes[0].stderr.closed
