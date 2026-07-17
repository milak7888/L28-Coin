"""Offline verification for Foundation 24 scenario-suite evidence.

This module accepts only caller-supplied JSON-compatible text or bytes.  It
does not discover files, perform I/O, construct runtime nodes, or access a
network, ledger, miner, wallet, checkpoint, or signing service.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from . import node_role_scenario_suite as suite_core
from . import node_role_scenario_suite_cli as suite_cli


EVIDENCE_VERSION = "l28-node-role-scenario-suite-evidence/v0.1"
VERIFIER_VERSION = "l28-node-role-scenario-suite-evidence-verifier/v0.1"
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024

TOP_LEVEL_FIELDS = frozenset({"evidence_version", "suite", "report"})
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
    "suite_invalid",
    "report_schema_invalid",
    "report_id_invalid",
    "suite_report_mismatch",
    "coverage_invalid",
    "terminal_evidence_invalid",
    "internal_error",
)

SUCCESS_CHECKS = (
    "identity",
    "schema",
    "suite_verification",
    "report_schema",
    "report_id",
    "suite_report_binding",
    "transition_coverage",
    "reserved_state_coverage",
    "terminal_evidence",
    "semantic_commitment",
)


class _DuplicateKey(ValueError):
    pass


class _EvidenceError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class NodeRoleScenarioSuiteEvidenceResult:
    ok: bool
    code: str
    evidence_sha256: str
    suite_sha256: str
    report_id: str
    case_count: int
    roles: tuple[str, ...]
    core_transition_count: int
    p2p_transition_count: int
    core_reserved_rejection_count: int
    p2p_reserved_rejection_count: int
    checks: tuple[str, ...]
    detail: str = ""
    evidence_version: str = EVIDENCE_VERSION
    suite_version: str = suite_core.SUITE_VERSION
    report_version: str = suite_cli.REPORT_VERSION
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


def _decode(payload: str | bytes) -> str:
    if type(payload) is bytes:
        raw = payload
        if len(raw) > MAX_EVIDENCE_BYTES:
            raise _EvidenceError("evidence_too_large", "input_exceeds_maximum")
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raise _EvidenceError("invalid_encoding", "input_not_utf8") from None

    if type(payload) is str:
        try:
            raw = payload.encode("utf-8")
        except UnicodeEncodeError:
            raise _EvidenceError("invalid_encoding", "input_not_utf8") from None
        if len(raw) > MAX_EVIDENCE_BYTES:
            raise _EvidenceError("evidence_too_large", "input_exceeds_maximum")
        return payload

    raise _EvidenceError("input_type_invalid", "input_must_be_text_or_bytes")


def _parse(payload: str | bytes) -> dict[str, Any]:
    text = _decode(payload)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey:
        raise _EvidenceError("duplicate_key", "duplicate_object_key") from None
    except (json.JSONDecodeError, ValueError):
        raise _EvidenceError("invalid_json", "input_not_valid_json") from None

    if type(value) is not dict:
        raise _EvidenceError("schema_error", "top_level_must_be_object")
    return value


def _validate_top_level(value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if frozenset(value) != TOP_LEVEL_FIELDS:
        raise _EvidenceError("schema_error", "top_level_fields_invalid")

    version = value.get("evidence_version")
    if type(version) is not str:
        raise _EvidenceError("schema_error", "evidence_version_type_invalid")
    if version != EVIDENCE_VERSION:
        raise _EvidenceError("version_unsupported", "evidence_version_unsupported")

    suite = value.get("suite")
    report = value.get("report")
    if type(suite) is not dict:
        raise _EvidenceError("schema_error", "suite_must_be_object")
    if type(report) is not dict:
        raise _EvidenceError("schema_error", "report_must_be_object")
    return suite, report


def _validate_report_schema(report: dict[str, Any]) -> str:
    if frozenset(report) != suite_cli.REPORT_FIELDS:
        raise _EvidenceError("report_schema_invalid", "report_fields_invalid")

    report_id = report.get("report_id")
    if type(report_id) is not str or HEX64_RE.fullmatch(report_id) is None:
        raise _EvidenceError("report_schema_invalid", "report_id_shape_invalid")

    if type(report.get("ok")) is not bool:
        raise _EvidenceError("report_schema_invalid", "report_ok_type_invalid")
    if type(report.get("code")) is not str:
        raise _EvidenceError("report_schema_invalid", "report_code_type_invalid")
    if type(report.get("case_count")) is not int or type(report.get("case_count")) is bool:
        raise _EvidenceError("report_schema_invalid", "case_count_type_invalid")

    for field in (
        "profile",
        "report_version",
        "cli_version",
        "suite_version",
        "scenario_version",
        "model_version",
        "transcript_version",
        "verifier_version",
        "suite_sha256",
        "detail",
    ):
        if type(report.get(field)) is not str:
            raise _EvidenceError("report_schema_invalid", "report_field_type_invalid")

    for field in (
        "roles",
        "core_covered_transitions",
        "core_missing_transitions",
        "p2p_covered_transitions",
        "p2p_missing_transitions",
        "core_reserved_rejections",
        "core_missing_reserved_rejections",
        "p2p_reserved_rejections",
        "p2p_missing_reserved_rejections",
        "cases",
        "checks",
    ):
        if type(report.get(field)) is not list:
            raise _EvidenceError("report_schema_invalid", "report_field_type_invalid")

    return report_id


def _failure_result(
    code: str,
    detail: str,
    *,
    evidence_sha256: str = "",
    suite_sha256: str = "",
    report_id: str = "",
) -> NodeRoleScenarioSuiteEvidenceResult:
    return NodeRoleScenarioSuiteEvidenceResult(
        ok=False,
        code=code,
        evidence_sha256=evidence_sha256,
        suite_sha256=suite_sha256,
        report_id=report_id,
        case_count=0,
        roles=(),
        core_transition_count=0,
        p2p_transition_count=0,
        core_reserved_rejection_count=0,
        p2p_reserved_rejection_count=0,
        checks=(),
        detail=detail,
    )


def _success_result(
    *,
    evidence_sha256: str,
    report_id: str,
    suite_result: suite_core.NodeRoleScenarioSuiteResult,
) -> NodeRoleScenarioSuiteEvidenceResult:
    return NodeRoleScenarioSuiteEvidenceResult(
        ok=True,
        code="evidence_valid",
        evidence_sha256=evidence_sha256,
        suite_sha256=suite_result.suite_sha256,
        report_id=report_id,
        case_count=suite_result.case_count,
        roles=tuple(suite_result.roles),
        core_transition_count=len(suite_result.core_covered_transitions),
        p2p_transition_count=len(suite_result.p2p_covered_transitions),
        core_reserved_rejection_count=len(suite_result.core_reserved_rejections),
        p2p_reserved_rejection_count=len(suite_result.p2p_reserved_rejections),
        checks=SUCCESS_CHECKS,
    )


def _validate_coverage(
    suite_result: suite_core.NodeRoleScenarioSuiteResult,
) -> None:
    if (
        tuple(suite_result.core_missing_transitions)
        or tuple(suite_result.p2p_missing_transitions)
        or len(suite_result.core_covered_transitions)
        != len(suite_core.CORE_REQUIRED_TRANSITIONS)
        or len(suite_result.p2p_covered_transitions)
        != len(suite_core.P2P_REQUIRED_TRANSITIONS)
    ):
        raise _EvidenceError("coverage_invalid", "transition_coverage_incomplete")

    if (
        tuple(suite_result.core_missing_reserved_rejections)
        or tuple(suite_result.p2p_missing_reserved_rejections)
        or not tuple(suite_result.core_reserved_rejections)
        or not tuple(suite_result.p2p_reserved_rejections)
    ):
        raise _EvidenceError("coverage_invalid", "reserved_coverage_incomplete")


def _validate_terminal_evidence(
    suite_result: suite_core.NodeRoleScenarioSuiteResult,
) -> None:
    if not suite_result.cases:
        raise _EvidenceError("terminal_evidence_invalid", "case_evidence_missing")
    if any(not case.ok or case.final_state != "STOPPED" for case in suite_result.cases):
        raise _EvidenceError("terminal_evidence_invalid", "case_not_terminal")


class NodeRoleScenarioSuiteEvidenceVerifier:
    @classmethod
    def verify_json(cls, payload: str | bytes) -> NodeRoleScenarioSuiteEvidenceResult:
        del cls
        return verify_scenario_suite_evidence_json(payload)


def verify_scenario_suite_evidence_json(
    payload: str | bytes,
) -> NodeRoleScenarioSuiteEvidenceResult:
    evidence_sha256 = ""
    suite_sha256 = ""
    report_id = ""

    try:
        value = _parse(payload)
        suite, report = _validate_top_level(value)
        evidence_sha256 = hashlib.sha256(_canonical_bytes(value)).hexdigest()

        suite_result = suite_core.verify_scenario_suite_json(_canonical_bytes(suite))
        suite_sha256 = suite_result.suite_sha256
        if not suite_result.ok or suite_result.code != "suite_valid":
            raise _EvidenceError("suite_invalid", "suite_verification_failed")

        report_id = _validate_report_schema(report)
        try:
            recomputed_report_id = suite_cli.compute_report_id(report)
        except Exception:
            raise _EvidenceError("report_id_invalid", "report_id_recomputation_failed") from None
        if recomputed_report_id != report_id:
            raise _EvidenceError("report_id_invalid", "report_id_mismatch")

        expected_report = suite_cli.build_report(suite_result)
        if _canonical_bytes(report) != _canonical_bytes(expected_report):
            raise _EvidenceError("suite_report_mismatch", "report_not_bound_to_suite")

        _validate_coverage(suite_result)
        _validate_terminal_evidence(suite_result)

        return _success_result(
            evidence_sha256=evidence_sha256,
            report_id=report_id,
            suite_result=suite_result,
        )
    except _EvidenceError as exc:
        return _failure_result(
            exc.code,
            exc.detail,
            evidence_sha256=evidence_sha256,
            suite_sha256=suite_sha256,
            report_id=report_id,
        )
    except Exception:
        return _failure_result(
            "internal_error",
            "internal_failure",
            evidence_sha256=evidence_sha256,
            suite_sha256=suite_sha256,
            report_id=report_id,
        )


__all__ = [
    "EVIDENCE_VERSION",
    "MAX_EVIDENCE_BYTES",
    "NodeRoleScenarioSuiteEvidenceResult",
    "NodeRoleScenarioSuiteEvidenceVerifier",
    "STABLE_CODES",
    "SUCCESS_CHECKS",
    "VERIFIER_VERSION",
    "verify_scenario_suite_evidence_json",
]
