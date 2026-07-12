# SPDX-License-Identifier: Apache-2.0
"""
L28 M2M Ed25519 envelope verifier (Foundation 5).

Verify-only. Does not generate keys, sign messages, store private material,
access wallets, or perform network or ledger writes.

Duplicate-key detection is guaranteed only at the raw-JSON boundary
(``verify_envelope_json``). A Python dict cannot retain evidence of duplicate
keys after ordinary parsing.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple, Union

from coin.tx_validation import RESERVED_SENDERS, compute_tx_id

# Cryptography imports are verify-only. Private-key types MUST NEVER be imported.
try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    _CRYPTO_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when dependency missing
    InvalidSignature = type("InvalidSignature", (Exception,), {})  # type: ignore[misc,assignment]
    Ed25519PublicKey = None  # type: ignore[assignment,misc]
    _CRYPTO_AVAILABLE = False

DOMAIN_PAYLOAD = b"L28-M2M-V0.1-PAYLOAD\x00"
DOMAIN_MESSAGE = b"L28-M2M-V0.1-MESSAGE\x00"
DOMAIN_SIGNATURE = b"L28-M2M-V0.1-SIGNATURE\x00"

SAFE_INT_MIN = -9007199254740991
SAFE_INT_MAX = 9007199254740991
PROP_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")

UNSIGNED_EXCLUDED = frozenset({"message_id", "signature"})

MESSAGE_TYPES = frozenset(
    {
        "service_request",
        "service_quote",
        "payment_authorization",
        "settlement_reference",
        "service_receipt",
        "failure_notice",
    }
)

REQUIRED_ENVELOPE_FIELDS = (
    "protocol",
    "protocol_version",
    "message_type",
    "message_id",
    "transaction_id",
    "created_at",
    "expires_at",
    "nonce",
    "previous_message_id",
    "payload_hash",
    "payload",
    "signature_suite",
    "signature",
)

# Codes that may be returned by the public API.
STABLE_CODES = frozenset(
    {
        "ok",
        "settlement_citation_valid",
        "invalid_json",
        "duplicate_key",
        "top_level_not_object",
        "missing_field",
        "unknown_message_type",
        "unknown_suite",
        "unsigned_envelope",
        "null_required_field",
        "invalid_field_type",
        "invalid_time_order",
        "float_rejected",
        "invalid_property_name",
        "integer_out_of_safe_range",
        "lone_surrogate",
        "padded_base64url",
        "malformed_base64url",
        "malformed_public_key_length",
        "malformed_signature_length",
        "mismatched_payload_hash",
        "mismatched_message_id",
        "identity_binding_mismatch",
        "reserved_identity",
        "verification_backend_unavailable",
        "bad_signature",
        "malformed_l28_transaction_id",
        "altered_settlement_material",
    }
)


class M2MVerifyError(Exception):
    """Internal fail-closed verification error carrying a stable public code."""

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in STABLE_CODES:
            code = "invalid_json"
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else f"{code}:{detail}")


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    code: str
    message_id: Optional[str] = None
    l28_transaction_id: Optional[str] = None


def _fail(
    code: str,
    *,
    message_id: Optional[str] = None,
    l28_transaction_id: Optional[str] = None,
) -> VerifyResult:
    if code not in STABLE_CODES:
        code = "invalid_json"
    return VerifyResult(
        ok=False,
        code=code,
        message_id=message_id,
        l28_transaction_id=l28_transaction_id,
    )


def _ok(
    *,
    code: str = "ok",
    message_id: Optional[str] = None,
    l28_transaction_id: Optional[str] = None,
) -> VerifyResult:
    return VerifyResult(
        ok=True,
        code=code,
        message_id=message_id,
        l28_transaction_id=l28_transaction_id,
    )


def _require_safe_int(value: Any) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise M2MVerifyError("invalid_field_type")
    if value < SAFE_INT_MIN or value > SAFE_INT_MAX:
        raise M2MVerifyError("integer_out_of_safe_range")
    return value


def _escape_string(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif o < 0x20:
            out.append(f"\\u{o:04x}")
        elif 0xD800 <= o <= 0xDFFF:
            raise M2MVerifyError("lone_surrogate")
        else:
            # solidus '/' is intentionally not escaped (L28-M2M profile)
            out.append(ch)
    out.append('"')
    return "".join(out)


def canonicalize(value: Any) -> str:
    """
    L28-M2M Canonical JSON v0.1 serializer.

    Restricted RFC 8785-compatible subset. Not a general-purpose RFC 8785 claim.
    """
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, bool):
        raise M2MVerifyError("invalid_field_type")
    if type(value) is int:
        _require_safe_int(value)
        return str(value)
    if isinstance(value, float):
        raise M2MVerifyError("float_rejected")
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, list):
        return "[" + ",".join(canonicalize(v) for v in value) + "]"
    if isinstance(value, dict):
        for k in value.keys():
            if not isinstance(k, str):
                raise M2MVerifyError("invalid_property_name")
            if not PROP_NAME_RE.match(k):
                raise M2MVerifyError("invalid_property_name")
        items = sorted(value.items(), key=lambda kv: kv[0])
        parts = [f"{_escape_string(k)}:{canonicalize(v)}" for k, v in items]
        return "{" + ",".join(parts) + "}"
    raise M2MVerifyError("invalid_field_type")


def canonical_bytes(value: Any) -> bytes:
    text = canonicalize(value)
    raw = text.encode("utf-8")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise M2MVerifyError("invalid_json")
    return raw


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def payload_hash_for(payload: Any) -> str:
    return sha256_hex(DOMAIN_PAYLOAD + canonical_bytes(payload))


def unsigned_envelope(envelope: Mapping[str, Any]) -> dict:
    return {k: v for k, v in envelope.items() if k not in UNSIGNED_EXCLUDED}


def message_id_for(envelope: Mapping[str, Any]) -> str:
    return sha256_hex(DOMAIN_MESSAGE + canonical_bytes(unsigned_envelope(envelope)))


def signature_preimage_for(envelope: Mapping[str, Any]) -> bytes:
    return DOMAIN_SIGNATURE + canonical_bytes(unsigned_envelope(envelope))


def encode_b64url_unpadded(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_b64url_unpadded(text: str) -> bytes:
    if not isinstance(text, str):
        raise M2MVerifyError("invalid_field_type")
    if "=" in text:
        raise M2MVerifyError("padded_base64url")
    if not text or not B64URL_RE.fullmatch(text):
        raise M2MVerifyError("malformed_base64url")
    if "+" in text or "/" in text:
        raise M2MVerifyError("malformed_base64url")
    pad = "=" * ((4 - (len(text) % 4)) % 4)
    try:
        raw = base64.urlsafe_b64decode(text + pad)
    except Exception as exc:
        raise M2MVerifyError("malformed_base64url") from exc
    # Reject noncanonical encodings by requiring exact re-encode match.
    if encode_b64url_unpadded(raw) != text:
        raise M2MVerifyError("malformed_base64url")
    return raw


def decode_public_key(text: str) -> bytes:
    raw = decode_b64url_unpadded(text)
    if len(raw) != 32:
        raise M2MVerifyError("malformed_public_key_length")
    return raw


def decode_signature(text: str) -> bytes:
    raw = decode_b64url_unpadded(text)
    if len(raw) != 64:
        raise M2MVerifyError("malformed_signature_length")
    return raw


def _reject_lone_surrogates_in_text(text: str) -> None:
    if re.search(r"\\u[dD][89aAbB][0-9a-fA-F]{2}(?!\\u[dD][cCdD][0-9a-fA-F]{2})", text):
        raise M2MVerifyError("lone_surrogate")
    if re.search(r"(?<!\\u[dD][89aAbB][0-9a-fA-F]{2})\\u[dD][cCdD][0-9a-fA-F]{2}", text):
        raise M2MVerifyError("lone_surrogate")


def _scan_value_for_surrogates(value: Any) -> None:
    if isinstance(value, str):
        for ch in value:
            o = ord(ch)
            if 0xD800 <= o <= 0xDFFF:
                raise M2MVerifyError("lone_surrogate")
    elif isinstance(value, list):
        for item in value:
            _scan_value_for_surrogates(item)
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str):
                _scan_value_for_surrogates(k)
            _scan_value_for_surrogates(v)


def _object_pairs_hook(pairs: Sequence[Tuple[str, Any]]) -> dict:
    out: dict = {}
    for key, value in pairs:
        if key in out:
            raise M2MVerifyError("duplicate_key")
        out[key] = value
    return out


def _parse_int_token(token: str) -> int:
    try:
        value = int(token, 10)
    except ValueError as exc:
        raise M2MVerifyError("invalid_json") from exc
    if value < SAFE_INT_MIN or value > SAFE_INT_MAX:
        raise M2MVerifyError("integer_out_of_safe_range")
    return value


def _parse_float_token(_token: str) -> Any:
    raise M2MVerifyError("float_rejected")


def _parse_constant(_token: str) -> Any:
    raise M2MVerifyError("float_rejected")


def parse_m2m_json_value(raw: Union[str, bytes]) -> Any:
    """
    Strict L28-M2M JSON document parser (any top-level JSON value).

    Guarantees duplicate-key detection. Python dicts cannot preserve that evidence
    after ordinary parsing.
    """
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise M2MVerifyError("invalid_json") from exc
    elif isinstance(raw, str):
        text = raw
    else:
        raise M2MVerifyError("invalid_json")

    if text.startswith("\ufeff"):
        raise M2MVerifyError("invalid_json")

    _reject_lone_surrogates_in_text(text)

    try:
        value = json.loads(
            text,
            parse_int=_parse_int_token,
            parse_float=_parse_float_token,
            parse_constant=_parse_constant,
            object_pairs_hook=_object_pairs_hook,
        )
    except M2MVerifyError:
        raise
    except json.JSONDecodeError as exc:
        raise M2MVerifyError("invalid_json") from exc
    except ValueError as exc:
        # Some json backends surface issues as ValueError.
        raise M2MVerifyError("invalid_json") from exc

    _scan_value_for_surrogates(value)
    return value


def parse_m2m_json(raw: Union[str, bytes]) -> dict:
    """
    Primary untrusted-input parser for a single M2M envelope object.

    Duplicate-key detection is guaranteed only at this raw-JSON boundary.
    """
    value = parse_m2m_json_value(raw)
    if not isinstance(value, dict):
        raise M2MVerifyError("top_level_not_object")
    return value


def _require_nonempty_str(envelope: Mapping[str, Any], field: str) -> str:
    if field not in envelope:
        raise M2MVerifyError("missing_field")
    value = envelope[field]
    if value is None:
        raise M2MVerifyError("null_required_field")
    if not isinstance(value, str):
        raise M2MVerifyError("invalid_field_type")
    if value == "":
        raise M2MVerifyError("invalid_field_type")
    return value


def _optional_nonempty_str(envelope: Mapping[str, Any], field: str) -> Optional[str]:
    if field not in envelope:
        return None
    value = envelope[field]
    if value is None:
        raise M2MVerifyError("null_required_field")
    if not isinstance(value, str):
        raise M2MVerifyError("invalid_field_type")
    if value == "":
        raise M2MVerifyError("invalid_field_type")
    return value


def _check_identity_string(value: str) -> None:
    if value in RESERVED_SENDERS:
        raise M2MVerifyError("reserved_identity")


def _validate_structure(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, Mapping):
        raise M2MVerifyError("top_level_not_object")

    # Canonicalization of the whole unsigned envelope enforces property-name rules
    # for every present key, including extras.
    for field in REQUIRED_ENVELOPE_FIELDS:
        if field not in envelope:
            # signature absence is a dedicated operational failure
            if field == "signature":
                raise M2MVerifyError("unsigned_envelope")
            raise M2MVerifyError("missing_field")

    protocol = _require_nonempty_str(envelope, "protocol")
    if protocol != "L28-M2M":
        raise M2MVerifyError("invalid_field_type")

    version = _require_nonempty_str(envelope, "protocol_version")
    if version != "0.1":
        raise M2MVerifyError("invalid_field_type")

    message_type = _require_nonempty_str(envelope, "message_type")
    if message_type not in MESSAGE_TYPES:
        raise M2MVerifyError("unknown_message_type")

    _require_nonempty_str(envelope, "transaction_id")
    _require_nonempty_str(envelope, "nonce")
    _require_nonempty_str(envelope, "message_id")
    _require_nonempty_str(envelope, "payload_hash")

    created_at = envelope["created_at"]
    expires_at = envelope["expires_at"]
    if created_at is None or expires_at is None:
        raise M2MVerifyError("null_required_field")
    if type(created_at) is not int or type(expires_at) is not int or isinstance(created_at, bool) or isinstance(
        expires_at, bool
    ):
        raise M2MVerifyError("invalid_field_type")
    _require_safe_int(created_at)
    _require_safe_int(expires_at)
    if expires_at <= created_at:
        raise M2MVerifyError("invalid_time_order")

    prev = envelope["previous_message_id"]
    if prev is not None:
        if not isinstance(prev, str) or prev == "":
            raise M2MVerifyError("invalid_field_type")
        if not HEX64_RE.fullmatch(prev):
            raise M2MVerifyError("invalid_field_type")

    payload = envelope["payload"]
    if payload is None:
        raise M2MVerifyError("null_required_field")
    if not isinstance(payload, dict):
        raise M2MVerifyError("invalid_field_type")

    suite = envelope["signature_suite"]
    if suite is None:
        raise M2MVerifyError("null_required_field")
    if not isinstance(suite, str):
        raise M2MVerifyError("invalid_field_type")
    if suite != "ed25519":
        raise M2MVerifyError("unknown_suite")

    signature = envelope["signature"]
    if signature is None:
        raise M2MVerifyError("unsigned_envelope")
    if not isinstance(signature, str):
        raise M2MVerifyError("invalid_field_type")
    if signature == "":
        raise M2MVerifyError("unsigned_envelope")

    sender_pk = _optional_nonempty_str(envelope, "sender_public_key")
    sender_id = _optional_nonempty_str(envelope, "sender_identity")
    recipient_pk = _optional_nonempty_str(envelope, "recipient_public_key")
    recipient_id = _optional_nonempty_str(envelope, "recipient_identity")

    if sender_pk is None and sender_id is None:
        raise M2MVerifyError("missing_field")
    if recipient_pk is None and recipient_id is None:
        raise M2MVerifyError("missing_field")

    # Operational Ed25519 verification requires the sender public key.
    if sender_pk is None:
        raise M2MVerifyError("missing_field")

    if sender_id is not None:
        _check_identity_string(sender_id)
    if recipient_id is not None:
        _check_identity_string(recipient_id)

    sender_key_id = _optional_nonempty_str(envelope, "sender_key_id")
    expected_kid = f"ed25519:{sender_pk}"
    if sender_key_id is None:
        raise M2MVerifyError("missing_field")
    if sender_key_id != expected_kid:
        raise M2MVerifyError("identity_binding_mismatch")

    message_id = envelope["message_id"]
    payload_hash = envelope["payload_hash"]
    if not HEX64_RE.fullmatch(message_id):
        raise M2MVerifyError("invalid_field_type")
    if not HEX64_RE.fullmatch(payload_hash):
        raise M2MVerifyError("invalid_field_type")


def verify_settlement_citation(payload: Mapping[str, Any]) -> VerifyResult:
    """
    Recompute Foundation 3 ``compute_tx_id`` for cited settlement material.

    Returns citation validity only. Never queries a network or ledger and never
    claims accepted, confirmed, irreversible, or final settlement.
    """
    try:
        if not isinstance(payload, Mapping):
            raise M2MVerifyError("invalid_field_type")
        if "l28_tx_id" not in payload:
            raise M2MVerifyError("missing_field")
        cited = payload["l28_tx_id"]
        if cited is None:
            raise M2MVerifyError("null_required_field")
        if not isinstance(cited, str):
            raise M2MVerifyError("invalid_field_type")
        if not HEX64_RE.fullmatch(cited):
            raise M2MVerifyError("malformed_l28_transaction_id")
        if "l28_transaction_material" not in payload:
            raise M2MVerifyError("missing_field")
        material = payload["l28_transaction_material"]
        if material is None:
            raise M2MVerifyError("null_required_field")
        if not isinstance(material, dict):
            raise M2MVerifyError("invalid_field_type")
        # Material participates in M2M canonicalization rules when present in envelopes.
        canonicalize(material)
        recomputed = compute_tx_id(dict(material))
        if recomputed != cited:
            raise M2MVerifyError("altered_settlement_material")
        return _ok(code="settlement_citation_valid", l28_transaction_id=cited)
    except M2MVerifyError as exc:
        return _fail(exc.code)


def verify_envelope(envelope: Mapping[str, Any]) -> VerifyResult:
    """
    Verify a parsed M2M envelope structurally and cryptographically.

    Duplicate-key detection is not available for already-parsed dicts; use
    ``verify_envelope_json`` for untrusted raw input.
    """
    message_id: Optional[str] = None
    l28_tx_id: Optional[str] = None
    try:
        if not isinstance(envelope, Mapping):
            raise M2MVerifyError("top_level_not_object")

        # Fast-path unsigned detection before broader required-field walk.
        if "signature" not in envelope or envelope.get("signature") in (None, ""):
            raise M2MVerifyError("unsigned_envelope")

        _validate_structure(envelope)
        message_id = envelope["message_id"]

        # Digests and identity encodings require full canonicalization of present fields.
        try:
            recomputed_payload_hash = payload_hash_for(envelope["payload"])
        except M2MVerifyError:
            raise
        if recomputed_payload_hash != envelope["payload_hash"]:
            raise M2MVerifyError("mismatched_payload_hash")

        recomputed_message_id = message_id_for(envelope)
        if recomputed_message_id != envelope["message_id"]:
            raise M2MVerifyError("mismatched_message_id")
        message_id = recomputed_message_id

        pk_bytes = decode_public_key(envelope["sender_public_key"])
        # Optional recipient key length/format check when present.
        if "recipient_public_key" in envelope and envelope["recipient_public_key"] is not None:
            decode_public_key(envelope["recipient_public_key"])

        sig_bytes = decode_signature(envelope["signature"])
        preimage = signature_preimage_for(envelope)

        if envelope.get("message_type") == "settlement_reference":
            citation = verify_settlement_citation(envelope["payload"])
            if not citation.ok:
                return _fail(citation.code, message_id=message_id)
            l28_tx_id = citation.l28_transaction_id

        if not _CRYPTO_AVAILABLE or Ed25519PublicKey is None:
            raise M2MVerifyError("verification_backend_unavailable")

        try:
            public_key = Ed25519PublicKey.from_public_bytes(pk_bytes)
            public_key.verify(sig_bytes, preimage)
        except InvalidSignature as exc:
            raise M2MVerifyError("bad_signature") from exc
        except (ValueError, TypeError) as exc:
            # Malformed points / backend input errors fail closed as bad_signature
            # once lengths and encodings have already been validated, or as length
            # errors if the backend disagrees with earlier checks.
            raise M2MVerifyError("bad_signature") from exc

        return _ok(message_id=message_id, l28_transaction_id=l28_tx_id)
    except M2MVerifyError as exc:
        return _fail(exc.code, message_id=message_id, l28_transaction_id=l28_tx_id)


def verify_envelope_json(raw: Union[str, bytes]) -> VerifyResult:
    """
    Primary untrusted-input boundary for M2M envelope verification.
    """
    try:
        envelope = parse_m2m_json(raw)
    except M2MVerifyError as exc:
        return _fail(exc.code)
    return verify_envelope(envelope)


__all__ = [
    "DOMAIN_MESSAGE",
    "DOMAIN_PAYLOAD",
    "DOMAIN_SIGNATURE",
    "M2MVerifyError",
    "SAFE_INT_MAX",
    "SAFE_INT_MIN",
    "STABLE_CODES",
    "VerifyResult",
    "canonical_bytes",
    "canonicalize",
    "decode_b64url_unpadded",
    "decode_public_key",
    "decode_signature",
    "encode_b64url_unpadded",
    "message_id_for",
    "parse_m2m_json",
    "parse_m2m_json_value",
    "payload_hash_for",
    "signature_preimage_for",
    "unsigned_envelope",
    "verify_envelope",
    "verify_envelope_json",
    "verify_settlement_citation",
]
