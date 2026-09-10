# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
from pathlib import Path

import pytest

from coin.signer_audit_log import SignerAuditLog
from coin.signer_trusted_time import (
    GENESIS_PREVIOUS_HASH,
    PROFILE,
    ROOT_HOST_COMPROMISE_RESISTANCE,
    SOURCE,
    TRUST_ROOT,
    TrustedTimeBackend,
    TrustedTimeError,
    canonical_bytes,
    evidence_hash,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/signer_trusted_time.py"
GATE_PATH = ROOT / "docs/l28_foundation173_trusted_time_backend_gate_v0.1.json"


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, key
        result[key] = value
    return result


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FakeClocks:
    def __init__(self, wall=1_700_000_000_000_000_000, mono=1_000):
        self.wall = wall
        self.mono = mono

    def time_ns(self):
        return self.wall

    def monotonic_ns(self):
        return self.mono


def backend(tmp_path, clocks=None, name="trusted-time.json"):
    clocks = clocks or FakeClocks()
    return TrustedTimeBackend(
        tmp_path / name,
        wall_clock=clocks.time_ns,
        monotonic_clock=clocks.monotonic_ns,
    ), clocks


def test_fresh_issuance_pass(tmp_path):
    time_backend, _clocks = backend(tmp_path)
    evidence = time_backend.issue()
    assert evidence["profile"] == PROFILE
    assert evidence["source"] == SOURCE
    assert evidence["sequence"] == 1
    assert evidence["previous_evidence_hash"] == GENESIS_PREVIOUS_HASH
    assert evidence["evidence_hash"] == evidence_hash(evidence)
    assert set(evidence) == {
        "profile",
        "source",
        "unix_time_ns",
        "monotonic_ns",
        "sequence",
        "previous_evidence_hash",
        "evidence_hash",
    }
    assert time_backend.latest() == evidence
    assert TRUST_ROOT == "HOST_OS_CLOCK"
    assert ROOT_HOST_COMPROMISE_RESISTANCE is False


def test_sequential_issuance_binds_previous_hash_and_increases_time(tmp_path):
    time_backend, clocks = backend(tmp_path)
    first = time_backend.issue()
    clocks.wall += 10
    clocks.mono += 5
    second = time_backend.issue()
    assert second["sequence"] == 2
    assert second["previous_evidence_hash"] == first["evidence_hash"]
    assert second["unix_time_ns"] > first["unix_time_ns"]
    assert second["monotonic_ns"] > first["monotonic_ns"]
    assert second["evidence_hash"] != first["evidence_hash"]


def test_persisted_evidence_verifies_after_restart(tmp_path):
    first_backend, clocks = backend(tmp_path)
    issued = first_backend.issue()
    restarted, clocks = backend(tmp_path, clocks=clocks)
    loaded = restarted.latest()
    assert loaded == issued
    clocks.wall += 1
    clocks.mono += 1
    follow = restarted.issue()
    assert follow["sequence"] == 2
    assert follow["previous_evidence_hash"] == issued["evidence_hash"]


def test_wall_clock_rollback_is_rejected(tmp_path):
    time_backend, clocks = backend(tmp_path)
    time_backend.issue()
    clocks.wall -= 1
    clocks.mono += 1
    with pytest.raises(TrustedTimeError, match="wall_clock_rollback"):
        time_backend.issue()


def test_in_process_monotonic_rollback_is_rejected(tmp_path):
    time_backend, clocks = backend(tmp_path)
    time_backend.issue()
    clocks.wall += 1
    clocks.mono -= 1
    with pytest.raises(TrustedTimeError, match="monotonic_rollback"):
        time_backend.issue()


def test_replay_and_duplicate_evidence_are_rejected(tmp_path):
    time_backend, clocks = backend(tmp_path)
    first = time_backend.issue()
    clocks.wall += 1
    clocks.mono += 1
    second = time_backend.issue()
    assert time_backend.verify_evidence(second) == second
    with pytest.raises(TrustedTimeError, match="replay_detected"):
        time_backend.verify_evidence(first)
    mutated = dict(second)
    mutated["unix_time_ns"] = second["unix_time_ns"] + 1
    mutated["evidence_hash"] = evidence_hash(mutated)
    with pytest.raises(TrustedTimeError, match="replay_detected"):
        time_backend.verify_evidence(mutated)


def test_corrupt_or_malformed_state_blocks_issuance(tmp_path):
    time_backend, clocks = backend(tmp_path)
    time_backend.issue()
    path = tmp_path / "trusted-time.json"
    original = path.read_bytes()
    path.write_bytes(b"{not-json")
    with pytest.raises(TrustedTimeError, match="state_corrupt"):
        time_backend.issue()
    path.write_bytes(original.replace(b"host_os_clock", b"host_os_clocx", 1))
    with pytest.raises(TrustedTimeError, match="state_corrupt"):
        time_backend.latest()


def test_duplicate_json_keys_are_rejected(tmp_path):
    time_backend, _clocks = backend(tmp_path)
    time_backend.issue()
    path = tmp_path / "trusted-time.json"
    text = path.read_text(encoding="utf-8")
    path.write_text(text[:-1] + ',"sequence":1}', encoding="utf-8")
    with pytest.raises(TrustedTimeError, match="duplicate_json_key"):
        time_backend.latest()


def test_atomic_persistence_and_fsync_order(tmp_path, monkeypatch):
    import os

    order = []
    real_fsync = os.fsync
    real_replace = os.replace

    def tracked_fsync(fd):
        order.append("fsync")
        return real_fsync(fd)

    def tracked_replace(src, dst):
        order.append("replace")
        return real_replace(src, dst)

    monkeypatch.setattr("coin.signer_trusted_time.os.fsync", tracked_fsync)
    monkeypatch.setattr("coin.signer_trusted_time.os.replace", tracked_replace)
    time_backend, _clocks = backend(tmp_path)
    evidence = time_backend.issue()
    assert order == ["fsync", "replace", "fsync"]
    persisted = json.loads((tmp_path / "trusted-time.json").read_text())
    assert persisted == evidence
    source = IMPL_PATH.read_text(encoding="utf-8")
    assert "os.replace" in source
    assert "os.fsync" in source
    assert "LOCK_EX" in source


def test_evidence_hash_binds_into_f172_audit_event(tmp_path):
    time_backend, _clocks = backend(tmp_path)
    evidence = time_backend.issue()
    audit = SignerAuditLog(tmp_path / "signer-audit-001.jsonl", "signer-audit-001")
    receipt = audit.append(
        {
            "decision_id": "decision-time-001",
            "request_id": "req-time-001",
            "idempotency_key": "idem-time-001",
            "decision": "BLOCKED",
            "reason_code": "custody_readiness_unresolved",
            "evidence_hash": hashlib.sha256(b"f173-decision").hexdigest(),
            "policy_hash": hashlib.sha256(b"f173-policy").hexdigest(),
            "approval_hash": hashlib.sha256(b"f173-approval").hexdigest(),
            "trusted_time_evidence_hash": evidence["evidence_hash"],
        }
    )
    assert receipt["sequence"] == 1
    records = [
        json.loads(line, object_pairs_hook=reject_duplicate_keys)
        for line in (tmp_path / "signer-audit-001.jsonl").read_text().splitlines()
    ]
    assert records[0]["event"]["trusted_time_evidence_hash"] == evidence["evidence_hash"]
    assert audit.verify()["ok"] is True


def test_caller_supplied_timestamp_is_not_trusted(tmp_path):
    time_backend, _clocks = backend(tmp_path)
    with pytest.raises(TrustedTimeError, match="caller_supplied_timestamp_rejected"):
        time_backend.issue(unix_time_ns=1)
    with pytest.raises(TrustedTimeError, match="caller_supplied_timestamp_rejected"):
        time_backend.issue(1)
    issued = time_backend.issue()
    assert issued["source"] == "host_os_clock"


def test_production_default_uses_stdlib_clocks(tmp_path):
    time_backend = TrustedTimeBackend(tmp_path / "prod-time.json")
    evidence = time_backend.issue()
    assert evidence["source"] == SOURCE
    assert type(evidence["unix_time_ns"]) is int
    assert type(evidence["monotonic_ns"]) is int
    assert time_backend.latest() == evidence


def test_no_network_signing_wallet_or_protocol_capability():
    source = IMPL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                calls.add(node.func.id)
    assert "coin" not in imports
    assert {"socket", "subprocess", "requests", "urllib", "http", "asyncio", "ntplib"}.isdisjoint(
        imports
    )
    assert "validate_transaction" not in calls
    assert {"sign", "broadcast", "mint", "settle", "connect"}.isdisjoint(calls)
    assert "time_ns" in source
    assert "monotonic_ns" in source
    assert "environ" not in source
    assert ".env" not in source
    assert "ntp" not in source.lower()


def test_gate_json_is_duplicate_free_and_does_not_overclaim():
    gate = load_json(GATE_PATH)
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate["trust_root"] == "HOST_OS_CLOCK"
    assert gate["ROOT_HOST_COMPROMISE_RESISTANCE"] is False
    assert gate["F172_PRODUCTION_AUDIT_BACKEND"] == "RESOLVED"
    assert gate["F173_PRODUCTION_TIME_BACKEND"] == "RESOLVED"
    assert gate["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert gate["production_dependencies"] == {
        "production_time_backend": "RESOLVED",
        "production_audit_backend": "RESOLVED",
        "custody_readiness": "UNRESOLVED",
        "runtime_hardening": "UNRESOLVED",
        "fault_recovery": "UNRESOLVED",
    }
    assert gate["activation_boundary"] == {
        "SIGNER_RUNTIME_ACTIVE": False,
        "SIGNING": False,
        "BROADCAST": False,
        "SETTLEMENT": False,
    }
    assert gate["security_review"] == {
        "PASS": 9,
        "GAP": 0,
        "BLOCKED": 0,
        "COMMIT_READY": True,
    }
    assert not any(gate["protected_authority"].values())
    assert canonical_bytes({"a": 1, "b": 2}) == b'{"a":1,"b":2}'
