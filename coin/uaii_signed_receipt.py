# SPDX-License-Identifier: Apache-2.0
"""Foundation 66/67 — F64 signed-receipt data contract + isolated Ed25519 slice.

Foundation 66: pure schema validation and deterministic receipt-material
construction via CanonUaii (`coin.uaii_json.canon_uaii`).

Foundation 67: isolated PureEd25519 signing over `build_signable_bytes` and
public-key verification. Private keys MUST remain outside this module (callable
signer boundary). MUST NOT call M2M canonicalize helpers, UAII processing,
transaction validation, replay stores, ledgers, or network services.

Does not execute approval/replay state, spend, settle, submit transactions,
mutate ledgers, persist keys, or process UAII envelopes.
"""

from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Callable
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .uaii_json import UaiiJsonError, canon_uaii

# Milestone flags (remain false; no production/runtime/persistent replay authority)
execution_authorized = False
signing_authorized = False
spend_authorized = False
settlement_authorized = False
ledger_mutated = False
private_material_exposed = False
persistent_keys_created = False
persistent_replay_storage_created = False
replay_state_mutated = False
persistent_expiration_state_created = False
system_clock_read = False
implicit_time_used = False
acceptance_state_mutated = False
receipt_recorded = False
transaction_submission_authorized = False
adapters_activated = False
runtime_activated = False
transition_proposed_only = True
transition_applied = False
accepted_receipt_ids_mutated = False
persistent_state_created = False
boundary_evaluated_only = True
application_authorized = False
application_executed = False
state_mutated = False

# Bound for caller-supplied accepted receipt-id lists (Foundation 60 L3).
MAX_ACCEPTED_RECEIPT_IDS = 256

# Foundation 64 §9.1.12 / §10.5 — envelope-style skew from Foundation 57.
RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS = 300

# Foundation 56 JSON safe-integer upper bound (cited in Foundation 64 §8.5).
MAX_UNIX_SECONDS = 9_007_199_254_740_991

RECEIPT_PROFILE = "l28-uaii-signed-receipt/v0.1"
APPROVAL_PROFILE = "l28-f64-approval-decision/v0.1"
REPLAY_PROFILE = "l28-f64-signing-replay/v0.1"
SIGNER_ALGORITHM_PROFILE = "ed25519-pure/v0.1"
PURPOSE_SIGNED_RECEIPT = "signed_receipt"
ASSET_L28 = "L28"

SIGNABLE_DOMAIN_PREFIX = b"L28-UAII-SIGN-V0.1-RECEIPT\x00"
RECEIPT_ID_DOMAIN_PREFIX = b"L28-UAII-SIGN-V0.1-RECEIPT-ID"
REPLAY_KEY_DOMAIN_PREFIX = b"L28-F64-SIGNING-REPLAY-V0.1"

MAX_APPROVED_CANONICAL_PAYLOAD_BYTES = 16384
MAX_SIGNABLE_BYTES = 16512

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX128_RE = re.compile(r"^[0-9a-f]{128}$")

SETTLEMENT_STATUSES = frozenset(
    {
        "authorization_signed",
        "service_result_signed",
        "settlement_pending",
        "settlement_confirmed",
        "settlement_failed",
        "refunded",
    }
)

# Foundation 64 §5.6 — required signer identity field by settlement_status
STATUS_SIGNER_IDENTITY_FIELD: dict[str, str] = {
    "authorization_signed": "payer_public_identity",
    "service_result_signed": "provider_public_identity",
    "settlement_pending": "payer_public_identity",
    "settlement_confirmed": "payer_public_identity",
    "settlement_failed": "payer_public_identity",
    "refunded": "payer_public_identity",
}

UNSIGNED_FACTS_FIELDS = (
    "receipt_profile",
    "prior_receipt_id",
    "correlation_id",
    "request_id",
    "quote_id",
    "service_result_id",
    "payer_public_identity",
    "provider_public_identity",
    "asset_id",
    "amount",
    "purpose",
    "created_at",
    "expires_at",
    "receipt_nonce",
    "transaction_id",
    "settlement_status",
    "signer_algorithm_profile",
    "signer_public_key_id",
    "signer_public_key",
    "signing_authorized",
    "spend_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
)

SIGNED_FACTS_FIELDS = (
    "receipt_profile",
    "receipt_id",
    "prior_receipt_id",
    "correlation_id",
    "request_id",
    "quote_id",
    "service_result_id",
    "payer_public_identity",
    "provider_public_identity",
    "asset_id",
    "amount",
    "purpose",
    "created_at",
    "expires_at",
    "receipt_nonce",
    "transaction_id",
    "settlement_status",
    "signer_algorithm_profile",
    "signer_public_key_id",
    "signer_public_key",
    "signed_payload_digest",
    "signature",
    "signing_authorized",
    "spend_authorized",
    "settlement_authorized",
    "ledger_mutated",
    "execution_authorized",
)

APPROVAL_DECISION_FIELDS = (
    "approval_profile",
    "approval_id",
    "request_id",
    "correlation_id",
    "quote_id",
    "payer_identity",
    "provider_identity",
    "asset_id",
    "amount",
    "purpose",
    "nonce",
    "expires_at",
    "signable_digest",
    "signer_key_handle",
    "policy_id",
    "per_transaction_limit",
    "cumulative_limit_evaluation",
    "decision",
    "decided_at",
    "approver_identity",
    "approval_signature_reference",
)

CUMULATIVE_LIMIT_FIELDS = (
    "policy_id",
    "subject_identity",
    "asset_id",
    "window_start",
    "window_end",
    "prior_authorized_amount",
    "proposed_amount",
    "cumulative_maximum",
    "evaluation_timestamp",
    "evaluation_result",
)

REPLAY_MATERIAL_FIELDS = (
    "replay_profile",
    "signer_key_handle",
    "signature_purpose",
    "payer_identity",
    "provider_identity",
    "asset_id",
    "amount",
    "request_id",
    "quote_id",
    "correlation_id",
    "nonce",
    "expires_at",
    "signed_payload_digest",
)

assert len(UNSIGNED_FACTS_FIELDS) == 24
assert len(SIGNED_FACTS_FIELDS) == 27
assert len(APPROVAL_DECISION_FIELDS) == 21
assert len(REPLAY_MATERIAL_FIELDS) == 13
assert len(CUMULATIVE_LIMIT_FIELDS) == 10


class F64ReceiptSchemaError(Exception):
    """Fail-closed Foundation 64 schema/construction error with a stable code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _exact_int(value: Any, *, code: str = "schema_invalid") -> int:
    if type(value) is not int:
        raise F64ReceiptSchemaError(code)
    return value


def _utf8_len(value: str) -> int:
    return len(value.encode("utf-8"))


def _require_keys_order(
    obj: Any,
    fields: tuple[str, ...],
    *,
    code: str = "schema_invalid",
) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise F64ReceiptSchemaError(code)
    if tuple(obj.keys()) != fields:
        raise F64ReceiptSchemaError(code)
    return obj


def _check_hex64(value: Any, *, code: str = "schema_invalid") -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise F64ReceiptSchemaError(code)
    return value


def _check_hex128(value: Any, *, code: str = "schema_invalid") -> str:
    if not isinstance(value, str) or HEX128_RE.fullmatch(value) is None:
        raise F64ReceiptSchemaError(code)
    return value


def _check_identity_string(value: Any, *, code: str = "schema_invalid") -> str:
    if not isinstance(value, str):
        raise F64ReceiptSchemaError(code)
    n = _utf8_len(value)
    if n < 1 or n > 256:
        raise F64ReceiptSchemaError(code)
    return value


def _check_nonce_string(value: Any) -> str:
    if not isinstance(value, str):
        raise F64ReceiptSchemaError("nonce_invalid")
    raw = value.encode("utf-8")
    if len(raw) < 1 or len(raw) > 256 or "\0" in value:
        raise F64ReceiptSchemaError("nonce_invalid")
    return value


def _check_false_flag(value: Any, *, code: str = "schema_invalid") -> bool:
    if value is not False:
        raise F64ReceiptSchemaError(code)
    return False


def _check_prior_receipt_id(value: Any) -> Any:
    if value is None:
        return None
    return _check_hex64(value)


def _check_transaction_id(value: Any) -> str:
    if not isinstance(value, str):
        raise F64ReceiptSchemaError("schema_invalid")
    if value == "":
        return value
    return _check_hex64(value)


def _check_signer_public_key_id(value: Any, public_key_hex: str) -> str:
    if not isinstance(value, str) or not value.startswith("ed25519:"):
        raise F64ReceiptSchemaError("schema_invalid")
    b64 = value[len("ed25519:") :]
    if not b64 or "=" in b64:
        raise F64ReceiptSchemaError("schema_invalid")
    pad = "=" * ((4 - (len(b64) % 4)) % 4)
    try:
        raw = base64.urlsafe_b64decode(b64 + pad)
    except (ValueError, TypeError) as exc:
        raise F64ReceiptSchemaError("schema_invalid") from exc
    if len(raw) != 32:
        raise F64ReceiptSchemaError("schema_invalid")
    if raw.hex() != public_key_hex:
        raise F64ReceiptSchemaError("key_binding_invalid")
    return value


def _validate_receipt_common_body(obj: Mapping[str, Any]) -> None:
    if obj["receipt_profile"] != RECEIPT_PROFILE:
        raise F64ReceiptSchemaError("schema_invalid")
    _check_prior_receipt_id(obj["prior_receipt_id"])
    _check_hex64(obj["correlation_id"])
    _check_hex64(obj["request_id"])
    _check_hex64(obj["quote_id"])
    _check_hex64(obj["service_result_id"])
    _check_identity_string(obj["payer_public_identity"])
    _check_identity_string(obj["provider_public_identity"])
    if obj["asset_id"] != ASSET_L28:
        raise F64ReceiptSchemaError("asset_invalid")
    amount = _exact_int(obj["amount"], code="amount_invalid")
    if amount <= 0:
        raise F64ReceiptSchemaError("amount_invalid")
    if obj["purpose"] != PURPOSE_SIGNED_RECEIPT:
        raise F64ReceiptSchemaError("purpose_unsupported")
    created_at = _exact_int(obj["created_at"])
    if created_at < 0:
        raise F64ReceiptSchemaError("schema_invalid")
    expires_at = _exact_int(obj["expires_at"])
    if expires_at <= created_at:
        raise F64ReceiptSchemaError("schema_invalid")
    _check_nonce_string(obj["receipt_nonce"])
    _check_transaction_id(obj["transaction_id"])
    if not isinstance(obj["settlement_status"], str) or obj["settlement_status"] not in SETTLEMENT_STATUSES:
        raise F64ReceiptSchemaError("schema_invalid")
    if obj["signer_algorithm_profile"] != SIGNER_ALGORITHM_PROFILE:
        raise F64ReceiptSchemaError("algorithm_unsupported")
    public_key = _check_hex64(obj["signer_public_key"])
    _check_signer_public_key_id(obj["signer_public_key_id"], public_key)
    _check_false_flag(obj["signing_authorized"])
    _check_false_flag(obj["spend_authorized"])
    _check_false_flag(obj["settlement_authorized"])
    _check_false_flag(obj["ledger_mutated"])
    _check_false_flag(obj["execution_authorized"])


def validate_unsigned_facts(obj: Any) -> dict[str, Any]:
    """Validate exact 24-field UaiiSignedReceiptUnsignedFacts (F64 §6.2.1)."""
    ordered = _require_keys_order(obj, UNSIGNED_FACTS_FIELDS)
    _validate_receipt_common_body(ordered)
    return dict(ordered)


def validate_signed_facts(obj: Any) -> dict[str, Any]:
    """Validate exact 27-field UaiiSignedReceiptFacts (final form; F64 §6.2)."""
    ordered = _require_keys_order(obj, SIGNED_FACTS_FIELDS)
    _check_hex64(ordered["receipt_id"])
    _validate_receipt_common_body(ordered)
    _check_hex64(ordered["signed_payload_digest"])
    _check_hex128(ordered["signature"])
    return dict(ordered)


def validate_signed_facts_empty_receipt_id(obj: Any) -> dict[str, Any]:
    """Validate construction intermediate: §6.2 fields with receipt_id == \"\"."""
    ordered = _require_keys_order(obj, SIGNED_FACTS_FIELDS)
    if ordered["receipt_id"] != "":
        raise F64ReceiptSchemaError("schema_invalid")
    _validate_receipt_common_body(ordered)
    _check_hex64(ordered["signed_payload_digest"])
    _check_hex128(ordered["signature"])
    return dict(ordered)


def _validate_cumulative_limit_evaluation(
    obj: Any,
    *,
    policy_id: str,
    amount: int,
) -> dict[str, Any]:
    ordered = _require_keys_order(obj, CUMULATIVE_LIMIT_FIELDS)
    if ordered["policy_id"] != policy_id:
        raise F64ReceiptSchemaError("cumulative_limit_invalid")
    _check_identity_string(ordered["subject_identity"])
    if ordered["asset_id"] != ASSET_L28:
        raise F64ReceiptSchemaError("asset_invalid")
    window_start = _exact_int(ordered["window_start"])
    if window_start < 0:
        raise F64ReceiptSchemaError("cumulative_limit_invalid")
    window_end = _exact_int(ordered["window_end"])
    if window_end <= window_start:
        raise F64ReceiptSchemaError("cumulative_limit_invalid")
    prior = _exact_int(ordered["prior_authorized_amount"], code="amount_invalid")
    if prior < 0:
        raise F64ReceiptSchemaError("amount_invalid")
    proposed = _exact_int(ordered["proposed_amount"], code="amount_invalid")
    if proposed < 0:
        raise F64ReceiptSchemaError("amount_invalid")
    if proposed != amount:
        raise F64ReceiptSchemaError("cumulative_limit_invalid")
    cumulative_maximum = _exact_int(ordered["cumulative_maximum"], code="amount_invalid")
    if cumulative_maximum < 0:
        raise F64ReceiptSchemaError("amount_invalid")
    _exact_int(ordered["evaluation_timestamp"])
    if ordered["evaluation_result"] not in ("pass", "fail"):
        raise F64ReceiptSchemaError("cumulative_limit_invalid")
    return dict(ordered)


def validate_approval_decision(obj: Any) -> dict[str, Any]:
    """Validate exact 21-field ApprovalDecision including nested §8.5 object."""
    ordered = _require_keys_order(obj, APPROVAL_DECISION_FIELDS)
    if ordered["approval_profile"] != APPROVAL_PROFILE:
        raise F64ReceiptSchemaError("schema_invalid")
    _check_hex64(ordered["approval_id"])
    _check_hex64(ordered["request_id"])
    _check_hex64(ordered["correlation_id"])
    _check_hex64(ordered["quote_id"])
    _check_identity_string(ordered["payer_identity"])
    _check_identity_string(ordered["provider_identity"])
    if ordered["asset_id"] != ASSET_L28:
        raise F64ReceiptSchemaError("asset_invalid")
    amount = _exact_int(ordered["amount"], code="amount_invalid")
    if amount < 0:
        raise F64ReceiptSchemaError("amount_invalid")
    if ordered["purpose"] != PURPOSE_SIGNED_RECEIPT:
        raise F64ReceiptSchemaError("purpose_unsupported")
    _check_nonce_string(ordered["nonce"])
    _exact_int(ordered["expires_at"])
    _check_hex64(ordered["signable_digest"])
    _check_identity_string(ordered["signer_key_handle"])
    policy_id = _check_identity_string(ordered["policy_id"])
    per_tx = _exact_int(ordered["per_transaction_limit"], code="amount_invalid")
    if per_tx < 0:
        raise F64ReceiptSchemaError("amount_invalid")
    cle = _validate_cumulative_limit_evaluation(
        ordered["cumulative_limit_evaluation"],
        policy_id=policy_id,
        amount=amount,
    )
    if ordered["decision"] not in ("approved", "rejected"):
        raise F64ReceiptSchemaError("schema_invalid")
    _exact_int(ordered["decided_at"])
    _check_identity_string(ordered["approver_identity"])
    if ordered["approval_signature_reference"] is not None:
        raise F64ReceiptSchemaError("schema_invalid")
    out = dict(ordered)
    out["cumulative_limit_evaluation"] = cle
    return out


def validate_replay_key_material(obj: Any) -> dict[str, Any]:
    """Validate exact 13-field F64SigningReplayKeyMaterial (F64 §10.1)."""
    ordered = _require_keys_order(obj, REPLAY_MATERIAL_FIELDS)
    if ordered["replay_profile"] != REPLAY_PROFILE:
        raise F64ReceiptSchemaError("schema_invalid")
    _check_identity_string(ordered["signer_key_handle"])
    if ordered["signature_purpose"] != PURPOSE_SIGNED_RECEIPT:
        raise F64ReceiptSchemaError("purpose_unsupported")
    _check_identity_string(ordered["payer_identity"])
    _check_identity_string(ordered["provider_identity"])
    if ordered["asset_id"] != ASSET_L28:
        raise F64ReceiptSchemaError("asset_invalid")
    amount = _exact_int(ordered["amount"], code="amount_invalid")
    if amount < 0:
        raise F64ReceiptSchemaError("amount_invalid")
    _check_hex64(ordered["request_id"])
    _check_hex64(ordered["quote_id"])
    _check_hex64(ordered["correlation_id"])
    _check_nonce_string(ordered["nonce"])
    _exact_int(ordered["expires_at"])
    _check_hex64(ordered["signed_payload_digest"])
    return dict(ordered)


def _canon(obj: Mapping[str, Any]) -> bytes:
    try:
        return canon_uaii(dict(obj))
    except UaiiJsonError as exc:
        raise F64ReceiptSchemaError(exc.code) from exc


def approved_canonical_payload(unsigned_facts: Any) -> bytes:
    """CanonUaii(UaiiSignedReceiptUnsignedFacts); size-bounded."""
    validated = validate_unsigned_facts(unsigned_facts)
    payload = _canon(validated)
    if len(payload) > MAX_APPROVED_CANONICAL_PAYLOAD_BYTES:
        raise F64ReceiptSchemaError("input_too_large")
    return payload


def build_signable_bytes(unsigned_facts: Any) -> bytes:
    """Domain-separated signable bytes (hash/construction only; no signing)."""
    payload = approved_canonical_payload(unsigned_facts)
    out = SIGNABLE_DOMAIN_PREFIX + payload
    if len(out) > MAX_SIGNABLE_BYTES:
        raise F64ReceiptSchemaError("input_too_large")
    return out


def compute_signed_payload_digest(unsigned_facts: Any) -> str:
    """lowercase_hex(SHA-256(signable_bytes)); excludes digest/signature/receipt_id."""
    return hashlib.sha256(build_signable_bytes(unsigned_facts)).hexdigest()


def unsigned_facts_from_signed(signed_facts: Any) -> dict[str, Any]:
    """Extract §6.2.1 unsigned facts from a complete signed-facts object."""
    signed = validate_signed_facts(signed_facts)
    extracted = {k: signed[k] for k in UNSIGNED_FACTS_FIELDS}
    return validate_unsigned_facts(extracted)


def compute_receipt_id(signed_facts_empty_id: Any) -> str:
    """Compute receipt_id from §6.2.4 empty-id intermediate (no signing)."""
    validated = validate_signed_facts_empty_receipt_id(signed_facts_empty_id)
    material = RECEIPT_ID_DOMAIN_PREFIX + _canon(validated)
    return hashlib.sha256(material).hexdigest()


def compute_replay_key(replay_material: Any) -> str:
    """Compute F64 replay_key digest material only (no store / no replay check)."""
    validated = validate_replay_key_material(replay_material)
    material = REPLAY_KEY_DOMAIN_PREFIX + _canon(validated)
    return hashlib.sha256(material).hexdigest()


def build_signed_facts_empty_id(
    *,
    unsigned_facts: Any,
    signed_payload_digest: str,
    signature: str,
) -> dict[str, Any]:
    """Assemble construction step-8 object (receipt_id temporary empty string)."""
    unsigned = validate_unsigned_facts(unsigned_facts)
    digest = _check_hex64(signed_payload_digest)
    sig = _check_hex128(signature)
    ordered: dict[str, Any] = {
        "receipt_profile": unsigned["receipt_profile"],
        "receipt_id": "",
        "prior_receipt_id": unsigned["prior_receipt_id"],
        "correlation_id": unsigned["correlation_id"],
        "request_id": unsigned["request_id"],
        "quote_id": unsigned["quote_id"],
        "service_result_id": unsigned["service_result_id"],
        "payer_public_identity": unsigned["payer_public_identity"],
        "provider_public_identity": unsigned["provider_public_identity"],
        "asset_id": unsigned["asset_id"],
        "amount": unsigned["amount"],
        "purpose": unsigned["purpose"],
        "created_at": unsigned["created_at"],
        "expires_at": unsigned["expires_at"],
        "receipt_nonce": unsigned["receipt_nonce"],
        "transaction_id": unsigned["transaction_id"],
        "settlement_status": unsigned["settlement_status"],
        "signer_algorithm_profile": unsigned["signer_algorithm_profile"],
        "signer_public_key_id": unsigned["signer_public_key_id"],
        "signer_public_key": unsigned["signer_public_key"],
        "signed_payload_digest": digest,
        "signature": sig,
        "signing_authorized": unsigned["signing_authorized"],
        "spend_authorized": unsigned["spend_authorized"],
        "settlement_authorized": unsigned["settlement_authorized"],
        "ledger_mutated": unsigned["ledger_mutated"],
        "execution_authorized": unsigned["execution_authorized"],
    }
    return validate_signed_facts_empty_receipt_id(ordered)


def required_signer_identity_field(settlement_status: str) -> str:
    """Return the Foundation 64 §5.6 identity field name for a status."""
    try:
        return STATUS_SIGNER_IDENTITY_FIELD[settlement_status]
    except KeyError as exc:
        raise F64ReceiptSchemaError("schema_invalid") from exc


def required_signer_identity(unsigned_or_signed_facts: Mapping[str, Any]) -> str:
    """Return the identity string that MUST own the signer key for these facts."""
    status = unsigned_or_signed_facts["settlement_status"]
    field = required_signer_identity_field(status)
    value = unsigned_or_signed_facts[field]
    if not isinstance(value, str) or value == "":
        raise F64ReceiptSchemaError("key_binding_invalid")
    return value


def public_key_id_for_raw(public_key_raw: bytes) -> str:
    """Encode `ed25519:` + base64url-unpadded raw public key (F64 §5.2)."""
    if len(public_key_raw) != 32:
        raise F64ReceiptSchemaError("schema_invalid")
    return "ed25519:" + base64.urlsafe_b64encode(public_key_raw).decode("ascii").rstrip("=")


def _verify_ed25519(*, public_key_hex: str, signature_hex: str, message: bytes) -> None:
    try:
        pk_bytes = bytes.fromhex(public_key_hex)
        sig_bytes = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise F64ReceiptSchemaError("signature_invalid") from exc
    if len(pk_bytes) != 32 or len(sig_bytes) != 64:
        raise F64ReceiptSchemaError("signature_invalid")
    try:
        Ed25519PublicKey.from_public_bytes(pk_bytes).verify(sig_bytes, message)
    except (InvalidSignature, ValueError) as exc:
        raise F64ReceiptSchemaError("signature_invalid") from exc


def sign_unsigned_receipt_facts(
    unsigned_facts: Any,
    *,
    sign_signable_bytes: Callable[[bytes], bytes],
    expected_signer_identity: str,
) -> dict[str, Any]:
    """Sign exact `build_signable_bytes` output; return complete 27-field facts.

    ``sign_signable_bytes`` is the isolated signer boundary: it MUST accept the
    domain-separated signable bytes and return raw 64-byte PureEd25519 signature
    bytes. This module never accepts, stores, logs, or serializes private keys.
    """
    if not callable(sign_signable_bytes):
        raise F64ReceiptSchemaError("schema_invalid")
    if not isinstance(expected_signer_identity, str) or expected_signer_identity == "":
        raise F64ReceiptSchemaError("key_binding_invalid")

    unsigned = validate_unsigned_facts(unsigned_facts)
    if unsigned["signer_algorithm_profile"] != SIGNER_ALGORITHM_PROFILE:
        raise F64ReceiptSchemaError("algorithm_unsupported")

    bound_identity = required_signer_identity(unsigned)
    if expected_signer_identity != bound_identity:
        raise F64ReceiptSchemaError("key_binding_invalid")

    signable = build_signable_bytes(unsigned)
    digest = hashlib.sha256(signable).hexdigest()

    try:
        signature_raw = sign_signable_bytes(signable)
    except F64ReceiptSchemaError:
        raise
    except Exception as exc:  # noqa: BLE001 — fail closed at signer boundary
        raise F64ReceiptSchemaError("signature_invalid") from exc

    if not isinstance(signature_raw, (bytes, bytearray)) or len(signature_raw) != 64:
        raise F64ReceiptSchemaError("signature_invalid")
    signature_hex = bytes(signature_raw).hex()

    # Ensure the isolated signer matched the declared public key (no private material).
    _verify_ed25519(
        public_key_hex=unsigned["signer_public_key"],
        signature_hex=signature_hex,
        message=signable,
    )

    empty = build_signed_facts_empty_id(
        unsigned_facts=unsigned,
        signed_payload_digest=digest,
        signature=signature_hex,
    )
    receipt_id = compute_receipt_id(empty)
    complete = dict(empty)
    complete["receipt_id"] = receipt_id
    return validate_signed_facts(complete)


def verify_signed_receipt_facts(signed_facts: Any) -> dict[str, Any]:
    """Verify schema, §5.6 identity binding, digest, PureEd25519 signature, receipt_id.

    Reconstructs signable bytes only through Foundation 66 helpers. Does not call
    M2M canonicalization, UAII processing, validate_transaction, replay stores,
    ledger, or network code.
    """
    signed = validate_signed_facts(signed_facts)

    if signed["signer_algorithm_profile"] != SIGNER_ALGORITHM_PROFILE:
        raise F64ReceiptSchemaError("algorithm_unsupported")

    # §5.6 — required identity field must be present and selected deterministically.
    required_signer_identity(signed)

    unsigned = {k: signed[k] for k in UNSIGNED_FACTS_FIELDS}
    unsigned = validate_unsigned_facts(unsigned)

    signable = build_signable_bytes(unsigned)
    recomputed_digest = hashlib.sha256(signable).hexdigest()
    if recomputed_digest != signed["signed_payload_digest"]:
        raise F64ReceiptSchemaError("digest_mismatch")

    _verify_ed25519(
        public_key_hex=signed["signer_public_key"],
        signature_hex=signed["signature"],
        message=signable,
    )

    empty = dict(signed)
    empty["receipt_id"] = ""
    recomputed_id = compute_receipt_id(empty)
    if recomputed_id != signed["receipt_id"]:
        raise F64ReceiptSchemaError("receipt_id_invalid")

    return signed


def validate_accepted_receipt_ids(accepted_receipt_ids: Any) -> tuple[str, ...]:
    """Validate caller-supplied previously-accepted receipt_id collection.

    Pure and side-effect free: does not mutate the input, retain state, touch a
    store, or consult time/network/environment. Duplicates are ambiguous and
    rejected. Length MUST be ``<= MAX_ACCEPTED_RECEIPT_IDS`` (F60-L3).
    """
    if not isinstance(accepted_receipt_ids, list):
        raise F64ReceiptSchemaError("schema_invalid")
    if len(accepted_receipt_ids) > MAX_ACCEPTED_RECEIPT_IDS:
        raise F64ReceiptSchemaError("input_too_large")
    out: list[str] = []
    seen: set[str] = set()
    for item in accepted_receipt_ids:
        if item is None:
            raise F64ReceiptSchemaError("schema_invalid")
        rid = _check_hex64(item)
        if rid in seen:
            raise F64ReceiptSchemaError("schema_invalid")
        seen.add(rid)
        out.append(rid)
    return tuple(out)


def classify_signed_receipt_replay(
    signed_facts: Any,
    accepted_receipt_ids: Any,
) -> dict[str, Any]:
    """Verify signed facts (F67), then classify receipt_id membership.

    Normative identifier for this pure slice: Foundation 64 ``receipt_id``
    (§6.2 / §6.2.4). Classification runs only after cryptographic and integrity
    verification succeeds. Does not mutate ``accepted_receipt_ids``, create
    storage, or evaluate time-scoped ``replay_key`` uniqueness (F64 §10.3
    remains an external-authority obligation).

    Returns public facts including ``replay_status`` of ``fresh`` or ``replayed``.
    """
    verified = verify_signed_receipt_facts(signed_facts)
    accepted = validate_accepted_receipt_ids(accepted_receipt_ids)
    receipt_id = verified["receipt_id"]
    replay_status = "replayed" if receipt_id in accepted else "fresh"
    return {
        "verification_status": "verified",
        "replay_status": replay_status,
        "receipt_id": receipt_id,
        "signed_payload_digest": verified["signed_payload_digest"],
        "verified_facts": verified,
    }


def validate_verification_time(verification_time: Any) -> int:
    """Validate caller-supplied Unix-seconds verification time (exact int).

    Representation: timezone-independent integer Unix seconds (Foundation 56/57
    / 64). No system clock, timezone config, or environment is consulted.
    """
    if type(verification_time) is not int:
        raise F64ReceiptSchemaError("schema_invalid")
    if verification_time < 0 or verification_time > MAX_UNIX_SECONDS:
        raise F64ReceiptSchemaError("schema_invalid")
    return verification_time


def expiration_status_for_verified_facts(
    verified_facts: Mapping[str, Any],
    verification_time: Any,
) -> str:
    """Classify expiration from already-verified facts and explicit time.

    Foundation 64 §9.1.12 / §10.5 envelope-style rule (Foundation 57):

        expired  iff  verification_time > expires_at + 300
        valid    otherwise

    Therefore ``verification_time == expires_at`` is **valid** (not expired).
    Does not mutate inputs or read any clock.
    """
    if not isinstance(verified_facts, Mapping):
        raise F64ReceiptSchemaError("schema_invalid")
    expires_at = verified_facts.get("expires_at")
    if type(expires_at) is not int:
        raise F64ReceiptSchemaError("schema_invalid")
    t = validate_verification_time(verification_time)
    if t > expires_at + RECEIPT_EXPIRY_CLOCK_SKEW_SECONDS:
        return "expired"
    return "valid"


def classify_signed_receipt_expiration(
    signed_facts: Any,
    verification_time: Any,
) -> dict[str, Any]:
    """Verify signed facts (F67), then classify expiration vs explicit time."""
    verified = verify_signed_receipt_facts(signed_facts)
    expiration_status = expiration_status_for_verified_facts(verified, verification_time)
    return {
        "verification_status": "verified",
        "expiration_status": expiration_status,
        "receipt_id": verified["receipt_id"],
        "expires_at": verified["expires_at"],
        "verification_time": validate_verification_time(verification_time),
        "verified_facts": verified,
    }


def classify_signed_receipt_replay_and_expiration(
    signed_facts: Any,
    accepted_receipt_ids: Any,
    verification_time: Any,
) -> dict[str, Any]:
    """Verify once, then classify replay and expiration in that order."""
    verified = verify_signed_receipt_facts(signed_facts)
    accepted = validate_accepted_receipt_ids(accepted_receipt_ids)
    t = validate_verification_time(verification_time)
    receipt_id = verified["receipt_id"]
    replay_status = "replayed" if receipt_id in accepted else "fresh"
    expiration_status = expiration_status_for_verified_facts(verified, t)
    return {
        "verification_status": "verified",
        "replay_status": replay_status,
        "expiration_status": expiration_status,
        "receipt_id": receipt_id,
        "signed_payload_digest": verified["signed_payload_digest"],
        "expires_at": verified["expires_at"],
        "verification_time": t,
        "verified_facts": verified,
    }


def acceptance_decision_from_classifications(
    *,
    replay_status: str,
    expiration_status: str,
) -> tuple[str, str]:
    """Map replay/expiration classifications to acceptance decision + reason.

    Precedence when both reject conditions apply: replay before expiration.
    Returns ``(acceptance_decision, rejection_reason)`` where ``rejection_reason``
    is ``""`` when accepted.
    """
    if replay_status not in ("fresh", "replayed"):
        raise F64ReceiptSchemaError("schema_invalid")
    if expiration_status not in ("valid", "expired"):
        raise F64ReceiptSchemaError("schema_invalid")
    if replay_status == "replayed":
        return "rejected", "replayed"
    if expiration_status == "expired":
        return "rejected", "expired"
    return "accepted", ""


def decide_signed_receipt_acceptance(
    signed_facts: Any,
    accepted_receipt_ids: Any,
    verification_time: Any,
) -> dict[str, Any]:
    """Compose F67/F69/F70 outcomes into one informational acceptance decision.

    Order: cryptographic verify → replay → expiration → acceptance.
    Schema/crypto failures raise ``F64ReceiptSchemaError`` and emit no acceptance
    fields. Acceptance never records receipts, mutates context, or authorizes
    spend/settlement/submission.
    """
    classified = classify_signed_receipt_replay_and_expiration(
        signed_facts,
        accepted_receipt_ids,
        verification_time,
    )
    decision, reason = acceptance_decision_from_classifications(
        replay_status=classified["replay_status"],
        expiration_status=classified["expiration_status"],
    )
    out = dict(classified)
    out["acceptance_decision"] = decision
    out["rejection_reason"] = reason
    return out


ACCEPTANCE_TRANSITION_PROPOSAL_FIELDS = (
    "proposal_status",
    "transition_kind",
    "receipt_id",
    "expected_prior_replay_status",
    "proposed_resulting_replay_status",
    "precondition",
    "proposed_effect",
    "transition_applied",
    "transition_proposed_only",
)


def acceptance_transition_proposal_from_decision(
    decided: Mapping[str, Any],
) -> dict[str, Any]:
    """Map a Foundation 71 decision to an inert acceptance-state transition proposal.

    Applicable only when ``acceptance_decision == "accepted"``. Uses Foundation 69
    replay vocabulary (``fresh`` / ``replayed``) for prior/resulting status. Never
    mutates caller context; ``transition_applied`` is always ``False``.
    """
    receipt_id = decided["receipt_id"]
    if not isinstance(receipt_id, str):
        raise F64ReceiptSchemaError("schema_invalid")
    if decided.get("acceptance_decision") == "accepted":
        if decided.get("replay_status") != "fresh":
            raise F64ReceiptSchemaError("schema_invalid")
        if decided.get("expiration_status") != "valid":
            raise F64ReceiptSchemaError("schema_invalid")
        proposal = {
            "proposal_status": "applicable",
            "transition_kind": "add_accepted_receipt_id",
            "receipt_id": receipt_id,
            "expected_prior_replay_status": "fresh",
            "proposed_resulting_replay_status": "replayed",
            "precondition": "receipt_id_absent_from_accepted_receipt_ids",
            "proposed_effect": "add_receipt_id_to_accepted_receipt_ids",
            "transition_applied": False,
            "transition_proposed_only": True,
        }
    else:
        proposal = {
            "proposal_status": "not_applicable",
            "transition_kind": "",
            "receipt_id": receipt_id,
            "expected_prior_replay_status": "",
            "proposed_resulting_replay_status": "",
            "precondition": "",
            "proposed_effect": "",
            "transition_applied": False,
            "transition_proposed_only": True,
        }
    if tuple(proposal.keys()) != ACCEPTANCE_TRANSITION_PROPOSAL_FIELDS:
        raise F64ReceiptSchemaError("schema_invalid")
    return proposal


def propose_signed_receipt_acceptance_transition(
    signed_facts: Any,
    accepted_receipt_ids: Any,
    verification_time: Any,
) -> dict[str, Any]:
    """Compose F71 acceptance into a pure, inert transition proposal.

    Order: verify → replay → expiration → acceptance → proposal.
    Does not insert into ``accepted_receipt_ids``, persist state, or claim
    that acceptance was recorded.
    """
    decided = decide_signed_receipt_acceptance(
        signed_facts,
        accepted_receipt_ids,
        verification_time,
    )
    proposal = acceptance_transition_proposal_from_decision(decided)
    out = dict(decided)
    out["acceptance_transition_proposal"] = proposal
    return out


APPLICATION_BOUNDARY_RESULT_FIELDS = (
    "application_boundary_status",
    "application_boundary_reason",
    "receipt_id",
    "transition_kind",
    "application_authorized",
    "application_executed",
    "state_mutated",
    "persistent_state_created",
)


def _hex64_receipt_id_or_empty(value: Any) -> str:
    if not isinstance(value, str) or value == "":
        return ""
    try:
        return _check_hex64(value)
    except F64ReceiptSchemaError:
        return ""


def application_boundary_from_proposed_acceptance(
    proposed: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate structural eligibility of a Foundation 72 proposal for a future authority.

    Eligibility is not authorization and not execution. Always returns
    ``application_authorized=false`` and ``application_executed=false``.
    """
    if not isinstance(proposed, Mapping):
        raise F64ReceiptSchemaError("schema_invalid")
    decision = proposed.get("acceptance_decision")
    rejection_reason = proposed.get("rejection_reason")
    proposal = proposed.get("acceptance_transition_proposal")
    if not isinstance(proposal, Mapping):
        raise F64ReceiptSchemaError("schema_invalid")
    if tuple(proposal.keys()) != ACCEPTANCE_TRANSITION_PROPOSAL_FIELDS:
        raise F64ReceiptSchemaError("schema_invalid")

    receipt_id = _hex64_receipt_id_or_empty(proposal.get("receipt_id"))
    inert_ok = (
        proposal.get("transition_applied") is False
        and proposal.get("transition_proposed_only") is True
    )
    eligible = (
        decision == "accepted"
        and rejection_reason == ""
        and proposal.get("proposal_status") == "applicable"
        and proposal.get("transition_kind") == "add_accepted_receipt_id"
        and receipt_id != ""
        and proposal.get("expected_prior_replay_status") == "fresh"
        and proposal.get("proposed_resulting_replay_status") == "replayed"
        and proposal.get("precondition") == "receipt_id_absent_from_accepted_receipt_ids"
        and proposal.get("proposed_effect") == "add_receipt_id_to_accepted_receipt_ids"
        and inert_ok
        and proposed.get("replay_status") == "fresh"
        and proposed.get("expiration_status") == "valid"
    )

    if eligible:
        boundary = {
            "application_boundary_status": "eligible",
            "application_boundary_reason": "",
            "receipt_id": receipt_id,
            "transition_kind": "add_accepted_receipt_id",
            "application_authorized": False,
            "application_executed": False,
            "state_mutated": False,
            "persistent_state_created": False,
        }
    else:
        if decision == "rejected" and rejection_reason in ("replayed", "expired"):
            reason = rejection_reason
        elif proposal.get("proposal_status") == "not_applicable":
            reason = "proposal_not_applicable"
        else:
            reason = "proposal_inconsistent"
        boundary = {
            "application_boundary_status": "ineligible",
            "application_boundary_reason": reason,
            "receipt_id": receipt_id,
            "transition_kind": "",
            "application_authorized": False,
            "application_executed": False,
            "state_mutated": False,
            "persistent_state_created": False,
        }
    if tuple(boundary.keys()) != APPLICATION_BOUNDARY_RESULT_FIELDS:
        raise F64ReceiptSchemaError("schema_invalid")
    return boundary


def evaluate_signed_receipt_acceptance_transition_application_boundary(
    signed_facts: Any,
    accepted_receipt_ids: Any,
    verification_time: Any,
) -> dict[str, Any]:
    """Compose F72 proposal into a pure, non-executing application boundary result.

    Order: verify → replay → expiration → acceptance → proposal → boundary.
    Never authorizes or executes application; never mutates accepted IDs.
    """
    proposed = propose_signed_receipt_acceptance_transition(
        signed_facts,
        accepted_receipt_ids,
        verification_time,
    )
    boundary = application_boundary_from_proposed_acceptance(proposed)
    out = dict(proposed)
    out["acceptance_transition_application_boundary"] = boundary
    return out
