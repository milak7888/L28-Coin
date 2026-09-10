# SPDX-License-Identifier: Apache-2.0
"""Self-hosted durable tamper-evident append-only signer audit log.

Importing this module is inert. It never signs, broadcasts, settles, mints,
loads keys, or calls coin.tx_validation.validate_transaction. It does not
obtain trusted time; it stores only a caller-supplied hash reference.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX lock is required
    fcntl = None


AUDIT_PROFILE = "l28-signer-audit-log/v0.1"
GENESIS_PREVIOUS_HASH = hashlib.sha256(b"L28-SIGNER-AUDIT-LOG-V0.1-GENESIS").hexdigest()
HEX64 = 64

ALLOWED_EVENT_FIELDS = frozenset(
    {
        "decision_id",
        "request_id",
        "idempotency_key",
        "decision",
        "result",
        "reason_code",
        "evidence_hash",
        "policy_hash",
        "approval_hash",
        "trusted_time_evidence_hash",
    }
)
HASH_FIELDS = frozenset(
    {
        "evidence_hash",
        "policy_hash",
        "approval_hash",
        "trusted_time_evidence_hash",
    }
)
SECRET_KEYS = frozenset(
    {
        "private_key",
        "seed",
        "seed_phrase",
        "mnemonic",
        "xprv",
        "wallet_credential",
        "wallet_credentials",
        "rpc_user",
        "rpc_password",
        "rpc_cookie",
        "rpc_credential",
        "token",
        "password",
        "secret",
    }
)
RECORD_FIELDS = (
    "audit_profile",
    "log_id",
    "sequence",
    "previous_hash",
    "event",
    "entry_hash",
)
RECEIPT_FIELDS = (
    "audit_profile",
    "log_id",
    "sequence",
    "previous_hash",
    "entry_hash",
)


class SignerAuditLogError(ValueError):
    """Fail-closed audit-log error; does not repair or rewrite history."""


def canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SignerAuditLogError("duplicate_json_key")
        result[key] = value
    return result


def _load_json(text):
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant)


def _reject_constant(value):
    raise SignerAuditLogError("schema_invalid")


def _is_hex64(value):
    return isinstance(value, str) and len(value) == HEX64 and all(
        char in "0123456789abcdef" for char in value
    )


def _contains_secret(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in SECRET_KEYS:
                return True
            if _contains_secret(value):
                return True
    elif isinstance(node, (list, tuple)):
        return any(_contains_secret(item) for item in node)
    return False


def _validate_log_id(log_id):
    if not isinstance(log_id, str) or not log_id or log_id != log_id.strip():
        raise SignerAuditLogError("schema_invalid")
    if log_id.startswith("/") or "\\" in log_id or "/" in log_id or ".." in log_id:
        raise SignerAuditLogError("path_forbidden")


def _validate_event(event):
    if not isinstance(event, dict):
        raise SignerAuditLogError("schema_invalid")
    if _contains_secret(event):
        raise SignerAuditLogError("secret_material_forbidden")
    unknown = set(event) - ALLOWED_EVENT_FIELDS
    if unknown:
        raise SignerAuditLogError("schema_invalid")
    if not event.get("decision_id") or not event.get("request_id"):
        raise SignerAuditLogError("schema_invalid")
    if not event.get("decision") and not event.get("result"):
        raise SignerAuditLogError("schema_invalid")
    for key, value in event.items():
        if not isinstance(value, str) or not value:
            raise SignerAuditLogError("schema_invalid")
        if key in HASH_FIELDS and not _is_hex64(value):
            raise SignerAuditLogError("schema_invalid")


def _payload(record):
    return {key: record[key] for key in RECORD_FIELDS if key != "entry_hash"}


def _entry_hash(record):
    return hashlib.sha256(canonical_bytes(_payload(record))).hexdigest()


def _receipt(record):
    return {key: record[key] for key in RECEIPT_FIELDS}


class SignerAuditLog:
    """Append-only JSONL audit store. No rewrite, delete, or truncate API."""

    def __init__(self, path, log_id):
        if fcntl is None:
            raise SignerAuditLogError("exclusive_lock_unavailable")
        _validate_log_id(log_id)
        self._path = Path(path)
        self._log_id = log_id

    def append(self, event):
        _validate_event(event)
        fd = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            records = self._read_verified(fd)
            previous_hash = records[-1]["entry_hash"] if records else GENESIS_PREVIOUS_HASH
            record = {
                "audit_profile": AUDIT_PROFILE,
                "log_id": self._log_id,
                "sequence": len(records) + 1,
                "previous_hash": previous_hash,
                "event": dict(event),
            }
            record["entry_hash"] = _entry_hash(record)
            line = canonical_bytes(record) + b"\n"
            os.lseek(fd, 0, os.SEEK_END)
            os.write(fd, line)
            os.fsync(fd)
            return _receipt(record)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def verify(self, expected_head=None):
        if not self._path.exists():
            if expected_head is not None:
                raise SignerAuditLogError("truncation_detected")
            return {"ok": True, "count": 0, "head": None}
        fd = os.open(self._path, os.O_RDONLY)
        fcntl.flock(fd, fcntl.LOCK_SH)
        try:
            records = self._read_verified(fd)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        head = _receipt(records[-1]) if records else None
        if expected_head is not None:
            matched = next(
                (
                    record
                    for record in records
                    if record["sequence"] == expected_head.get("sequence")
                ),
                None,
            )
            if matched is None:
                raise SignerAuditLogError("truncation_detected")
            if _receipt(matched) != expected_head:
                raise SignerAuditLogError("chain_broken")
        return {"ok": True, "count": len(records), "head": head}

    def _read_all(self, fd):
        os.lseek(fd, 0, os.SEEK_SET)
        chunks = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)

    def _read_verified(self, fd):
        raw = self._read_all(fd)
        if not raw:
            return []
        if not raw.endswith(b"\n"):
            raise SignerAuditLogError("log_corrupt")
        records = []
        expected_previous = GENESIS_PREVIOUS_HASH
        for index, line in enumerate(raw.splitlines(), start=1):
            if not line:
                raise SignerAuditLogError("log_corrupt")
            try:
                record = _load_json(line.decode("utf-8"))
            except SignerAuditLogError:
                raise
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                raise SignerAuditLogError("log_corrupt") from error
            self._assert_record(record, index, expected_previous)
            records.append(record)
            expected_previous = record["entry_hash"]
        return records

    def _assert_record(self, record, sequence, expected_previous):
        if not isinstance(record, dict) or set(record) != set(RECORD_FIELDS):
            raise SignerAuditLogError("log_corrupt")
        if record["audit_profile"] != AUDIT_PROFILE or record["log_id"] != self._log_id:
            raise SignerAuditLogError("log_corrupt")
        if record["sequence"] != sequence:
            raise SignerAuditLogError("invalid_sequence")
        if not _is_hex64(record["previous_hash"]) or record["previous_hash"] != expected_previous:
            raise SignerAuditLogError("invalid_previous_hash")
        try:
            _validate_event(record["event"])
        except SignerAuditLogError as error:
            raise SignerAuditLogError("log_corrupt") from error
        if not _is_hex64(record["entry_hash"]) or record["entry_hash"] != _entry_hash(record):
            raise SignerAuditLogError("invalid_entry_hash")
