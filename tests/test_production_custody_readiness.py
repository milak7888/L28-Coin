# SPDX-License-Identifier: Apache-2.0
"""Production custody readiness stays blocked for disposable custody."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import coin.disposable_custody_continuity as custody
import coin.isolated_nonproduction_signer as signer
import coin.production_custody_readiness as readiness
from coin.signer_custody_evidence import BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS
from coin.signer_gate_readiness import GATE_BLOCKED


def _secret_leaked(directory: Path, blob: bytes) -> bool:
    raw = (directory / custody.KEY_NAME).read_bytes()
    try:
        return raw in blob or raw.hex().encode("ascii") in blob
    finally:
        del raw


def test_public_assessment_does_not_read_the_private_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "custody"
    record = custody.initialize_public(directory)
    key_path = directory / custody.KEY_NAME
    aside = tmp_path / "aside"
    key_path.replace(aside)

    def fail_key_read(*_args, **_kwargs):
        raise AssertionError("private key read")

    monkeypatch.setattr(custody, "_read_key_bytes", fail_key_read)
    monkeypatch.setattr(custody, "load_signer_key", fail_key_read)
    report = readiness.assess_public_custody(directory)
    aside.replace(key_path)
    assert report["signer_public_identity"] == record["public_identity"]
    assert report["custody_evidence_result"] == BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS
    assert report["gate_result"] == GATE_BLOCKED
    assert report["CUSTODY_READINESS"] == "UNRESOLVED"
    assert report["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert report["key_loaded"] is False
    assert report["private_material_read"] is False
    assert report["SIGNER_RUNTIME_ACTIVE"] is False
    assert report["SIGNING"] is False
    assert report["BROADCAST"] is False
    assert report["production_settlement"] is False


def test_production_claim_is_rejected_and_eligibility_stays_blocked(tmp_path: Path) -> None:
    directory = tmp_path / "custody"
    readiness_record = custody.initialize_public(directory)
    claim = readiness.reject_production_claim(directory)
    assert claim["production_claim_rejected"] is True
    assert claim["production_claim_reason"] == "unresolved_decision_claimed_resolved"
    assert claim["CUSTODY_READINESS"] == "UNRESOLVED"
    assert claim["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert claim["SIGNER_RUNTIME_ACTIVE"] is False
    assert _secret_leaked(directory, json.dumps(claim).encode("utf-8")) is False
    assert readiness_record["public_identity"] not in json.dumps(claim) or claim["production_claim_rejected"] is True


def test_production_eligibility_flag_refuses_before_opening_custody(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "absent"
    code = signer.main(
        [
            "--role",
            "signer",
            "--production-eligibility",
            "--custody-dir",
            str(missing),
            "--custody-mode",
            "reuse",
            "--expected-identity",
            "l28disp_not_opened",
        ]
    )
    assert code == 1
    assert missing.exists() is False
    assert capsys.readouterr().err.strip() == "production_eligibility_blocked"


def test_missing_public_record_fails_closed(tmp_path: Path) -> None:
    directory = tmp_path / "empty"
    directory.mkdir(mode=0o700)
    with pytest.raises(custody.CustodyError) as exc:
        readiness.assess_public_custody(directory)
    assert exc.value.code == "custody_missing"
    assert list(directory.iterdir()) == []


def test_source_does_not_load_keys_or_define_a_validator() -> None:
    source = Path(readiness.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "validate_transaction" not in defined
    assert "load_signer_key" not in called and "load_signer_key" not in attributes
    assert "_read_key_bytes" not in called and "_read_key_bytes" not in attributes
    assert "private_bytes" not in called and "private_bytes" not in attributes
    assert "from_private_bytes" not in called and "from_private_bytes" not in attributes
    assert "print" not in called
    assert "environ" not in source
    signer_source = Path(signer.__file__).read_text(encoding="utf-8")
    signer_tree = ast.parse(signer_source)
    main_fn = next(node for node in signer_tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    main_source = ast.get_source_segment(signer_source, main_fn)
    assert main_source is not None
    assert main_source.index("production_eligibility") < main_source.index("_open_disposable_signer")


def test_real_readiness_process_blocks_production_eligibility(tmp_path: Path) -> None:
    result = readiness.execute_production_custody_readiness(tmp_path / "custody")
    assert result["signer_public_identity"] == result["disposable_signer_identity"]
    assert result["custody_evidence_result"] == BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS
    assert result["gate_result"] == GATE_BLOCKED
    assert result["production_claim_rejected"] is True
    assert result["production_signer_refused_before_key_load"] is True
    assert result["disposable_signer_started"] is True
    assert result["readiness_key_loaded"] is False
    assert "key_loaded" not in result
    assert result["CUSTODY_READINESS"] == "UNRESOLVED"
    assert result["RUNTIME_HARDENING"] == "UNRESOLVED"
    assert result["FAULT_RECOVERY"] == "UNRESOLVED"
    assert result["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert result["SIGNER_RUNTIME_ACTIVE"] is False
    assert result["SIGNING"] is False
    assert result["BROADCAST"] is False
    assert result["production_settlement"] is False
    assert result["canonical_history_touched"] is False
    assert _secret_leaked(tmp_path / "custody", json.dumps(result).encode("utf-8")) is False
