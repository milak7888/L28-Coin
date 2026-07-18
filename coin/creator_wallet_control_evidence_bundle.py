"""Bounded offline creator-wallet control evidence-bundle verifier."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from .creator_wallet_control_proof_evidence import (
    verify_creator_wallet_control_proof_evidence_json,
)

BUNDLE_VERSION = "l28-creator-wallet-control-evidence-bundle/v0.1"
VERIFIER_VERSION = "l28-creator-wallet-control-evidence-bundle-verifier/v0.1"
BUNDLE_REPORT_VERSION = "l28-creator-wallet-control-evidence-bundle-report/v0.1"
BUNDLE_DOMAIN = BUNDLE_VERSION.encode("utf-8") + b"\x00"
MAX_BUNDLE_BYTES = 270336
MIN_MEMBERS = 1
MAX_MEMBERS = 32
TOP_LEVEL_FIELDS = ("bundle_version", "members")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

STABLE_CODES = (
    "ok",
    "invalid_input_type",
    "bundle_too_large",
    "invalid_encoding",
    "invalid_json",
    "duplicate_key",
    "invalid_top_level",
    "invalid_bundle_version",
    "invalid_members",
    "member_count_invalid",
    "member_invalid",
    "duplicate_member",
    "duplicate_challenge",
    "noncanonical_member_order",
    "internal_error",
)

SUCCESS_CHECKS = (
    "bundle_version_valid",
    "member_count_valid",
    "all_members_valid",
    "member_commitments_unique",
    "challenge_ids_unique",
    "member_order_canonical",
    "aggregate_commitment_valid",
)


class _DuplicateKey(ValueError):
    pass


class _BundleError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CreatorWalletControlEvidenceBundleResult:
    ok: bool
    code: str
    checks: tuple[str, ...] = ()
    bundle_sha256: str = ""
    aggregate_commitment: str = ""
    member_evidence_sha256: tuple[str, ...] = ()


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(value)


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
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_BUNDLE_BYTES:
            raise _BundleError("bundle_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _BundleError("invalid_encoding") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _BundleError("invalid_encoding") from exc
        if len(encoded) > MAX_BUNDLE_BYTES:
            raise _BundleError("bundle_too_large")
        return payload
    raise _BundleError("invalid_input_type")


def _parse(payload: str | bytes) -> dict[str, Any]:
    text = _decode(payload)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _BundleError("duplicate_key") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise _BundleError("invalid_json") from exc
    if not isinstance(value, dict):
        raise _BundleError("invalid_top_level")
    return value


def _validate_top_level(bundle: dict[str, Any]) -> list[Any]:
    if tuple(bundle.keys()) != TOP_LEVEL_FIELDS:
        raise _BundleError("invalid_top_level")
    if bundle["bundle_version"] != BUNDLE_VERSION:
        raise _BundleError("invalid_bundle_version")
    members = bundle["members"]
    if not isinstance(members, list):
        raise _BundleError("invalid_members")
    if not MIN_MEMBERS <= len(members) <= MAX_MEMBERS:
        raise _BundleError("member_count_invalid")
    return members


def _verify_members(members: list[Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    evidence_hashes: list[str] = []
    challenge_ids: list[str] = []
    seen_hashes: set[str] = set()
    seen_challenges: set[str] = set()
    previous_hash: str | None = None

    for member in members:
        if not isinstance(member, dict):
            raise _BundleError("member_invalid")
        try:
            member_bytes = _json_bytes_preserve_order(member)
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            raise _BundleError("member_invalid") from exc

        result = verify_creator_wallet_control_proof_evidence_json(member_bytes)
        if not result.ok:
            raise _BundleError("member_invalid")

        evidence_hash = result.evidence_sha256
        if not isinstance(evidence_hash, str) or not HEX64_RE.fullmatch(evidence_hash):
            raise _BundleError("member_invalid")

        challenge_id = member.get("expected_challenge_id")
        if not isinstance(challenge_id, str) or not HEX64_RE.fullmatch(challenge_id):
            raise _BundleError("member_invalid")

        if evidence_hash in seen_hashes:
            raise _BundleError("duplicate_member")
        if challenge_id in seen_challenges:
            raise _BundleError("duplicate_challenge")
        if previous_hash is not None and evidence_hash <= previous_hash:
            raise _BundleError("noncanonical_member_order")

        seen_hashes.add(evidence_hash)
        seen_challenges.add(challenge_id)
        evidence_hashes.append(evidence_hash)
        challenge_ids.append(challenge_id)
        previous_hash = evidence_hash

    return tuple(evidence_hashes), tuple(challenge_ids)


def _aggregate_commitment(evidence_hashes: tuple[str, ...]) -> str:
    body = {
        "bundle_version": BUNDLE_VERSION,
        "member_evidence_sha256": list(evidence_hashes),
    }
    return hashlib.sha256(BUNDLE_DOMAIN + _canonical_bytes(body)).hexdigest()


def verify_creator_wallet_control_evidence_bundle_json(
    payload: str | bytes,
) -> CreatorWalletControlEvidenceBundleResult:
    try:
        bundle = _parse(payload)
        members = _validate_top_level(bundle)
        evidence_hashes, _challenge_ids = _verify_members(members)
        return CreatorWalletControlEvidenceBundleResult(
            ok=True,
            code="ok",
            checks=SUCCESS_CHECKS,
            bundle_sha256=hashlib.sha256(_canonical_bytes(bundle)).hexdigest(),
            aggregate_commitment=_aggregate_commitment(evidence_hashes),
            member_evidence_sha256=evidence_hashes,
        )
    except _BundleError as exc:
        return CreatorWalletControlEvidenceBundleResult(False, exc.code)
    except Exception:
        return CreatorWalletControlEvidenceBundleResult(False, "internal_error")


class CreatorWalletControlEvidenceBundleVerifier:
    @classmethod
    def verify_json(
        cls,
        payload: str | bytes,
    ) -> CreatorWalletControlEvidenceBundleResult:
        del cls
        return verify_creator_wallet_control_evidence_bundle_json(payload)
