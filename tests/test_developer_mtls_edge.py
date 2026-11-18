import datetime
import hashlib
import json
import socket
import ssl
import subprocess
import sys
import time

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from coin import developer_mtls_edge as edge_module


@pytest.mark.parametrize("session", [3, 120])
def test_real_edge_and_stub(tmp_path, session):
    now = datetime.datetime.now(datetime.timezone.utc)

    def cert(name, issuer=None):
        key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        builder = (x509.CertificateBuilder().subject_name(subject)
                   .issuer_name(subject if issuer is None else issuer[1].subject)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - datetime.timedelta(minutes=1))
                   .not_valid_after(now + datetime.timedelta(minutes=5))
                   .add_extension(x509.BasicConstraints(ca=issuer is None, path_length=None), critical=True))
        if name == "edge":
            builder = builder.add_extension(x509.SubjectAlternativeName([
                x509.DNSName(edge_module.HOST)]), critical=False)
        certificate = builder.sign(key if issuer is None else issuer[0], hashes.SHA256())
        cert_path, key_path = tmp_path / (name + ".pem"), tmp_path / (name + ".key")
        cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        return key, certificate, cert_path, key_path

    ca = cert("ca")
    edge, client, wrong = [cert(name, ca) for name in ("edge", "client", "wrong")]
    approved = client[1].public_bytes(serialization.Encoding.DER)

    stub_code = """
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
class Stub(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith("/provider_hello"):
            time.sleep(0.5)
            return
        body = b'{ "signed": {"z":1,"a":2} }'
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print(self.path, flush=True)
with HTTPServer(("127.0.0.1", 0), Stub) as server:
    print(server.server_port, flush=True)
    server.serve_forever()
"""
    stub = subprocess.Popen([sys.executable, "-B", "-c", stub_code], stdout=subprocess.PIPE, text=True)
    proc = None
    start = time.monotonic()
    try:
        upstream = int(stub.stdout.readline())
        code = """
import ssl, sys
from coin import developer_mtls_edge as e
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.verify_mode = ssl.CERT_REQUIRED
ctx.load_cert_chain(sys.argv[1], sys.argv[2])
ctx.load_verify_locations(sys.argv[3])
e.serve(bind=e.LOOPBACK, port=0, source=e.LOOPBACK, hostname=e.HOST,
        context=ctx, fingerprint=sys.argv[4], upstream_port=int(sys.argv[5]),
        session_seconds=float(sys.argv[6]), request_seconds=0.25)
"""
        proc = subprocess.Popen([sys.executable, "-B", "-c", code, str(edge[2]), str(edge[3]),
            str(ca[2]), hashlib.sha256(approved).hexdigest(), str(upstream), str(session)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        port = json.loads(proc.stdout.readline())["port"]

        def request(identity=client, host=edge_module.HOST, method="GET", path=edge_module.DISCOVERY_PATH,
                    headers="", source=None):
            ctx = ssl.create_default_context(cafile=ca[2])
            if identity:
                ctx.load_cert_chain(identity[2], identity[3])
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1, source_address=source) as raw:
                    with ctx.wrap_socket(raw, server_hostname=host) as sock:
                        sock.sendall(f"{method} {path} HTTP/1.1\r\nHost: {host}:{port}\r\n{headers}\r\n".encode())
                        with sock.makefile("rb") as stream:
                            return stream.read()
            except OSError:
                return b""

        with socket.create_connection(("127.0.0.1", port), timeout=1) as slow:
            time.sleep(0.04)
            assert request() == b""
            assert slow.recv(1) == b""
        for identity, host in ((None, edge_module.HOST), (wrong, edge_module.HOST), (client, "wrong.invalid")):
            assert b"200 OK" not in request(identity, host)
        assert request(source=("127.0.0.2", 0)) == b""
        assert b"400 Bad Request" in request(method="POST")
        assert b"400 Bad Request" in request(path="/unapproved")
        assert b"400 Bad Request" in request(headers="Content-Length: 65537\r\n")
        ctx = ssl.create_default_context(cafile=ca[2])
        ctx.load_cert_chain(client[2], client[3])
        with socket.create_connection(("127.0.0.1", port), timeout=1) as raw:
            with ctx.wrap_socket(raw, server_hostname=edge_module.HOST) as slow_http:
                slow_http.sendall(b"GET ")
                assert slow_http.recv(1) == b""
        assert request(path=edge_module.HELLO_PATH) == b""
        time.sleep(0.3)
        for _ in range(3):
            assert request().endswith(b'{ "signed": {"z":1,"a":2} }')
        assert request() == b""
        out, err = proc.communicate(timeout=session)
        assert proc.returncode == 0 and not err, err
        assert json.loads(out) == {"edge_closed": True, "admitted": 12}
        assert time.monotonic() - start < session + (0.5 if session == 3 else 0)
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=2)
        stub.terminate()
        out, _ = stub.communicate(timeout=2)
    assert out.splitlines() == [edge_module.DISCOVERY_PATH] * 3
    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", upstream)) != 0


@pytest.mark.parametrize("flags,expected", [
    (["--physical"], ("100.66.229.15", 8443, "100.98.56.15", 28429)),
    (["--loopback-test", "--upstream-port", "18080"],
     ("127.0.0.1", 0, "127.0.0.1", 18080)),
    ([], None),
    (["--physical", "--loopback-test"], None),
    (["--physical", "--upstream-port", "18080"], None),
    (["--loopback-test"], None),
])
def test_edge_mode_selection(monkeypatch, flags, expected):
    from types import SimpleNamespace

    ctx = SimpleNamespace(load_cert_chain=lambda *_: None,
                          load_verify_locations=lambda **_: None)
    calls = []
    monkeypatch.setattr(edge_module.ssl, "SSLContext", lambda _: ctx)
    monkeypatch.setattr(edge_module, "serve", lambda **kwargs: calls.append(kwargs))
    argv = ["--server-cert", "fixture.pem", "--server-key", "fixture.key",
            "--client-ca", "ca.pem", "--client-sha256", "a" * 64, *flags]
    if expected is None:
        with pytest.raises(SystemExit) as error:
            edge_module.main(argv)
        assert error.value.code == 2
        assert not calls
    else:
        edge_module.main(argv)
        options, = calls
        assert tuple(options[k] for k in ("bind", "port", "source", "upstream_port")) == expected
        assert options["hostname"] == "pjay.tail8ba219.ts.net"
        assert options["fingerprint"] == "a" * 64
        assert options["context"].verify_mode == ssl.CERT_REQUIRED


def _post(body, extra=b"", length=None):
    target = edge_module.SESSION_PATH.encode()
    size = str(len(body)).encode() if length is None else length
    return (b"POST " + target + b" HTTP/1.1\r\nHost: edge:8443\r\nContent-Length: "
            + size + b"\r\n" + extra + b"\r\n" + body)


@pytest.mark.parametrize("extra,length", [
    (b"Content-Length: 1\r\n", None), (b"Transfer-Encoding: chunked\r\n", None),
    (b"", b"1, 1"), (b"", b"65537"), (b"", b"+1"), (b"", b"2"),
])
def test_purchase_framing_denied(extra, length):
    import io
    with pytest.raises(ValueError):
        edge_module._read_route(io.BytesIO(_post(b"x", extra, length)), "edge:8443", purchase=True)


def test_purchase_slot_consumed_before_failed_forward(monkeypatch):
    import io
    from contextlib import nullcontext
    from types import SimpleNamespace
    from coin import public_testnet_service_demo as demo

    slot = edge_module._PurchaseSlot()
    sent = []
    replies = []
    leaf = b"fixture certificate"
    fingerprint = hashlib.sha256(leaf).hexdigest()
    monkeypatch.setattr(edge_module, "_DeveloperSocketDeadline",
        lambda *_: SimpleNamespace(check=lambda: None, close=lambda: None))
    monkeypatch.setattr(edge_module, "_reply", lambda _, status, body=b"": replies.append((status, body)))

    def proxy(method, target, body, *_):
        sent.append((method, target, body))
        if len(sent) == 2:
            assert slot.sequence == 0
            raise TimeoutError("upstream outcome unknown")
        return b'{ "signed": {"z":1,"a":2} }'

    monkeypatch.setattr(edge_module, "_proxy", proxy)
    binding = demo.public_testnet_binding()
    quote = demo.frame_bytes("service_request", 2, {"z": 1, "a": 2}, binding)
    payment = demo.frame_bytes("payment_package", 4, {"z": 1, "a": 2}, binding)

    def handle(body, presented=leaf, gate=slot):
        client = SimpleNamespace(getpeercert=lambda **_: presented,
                                 makefile=lambda _: io.BytesIO(_post(body)))
        raw = io.BytesIO()
        raw.settimeout = lambda _: None
        ctx = SimpleNamespace(wrap_socket=lambda *_a, **_k: nullcontext(client))
        edge_module._handle(raw, ctx, fingerprint, "edge:8443", 28429,
                            time.monotonic()+10, gate)

    handle(quote, presented=b"wrong certificate")
    handle(quote, gate=None)
    assert not sent and slot.sequence == 2
    handle(quote)
    assert replies[-1] == ("200 OK", b'{ "signed": {"z":1,"a":2} }')
    handle(payment)
    handle(payment)
    assert [body for _, _, body in sent] == [quote, payment]
    assert replies[-1][0] == "400 Bad Request"


def test_purchase_expired_shared_attempt_rejected_before_socket(monkeypatch):
    monkeypatch.setattr(edge_module.socket, "socket", lambda *_: pytest.fail("socket opened"))
    with pytest.raises(ValueError, match="invalid_shared_attempt_start"):
        edge_module.serve(bind=edge_module.MAC, port=8443, source=edge_module.CLIENT,
            hostname=edge_module.HOST, context=None, fingerprint="a"*64, upstream_port=28429,
            purchase=True, attempt_start=time.monotonic()-106)


@pytest.mark.parametrize("overrides,extra,accepted", [
    ({}, [], True),
    ({"bind-ip": None}, [], False),
    ({"bind-ip": "0.0.0.0"}, [], False),
    ({"bind-ip": "0.1.2.3"}, [], False),
    ({"bind-ip": "::1"}, [], False),
    ({"bind-port": "28429"}, [], False),
    ({"bind-port": "65536"}, [], False),
    ({"source-ip": "224.0.0.1"}, [], False),
    ({"source-ip": "169.254.1.2"}, [], False),
    ({"source-ip": "127.0.0.0/8"}, [], False),
    ({"hostname": "test.example:8443"}, [], False),
    ({"hostname": "*.example"}, [], False),
    ({"hostname": "1.2.3.4"}, [], False),
    ({"attempt-start": None}, [], False),
    ({}, ["--upstream-port", "18100"], False),
    ({}, ["--physical"], False),
    ({}, ["--physical-single-purchase"], False),
    ({}, ["--loopback-test"], False),
])
def test_public_origin_mode_selection(monkeypatch, overrides, extra, accepted):
    from types import SimpleNamespace

    ctx = SimpleNamespace(load_cert_chain=lambda *_: None,
                          load_verify_locations=lambda **_: None)
    calls = []
    monkeypatch.setattr(edge_module.ssl, "SSLContext", lambda _: ctx)
    monkeypatch.setattr(edge_module, "serve", lambda **kwargs: calls.append(kwargs))
    config = {"bind-ip": "127.0.0.1", "bind-port": "18443",
              "source-ip": "127.0.0.2", "hostname": "test.example",
              "attempt-start": "123.5"}
    config.update(overrides)
    argv = ["--public-origin-single-purchase", "--server-cert", "fixture.pem",
            "--server-key", "fixture.key", "--client-ca", "ca.pem",
            "--client-sha256", "b" * 64]
    for key, value in config.items():
        if value is not None:
            argv.extend([f"--{key}", value])
    if not accepted:
        with pytest.raises(SystemExit) as error:
            edge_module.main(argv + extra)
        assert error.value.code == 2
        assert not calls
        return
    edge_module.main(argv)
    assert calls == [{
        "bind": "127.0.0.1", "port": 18443, "source": "127.0.0.2",
        "hostname": "test.example", "context": ctx, "fingerprint": "b" * 64,
        "upstream_port": 28429, "purchase": True, "attempt_start": 123.5,
        "report_peer": True,
    }]
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_legacy_mode_rejects_public_origin_options(monkeypatch):
    monkeypatch.setattr(edge_module, "serve", lambda **_: pytest.fail("listener started"))
    with pytest.raises(SystemExit) as error:
        edge_module.main(["--physical", "--source-ip", "127.0.0.1",
                          "--server-cert", "fixture.pem", "--server-key", "fixture.key",
                          "--client-ca", "ca.pem", "--client-sha256", "a" * 64])
    assert error.value.code == 2


def test_beta_rate_and_session_admission_budget():
    clients = {"a": ("192.0.2.1", "payer-a"), "b": ("192.0.2.2", "payer-b")}
    beta = edge_module._BetaSessions(clients, "unused")
    now = time.monotonic()
    assert not beta.admit_connection("192.0.2.3", now)
    for _ in range(4):
        assert beta.admit_connection("192.0.2.1", now)
    assert not beta.admit_connection("192.0.2.1", now)
    beta.owner, beta.cutoff, beta.admitted = "a", now + 105, 11
    assert beta.admit_connection("192.0.2.2", now)
    assert beta.admitted == 11
    assert beta.admit_connection("192.0.2.1", now + 5)
    assert not beta.admit_connection("192.0.2.1", now + 10)
    assert beta.admit_connection("192.0.2.1", now + 105)
    assert beta.owner is None


def test_beta_cross_peer_and_uncertain_payment(monkeypatch):
    import io
    from contextlib import nullcontext
    from types import SimpleNamespace
    from coin import public_testnet_service_demo as demo

    class Guard:
        def __init__(self, _sock, deadline):
            self.deadline = deadline

        def check(self):
            pass

        def close(self):
            pass

    a, b, wrong = b"enrolled-a", b"enrolled-b", b"not enrolled"
    first, second = [hashlib.sha256(leaf).hexdigest() for leaf in (a, b)]
    clients = {first: ("192.0.2.1", "payer-a"), second: ("192.0.2.2", "payer-b")}
    beta = edge_module._BetaSessions(clients, "fixture-origin")
    forwarded, replies = [], []

    def proxy(method, target, body, _port, _deadline, *, origin_headers):
        forwarded.append((method, target, body, origin_headers))
        if len(forwarded) == 3:
            assert beta.payment_pending
            raise TimeoutError("unknown")
        return 200, b'{"result":{"z":1,"a":2}}'

    monkeypatch.setattr(edge_module, "_DeveloperSocketDeadline", Guard)
    monkeypatch.setattr(edge_module, "_proxy", proxy)
    monkeypatch.setattr(edge_module, "_reply", lambda _, status, body=b"": replies.append((status, body)))

    def handle(leaf, source, wire):
        tls = SimpleNamespace(getpeercert=lambda **_: leaf, makefile=lambda _: io.BytesIO(wire))
        raw = io.BytesIO()
        raw.settimeout = lambda _: None
        ctx = SimpleNamespace(wrap_socket=lambda *_a, **_k: nullcontext(tls))
        edge_module._handle(raw, ctx, None, "edge:8443", 28429, time.monotonic() + 10,
                            report_source=source, beta=beta)

    hello = (f"GET {demo.HELLO_PATH} HTTP/1.1\r\nHost: edge:8443\r\n"
             "X-L28-Origin-Token: should-not-forward\r\n\r\n").encode()
    handle(wrong, "192.0.2.1", hello)
    handle(a, "192.0.2.2", hello)
    assert not forwarded
    handle(a, "192.0.2.1", hello)
    handle(b, "192.0.2.2", hello)
    assert replies[-1][0] == "400 Bad Request"
    assert forwarded[0][3][demo.BETA_ORIGIN_TOKEN] == "fixture-origin"
    binding = demo.public_testnet_binding()
    quote = demo.frame_bytes("service_request", 2, {"sample": 1}, binding)
    payment = demo.frame_bytes("payment_package", 4, {"sample": 2}, binding)
    handle(b, "192.0.2.2", _post(quote))
    handle(a, "192.0.2.1", _post(quote))
    assert replies[-1] == ("200 OK", b'{"result":{"z":1,"a":2}}')
    handle(a, "192.0.2.1", _post(payment))
    assert beta.uncertain and [item[2] for item in forwarded[1:]] == [quote, payment]
