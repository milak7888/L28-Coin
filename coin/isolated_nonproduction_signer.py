# SPDX-License-Identifier: Apache-2.0
"""Isolated disposable signer process.

The process signs only the existing disposable service artifacts. With no
custody directory it holds one in-memory key and writes nothing. An explicit
disposable custody directory is used only when the continuity slice supplies
one. It does not validate payments, broadcast, or settle. Production signer
gates stay closed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin.disposable_offline_transfer_demo import (
    DEMO_TIMESTAMP,
    build_signed_transfer,
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
    DemoError,
    _public_key_hex,
    build_payment_authorization,
    build_service_quote,
    build_service_receipt,
    build_service_request,
    build_service_result,
)


PROFILE = "l28-isolated-nonproduction-signer/v0.1"
LOOPBACK_HOST = "127.0.0.1"
MAX_BODY_BYTES = 65536
HELLO_PATH = "/v1/l28/isolated-signer/hello"
SIGN_PATH = "/v1/l28/isolated-signer/sign"
SHUTDOWN_PATH = "/v1/l28/isolated-signer/shutdown"
PURPOSES = {
    "service_request": ("input_text", "provider_identity"),
    "service_quote": ("request",),
    "transfer": ("amount", "nonce", "receiver", "timestamp"),
    "payment_authorization": ("payment_tx", "quote", "request"),
    "service_result": ("output", "payment_tx_id", "quote", "request"),
    "service_receipt": ("payment_tx_id", "quote", "request", "service_result"),
}


class IsolatedSignerError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def assert_production_flags_closed() -> None:
    if any(
        (
            RUNTIME_AUTHORIZED,
            NETWORK_AUTHORIZED,
            TESTNET_START_AUTHORIZED,
            SIGNING_AUTHORIZED,
            MINING_AUTHORIZED,
            BROADCAST_AUTHORIZED,
            SETTLEMENT_AUTHORIZED,
        )
    ):
        raise IsolatedSignerError("identity_flag_mutated")


class DisposableSigner:
    def __init__(
        self,
        signing_key: Ed25519PrivateKey | None = None,
        *,
        key_persisted: bool = False,
        custody_profile: str | None = None,
    ) -> None:
        assert_production_flags_closed()
        if signing_key is None:
            self._key = Ed25519PrivateKey.generate()
            self._key_persisted = False
            self._custody_profile = None
        else:
            self._key = signing_key
            self._key_persisted = key_persisted
            self._custody_profile = custody_profile
        self.public_key = _public_key_hex(self._key)
        self.identity = public_identity(self.public_key)
        self._lock = threading.Lock()

    def close(self) -> None:
        self._key = None

    def hello(self) -> dict[str, Any]:
        body = {
            "profile": PROFILE,
            "public_key": self.public_key,
            "identity": self.identity,
            "production_keys_used": False,
            "production_signing": False,
            "SIGNER_RUNTIME_ACTIVE": False,
            "SIGNING": False,
            "key_persisted": self._key_persisted,
        }
        if self._custody_profile is not None:
            body["custody_profile"] = self._custody_profile
        return body

    def sign_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._key is None:
                raise IsolatedSignerError("signer_closed")
            if not isinstance(payload, dict):
                raise IsolatedSignerError("malformed_json")
            purpose = payload.get("purpose")
            if purpose not in PURPOSES:
                raise IsolatedSignerError("purpose_rejected")
            expected = ("purpose",) + PURPOSES[purpose]
            if tuple(sorted(payload)) != tuple(sorted(expected)):
                raise IsolatedSignerError("unexpected_field")
            if any(str(key).lower() in {"private_key", "seed", "mnemonic", "xprv"} for key in payload):
                raise IsolatedSignerError("secret_material_forbidden")
            return self._sign_locked(str(purpose), payload)

    def _sign_locked(self, purpose: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        key = self._key
        if purpose == "service_request":
            return build_service_request(
                key,
                provider_identity=payload["provider_identity"],
                input_text=payload["input_text"],
            )
        if purpose == "service_quote":
            quote = build_service_quote(key, request=payload["request"])
            if quote["provider_identity"] != self.identity or quote["amount"] != PRICE_L28:
                raise IsolatedSignerError("wrong_amount")
            return quote
        if purpose == "transfer":
            if payload["amount"] != PRICE_L28 or type(payload["amount"]) is not int:
                raise IsolatedSignerError("wrong_amount")
            if type(payload["timestamp"]) is not int or type(payload["nonce"]) is not int:
                raise IsolatedSignerError("malformed_json")
            return build_signed_transfer(
                key,
                receiver=payload["receiver"],
                amount=PRICE_L28,
                timestamp=payload["timestamp"],
                nonce=payload["nonce"],
            )
        if purpose == "payment_authorization":
            return build_payment_authorization(
                key,
                request=payload["request"],
                quote=payload["quote"],
                payment_tx=payload["payment_tx"],
            )
        if purpose == "service_result":
            return build_service_result(
                key,
                request=payload["request"],
                quote=payload["quote"],
                payment_tx_id=payload["payment_tx_id"],
                output=payload["output"],
            )
        return build_service_receipt(
            key,
            request=payload["request"],
            quote=payload["quote"],
            service_result=payload["service_result"],
            payment_tx_id=payload["payment_tx_id"],
        )


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=False, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: "_SignerServer"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, payload: Mapping[str, Any], status: int) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == HELLO_PATH:
            self._send(self.server.signer.hello(), 200)
            return
        if self.path == SHUTDOWN_PATH:
            self._send({"ok": True, "shutdown": True}, 200)
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self._send({"ok": False, "error": "path_not_found"}, 404)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY_BYTES or self.path != SIGN_PATH:
            code = "path_not_found" if self.path != SIGN_PATH else "oversized_body"
            self._send({"ok": False, "error": code}, 400 if self.path == SIGN_PATH else 404)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            signed = self.server.signer.sign_payload(payload)
        except (IsolatedSignerError, DemoError, UnicodeError, json.JSONDecodeError) as exc:
            self._send({"ok": False, "error": getattr(exc, "code", "malformed_json")}, 400)
            return
        self._send(signed, 200)


class _SignerServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, signer: DisposableSigner) -> None:
        self.signer = signer
        super().__init__((LOOPBACK_HOST, 0), _Handler)
        if self.server_address[0] != LOOPBACK_HOST:
            self.server_close()
            raise IsolatedSignerError("localhost_request_path")


def _spawn(role_args: list[str]) -> tuple[subprocess.Popen[str], dict[str, Any]]:
    process = subprocess.Popen(
        [sys.executable, *role_args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert process.stdout is not None
    ready = json.loads(process.stdout.readline())
    if ready.get("host") != LOOPBACK_HOST:
        process.kill()
        raise IsolatedSignerError("provider_start_failed")
    return process, ready


def _stop(process: subprocess.Popen[str], port: int, path: str) -> None:
    from coin.durable_restart_safe_service_demo import _exchange

    try:
        _exchange(port, "GET", path)
    except (OSError, json.JSONDecodeError, IsolatedSignerError, Exception):
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def execute_isolated_signer_purchase(state_dir: str | Path, input_text: str) -> dict[str, Any]:
    directory = Path(state_dir)
    directory.mkdir(parents=True, exist_ok=True)
    payer_process, payer = _spawn(["-m", "coin.isolated_nonproduction_signer", "--role", "signer"])
    provider_signer_process, provider_signer = _spawn(["-m", "coin.isolated_nonproduction_signer", "--role", "signer"])
    try:
        return _purchase_with_signers(directory, input_text, payer_process, payer, provider_signer_process, provider_signer)
    finally:
        if payer_process.poll() is None:
            _stop(payer_process, int(payer["port"]), SHUTDOWN_PATH)
        if provider_signer_process.poll() is None:
            _stop(provider_signer_process, int(provider_signer["port"]), SHUTDOWN_PATH)


def _purchase_with_signers(
    directory: Path,
    input_text: str,
    payer_process: subprocess.Popen[str],
    payer: Mapping[str, Any],
    provider_signer_process: subprocess.Popen[str],
    provider_signer: Mapping[str, Any],
) -> dict[str, Any]:
    from coin.durable_restart_safe_service_demo import (
        PAYMENT_PATH,
        REQUEST_PATH,
        SHUTDOWN_PATH,
        _exchange,
        _json_bytes,
    )
    from coin.two_agent_service_transaction_demo import (
        structured_text_analysis,
        verify_service_quote,
        verify_service_receipt,
        verify_service_result,
    )

    provider_process, provider_ready = _spawn(
        [
            "-m",
            "coin.durable_restart_safe_service_demo",
            "--role",
            "provider",
            "--state-dir",
            str(directory),
            "--port",
            "0",
            "--signer-port",
            str(provider_signer["port"]),
        ]
    )
    try:
        if payer.get("production_signing") is not False or payer.get("SIGNER_RUNTIME_ACTIVE") is not False:
            raise IsolatedSignerError("production_signer_refused")
        if provider_ready.get("coordination") != "provider_ready":
            raise IsolatedSignerError("provider_start_failed")
        provider_port = int(provider_ready["port"])
        hello = _exchange(provider_port, "GET", "/v1/l28/production-entry/provider_hello")
        hello.pop("_status", None)
        if hello.get("provider_identity") != provider_signer["identity"]:
            raise IsolatedSignerError("identity_mismatch")
        request = _signer_sign(
            int(payer["port"]),
            "service_request",
            {"provider_identity": hello["provider_identity"], "input_text": input_text},
        )
        quote = _exchange(provider_port, "POST", REQUEST_PATH, _json_bytes(request))
        quote.pop("_status", None)
        verify_service_quote(quote, request=request)
        payment_tx = _signer_sign(
            int(payer["port"]),
            "transfer",
            {
                "receiver": hello["provider_identity"],
                "amount": PRICE_L28,
                "timestamp": DEMO_TIMESTAMP,
                "nonce": 100,
            },
        )
        authorization = _signer_sign(
            int(payer["port"]),
            "payment_authorization",
            {"request": request, "quote": quote, "payment_tx": payment_tx},
        )
        package = {
            "request": request,
            "quote": quote,
            "payment_tx": payment_tx,
            "payment_authorization": authorization,
        }
        first = _exchange(provider_port, "POST", PAYMENT_PATH, _json_bytes(package))
        first.pop("_status", None)
        if first.get("ok") is not True:
            raise IsolatedSignerError(str(first.get("error", "payment_apply_failed")))
        verify_service_result(first["service_result"], request=request, quote=quote, payment_tx_id=payment_tx["id"])
        verify_service_receipt(
            first["receipt"],
            request=request,
            quote=quote,
            service_result=first["service_result"],
            payment_tx_id=payment_tx["id"],
        )
        if first["service_result"]["output"] != structured_text_analysis(input_text):
            raise IsolatedSignerError("tampered_result")
    finally:
        _stop(provider_process, int(provider_ready["port"]), SHUTDOWN_PATH)
    time.sleep(0.05)
    restarted, restarted_ready = _spawn(
        [
            "-m",
            "coin.durable_restart_safe_service_demo",
            "--role",
            "provider",
            "--state-dir",
            str(directory),
            "--port",
            "0",
            "--signer-port",
            str(provider_signer["port"]),
        ]
    )
    try:
        restarted_port = int(restarted_ready["port"])
        replay = _exchange(restarted_port, "POST", PAYMENT_PATH, _json_bytes(package))
        replay.pop("_status", None)
        if replay.get("ok") is not False or replay.get("error") != "replay":
            raise IsolatedSignerError("replay_not_rejected")
        fresh_tx = _signer_sign(
            int(payer["port"]),
            "transfer",
            {
                "receiver": provider_signer["identity"],
                "amount": PRICE_L28,
                "timestamp": DEMO_TIMESTAMP,
                "nonce": 101,
            },
        )
        fresh_request = _signer_sign(
            int(payer["port"]),
            "service_request",
            {"provider_identity": provider_signer["identity"], "input_text": input_text},
        )
        fresh_quote = _exchange(restarted_port, "POST", REQUEST_PATH, _json_bytes(fresh_request))
        fresh_quote.pop("_status", None)
        verify_service_quote(fresh_quote, request=fresh_request)
        fresh_authorization = _signer_sign(
            int(payer["port"]),
            "payment_authorization",
            {"request": fresh_request, "quote": fresh_quote, "payment_tx": fresh_tx},
        )
        fresh = _exchange(
            restarted_port,
            "POST",
            PAYMENT_PATH,
            _json_bytes(
                {
                    "request": fresh_request,
                    "quote": fresh_quote,
                    "payment_tx": fresh_tx,
                    "payment_authorization": fresh_authorization,
                }
            ),
        )
        fresh.pop("_status", None)
    finally:
        _stop(restarted, int(restarted_ready["port"]), SHUTDOWN_PATH)
        _stop(payer_process, int(payer["port"]), SHUTDOWN_PATH)
        _stop(provider_signer_process, int(provider_signer["port"]), SHUTDOWN_PATH)
    if fresh.get("ok") is not True:
        raise IsolatedSignerError(str(fresh.get("error", "payment_apply_failed")))
    if fresh["evidence"]["receiver"] != first["evidence"]["receiver"]:
        raise IsolatedSignerError("signer_identity_changed")
    if fresh["evidence"]["provider_balance_before"] != 28 or fresh["evidence"]["provider_balance_after"] != 56:
        raise IsolatedSignerError("balance_transition_mismatch")
    if fresh["evidence"]["requester_balance_before"] != 72 or fresh["evidence"]["requester_balance_after"] != 44:
        raise IsolatedSignerError("balance_transition_mismatch")
    if replay["evidence"]["service_executed"] is not False:
        raise IsolatedSignerError("replay_not_rejected")
    state_bytes = b"".join(path.read_bytes() for path in directory.rglob("*") if path.is_file())
    if b"PRIVATE KEY" in state_bytes or b"private_bytes" in state_bytes:
        raise IsolatedSignerError("secret_material_forbidden")
    return {
        "runtime_profile": PROFILE,
        "isolated_nonproduction_signer": True,
        "same_signer_identity_after_provider_restart": True,
        "key_persisted": False,
        "run1": first["evidence"],
        "run2_replay": replay["evidence"],
        "run3": fresh["evidence"],
        "production_keys_used": False,
        "production_signing": False,
        "SIGNER_RUNTIME_ACTIVE": False,
        "SIGNING": False,
        "canonical_broadcast_used": False,
        "production_settlement": False,
        "canonical_history_touched": False,
        "CUSTODY_READINESS": "UNRESOLVED",
        "RUNTIME_HARDENING": "UNRESOLVED",
        "FAULT_RECOVERY": "UNRESOLVED",
        "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
    }


def _signer_sign(port: int, purpose: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    from coin.durable_restart_safe_service_demo import _exchange, _json_bytes

    signed = _exchange(port, "POST", SIGN_PATH, _json_bytes({"purpose": purpose, **dict(payload)}))
    signed.pop("_status", None)
    if signed.get("ok") is False:
        raise IsolatedSignerError(str(signed.get("error", "signer_rejected")))
    return signed


def _open_disposable_signer(args: argparse.Namespace) -> DisposableSigner:
    if args.custody_dir is None and args.custody_mode is None and args.expected_identity is None:
        return DisposableSigner()
    if not args.custody_dir or args.custody_mode is None:
        raise IsolatedSignerError("custody_dir_required")
    from coin.disposable_custody_continuity import CUSTODY_PROFILE, CustodyError, load_signer_key

    try:
        signing_key = load_signer_key(args.custody_dir, args.custody_mode, args.expected_identity)
    except CustodyError as exc:
        raise IsolatedSignerError(exc.code) from None
    return DisposableSigner(signing_key, key_persisted=True, custody_profile=CUSTODY_PROFILE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m coin.isolated_nonproduction_signer")
    parser.add_argument("--role", choices=("signer", "parent"), default="parent")
    parser.add_argument("--state-dir")
    parser.add_argument("--custody-dir")
    parser.add_argument("--custody-mode", choices=("init", "reuse"))
    parser.add_argument("--expected-identity")
    parser.add_argument("--production-eligibility", action="store_true")
    parser.add_argument("--input", default="L28 enables machine payments between autonomous systems.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    signer: DisposableSigner | None = None
    server: _SignerServer | None = None
    thread: threading.Thread | None = None
    try:
        assert_production_flags_closed()
        if args.production_eligibility:
            raise IsolatedSignerError("production_eligibility_blocked")
        if args.role == "signer":
            signer = _open_disposable_signer(args)
            server = _SignerServer(signer)
            host, port = server.server_address
            ready = signer.hello()
            ready.update({"coordination": "signer_ready", "host": host, "port": port})
            sys.stdout.write(json.dumps(ready, sort_keys=True) + "\n")
            sys.stdout.flush()
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            thread.join()
            return 0
        if not args.state_dir:
            raise IsolatedSignerError("missing_state")
        result = execute_isolated_signer_purchase(args.state_dir, args.input)
    except (IsolatedSignerError, DemoError) as exc:
        sys.stderr.write(getattr(exc, "code", "signer_failed") + "\n")
        return 1
    finally:
        if server is not None and thread is not None and thread.is_alive():
            server.shutdown()
            thread.join(timeout=2)
        if server is not None:
            server.server_close()
        if signer is not None:
            signer.close()
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
