"""Offline verifier for L28 node-role composition-manifest evidence."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from typing import Any

from coin import node_role_composition_manifest as manifest_core
from coin import node_role_composition_manifest_cli as manifest_cli


EVIDENCE_VERSION = "l28-node-role-composition-manifest-evidence/v0.1"
VERIFIER_VERSION = "l28-node-role-composition-manifest-evidence-verifier/v0.1"
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024
TOP_LEVEL_FIELDS = frozenset({"evidence_version", "manifest", "report"})
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

STABLE_CODES = (
    "evidence_valid",
    "input_type_invalid",
    "evidence_too_large",
    "invalid_encoding",
    "invalid_json",
    "duplicate_key",
    "schema_error",
    "version_unsupported",
    "manifest_invalid",
    "report_schema_invalid",
    "report_id_invalid",
    "manifest_report_mismatch",
    "internal_error",
)

SUCCESS_CHECKS = (
    "identity",
    "schema",
    "manifest_verification",
    "report_schema",
    "report_identifier",
    "manifest_report_binding",
    "semantic_commitment",
)


class _DuplicateKey(ValueError):
    """Raised when a JSON object contains the same key more than once."""


class _EvidenceError(ValueError):
    """Raised for a stable, sanitized evidence-verification failure."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclasses.dataclass(frozen=True)
class NodeRoleCompositionManifestEvidenceResult:
    """Immutable result of offline composition-manifest evidence verification."""

    ok: bool
    code: str
    evidence_sha256: str
    manifest_sha256: str
    report_id: str
    component_ids: tuple[str, ...]
    roles: tuple[str, ...]
    trust_boundary_ids: tuple[str, ...]
    checks: tuple[str, ...]
    detail: str = ""
    evidence_version: str = EVIDENCE_VERSION
    manifest_version: str = manifest_core.MANIFEST_VERSION
    report_version: str = manifest_cli.REPORT_VERSION
    verifier_version: str = VERIFIER_VERSION


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise ValueError("non-finite number")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_composition_manifest_evidence_sha256(evidence: object) -> str:
    """Return the SHA-256 of canonical logical evidence content."""

    return hashlib.sha256(_canonical_bytes(evidence)).hexdigest()


def _decode(payload: str | bytes) -> str:
    if type(payload) is bytes:
        if len(payload) > MAX_EVIDENCE_BYTES:
            raise _EvidenceError("evidence_too_large", "input_exceeds_maximum")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            raise _EvidenceError("invalid_encoding", "input_not_utf8") from None

    if type(payload) is str:
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError:
            raise _EvidenceError("invalid_encoding", "input_not_utf8") from None
        if len(encoded) > MAX_EVIDENCE_BYTES:
            raise _EvidenceError("evidence_too_large", "input_exceeds_maximum")
        return payload

    raise _EvidenceError("input_type_invalid", "input_must_be_text_or_bytes")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _EvidenceError:
        raise
    except _DuplicateKey:
        raise _EvidenceError("duplicate_key", "duplicate_object_key") from None
    except (json.JSONDecodeError, ValueError):
        raise _EvidenceError("invalid_json", "input_not_valid_json") from None

    if type(value) is not dict:
        raise _EvidenceError("schema_error", "top_level_must_be_object")
    return value


def parse_node_role_composition_manifest_evidence_json(
    payload: str | bytes,
) -> dict[str, Any]:
    """Parse strict JSON evidence without running verification."""

    return _parse(payload)


def _validate_top_level(value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if frozenset(value) != TOP_LEVEL_FIELDS:
        raise _EvidenceError("schema_error", "top_level_fields_invalid")

    if type(value.get("evidence_version")) is not str:
        raise _EvidenceError("schema_error", "evidence_version_type_invalid")
    if value["evidence_version"] != EVIDENCE_VERSION:
        raise _EvidenceError("version_unsupported", "evidence_version_unsupported")

    manifest = value.get("manifest")
    report = value.get("report")
    if type(manifest) is not dict:
        raise _EvidenceError("schema_error", "manifest_must_be_object")
    if type(report) is not dict:
        raise _EvidenceError("schema_error", "report_must_be_object")
    return manifest, report


def _validate_report_schema(report: dict[str, Any]) -> str:
    if frozenset(report) != manifest_cli.REPORT_FIELDS:
        raise _EvidenceError("report_schema_invalid", "report_fields_invalid")

    report_id = report.get("report_id")
    if type(report_id) is not str or HEX64_RE.fullmatch(report_id) is None:
        raise _EvidenceError("report_schema_invalid", "report_id_shape_invalid")

    if type(report.get("ok")) is not bool:
        raise _EvidenceError("report_schema_invalid", "report_ok_type_invalid")

    for field in (
        "code",
        "detail",
        "profile",
        "report_version",
        "cli_version",
        "manifest_version",
        "security_profile_version",
        "evidence_version",
        "evidence_report_version",
        "verifier_version",
        "manifest_sha256",
        "security_profile_sha256",
        "evidence_sha256",
        "evidence_report_id",
    ):
        if type(report.get(field)) is not str:
            raise _EvidenceError("report_schema_invalid", "report_field_type_invalid")

    for field in ("component_ids", "roles", "trust_boundary_ids", "checks"):
        if type(report.get(field)) is not list:
            raise _EvidenceError("report_schema_invalid", "report_field_type_invalid")

    return report_id


def _failure_result(
    code: str,
    detail: str,
    *,
    evidence_sha256: str = "",
    manifest_sha256: str = "",
    report_id: str = "",
) -> NodeRoleCompositionManifestEvidenceResult:
    return NodeRoleCompositionManifestEvidenceResult(
        ok=False,
        code=code,
        evidence_sha256=evidence_sha256,
        manifest_sha256=manifest_sha256,
        report_id=report_id,
        component_ids=(),
        roles=(),
        trust_boundary_ids=(),
        checks=(),
        detail=detail,
    )


def _success_result(
    *,
    evidence_sha256: str,
    report_id: str,
    manifest_result: manifest_core.NodeRoleCompositionManifestResult,
) -> NodeRoleCompositionManifestEvidenceResult:
    return NodeRoleCompositionManifestEvidenceResult(
        ok=True,
        code="evidence_valid",
        evidence_sha256=evidence_sha256,
        manifest_sha256=manifest_result.manifest_sha256,
        report_id=report_id,
        component_ids=tuple(manifest_result.component_ids),
        roles=tuple(manifest_result.roles),
        trust_boundary_ids=tuple(manifest_result.trust_boundary_ids),
        checks=SUCCESS_CHECKS,
    )


def verify_node_role_composition_manifest_evidence_json(
    payload: str | bytes,
) -> NodeRoleCompositionManifestEvidenceResult:
    """Verify explicit offline composition-manifest evidence and its report."""

    evidence_sha256 = ""
    manifest_sha256 = ""
    report_id = ""

    try:
        value = _parse(payload)
        manifest, report = _validate_top_level(value)
        evidence_sha256 = compute_composition_manifest_evidence_sha256(value)

        manifest_result = manifest_core.verify_node_role_composition_manifest_json(
            _canonical_bytes(manifest)
        )
        manifest_sha256 = manifest_result.manifest_sha256
        if not manifest_result.ok or manifest_result.code != "manifest_valid":
            raise _EvidenceError("manifest_invalid", "manifest_verification_failed")

        report_id = _validate_report_schema(report)
        try:
            recomputed_report_id = manifest_cli.compute_report_id(report)
        except Exception:
            raise _EvidenceError(
                "report_id_invalid", "report_id_recomputation_failed"
            ) from None
        if recomputed_report_id != report_id:
            raise _EvidenceError("report_id_invalid", "report_id_mismatch")

        expected_report = manifest_cli.build_report(manifest_result)
        if _canonical_bytes(report) != _canonical_bytes(expected_report):
            raise _EvidenceError(
                "manifest_report_mismatch", "report_not_bound_to_manifest"
            )

        return _success_result(
            evidence_sha256=evidence_sha256,
            report_id=report_id,
            manifest_result=manifest_result,
        )
    except _EvidenceError as exc:
        return _failure_result(
            exc.code,
            exc.detail,
            evidence_sha256=evidence_sha256,
            manifest_sha256=manifest_sha256,
            report_id=report_id,
        )
    except Exception:
        return _failure_result(
            "internal_error",
            "internal_failure",
            evidence_sha256=evidence_sha256,
            manifest_sha256=manifest_sha256,
            report_id=report_id,
        )


class NodeRoleCompositionManifestEvidenceVerifier:
    """Class wrapper for the public offline evidence verifier."""

    @classmethod
    def verify_json(
        cls, payload: str | bytes
    ) -> NodeRoleCompositionManifestEvidenceResult:
        del cls
        return verify_node_role_composition_manifest_evidence_json(payload)
