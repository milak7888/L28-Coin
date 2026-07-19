"""Offline verifier for unsigned creator-wallet transfer intents."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from .creator_wallet_control_proof import FIXED_CREATOR_ADDRESS


INTENT_VERSION = "l28-creator-wallet-transfer-intent/v0.1"
INTENT_DOMAIN = "l28-creator-wallet-transfer-intent/v0.1"
VERIFIER_VERSION = "l28-creator-wallet-transfer-intent-verifier/v0.1"
MAX_INTENT_BYTES = 4096
INTENT_ID_DOMAIN = b"l28-creator-wallet-transfer-intent/v0.1\x00"
TOP_LEVEL_FIELDS = (
    "intent_version",
    "domain",
    "creator_address",
    "recipient_address",
    "amount",
    "nonce",
    "expires_at_unix",
    "control_bundle_sha256",
    "control_bundle_aggregate_commitment",
    "intent_id",
)
ADDRESS_RE = re.compile(r"L28[0-9a-f]{40}\Z")
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
STABLE_CODES = (
    "ok",
    "invalid_expected_commitment",
    "invalid_input_type",
    "intent_too_large",
    "invalid_encoding",
    "invalid_json",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "intent_version_invalid",
    "domain_invalid",
    "creator_identity_mismatch",
    "recipient_invalid",
    "amount_invalid",
    "nonce_invalid",
    "expiry_invalid",
    "control_bundle_sha256_invalid",
    "control_bundle_aggregate_commitment_invalid",
    "control_bundle_mismatch",
    "intent_id_invalid",
    "intent_id_mismatch",
    "internal_error",
)
SUCCESS_CHECKS = (
    "schema_exact",
    "creator_identity_bound",
    "recipient_valid",
    "amount_valid",
    "nonce_committed",
    "expiry_committed",
    "control_bundle_bound",
    "intent_id_bound",
    "unsigned_non_activation",
)


class _DuplicateKey(ValueError):
    pass


class _IntentError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CreatorWalletTransferIntentResult:
    ok: bool
    code: str
    checks: tuple[str, ...] = ()
    intent_sha256: str = ""
    intent_id: str = ""
    creator_address: str = ""
    recipient_address: str = ""
    amount: int = 0
    expires_at_unix: int = 0
    control_bundle_sha256: str = ""
    control_bundle_aggregate_commitment: str = ""


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    del value
    raise ValueError("non-finite JSON constant")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_INTENT_BYTES:
            raise _IntentError("intent_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _IntentError("invalid_encoding") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _IntentError("invalid_encoding") from exc
        if len(encoded) > MAX_INTENT_BYTES:
            raise _IntentError("intent_too_large")
        return payload
    raise _IntentError("invalid_input_type")


def _parse(payload: str | bytes) -> dict[str, Any]:
    text = _decode(payload)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _IntentError("duplicate_key") from exc
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _IntentError("invalid_json") from exc
    if not isinstance(value, dict):
        raise _IntentError("invalid_top_level")
    return value


def _validate_expected_commitments(
    expected_control_bundle_sha256: str,
    expected_control_bundle_aggregate_commitment: str,
) -> None:
    if not isinstance(expected_control_bundle_sha256, str) or not HEX64_RE.fullmatch(
        expected_control_bundle_sha256
    ):
        raise _IntentError("invalid_expected_commitment")
    if not isinstance(expected_control_bundle_aggregate_commitment, str) or not HEX64_RE.fullmatch(
        expected_control_bundle_aggregate_commitment
    ):
        raise _IntentError("invalid_expected_commitment")


def _validate_schema(intent: dict[str, Any]) -> None:
    if tuple(intent.keys()) != TOP_LEVEL_FIELDS:
        raise _IntentError("schema_invalid")
    if intent["intent_version"] != INTENT_VERSION:
        raise _IntentError("intent_version_invalid")
    if intent["domain"] != INTENT_DOMAIN:
        raise _IntentError("domain_invalid")
    if intent["creator_address"] != FIXED_CREATOR_ADDRESS:
        raise _IntentError("creator_identity_mismatch")
    recipient = intent["recipient_address"]
    if (
        not isinstance(recipient, str)
        or not ADDRESS_RE.fullmatch(recipient)
        or recipient == FIXED_CREATOR_ADDRESS
    ):
        raise _IntentError("recipient_invalid")
    if type(intent["amount"]) is not int or intent["amount"] <= 0:
        raise _IntentError("amount_invalid")
    if not isinstance(intent["nonce"], str) or not HEX64_RE.fullmatch(intent["nonce"]):
        raise _IntentError("nonce_invalid")
    if type(intent["expires_at_unix"]) is not int or intent["expires_at_unix"] <= 0:
        raise _IntentError("expiry_invalid")
    if not isinstance(intent["control_bundle_sha256"], str) or not HEX64_RE.fullmatch(
        intent["control_bundle_sha256"]
    ):
        raise _IntentError("control_bundle_sha256_invalid")
    if not isinstance(intent["control_bundle_aggregate_commitment"], str) or not HEX64_RE.fullmatch(
        intent["control_bundle_aggregate_commitment"]
    ):
        raise _IntentError("control_bundle_aggregate_commitment_invalid")
    if not isinstance(intent["intent_id"], str) or not HEX64_RE.fullmatch(intent["intent_id"]):
        raise _IntentError("intent_id_invalid")


def _intent_id(intent: dict[str, Any]) -> str:
    body = {key: value for key, value in intent.items() if key != "intent_id"}
    return hashlib.sha256(INTENT_ID_DOMAIN + _canonical_bytes(body)).hexdigest()


def verify_creator_wallet_transfer_intent_json(
    payload: str | bytes,
    *,
    expected_control_bundle_sha256: str,
    expected_control_bundle_aggregate_commitment: str,
) -> CreatorWalletTransferIntentResult:
    try:
        _validate_expected_commitments(
            expected_control_bundle_sha256,
            expected_control_bundle_aggregate_commitment,
        )
        intent = _parse(payload)
        _validate_schema(intent)
        if (
            intent["control_bundle_sha256"] != expected_control_bundle_sha256
            or intent["control_bundle_aggregate_commitment"]
            != expected_control_bundle_aggregate_commitment
        ):
            raise _IntentError("control_bundle_mismatch")
        recomputed_intent_id = _intent_id(intent)
        if intent["intent_id"] != recomputed_intent_id:
            raise _IntentError("intent_id_mismatch")
        return CreatorWalletTransferIntentResult(
            True,
            "ok",
            SUCCESS_CHECKS,
            hashlib.sha256(_canonical_bytes(intent)).hexdigest(),
            recomputed_intent_id,
            intent["creator_address"],
            intent["recipient_address"],
            intent["amount"],
            intent["expires_at_unix"],
            intent["control_bundle_sha256"],
            intent["control_bundle_aggregate_commitment"],
        )
    except _IntentError as exc:
        return CreatorWalletTransferIntentResult(False, exc.code)
    except Exception:
        return CreatorWalletTransferIntentResult(False, "internal_error")


class CreatorWalletTransferIntentVerifier:
    @classmethod
    def verify_json(
        cls,
        payload: str | bytes,
        *,
        expected_control_bundle_sha256: str,
        expected_control_bundle_aggregate_commitment: str,
    ) -> CreatorWalletTransferIntentResult:
        del cls
        return verify_creator_wallet_transfer_intent_json(
            payload,
            expected_control_bundle_sha256=expected_control_bundle_sha256,
            expected_control_bundle_aggregate_commitment=(
                expected_control_bundle_aggregate_commitment
            ),
        )
