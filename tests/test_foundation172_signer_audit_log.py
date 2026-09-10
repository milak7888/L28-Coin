# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
import os
import threading
from pathlib import Path

import pytest

from coin.signer_audit_log import (
    AUDIT_PROFILE,
    GENESIS_PREVIOUS_HASH,
    SignerAuditLog,
    SignerAuditLogError,
    canonical_bytes,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/signer_audit_log.py"
GATE_PATH = ROOT / "docs/l28_foundation172_signer_audit_backend_gate_v0.1.json"
HASH_A = hashlib.sha256(b"f172-evidence").hexdigest()
HASH_B = hashlib.sha256(b"f172-policy").hexdigest()
HASH_C = hashlib.sha256(b"f172-approval").hexdigest()
HASH_T = hashlib.sha256(b"f172-trusted-time-ref").hexdigest()


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


def event(suffix="001", **overrides):
    payload = {
        "decision_id": f"decision-{suffix}",
        "request_id": f"req-{suffix}",
        "idempotency_key": f"idem-{suffix}",
        "decision": "NOT_ELIGIBLE",
        "reason_code": "identity_evidence_unavailable",
        "evidence_hash": HASH_A,
        "policy_hash": HASH_B,
        "approval_hash": HASH_C,
        "trusted_time_evidence_hash": HASH_T,
    }
    payload.update(overrides)
    return payload


def open_log(tmp_path, name="signer-audit-001"):
    return SignerAuditLog(tmp_path / f"{name}.jsonl", name)


def persisted_records(path):
    records = []
    for line in path.read_bytes().splitlines():
        records.append(
            json.loads(line.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
        )
    return records


def test_fresh_log_append_and_verify_pass(tmp_path):
    log = open_log(tmp_path)
    receipt = log.append(event())
    verified = log.verify()
    assert verified["ok"] is True
    assert verified["count"] == 1
    assert verified["head"] == receipt
    assert receipt["audit_profile"] == AUDIT_PROFILE
    assert receipt["log_id"] == "signer-audit-001"
    assert receipt["sequence"] == 1
    assert receipt["previous_hash"] == GENESIS_PREVIOUS_HASH
    assert set(receipt) == {
        "audit_profile",
        "log_id",
        "sequence",
        "previous_hash",
        "entry_hash",
    }
    assert str(tmp_path) not in json.dumps(receipt)
    assert "/" not in receipt["log_id"]


def test_sequential_appends_preserve_exact_hash_chain(tmp_path):
    log = open_log(tmp_path)
    first = log.append(event("001"))
    second = log.append(event("002"))
    third = log.append(event("003"))
    records = persisted_records(tmp_path / "signer-audit-001.jsonl")
    assert [record["sequence"] for record in records] == [1, 2, 3]
    assert records[0]["previous_hash"] == GENESIS_PREVIOUS_HASH
    assert records[1]["previous_hash"] == first["entry_hash"]
    assert records[2]["previous_hash"] == second["entry_hash"]
    assert records[0]["entry_hash"] == first["entry_hash"]
    assert records[1]["entry_hash"] == second["entry_hash"]
    assert records[2]["entry_hash"] == third["entry_hash"]
    assert log.verify()["head"] == third


def test_receipt_matches_persisted_entry(tmp_path):
    log = open_log(tmp_path)
    receipt = log.append(event())
    record = persisted_records(tmp_path / "signer-audit-001.jsonl")[0]
    assert {key: record[key] for key in receipt} == receipt
    assert record["entry_hash"] == hashlib.sha256(
        canonical_bytes(
            {
                "audit_profile": record["audit_profile"],
                "log_id": record["log_id"],
                "sequence": record["sequence"],
                "previous_hash": record["previous_hash"],
                "event": record["event"],
            }
        )
    ).hexdigest()


def test_byte_and_field_tampering_is_detected(tmp_path):
    log = open_log(tmp_path)
    log.append(event())
    path = tmp_path / "signer-audit-001.jsonl"
    original = path.read_bytes()
    path.write_bytes(original.replace(b"NOT_ELIGIBLE", b"NOT_ELIGIBLX", 1))
    with pytest.raises(SignerAuditLogError, match="invalid_entry_hash"):
        log.verify()
    path.write_bytes(original[:-2] + b"x\n")
    with pytest.raises(SignerAuditLogError, match="log_corrupt|invalid_entry_hash"):
        log.verify()


def test_entry_reordering_is_detected(tmp_path):
    log = open_log(tmp_path)
    log.append(event("001"))
    log.append(event("002"))
    path = tmp_path / "signer-audit-001.jsonl"
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(lines[1] + lines[0])
    with pytest.raises(SignerAuditLogError, match="invalid_sequence|invalid_previous_hash"):
        log.verify()


def test_middle_entry_deletion_is_detected(tmp_path):
    log = open_log(tmp_path)
    log.append(event("001"))
    log.append(event("002"))
    log.append(event("003"))
    path = tmp_path / "signer-audit-001.jsonl"
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(lines[0] + lines[2])
    with pytest.raises(SignerAuditLogError, match="invalid_sequence|invalid_previous_hash"):
        log.verify()


def test_tail_truncation_is_detected_against_head_receipt(tmp_path):
    log = open_log(tmp_path)
    log.append(event("001"))
    log.append(event("002"))
    head = log.append(event("003"))
    path = tmp_path / "signer-audit-001.jsonl"
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(lines[0] + lines[1])
    assert log.verify()["count"] == 2
    with pytest.raises(SignerAuditLogError, match="truncation_detected"):
        log.verify(expected_head=head)


def test_invalid_sequence_previous_hash_and_entry_hash_are_rejected(tmp_path):
    path = tmp_path / "signer-audit-001.jsonl"
    log = open_log(tmp_path)
    receipt = log.append(event())
    record = persisted_records(path)[0]

    mutated = dict(record)
    mutated["sequence"] = 2
    path.write_bytes(canonical_bytes(mutated) + b"\n")
    with pytest.raises(SignerAuditLogError, match="invalid_sequence"):
        log.verify()

    mutated = dict(record)
    mutated["previous_hash"] = "ab" * 32
    mutated["entry_hash"] = hashlib.sha256(
        canonical_bytes(
            {
                "audit_profile": mutated["audit_profile"],
                "log_id": mutated["log_id"],
                "sequence": mutated["sequence"],
                "previous_hash": mutated["previous_hash"],
                "event": mutated["event"],
            }
        )
    ).hexdigest()
    path.write_bytes(canonical_bytes(mutated) + b"\n")
    with pytest.raises(SignerAuditLogError, match="invalid_previous_hash"):
        log.verify()

    mutated = dict(record)
    mutated["entry_hash"] = "cd" * 32
    path.write_bytes(canonical_bytes(mutated) + b"\n")
    with pytest.raises(SignerAuditLogError, match="invalid_entry_hash"):
        log.verify()
    assert receipt["previous_hash"] == GENESIS_PREVIOUS_HASH


def test_duplicate_json_keys_are_rejected(tmp_path):
    log = open_log(tmp_path)
    log.append(event())
    path = tmp_path / "signer-audit-001.jsonl"
    line = path.read_text(encoding="utf-8").rstrip("\n")
    path.write_text(line[:-1] + ',"sequence":1}\n', encoding="utf-8")
    with pytest.raises(SignerAuditLogError, match="duplicate_json_key"):
        log.verify()


def test_corrupt_existing_log_prevents_append(tmp_path):
    log = open_log(tmp_path)
    log.append(event())
    path = tmp_path / "signer-audit-001.jsonl"
    original = path.read_bytes()
    path.write_bytes(original.replace(b"NOT_ELIGIBLE", b"NOT_ELIGIBLX", 1))
    with pytest.raises(SignerAuditLogError):
        log.append(event("002"))
    assert path.read_bytes() == original.replace(b"NOT_ELIGIBLE", b"NOT_ELIGIBLX", 1)


def test_secret_bearing_events_are_rejected(tmp_path):
    log = open_log(tmp_path)
    with pytest.raises(SignerAuditLogError, match="secret_material_forbidden"):
        log.append(event(private_key="forbidden"))
    with pytest.raises(SignerAuditLogError, match="secret_material_forbidden"):
        log.append(event(mnemonic="forbidden"))
    with pytest.raises(SignerAuditLogError, match="secret_material_forbidden"):
        log.append(event(xprv="forbidden"))
    with pytest.raises(SignerAuditLogError, match="secret_material_forbidden"):
        log.append(event(token="forbidden"))
    assert not (tmp_path / "signer-audit-001.jsonl").exists()


def test_fsync_occurs_before_append_reports_success(tmp_path, monkeypatch):
    order = []
    real_fsync = os.fsync

    def tracked_fsync(fd):
        order.append("fsync")
        return real_fsync(fd)

    monkeypatch.setattr("coin.signer_audit_log.os.fsync", tracked_fsync)
    log = open_log(tmp_path)
    receipt = log.append(event())
    assert order == ["fsync"]
    assert receipt["sequence"] == 1

    def failing_fsync(fd):
        order.append("fsync_fail")
        raise OSError("fsync_failed")

    monkeypatch.setattr("coin.signer_audit_log.os.fsync", failing_fsync)
    with pytest.raises(OSError, match="fsync_failed"):
        log.append(event("002"))
    assert "fsync_fail" in order


def test_no_rewrite_delete_or_truncate_api():
    forbidden = {
        "rewrite",
        "overwrite",
        "delete",
        "remove",
        "truncate",
        "clear",
        "reset",
        "rewrite_entry",
        "delete_entry",
    }
    assert forbidden.isdisjoint(set(dir(SignerAuditLog)))


def test_concurrent_writers_are_exclusively_locked(tmp_path):
    log = open_log(tmp_path)
    errors = []

    def write(suffix):
        try:
            log.append(event(suffix))
        except Exception as error:  # noqa: BLE001 - collect worker failures
            errors.append(error)

    workers = [
        threading.Thread(target=write, args=(f"{index:03d}",))
        for index in range(1, 5)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert errors == []
    verified = log.verify()
    assert verified["ok"] is True
    assert verified["count"] == 4
    records = persisted_records(tmp_path / "signer-audit-001.jsonl")
    previous = GENESIS_PREVIOUS_HASH
    for index, record in enumerate(records, start=1):
        assert record["sequence"] == index
        assert record["previous_hash"] == previous
        previous = record["entry_hash"]


def test_implementation_has_no_signing_wallet_network_or_protocol_capability():
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
    assert {"socket", "subprocess", "requests", "urllib", "http", "asyncio"}.isdisjoint(imports)
    assert "validate_transaction" not in calls
    assert {"sign", "broadcast", "mint", "settle", "connect"}.isdisjoint(calls)
    assert "fcntl" in imports
    assert "LOCK_EX" in source
    assert "os.fsync" in source
    assert "environ" not in source
    assert ".env" not in source


def test_gate_json_is_duplicate_free_and_records_resolved_audit_only():
    gate = load_json(GATE_PATH)
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate["production_audit_backend"] == "RESOLVED"
    assert gate["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert gate["production_dependencies"] == {
        "production_time_backend": "UNRESOLVED",
        "production_audit_backend": "RESOLVED",
        "custody_readiness": "UNRESOLVED",
        "runtime_hardening": "UNRESOLVED",
        "fault_recovery": "UNRESOLVED",
    }
    assert gate["activation_boundary"]["SIGNER_RUNTIME_ACTIVE"] is False
    assert gate["activation_boundary"]["SIGNING"] is False
    assert gate["activation_boundary"]["BROADCAST"] is False
    assert gate["activation_boundary"]["SETTLEMENT"] is False
    assert gate["security_review"] == {
        "PASS": 7,
        "GAP": 0,
        "BLOCKED": 0,
        "COMMIT_READY": True,
    }
    assert not any(gate["protected_authority"].values())
