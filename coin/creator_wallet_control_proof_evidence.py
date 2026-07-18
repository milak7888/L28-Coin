"""Offline creator-wallet control-proof evidence verifier.

This verifier binds one caller-supplied Foundation 29 public control proof to
its deterministic Foundation 29 report. It does not read files, load wallets,
read private keys, sign, transfer, mutate ledgers, use networks, or activate
runtime components.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .creator_wallet_control_proof import (
    STABLE_CODES as PROOF_STABLE_CODES,
    SUCCESS_CHECKS as PROOF_SUCCESS_CHECKS,
    verify_creator_wallet_control_proof_json,
)


EVIDENCE_VERSION = "l28-creator-wallet-control-proof-evidence/v0.1"
VERIFIER_VERSION = "l28-creator-wallet-control-proof-evidence-verifier/v0.1"
REPORT_VERSION = "l28-creator-wallet-control-proof-report/v0.1"
EVIDENCE_REPORT_VERSION = "l28-creator-wallet-control-proof-evidence-report/v0.1"
MAX_EVIDENCE_BYTES = 8192

TOP_LEVEL_FIELDS = (
    "evidence_version",
    "expected_challenge_id",
    "proof",
    "report",
)

REPORT_FIELDS = (
    "report_id",
    "report_version",
    "ok",
    "code",
    "checks",
    "proof_sha256",
    "stable_codes",
    "runtime_activation",
    "wallet_loaded",
    "private_key_read",
    "signature_created",
    "transfer_created",
    "ledger_mutated",
    "network_access",
)

SUCCESS_CHECKS = (
    "schema_exact",
    "challenge_bound",
    "proof_reverified",
    "report_schema_exact",
    "report_recomputed",
    "evidence_hash_bound",
)

STABLE_CODES = (
    "ok",
    "invalid_input_type",
    "evidence_too_large",
    "invalid_json",
    "schema_invalid",
    "challenge_invalid",
    "proof_invalid",
    "report_invalid",
    "internal_error",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
PROOF_REPORT_DOMAIN = b"l28-creator-wallet-control-proof-report/v0.1\x00"


class _DuplicateKey(ValueError):
    pass


class _EvidenceError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CreatorWalletControlProofEvidenceResult:
    ok: bool
    code: str
    checks: tuple[str, ...] = ()
    evidence_sha256: str = ""
    proof_sha256: str = ""


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise _DuplicateKey("duplicate key")
        seen.add(key)
        output[key] = value
    return output


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_bytes_preserve_order(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _decode(payload: str | bytes) -> bytes:
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        raw = bytes(payload)
    else:
        raise _EvidenceError("invalid_input_type")
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise _EvidenceError("evidence_too_large")
    return raw


def _parse(payload: str | bytes) -> dict[str, Any]:
    raw = _decode(payload)
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise _EvidenceError("invalid_json") from None
    if not isinstance(value, dict):
        raise _EvidenceError("schema_invalid")
    return value


def _report_id(report: dict[str, Any]) -> str:
    body = {key: value for key, value in report.items() if key != "report_id"}
    return hashlib.sha256(PROOF_REPORT_DOMAIN + _canonical_bytes(body)).hexdigest()


def _build_expected_proof_report(
    *,
    ok: bool,
    code: str,
    checks: tuple[str, ...],
    proof_sha256: str,
) -> dict[str, Any]:
    report = {
        "report_version": REPORT_VERSION,
        "ok": ok,
        "code": code,
        "checks": list(checks),
        "proof_sha256": proof_sha256,
        "stable_codes": list(PROOF_STABLE_CODES),
        "runtime_activation": False,
        "wallet_loaded": False,
        "private_key_read": False,
        "signature_created": False,
        "transfer_created": False,
        "ledger_mutated": False,
        "network_access": False,
    }
    return {"report_id": _report_id(report), **report}


def _validate_top_level(evidence: dict[str, Any]) -> None:
    if tuple(evidence.keys()) != TOP_LEVEL_FIELDS:
        raise _EvidenceError("schema_invalid")
    if evidence["evidence_version"] != EVIDENCE_VERSION:
        raise _EvidenceError("schema_invalid")
    if not isinstance(evidence["expected_challenge_id"], str):
        raise _EvidenceError("challenge_invalid")
    if not HEX64_RE.fullmatch(evidence["expected_challenge_id"]):
        raise _EvidenceError("challenge_invalid")
    if not isinstance(evidence["proof"], dict):
        raise _EvidenceError("proof_invalid")
    if not isinstance(evidence["report"], dict):
        raise _EvidenceError("report_invalid")


def _validate_report_schema(report: dict[str, Any]) -> None:
    if tuple(report.keys()) != REPORT_FIELDS:
        raise _EvidenceError("report_invalid")
    if not isinstance(report["report_id"], str) or not HEX64_RE.fullmatch(report["report_id"]):
        raise _EvidenceError("report_invalid")
    if report["report_version"] != REPORT_VERSION:
        raise _EvidenceError("report_invalid")
    if not isinstance(report["ok"], bool):
        raise _EvidenceError("report_invalid")
    if report["code"] not in PROOF_STABLE_CODES:
        raise _EvidenceError("report_invalid")
    if not isinstance(report["checks"], list) or not all(isinstance(item, str) for item in report["checks"]):
        raise _EvidenceError("report_invalid")
    if not isinstance(report["proof_sha256"], str) or (
        report["proof_sha256"] and not HEX64_RE.fullmatch(report["proof_sha256"])
    ):
        raise _EvidenceError("report_invalid")
    if report["stable_codes"] != list(PROOF_STABLE_CODES):
        raise _EvidenceError("report_invalid")
    for key in (
        "runtime_activation",
        "wallet_loaded",
        "private_key_read",
        "signature_created",
        "transfer_created",
        "ledger_mutated",
        "network_access",
    ):
        if report[key] is not False:
            raise _EvidenceError("report_invalid")
    if report["report_id"] != _report_id(report):
        raise _EvidenceError("report_invalid")


def _reverify_proof(evidence: dict[str, Any]) -> tuple[bool, str, tuple[str, ...], str]:
    result = verify_creator_wallet_control_proof_json(
        _json_bytes_preserve_order(evidence["proof"]),
        expected_challenge_id=evidence["expected_challenge_id"],
    )
    if not result.ok:
        raise _EvidenceError("proof_invalid")
    return result.ok, result.code, result.checks, result.proof_sha256


def verify_creator_wallet_control_proof_evidence_json(
    payload: str | bytes,
) -> CreatorWalletControlProofEvidenceResult:
    try:
        evidence = _parse(payload)
        _validate_top_level(evidence)
        _validate_report_schema(evidence["report"])
        ok, code, checks, proof_sha256 = _reverify_proof(evidence)
        expected_report = _build_expected_proof_report(
            ok=ok,
            code=code,
            checks=checks,
            proof_sha256=proof_sha256,
        )
        if evidence["report"] != expected_report:
            raise _EvidenceError("report_invalid")
        return CreatorWalletControlProofEvidenceResult(
            True,
            "ok",
            SUCCESS_CHECKS,
            hashlib.sha256(_canonical_bytes(evidence)).hexdigest(),
            proof_sha256,
        )
    except _EvidenceError as exc:
        return CreatorWalletControlProofEvidenceResult(False, exc.code)
    except Exception:
        return CreatorWalletControlProofEvidenceResult(False, "internal_error")


class CreatorWalletControlProofEvidenceVerifier:
    @classmethod
    def verify_json(cls, payload: str | bytes) -> CreatorWalletControlProofEvidenceResult:
        del cls
        return verify_creator_wallet_control_proof_evidence_json(payload)
