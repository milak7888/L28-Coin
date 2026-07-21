"""Offline creator-wallet transfer-intent authorization evidence verifier.

Binds one caller-supplied Foundation 33 public authorization to its
deterministic Foundation 33 report. Does not read files, load wallets, read
private keys, sign, transfer, mutate ledgers, use clocks, access replay state,
use networks, or activate runtime components.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .creator_wallet_transfer_intent_authorization import (
    STABLE_CODES as AUTHORIZATION_STABLE_CODES,
    verify_creator_wallet_transfer_intent_authorization_json,
)

EVIDENCE_VERSION = (
    "l28-creator-wallet-transfer-intent-authorization-evidence/v0.1"
)
VERIFIER_VERSION = (
    "l28-creator-wallet-transfer-intent-authorization-evidence-verifier/v0.1"
)
EVIDENCE_REPORT_VERSION = (
    "l28-creator-wallet-transfer-intent-authorization-evidence-report/v0.1"
)
AUTHORIZATION_REPORT_VERSION = (
    "l28-creator-wallet-transfer-intent-authorization-report/v0.1"
)
AUTHORIZATION_REPORT_DOMAIN = (AUTHORIZATION_REPORT_VERSION + "\x00").encode("utf-8")
AUTHORIZATION_CLI_CODES = (
    "invalid_path",
    "file_too_large",
    "io_error",
    "internal_error",
)
MAX_EVIDENCE_BYTES = 16384

TOP_LEVEL_FIELDS = (
    "evidence_version",
    "expected_control_bundle_sha256",
    "expected_control_bundle_aggregate_commitment",
    "authorization",
    "report",
)

REPORT_FIELDS = (
    "report_id",
    "report_version",
    "ok",
    "code",
    "checks",
    "authorization_sha256",
    "authorization_id",
    "intent_sha256",
    "intent_id",
    "creator_address",
    "recipient_address",
    "amount",
    "expires_at_unix",
    "control_bundle_sha256",
    "control_bundle_aggregate_commitment",
    "stable_codes",
    "runtime_activation",
    "wallet_loaded",
    "private_key_read",
    "signature_created",
    "transfer_created",
    "ledger_mutated",
    "clock_access",
    "replay_state_access",
    "network_access",
    "execution_authorized",
)

SUCCESS_CHECKS = (
    "schema_exact",
    "commitments_bound",
    "authorization_reverified",
    "report_schema_exact",
    "report_recomputed",
    "evidence_hash_bound",
)

STABLE_CODES = (
    "ok",
    "input_type_invalid",
    "input_too_large",
    "encoding_invalid",
    "json_invalid",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "invalid_expected_commitment",
    "authorization_invalid",
    "report_invalid",
    "internal_error",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
REPORT_FALSE_FLAGS = (
    "runtime_activation",
    "wallet_loaded",
    "private_key_read",
    "signature_created",
    "transfer_created",
    "ledger_mutated",
    "clock_access",
    "replay_state_access",
    "network_access",
    "execution_authorized",
)


class _DuplicateKey(ValueError):
    pass


class _EvidenceError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CreatorWalletTransferIntentAuthorizationEvidenceResult:
    ok: bool
    code: str
    checks: tuple[str, ...] = ()
    evidence_sha256: str = ""
    authorization_sha256: str = ""
    authorization_id: str = ""


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise _EvidenceError("json_invalid")


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _EvidenceError("schema_invalid") from exc


def _json_bytes_preserve_order(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _EvidenceError("authorization_invalid") from exc


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_EVIDENCE_BYTES:
            raise _EvidenceError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _EvidenceError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _EvidenceError("encoding_invalid") from exc
        if len(encoded) > MAX_EVIDENCE_BYTES:
            raise _EvidenceError("input_too_large")
        return payload
    raise _EvidenceError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _EvidenceError("duplicate_key") from exc
    except _EvidenceError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _EvidenceError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _EvidenceError("invalid_top_level")
    return value


def _authorization_report_id(body: dict[str, Any]) -> str:
    without_id = {key: value for key, value in body.items() if key != "report_id"}
    return hashlib.sha256(
        AUTHORIZATION_REPORT_DOMAIN + _canonical_bytes(without_id)
    ).hexdigest()


def _build_expected_authorization_report(result: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "report_version": AUTHORIZATION_REPORT_VERSION,
        "ok": result.ok,
        "code": result.code,
        "checks": list(result.checks),
        "authorization_sha256": result.authorization_sha256,
        "authorization_id": result.authorization_id,
        "intent_sha256": result.intent_sha256,
        "intent_id": result.intent_id,
        "creator_address": result.creator_address,
        "recipient_address": result.recipient_address,
        "amount": result.amount,
        "expires_at_unix": result.expires_at_unix,
        "control_bundle_sha256": result.control_bundle_sha256,
        "control_bundle_aggregate_commitment": (
            result.control_bundle_aggregate_commitment
        ),
        "stable_codes": list(AUTHORIZATION_STABLE_CODES) + list(AUTHORIZATION_CLI_CODES),
        "runtime_activation": False,
        "wallet_loaded": False,
        "private_key_read": False,
        "signature_created": False,
        "transfer_created": False,
        "ledger_mutated": False,
        "clock_access": False,
        "replay_state_access": False,
        "network_access": False,
        "execution_authorized": False,
    }
    return {"report_id": _authorization_report_id(body), **body}


def _validate_top_level(evidence: dict[str, Any]) -> None:
    if tuple(evidence.keys()) != TOP_LEVEL_FIELDS:
        raise _EvidenceError("schema_invalid")
    if evidence["evidence_version"] != EVIDENCE_VERSION:
        raise _EvidenceError("schema_invalid")
    bundle = evidence["expected_control_bundle_sha256"]
    aggregate = evidence["expected_control_bundle_aggregate_commitment"]
    if (
        not isinstance(bundle, str)
        or HEX64_RE.fullmatch(bundle) is None
        or not isinstance(aggregate, str)
        or HEX64_RE.fullmatch(aggregate) is None
    ):
        raise _EvidenceError("invalid_expected_commitment")
    if not isinstance(evidence["authorization"], dict):
        raise _EvidenceError("authorization_invalid")
    if not isinstance(evidence["report"], dict):
        raise _EvidenceError("report_invalid")


def _validate_report_schema(report: dict[str, Any]) -> None:
    if tuple(report.keys()) != REPORT_FIELDS:
        raise _EvidenceError("report_invalid")
    if (
        not isinstance(report["report_id"], str)
        or HEX64_RE.fullmatch(report["report_id"]) is None
    ):
        raise _EvidenceError("report_invalid")
    if report["report_version"] != AUTHORIZATION_REPORT_VERSION:
        raise _EvidenceError("report_invalid")
    if not isinstance(report["ok"], bool):
        raise _EvidenceError("report_invalid")
    if report["code"] not in AUTHORIZATION_STABLE_CODES:
        raise _EvidenceError("report_invalid")
    if not isinstance(report["checks"], list) or not all(
        isinstance(item, str) for item in report["checks"]
    ):
        raise _EvidenceError("report_invalid")
    for name in (
        "authorization_sha256",
        "authorization_id",
        "intent_sha256",
        "intent_id",
        "control_bundle_sha256",
        "control_bundle_aggregate_commitment",
    ):
        value = report[name]
        if not isinstance(value, str) or (value and HEX64_RE.fullmatch(value) is None):
            raise _EvidenceError("report_invalid")
    if not isinstance(report["creator_address"], str):
        raise _EvidenceError("report_invalid")
    if not isinstance(report["recipient_address"], str):
        raise _EvidenceError("report_invalid")
    if type(report["amount"]) is not int:
        raise _EvidenceError("report_invalid")
    if type(report["expires_at_unix"]) is not int:
        raise _EvidenceError("report_invalid")
    expected_codes = list(AUTHORIZATION_STABLE_CODES) + list(AUTHORIZATION_CLI_CODES)
    if report["stable_codes"] != expected_codes:
        raise _EvidenceError("report_invalid")
    for key in REPORT_FALSE_FLAGS:
        if report[key] is not False:
            raise _EvidenceError("report_invalid")
    if report["report_id"] != _authorization_report_id(report):
        raise _EvidenceError("report_invalid")


def _reverify_authorization(evidence: dict[str, Any]) -> Any:
    result = verify_creator_wallet_transfer_intent_authorization_json(
        _json_bytes_preserve_order(evidence["authorization"]),
        expected_control_bundle_sha256=evidence["expected_control_bundle_sha256"],
        expected_control_bundle_aggregate_commitment=(
            evidence["expected_control_bundle_aggregate_commitment"]
        ),
    )
    if not result.ok:
        raise _EvidenceError("authorization_invalid")
    return result


def verify_creator_wallet_transfer_intent_authorization_evidence_json(
    payload: str | bytes,
) -> CreatorWalletTransferIntentAuthorizationEvidenceResult:
    try:
        evidence = _parse(payload)
        _validate_top_level(evidence)
        _validate_report_schema(evidence["report"])
        result = _reverify_authorization(evidence)
        expected_report = _build_expected_authorization_report(result)
        if evidence["report"] != expected_report:
            raise _EvidenceError("report_invalid")
        if expected_report["execution_authorized"] is not False:
            raise _EvidenceError("report_invalid")
        return CreatorWalletTransferIntentAuthorizationEvidenceResult(
            True,
            "ok",
            SUCCESS_CHECKS,
            hashlib.sha256(_canonical_bytes(evidence)).hexdigest(),
            result.authorization_sha256,
            result.authorization_id,
        )
    except _EvidenceError as exc:
        return CreatorWalletTransferIntentAuthorizationEvidenceResult(False, exc.code)
    except Exception:
        return CreatorWalletTransferIntentAuthorizationEvidenceResult(
            False, "internal_error"
        )


class CreatorWalletTransferIntentAuthorizationEvidenceVerifier:
    @classmethod
    def verify_json(
        cls, payload: str | bytes
    ) -> CreatorWalletTransferIntentAuthorizationEvidenceResult:
        del cls
        return verify_creator_wallet_transfer_intent_authorization_evidence_json(payload)
