"""Offline public creator-wallet control-proof verifier.

This module verifies a caller-supplied public challenge proof. It does not
load wallets, read private keys, sign data, transfer funds, touch ledgers, or
perform runtime/network activation.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover
    InvalidSignature = Exception  # type: ignore[assignment,misc]
    Ed25519PublicKey = None  # type: ignore[assignment,misc]


PROOF_VERSION = "l28-creator-wallet-control-proof/v0.1"
PROOF_DOMAIN = "l28-creator-wallet-control-proof/v0.1"
FIXED_CREATOR_PUBLIC_KEY = (
    "c03a4ffd7e94cba2199f6a95a94f13d5aa0c6090f0c3f06aa59f6afc8dd26ff5"
)
FIXED_CREATOR_ADDRESS = "L28d7d0903ab9e10e706c418c31fac95109577cdea6"
MAX_PROOF_BYTES = 4096

TOP_LEVEL_FIELDS = (
    "proof_version",
    "domain",
    "challenge_id",
    "public_key",
    "address",
    "signature",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX128_RE = re.compile(r"^[0-9a-f]{128}$")
ADDRESS_RE = re.compile(r"^L28[0-9a-f]{40}$")

SUCCESS_CHECKS = (
    "schema_exact",
    "version_exact",
    "domain_exact",
    "challenge_bound",
    "public_key_exact",
    "address_exact",
    "public_key_derives_address",
    "signature_valid",
)

STABLE_CODES = (
    "ok",
    "invalid_input_type",
    "proof_too_large",
    "invalid_json",
    "schema_invalid",
    "version_invalid",
    "domain_invalid",
    "challenge_invalid",
    "identity_invalid",
    "signature_invalid",
    "verification_backend_unavailable",
    "internal_error",
)


class _DuplicateKey(ValueError):
    pass


class _ProofError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CreatorWalletControlProofResult:
    ok: bool
    code: str
    checks: tuple[str, ...] = ()
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


def _decode(payload: str | bytes) -> bytes:
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        raw = bytes(payload)
    else:
        raise _ProofError("invalid_input_type")
    if len(raw) > MAX_PROOF_BYTES:
        raise _ProofError("proof_too_large")
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
        raise _ProofError("invalid_json") from None
    if not isinstance(value, dict):
        raise _ProofError("schema_invalid")
    return value


def _derive_address(public_key_hex: str) -> str:
    public_key_bytes = bytes.fromhex(public_key_hex)
    return "L28" + hashlib.sha256(public_key_bytes).hexdigest()[:40]


def _validate_schema(proof: dict[str, Any]) -> None:
    if tuple(proof.keys()) != TOP_LEVEL_FIELDS:
        raise _ProofError("schema_invalid")
    for field in TOP_LEVEL_FIELDS:
        if not isinstance(proof[field], str):
            raise _ProofError("schema_invalid")
    if proof["proof_version"] != PROOF_VERSION:
        raise _ProofError("version_invalid")
    if proof["domain"] != PROOF_DOMAIN:
        raise _ProofError("domain_invalid")
    if not HEX64_RE.fullmatch(proof["challenge_id"]):
        raise _ProofError("challenge_invalid")
    if not HEX64_RE.fullmatch(proof["public_key"]):
        raise _ProofError("identity_invalid")
    if not ADDRESS_RE.fullmatch(proof["address"]):
        raise _ProofError("identity_invalid")
    if not HEX128_RE.fullmatch(proof["signature"]):
        raise _ProofError("signature_invalid")


def _signature_preimage(proof: dict[str, Any]) -> bytes:
    unsigned = {
        "proof_version": proof["proof_version"],
        "domain": proof["domain"],
        "challenge_id": proof["challenge_id"],
        "public_key": proof["public_key"],
        "address": proof["address"],
    }
    return _canonical_bytes(unsigned)


def _verify_signature(proof: dict[str, Any]) -> None:
    if Ed25519PublicKey is None:
        raise _ProofError("verification_backend_unavailable")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(proof["public_key"]))
        public_key.verify(bytes.fromhex(proof["signature"]), _signature_preimage(proof))
    except InvalidSignature:
        raise _ProofError("signature_invalid") from None
    except _ProofError:
        raise
    except Exception:
        raise _ProofError("signature_invalid") from None


def _validate_identity(proof: dict[str, Any]) -> None:
    if proof["public_key"] != FIXED_CREATOR_PUBLIC_KEY:
        raise _ProofError("identity_invalid")
    if proof["address"] != FIXED_CREATOR_ADDRESS:
        raise _ProofError("identity_invalid")
    if _derive_address(proof["public_key"]) != proof["address"]:
        raise _ProofError("identity_invalid")


def verify_creator_wallet_control_proof_json(
    payload: str | bytes,
    *,
    expected_challenge_id: str,
) -> CreatorWalletControlProofResult:
    try:
        if not isinstance(expected_challenge_id, str) or not HEX64_RE.fullmatch(expected_challenge_id):
            return CreatorWalletControlProofResult(False, "challenge_invalid")
        proof = _parse(payload)
        _validate_schema(proof)
        if proof["challenge_id"] != expected_challenge_id:
            raise _ProofError("challenge_invalid")
        _validate_identity(proof)
        _verify_signature(proof)
        return CreatorWalletControlProofResult(
            True,
            "ok",
            SUCCESS_CHECKS,
            hashlib.sha256(_canonical_bytes(proof)).hexdigest(),
        )
    except _ProofError as exc:
        return CreatorWalletControlProofResult(False, exc.code)
    except Exception:
        return CreatorWalletControlProofResult(False, "internal_error")


class CreatorWalletControlProofVerifier:
    @classmethod
    def verify_json(
        cls,
        payload: str | bytes,
        *,
        expected_challenge_id: str,
    ) -> CreatorWalletControlProofResult:
        del cls
        return verify_creator_wallet_control_proof_json(
            payload,
            expected_challenge_id=expected_challenge_id,
        )
