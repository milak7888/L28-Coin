# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import asyncio
import ast
import json
import hashlib
import queue
import struct
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin import persistent_disposable_testnet_node as node
from coin.tx_validation import (
    L28_EMISSION_CEILING,
    L28_HISTORICAL_LAST_ENTRY,
    L28_HISTORICAL_MINED,
    L28_MAX_SUPPLY,
    L28_NEXT_HEIGHT_AFTER_CHECKPOINT,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/persistent_disposable_testnet_node.py"


def _events():
    private_key = Ed25519PrivateKey.generate()
    binding = node.persistent_testnet_binding()
    writer = node.public_identity(node._public_key_hex(private_key))
    events = [
        node._build_coinbase(writer),
        node._build_signed_transfer(private_key, node.follower_identity(binding)),
    ]
    del private_key
    return events


def _tls_pair():
    context = node.lan_context("c" * 32, int(time.time()), "initial",
                               node.lan_source_inventory()["source_digest"])
    identities = [node.MemoryTLSIdentity(role) for role in ("writer", "follower")]
    endpoints = [node.PinnedTLSHandoff(identities[0], identities[1].pin, context, node.LAN_FOLLOWER_IP),
                 node.PinnedTLSHandoff(identities[1], identities[0].pin, context, node.LAN_WRITER_IP)]
    return context, identities, endpoints


def _finish_tls(endpoints):
    for _ in range(128):
        for endpoint in endpoints:
            endpoint.advance()
        for i, endpoint in enumerate(endpoints):
            wire = endpoint.drain()
            if wire:
                endpoints[1-i].feed(wire)
        if all(endpoint.complete for endpoint in endpoints):
            return
    raise AssertionError("TLS handoff did not finish")


def test_endpoint_amendment_binds_context_certificate_and_rejects_retired_peer():
    from cryptography import x509
    from ipaddress import ip_address

    assert (node.LAN_WRITER_IP, node.LAN_FOLLOWER_IP, node.LAN_PORT) == (
        "192.168.68.50", "192.168.68.54", 42828)
    context = node.lan_context("c" * 32, int(time.time()), "initial",
                               node.lan_source_inventory()["source_digest"])
    assert (context["writer"], context["follower"], context["port"]) == (
        "192.168.68.50", "192.168.68.54", 42828)
    identities = [node.MemoryTLSIdentity(role) for role in ("writer", "follower")]
    try:
        for identity, address in zip(identities, ("192.168.68.50", "192.168.68.54")):
            san = identity.certificate.extensions.get_extension_for_class(
                x509.SubjectAlternativeName).value
            assert san.get_values_for_type(x509.IPAddress) == [ip_address(address)]
        with pytest.raises(node.PersistentNodeError, match="^tls_peer_binding_invalid$"):
            node.PinnedTLSHandoff(identities[0], identities[1].pin, context,
                                  "192.168.68.75")
        retired = dict(context, follower="192.168.68.75")
        with pytest.raises(node.PersistentNodeError):
            node._handoff_context(retired)
    finally:
        for identity in identities:
            identity.close()
    assert all(identity.closed and identity._key is None for identity in identities)


def test_handoff_actual_tls_and_existing_hmac_are_memory_only(monkeypatch, capsys, caplog):
    # Preload dependency modules before guarding file writes and forbidden APIs.
    SSL = node._tls_backend()
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    import builtins
    import io
    import os
    generated, encrypted = [], []
    original_random = node.secrets.token_bytes
    original_drain = node.PinnedTLSHandoff.drain
    original_open = builtins.open
    original_os_open = os.open

    def random_secret(size):
        result = original_random(size)
        generated.append(result)
        return result
    def drain(endpoint):
        result = original_drain(endpoint)
        encrypted.append(result)
        return result
    def no_write(file, mode="r", *args, **kwargs):
        if any(c in mode for c in "wax+"):
            raise AssertionError("file write during handoff")
        return original_open(file, mode, *args, **kwargs)
    def no_os_write(file, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise AssertionError("OS file write during handoff")
        return original_os_open(file, flags, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("forbidden socket, process, or TLS file loader")
    monkeypatch.setattr(node.secrets, "token_bytes", random_secret)
    monkeypatch.setattr(node.PinnedTLSHandoff, "drain", drain)
    monkeypatch.setattr(builtins, "open", no_write)
    monkeypatch.setattr(io, "open", no_write)
    monkeypatch.setattr(os, "open", no_os_write)
    monkeypatch.setattr(node.socket, "socket", forbidden)
    monkeypatch.setattr(node.subprocess, "Popen", forbidden)
    monkeypatch.setattr(SSL.Context, "use_certificate_file", forbidden)
    monkeypatch.setattr(SSL.Context, "use_privatekey_file", forbidden)
    monkeypatch.setattr(SSL.Context, "set_keylog_callback", forbidden)
    assert node.main(["--offline-auth-handoff"]) == 0
    output = capsys.readouterr()
    report = json.loads(output.out)
    assert report["both_node_roles_authenticated"]
    assert report["mutual_certificate_pins_verified"]
    assert report["cleanup_complete"] and report["single_use_inputs_consumed"]
    assert not report["physical_two_host_verified"]
    # token_hex uses token_bytes too: select the one 32-byte authentication value
    # that actually appears inside TLS delivery, never in ciphertext or evidence.
    evidence = (output.out + output.err + caplog.text).encode()
    assert generated and any(encrypted)
    for secret in generated:
        assert secret not in evidence and secret.hex().encode() not in evidence
        assert all(secret not in wire and secret.hex().encode() not in wire for wire in encrypted)


@pytest.mark.parametrize("case,code", [
    ("wrong-pin", "tls_peer_or_record_authentication_failed"),
    ("wrong-peer", "tls_peer_binding_invalid"),
    ("expired", "lan_session_invalid_or_expired"),
    ("incomplete", "tls_delivery_incomplete"),
    ("tamper", "tls_peer_or_record_authentication_failed"),
    ("replay", "tls_peer_or_record_authentication_failed"),
])
def test_handoff_negative_cases_release_all_owned_credentials(case, code, monkeypatch):
    identities, endpoints = [], []
    identity_init = node.MemoryTLSIdentity.__init__
    endpoint_init = node.PinnedTLSHandoff.__init__
    def identity(self, *args, **kwargs):
        identity_init(self, *args, **kwargs)
        identities.append(self)
    def endpoint(self, *args, **kwargs):
        endpoints.append(self)
        endpoint_init(self, *args, **kwargs)
    monkeypatch.setattr(node.MemoryTLSIdentity, "__init__", identity)
    monkeypatch.setattr(node.PinnedTLSHandoff, "__init__", endpoint)
    with pytest.raises(node.PersistentNodeError) as failure:
        node.execute_offline_auth_handoff(case)
    assert failure.value.code == code
    assert all(i.closed and i._key is None and i.certificate is None for i in identities)
    assert all(e.closed and not e._secret and not e._incoming and e._connection is None for e in endpoints)


def test_handoff_material_matches_roles_and_is_consumed_once():
    context, identities, endpoints = _tls_pair()
    materials = []
    try:
        _finish_tls(endpoints)
        materials = [e.take_material() for e in endpoints]
        left = materials[0].consume("writer", context)
        right = materials[1].consume("follower", context)
        assert __import__("hmac").compare_digest(left, right)
        assert len(left) == 32 and all(m.closed and not m._material for m in materials)
        assert "redacted" in repr(materials[0])
        with pytest.raises(node.PersistentNodeError, match="binding_invalid"):
            materials[0].consume("writer", context)
        del left, right
    finally:
        for material in materials:
            material.close()
        for endpoint in endpoints:
            endpoint.close()
        for identity in identities:
            identity.close()


@pytest.mark.parametrize("field,value", [("role", "follower"), ("source_digest", "0" * 64),
                                         ("session", "d" * 32), ("phase", "restart")])
def test_handoff_wrong_input_binding_discards_material(field, value):
    context, identities, endpoints = _tls_pair()
    material = None
    try:
        _finish_tls(endpoints)
        material = endpoints[0].take_material()
        role, altered = "writer", deepcopy(context)
        if field == "role":
            role = value
        else:
            altered[field] = value
        with pytest.raises(node.PersistentNodeError):
            material.consume(role, altered)
        assert material.closed and not material._material
    finally:
        if material:
            material.close()
        for endpoint in endpoints:
            endpoint.close()


@pytest.mark.parametrize("operation", ["advance", "feed", "drain", "take_material"])
def test_handoff_expiry_closes_endpoint_on_every_interface(operation):
    context, identities, endpoints = _tls_pair()
    try:
        endpoint = endpoints[0]
        endpoint._deadline = 0
        with pytest.raises(node.PersistentNodeError, match="deadline"):
            getattr(endpoint, operation)(b"invalid") if operation == "feed" else getattr(endpoint, operation)()
        assert endpoint.closed and endpoint._connection is None and identities[0].closed
    finally:
        for endpoint in endpoints:
            endpoint.close()


def test_handoff_incomplete_material_cannot_reach_node():
    context, identities, endpoints = _tls_pair()
    try:
        with pytest.raises(node.PersistentNodeError, match="delivery_incomplete"):
            endpoints[0].take_material()
        assert endpoints[0].closed and not endpoints[0]._secret
    finally:
        for endpoint in endpoints:
            endpoint.close()


@pytest.mark.parametrize("payload", [{"nonce": "not-hex"}, {"nonce": True}, {},
                                    {"nonce": "0" * 64, "extra": 1}])
def test_handoff_malformed_authenticated_frames_reject(payload):
    context, identities, endpoints = _tls_pair()
    try:
        endpoint = endpoints[0]
        endpoint._state = "wait_ready"
        packet = {"profile": node.HANDOFF_PROFILE, "context": context, "role": "follower",
                  "sequence": 1, "type": "ready", "payload": payload}
        with pytest.raises(node.PersistentNodeError):
            endpoint._accept(node._canonical_bytes(packet))
        assert not endpoint._secret
    finally:
        for endpoint in endpoints:
            endpoint.close()


def test_handoff_authentication_failure_and_in_memory_node_input(monkeypatch, tmp_path):
    context, identities, endpoints = _tls_pair()
    material = None
    try:
        _finish_tls(endpoints)
        material = endpoints[0].take_material()
        called = []
        def no_socket(*args, **kwargs):
            called.append(True)
            raise node.PersistentNodeError("offline_socket_boundary")
        monkeypatch.setattr(node.socket, "socket", no_socket)
        args = ["--lan", "--role", "writer", "--phase", "initial", "--session-id", context["session"],
                "--session-start", str(context["started"]), "--data-dir", str(tmp_path / "unused"), "--ack-private-lan"]
        assert node.main(args, authentication=material) == 1
        assert called and material.closed and not (tmp_path / "unused").exists()
    finally:
        if material:
            material.close()
        for endpoint in endpoints:
            endpoint.close()


def test_handoff_cli_rejects_mode_confusion(capsys):
    assert node.main(["--offline-auth-handoff", "--source-inventory"]) == 1
    assert capsys.readouterr().err.strip() == "offline_handoff_arguments_invalid"
    assert node.main(["--handoff-case", "tamper"]) == 1
    assert capsys.readouterr().err.strip() == "offline_handoff_mode_required"


def test_handoff_follower_also_requires_the_exact_writer_pin():
    context = node.lan_context("e" * 32, int(time.time()), "initial",
                              node.lan_source_inventory()["source_digest"])
    identities = [node.MemoryTLSIdentity(r) for r in ("writer", "follower")]
    endpoints = [node.PinnedTLSHandoff(identities[0], identities[1].pin, context, node.LAN_FOLLOWER_IP),
                 node.PinnedTLSHandoff(identities[1], "0" * 64, context, node.LAN_WRITER_IP)]
    try:
        with pytest.raises(node.PersistentNodeError, match="peer_or_record_authentication_failed"):
            _finish_tls(endpoints)
        assert not any(e.complete for e in endpoints)
    finally:
        for endpoint in endpoints:
            endpoint.close()


@pytest.mark.parametrize("field,value", [("source_digest", "0" * 64), ("version", True),
                                        ("writer", "192.168.68.51"), ("started", True)])
def test_handoff_context_requires_real_source_and_exact_types(field, value):
    context = node.lan_context("e" * 32, int(time.time()), "initial",
                              node.lan_source_inventory()["source_digest"])
    identity = node.MemoryTLSIdentity("writer")
    context[field] = value
    with pytest.raises(node.PersistentNodeError):
        node.PinnedTLSHandoff(identity, "0" * 64, context, node.LAN_FOLLOWER_IP)
    assert identity.closed and identity._key is None


@pytest.mark.parametrize("kind", ["malformed-secret", "wrong-proof", "duplicate", "wrong-session", "noncanonical"])
def test_handoff_authenticated_application_rejections(kind):
    context, identities, endpoints = _tls_pair()
    try:
        endpoint = endpoints[1]
        endpoint._state, endpoint._nonce = "wait_deliver", "f" * 64
        body = {"profile": node.HANDOFF_PROFILE, "context": context, "role": "writer", "sequence": 1,
                "type": "deliver", "payload": {"nonce": endpoint._nonce, "writer_nonce": "e" * 64, "secret": "not-valid-material"}}
        if kind == "wrong-proof":
            endpoint._state = "wait_commit"
            endpoint._secret = bytearray(node.secrets.token_bytes(32))
            endpoint._writer_nonce = "e" * 64
            body.update(type="commit", payload={"proof": "0" * 64})
        elif kind == "duplicate":
            endpoint._received = 1
        elif kind == "wrong-session":
            body["context"] = {**context, "session": "f" * 32}
        raw = (json.dumps(body).encode() if kind == "noncanonical" else node._canonical_bytes(body))
        with pytest.raises(node.PersistentNodeError):
            endpoint._accept(raw)
        assert not endpoint.complete
    finally:
        for endpoint in endpoints:
            endpoint.close()
        assert all(not e._secret and e.closed for e in endpoints)


def test_handoff_hmac_failure_has_bounded_cleanup_and_public_error(monkeypatch, capsys):
    original = node.LanChannel.authenticate
    def mismatch(channel):
        if channel.role == "follower":
            channel.key = b"different-public-fixture-key".ljust(32, b"0")
        return original(channel)
    monkeypatch.setattr(node.LanChannel, "authenticate", mismatch)
    assert node.main(["--offline-auth-handoff"]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert output.err.strip() == "offline_hmac_authentication_failed"
    assert not any(t.name.startswith("Thread-") and t.is_alive() and t.daemon
                   for t in __import__("threading").enumerate())


def test_handoff_endpoint_limits_reject_oversize_before_allocation():
    context, identities, endpoints = _tls_pair()
    try:
        with pytest.raises(node.PersistentNodeError, match="wire_invalid"):
            endpoints[0].feed(b"x" * (2 * node.MAX_FRAME_BYTES + 1))
        assert endpoints[0].closed and not endpoints[0]._secret
    finally:
        for endpoint in endpoints:
            endpoint.close()


def test_handoff_structure_has_no_secret_file_or_display_calls():
    tree = ast.parse(IMPL_PATH.read_text())
    forbidden = {"private_bytes", "use_privatekey_file", "use_certificate_file", "set_keylog_callback", "getpass"}
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr in forbidden for n in ast.walk(tree))


def test_handoff_partial_identity_failure_discards_private_reference(monkeypatch):
    from cryptography import x509
    identity = node.MemoryTLSIdentity.__new__(node.MemoryTLSIdentity)
    def fail(*args, **kwargs):
        raise ValueError("public fixture failure")
    monkeypatch.setattr(x509.CertificateBuilder, "sign", fail)
    with pytest.raises(node.PersistentNodeError, match="tls_identity_creation_failed"):
        identity.__init__("writer")
    assert identity.closed and identity._key is None and identity.certificate is None


@pytest.mark.parametrize("argv", [["--source-inventory"], ["--session-start", "not-numeric"]])
def test_handoff_invalid_cli_input_closes_material(argv):
    context = node.lan_context("e" * 32, int(time.time()), "initial",
                               node.lan_source_inventory()["source_digest"])
    material = node.HandoffMaterial(bytearray(b"public-test-only-fixture".ljust(32, b"0")), "writer", context)
    if "not-numeric" in argv:
        with pytest.raises(SystemExit) as failure:
            node.main(argv, authentication=material)
        assert failure.value.code == 2
    else:
        assert node.main(argv, authentication=material) == 1
    assert material.closed and not material._material


def test_coordinator_actual_offline_execution_is_nondisclosing_and_cleans_up(monkeypatch, capsys, caplog):
    SSL = node._tls_backend()
    generated, removed = [], []
    original_random, original_remove = node.secrets.token_bytes, node.shutil.rmtree
    original_socket = node.socket.socket
    def random(size):
        value = original_random(size)
        if size == 32:
            generated.append(value)
        return value
    def remove(root, *args, **kwargs):
        assert root.name.startswith("l28-disposable-lan-")
        for path in root.rglob("*"):
            if path.is_file():
                raw = path.read_bytes()
                assert b"BEGIN PRIVATE" not in raw
                assert all(value not in raw and value.hex().encode() not in raw for value in generated)
        removed.append(root)
        return original_remove(root, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("offline coordinator attempted socket/process or credential-file API")
    def no_network(family=node.socket.AF_INET, *args, **kwargs):
        # Existing asyncio ledger execution uses local self-pipe socketpairs.
        if family == node.socket.AF_UNIX:
            return original_socket(family, *args, **kwargs)
        return forbidden()
    monkeypatch.setattr(node.secrets, "token_bytes", random)
    monkeypatch.setattr(node.shutil, "rmtree", remove)
    monkeypatch.setattr(node.socket, "socket", no_network)
    monkeypatch.setattr(node.subprocess, "Popen", forbidden)
    monkeypatch.setattr(SSL.Context, "use_privatekey_file", forbidden)
    monkeypatch.setattr(SSL.Context, "use_certificate_file", forbidden)
    monkeypatch.setattr(SSL.Context, "set_keylog_callback", forbidden)
    assert node.main(["--offline-coordinator"]) == 0
    output = capsys.readouterr()
    report = json.loads(output.out.splitlines()[-1])
    assert report["result"] == "OFFLINE_COORDINATOR_PASS"
    assert report["state"]["issued_supply"] == 28
    assert sorted(report["state"]["balances"].values()) == [0, 28]
    assert len(report["state"]["transaction_ids"]) == 2
    assert all(report[k] for k in ("cleanup_complete", "pinned_tls_and_hmac_verified",
               "independent_validation", "durable_reopen_agreement", "replay_rejected", "divergence_halted"))
    assert not report["physical_two_host_verified"] and not report["physical_process_restart_verified"]
    assert report["prepared_public_records_verified"] and not report["physical_inspection_verified"]
    assert len(removed) == 2 and all(not p.exists() for p in removed)
    evidence = (output.out + output.err + caplog.text).encode()
    assert generated and all(v not in evidence and v.hex().encode() not in evidence for v in generated)


@pytest.mark.parametrize("case,code", [
    ("wrong-pin", "tls_peer_or_record_authentication_failed"),
    ("wrong-peer", "coordinator_peer_address_invalid"),
    ("source-mismatch", "coordinator_enrollment_binding_invalid"),
    ("interrupted", "coordinator_interrupted"),
    ("tamper", "tls_peer_or_record_authentication_failed"),
    ("bootstrap-context", "tls_frame_binding_invalid"),
    ("bootstrap-pin", "coordinator_pin_mismatch"),
    ("unverified-record", "coordinator_physical_verification_required"),
    ("substituted-record", "coordinator_prepared_record_invalid"),
    ("wrong-record-source", "coordinator_prepared_record_invalid"),
    ("wrong-record-role", "coordinator_prepared_record_invalid"),
])
def test_coordinator_negative_paths_fail_closed_and_dispose_resources(case, code, monkeypatch, capsys):
    identities, pipes = [], []
    identity_init, pipe_init = node.MemoryTLSIdentity.__init__, node._OfflinePipe.__init__
    def identity(self, *args, **kwargs):
        identity_init(self, *args, **kwargs)
        identities.append(self)
    def pipe(self, *args, **kwargs):
        pipe_init(self, *args, **kwargs)
        pipes.append(self)
    monkeypatch.setattr(node.MemoryTLSIdentity, "__init__", identity)
    monkeypatch.setattr(node._OfflinePipe, "__init__", pipe)
    assert node.main(["--offline-coordinator", "--coordinator-case", case]) == 1
    output = capsys.readouterr()
    assert not output.out and output.err.strip() == code
    assert all(i.closed and i._key is None for i in identities)
    assert all(p.closed for p in pipes)


@pytest.mark.parametrize("field,value", [("profile", "other"), ("role", "follower"),
    ("pin", "not-a-pin"), ("source_digest", "0" * 64), ("extra", True),
    ("started", True), ("writer", "192.168.68.51"), ("network", "OTHER")])
def test_coordinator_enrollment_has_exact_public_bindings(field, value):
    context = node.lan_context("c" * 32, int(time.time()), "initial",
                               node.lan_source_inventory()["source_digest"])
    peer = {"profile": node.ENROLLMENT_PROFILE, "role": "writer", "pin": "f" * 64,
            "source_digest": context["source_digest"], "context": context}
    if field in ("started", "writer", "network"):
        peer["context"][field] = value
    else:
        peer[field] = value
    with pytest.raises(node.PersistentNodeError):
        node._coordinator_peer(peer, "follower", None)


def test_coordinator_automatic_start_and_public_enrollment_only():
    context = node.lan_context("c" * 32, int(time.time()), "initial",
                               node.lan_source_inventory()["source_digest"])
    identity = node.MemoryTLSIdentity("writer")
    try:
        enrollment = node._coordinator_enrollment(identity, context)
        received = node._coordinator_peer(enrollment, "follower", None)
        assert type(received["started"]) is int and received == context
        assert set(enrollment) == {"profile", "role", "pin", "source_digest", "context"}
        assert "secret" not in node._canonical_bytes(enrollment).decode()
        assert "private" not in node._canonical_bytes(enrollment).decode()
    finally:
        identity.close()


@pytest.mark.parametrize("argv", [
    ["--coordinate", "--source-inventory"], ["--offline-coordinator", "--lan"],
    ["--runtime-check", "--phase", "initial"], ["--coordinator-case", "wrong-pin"],
    ["--coordinate", "--role", "writer", "--phase", "initial", "--session-start", "1", "--ack-private-lan"],
])
def test_coordinator_cli_conflicts_reject_before_any_socket(argv, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected runtime operation")
    monkeypatch.setattr(node.socket, "socket", forbidden)
    monkeypatch.setattr(node.MemoryTLSIdentity, "__init__", forbidden)
    assert node.main(argv) == 1
    output = capsys.readouterr()
    assert "PASS" not in output.out and output.err


def test_coordinator_runtime_source_parity_is_fail_closed(capsys):
    digest = node.lan_source_inventory()["source_digest"]
    assert node.main(["--runtime-check", "--expected-source-digest", digest]) == 0
    assert json.loads(capsys.readouterr().out)["network_started"] is False
    assert node.main(["--runtime-check", "--expected-source-digest", "0" * 64]) == 1
    output = capsys.readouterr()
    assert not output.out and output.err.strip() == "coordinator_source_parity_invalid"


@pytest.mark.parametrize("value", ["not-json", "{}", "0" * 64])
def test_coordinator_bad_public_input_never_prints_pass_or_generates_auth(value, monkeypatch, capsys):
    identities = []
    original = node.MemoryTLSIdentity.__init__
    def identity(self, *args):
        original(self, *args)
        identities.append(self)
    def forbidden(*args, **kwargs):
        raise AssertionError("socket opened before enrollment")
    monkeypatch.setattr(node.MemoryTLSIdentity, "__init__", identity)
    monkeypatch.setattr(node, "_coordinator_public_input", lambda *args: value)
    monkeypatch.setattr(node.socket, "socket", forbidden)
    assert node.main(["--coordinate", "--role", "writer", "--phase", "initial", "--ack-private-lan",
                      "--expected-source-digest", node.lan_source_inventory()["source_digest"]]) == 1
    output = capsys.readouterr()
    assert "PASS" not in output.out and output.err
    assert identities and all(i.closed and i._key is None for i in identities)


@pytest.mark.parametrize("characters,expected", [("PUBLIC\r", "PUBLIC"), ("AB\bC\r", "AC"),
                                             ("\xe0", None), ("\x01", None)])
def test_coordinator_windows_public_input_is_bounded(characters, expected, monkeypatch):
    from collections import deque
    from types import SimpleNamespace
    pending = deque(characters)
    monkeypatch.setattr(node.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(node.sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(kbhit=lambda: bool(pending), getwch=pending.popleft))
    if expected is None:
        with pytest.raises(node.PersistentNodeError, match="public_input_invalid"):
            node._coordinator_public_input("PUBLIC only", time.monotonic() + 1)
    else:
        assert node._coordinator_public_input("PUBLIC only", time.monotonic() + 1) == expected
    with pytest.raises(node.PersistentNodeError, match="deadline_expired"):
        node._coordinator_public_input("PUBLIC only", 0)


def test_coordinator_transport_rejects_oversized_or_incomplete_tls_frames():
    for wire, code in [(struct.pack(">I", 2 * node.MAX_FRAME_BYTES + 1), "tls_wire_limit_exceeded"),
                       (b"", "coordinator_interrupted")]:
        context, identities, endpoints = _tls_pair()
        pipes = [node._OfflinePipe("writer"), node._OfflinePipe("follower")]
        pipes[0].other, pipes[1].other = pipes[1], pipes[0]
        pipes[0].queue.put(wire)
        try:
            with pytest.raises(node.PersistentNodeError, match=code):
                node._coordinator_handoff(pipes[0], endpoints[0], time.monotonic() + 1)
        finally:
            for endpoint in endpoints:
                endpoint.close()
            for pipe in pipes:
                pipe.close()


def test_coordinator_both_cli_roles_use_public_enrollment_and_close_listener(monkeypatch, tmp_path):
    import threading
    from types import SimpleNamespace
    monkeypatch.setattr(node.tempfile, "gettempdir", lambda: str(tmp_path))
    public, reports, errors, exits = {}, [], [], []
    inputs = {"writer": [], "follower": []}
    enrolled, listening = threading.Condition(), threading.Event()
    pipes = [node._OfflinePipe("writer"), node._OfflinePipe("follower")]
    pipes[0].other, pipes[1].other = pipes[1], pipes[0]
    listeners = []
    original_socket = node.socket.socket
    class Listener:
        closed = False
        def settimeout(self, timeout):
            pass
        def bind(self, address):
            assert address == (node.LAN_FOLLOWER_IP, node.LAN_PORT)
        def listen(self, backlog):
            assert backlog == 1
            listening.set()
        def accept(self):
            return pipes[1], (node.LAN_WRITER_IP, 42829)
        def shutdown(self, how):
            self.closed = True
        def close(self):
            self.closed = True
    def emit(value):
        reports.append(value)
        if value.get("status") == "PUBLIC_ENROLLMENT":
            with enrolled:
                public[value["enrollment"]["role"]] = value["enrollment"]
                enrolled.notify_all()
    def read(prompt, deadline):
        role = threading.current_thread().name
        inputs[role].append(prompt)
        if "READY" in prompt:
            assert role == "writer", "follower requested redundant READY input"
            assert listening.wait(2)
            return "READY"
        peer = "follower" if role == "writer" else "writer"
        with enrolled:
            assert enrolled.wait_for(lambda: peer in public, timeout=2)
            return "VERIFIED " + node._canonical_bytes({"status": "PUBLIC_ENROLLMENT", "enrollment": public[peer]}).decode()
    def socket(family, *args, **kwargs):
        if family == node.socket.AF_UNIX:
            return original_socket(family, *args, **kwargs)
        assert family == node.socket.AF_INET
        if threading.current_thread().name == "follower":
            listener = Listener()
            listeners.append(listener)
            return listener
        pipes[0].bind = lambda address: None if address == (node.LAN_WRITER_IP, 0) else pytest.fail("bad writer bind")
        pipes[0].connect = lambda address: None if address == (node.LAN_FOLLOWER_IP, node.LAN_PORT) else pytest.fail("bad destination")
        return pipes[0]
    def run(role):
        args = SimpleNamespace(role=role, phase="initial", ack_private_lan=True, port=None,
             session_id=None, session_start=None, data_dir=None,
             expected_source_digest=node.lan_source_inventory()["source_digest"])
        try:
            exits.append(node.coordinator_main(args))
        except Exception as exc:
            errors.append(type(exc).__name__)
    monkeypatch.setattr(node, "_emit", emit)
    monkeypatch.setattr(node, "_coordinator_public_input", read)
    monkeypatch.setattr(node.socket, "socket", socket)
    workers = [threading.Thread(target=run, args=(r,), name=r, daemon=True) for r in ("writer", "follower")]
    try:
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=5)
        assert not any(w.is_alive() for w in workers)
        assert not errors and exits == [0, 0]
        results = [r for r in reports if r.get("result") == "COORDINATOR_PHASE_PASS"]
        assert len(results) == 2 and results[0]["state"] == results[1]["state"]
        assert all(r["pinned_tls_handoff_verified"] for r in results)
        assert type(results[0]["session_start"]) is int
        assert results[0]["session_start"] == results[1]["session_start"]
        assert all(p["context"] is None and "certificate_der" in p for p in public.values())
        assert len([r for r in reports if r.get("status") == "PREPARED_ENROLLED"]) == 2
        assert len(inputs["follower"]) == 1 and len(inputs["writer"]) == 2
    finally:
        for pipe in pipes:
            pipe.close()
        for worker in workers:
            worker.join(timeout=2)
    assert listeners and all(l.closed for l in listeners) and all(p.closed for p in pipes)


@pytest.mark.parametrize("role,stage", [("follower", "bind"), ("follower", "listen"),
                                      ("follower", "accept"), ("writer", "connect"), ("follower", "close")])
def test_coordinator_socket_setup_failure_closes_identity_and_listener(role, stage, monkeypatch, capsys):
    context = node.lan_context("c" * 32, int(time.time()), "initial",
                               node.lan_source_inventory()["source_digest"])
    peer = {"profile": node.ENROLLMENT_PROFILE, "role": "writer" if role == "follower" else "follower",
            "pin": "f" * 64, "source_digest": context["source_digest"],
            "context": context if role == "follower" else None}
    identities, sockets = [], []
    peer_identity = node.MemoryTLSIdentity("writer" if role == "follower" else "follower")
    try:
        prepared = "VERIFIED " + node._canonical_bytes(node._coordinator_prepared_record(peer_identity, "initial", None)).decode()
    finally:
        peer_identity.close()
    identity_init = node.MemoryTLSIdentity.__init__
    def identity(self, *args):
        identity_init(self, *args)
        identities.append(self)
    class FailingSocket:
        closed = False
        def settimeout(self, timeout):
            assert 0 < timeout <= node.PARENT_DEADLINE_SECONDS
        def bind(self, address):
            if stage in ("bind", "close"):
                raise OSError("public fixture")
        def listen(self, backlog):
            if stage == "listen":
                raise OSError("public fixture")
        def accept(self):
            raise OSError("public fixture")
        def connect(self, address):
            raise OSError("public fixture")
        def shutdown(self, how):
            self.closed = True
        def close(self):
            self.closed = True
            if stage == "close":
                raise OSError("public fixture close failure")
    def socket(*args):
        value = FailingSocket()
        sockets.append(value)
        return value
    monkeypatch.setattr(node.MemoryTLSIdentity, "__init__", identity)
    monkeypatch.setattr(node.socket, "socket", socket)
    monkeypatch.setattr(node, "_coordinator_public_input",
                        lambda prompt, deadline: "READY" if "READY" in prompt else prepared)
    assert node.main(["--coordinate", "--role", role, "--phase", "initial", "--ack-private-lan",
                      "--expected-source-digest", context["source_digest"]]) == 1
    output = capsys.readouterr()
    assert "PASS" not in output.out
    assert output.err.strip() == ("coordinator_cleanup_failed" if stage == "close" else "coordinator_io_failure")
    assert identities and all(i.closed and i._key is None for i in identities)
    assert sockets and all(s.closed for s in sockets)


@pytest.mark.parametrize("mutation", ["supply", "source", "role", "start"])
def test_coordinator_restart_rejects_altered_public_metadata(mutation, monkeypatch, tmp_path):
    monkeypatch.setattr(node.tempfile, "gettempdir", lambda: str(tmp_path))
    context = node.lan_context("c" * 32, int(time.time()), "initial",
                               node.lan_source_inventory()["source_digest"])
    root = tmp_path / ("l28-disposable-lan-" + context["session"] + "-writer")
    root.mkdir()
    metadata = {k: v for k, v in context.items() if k != "phase"}
    metadata["role"] = "writer"
    if mutation == "supply":
        metadata["supply"] = 28
    elif mutation == "source":
        metadata["source_digest"] = "0" * 64
    elif mutation == "role":
        metadata["role"] = "follower"
    else:
        metadata["started"] = True
    (root / "session.json").write_bytes(node._canonical_bytes(metadata))
    with pytest.raises(node.PersistentNodeError):
        node._coordinator_restart_context(root, "writer")


@pytest.fixture
def coordinator_clock(monkeypatch):
    """Offline control-flow clock; real TLS/ledger coverage stays in existing tests."""
    from types import SimpleNamespace
    baseline = time.time()
    clock = SimpleNamespace(elapsed=0.0, wall=baseline, timers=[], identities=[],
                            sockets=[], transitions=[], tokens=[], delay=0.0,
                            active_delay=0.0, ready_delay=0.0, ready_value="READY", join_delay=0.0,
                            raw_override=None, attested=True, record_mutation=None,
                            restart_context=None, input_error=None, input_exception=None, inputs=[])
    peer_records = {}
    for role in ("writer", "follower"):
        peer_identity = node.MemoryTLSIdentity(role)
        try:
            peer_records[role] = node._coordinator_prepared_record(peer_identity, "initial", None)
        finally:
            peer_identity.close()
    monkeypatch.setattr(node.time, "monotonic", lambda: 1000.0 + clock.elapsed)
    monkeypatch.setattr(node.time, "time", lambda: clock.wall + clock.elapsed)
    class Timer:
        def __init__(self, seconds, callback):
            self.seconds, self.callback = seconds, callback
            self.ident, self.cancelled, self.joined = None, False, False
            clock.timers.append(self)
        def start(self):
            self.ident = 1
        def cancel(self):
            self.cancelled = True
        def join(self, timeout=None):
            if not self.joined and self is clock.timers[0]:
                clock.elapsed += clock.join_delay
            self.joined = True
    class Socket:
        closed = False
        def __init__(self, *args):
            clock.sockets.append(self)
        def settimeout(self, timeout):
            assert 0 < timeout <= 120
        def bind(self, address):
            pass
        def listen(self, backlog):
            pass
        def accept(self):
            return Socket(), (node.LAN_WRITER_IP, 42829)
        def connect(self, address):
            pass
        def shutdown(self, how):
            pass
        def close(self):
            self.closed = True
        def recv(self, size):
            raise AssertionError("expired runtime attempted a read")
    original_identity, original_token = node.MemoryTLSIdentity.__init__, node.secrets.token_hex
    def identity(self, *args):
        original_identity(self, *args)
        clock.identities.append(self)
    def token(size):
        clock.tokens.append(clock.elapsed)
        return original_token(size)
    def public_input(prompt, deadline):
        clock.inputs.append(prompt)
        assert not clock.sockets and not clock.transitions and not clock.tokens
        assert len(clock.timers) == 1 and 0 < clock.timers[0].seconds <= 600
        if "READY" in prompt:
            clock.elapsed += clock.ready_delay
            return clock.ready_value
        clock.elapsed += (clock.identities[-1].certificate.not_valid_after_utc.timestamp() - clock.wall
                          if clock.delay == "expiry" else clock.delay)
        if clock.input_exception is not None:
            raise clock.input_exception
        if clock.input_error:
            raise node.PersistentNodeError(clock.input_error)
        if clock.raw_override is not None:
            return clock.raw_override
        role = "writer" if clock.identities[-1].role == "follower" else "follower"
        record = deepcopy(peer_records[role])
        if clock.restart_context is not None:
            record["enrollment"].update(phase="restart", context=clock.restart_context)
        if clock.record_mutation:
            clock.record_mutation(record)
        return ("VERIFIED " if clock.attested else "") + node._canonical_bytes(record).decode()
    def connected(sock, identity, peer, context, root, deadline):
        clock.transitions.append((clock.elapsed, deadline, context))
        if clock.active_delay:
            clock.elapsed += clock.active_delay
            node._coordinator_read(sock, 1, deadline)
        return {"timing_fixture_only": True}
    def forbidden(*args, **kwargs):
        raise AssertionError("timing fixture attempted ledger activity")
    monkeypatch.setattr(node.threading, "Timer", Timer)
    monkeypatch.setattr(node.MemoryTLSIdentity, "__init__", identity)
    monkeypatch.setattr(node.secrets, "token_hex", token)
    monkeypatch.setattr(node.socket, "socket", Socket)
    monkeypatch.setattr(node, "_coordinator_public_input", public_input)
    monkeypatch.setattr(node, "_coordinator_connected", connected)
    monkeypatch.setattr(node, "_lan_open_state", forbidden)
    return clock


def _clock_coordinator(role="writer", phase="initial"):
    return node.main(["--coordinate", "--role", role, "--phase", phase,
                      *(["--data-dir", "/public-timing-fixture"] if phase == "restart" else []),
                      "--ack-private-lan", "--expected-source-digest",
                      node.lan_source_inventory()["source_digest"]])


def _assert_clock_cleanup(clock):
    assert clock.identities and all(i.closed and i._key is None for i in clock.identities)
    assert all(s.closed for s in clock.sockets)
    assert clock.timers and all(t.cancelled and t.joined for t in clock.timers)


@pytest.fixture
def prepared_records():
    identities = [node.MemoryTLSIdentity(role) for role in ("writer", "follower")]
    try:
        records = [node._coordinator_prepared_record(i, "initial", None) for i in identities]
        yield identities, records
    finally:
        for identity in identities:
            identity.close()


def test_prepared_complete_record_is_public_and_preserves_identity(prepared_records):
    identities, records = prepared_records
    key, certificate = identities[0]._key, identities[0].certificate
    peer, expiration = node._coordinator_prepared_peer(
        "VERIFIED " + node._canonical_bytes(records[1]).decode(), identities[0], "initial", None)
    assert peer == node._coordinator_enrollment(identities[1], None)
    assert expiration == identities[1].certificate.not_valid_after_utc.timestamp()
    assert identities[0]._key is key and identities[0].certificate is certificate
    assert set(records[1]) == {"status", "enrollment"}
    assert "private" not in node._canonical_bytes(records[1]).decode()
    assert "secret" not in node._canonical_bytes(records[1]).decode()


@pytest.mark.parametrize("mutation", ["profile", "status", "role", "source", "writer", "follower",
    "port", "bool_port", "phase", "context", "missing", "extra", "certificate", "substitution",
    "signature", "duplicate", "noncanonical", "oversized", "unverified", "pin_only"])
def test_prepared_record_rejects_malformed_substituted_and_unverified_input(mutation, prepared_records):
    identities, records = prepared_records
    record = deepcopy(records[1])
    peer = record["enrollment"]
    if mutation in ("profile", "role", "writer", "follower", "phase"):
        peer[mutation] = "OTHER"
    elif mutation == "status":
        record["status"] = "OTHER"
    elif mutation == "source":
        peer["source_digest"] = "0" * 64
    elif mutation == "port":
        peer["port"] = 42829
    elif mutation == "bool_port":
        peer["port"] = True
    elif mutation == "context":
        peer["context"] = {}
    elif mutation == "missing":
        del peer["certificate_der"]
    elif mutation == "extra":
        peer["verified"] = True
    elif mutation == "certificate":
        peer["certificate_der"] = "not-der"
    elif mutation == "substitution":
        peer["certificate_der"] = records[0]["enrollment"]["certificate_der"]
    elif mutation == "signature":
        damaged = bytes.fromhex(peer["certificate_der"])
        damaged = damaged[:-1] + bytes([damaged[-1] ^ 1])
        peer["certificate_der"] = damaged.hex()
        peer["pin"] = hashlib.sha256(damaged).hexdigest()
    raw = "VERIFIED " + node._canonical_bytes(record).decode()
    if mutation == "duplicate":
        raw = raw.replace('"status":"PUBLIC_ENROLLMENT"', '"status":"PUBLIC_ENROLLMENT","status":"PUBLIC_ENROLLMENT"')
    elif mutation == "noncanonical":
        raw = "VERIFIED " + json.dumps(record, indent=2)
    elif mutation == "oversized":
        raw = "VERIFIED " + " " * (node.MAX_FRAME_BYTES + 1)
    elif mutation == "unverified":
        raw = node._canonical_bytes(record).decode()
    elif mutation == "pin_only":
        raw = "VERIFIED " + peer["pin"]
    with pytest.raises(node.PersistentNodeError):
        node._coordinator_prepared_peer(raw, identities[0], "initial", None)


@pytest.mark.parametrize("offset", [-31, 600, 601])
def test_prepared_record_rejects_not_yet_valid_or_expired_certificate(offset, prepared_records, monkeypatch):
    identities, records = prepared_records
    before = identities[1].certificate.not_valid_before_utc.timestamp()
    # The unchanged certificate spans creation-30 through creation+600.
    monkeypatch.setattr(node.time, "time", lambda: before + 30 + offset)
    with pytest.raises(node.PersistentNodeError, match="coordinator_peer_credentials_expired"):
        node._coordinator_prepared_peer("VERIFIED " + node._canonical_bytes(records[1]).decode(),
                                        identities[0], "initial", None)


@pytest.mark.parametrize("mutation", ["session", "started", "source_digest"])
def test_prepared_restart_record_requires_exact_retained_session(mutation, prepared_records):
    identities, _ = prepared_records
    context = node.lan_context("a" * 32, int(time.time()), "restart", node.lan_source_inventory()["source_digest"])
    record = node._coordinator_prepared_record(identities[1], "restart", context)
    raw = "VERIFIED " + node._canonical_bytes(record).decode()
    peer, _ = node._coordinator_prepared_peer(raw, identities[0], "restart", context)
    assert peer["context"] == context
    record["enrollment"]["context"] = dict(context)
    record["enrollment"]["context"][mutation] = "0" * 64 if mutation == "source_digest" else (True if mutation == "started" else "b" * 32)
    with pytest.raises(node.PersistentNodeError):
        node._coordinator_prepared_peer("VERIFIED " + node._canonical_bytes(record).decode(),
                                        identities[0], "restart", context)


def test_prepared_unverified_record_cannot_reach_listener(coordinator_clock, capsys):
    clock = coordinator_clock
    clock.attested = False
    assert _clock_coordinator("follower") == 1
    output = capsys.readouterr()
    assert output.err.strip() == "coordinator_physical_verification_required"
    assert "PREPARED_ENROLLED" not in output.out and not clock.sockets and not clock.tokens
    _assert_clock_cleanup(clock)


@pytest.mark.parametrize("delay", [0, 299, 450])
def test_prepared_follower_listens_after_one_verified_record_input(delay, coordinator_clock, capsys):
    clock = coordinator_clock
    clock.delay = delay
    assert _clock_coordinator("follower") == 0
    reports = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(clock.inputs) == 1 and "READY" not in clock.inputs[0]
    assert [r.get("status") for r in reports[:3]] == ["PUBLIC_ENROLLMENT", "PREPARED_ENROLLED", "FOLLOWER_LISTENING"]
    assert reports[-1]["result"] == "COORDINATOR_PHASE_PASS"
    assert clock.transitions[0][0] == delay and clock.transitions[0][1] - (1000 + delay) == 120
    assert 599 <= clock.timers[0].seconds <= 600 and clock.timers[1].seconds == 120 and not clock.tokens
    _assert_clock_cleanup(clock)


@pytest.mark.parametrize("raw,delay,error,exception,code", [
    ("VERIFIED {}", 0, None, None, "coordinator_prepared_record_invalid"),
    ("VERIFIED not-json", 0, None, None, "coordinator_prepared_record_invalid"),
    ("", 0, None, None, "coordinator_physical_verification_required"),
    (None, "expiry", None, None, "coordinator_preparation_expired"),
    (None, 0, "coordinator_deadline_expired", None, "coordinator_preparation_expired"),
    (None, 0, None, EOFError(), "coordinator_io_failure"),
    (None, 0, None, KeyboardInterrupt(), "coordinator_cancelled"),
])
def test_prepared_follower_rejects_record_expiry_and_interruption(raw, delay, error, exception, code, coordinator_clock, capsys):
    clock = coordinator_clock
    clock.raw_override, clock.delay = raw, delay
    clock.input_error, clock.input_exception = error, exception
    assert _clock_coordinator("follower") == 1
    output = capsys.readouterr()
    assert output.err.strip() == code and "FOLLOWER_LISTENING" not in output.out and "PASS" not in output.out
    assert len(clock.inputs) == 1 and not clock.sockets and not clock.tokens
    _assert_clock_cleanup(clock)


@pytest.mark.parametrize("role", ["writer", "follower"])
@pytest.mark.parametrize("delay", [0, 299, 450])
def test_prepared_slow_public_input_preserves_full_active_budget(role, delay, coordinator_clock, capsys):
    clock = coordinator_clock
    clock.delay = delay
    assert _clock_coordinator(role) == 0
    elapsed, deadline, context = clock.transitions[0]
    assert elapsed == delay and deadline - (1000 + elapsed) == 120
    assert 599 <= clock.timers[0].seconds <= 600 and clock.timers[1].seconds == 120
    if role == "writer":
        assert clock.tokens == [delay]
        assert context["started"] == int(clock.wall + delay)
    else:
        assert not clock.tokens and context is None
    _assert_clock_cleanup(clock)
    capsys.readouterr()


@pytest.mark.parametrize("role", ["writer", "follower"])
def test_prepared_expiry_rejects_without_socket_or_start(role, coordinator_clock, capsys):
    clock = coordinator_clock
    clock.delay = "expiry"
    assert _clock_coordinator(role) == 1
    output = capsys.readouterr()
    assert output.err.strip() == "coordinator_preparation_expired" and "PASS" not in output.out
    assert not clock.sockets and not clock.transitions and not clock.tokens
    _assert_clock_cleanup(clock)


@pytest.mark.parametrize("pin", ["0" * 64, "not-a-pin"])
def test_prepared_bad_pin_never_starts_runtime(pin, coordinator_clock, capsys):
    clock = coordinator_clock
    clock.record_mutation = lambda record: record["enrollment"].update(pin=pin)
    assert _clock_coordinator() == 1
    assert capsys.readouterr().err.strip() == "coordinator_prepared_record_invalid"
    assert not clock.sockets and not clock.tokens and len(clock.timers) == 1
    _assert_clock_cleanup(clock)


def test_prepared_public_input_timeout_has_phase_specific_failure(coordinator_clock, capsys):
    clock = coordinator_clock
    clock.input_error = "coordinator_deadline_expired"
    assert _clock_coordinator() == 1
    assert capsys.readouterr().err.strip() == "coordinator_preparation_expired"
    assert not clock.sockets and not clock.tokens
    _assert_clock_cleanup(clock)


@pytest.mark.parametrize("delay,value,code", [
    (450, "READY", None), (601, "READY", "coordinator_preparation_expired"),
    (0, "NOT_READY", "coordinator_readiness_not_confirmed")])
def test_prepared_writer_readiness_is_offline_and_bounded(delay, value, code, coordinator_clock, capsys):
    clock = coordinator_clock
    clock.ready_delay, clock.ready_value = delay, value
    assert _clock_coordinator() == (1 if code else 0)
    output = capsys.readouterr()
    if code:
        assert output.err.strip() == code and "PASS" not in output.out
        assert not clock.sockets and not clock.tokens
    else:
        assert clock.tokens == [450] and clock.transitions[0][1] - 1450 == 120
    _assert_clock_cleanup(clock)


def test_prepared_active_timeout_fails_closed_after_slow_enrollment(coordinator_clock, capsys):
    clock = coordinator_clock
    clock.delay, clock.active_delay = 450, 120
    assert _clock_coordinator() == 1
    output = capsys.readouterr()
    assert output.err.strip() == "coordinator_deadline_expired" and "PASS" not in output.out
    _assert_clock_cleanup(clock)


def test_prepared_watchdog_transition_does_not_extend_active_budget(coordinator_clock, capsys):
    clock = coordinator_clock
    clock.delay, clock.join_delay = 299, 0.5
    assert _clock_coordinator() == 0
    elapsed, deadline, _ = clock.transitions[0]
    assert elapsed == 299.5 and deadline == 1419
    assert clock.timers[-1].seconds == 119.5
    _assert_clock_cleanup(clock)
    capsys.readouterr()


@pytest.mark.parametrize("delay,expired", [(10, False), (101, True)])
def test_prepared_restart_never_resets_or_extends_session(delay, expired, coordinator_clock, monkeypatch, capsys):
    clock = coordinator_clock
    context = node.lan_context("c" * 32, int(clock.wall) - 500, "restart",
                               node.lan_source_inventory()["source_digest"])
    def load_context(*args):
        assert len(clock.timers) == 1 and clock.timers[0].ident is not None
        assert len(clock.identities) == 1 and not clock.sockets
        return context
    monkeypatch.setattr(node, "_coordinator_restart_context", load_context)
    clock.restart_context = context
    clock.delay = delay
    assert _clock_coordinator(phase="restart") == (1 if expired else 0)
    output = capsys.readouterr()
    assert not clock.tokens
    if expired:
        assert output.err.strip() == "lan_session_invalid_or_expired" and "PASS" not in output.out
        assert not clock.sockets and len(clock.timers) == 1
    else:
        elapsed, deadline, actual = clock.transitions[0]
        assert actual["started"] == context["started"]
        remaining = context["started"] + 600 - (clock.wall + elapsed)
        assert deadline - (1000 + elapsed) == pytest.approx(remaining)
        assert 0 < clock.timers[-1].seconds < 90.01
    _assert_clock_cleanup(clock)


def test_prepared_late_activation_is_capped_by_existing_certificate(coordinator_clock, capsys):
    clock = coordinator_clock
    clock.delay = 590
    assert _clock_coordinator() == 0
    elapsed, deadline, context = clock.transitions[0]
    assert elapsed == 590 and 0 < deadline - (1000 + elapsed) <= 10
    assert clock.tokens == [590] and context["started"] == int(clock.wall + 590)
    assert len(clock.identities) == 1
    _assert_clock_cleanup(clock)
    capsys.readouterr()


def test_auto_pair_fingerprint_is_full_role_ordered_and_binding_sensitive(prepared_records):
    _, records = prepared_records
    fingerprint = node._pair_fingerprint(*records)
    assert len(fingerprint) == 64 and node._lan_hex(fingerprint, 64)
    assert fingerprint == node._pair_fingerprint(*reversed(records))
    assert fingerprint == hashlib.sha256(node.PAIR_DOMAIN + node._canonical_bytes({
        "profile": node.PAIR_PROFILE, "writer": records[0], "follower": records[1]})).hexdigest()
    for key in ("pin", "source_digest", "writer", "follower", "port", "phase", "context", "certificate_der"):
        altered = deepcopy(records[1])
        altered["enrollment"][key] = "ALTERED"
        assert node._pair_fingerprint(records[0], altered) != fingerprint


@pytest.mark.parametrize("case", ["valid", "decline", "one-sided", "wrong-source", "wrong-role",
    "wrong-endpoint", "substituted", "mismatch", "expired", "interrupted"])
def test_auto_pair_public_transport_is_not_approval(case, prepared_records, monkeypatch):
    identities, _ = prepared_records
    pipes = [node._OfflinePipe("writer"), node._OfflinePipe("follower")]
    pipes[0].other, pipes[1].other = pipes[1], pipes[0]
    reports, decisions, results, errors = [], [], [], []
    original_send = node._pair_send
    def send(sock, value, deadline):
        value = deepcopy(value)
        if sock.role == "follower" and "enrollment" in value:
            if case == "wrong-source": value["enrollment"]["source_digest"] = "0" * 64
            if case == "wrong-role": value["enrollment"]["role"] = "writer"
            if case == "wrong-endpoint": value["enrollment"]["writer"] = "192.168.68.51"
            if case == "substituted": value["enrollment"]["certificate_der"] = "00"
        if case == "mismatch" and sock.role == "follower" and "fingerprint" in value:
            value["fingerprint"] = "0" * 64
        original_send(sock, value, deadline)
    def public_input(prompt, deadline):
        role = __import__('threading').current_thread().name
        decisions.append(role)
        if case == "expired": raise node.PersistentNodeError("coordinator_deadline_expired")
        if case == "interrupted": raise EOFError
        return "NO" if case == "decline" or (case == "one-sided" and role == "follower") else "PAIR"
    def forbidden(*args, **kwargs):
        raise AssertionError("untrusted pairing invoked secret or ledger API")
    monkeypatch.setattr(node, "_emit", reports.append)
    monkeypatch.setattr(node, "_pair_send", send)
    monkeypatch.setattr(node, "_coordinator_public_input", public_input)
    monkeypatch.setattr(node, "_lan_open_state", forbidden)
    monkeypatch.setattr(node.PinnedTLSHandoff, "__init__", forbidden)
    def run(index):
        try:
            results.append(node._pair_exchange(pipes[index], identities[index], "initial", None, time.monotonic() + 2))
        except (node.PersistentNodeError, EOFError) as exc:
            errors.append(getattr(exc, "code", "EOF"))
        finally:
            pipes[index].close()
    import threading
    workers = [threading.Thread(target=run, args=(i,), name=r, daemon=True) for i,r in enumerate(("writer", "follower"))]
    try:
        for worker in workers: worker.start()
        for worker in workers: worker.join(timeout=3)
        assert not any(w.is_alive() for w in workers)
        if case == "valid":
            assert not errors and len(results) == 2 and sorted(decisions) == ["follower", "writer"]
            assert results[0][2] == results[1][2]
        else:
            assert errors
            if case in ("decline", "one-sided"):
                assert "pairing_not_approved" in errors
            if case == "mismatch": assert "pairing_fingerprint_mismatch" in errors
        assert all(r["records"] == "UNTRUSTED" and not r["ledger_started"] for r in reports)
    finally:
        for pipe in pipes: pipe.close()
        for worker in workers: worker.join(timeout=2)


@pytest.mark.parametrize("raw,code", [(b"{", "coordinator_interrupted"),
    (b"{} ", "pair_frame_noncanonical"), (b"[]", "pair_frame_noncanonical")])
def test_auto_pair_frame_rejects_malformed_and_noncanonical(raw, code):
    pipe = node._OfflinePipe("writer")
    pipe.other = node._OfflinePipe("follower")
    pipe.other.other = pipe
    try:
        wire = struct.pack(">I", len(raw) + (1 if raw == b"{" else 0)) + raw
        pipe.queue.put(wire)
        pipe.queue.put(b"")
        with pytest.raises(node.PersistentNodeError, match=code):
            node._pair_receive(pipe, time.monotonic()+1)
        pipe.pending = b""
        while not pipe.queue.empty(): pipe.queue.get_nowait()
        pipe.queue.put(struct.pack(">I", node.MAX_FRAME_BYTES+1))
        with pytest.raises(node.PersistentNodeError, match="pair_frame_oversized"):
            node._pair_receive(pipe, time.monotonic()+1)
    finally:
        pipe.close(); pipe.other.close()


@pytest.mark.parametrize("platform,role", [("mac", "writer"), ("windows", "follower")])
def test_auto_pair_launcher_is_public_and_does_not_start_runtime(platform, role, monkeypatch, capsys):
    original_popen = subprocess.Popen
    def forbidden(*args, **kwargs):
        raise AssertionError("launcher generation started runtime or credentials")
    monkeypatch.setattr(node.MemoryTLSIdentity, "__init__", forbidden)
    monkeypatch.setattr(node.socket, "socket", forbidden)
    monkeypatch.setattr(node.subprocess, "Popen", forbidden)
    digest=node.lan_source_inventory()["source_digest"]
    assert node.main(["--print-launcher", "--launcher-platform", platform, "--role", role,
                      "--ack-private-lan", "--expected-source-digest", digest]) == 0
    script=capsys.readouterr().out
    assert script.count("--paired-coordinate") >= 2 and "--phase initial" in script and "--phase restart" in script
    assert "--report-dir" in script and "Read-Host" not in script and "read " not in script
    assert "--session-start" not in script and "--session-id" not in script
    assert digest in script and "private_bytes" not in script
    if platform == "mac":
        monkeypatch.setattr(node.subprocess, "Popen", original_popen)
        if Path("/bin/zsh").is_file():
            result=subprocess.run(["/bin/zsh", "-n"],input=script,text=True,capture_output=True)
            assert result.returncode == 0,result.stderr
        assert 'pgrep -P "$l28Parent"' in script and "MAC_CLEANUP_VERIFIED" in script
    else:
        assert "-Profile Private" in script and "-LocalAddress 192.168.68.54" in script
        assert "-RemoteAddress 192.168.68.50 -LocalPort 42828" in script
        assert "finally" in script and "Remove-NetFirewallRule" in script and "ParentProcessId -eq $PID" in script


@pytest.mark.parametrize("argv", [["--paired-coordinate", "--runtime-check"],
    ["--paired-coordinate", "--offline-pair-role"], ["--offline-fd", "1"],
    ["--print-launcher", "--role", "writer"], ["--paired-coordinate", "--role", "writer", "--phase", "initial"]])
def test_auto_pair_conflicting_or_unscoped_modes_fail_closed(argv, monkeypatch, capsys):
    def forbidden(*args, **kwargs): raise AssertionError("operation before valid mode")
    monkeypatch.setattr(node.MemoryTLSIdentity, "__init__", forbidden)
    monkeypatch.setattr(node.socket, "socket", forbidden)
    assert node.main(argv) == 1
    assert "PASS" not in capsys.readouterr().out


@pytest.mark.parametrize("approval", [False, True])
def test_auto_pair_peer_approval_wait_is_certificate_bounded_not_ten_seconds(approval, monkeypatch):
    class Transport:
        def __init__(self): self.raw, self.timeouts = bytearray(struct.pack(">I", 2) + b"{}"), []
        def settimeout(self, value): self.timeouts.append(value)
        def recv(self, size):
            elapsed[0] += 12
            result = bytes(self.raw[:size]); del self.raw[:size]
            return result
    elapsed = [0]
    monkeypatch.setattr(node.time, "monotonic", lambda: 1000 + elapsed[0])
    transport = Transport()
    assert node._pair_receive(transport, 1100, enrollment_wait=approval) == {}
    assert transport.timeouts == ([100, 88] if approval else [10, 10])
    with pytest.raises(node.PersistentNodeError, match="coordinator_deadline_expired"):
        node._pair_receive(transport, 1000, enrollment_wait=True)


@pytest.mark.parametrize("address,accept_error", [(node.LAN_WRITER_IP, False),
    ("192.168.68.51", False), (node.LAN_WRITER_IP, True)])
def test_auto_pair_listener_is_scoped_restartable_and_closed_on_failure(address, accept_error, monkeypatch):
    class Socket:
        def __init__(self): self.closed, self.options, self.bound = False, [], None
        def setsockopt(self, *args): self.options.append(args)
        def settimeout(self, value): assert 0 < value <= 600
        def bind(self, value): self.bound = value
        def listen(self, value): assert value == 1
        def accept(self):
            if accept_error: raise TimeoutError
            return connection, (address, 42829)
        def shutdown(self, value): pass
        def close(self): self.closed = True
    listener, connection = Socket(), Socket()
    monkeypatch.setattr(node.socket, "socket", lambda *args: listener)
    monkeypatch.setattr(node, "_emit", lambda value: None)
    if address == node.LAN_WRITER_IP and not accept_error:
        assert node._pair_open("follower", time.monotonic()+600) is connection
        assert not connection.closed
    else:
        with pytest.raises((node.PersistentNodeError, TimeoutError)):
            node._pair_open("follower", time.monotonic()+600)
        assert accept_error or connection.closed
    assert listener.closed and listener.bound == (node.LAN_FOLLOWER_IP, node.LAN_PORT)
    assert listener.options == [(node.socket.SOL_SOCKET, node.socket.SO_REUSEADDR, 1)]


@pytest.mark.parametrize("delay,stage", [(0, "valid"), (450, "valid"), (590, "valid"),
    (601, "valid"), (0, "decline"), (0, "auth"), (0, "active-timeout")])
def test_auto_pair_activation_deadlines_and_all_exit_cleanup(delay, stage, prepared_records, monkeypatch, capsys):
    import tempfile, shutil
    identities, records = prepared_records
    root = Path(tempfile.mkdtemp(prefix="l28-pair-launch-")).resolve()
    wall, elapsed, timers, created, activated = time.time(), [0], [], [], []
    monkeypatch.setattr(node.time, "time", lambda: wall + elapsed[0])
    monkeypatch.setattr(node.time, "monotonic", lambda: 1000 + elapsed[0])
    class Timer:
        def __init__(self, seconds, callback):
            self.seconds, self.ident, self.cancelled, self.joined = seconds, None, False, False
            timers.append(self)
        def start(self): self.ident = 1
        def cancel(self): self.cancelled = True
        def join(self, timeout=None): self.joined = True
    class Transport:
        closed = False
        def getsockname(self): return (node.LAN_WRITER_IP, 42829)
        def getpeername(self): return (node.LAN_FOLLOWER_IP, node.LAN_PORT)
        def shutdown(self, how): pass
        def close(self): self.closed = True
        def recv(self, size): raise AssertionError("expired runtime read")
    transport = Transport()
    original_init = node.MemoryTLSIdentity.__init__
    def identity(self, role):
        original_init(self, role); created.append(self)
    def exchange(sock, identity, phase, context, deadline):
        elapsed[0] += delay
        if stage == "decline": raise node.PersistentNodeError("pairing_not_approved")
        raw = node._canonical_bytes(records[1]).decode()
        peer, expiry = node._coordinator_record_peer(raw, identity, phase, context)
        return peer, expiry, "a" * 64, raw
    def connected(sock, identity, peer, context, data_dir, deadline, *, activation):
        if stage == "auth": raise node.PersistentNodeError("tls_peer_authentication_failed")
        assert not identity.closed and identity.certificate is not None
        active = activation(context)
        activated.append(active)
        if stage == "active-timeout":
            elapsed[0] += 120
            node._coordinator_read(sock, 1, active)
        return {"timing_fixture_only": True}
    monkeypatch.setattr(node.threading, "Timer", Timer)
    monkeypatch.setattr(node.MemoryTLSIdentity, "__init__", identity)
    monkeypatch.setattr(node, "_pair_open", lambda *args: transport)
    monkeypatch.setattr(node, "_pair_exchange", exchange)
    monkeypatch.setattr(node, "_coordinator_connected", connected)
    try:
        expected = stage == "valid" and delay < 600
        assert node.main(["--paired-coordinate", "--role", "writer", "--phase", "initial",
            "--report-dir", str(root), "--ack-private-lan", "--expected-source-digest",
            node.lan_source_inventory()["source_digest"]]) == (0 if expected else 1)
        output = capsys.readouterr()
        assert transport.closed and all(i.closed and i._key is None for i in created)
        assert timers and all(t.cancelled and t.joined for t in timers)
        if expected:
            assert 0 < activated[0] - (1000 + delay) <= min(120, 600 - delay)
            assert (root / "initial.json").is_file()
        else:
            assert "PASS" not in output.out and not list(root.iterdir())
            if stage == "decline": assert "pairing_not_approved" in output.err
            elif stage == "auth": assert "tls_peer_authentication_failed" in output.err
            elif stage == "active-timeout": assert "coordinator_deadline_expired" in output.err
            else: assert "coordinator_peer_credentials_expired" in output.err
    finally:
        shutil.rmtree(root)


@pytest.mark.skipif(sys.platform == "win32", reason="Explicit POSIX-only AF_UNIX/PTY offline CLI interface")
def test_auto_pair_real_process_restart_offline(tmp_path):
    """Two actual L28 processes at a time; PTY supplies PUBLIC test approvals only."""
    import os, pty, socket, tempfile, shutil
    reports_dirs=[Path(tempfile.mkdtemp(prefix="l28-pair-launch-")).resolve() for _ in range(2)]
    processes, masters, sockets, prior, evidence = [], [], [], None, []
    digest=node.lan_source_inventory()["source_digest"]
    try:
        for phase in ("initial", "restart"):
            sockets=list(socket.socketpair())
            processes=[]; masters=[]
            for i,role in enumerate(("writer", "follower")):
                master,slave=pty.openpty(); masters.append(master)
                argv=[sys.executable,"-B","-m","coin.persistent_disposable_testnet_node",
                    "--offline-pair-role","--role",role,"--phase",phase,"--offline-fd",str(sockets[i].fileno()),
                    "--report-dir",str(reports_dirs[i]),"--expected-source-digest",digest]
                if prior: argv += ["--data-dir",prior[i]["data_dir"]]
                processes.append(subprocess.Popen(argv,stdin=slave,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    text=True,pass_fds=(sockets[i].fileno(),)))
                os.close(slave)
            for sock in sockets: sock.close()
            def enrollment(process):
                while True:
                    line=process.stdout.readline()
                    if not line: raise AssertionError(process.stderr.read())
                    if line.startswith('{'):
                        value=json.loads(line)
                        if value.get("status")=="PAIRING_REQUIRED": return value
            pool = ThreadPoolExecutor(max_workers=2)
            try:
                futures=[pool.submit(enrollment,p) for p in processes]
                pair=[f.result(timeout=15) for f in futures]
                assert pair[0]["fingerprint"]==pair[1]["fingerprint"] and len(pair[0]["fingerprint"])==64
                for master in masters: os.write(master,b"PAIR\n")
                for p in processes:
                    out,err=p.communicate(timeout=15)
                    assert p.returncode==0,(out,err)
            finally:
                for p in processes:
                    if p.poll() is None: p.kill()
                pool.shutdown(wait=True)
            current=[json.loads((d/(phase+".json")).read_text()) for d in reports_dirs]
            assert current[0]["state"]==current[1]["state"]
            assert all(r["pid"]==p.pid and r["pinned_tls_handoff_verified"] and not r["physical_two_host_verified"] for r,p in zip(current,processes))
            assert all(r["transport"]=="OFFLINE_IPC" and r["physical_comparison"]=="offline_fixture" for r in current)
            if prior:
                assert all(r["previous_pid"]==before["pid"] and r["pid"]!=before["pid"]
                           and r["genuine_local_process_restart_verified"] and r["terminal_divergence_halt"]
                           and r["replay_rejected_without_mutation"] for r,before in zip(current,prior))
                assert all(r["state"]==before["state"] and r["session_start"]==before["session_start"] for r,before in zip(current,prior))
            prior=current; evidence.extend(current)
            for master in masters: os.close(master)
            masters=[]
        assert all(r["state"]["issued_supply"]==28 and sorted(r["state"]["balances"].values())==[0,28] for r in evidence)
    finally:
        for process in processes:
            if process.poll() is None: process.kill()
            process.wait(timeout=5)
        for master in masters: os.close(master)
        for sock in sockets: sock.close()
        if prior:
            for r in prior:
                root=Path(r["data_dir"])
                assert root.parent.resolve()==Path(tempfile.gettempdir()).resolve() and root.name.startswith("l28-disposable-lan-")
                if root.exists(): shutil.rmtree(root)
        for directory in reports_dirs: shutil.rmtree(directory)


class _MemoryWire:
    """Byte transport only: offline protocol tests never open LAN sockets."""
    def __init__(self):
        self.inbox = queue.Queue()
        self.pending = b""
        self.timeout = 2

    def settimeout(self, value):
        self.timeout = min(value, 2)

    def sendall(self, raw):
        self.other.inbox.put(raw)

    def recv(self, size):
        if not self.pending:
            self.pending = self.inbox.get(timeout=self.timeout)
        result, self.pending = self.pending[:size], self.pending[size:]
        return result


def _lan_pair(phase="initial"):
    first, second = _MemoryWire(), _MemoryWire()
    first.other, second.other = second, first
    context = node.lan_context("a" * 32, int(time.time()), phase, "b" * 64)
    # Public disposable fixture, never a runtime session secret.
    channels = [node.LanChannel(sock, b"public-offline-fixture".ljust(32, b"0"), context,
                                role, time.monotonic() + 10)
                for sock, role in ((first, "writer"), (second, "follower"))]
    return channels


def _parallel(first, second):
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(first), pool.submit(second)
        return a.result(timeout=5), b.result(timeout=5)


def test_lan_authenticated_sync_restart_replay_and_terminal_halt(tmp_path):
    roots = [tmp_path / "writer", tmp_path / "follower"]
    ledgers = [node._new_ledger(root / "ledger") for root in roots]
    asyncio.run(node._apply_events(ledgers[0], _events()))
    initial = None
    for phase in ("initial", "restart"):
        channels = _lan_pair(phase)
        _parallel(channels[0].authenticate, channels[1].authenticate)
        assert channels[0].key == channels[1].key
        if phase == "restart":
            ledgers = [asyncio.run(node._load_ledger(root / "ledger")) for root in roots]
        results = _parallel(lambda: node.lan_sync(channels[0], ledgers[0], roots[0]),
                            lambda: node.lan_sync(channels[1], ledgers[1], roots[1]))
        assert results[0] == results[1]
        assert results[0]["replay_rejected_without_mutation"]
        assert results[0]["terminal_divergence_halt"] == (phase == "restart")
        if initial is None:
            initial = results[0]["state"]
        assert results[0]["state"] == initial
        assert initial["issued_supply"] == 28
        assert sorted(initial["balances"].values()) == [0, 28]
    assert all((root / "halted.json").is_file() for root in roots)


def test_lan_partial_follower_recovers_only_validated_prefix(tmp_path):
    events = _events()
    roots = [tmp_path / "writer", tmp_path / "follower"]
    writer, follower = [node._new_ledger(root / "ledger") for root in roots]
    asyncio.run(node._apply_events(writer, events))
    asyncio.run(node._apply_events(follower, events[:1]))
    follower = asyncio.run(node._load_ledger(roots[1] / "ledger"))
    a, b = _lan_pair("restart")
    _parallel(a.authenticate, b.authenticate)
    left, right = _parallel(lambda: node.lan_sync(a, writer, roots[0]),
                            lambda: node.lan_sync(b, follower, roots[1]))
    assert left == right
    assert left["state"]["transaction_ids"] == [e["id"] for e in events]


@pytest.mark.parametrize("mutation", ["key", "role", "network", "session", "source", "phase",
                                      "type", "sequence", "boolean_sequence", "boolean_version", "payload"])
def test_lan_binding_tampering_rejects_without_advancing_sequence(mutation):
    a, b = _lan_pair()
    packet = json.loads(a.encode("event", {"example": 1})[4:])
    if mutation == "key":
        b.key = b"x" * 32
    elif mutation in ("network", "session", "source", "phase"):
        field = "source_digest" if mutation == "source" else mutation
        packet["body"]["context"][field] = "different"
    elif mutation == "boolean_version":
        packet["body"]["context"]["version"] = True
    elif mutation == "boolean_sequence":
        packet["body"]["sequence"] = True
    else:
        packet["body"][mutation] = "different"
    if mutation not in ("key", "payload"):
        # Correct MAC, wrong authenticated binding: reject independently of MAC failure.
        packet["mac"] = node._lan_mac(a.key, "frame", packet["body"])
    with pytest.raises(node.PersistentNodeError):
        b.decode(node._canonical_bytes(packet), "event")
    assert b.received == 0


def test_lan_sequence_replay_cross_handshake_and_bad_auth_rejected():
    a, b = _lan_pair()
    raw = a.encode("event", {})[4:]
    assert b.decode(raw, "event") == {}
    with pytest.raises(node.PersistentNodeError):
        b.decode(raw, "event")
    a, b = _lan_pair()
    captured = a.encode("event", {})[4:]
    a.sent = 0
    _parallel(a.authenticate, b.authenticate)
    with pytest.raises(node.PersistentNodeError):
        b.decode(captured, "event")
    a, b = _lan_pair()
    b.key = b"x" * 32
    a.send("hello", {"writer": "f" * 64})
    with pytest.raises(node.PersistentNodeError, match="auth_or_binding"):
        b.authenticate()


@pytest.mark.parametrize("raw", [b"", b"{}", b"{", b"\xff", b'{"body":{},"body":{}}',
                                  b"[" * 2000, b"x" * (node.MAX_FRAME_BYTES + 1)])
def test_lan_malformed_and_oversized_json(raw):
    _, b = _lan_pair()
    with pytest.raises(node.PersistentNodeError):
        b.decode(raw, "event")


def test_lan_length_noncanonical_and_interruption_checks():
    a, b = _lan_pair()
    packet = json.loads(a.encode("event", {})[4:])
    with pytest.raises(node.PersistentNodeError, match="noncanonical"):
        b.decode(json.dumps(packet).encode(), "event")
    a.sock.sendall(struct.pack(">I", node.MAX_FRAME_BYTES + 1))
    with pytest.raises(node.PersistentNodeError, match="size"):
        b.receive("event")
    a.sock.sendall(b"")
    with pytest.raises(node.PersistentNodeError, match="interrupted"):
        b.receive("event")


def test_lan_invalid_event_fails_before_persistence(tmp_path):
    events = _events()
    root = tmp_path / "follower"
    ledger = node._new_ledger(root / "ledger")
    asyncio.run(node._apply_events(ledger, events[:1]))
    before = node.ledger_state(ledger)
    files = {p.name: p.read_bytes() for p in (root / "ledger").iterdir()}
    invalid = deepcopy(events[1])
    invalid["signature"] = "00" * 64
    invalid["id"] = node.compute_tx_id(invalid)
    with pytest.raises(node.PersistentNodeError):
        asyncio.run(node._apply_events(ledger, [invalid]))
    assert node.ledger_state(ledger) == before
    assert files == {p.name: p.read_bytes() for p in (root / "ledger").iterdir()}


def test_lan_state_directory_restart_guards(tmp_path, monkeypatch):
    monkeypatch.setattr(node.tempfile, "gettempdir", lambda: str(tmp_path))
    context = _lan_pair()[0].context
    root = tmp_path / ("l28-disposable-lan-" + context["session"] + "-follower")
    ledger = node._lan_open_state(root, context, "follower")
    events = _events()
    asyncio.run(node._apply_events(ledger, events[:1]))
    context = {**context, "phase": "restart"}
    with pytest.raises(node.PersistentNodeError, match="locked_halted"):
        node._lan_open_state(root, context, "follower")
    (root / "running.lock").unlink()
    reopened = node._lan_open_state(root, context, "follower")
    assert node.ledger_state(reopened) == node.ledger_state(ledger)
    (root / "running.lock").unlink()
    shard = next((root / "ledger").iterdir())
    with shard.open("ab") as stream:
        stream.write(b"corrupt\n")
    with pytest.raises((node.PersistentNodeError, ValueError)):
        node._lan_open_state(root, context, "follower")
    assert (root / "running.lock").exists()  # Error is terminal, never auto-repair.


def test_lan_divergence_persists_halt_without_rewriting_ledger(tmp_path):
    ledger = node._new_ledger(tmp_path / "ledger")
    asyncio.run(node._apply_events(ledger, _events()))
    before = node.ledger_state(ledger)
    divergent = deepcopy(before)
    divergent["total_volume"] += 1
    divergent["state_commitment"] = node._state_commitment({
        k: v for k, v in divergent.items() if k != "state_commitment"})
    with pytest.raises(node.PersistentNodeError, match="divergence_halted"):
        node._lan_agree(tmp_path, before, divergent)
    assert node.ledger_state(ledger) == before
    assert (tmp_path / "halted.json").exists()


@pytest.mark.parametrize("started,now", [(0, 600), (100, 99), (True, 1)])
def test_lan_expiry_and_invalid_session(started, now):
    with pytest.raises(node.PersistentNodeError):
        node.lan_context("a" * 32, started, "initial", "b" * 64, now=now)


def test_lan_source_inventory_and_cli_fail_closed(capsys, monkeypatch):
    inventory = node.lan_source_inventory()
    assert inventory["files"]["coin/persistent_disposable_testnet_node.py"] == hashlib.sha256(IMPL_PATH.read_bytes()).hexdigest()
    assert node.main(["--source-inventory"]) == 0
    assert json.loads(capsys.readouterr().out) == inventory
    assert node.main(["--lan"]) == 1
    assert "prerequisites_missing" in capsys.readouterr().err
    assert node.main(["--session-id", "a" * 32]) == 1
    assert "explicit_lan_mode" in capsys.readouterr().err


def test_lan_actual_cli_inventory_and_noninteractive_guard(tmp_path):
    command = [sys.executable, "-B", "-m", "coin.persistent_disposable_testnet_node"]
    result = subprocess.run(command + ["--source-inventory"], cwd=ROOT,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert json.loads(result.stdout) == node.lan_source_inventory()
    result = subprocess.run(command + ["--lan", "--role", "writer", "--phase", "initial",
                            "--session-id", "a" * 32, "--session-start", str(int(time.time())),
                            "--data-dir", str(tmp_path / "must-not-exist"), "--ack-private-lan"],
                            cwd=ROOT, input="", capture_output=True, text=True, timeout=5)
    assert result.returncode == 1
    assert result.stderr.strip() == "lan_authentication_handoff_required"
    assert not (tmp_path / "must-not-exist").exists()


def test_lan_nonprefix_history_halts_before_applying_events(tmp_path):
    ledger = node._new_ledger(tmp_path / "ledger")
    asyncio.run(node._apply_events(ledger, _events()))
    before = node.ledger_state(ledger)
    class Peer:
        role = "writer"
        def send(self, *args):
            pass
        def receive(self, kind):
            assert kind == "prefix"
            return ["f" * 64]
    with pytest.raises(node.PersistentNodeError, match="divergence_halted"):
        node.lan_sync(Peer(), ledger, tmp_path)
    assert (tmp_path / "halted.json").exists()
    assert node.ledger_state(ledger) == before


def test_lan_state_path_and_halted_session_reject(tmp_path, monkeypatch):
    monkeypatch.setattr(node.tempfile, "gettempdir", lambda: str(tmp_path))
    context = _lan_pair()[0].context
    with pytest.raises(node.PersistentNodeError, match="directory_invalid"):
        node._lan_open_state(tmp_path / "arbitrary", context, "follower")
    root = tmp_path / ("l28-disposable-lan-" + context["session"] + "-follower")
    node._lan_open_state(root, context, "follower")
    (root / "running.lock").unlink()
    node._lan_halt(root, "test")
    with pytest.raises(node.PersistentNodeError, match="locked_halted"):
        node._lan_open_state(root, {**context, "phase": "restart"}, "follower")


def test_binding_is_disposable_and_all_production_authority_stays_false():
    binding = node.persistent_testnet_binding()
    assert binding["network_id"] == node.NETWORK_ID
    assert binding["data_dir_tag"] == node.DATA_DIR_TAG
    assert binding["network_scope"] == "DISPOSABLE_TEST_ONLY"
    for field in (
        "runtime_authorized",
        "network_authorized",
        "testnet_start_authorized",
        "signing_authorized",
        "mining_authorized",
        "broadcast_authorized",
        "settlement_authorized",
    ):
        assert binding[field] is False


def test_coinbase_and_transfer_use_existing_validator_and_ledger(tmp_path):
    ledger = node._new_ledger(tmp_path)
    events = _events()
    assert asyncio.run(node._apply_events(ledger, events)) == [
        event["id"] for event in events
    ]
    state = node.ledger_state(ledger)
    assert state["transaction_ids"] == [event["id"] for event in events]
    assert state["issued_supply"] == 28
    assert state["mint_height"] == 1
    assert state["total_transactions"] == 2
    assert sorted(state["balances"].values()) == [0, 28]
    replay_ok, replay_id, replay_reason = node.classify_event(ledger, events[-1])
    assert (replay_ok, replay_id, replay_reason) == (
        False,
        events[-1]["id"],
        "replay",
    )


def test_validated_durable_replay_reconstructs_exact_state(tmp_path):
    ledger = node._new_ledger(tmp_path)
    events = _events()
    asyncio.run(node._apply_events(ledger, events))
    before = node.ledger_state(ledger)
    reopened = asyncio.run(node._load_ledger(tmp_path))
    assert reopened.is_canonical_issuance_ready() is True
    assert node.ledger_state(reopened) == before
    assert asyncio.run(reopened.add_transaction(events[-1])) is False
    assert node.ledger_state(reopened) == before


def test_persistence_failure_does_not_expose_memory_ahead_of_disk(
    tmp_path, monkeypatch
):
    ledger = node._new_ledger(tmp_path)
    coinbase = _events()[0]

    async def fail_persist(_transaction, _shard_id):
        raise OSError("test-only persistence failure")

    monkeypatch.setattr(ledger, "_save_transaction", fail_persist)
    assert asyncio.run(ledger.add_transaction(coinbase)) is False
    assert ledger.transactions == {}
    assert ledger.total_transactions == 0
    assert ledger.issued_supply == 0
    assert ledger.mint_height == 0
    assert ledger.get_balance(coinbase["receiver"]) == 0


def test_malformed_cross_network_and_noncanonical_frames_fail_closed():
    binding = node.persistent_testnet_binding()
    encoded = node.encode_frame("initial_events", 1, {"events": []}, binding)
    length = int.from_bytes(encoded[:4], "big")
    body = encoded[4:]
    assert length == len(body)
    assert node.decode_frame(
        body,
        expected_sequence=1,
        expected_message_type="initial_events",
        binding=binding,
    )["network_id"] == node.NETWORK_ID

    parsed = json.loads(body)
    parsed["network_id"] = "L28-DISPOSABLE-WRONG001"
    with pytest.raises(node.PersistentNodeError, match="frame_network_invalid"):
        node.decode_frame(
            node._canonical_bytes(parsed),
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )
    with pytest.raises(node.PersistentNodeError, match="frame_malformed"):
        node.decode_frame(
            b"{",
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )
    with pytest.raises(node.PersistentNodeError, match="frame_noncanonical"):
        node.decode_frame(
            json.dumps(json.loads(body), indent=2).encode("utf-8"),
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )
    bool_version = json.loads(body)
    bool_version["version"] = True
    with pytest.raises(node.PersistentNodeError, match="frame_profile_invalid"):
        node.decode_frame(
            node._canonical_bytes(bool_version),
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )
    bool_sequence = json.loads(body)
    bool_sequence["sequence"] = True
    with pytest.raises(node.PersistentNodeError, match="frame_sequence_invalid"):
        node.decode_frame(
            node._canonical_bytes(bool_sequence),
            expected_sequence=1,
            expected_message_type="initial_events",
            binding=binding,
        )


def test_option_a_halts_divergence_without_rewriting_local_state(tmp_path):
    ledger = node._new_ledger(tmp_path)
    asyncio.run(node._apply_events(ledger, _events()))
    local = node.ledger_state(ledger)
    local_before = deepcopy(local)
    peer = deepcopy(local)
    first_address = sorted(peer["balances"])[0]
    peer["balances"][first_address] += 1
    material = {
        key: peer[key]
        for key in node.STATE_FIELDS
        if key != "state_commitment"
    }
    peer["state_commitment"] = node._state_commitment(material)
    result = node.assess_state_agreement(
        local, peer, node.persistent_testnet_binding()
    )
    assert result["equal"] is False
    assert result["conflict"] is True
    assert result["policy_status"] == "HALTED_CONFLICT"
    assert result["policy_code"] == "HALTED_BY_OPTION_A"
    assert result["canonical_state_changed"] is False
    assert result["ledger_mutated"] is False
    assert local == local_before == node.ledger_state(ledger)


def test_corrupt_and_cross_network_persisted_events_fail_validated_replay(
    tmp_path
):
    source = tmp_path / "source"
    ledger = node._new_ledger(source)
    asyncio.run(node._apply_events(ledger, _events()))
    shard = next(path for path in sorted(source.glob("shard_*.jsonl")) if path.stat().st_size)

    corrupt = tmp_path / "corrupt"
    corrupt.mkdir()
    for path in source.glob("shard_*.jsonl"):
        (corrupt / path.name).write_bytes(path.read_bytes())
    corrupt_shard = corrupt / shard.name
    corrupt_shard.write_bytes(corrupt_shard.read_bytes()[:-1])
    with pytest.raises(ValueError, match="validated_replay_truncated_record"):
        asyncio.run(node._load_ledger(corrupt))

    blank = tmp_path / "blank-record"
    blank.mkdir()
    for path in source.glob("shard_*.jsonl"):
        content = path.read_text(encoding="utf-8")
        if path.name == shard.name:
            content += "\n"
        (blank / path.name).write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="validated_replay_blank_record"):
        asyncio.run(node._load_ledger(blank))

    unexpected = tmp_path / "unexpected-shard"
    unexpected.mkdir()
    for path in source.glob("shard_*.jsonl"):
        (unexpected / path.name).write_bytes(path.read_bytes())
    (unexpected / "shard_99.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="validated_replay_unexpected_shard_file"):
        asyncio.run(node._load_ledger(unexpected))

    wrong = tmp_path / "wrong-network"
    wrong.mkdir()
    for path in source.glob("shard_*.jsonl"):
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            event["network"] = "L28-DISPOSABLE-WRONG001"
            event["id"] = node.compute_tx_id(event)
            records.append(node._canonical_bytes(event).decode("utf-8"))
        (wrong / path.name).write_text(
            "\n".join(records) + ("\n" if records else ""), encoding="utf-8"
        )
    with pytest.raises(ValueError, match="validated_replay_wrong_network"):
        asyncio.run(node._load_ledger(wrong))


def test_real_two_process_restart_workflow_and_no_private_material_persists(
    tmp_path
):
    result = node.execute_persistent_two_node_workflow(tmp_path)
    assert result["transport"] == "IPv4_LOOPBACK_ONLY"
    assert result["node_processes_per_phase"] == 2
    assert result["initial_processes_terminal"] is True
    assert result["restart_processes_terminal"] is True
    assert result["processes_restarted"] is True
    assert result["independent_validation"] is True
    assert len(result["validated_event_ids"]) == 2
    assert result["issued_supply"] == 28
    assert result["mint_height"] == 1
    assert result["total_transactions"] == 2
    assert sorted(result["balances"].values()) == [0, 28]
    assert result["durable_restart_agreement"] is True
    assert result["replay_rejected_after_restart"] is True
    assert result["corruption_rejected"] is True
    assert result["malformed_input_rejected"] is True
    assert result["cross_network_input_rejected"] is True
    assert result["divergence_halted_by_option_a"] is True
    assert result["canonical_history_touched"] is False
    assert result["historical_state_imported"] is False
    assert result["production_keys_used"] is False
    assert result["private_test_material_persisted"] is False
    assert result["mining_used"] is False
    assert result["public_network_used"] is False
    assert result["broadcast_used"] is False
    assert result["production_settlement"] is False
    persisted = "\n".join(
        path.read_text(encoding="utf-8", errors="strict")
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    for forbidden in (
        "private_key",
        "seed_phrase",
        "mnemonic",
        "xprv",
        "BEGIN PRIVATE",
    ):
        assert forbidden not in persisted


def test_source_has_no_private_serialization_public_bind_or_mining_call():
    source = IMPL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert "private_bytes" not in source
    assert "from_private_bytes" not in source
    assert "mine_block" not in calls
    assert "0.0.0.0" not in source
    assert "validate_transaction" in calls
    assert "add_transaction" in calls
    assert "assess_option_a" in calls


def test_protected_economics_and_history_constants_are_unchanged():
    assert L28_MAX_SUPPLY == 28_000_000
    assert L28_EMISSION_CEILING == 11_130_000
    assert L28_HISTORICAL_MINED == 2_824_584
    assert L28_HISTORICAL_LAST_ENTRY == 100_877
    assert L28_NEXT_HEIGHT_AFTER_CHECKPOINT == 100_878
