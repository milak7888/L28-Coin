"""One bounded mTLS window. Never starts or restarts an upstream."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import http.client
import ipaddress
import json
import math
import re
import secrets
import socket
import ssl
import threading
import time

from pathlib import Path

from coin.public_testnet_service_demo import (
    BETA_ORIGIN_TOKEN, BETA_PAYER, BETA_SESSION, _beta_clean_run, _beta_stop_signal,
    load_beta_config, read_beta_credential,
    DISCOVERY_PATH, HELLO_PATH, SESSION_PATH, PublicTestnetError,
    _DeveloperSocketDeadline, parse_frame, public_testnet_binding,
)

MAC = "100.66.229.15"
CLIENT = "100.98.56.15"
HOST = "pjay.tail8ba219.ts.net"
LOOPBACK = "127.0.0.1"
MAX_BODY = 65536
MAX_HEADERS = 8192
MAX_REQUESTS = 12
REQUEST_SECONDS = 10
SESSION_SECONDS = 120
CLEANUP_SECONDS = 5


def _read_route(stream, authority, *, purchase=False):
    line = stream.readline(MAX_HEADERS + 1)
    if len(line) > MAX_HEADERS or not line.endswith(b"\r\n"):
        raise ValueError("request_line")
    method, target, version = line[:-2].decode("ascii").split(" ")
    allowed = (method == "GET" and target in (DISCOVERY_PATH, HELLO_PATH)
               or purchase and (method, target) == ("POST", SESSION_PATH))
    if not allowed or version != "HTTP/1.1":
        raise ValueError("route")
    size = len(line)
    headers = {}
    while True:
        line = stream.readline(MAX_HEADERS + 1)
        size += len(line)
        if size > MAX_HEADERS or not line.endswith(b"\r\n"):
            raise ValueError("headers")
        if line == b"\r\n":
            break
        name, value = line[:-2].decode("ascii").split(":", 1)
        name = name.lower()
        if not re.fullmatch(r"[a-z0-9-]+", name) or name in headers:
            raise ValueError("header_name")
        headers[name] = value.strip()
    if headers.get("host") != authority or "transfer-encoding" in headers:
        raise ValueError("authority_or_framing")
    length = headers.get("content-length")
    if method == "GET":
        if length not in (None, "0"):
            raise ValueError("get_body")
        return method, target, b""
    if length is None or not re.fullmatch(r"[1-9][0-9]{0,4}", length) or int(length) > MAX_BODY:
        raise ValueError("post_body_length")
    body = stream.read(int(length))
    if len(body) != int(length):
        raise ValueError("truncated_body")
    return method, target, body


class _PurchaseSlot:
    """The edge gates forwarding; the provider validates signatures and settles."""

    def __init__(self):
        self.sequence = 2

    def admit(self, body):
        if self.sequence == 0:
            raise ValueError("payment_slot_consumed")
        parse_frame(body, expected_sequence=self.sequence, binding=public_testnet_binding())
        # Reserve before any upstream I/O. Failure cannot reopen the slot.
        self.sequence = 4 if self.sequence == 2 else 0


def _reply(client, status, body=b""):
    header = (f"HTTP/1.1 {status}\r\nContent-Length: {len(body)}\r\n"
              "Content-Type: application/json\r\nConnection: close\r\n\r\n")
    client.sendall(header.encode("ascii") + body)


def _proxy(method, target, body, upstream_port, deadline, *, origin_headers=None):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as upstream:
        guard = _DeveloperSocketDeadline(upstream, deadline)
        try:
            guard.check()
            upstream.settimeout(max(0.001, deadline - time.monotonic()))
            upstream.connect((LOOPBACK, upstream_port))
            guard.check()
            headers = f"{method} {target} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n"
            if origin_headers is not None:
                headers += "".join(f"{name}: {value}\r\n" for name, value in origin_headers.items())
            if method == "POST":
                headers += f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n"
            upstream.sendall((headers + "\r\n").encode("ascii") + body)
            with http.client.HTTPResponse(upstream) as reply:
                reply.begin()
                if reply.status != 200 and (origin_headers is None or reply.status != 400):
                    raise ValueError("upstream_status")
                length = reply.length
                if origin_headers is not None and (reply.chunked or length is None or length > MAX_BODY):
                    raise ValueError("upstream_framing")
                body = reply.read(MAX_BODY + 1)
                if origin_headers is not None and len(body) != length:
                    raise ValueError("upstream_truncated")
                status = reply.status
            guard.check()
            if len(body) > MAX_BODY:
                raise ValueError("upstream_body")
            return body if origin_headers is None else (status, body)
        finally:
            guard.close()


class _BetaSessions:
    def __init__(self, clients, origin_token):
        self.clients = clients
        self.origin_token = origin_token
        self.buckets = {source: (4.0, time.monotonic()) for source, _ in clients.values()}
        self.uncertain = False
        self.payment_pending = False
        self._clear()

    def _clear(self):
        self.owner = self.token = self.slot = None
        self.admitted = 0
        self.cutoff = 0.0

    def admit_connection(self, source, now):
        if self.owner is not None and now >= self.cutoff:
            self._clear()
        if source not in self.buckets:
            return False
        tokens, last = self.buckets[source]
        tokens = min(4.0, tokens + (now - last) / 5)
        if tokens < 1:
            return False
        self.buckets[source] = (tokens - 1, now)
        if self.owner is not None and source == self.clients[self.owner][0]:
            if self.admitted >= MAX_REQUESTS:
                return False
            self.admitted += 1
        return True

    def forward(self, client, fingerprint, method, target, payload, upstream_port, guard):
        headers = {BETA_ORIGIN_TOKEN: self.origin_token}
        payment = False
        if target != DISCOVERY_PATH:
            if target == HELLO_PATH:
                if self.owner is not None:
                    raise ValueError("beta_session_busy")
                self.owner, self.token = fingerprint, secrets.token_hex(32)
                self.slot = _PurchaseSlot()
                self.admitted = 1
                self.cutoff = time.monotonic() + 105
            elif self.owner != fingerprint or time.monotonic() >= self.cutoff:
                raise ValueError("beta_session_rejected")
            else:
                self.slot.admit(payload)
                payment = self.slot.sequence == 0
            headers.update({BETA_PAYER: self.clients[fingerprint][1], BETA_SESSION: self.token})
        guard.check()
        deadline = guard.deadline if target == DISCOVERY_PATH else min(guard.deadline, self.cutoff)
        # Remain held until the complete upstream response is forwarded.
        self.payment_pending = payment
        status, body = _proxy(method, target, payload, upstream_port, deadline, origin_headers=headers)
        guard.check()
        if payment and status != 200 and body != b'{"error":"replay","ok":false}':
            return
        _reply(client, "200 OK" if status == 200 else "400 Bad Request", body)
        guard.check()
        if payment or (status == 400 and fingerprint == self.owner):
            self._clear()
        self.payment_pending = False


def _handle(raw, context, fingerprint, authority, upstream_port, deadline, slot=None,
            *, report_source=None, beta=None):
    with raw:
        guard = _DeveloperSocketDeadline(raw, deadline)
        try:
            guard.check()
            raw.settimeout(max(0.001, deadline - time.monotonic()))
            with context.wrap_socket(raw, server_side=True) as client:
                guard.check()
                actual = hashlib.sha256(client.getpeercert(binary_form=True)).hexdigest()
                if beta is None:
                    if not hmac.compare_digest(actual, fingerprint):
                        return
                elif actual not in beta.clients or beta.clients[actual][0] != report_source:
                    return
                if report_source is not None and beta is None:
                    print(json.dumps({"authenticated_source": report_source,
                                      "client_leaf_sha256": actual}), flush=True)
                with client.makefile("rb") as stream:
                    try:
                        method, target, payload = _read_route(stream, authority, purchase=slot is not None or beta is not None)
                        guard.check()
                        if method == "POST" and beta is None:
                            slot.admit(payload)
                    except (ValueError, PublicTestnetError, RecursionError):
                        _reply(client, "400 Bad Request")
                        return
                guard.check()
                if beta is not None:
                    try:
                        beta.forward(client, actual, method, target, payload, upstream_port, guard)
                    except (ValueError, PublicTestnetError, RecursionError):
                        if not beta.payment_pending:
                            _reply(client, "400 Bad Request")
                    finally:
                        if beta.payment_pending:
                            beta.uncertain = True
                    return
                body = _proxy(method, target, payload, upstream_port, deadline)
                guard.check()
                _reply(client, "200 OK", body)
        except (OSError, ValueError, PublicTestnetError, http.client.HTTPException):
            return
        finally:
            guard.close()


def serve(*, bind, port, source, hostname, context, fingerprint, upstream_port,
          session_seconds=SESSION_SECONDS, request_seconds=REQUEST_SECONDS,
          purchase=False, attempt_start=None, report_peer=False, beta=None, stop=None):
    slot = _PurchaseSlot() if purchase else None
    if purchase:
        if attempt_start is None or not math.isfinite(attempt_start) or not 0 <= time.monotonic()-attempt_start < 105:
            raise ValueError("invalid_shared_attempt_start")
        cutoff = attempt_start + 115
        stop_ingress = attempt_start + 105
    else:
        cutoff = time.monotonic() + session_seconds
        stop_ingress = cutoff - min(CLEANUP_SECONDS, session_seconds / 4)
    worker = None
    admitted = 0

    def sni(_sock, name, _context):
        if name != hostname:
            return ssl.ALERT_DESCRIPTION_UNRECOGNIZED_NAME
        return None

    context.set_servername_callback(sni)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            if beta is not None:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((bind, port))
            listener.listen(8)
            actual_port = listener.getsockname()[1]
            authority = hostname if actual_port == 443 else f"{hostname}:{actual_port}"
            print(json.dumps({"edge_ready": True, "port": actual_port}), flush=True)
            while (time.monotonic() < stop_ingress if beta is None else
                   not stop.is_set() and not beta.uncertain):
                listener.settimeout(min(0.05, max(0.001, stop_ingress - time.monotonic())))
                try:
                    raw, address = listener.accept()
                except socket.timeout:
                    continue
                now = time.monotonic()
                if worker is not None and worker.is_alive():
                    raw.close()
                    continue
                if beta is None:
                    allowed = address[0] == source and admitted < MAX_REQUESTS and now < stop_ingress
                else:
                    allowed = not stop.is_set() and not beta.uncertain and beta.admit_connection(address[0], now)
                if not allowed:
                    raw.close()
                    continue
                admitted += 1
                deadline = min(stop_ingress, now + request_seconds) if beta is None else now + request_seconds
                if beta is not None and beta.owner is not None:
                    deadline = min(deadline, beta.cutoff)
                worker = threading.Thread(target=_handle, args=(
                    raw, context, fingerprint, authority, upstream_port, deadline, slot),
                    kwargs={"report_source": address[0] if report_peer or beta is not None else None,
                            "beta": beta})
                worker.start()
    finally:
        if worker is not None:
            worker.join(max(0, cutoff - time.monotonic()) if beta is None else request_seconds + CLEANUP_SECONDS)
            if worker.is_alive():
                raise RuntimeError("edge_cleanup_deadline")
    if beta is not None and beta.uncertain:
        raise RuntimeError("beta_payment_outcome_uncertain")
    print(json.dumps({"edge_closed": True, "admitted": admitted}), flush=True)


def _unicast_ipv4(value):
    address = ipaddress.IPv4Address(value)
    if (address.is_unspecified or address.is_multicast or address.is_reserved
            or address.is_link_local or address in ipaddress.IPv4Network("0.0.0.0/8")):
        raise ValueError("expected an exact unicast IPv4 address")
    return str(address)


def _dns_hostname(value):
    label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    if (len(value) > 253 or not re.fullmatch(rf"{label}(?:\.{label})+", value)
            or not re.search(r"[a-z]", value.rsplit(".", 1)[-1])):
        raise ValueError("expected a lowercase DNS hostname")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("server-cert", "server-key", "client-ca"):
        parser.add_argument("--" + option, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--loopback-test", action="store_true")
    modes.add_argument("--public-beta", action="store_true")
    modes.add_argument("--beta-loopback-test", action="store_true")
    parser.add_argument("--client-sha256")
    parser.add_argument("--beta-config", type=Path)
    parser.add_argument("--beta-origin-token", type=Path)
    parser.add_argument("--beta-run-marker", type=Path)
    modes.add_argument("--physical", action="store_true")
    modes.add_argument("--physical-single-purchase", action="store_true")
    modes.add_argument("--public-origin-single-purchase", action="store_true")
    parser.add_argument("--bind-ip")
    parser.add_argument("--bind-port", type=int)
    parser.add_argument("--source-ip")
    parser.add_argument("--hostname")
    parser.add_argument("--attempt-start", type=float)
    parser.add_argument("--upstream-port", type=int)
    args = parser.parse_args(argv)
    beta_mode = args.public_beta or args.beta_loopback_test
    beta_options = (args.beta_config, args.beta_origin_token, args.beta_run_marker)
    if beta_mode and (not all(beta_options) or args.client_sha256 is not None):
        parser.error("beta mode requires config, origin credential and run marker")
    if not beta_mode and (any(beta_options) or not re.fullmatch(r"[a-f0-9]{64}", args.client_sha256 or "")):
        parser.error("invalid client fingerprint")
    purchase = args.physical_single_purchase or args.public_origin_single_purchase
    if (args.attempt_start is not None) != purchase:
        parser.error("--attempt-start is required exactly in single-purchase modes")
    origin = (args.bind_ip, args.bind_port, args.source_ip, args.hostname)
    hostname = HOST
    if beta_mode:
        if args.source_ip is not None:
            parser.error("beta source addresses come from the enrollment")
        try:
            _, clients, _ = load_beta_config(args.beta_config)
            origin_token = read_beta_credential(args.beta_origin_token).hex()
            if args.beta_loopback_test:
                if any(value is not None for value in origin) or not 1 <= (args.upstream_port or 0) <= 65535:
                    raise ValueError("beta loopback mode requires only an upstream port")
                if any(source != LOOPBACK for source, _ in clients.values()):
                    raise ValueError("beta loopback enrollment requires loopback sources")
                bind, port, hostname, upstream_port = LOOPBACK, 0, "localhost", args.upstream_port
            else:
                if (args.bind_ip is None or args.bind_port != 8443 or args.hostname is None
                        or args.upstream_port is not None):
                    raise ValueError("public beta requires explicit bind IPv4, TCP 8443 and hostname")
                bind, port, hostname, upstream_port = _unicast_ipv4(args.bind_ip), 8443, _dns_hostname(args.hostname), 28429
                if not ipaddress.IPv4Address(bind).is_global or any(
                        not ipaddress.IPv4Address(source).is_global for source, _ in clients.values()):
                    raise ValueError("public beta requires global IPv4 bind and sources")
        except (OSError, ValueError, PublicTestnetError) as exc:
            parser.error(f"invalid beta configuration ({type(exc).__name__})")
        source = None
    elif args.public_origin_single_purchase:
        if any(value is None for value in origin) or args.upstream_port is not None:
            parser.error("public-origin mode requires --bind-ip, --bind-port, --source-ip and --hostname; "
                         "upstream is fixed at 127.0.0.1:28429")
        if not 1 <= args.bind_port <= 65535 or args.bind_port == 28429:
            parser.error("invalid public-origin edge port")
        try:
            bind = _unicast_ipv4(args.bind_ip)
            source = _unicast_ipv4(args.source_ip)
            hostname = _dns_hostname(args.hostname)
        except ValueError as exc:
            parser.error(str(exc))
        port, upstream_port = args.bind_port, 28429
    elif any(value is not None for value in origin):
        parser.error("endpoint options require --public-origin-single-purchase")
    elif args.physical or args.physical_single_purchase:
        if args.upstream_port is not None:
            parser.error("physical mode uses fixed upstream port 28429")
        bind, port, source, upstream_port = MAC, 8443, CLIENT, 28429
    else:
        if args.upstream_port is None or not 1 <= args.upstream_port <= 65535:
            parser.error("loopback mode requires a valid upstream port")
        bind, port, source, upstream_port = LOOPBACK, 0, LOOPBACK, args.upstream_port
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(args.server_cert, args.server_key)
    ctx.load_verify_locations(cafile=args.client_ca)
    if beta_mode:
        with _beta_stop_signal() as stop, _beta_clean_run(args.beta_run_marker):
            serve(bind=bind, port=port, source=None, hostname=hostname, context=ctx,
                  fingerprint=None, upstream_port=upstream_port,
                  beta=_BetaSessions(clients, origin_token), stop=stop)
        return
    serve(bind=bind, port=port, source=source, hostname=hostname, context=ctx,
          fingerprint=args.client_sha256, upstream_port=upstream_port,
          purchase=purchase, attempt_start=args.attempt_start,
          report_peer=args.public_origin_single_purchase)


if __name__ == "__main__":
    main()
