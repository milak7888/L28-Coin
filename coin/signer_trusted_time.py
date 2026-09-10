# SPDX-License-Identifier: Apache-2.0
"""Self-hosted trusted-time evidence backend for future signer eligibility.

Trust root is the host OS wall clock. This module does not resist a
compromised or root-controlled host. Importing is inert. It never signs,
broadcasts, settles, mints, loads keys, or calls
coin.tx_validation.validate_transaction. It never reads remote clock
sources and never accepts a caller-supplied timestamp as trusted time.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX lock is required
    fcntl = None


PROFILE = "l28-signer-trusted-time/v0.1"
SOURCE = "host_os_clock"
TRUST_ROOT = "HOST_OS_CLOCK"
ROOT_HOST_COMPROMISE_RESISTANCE = False
GENESIS_PREVIOUS_HASH = hashlib.sha256(
    b"L28-SIGNER-TRUSTED-TIME-V0.1-GENESIS"
).hexdigest()
HEX64 = 64
EVIDENCE_FIELDS = (
    "profile",
    "source",
    "unix_time_ns",
    "monotonic_ns",
    "sequence",
    "previous_evidence_hash",
    "evidence_hash",
)


class TrustedTimeError(ValueError):
    """Fail-closed trusted-time error; does not repair persisted state."""


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
            raise TrustedTimeError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value):
    raise TrustedTimeError("schema_invalid")


def _load_json(text):
    return json.loads(
        text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant
    )


def _is_hex64(value):
    return isinstance(value, str) and len(value) == HEX64 and all(
        char in "0123456789abcdef" for char in value
    )


def _is_natural_int(value):
    return type(value) is int and value >= 0


def _payload(evidence):
    return {key: evidence[key] for key in EVIDENCE_FIELDS if key != "evidence_hash"}


def evidence_hash(evidence):
    return hashlib.sha256(canonical_bytes(_payload(evidence))).hexdigest()


def _validate_evidence(evidence):
    if not isinstance(evidence, dict) or set(evidence) != set(EVIDENCE_FIELDS):
        raise TrustedTimeError("schema_invalid")
    if evidence["profile"] != PROFILE or evidence["source"] != SOURCE:
        raise TrustedTimeError("schema_invalid")
    if not _is_natural_int(evidence["unix_time_ns"]) or not _is_natural_int(evidence["monotonic_ns"]):
        raise TrustedTimeError("schema_invalid")
    if not _is_natural_int(evidence["sequence"]) or evidence["sequence"] < 1:
        raise TrustedTimeError("schema_invalid")
    if not _is_hex64(evidence["previous_evidence_hash"]):
        raise TrustedTimeError("schema_invalid")
    if evidence["sequence"] == 1 and evidence["previous_evidence_hash"] != GENESIS_PREVIOUS_HASH:
        raise TrustedTimeError("invalid_previous_evidence_hash")
    if not _is_hex64(evidence["evidence_hash"]) or evidence["evidence_hash"] != evidence_hash(evidence):
        raise TrustedTimeError("invalid_evidence_hash")


class TrustedTimeBackend:
    """Issue hash-chained host-clock evidence. No caller-supplied time."""

    def __init__(self, path, wall_clock=None, monotonic_clock=None):
        if fcntl is None:
            raise TrustedTimeError("exclusive_lock_unavailable")
        if wall_clock is not None and not callable(wall_clock):
            raise TrustedTimeError("schema_invalid")
        if monotonic_clock is not None and not callable(monotonic_clock):
            raise TrustedTimeError("schema_invalid")
        self._path = Path(path)
        self._lock_path = self._path.with_name(self._path.name + ".lock")
        self._wall_clock = wall_clock or time.time_ns
        self._monotonic_clock = monotonic_clock or time.monotonic_ns
        self._last_monotonic_ns = None
        self._seen_hashes = set()

    def issue(self, *args, **kwargs):
        if args or kwargs:
            raise TrustedTimeError("caller_supplied_timestamp_rejected")
        return self._locked(self._issue_locked)

    def latest(self):
        return self._locked(self._latest_locked)

    def verify_evidence(self, evidence):
        _validate_evidence(evidence)
        return self._locked(lambda fd: self._verify_evidence_locked(evidence))

    def _issue_locked(self, fd):
        head = self._read_verified_head()
        unix_time_ns = self._wall_clock()
        monotonic_ns = self._monotonic_clock()
        if not _is_natural_int(unix_time_ns) or not _is_natural_int(monotonic_ns):
            raise TrustedTimeError("clock_sample_invalid")
        if head is not None and unix_time_ns < head["unix_time_ns"]:
            raise TrustedTimeError("wall_clock_rollback")
        if self._last_monotonic_ns is not None and monotonic_ns <= self._last_monotonic_ns:
            raise TrustedTimeError("monotonic_rollback")
        previous = head["evidence_hash"] if head is not None else GENESIS_PREVIOUS_HASH
        evidence = {
            "profile": PROFILE,
            "source": SOURCE,
            "unix_time_ns": unix_time_ns,
            "monotonic_ns": monotonic_ns,
            "sequence": 1 if head is None else head["sequence"] + 1,
            "previous_evidence_hash": previous,
        }
        evidence["evidence_hash"] = evidence_hash(evidence)
        if evidence["evidence_hash"] in self._seen_hashes or (
            head is not None and evidence["evidence_hash"] == head["evidence_hash"]
        ):
            raise TrustedTimeError("replay_detected")
        self._persist(evidence)
        self._last_monotonic_ns = monotonic_ns
        self._seen_hashes.add(evidence["evidence_hash"])
        return dict(evidence)

    def _latest_locked(self, fd):
        head = self._read_verified_head()
        if head is not None:
            self._seen_hashes.add(head["evidence_hash"])
        return dict(head) if head is not None else None

    def _verify_evidence_locked(self, evidence):
        head = self._read_verified_head()
        if head is None:
            raise TrustedTimeError("state_unavailable")
        if evidence["sequence"] < head["sequence"]:
            raise TrustedTimeError("replay_detected")
        if evidence != head:
            raise TrustedTimeError("replay_detected")
        return dict(head)

    def _read_verified_head(self):
        if not self._path.exists():
            return None
        raw = self._path.read_bytes()
        if not raw:
            raise TrustedTimeError("state_corrupt")
        try:
            evidence = _load_json(raw.decode("utf-8"))
        except TrustedTimeError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise TrustedTimeError("state_corrupt") from error
        try:
            _validate_evidence(evidence)
        except TrustedTimeError as error:
            raise TrustedTimeError("state_corrupt") from error
        return evidence

    def _persist(self, evidence):
        payload = canonical_bytes(evidence)
        temporary = self._path.with_name(self._path.name + ".tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, self._path)
        parent = os.open(self._path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)

    def _locked(self, action):
        descriptor = os.open(self._lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            return action(descriptor)
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
