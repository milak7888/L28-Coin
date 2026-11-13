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
import socket
import ssl
import threading
import time

from coin.public_testnet_service_demo import (
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


def _proxy(method, target, body, upstream_port, deadline):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as upstream:
        guard = _DeveloperSocketDeadline(upstream, deadline)
        try:
            guard.check()
            upstream.settimeout(max(0.001, deadline - time.monotonic()))
            upstream.connect((LOOPBACK, upstream_port))
            guard.check()
            headers = f"{method} {target} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n"
            if method == "POST":
                headers += f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n"
            upstream.sendall((headers + "\r\n").encode("ascii") + body)
            with http.client.HTTPResponse(upstream) as reply:
                reply.begin()
                if reply.status != 200:
                    raise ValueError("upstream_status")
                body = reply.read(MAX_BODY + 1)
            guard.check()
            if len(body) > MAX_BODY:
                raise ValueError("upstream_body")
            return body
        finally:
            guard.close()


def _handle(raw, context, fingerprint, authority, upstream_port, deadline, slot=None,
            *, report_source=None):
    with raw:
        guard = _DeveloperSocketDeadline(raw, deadline)
        try:
            guard.check()
            raw.settimeout(max(0.001, deadline - time.monotonic()))
            with context.wrap_socket(raw, server_side=True) as client:
                guard.check()
                actual = hashlib.sha256(client.getpeercert(binary_form=True)).hexdigest()
                if not hmac.compare_digest(actual, fingerprint):
                    return
                if report_source is not None:
                    print(json.dumps({"authenticated_source": report_source,
                                      "client_leaf_sha256": actual}), flush=True)
                with client.makefile("rb") as stream:
                    try:
                        method, target, payload = _read_route(stream, authority, purchase=slot is not None)
                        guard.check()
                        if method == "POST":
                            slot.admit(payload)
                    except (ValueError, PublicTestnetError, RecursionError):
                        _reply(client, "400 Bad Request")
                        return
                guard.check()
                body = _proxy(method, target, payload, upstream_port, deadline)
                guard.check()
                _reply(client, "200 OK", body)
        except (OSError, ValueError, PublicTestnetError, http.client.HTTPException):
            return
        finally:
            guard.close()


def serve(*, bind, port, source, hostname, context, fingerprint, upstream_port,
          session_seconds=SESSION_SECONDS, request_seconds=REQUEST_SECONDS,
          purchase=False, attempt_start=None, report_peer=False):
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
            listener.bind((bind, port))
            listener.listen(8)
            actual_port = listener.getsockname()[1]
            authority = hostname if actual_port == 443 else f"{hostname}:{actual_port}"
            print(json.dumps({"edge_ready": True, "port": actual_port}), flush=True)
            while time.monotonic() < stop_ingress:
                listener.settimeout(min(0.05, max(0.001, stop_ingress - time.monotonic())))
                try:
                    raw, address = listener.accept()
                except socket.timeout:
                    continue
                if (address[0] != source or admitted >= MAX_REQUESTS
                        or (worker is not None and worker.is_alive())
                        or time.monotonic() >= stop_ingress):
                    raw.close()
                    continue
                admitted += 1
                deadline = min(stop_ingress, time.monotonic() + request_seconds)
                worker = threading.Thread(target=_handle, args=(
                    raw, context, fingerprint, authority, upstream_port, deadline, slot),
                    kwargs={"report_source": address[0] if report_peer else None})
                worker.start()
    finally:
        if worker is not None:
            worker.join(max(0, cutoff - time.monotonic()))
            if worker.is_alive():
                raise RuntimeError("edge_cleanup_deadline")
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
    for option in ("server-cert", "server-key", "client-ca", "client-sha256"):
        parser.add_argument("--" + option, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--loopback-test", action="store_true")
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
    if not re.fullmatch(r"[a-f0-9]{64}", args.client_sha256):
        parser.error("invalid client fingerprint")
    purchase = args.physical_single_purchase or args.public_origin_single_purchase
    if (args.attempt_start is not None) != purchase:
        parser.error("--attempt-start is required exactly in single-purchase modes")
    origin = (args.bind_ip, args.bind_port, args.source_ip, args.hostname)
    hostname = HOST
    if args.public_origin_single_purchase:
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
    serve(bind=bind, port=port, source=source, hostname=hostname, context=ctx,
          fingerprint=args.client_sha256, upstream_port=upstream_port,
          purchase=purchase, attempt_start=args.attempt_start,
          report_peer=args.public_origin_single_purchase)


if __name__ == "__main__":
    main()
