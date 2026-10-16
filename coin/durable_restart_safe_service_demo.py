# SPDX-License-Identifier: Apache-2.0
"""Disposable restart-safe paid-service runtime.

The provider keeps exactly-once disposable payment state in an explicit
directory. Private keys stay in the owning process and are not written.
This runtime is not production signing, custody, broadcast, or settlement.
"""

from __future__ import annotations

import argparse
import asyncio
import http.client
import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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
from coin.disposable_testnet_identity import (
    BROADCAST_AUTHORIZED,
    GENESIS_PROFILE,
    MINING_AUTHORIZED,
    NETWORK_AUTHORIZED,
    NETWORK_SCOPE,
    PROFILE as IDENTITY_PROFILE,
    PROTECTED_ECONOMIC_FACTS,
    PROTOCOL_VERSION,
    RUNTIME_AUTHORIZED,
    SETTLEMENT_AUTHORIZED,
    SIGNING_AUTHORIZED,
    TESTNET_START_AUTHORIZED,
    validate_and_bind_disposable_testnet_config,
)
from coin.two_agent_service_transaction_demo import (
    PRICE_L28,
    DemoError as ServiceDemoError,
    _perform_paid_service,
    _public_key_hex,
    build_payment_authorization,
    build_service_quote,
    build_service_receipt,
    build_service_request,
    build_service_result,
    structured_text_analysis,
    verify_payment_intent_binding,
    verify_service_quote,
    verify_service_receipt,
    verify_service_request,
    verify_service_result,
)


RUNTIME_PROFILE = "l28-production-entry-durable-runtime/v0.1"
NETWORK_ID = "L28-DISPOSABLE-PRODUCTION-ENTRY001"
DATA_DIR_TAG = "l28-disposable-testnet:production-entry001"
LOOPBACK_HOST = "127.0.0.1"
MAX_BODY_BYTES = 65536
REQUEST_TIMEOUT_SECONDS = 10.0
HELLO_PATH = "/v1/l28/production-entry/provider_hello"
REQUEST_PATH = "/v1/l28/production-entry/service_request"
PAYMENT_PATH = "/v1/l28/production-entry/payment"
SHUTDOWN_PATH = "/v1/l28/production-entry/shutdown"
MARKER_NAME = "runtime-initialized"
DB_NAME = "disposable_runtime.sqlite"


class DurableRuntimeError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def assert_identity_flags_unchanged() -> None:
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
        raise DurableRuntimeError("identity_flag_mutated")


def production_entry_binding() -> dict[str, Any]:
    assert_identity_flags_unchanged()
    binding = validate_and_bind_disposable_testnet_config(
        {
            "profile": IDENTITY_PROFILE,
            "protocol_version": PROTOCOL_VERSION,
            "network_scope": NETWORK_SCOPE,
            "network_id": NETWORK_ID,
            "data_dir_tag": DATA_DIR_TAG,
            "genesis": {
                "profile": GENESIS_PROFILE,
                "network_id": NETWORK_ID,
                "initial_height": 0,
                "initial_issued_supply": 0,
                "historical_checkpoint_imported": False,
                "historical_balances_loaded": False,
                "protected_economic_facts": dict(PROTECTED_ECONOMIC_FACTS),
            },
            "key_policy": {
                "allow_production_keys": False,
                "allow_creator_private_material": False,
                "allow_external_wallet_paths": False,
            },
            "acknowledge_disposable_test_only": True,
        }
    )
    if binding["network_id"] != NETWORK_ID or any(
        binding[name] is not False
        for name in (
            "runtime_authorized",
            "network_authorized",
            "testnet_start_authorized",
            "signing_authorized",
            "mining_authorized",
            "broadcast_authorized",
            "settlement_authorized",
        )
    ):
        raise DurableRuntimeError("identity_flag_mutated")
    return binding


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=5, isolation_level=None, check_same_thread=False)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


class DurableStore:
    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)
        self.db_path = self.state_dir / DB_NAME
        self.marker_path = self.state_dir / MARKER_NAME
        self.connection: sqlite3.Connection | None = None
        self.restart_generation = 0
        self.reopened = False

    def open(self) -> None:
        if self.state_dir.exists() and not self.state_dir.is_dir():
            raise DurableRuntimeError("missing_state")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        marker = self.marker_path.exists()
        database = self.db_path.exists()
        if marker != database:
            raise DurableRuntimeError("missing_state" if marker and not database else "corrupt_state")
        if database and self.db_path.stat().st_size < 16:
            raise DurableRuntimeError("corrupt_state")
        try:
            self.connection = _connect(self.db_path)
            if not database:
                self._create()
                self.marker_path.write_text(RUNTIME_PROFILE + "\n", encoding="utf-8")
                self.restart_generation = 1
                self.reopened = False
            else:
                self._require_schema()
                self.restart_generation = self._bump_generation()
                self.reopened = True
        except DurableRuntimeError:
            self.close()
            raise
        except sqlite3.Error as exc:
            self.close()
            raise DurableRuntimeError("corrupt_state") from exc

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def _require(self) -> sqlite3.Connection:
        if self.connection is None:
            raise DurableRuntimeError("missing_state")
        return self.connection

    def _create(self) -> None:
        connection = self._require()
        statements = (
            """
            CREATE TABLE meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                state_version INTEGER NOT NULL CHECK (state_version >= 0),
                restart_generation INTEGER NOT NULL CHECK (restart_generation >= 1),
                opening_seeded INTEGER NOT NULL CHECK (opening_seeded IN (0, 1))
            )
            """,
            """
            CREATE TABLE balances (
                identity TEXT PRIMARY KEY,
                amount INTEGER NOT NULL CHECK (amount >= 0)
            )
            """,
            """
            CREATE TABLE accepted_payments (
                payment_tx_id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                receiver TEXT NOT NULL,
                amount INTEGER NOT NULL,
                state_version INTEGER NOT NULL,
                receipt_id TEXT,
                service_executed INTEGER NOT NULL CHECK (service_executed IN (0, 1))
            )
            """,
            """
            CREATE TABLE audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state_version INTEGER NOT NULL,
                payment_tx_id TEXT NOT NULL,
                event TEXT NOT NULL
            )
            """,
            """
            CREATE TRIGGER meta_no_rollback
            BEFORE UPDATE ON meta
            WHEN NEW.state_version < OLD.state_version
              OR NEW.restart_generation < OLD.restart_generation
            BEGIN
                SELECT RAISE(ABORT, 'state_rollback');
            END
            """,
            """
            INSERT INTO meta(id, state_version, restart_generation, opening_seeded)
            VALUES (1, 0, 1, 0)
            """,
        )
        connection.execute("BEGIN IMMEDIATE")
        try:
            for statement in statements:
                connection.execute(statement)
            connection.execute("COMMIT")
        except sqlite3.Error:
            connection.execute("ROLLBACK")
            raise

    def _require_schema(self) -> None:
        connection = self._require()
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not {"meta", "balances", "accepted_payments", "audit"}.issubset(tables):
            raise DurableRuntimeError("corrupt_state")
        row = connection.execute(
            "SELECT state_version, restart_generation, opening_seeded FROM meta WHERE id=1"
        ).fetchone()
        if row is None or row[0] < 0 or row[1] < 1 or row[2] not in (0, 1):
            raise DurableRuntimeError("corrupt_state")

    def _bump_generation(self) -> int:
        connection = self._require()
        connection.execute("BEGIN IMMEDIATE")
        try:
            current = connection.execute("SELECT restart_generation FROM meta WHERE id=1").fetchone()
            if current is None:
                raise DurableRuntimeError("missing_state")
            updated = int(current[0]) + 1
            cursor = connection.execute(
                "UPDATE meta SET restart_generation=? WHERE id=1 AND restart_generation=?",
                (updated, current[0]),
            )
            if cursor.rowcount != 1:
                raise DurableRuntimeError("corrupt_state")
            connection.execute("COMMIT")
        except sqlite3.Error as exc:
            connection.execute("ROLLBACK")
            raise DurableRuntimeError("corrupt_state") from exc
        return updated

    def snapshot(self) -> dict[str, Any]:
        connection = self._require()
        meta = connection.execute(
            "SELECT state_version, restart_generation, opening_seeded FROM meta WHERE id=1"
        ).fetchone()
        if meta is None:
            raise DurableRuntimeError("missing_state")
        balances = {
            identity: int(amount)
            for identity, amount in connection.execute("SELECT identity, amount FROM balances")
        }
        accepted = {
            tx_id: {
                "sender": sender,
                "receiver": receiver,
                "amount": int(amount),
                "state_version": int(version),
                "service_executed": bool(executed),
                "receipt_id": receipt_id,
            }
            for tx_id, sender, receiver, amount, version, receipt_id, executed in connection.execute(
                """
                SELECT payment_tx_id, sender, receiver, amount, state_version, receipt_id, service_executed
                FROM accepted_payments
                """
            )
        }
        return {
            "state_version": int(meta[0]),
            "restart_generation": int(meta[1]),
            "opening_seeded": bool(meta[2]),
            "balances": balances,
            "accepted": accepted,
        }

    def commit_payment(
        self,
        *,
        sender: str,
        receiver: str,
        amount: int,
        payment_tx_id: str,
        balances_after: Mapping[str, int],
        expected_version: int,
    ) -> int:
        connection = self._require()
        connection.execute("BEGIN IMMEDIATE")
        try:
            meta = connection.execute(
                "SELECT state_version, opening_seeded FROM meta WHERE id=1"
            ).fetchone()
            if meta is None or int(meta[0]) != expected_version or int(meta[0]) < 0:
                raise DurableRuntimeError("missing_state")
            if connection.execute(
                "SELECT 1 FROM accepted_payments WHERE payment_tx_id=?",
                (payment_tx_id,),
            ).fetchone():
                raise DurableRuntimeError("replay")
            next_version = int(meta[0]) + 1
            cursor = connection.execute(
                """
                UPDATE meta
                SET state_version=?, opening_seeded=1
                WHERE id=1 AND state_version=?
                """,
                (next_version, expected_version),
            )
            if cursor.rowcount != 1:
                raise DurableRuntimeError("corrupt_state")
            for identity, balance in balances_after.items():
                if type(balance) is not int or balance < 0:
                    raise DurableRuntimeError("corrupt_state")
                connection.execute(
                    """
                    INSERT INTO balances(identity, amount) VALUES(?, ?)
                    ON CONFLICT(identity) DO UPDATE SET amount=excluded.amount
                    """,
                    (identity, balance),
                )
            connection.execute(
                """
                INSERT INTO accepted_payments(
                    payment_tx_id, sender, receiver, amount, state_version, receipt_id, service_executed
                ) VALUES(?, ?, ?, ?, ?, NULL, 0)
                """,
                (payment_tx_id, sender, receiver, amount, next_version),
            )
            connection.execute(
                "INSERT INTO audit(state_version, payment_tx_id, event) VALUES(?, ?, 'payment_committed')",
                (next_version, payment_tx_id),
            )
            connection.execute("COMMIT")
        except DurableRuntimeError:
            connection.execute("ROLLBACK")
            raise
        except sqlite3.Error as exc:
            connection.execute("ROLLBACK")
            raise DurableRuntimeError("corrupt_state") from exc
        return next_version

    def mark_executed(self, payment_tx_id: str, receipt_id: str) -> None:
        connection = self._require()
        cursor = connection.execute(
            """
            UPDATE accepted_payments
            SET service_executed=1, receipt_id=?
            WHERE payment_tx_id=? AND service_executed=0 AND receipt_id IS NULL
            """,
            (receipt_id, payment_tx_id),
        )
        if cursor.rowcount != 1:
            raise DurableRuntimeError("replay")
        version = connection.execute("SELECT state_version FROM meta WHERE id=1").fetchone()
        if version is None:
            raise DurableRuntimeError("missing_state")
        connection.execute(
            "INSERT INTO audit(state_version, payment_tx_id, event) VALUES(?, ?, 'receipt_linked')",
            (int(version[0]), payment_tx_id),
        )


def _ledger_from_snapshot(snapshot: Mapping[str, Any], sender: str, receiver: str) -> tuple[Any, dict[str, int], bool]:
    directory = tempfile.TemporaryDirectory(prefix="l28-production-entry-ledger-")
    ledger = _open_ledger(directory.name)
    opening = not snapshot["opening_seeded"]
    balances = dict(snapshot["balances"])
    if opening:
        if balances or snapshot["accepted"] or snapshot["state_version"] != 0:
            directory.cleanup()
            raise DurableRuntimeError("missing_state")
        balances = {sender: ALICE_INITIAL_BALANCE, receiver: BOB_INITIAL_BALANCE}
    else:
        balances.setdefault(sender, 0)
        balances.setdefault(receiver, 0)
    for identity, amount in balances.items():
        ledger.balances[identity] = amount
    ledger._seen_tx_ids.update(snapshot["accepted"])
    ledger._production_entry_directory = directory
    return ledger, balances, opening


def _evidence(
    *,
    snapshot: Mapping[str, Any],
    payment_tx_id: str,
    canonical_validation: str,
    payment_applied: bool,
    replay_rejected: bool,
    sender: str,
    receiver: str,
    sender_before: int,
    sender_after: int,
    receiver_before: int,
    receiver_after: int,
    service_executed: bool,
    result_verified: bool,
    receipt_verified: bool,
    reopened: bool,
) -> dict[str, Any]:
    return {
        "runtime_profile": RUNTIME_PROFILE,
        "network_id": NETWORK_ID,
        "state_version": snapshot["state_version"],
        "payment_tx_id": payment_tx_id,
        "canonical_validation": canonical_validation,
        "payment_applied": payment_applied,
        "replay_rejected": replay_rejected,
        "requester_balance_before": sender_before,
        "requester_balance_after": sender_after,
        "provider_balance_before": receiver_before,
        "provider_balance_after": receiver_after,
        "service_executed": service_executed,
        "result_verified": result_verified,
        "receipt_verified": receipt_verified,
        "restart_generation": snapshot["restart_generation"],
        "durable_state_reopened": reopened,
        "canonical_history_touched": False,
        "production_keys_used": False,
        "production_signing": False,
        "canonical_broadcast_used": False,
        "production_settlement": False,
        "sender": sender,
        "receiver": receiver,
        "durable_balances": {identity: int(amount) for identity, amount in snapshot["balances"].items()},
    }


class DurableProvider:
    def __init__(self, state_dir: str | Path) -> None:
        production_entry_binding()
        self.store = DurableStore(state_dir)
        self.store.open()
        self._key = Ed25519PrivateKey.generate()
        self.public_key = _public_key_hex(self._key)
        self.identity = public_identity(self.public_key)
        self._lock = threading.Lock()
        self.fatal = False

    def close(self) -> None:
        self._key = None  # type: ignore[assignment]
        self.store.close()

    def hello(self) -> dict[str, str]:
        return {"provider_identity": self.identity, "provider_public_key": self.public_key}

    def quote_for(self, request: Mapping[str, Any]) -> dict[str, Any]:
        verified = verify_service_request(request)
        if verified["provider_identity"] != self.identity:
            raise DurableRuntimeError("wrong_provider_identity")
        quote = build_service_quote(self._key, request=request)
        if quote["amount"] != PRICE_L28:
            raise DurableRuntimeError("wrong_amount")
        return quote

    def handle_payment(self, package: Mapping[str, Any], *, fault: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self.fatal:
                raise DurableRuntimeError("missing_state")
            try:
                return self._handle_locked(package, fault=fault)
            except DurableRuntimeError as exc:
                if exc.code in {"corrupt_state", "interrupted_after_commit"}:
                    self.fatal = True
                raise

    def _handle_locked(self, package: Mapping[str, Any], *, fault: str | None) -> dict[str, Any]:
        required = ("payment_authorization", "payment_tx", "quote", "request")
        if not isinstance(package, dict) or tuple(sorted(package)) != required:
            raise DurableRuntimeError("unexpected_field")
        payment_tx = package["payment_tx"]
        if not isinstance(payment_tx, dict) or not isinstance(payment_tx.get("id"), str):
            raise DurableRuntimeError("malformed_json")
        if not isinstance(package["request"], dict) or not isinstance(package["quote"], dict):
            raise DurableRuntimeError("malformed_json")
        if not isinstance(package["payment_authorization"], dict):
            raise DurableRuntimeError("malformed_json")
        sender = str(payment_tx.get("sender", ""))
        receiver = str(payment_tx.get("receiver", ""))
        snapshot = self.store.snapshot()
        known = payment_tx["id"] in snapshot["accepted"]
        ledger, seeded, _opening = _ledger_from_snapshot(snapshot, sender, receiver)
        try:
            canonical_ok, payment_tx_id, canonical_reason = classify_transfer(ledger, payment_tx)
            if known:
                if canonical_ok or canonical_reason != "replay" or payment_tx_id != payment_tx["id"]:
                    raise DurableRuntimeError("replay_not_rejected")
                record = snapshot["accepted"][payment_tx_id]
                sender_balance = int(snapshot["balances"].get(record["sender"], 0))
                receiver_balance = int(snapshot["balances"].get(record["receiver"], 0))
                return {
                    "ok": False,
                    "error": "replay",
                    "evidence": _evidence(
                        snapshot=snapshot,
                        payment_tx_id=payment_tx_id,
                        canonical_validation="replay",
                        payment_applied=False,
                        replay_rejected=True,
                        sender=record["sender"],
                        receiver=record["receiver"],
                        sender_before=sender_balance,
                        sender_after=sender_balance,
                        receiver_before=receiver_balance,
                        receiver_after=receiver_balance,
                        service_executed=False,
                        result_verified=False,
                        receipt_verified=False,
                        reopened=self.store.reopened,
                    ),
                }
            if not canonical_ok or canonical_reason != "ok":
                raise DurableRuntimeError(canonical_reason or "canonical_validation_failed")
            if payment_tx.get("amount") != PRICE_L28:
                raise DurableRuntimeError("wrong_amount")
            verify_payment_intent_binding(
                request=package["request"],
                quote=package["quote"],
                payment_tx=payment_tx,
                payment_authorization=package["payment_authorization"],
            )
            if fault == "before_commit":
                raise DurableRuntimeError("interrupted_before_commit")
            if not asyncio.run(apply_transfer(ledger, payment_tx)):
                raise DurableRuntimeError("payment_apply_failed")
            if ledger.issued_supply != 0 or ledger.mint_height != 0:
                raise DurableRuntimeError("canonical_history_touched")
            sender_after = ledger.get_balance(sender)
            receiver_after = ledger.get_balance(receiver)
            balances_after = dict(seeded)
            balances_after[sender] = sender_after
            balances_after[receiver] = receiver_after
            version = self.store.commit_payment(
                sender=sender,
                receiver=receiver,
                amount=PRICE_L28,
                payment_tx_id=payment_tx_id,
                balances_after=balances_after,
                expected_version=snapshot["state_version"],
            )
            if fault == "after_commit":
                raise DurableRuntimeError("interrupted_after_commit")
            output = _perform_paid_service(package["request"]["input"]["text"], payment_verified=True)
            service_result = build_service_result(
                self._key,
                request=package["request"],
                quote=package["quote"],
                payment_tx_id=payment_tx_id,
                output=output,
            )
            receipt = build_service_receipt(
                self._key,
                request=package["request"],
                quote=package["quote"],
                service_result=service_result,
                payment_tx_id=payment_tx_id,
            )
            verify_service_result(
                service_result,
                request=package["request"],
                quote=package["quote"],
                payment_tx_id=payment_tx_id,
            )
            verify_service_receipt(
                receipt,
                request=package["request"],
                quote=package["quote"],
                service_result=service_result,
                payment_tx_id=payment_tx_id,
            )
            self.store.mark_executed(payment_tx_id, str(receipt["receipt_id"]))
        finally:
            directory = getattr(ledger, "_production_entry_directory", None)
            if directory is not None:
                directory.cleanup()
        committed = self.store.snapshot()
        return {
            "ok": True,
            "service_result": service_result,
            "receipt": receipt,
            "evidence": _evidence(
                snapshot=committed,
                payment_tx_id=payment_tx_id,
                canonical_validation="PASS",
                payment_applied=True,
                replay_rejected=False,
                sender=sender,
                receiver=receiver,
                sender_before=seeded[sender],
                sender_after=sender_after,
                receiver_before=seeded[receiver],
                receiver_after=receiver_after,
                service_executed=True,
                result_verified=True,
                receipt_verified=True,
                reopened=self.store.reopened,
            ),
        }


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=False, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _read_json(body: bytes) -> dict[str, Any]:
    if len(body) > MAX_BODY_BYTES:
        raise DurableRuntimeError("oversized_body")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DurableRuntimeError("malformed_json") from exc
    if not isinstance(payload, dict):
        raise DurableRuntimeError("malformed_json")
    return payload


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: "_Server"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _error(self, code: str, status: int = 400) -> None:
        body = json.dumps({"ok": False, "error": code}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _ok(self, payload: Mapping[str, Any], status: int = 200) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> bytes:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else -1
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY_BYTES:
            raise DurableRuntimeError("oversized_body")
        body = self.rfile.read(length)
        if len(body) != length:
            raise DurableRuntimeError("truncated_body")
        return body

    def do_GET(self) -> None:
        if self.path == HELLO_PATH:
            self._ok(self.server.provider.hello())
            return
        if self.path == SHUTDOWN_PATH:
            self._ok({"ok": True, "shutdown": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self._error("path_not_found", 404)

    def do_POST(self) -> None:
        try:
            body = self._body()
            payload = _read_json(body)
            if self.path == REQUEST_PATH:
                self._ok(self.server.provider.quote_for(payload))
                return
            if self.path == PAYMENT_PATH:
                result = self.server.provider.handle_payment(payload)
                self._ok(result, 200 if result.get("ok") else 409)
                return
            self._error("path_not_found", 404)
        except (DurableRuntimeError, ServiceDemoError) as exc:
            self._error(getattr(exc, "code", "request_rejected"))


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, provider: DurableProvider, port: int) -> None:
        if type(port) is not int or not 0 <= port <= 65535:
            raise DurableRuntimeError("invalid_port")
        self.provider = provider
        super().__init__((LOOPBACK_HOST, port), _Handler)
        if self.server_address[0] != LOOPBACK_HOST:
            self.server_close()
            raise DurableRuntimeError("localhost_request_path")


def start_provider(state_dir: str | Path, port: int = 0) -> tuple[_Server, threading.Thread, DurableProvider]:
    provider = DurableProvider(state_dir)
    server = _Server(provider, port)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    return server, thread, provider


def stop_provider(server: _Server, thread: threading.Thread) -> None:
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()
    server.provider.close()


def _exchange(port: int, method: str, path: str, body: bytes | None = None) -> dict[str, Any]:
    connection = http.client.HTTPConnection(LOOPBACK_HOST, port, timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        connection.request(
            method,
            path,
            body=body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(body or b""))},
        )
        if connection.sock is not None and connection.sock.getpeername()[0] != LOOPBACK_HOST:
            raise DurableRuntimeError("localhost_request_path")
        response = connection.getresponse()
        payload = response.read(MAX_BODY_BYTES + 1)
    finally:
        connection.close()
    if len(payload) > MAX_BODY_BYTES:
        raise DurableRuntimeError("oversized_body")
    parsed = _read_json(payload)
    parsed["_status"] = response.status
    return parsed


def _purchase(port: int, payer: Ed25519PrivateKey, input_text: str, nonce: int) -> dict[str, Any]:
    hello = _exchange(port, "GET", HELLO_PATH)
    hello.pop("_status", None)
    request = build_service_request(payer, provider_identity=hello["provider_identity"], input_text=input_text)
    quote = _exchange(port, "POST", REQUEST_PATH, _json_bytes(request))
    quote.pop("_status", None)
    verify_service_quote(quote, request=request)
    if quote.get("amount") != PRICE_L28:
        raise DurableRuntimeError("wrong_amount")
    payment_tx = build_signed_transfer(
        payer,
        receiver=hello["provider_identity"],
        amount=PRICE_L28,
        timestamp=DEMO_TIMESTAMP,
        nonce=nonce,
    )
    authorization = build_payment_authorization(payer, request=request, quote=quote, payment_tx=payment_tx)
    package = {
        "request": request,
        "quote": quote,
        "payment_tx": payment_tx,
        "payment_authorization": authorization,
    }
    result = _exchange(port, "POST", PAYMENT_PATH, _json_bytes(package))
    if result.get("ok") is True:
        if result.get("_status") != 200:
            raise DurableRuntimeError("payment_apply_failed")
        verify_service_result(result["service_result"], request=request, quote=quote, payment_tx_id=payment_tx["id"])
        verify_service_receipt(
            result["receipt"],
            request=request,
            quote=quote,
            service_result=result["service_result"],
            payment_tx_id=payment_tx["id"],
        )
        if result["service_result"]["output"] != structured_text_analysis(input_text):
            raise DurableRuntimeError("tampered_result")
    result["payment_package"] = package
    return result


def _spawn_provider(state_dir: Path) -> tuple[subprocess.Popen[str], int]:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "coin.durable_restart_safe_service_demo",
            "--role",
            "provider",
            "--state-dir",
            str(state_dir),
            "--port",
            "0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert process.stdout is not None
    line = process.stdout.readline()
    ready = json.loads(line)
    if ready.get("coordination") != "provider_ready" or ready.get("host") != LOOPBACK_HOST:
        process.kill()
        raise DurableRuntimeError("provider_start_failed")
    return process, int(ready["port"])


def _stop_process(process: subprocess.Popen[str], port: int) -> None:
    try:
        _exchange(port, "GET", SHUTDOWN_PATH)
    except (DurableRuntimeError, OSError, json.JSONDecodeError):
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def execute_durable_restart_sequence(state_dir: str | Path, input_text: str) -> dict[str, Any]:
    directory = Path(state_dir)
    payer = Ed25519PrivateKey.generate()
    first_process, first_port = _spawn_provider(directory)
    try:
        first = _purchase(first_port, payer, input_text, 100)
    finally:
        _stop_process(first_process, first_port)
    if first.get("ok") is not True:
        raise DurableRuntimeError(str(first.get("error", "payment_apply_failed")))
    package = first.pop("payment_package")
    time.sleep(0.05)
    second_process, second_port = _spawn_provider(directory)
    try:
        replay = _exchange(second_port, "POST", PAYMENT_PATH, _json_bytes(package))
        if replay.get("_status") != 409 or replay.get("ok") is not False or replay.get("error") != "replay":
            raise DurableRuntimeError("replay_not_rejected")
        fresh = _purchase(second_port, payer, input_text, 101)
    finally:
        _stop_process(second_process, second_port)
    if fresh.get("ok") is not True:
        raise DurableRuntimeError(str(fresh.get("error", "payment_apply_failed")))
    fresh.pop("payment_package", None)
    if first["evidence"]["payment_tx_id"] == fresh["evidence"]["payment_tx_id"]:
        raise DurableRuntimeError("replay")
    if replay["evidence"]["requester_balance_after"] != 72 or replay["evidence"]["provider_balance_after"] != 28:
        raise DurableRuntimeError("balance_transition_mismatch")
    if replay["evidence"]["service_executed"] is not False:
        raise DurableRuntimeError("replay_not_rejected")
    original_receiver = first["evidence"]["receiver"]
    if fresh["evidence"]["durable_balances"].get(original_receiver) != 28:
        raise DurableRuntimeError("balance_transition_mismatch")
    if fresh["evidence"]["requester_balance_before"] != 72 or fresh["evidence"]["requester_balance_after"] != 44:
        raise DurableRuntimeError("balance_transition_mismatch")
    return {
        "runtime_profile": RUNTIME_PROFILE,
        "network_id": NETWORK_ID,
        "same_state_directory": True,
        "run1": first["evidence"],
        "run2_replay": replay["evidence"],
        "run3": fresh["evidence"],
        "canonical_history_touched": False,
        "production_keys_used": False,
        "production_signing": False,
        "canonical_broadcast_used": False,
        "production_settlement": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m coin.durable_restart_safe_service_demo")
    parser.add_argument("--role", choices=("parent", "provider"), default="parent")
    parser.add_argument("--state-dir")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--input", default="L28 enables machine payments between autonomous systems.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    provider: DurableProvider | None = None
    server: _Server | None = None
    thread: threading.Thread | None = None
    try:
        assert_identity_flags_unchanged()
        if args.role == "provider":
            if not args.state_dir:
                raise DurableRuntimeError("missing_state")
            provider = DurableProvider(args.state_dir)
            server = _Server(provider, args.port)
            host, port = server.server_address
            sys.stdout.write(
                json.dumps({"coordination": "provider_ready", "host": host, "port": port}, sort_keys=True) + "\n"
            )
            sys.stdout.flush()
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            thread.join()
            return 0
        state_dir = args.state_dir or tempfile.mkdtemp(prefix="l28-production-entry-")
        result = execute_durable_restart_sequence(state_dir, args.input)
    except (DurableRuntimeError, ServiceDemoError) as exc:
        sys.stderr.write(getattr(exc, "code", "runtime_failed") + "\n")
        return 1
    finally:
        if server is not None and thread is not None and thread.is_alive():
            server.shutdown()
            thread.join(timeout=2)
        if server is not None:
            server.server_close()
        if provider is not None:
            provider.close()
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
