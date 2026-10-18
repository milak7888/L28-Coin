# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import public_testnet_service_demo as demo
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
    manifest_path = RELEASE_DIR / "manifest.json"
    sums_path = RELEASE_DIR / "SHA256SUMS"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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
        path = REPO_ROOT / artifact["path"]
        content = path.read_bytes()
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
        assert hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest() == digest


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
