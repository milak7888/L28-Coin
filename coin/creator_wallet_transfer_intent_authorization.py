"""Offline creator-wallet transfer-intent authorization verification."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .creator_wallet_control_proof import FIXED_CREATOR_ADDRESS, FIXED_CREATOR_PUBLIC_KEY
from .creator_wallet_transfer_intent import verify_creator_wallet_transfer_intent_json

AUTHORIZATION_VERSION = "l28-creator-wallet-transfer-intent-authorization/v0.1"
AUTHORIZATION_DOMAIN = AUTHORIZATION_VERSION
VERIFIER_VERSION = "l28-creator-wallet-transfer-intent-authorization-verifier/v0.1"
AUTHORIZATION_ID_DOMAIN = (AUTHORIZATION_VERSION + "\x00").encode("utf-8")
MAX_AUTHORIZATION_BYTES = 8192
TOP_LEVEL_FIELDS = (
    "authorization_version", "domain", "intent", "intent_sha256", "intent_id",
    "creator_address", "creator_public_key", "signature", "authorization_id",
)
SIGNATURE_PAYLOAD_FIELDS = (
    "authorization_version", "domain", "intent_sha256", "intent_id",
    "creator_address", "creator_public_key",
)
STABLE_CODES = (
    "ok", "invalid_expected_commitment", "input_type_invalid", "input_too_large",
    "encoding_invalid", "json_invalid", "duplicate_key", "invalid_top_level",
    "schema_invalid", "version_invalid", "domain_invalid", "intent_invalid",
    "intent_binding_invalid", "identity_invalid", "signature_invalid",
    "authorization_id_invalid", "internal_error",
)
SUCCESS_CHECKS = (
    "schema_exact", "intent_reverified", "intent_bound", "creator_identity_bound",
    "signature_verified", "authorization_id_bound", "offline_non_activation",
)
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX128_RE = re.compile(r"^[0-9a-f]{128}$")


class _DuplicateKey(ValueError):
    pass


class _AuthorizationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CreatorWalletTransferIntentAuthorizationResult:
    ok: bool
    code: str
    checks: tuple[str, ...] = ()
    authorization_sha256: str = ""
    authorization_id: str = ""
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


def _reject_constant(_: str) -> None:
    raise _AuthorizationError("json_invalid")


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_AUTHORIZATION_BYTES:
            raise _AuthorizationError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _AuthorizationError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _AuthorizationError("encoding_invalid") from exc
        if len(encoded) > MAX_AUTHORIZATION_BYTES:
            raise _AuthorizationError("input_too_large")
        return payload
    raise _AuthorizationError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload), object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _AuthorizationError("duplicate_key") from exc
    except _AuthorizationError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _AuthorizationError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _AuthorizationError("invalid_top_level")
    return value


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, allow_nan=False,
            separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _AuthorizationError("schema_invalid") from exc


def _intent_bytes(intent: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            intent, ensure_ascii=False, allow_nan=False,
            separators=(",", ":"), sort_keys=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _AuthorizationError("intent_invalid") from exc


def _validate_expected_commitments(bundle_sha256: str, aggregate: str) -> None:
    if (
        not isinstance(bundle_sha256, str) or HEX64_RE.fullmatch(bundle_sha256) is None
        or not isinstance(aggregate, str) or HEX64_RE.fullmatch(aggregate) is None
    ):
        raise _AuthorizationError("invalid_expected_commitment")


def _validate_schema(value: dict[str, Any]) -> None:
    if tuple(value.keys()) != TOP_LEVEL_FIELDS:
        raise _AuthorizationError("schema_invalid")
    if value["authorization_version"] != AUTHORIZATION_VERSION:
        raise _AuthorizationError("version_invalid")
    if value["domain"] != AUTHORIZATION_DOMAIN:
        raise _AuthorizationError("domain_invalid")
    if not isinstance(value["intent"], dict):
        raise _AuthorizationError("intent_invalid")
    if any(
        not isinstance(value[name], str) or HEX64_RE.fullmatch(value[name]) is None
        for name in ("intent_sha256", "intent_id")
    ):
        raise _AuthorizationError("intent_binding_invalid")
    if (
        not isinstance(value["creator_address"], str)
        or not isinstance(value["creator_public_key"], str)
    ):
        raise _AuthorizationError("identity_invalid")
    if (
        not isinstance(value["signature"], str)
        or HEX128_RE.fullmatch(value["signature"]) is None
    ):
        raise _AuthorizationError("signature_invalid")
    if (
        not isinstance(value["authorization_id"], str)
        or HEX64_RE.fullmatch(value["authorization_id"]) is None
    ):
        raise _AuthorizationError("authorization_id_invalid")


def _signature_payload(value: dict[str, Any]) -> dict[str, Any]:
    return {name: value[name] for name in SIGNATURE_PAYLOAD_FIELDS}


def _verify_signature(value: dict[str, Any]) -> None:
    try:
        key_bytes = bytes.fromhex(FIXED_CREATOR_PUBLIC_KEY)
        signature_bytes = bytes.fromhex(value["signature"])
        if len(key_bytes) != 32 or len(signature_bytes) != 64:
            raise _AuthorizationError("signature_invalid")
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(
            signature_bytes, _canonical_bytes(_signature_payload(value))
        )
    except _AuthorizationError:
        raise
    except (InvalidSignature, TypeError, ValueError) as exc:
        raise _AuthorizationError("signature_invalid") from exc


def _authorization_id(value: dict[str, Any]) -> str:
    body = {name: value[name] for name in TOP_LEVEL_FIELDS if name != "authorization_id"}
    return hashlib.sha256(AUTHORIZATION_ID_DOMAIN + _canonical_bytes(body)).hexdigest()


def verify_creator_wallet_transfer_intent_authorization_json(
    payload: str | bytes,
    *,
    expected_control_bundle_sha256: str,
    expected_control_bundle_aggregate_commitment: str,
) -> CreatorWalletTransferIntentAuthorizationResult:
    try:
        _validate_expected_commitments(
            expected_control_bundle_sha256,
            expected_control_bundle_aggregate_commitment,
        )
        value = _parse(payload)
        _validate_schema(value)
        intent_result = verify_creator_wallet_transfer_intent_json(
            _intent_bytes(value["intent"]),
            expected_control_bundle_sha256=expected_control_bundle_sha256,
            expected_control_bundle_aggregate_commitment=(
                expected_control_bundle_aggregate_commitment
            ),
        )
        if not intent_result.ok:
            raise _AuthorizationError("intent_invalid")
        if (
            value["intent_sha256"] != intent_result.intent_sha256
            or value["intent_id"] != intent_result.intent_id
        ):
            raise _AuthorizationError("intent_binding_invalid")
        if (
            value["creator_address"] != FIXED_CREATOR_ADDRESS
            or value["creator_public_key"] != FIXED_CREATOR_PUBLIC_KEY
            or intent_result.creator_address != FIXED_CREATOR_ADDRESS
        ):
            raise _AuthorizationError("identity_invalid")
        _verify_signature(value)
        authorization_id = _authorization_id(value)
        if value["authorization_id"] != authorization_id:
            raise _AuthorizationError("authorization_id_invalid")
        return CreatorWalletTransferIntentAuthorizationResult(
            True, "ok", SUCCESS_CHECKS,
            hashlib.sha256(_canonical_bytes(value)).hexdigest(), authorization_id,
            intent_result.intent_sha256, intent_result.intent_id,
            intent_result.creator_address, intent_result.recipient_address,
            intent_result.amount, intent_result.expires_at_unix,
            intent_result.control_bundle_sha256,
            intent_result.control_bundle_aggregate_commitment,
        )
    except _AuthorizationError as exc:
        return CreatorWalletTransferIntentAuthorizationResult(False, exc.code)
    except Exception:
        return CreatorWalletTransferIntentAuthorizationResult(False, "internal_error")


class CreatorWalletTransferIntentAuthorizationVerifier:
    @classmethod
    def verify_json(
        cls,
        payload: str | bytes,
        *,
        expected_control_bundle_sha256: str,
        expected_control_bundle_aggregate_commitment: str,
    ) -> CreatorWalletTransferIntentAuthorizationResult:
        del cls
        return verify_creator_wallet_transfer_intent_authorization_json(
            payload,
            expected_control_bundle_sha256=expected_control_bundle_sha256,
            expected_control_bundle_aggregate_commitment=(
                expected_control_bundle_aggregate_commitment
            ),
        )
