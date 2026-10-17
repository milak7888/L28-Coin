# SPDX-License-Identifier: Apache-2.0
"""Disposable custody continuity tests. No private key is printed or stored in the repo."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import coin.disposable_custody_continuity as custody
import coin.isolated_nonproduction_signer as signer
from coin.disposable_offline_transfer_demo import public_identity
from coin.durable_restart_safe_service_demo import _exchange, _json_bytes
from coin.isolated_nonproduction_signer import SIGN_PATH, SHUTDOWN_PATH, _stop


def _secret_leaked(directory: Path, blob: bytes) -> bool:
    raw = (directory / custody.KEY_NAME).read_bytes()
    try:
        return raw in blob or raw.hex().encode("ascii") in blob
    finally:
        del raw


def test_initialization_derives_identity_and_reopens_same_identity(tmp_path: Path) -> None:
    directory = tmp_path / "custody"
    record = custody.initialize_public(directory)
    assert record["profile"] == custody.CUSTODY_PROFILE
    assert record["version"] == 1
    assert record["public_identity"] == public_identity(record["public_key"])
    assert custody.reopen_identity(directory, record["public_identity"]) == record["public_identity"]
    assert (directory / custody.KEY_NAME).stat().st_mode & 0o077 == 0
    assert directory.stat().st_mode & 0o077 == 0
    assert _secret_leaked(directory, (directory / custody.PUBLIC_NAME).read_bytes()) is False


def test_second_initialization_does_not_replace_existing_custody(tmp_path: Path) -> None:
    directory = tmp_path / "custody"
    custody.initialize_public(directory)
    before = (directory / custody.PUBLIC_NAME).read_bytes()
    with pytest.raises(custody.CustodyError) as exc:
        custody.initialize_public(directory)
    assert exc.value.code == "custody_exists"
    assert str(exc.value) == "custody_exists"
    assert (directory / custody.PUBLIC_NAME).read_bytes() == before


def test_missing_reuse_fails_closed_without_creating_a_key(tmp_path: Path) -> None:
    directory = tmp_path / "missing"
    directory.mkdir(mode=0o700)
    os.chmod(directory, 0o700)
    with pytest.raises(custody.CustodyError) as exc:
        custody.reopen_identity(directory, "l28disp_missing")
    assert exc.value.code == "custody_missing"
    assert list(directory.iterdir()) == []
    with pytest.raises(custody.CustodyError) as required:
        custody.load_signer_key(directory, "reuse", None)
    assert required.value.code == "custody_continuity_required"
    assert list(directory.iterdir()) == []


def test_corrupt_truncated_and_malformed_custody_fail_closed(tmp_path: Path) -> None:
    truncated = tmp_path / "truncated"
    record = custody.initialize_public(truncated)
    key_path = truncated / custody.KEY_NAME
    key_path.write_bytes(key_path.read_bytes()[:8])
    os.chmod(key_path, 0o600)
    with pytest.raises(custody.CustodyError) as exc:
        custody.reopen_identity(truncated, record["public_identity"])
    assert exc.value.code == "custody_corrupt"
    assert _secret_leaked(truncated, str(exc.value).encode("utf-8")) is False

    malformed = tmp_path / "malformed"
    custody.initialize_public(malformed)
    public_path = malformed / custody.PUBLIC_NAME
    public_path.write_bytes(b"{")
    os.chmod(public_path, 0o600)
    with pytest.raises(custody.CustodyError) as bad:
        custody.reopen_identity(malformed, record["public_identity"])
    assert bad.value.code == "custody_malformed"


def test_replacement_and_identity_mismatch_are_not_adopted(tmp_path: Path) -> None:
    original = tmp_path / "original"
    other = tmp_path / "other"
    first = custody.initialize_public(original)
    second = custody.initialize_public(other)
    for name in (custody.KEY_NAME, custody.PUBLIC_NAME):
        target = original / name
        target.write_bytes((other / name).read_bytes())
        os.chmod(target, 0o600)
    with pytest.raises(custody.CustodyError) as replaced:
        custody.reopen_identity(original, first["public_identity"])
    assert replaced.value.code == "custody_replaced"
    assert str(replaced.value) == "custody_replaced"

    mismatch = tmp_path / "mismatch"
    custody.initialize_public(mismatch)
    key_only = mismatch / custody.KEY_NAME
    key_only.write_bytes((other / custody.KEY_NAME).read_bytes())
    os.chmod(key_only, 0o600)
    with pytest.raises(custody.CustodyError) as corrupt:
        custody.reopen_identity(mismatch, first["public_identity"])
    assert corrupt.value.code == "custody_corrupt"
    assert second["public_identity"] != first["public_identity"]


def test_unsafe_permissions_fail_closed(tmp_path: Path) -> None:
    directory = tmp_path / "loose-key"
    record = custody.initialize_public(directory)
    os.chmod(directory / custody.KEY_NAME, 0o644)
    with pytest.raises(custody.CustodyError) as key_error:
        custody.reopen_identity(directory, record["public_identity"])
    assert key_error.value.code == "permissions_invalid"

    loose_dir = tmp_path / "loose-dir"
    loose_record = custody.initialize_public(loose_dir)
    os.chmod(loose_dir, 0o755)
    with pytest.raises(custody.CustodyError) as dir_error:
        custody.reopen_identity(loose_dir, loose_record["public_identity"])
    assert dir_error.value.code == "permissions_invalid"


def test_signer_allowlist_rejects_arbitrary_signing(tmp_path: Path) -> None:
    directory = tmp_path / "custody"
    record = custody.initialize_public(directory)
    signing_key = custody.load_signer_key(directory, "reuse", record["public_identity"])
    disposable = signer.DisposableSigner(signing_key, key_persisted=True, custody_profile=custody.CUSTODY_PROFILE)
    try:
        with pytest.raises(signer.IsolatedSignerError) as purpose:
            disposable.sign_payload({"purpose": "arbitrary_bytes", "payload": "aa"})
        assert purpose.value.code == "purpose_rejected"
        with pytest.raises(signer.IsolatedSignerError) as amount:
            disposable.sign_payload(
                {
                    "purpose": "transfer",
                    "receiver": record["public_identity"],
                    "amount": 27,
                    "timestamp": 1,
                    "nonce": 1,
                }
            )
        assert amount.value.code == "wrong_amount"
        assert disposable.hello()["key_persisted"] is True
        assert disposable.hello()["SIGNER_RUNTIME_ACTIVE"] is False
        assert disposable.hello()["SIGNING"] is False
        assert _secret_leaked(directory, json.dumps(disposable.hello()).encode("utf-8")) is False
    finally:
        disposable.close()
        del signing_key


def test_signer_process_rejects_arbitrary_bytes_before_signing(tmp_path: Path) -> None:
    directory = tmp_path / "custody"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "coin.isolated_nonproduction_signer",
            "--role",
            "signer",
            "--custody-dir",
            str(directory),
            "--custody-mode",
            "init",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(Path(signer.__file__).resolve().parents[1]),
    )
    assert process.stdout is not None
    line = process.stdout.readline()
    ready = json.loads(line)
    try:
        rejected = _exchange(
            int(ready["port"]),
            "POST",
            SIGN_PATH,
            _json_bytes({"purpose": "arbitrary_bytes", "payload": "aa"}),
        )
        assert rejected["_status"] == 400
        assert rejected["error"] == "purpose_rejected"
        assert rejected["ok"] is False
    finally:
        _stop(process, int(ready["port"]), SHUTDOWN_PATH)
    assert _secret_leaked(directory, line) is False
    assert _secret_leaked(directory, json.dumps(rejected).encode("utf-8")) is False


def test_symlink_key_path_is_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "custody"
    record = custody.initialize_public(directory)
    key_path = directory / custody.KEY_NAME
    parked = tmp_path / "parked"
    parked.write_bytes(key_path.read_bytes())
    key_path.unlink()
    key_path.symlink_to(parked)
    with pytest.raises(custody.CustodyError) as exc:
        custody.reopen_identity(directory, record["public_identity"])
    assert exc.value.code == "custody_path_rejected"


def test_source_reuses_canonical_validation_and_does_not_emit_secrets() -> None:
    source = Path(custody.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "validate_transaction" not in defined
    assert "def validate_transaction" not in source
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "print" not in calls
    assert "environ" not in source
    assert "expanduser" not in source
    assert "0.0.0.0" not in source
    assert "SIGNER_RUNTIME_ACTIVE = True" not in source
    signer_source = Path(signer.__file__).read_text(encoding="utf-8")
    signer_tree = ast.parse(signer_source)
    names = {node.id for node in ast.walk(signer_tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(signer_tree) if isinstance(node, ast.Attribute)}
    assert "private_bytes" not in names and "private_bytes" not in attributes
    assert "from_private_bytes" not in names and "from_private_bytes" not in attributes


def test_real_signer_restart_preserves_identity_and_payment(tmp_path: Path) -> None:
    result = custody.execute_disposable_custody_continuity(
        tmp_path / "custody",
        tmp_path / "state",
        "L28 enables machine payments between autonomous systems.",
    )
    assert result["signer_identity_continuity"] is True
    assert result["custody_reopened"] is True
    assert result["signer_identity_before_restart"] == result["signer_identity_after_restart"]
    assert result["signer_public_identity"].startswith("l28disp_")
    assert result["canonical_validation"] == "PASS"
    assert result["replay_rejected"] is True
    assert result["replay_service_executed"] is False
    assert (result["requester_balance_before"], result["provider_balance_before"]) == (100, 0)
    assert (result["requester_balance_after"], result["provider_balance_after"]) == (72, 28)
    run3 = result["run3"]
    assert run3["receiver"] == result["signer_public_identity"]
    assert (run3["requester_balance_before"], run3["requester_balance_after"]) == (72, 44)
    assert (run3["provider_balance_before"], run3["provider_balance_after"]) == (28, 56)
    assert run3["result_verified"] is True
    assert run3["receipt_verified"] is True
    assert run3["canonical_validation"] == "PASS"
    assert result["service_executed"] is True
    probes = result["custody_failure_verification"]
    assert probes["truncated_custody_rejected"] == "custody_corrupt"
    assert probes["replacement_rejected"] == "custody_replaced"
    assert probes["loose_key_rejected"] == "permissions_invalid"
    assert probes["loose_directory_rejected"] == "permissions_invalid"
    assert probes["signed_after_rejection"] is False
    assert result["custody_private_material_exposed"] is False
    assert result["canonical_history_touched"] is False
    assert result["production_keys_used"] is False
    assert result["production_signing"] is False
    assert result["canonical_broadcast_used"] is False
    assert result["mining_used"] is False
    assert result["production_settlement"] is False
    assert result["SIGNER_RUNTIME_ACTIVE"] is False
    assert result["SIGNING"] is False
    assert result["CUSTODY_READINESS"] == "UNRESOLVED"
    assert result["RUNTIME_HARDENING"] == "UNRESOLVED"
    assert result["FAULT_RECOVERY"] == "UNRESOLVED"
    assert result["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert _secret_leaked(tmp_path / "custody", json.dumps(result).encode("utf-8")) is False
