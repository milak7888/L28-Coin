"""Offline creator-wallet transfer-intent authorization-evidence receipt verifier.

Binds one successfully verified Foundation 34 authorization-evidence object to a
deterministic public receipt. Does not read files, load wallets, read private
keys, sign, transfer, mutate ledgers, use clocks, access replay state, use
networks, or activate runtime components.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .creator_wallet_transfer_intent_authorization_evidence import (
    SUCCESS_CHECKS as EVIDENCE_SUCCESS_CHECKS,
    verify_creator_wallet_transfer_intent_authorization_evidence_json,
)

RECEIPT_VERSION = (
    "l28-creator-wallet-transfer-intent-authorization-evidence-receipt/v0.1"
)
VERIFIER_VERSION = (
    "l28-creator-wallet-transfer-intent-authorization-evidence-receipt-verifier/v0.1"
)
REPORT_VERSION = (
    "l28-creator-wallet-transfer-intent-authorization-evidence-receipt-report/v0.1"
)
RECEIPT_ID_DOMAIN = (RECEIPT_VERSION + "\x00").encode("utf-8")
MAX_RECEIPT_BYTES = 24576

TOP_LEVEL_FIELDS = (
    "receipt_version",
    "expected_control_bundle_sha256",
    "expected_control_bundle_aggregate_commitment",
    "evidence",
    "evidence_sha256",
    "authorization_report_id",
    "authorization_sha256",
    "authorization_id",
    "checks",
    "execution_authorized",
    "receipt_id",
)

SUCCESS_CHECKS = (
    "schema_exact",
    "commitments_bound",
    "evidence_reverified",
    "authorization_report_bound",
    "evidence_hash_bound",
    "checks_bound",
    "receipt_id_bound",
    "offline_non_activation",
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
    "evidence_invalid",
    "commitment_mismatch",
    "authorization_report_invalid",
    "evidence_commitment_invalid",
    "checks_invalid",
    "receipt_id_invalid",
    "internal_error",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class _DuplicateKey(ValueError):
    pass


class _ReceiptError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult:
    ok: bool
    code: str
    checks: tuple[str, ...] = ()
    receipt_id: str = ""
    evidence_sha256: str = ""
    authorization_report_id: str = ""
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
    raise _ReceiptError("json_invalid")


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
        raise _ReceiptError("schema_invalid") from exc


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
        raise _ReceiptError("evidence_invalid") from exc


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_RECEIPT_BYTES:
            raise _ReceiptError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _ReceiptError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _ReceiptError("encoding_invalid") from exc
        if len(encoded) > MAX_RECEIPT_BYTES:
            raise _ReceiptError("input_too_large")
        return payload
    raise _ReceiptError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _ReceiptError("duplicate_key") from exc
    except _ReceiptError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _ReceiptError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _ReceiptError("invalid_top_level")
    return value


def _receipt_id(value: dict[str, Any]) -> str:
    body = {key: value[key] for key in TOP_LEVEL_FIELDS if key != "receipt_id"}
    return hashlib.sha256(RECEIPT_ID_DOMAIN + _canonical_bytes(body)).hexdigest()


def _require_hex64(value: Any, code: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _ReceiptError(code)
    return value


def _validate_top_level(receipt: dict[str, Any]) -> None:
    if tuple(receipt.keys()) != TOP_LEVEL_FIELDS:
        raise _ReceiptError("schema_invalid")
    if receipt["receipt_version"] != RECEIPT_VERSION:
        raise _ReceiptError("schema_invalid")
    _require_hex64(receipt["expected_control_bundle_sha256"], "invalid_expected_commitment")
    _require_hex64(
        receipt["expected_control_bundle_aggregate_commitment"],
        "invalid_expected_commitment",
    )
    if not isinstance(receipt["evidence"], dict):
        raise _ReceiptError("evidence_invalid")
    _require_hex64(receipt["evidence_sha256"], "schema_invalid")
    _require_hex64(receipt["authorization_report_id"], "schema_invalid")
    _require_hex64(receipt["authorization_sha256"], "schema_invalid")
    _require_hex64(receipt["authorization_id"], "schema_invalid")
    if not isinstance(receipt["checks"], list) or not all(
        isinstance(item, str) for item in receipt["checks"]
    ):
        raise _ReceiptError("schema_invalid")
    if receipt["execution_authorized"] is not False:
        raise _ReceiptError("schema_invalid")
    _require_hex64(receipt["receipt_id"], "schema_invalid")


def _bind_commitments(receipt: dict[str, Any]) -> None:
    evidence = receipt["evidence"]
    if (
        evidence.get("expected_control_bundle_sha256")
        != receipt["expected_control_bundle_sha256"]
        or evidence.get("expected_control_bundle_aggregate_commitment")
        != receipt["expected_control_bundle_aggregate_commitment"]
    ):
        raise _ReceiptError("commitment_mismatch")


def _reverify_evidence(receipt: dict[str, Any]) -> Any:
    result = verify_creator_wallet_transfer_intent_authorization_evidence_json(
        _json_bytes_preserve_order(receipt["evidence"])
    )
    if not result.ok:
        raise _ReceiptError("evidence_invalid")
    return result


def _bind_verification_result(receipt: dict[str, Any], result: Any) -> None:
    evidence = receipt["evidence"]
    report = evidence.get("report")
    if not isinstance(report, dict):
        raise _ReceiptError("authorization_report_invalid")
    report_id = report.get("report_id")
    if (
        not isinstance(report_id, str)
        or report_id != receipt["authorization_report_id"]
    ):
        raise _ReceiptError("authorization_report_invalid")
    if receipt["evidence_sha256"] != result.evidence_sha256:
        raise _ReceiptError("evidence_commitment_invalid")
    if (
        receipt["authorization_sha256"] != result.authorization_sha256
        or receipt["authorization_id"] != result.authorization_id
    ):
        raise _ReceiptError("evidence_commitment_invalid")
    if list(receipt["checks"]) != list(result.checks):
        raise _ReceiptError("checks_invalid")
    if tuple(result.checks) != EVIDENCE_SUCCESS_CHECKS:
        raise _ReceiptError("checks_invalid")


def verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
    payload: str | bytes,
) -> CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult:
    try:
        receipt = _parse(payload)
        _validate_top_level(receipt)
        _bind_commitments(receipt)
        result = _reverify_evidence(receipt)
        _bind_verification_result(receipt, result)
        expected_id = _receipt_id(receipt)
        if receipt["receipt_id"] != expected_id:
            raise _ReceiptError("receipt_id_invalid")
        if receipt["execution_authorized"] is not False:
            raise _ReceiptError("schema_invalid")
        return CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult(
            True,
            "ok",
            SUCCESS_CHECKS,
            expected_id,
            result.evidence_sha256,
            receipt["authorization_report_id"],
            result.authorization_sha256,
            result.authorization_id,
        )
    except _ReceiptError as exc:
        return CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult(
            False, exc.code
        )
    except Exception:
        return CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult(
            False, "internal_error"
        )


class CreatorWalletTransferIntentAuthorizationEvidenceReceiptVerifier:
    @classmethod
    def verify_json(
        cls, payload: str | bytes
    ) -> CreatorWalletTransferIntentAuthorizationEvidenceReceiptResult:
        del cls
        return verify_creator_wallet_transfer_intent_authorization_evidence_receipt_json(
            payload
        )
