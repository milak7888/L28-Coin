# SPDX-License-Identifier: Apache-2.0
"""Public custody-readiness check for one disposable custody directory.

The check reads the public custody record only. It calls the existing custody
and signer-eligibility evaluators and keeps production eligibility blocked.
It does not load a key, sign, broadcast, or settle.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from coin.disposable_custody_continuity import (
    CUSTODY_PROFILE,
    KEY_NAME,
    PUBLIC_NAME,
    CustodyError,
    initialize_public,
    read_public_record,
)
from coin.signer_custody_evidence import (
    AUDIT_PROFILE,
    BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS,
    EVIDENCE_INVALID,
    TIME_PROFILE,
    UNRESOLVED_DECISIONS,
    canonical_bytes,
    evaluate_custody_evidence,
)
from coin.signer_gate_readiness import GATE_BLOCKED, reassess_signer_gate


READINESS_PROFILE = "l28-production-custody-readiness/v0.1"


class ReadinessError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def assess_public_custody(directory: str | Path) -> dict[str, Any]:
    record = read_public_record(directory)
    if record.get("profile") != CUSTODY_PROFILE:
        raise ReadinessError("custody_profile_rejected")
    custody = evaluate_custody_evidence(_honest_bundle(record))
    gate = reassess_signer_gate()
    if custody.get("CUSTODY_READINESS") != "UNRESOLVED" or custody.get("result") != BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS:
        raise ReadinessError("custody_readiness_overclaim")
    if gate.get("F171_SIGNER_ELIGIBILITY_RESULT") != "BLOCKED" or gate.get("result") != GATE_BLOCKED:
        raise ReadinessError("signer_eligibility_overclaim")
    if gate.get("CUSTODY_READINESS") != "UNRESOLVED":
        raise ReadinessError("custody_readiness_overclaim")
    return _report(record, custody, gate, production_claim_rejected=False)


def reject_production_claim(directory: str | Path) -> dict[str, Any]:
    record = read_public_record(directory)
    bundle = _honest_bundle(record)
    bundle["unresolved_decisions"]["LSOD-CUS-001"] = "RESOLVED"
    custody = evaluate_custody_evidence(bundle)
    if custody.get("result") != EVIDENCE_INVALID or custody.get("reason") != "unresolved_decision_claimed_resolved":
        raise ReadinessError("production_claim_not_rejected")
    if custody.get("CUSTODY_READINESS") != "UNRESOLVED" or custody.get("F171_SIGNER_ELIGIBILITY_RESULT") != "BLOCKED":
        raise ReadinessError("production_claim_not_rejected")
    return {
        "production_claim_rejected": True,
        "production_claim_reason": custody["reason"],
        "CUSTODY_READINESS": "UNRESOLVED",
        "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
        "SIGNER_RUNTIME_ACTIVE": False,
    }


def execute_production_custody_readiness(directory: str | Path) -> dict[str, Any]:
    custody_dir = Path(directory)
    record = initialize_public(custody_dir)
    identity = record["public_identity"]
    key_path = custody_dir / KEY_NAME
    aside = custody_dir.parent / f"{custody_dir.name}-key-aside"
    os.replace(key_path, aside)
    try:
        if key_path.exists():
            raise ReadinessError("private_material_read")
        report = assess_public_custody(custody_dir)
    finally:
        os.replace(aside, key_path)
        os.chmod(key_path, 0o600)
    if report["signer_public_identity"] != identity:
        raise ReadinessError("identity_mismatch")
    claim = reject_production_claim(custody_dir)
    refusal = _refuse_production_signer(custody_dir, identity)
    hello = _disposable_hello(custody_dir, identity)
    if hello != identity:
        raise ReadinessError("identity_mismatch")
    result = {
        **report,
        "production_claim_rejected": claim["production_claim_rejected"],
        "production_claim_reason": claim["production_claim_reason"],
        "production_signer_refused_before_key_load": refusal,
        "disposable_signer_started": True,
        "disposable_signer_identity": hello,
        "readiness_key_loaded": False,
        "private_material_in_evidence": False,
    }
    result.pop("key_loaded", None)
    _assert_key_unexposed(key_path, result)
    return result


def _honest_bundle(record: dict[str, Any]) -> dict[str, Any]:
    public = {
        "profile": record["profile"],
        "public_identity": record["public_identity"],
        "public_key": record["public_key"],
        "version": record["version"],
    }
    encoded = canonical_bytes(public)
    audit_hash = hashlib.sha256(b"l28-disposable-custody-public-audit\x00" + encoded).hexdigest()
    time_hash = hashlib.sha256(b"l28-disposable-custody-public-time\x00" + encoded).hexdigest()
    closed = {
        "status": "disposable_test_custody_only",
        "keys_loaded": False,
        "signer_invoked": False,
        "signing_attempted": False,
        "runtime_active": False,
    }
    return {
        "custody_policy": {
            "LSOD-CUS-002": "none",
            "generation_permitted": False,
            "import_permitted": False,
            "LSOD-CUS-008": "backup prohibited",
            "backup_permitted": False,
            "recovery_from_backup_permitted": False,
            "LSOD-CUS-012": "A",
            "custody_evidence_scope": "PUBLIC_NON_SECRET_ONLY",
        },
        "isolation_evidence": dict(closed),
        "access_control_evidence": {"status": "owner_only_disposable_directory"},
        "lifecycle_evidence": {"status": "disposable_restart_continuity_is_not_production_custody"},
        "revocation_evidence": {"status": "production_revocation_decision_unresolved"},
        "destruction_evidence": {"status": "production_destruction_decision_unresolved"},
        "compromise_response_evidence": {"status": "production_compromise_decision_unresolved"},
        "custody_verification_evidence": {
            "status": "public_record_only",
            "public_identity": record["public_identity"],
            "keys_loaded": False,
        },
        "audit_binding": {"profile": AUDIT_PROFILE, "evidence_hash": audit_hash},
        "trusted_time_binding": {"profile": TIME_PROFILE, "evidence_hash": time_hash},
        "unresolved_decisions": {name: "UNRESOLVED" for name in UNRESOLVED_DECISIONS},
    }


def _report(record: dict[str, Any], custody: dict[str, Any], gate: dict[str, Any], *, production_claim_rejected: bool) -> dict[str, Any]:
    return {
        "readiness_profile": READINESS_PROFILE,
        "custody_profile": record["profile"],
        "signer_public_identity": record["public_identity"],
        "custody_evidence_result": custody["result"],
        "custody_evidence_reason": custody["reason"],
        "gate_result": gate["result"],
        "gate_reason": gate["reason"],
        "production_claim_rejected": production_claim_rejected,
        "private_material_read": False,
        "key_loaded": False,
        "CUSTODY_READINESS": "UNRESOLVED",
        "RUNTIME_HARDENING": "UNRESOLVED",
        "FAULT_RECOVERY": "UNRESOLVED",
        "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
        "SIGNER_RUNTIME_ACTIVE": False,
        "SIGNING": False,
        "BROADCAST": False,
        "production_settlement": False,
        "production_keys_used": False,
        "canonical_history_touched": False,
    }


def _refuse_production_signer(directory: Path, identity: str) -> bool:
    completed = _run_signer(
        [
            "--role",
            "signer",
            "--custody-dir",
            str(directory),
            "--custody-mode",
            "reuse",
            "--expected-identity",
            identity,
            "--production-eligibility",
        ]
    )
    text = completed.stderr.decode("utf-8", errors="replace").strip()
    if completed.returncode == 0 or b"signer_ready" in completed.stdout or text != "production_eligibility_blocked":
        raise ReadinessError("production_signer_not_blocked")
    return True


def _disposable_hello(directory: Path, identity: str) -> str:
    from coin.isolated_nonproduction_signer import SHUTDOWN_PATH, _stop

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
            "reuse",
            "--expected-identity",
            identity,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert process.stdout is not None
    line = process.stdout.readline()
    ready: dict[str, Any] = {}
    try:
        ready = json.loads(line.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        process.kill()
        raise ReadinessError("disposable_signer_failed") from None
    try:
        if ready.get("coordination") != "signer_ready":
            raise ReadinessError("disposable_signer_failed")
        if ready.get("production_signing") is not False or ready.get("SIGNER_RUNTIME_ACTIVE") is not False:
            raise ReadinessError("production_signer_refused")
        if ready.get("identity") != identity:
            raise ReadinessError("identity_mismatch")
        return str(ready["identity"])
    finally:
        if process.poll() is None and type(ready.get("port")) is int:
            _stop(process, int(ready["port"]), SHUTDOWN_PATH)
        elif process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def _run_signer(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            [sys.executable, "-m", "coin.isolated_nonproduction_signer", *args],
            cwd=str(Path(__file__).resolve().parents[1]),
            capture_output=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ReadinessError("production_signer_not_blocked") from None


def _assert_key_unexposed(key_path: Path, result: dict[str, Any]) -> None:
    raw = key_path.read_bytes()
    try:
        blob = json.dumps(result, sort_keys=True).encode("utf-8")
        public = key_path.with_name(PUBLIC_NAME).read_bytes()
        if raw in blob or raw.hex().encode("ascii") in blob or raw.hex().encode("ascii") in public:
            raise ReadinessError("secret_material_forbidden")
    finally:
        del raw


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m coin.production_custody_readiness")
    parser.add_argument("--custody-dir")
    parser.add_argument("--claim-production-ready", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if not args.custody_dir:
            raise ReadinessError("custody_dir_required")
        if args.claim_production_ready:
            result = reject_production_claim(args.custody_dir)
        else:
            result = assess_public_custody(args.custody_dir)
    except (ReadinessError, CustodyError) as exc:
        sys.stderr.write(getattr(exc, "code", "readiness_failed") + "\n")
        return 1
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
